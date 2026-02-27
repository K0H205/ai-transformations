# Daily Report Skill

## 概要

今日のClaudeとの作業セッションをすべて読み込み、1日分の日報としてまとめてConfluenceへ投稿する。

**ポイント**: サマライズはClaude自身が行うためAnthropicへの追加API呼び出しは不要。

---

## 必要な環境変数

| 変数名 | 説明 | 例 |
|--------|------|----|
| `CONFLUENCE_BASE_URL` | ConfluenceのベースURL | `https://yourcompany.atlassian.net` |
| `CONFLUENCE_USER` | ログイン用メールアドレス | `you@yourcompany.com` |
| `CONFLUENCE_API_TOKEN` | Confluence APIトークン | `ATATT3xFfGF0...` |
| `CONFLUENCE_SPACE_KEY` | 投稿先スペースキー | `TEAM` |
| `CONFLUENCE_PARENT_ID` | 親ページID（任意） | `123456789` |

---

## 実行手順

### Step 1: 対象日付のヒアリング

Skill起動後、最初にユーザーへ確認する:

```
日報を作成する日付を教えてください。
（例: 今日、昨日、2026-02-26）
```

- 「今日」→ 実行時の日付（YYYY-MM-DD）
- 「昨日」→ 前日の日付
- 「YYYY-MM-DD」→ そのまま使用
- 確定した日付を `TARGET_DATE` として以降で使用する

---

### Step 2: セッションファイルの収集

Bashで `TARGET_DATE` に変更されたJSONLファイルを収集する:

```python
import os, glob, json
from datetime import datetime, date

target = date.fromisoformat("TARGET_DATE")  # ← TARGET_DATE に置換
day_start = datetime.combine(target, datetime.min.time()).timestamp()
day_end   = datetime.combine(target, datetime.max.time()).timestamp()

files = []
for f in glob.glob(os.path.expanduser("~/.claude/projects/**/*.jsonl"), recursive=True):
    mtime = os.path.getmtime(f)
    if day_start <= mtime <= day_end:
        files.append(f)

print(f"対象ファイル数: {len(files)}")
for f in files:
    print(f)
```

出力されたファイルパスをすべてメモしておく。

ファイルが0件の場合:
```
TARGET_DATE にセッションが見つかりませんでした。
```
とユーザーへ伝えてスキップする。

---

### Step 3: セッション内容の読み込み

Step 2で収集した各JSONLファイルをReadツールで読み込む。

各ファイルから以下を抽出する:
- **ユーザーのメッセージ**（`role: user` の `content`）
- **Claudeのテキスト応答**（`role: assistant` かつ `type: text` のブロック）
- **実行したツール**（`type: tool_use` の `name` と主要な入力値）

> ファイルが多い・大きい場合はファイルごとの要点を順次まとめていく。

---

### Step 4: 日報の生成

Step 3の内容を読んだClaude自身が、以下の構成で日報を作成する:

```markdown
# 日報 TARGET_DATE

## 今日取り組んだこと（概要）
（1〜3文で一言サマリー）

## 作業詳細

### セッション 1
- **目的**: ...
- **実施した作業**: ...
- **作成・変更したファイル**: ...

### セッション 2（複数ある場合）
...

## 主要な決定事項
（重要な技術選択や設計判断）

## 成果・完了したこと
（今日達成できたこと）

## 明日以降の課題
（残タスク・積み残し）
```

---

### Step 5: ユーザーへの確認（必須・スキップ禁止）

生成した日報をユーザーに表示し、以下を確認する:

1. 日報の内容をそのまま表示する
2. 「この内容でConfluenceに投稿しますか？」と確認する
3. ユーザーが修正を求めた場合は修正して再確認する
4. ユーザーが「はい」と回答した場合のみ Step 6 へ進む

---

### Step 6: Confluenceへ投稿

ユーザー承認後、以下のPythonスクリプトを `/tmp/post-daily-report.py` として作成してBashで実行する。

`SUMMARY_HTML` には Step 4 の日報をConfluence storage format（XHTML）に変換したものを入れる。

```python
import os, json, base64, urllib.request, urllib.error
from datetime import datetime

base_url   = os.environ["CONFLUENCE_BASE_URL"].rstrip("/")
user       = os.environ["CONFLUENCE_USER"]
token      = os.environ["CONFLUENCE_API_TOKEN"]
space_key  = os.environ["CONFLUENCE_SPACE_KEY"]
parent_id  = os.environ.get("CONFLUENCE_PARENT_ID")

creds = base64.b64encode(f"{user}:{token}".encode()).decode()

title = "日報 TARGET_DATE"  # ← TARGET_DATE に置換

# ここに Step 4 の日報をXHTML変換して埋め込む
summary_html = """SUMMARY_HTML"""  # ← 置換

page_data = {
    "type": "page",
    "title": title,
    "space": {"key": space_key},
    "body": {
        "storage": {
            "value": summary_html,
            "representation": "storage",
        }
    },
}
if parent_id:
    page_data["ancestors"] = [{"id": parent_id}]

body = json.dumps(page_data).encode()
req = urllib.request.Request(
    f"{base_url}/wiki/rest/api/content",
    data=body,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Basic {creds}",
    },
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        pid = result["id"]
        print(f"✅ 投稿完了: {base_url}/wiki/spaces/{space_key}/pages/{pid}")
except urllib.error.HTTPError as e:
    print(f"❌ エラー {e.code}: {e.read().decode()[:300]}")
```

スクリプトの `SUMMARY_HTML` と `TARGET_DATE` を実際の値に置換してから実行する:

```bash
python3 /tmp/post-daily-report.py
```

---

### Step 7: 完了報告

- **成功時**: ConfluenceページのURLをユーザーへ伝える
- **エラー時**: エラーメッセージを共有し、原因と対処法を案内する

---

## Markdown → Confluence XHTML の変換ルール

Step 6 で `summary_html` を組み立てる際に使う変換対応表:

| Markdown | Confluence XHTML |
|----------|-----------------|
| `# 見出し1` | `<h1>見出し1</h1>` |
| `## 見出し2` | `<h2>見出し2</h2>` |
| `### 見出し3` | `<h3>見出し3</h3>` |
| `- 項目` | `<ul><li>項目</li></ul>` |
| `**太字**` | `<strong>太字</strong>` |
| `` `code` `` | `<code>code</code>` |
| 通常テキスト | `<p>テキスト</p>` |
| `---` | `<hr/>` |

コードブロック（` ``` `）は以下の形式:
```xml
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">python</ac:parameter>
  <ac:plain-text-body><![CDATA[コード内容]]></ac:plain-text-body>
</ac:structured-macro>
```

---

## 注意事項

| 項目 | 内容 |
|------|------|
| **日付ヒアリング** | Step 1 を必ず最初に行う |
| **ユーザー確認** | Step 5 の承認前に投稿してはいけない |
| **APIキー不要** | サマライズはClaude自身が行うため `ANTHROPIC_API_KEY` は不要 |
| **ファイルが大量** | セッションが多い場合は要点のみ抽出してトークン節約 |

---

## トラブルシューティング

| 問題 | 対処 |
|------|------|
| セッションファイルが見つからない | `~/.claude/projects/` の存在を確認 |
| Confluence 401エラー | `CONFLUENCE_USER` と `CONFLUENCE_API_TOKEN` を確認 |
| Confluence 404エラー | `CONFLUENCE_BASE_URL` と `CONFLUENCE_SPACE_KEY` を確認 |
| 環境変数が未設定 | シェルのプロファイル（`.bashrc` / `.zshrc`）に `export` を追記 |
