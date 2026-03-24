# 日報 自動生成

## 概要

GitHub Copilot CLI のセッションログを取得し、Claude がサマライズして Confluence に日報を自動投稿する。

**フロー**: 日付ヒアリング → セッションファイル検索 → サマリー生成 → ユーザー確認 → Confluence 投稿

---

## Confluence 設定

### スペースキー

```
YOUR_CONFLUENCE_SPACE_KEY
```

> ⚠️ 上記を実際の Confluence スペースキー（例: `DEV`、`TEAM`）に書き換えてください。

### 親ページ ID

```
YOUR_CONFLUENCE_PARENT_PAGE_ID
```

> ⚠️ 日報を格納する親ページの数値 ID に書き換えてください。
> Confluence ページ URL の `?pageId=XXXXXXX` または `/pages/XXXXXXX/` から確認できます。

### Confluence ベース URL

```
YOUR_CONFLUENCE_BASE_URL
```

> ⚠️ 例: `https://your-org.atlassian.net/wiki` に書き換えてください。

---

## 実行手順

### Step 1: 対象日付のヒアリング（必須・最初に行うこと）

コマンド起動直後に、ユーザーへ以下を確認する:

```
日報を作成する日付を教えてください。
（例: 今日、昨日、2026-02-20 など。通常は平日を指定してください。）
```

- ユーザーの回答を解釈して ISO 形式（YYYY-MM-DD）の日付に変換する
  - 「今日」→ 実行時の日付
  - 「昨日」→ 実行時の前日
  - 「YYYY-MM-DD」形式 → そのまま使用
- 確定した日付が**土曜（weekday=6）または日曜（weekday=0）の場合**は以下の警告を出す:

```
⚠️ 指定された日付 YYYY-MM-DD は週末（土/日）です。
このまま続行しますか？
```

- ユーザーが続行を選択した場合のみ次のステップへ進む
- 確定した日付（`TARGET_DATE`）を以降のすべてのステップで使用する

---

### Step 2: セッションファイルの検索と読み込み

GitHub Copilot CLI は `~/.copilot/session-state/` 配下のサブディレクトリに `events.jsonl` としてセッションイベントを保存する。

#### 2-1. メイン検索（ファイル更新日時で絞り込み）

Bash ツールで以下を実行し、TARGET_DATE のセッションファイル一覧を取得する:

```bash
find ~/.copilot/session-state/ -name "events.jsonl" \
  -newermt "TARGET_DATE 00:00:00" \
  ! -newermt "TARGET_DATE 23:59:59" \
  2>/dev/null | sort
```

#### 2-2. フォールバック検索（0 件の場合）

上記で 0 件の場合は、直近 7 日以内の全 `events.jsonl` を検索する:

```bash
find ~/.copilot/session-state/ -name "events.jsonl" \
  -newermt "7 days ago" \
  2>/dev/null | sort
```

Read ツールでこれらのファイルを読み込み、各イベントの `timestamp` フィールドが
TARGET_DATE 内（00:00〜23:59 JST / UTC+9）のものだけを抽出する。

#### 2-3. ファイルが見つからない場合

それでも 0 件の場合は以下を表示してユーザーに確認を求める:

```
TARGET_DATE の GitHub Copilot CLI セッションが見つかりませんでした。
・別の日付を指定しますか？
・セッションファイルのパスを手動で指定しますか？
・セッションなしで手動入力モードに切り替えますか？
```

---

### Step 3: AI によるサマリー生成

Step 2 で取得した `events.jsonl` の内容を Read ツールで読み込み、以下の観点で分析する。

#### events.jsonl の主なイベントタイプ

| type | 内容 |
|------|------|
| `user_message` | ユーザーの入力テキスト |
| `assistant_message` | Copilot の回答テキスト |
| `tool_use` | Copilot が実行したコマンド・ツール |
| `tool_result` | ツール実行の結果・出力 |
| `session_start` / `session_end` | セッション境界 |

#### サマリー生成の観点

以下の 2 セクション（エラーがあれば第 3 セクションも）を日本語で生成する:

**【作業サマリー】**
- 何を達成しようとしたか（ゴール）
- 実際に行った作業（実装・調査・修正・コードレビューなど）
- 使用した主要なコマンド・ファイル・リポジトリ名

**【技術的な学び・メモ】**
- 新たに理解したコマンドや API
- ハマりやすいポイント・注意点
- 今後使えそうなパターン・テクニック

**【詰まったこと・解決策】**（`tool_result` にエラー出力が含まれる場合のみ）
- 遭遇したエラーや問題
- 試みた解決策と結果

文体: 箇条書き（`-` プレフィックス）。技術用語は日本語訳より英語表記を優先。

生成後、チャット内に表示して Step 4 に進む。

---

### Step 4: ユーザーへの確認（必須・スキップ禁止）

**以下をユーザーに提示し、明示的な承認を得ること。承認前に Confluence へ投稿してはいけない。**

1. Step 3 で生成したサマリーをそのまま表示する
2. 「このまま Confluence に投稿しますか？」と確認を求める
3. ユーザーが修正を求めた場合は内容を修正して再確認する
4. ユーザーが「はい」と回答した場合のみ Step 5 に進む

---

### Step 5: Confluence へ投稿

#### 5-1. 重複チェック

`mcp__confluence__search_content` を呼び出し、同じタイトルのページが存在しないか確認する:

```
mcp__confluence__search_content を呼び出し、
spaceKey: CONFLUENCE_SPACE_KEY
query:    title = "日報 TARGET_DATE"
で既存ページを検索してください。
```

既存ページが見つかった場合は以下を表示してユーザーに確認を求める:

```
⚠️ 「日報 TARGET_DATE」はすでに Confluence に存在します。
URL: [既存ページの URL]
・中止しますか？
・重複を承知で新規ページとして追加しますか？
```

#### 5-2. ページ本文の組み立て

Step 3 のサマリーを以下の Confluence ストレージ形式（HTML）に埋め込む:

```html
<h1>日報 TARGET_DATE</h1>

<h2>作業サマリー</h2>
<ul>
  <li>サマリー箇条書きをそれぞれ &lt;li&gt; タグで展開</li>
</ul>

<h2>技術的な学び・メモ</h2>
<ul>
  <li>学び箇条書きをそれぞれ &lt;li&gt; タグで展開</li>
</ul>

<h2>詰まったこと・解決策</h2>
<ul>
  <li>該当なしの場合はこのセクションを省略</li>
</ul>

<hr/>
<p><em>自動生成: claude daily-report / TARGET_DATETIME</em></p>
```

#### 5-3. ページ作成

`mcp__confluence__create_page` を呼び出してページを作成する:

```
mcp__confluence__create_page を呼び出し、
title:      "日報 TARGET_DATE"
spaceKey:   CONFLUENCE_SPACE_KEY
parentId:   CONFLUENCE_PARENT_PAGE_ID
body:       (Step 5-2 で組み立てた HTML)
bodyFormat: "storage"
で Confluence ページを作成してください。
```

#### 5-4. 完了確認

- **成功時**: 作成されたページの URL を表示してユーザーに完了を報告する
- **失敗時**: エラーメッセージを表示し、Step 3 のサマリーをチャットに残して手動投稿を促す

---

## 注意事項

| 項目 | 内容 |
|------|------|
| **日付ヒアリング** | Step 1 の日付確認を必ず最初に行うこと。省略禁止 |
| **投稿前の確認** | Step 4 のユーザー承認を必ずとること。省略・スキップ禁止 |
| **重複チェック** | Step 5-1 の既存ページ検索は必ず実行すること |
| **セッションファイル** | `~/.copilot/session-state/` 配下を Read ツールと Bash ツールで読み込む |
| **タイムゾーン** | `events.jsonl` のタイムスタンプが UTC の場合は +9h してから TARGET_DATE と比較する |
| **セッションなし** | ファイルが見つからない場合はユーザーへ確認し、手動入力モードに切り替える |

---

## トラブルシューティング

| 問題 | 対処法 |
|------|--------|
| `~/.copilot/session-state/` が存在しない | GitHub Copilot CLI のバージョンを確認。古いバージョンでは `~/.copilot/history-session-state/` を試す |
| `events.jsonl` が空 | セッションが途中で中断した可能性あり。前後のセッションディレクトリを確認する |
| Confluence MCP ツールが見つからない | MCP サーバーが起動しているか確認。`mcp__confluence__*` の実際のツール名を確認する |
| 重複ページが作成された | Confluence 上で手動マージし、古いページを削除する |
| サマリーの精度が低い | `events.jsonl` の内容をユーザーが確認し、Step 4 で直接修正して投稿する |
| タイムスタンプがずれる | システムタイムゾーンを確認し、UTC 基準で ±9h を適用して TARGET_DATE と比較する |
