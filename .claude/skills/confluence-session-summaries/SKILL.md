# Confluence Session Summaries

## 概要

Claude Code のセッション終了時に、AIとの作業内容を自動でサマライズしてConfluenceページへ投稿します。

**課題**: AIとの作業はgitの成果物に残らないため、後から「何をやったか」を振り返りにくい。
**解決策**: Stop hook でセッション終了を検知し、Claude APIでサマリーを生成→Confluenceへ自動投稿。

---

## 仕組み

```
セッション終了
    ↓
Stop Hook が起動 (.claude/hooks/post-session-to-confluence.py)
    ↓
セッションのトランスクリプトを受け取る
    ↓
Claude API (claude-sonnet-4-6) でサマリーを生成
    ↓
Confluence REST API でページを作成
```

### 生成されるConfluenceページの構成

- **Session ID** と **生成日時** のメタ情報（infoパネル）
- **背景・目的**: セッションで取り組んだ課題や背景
- **実施した作業**: 行った作業の箇条書き
- **作成・変更したファイル**: ファイルパスと変更概要
- **主要な決定事項・判断**: 設計判断や技術的な選択
- **成果・結果**: セッションで達成されたこと
- **次のステップ・残課題**: 未完了タスクや今後の課題

---

## セットアップ

### 1. 環境変数の設定

以下の環境変数を設定してください（シェルのプロファイルや `.env` ファイルへ追記）。

| 変数名 | 必須 | 説明 | 例 |
|--------|------|------|----|
| `CONFLUENCE_BASE_URL` | ✅ | ConfluenceのベースURL | `https://yourcompany.atlassian.net` |
| `CONFLUENCE_USER` | ✅ | ログイン用メールアドレス | `you@yourcompany.com` |
| `CONFLUENCE_API_TOKEN` | ✅ | Confluence APIトークン | `ATATT3xFfGF0...` |
| `CONFLUENCE_SPACE_KEY` | ✅ | 投稿先スペースキー | `TEAM` |
| `CONFLUENCE_PARENT_ID` | ➕ | 親ページのID（任意） | `123456789` |
| `ANTHROPIC_API_KEY` | ✅ | Anthropic APIキー | `sk-ant-...` |

#### APIトークンの取得方法

Confluence Cloud の場合:
1. https://id.atlassian.com/manage-profile/security/api-tokens を開く
2. **Create API token** をクリック
3. 任意のラベルをつけてトークンをコピー

### 2. 動作確認

設定後に Claude Code でセッションを開始し、何か作業してからセッションを終了すると
自動的にサマリーが生成されてConfluenceへ投稿されます。

```bash
# ログを確認したい場合（標準エラー出力）
# 正常時: "[confluence-hook] ✅ Confluenceページを作成しました: https://..."
# エラー時: "[confluence-hook] ..." というメッセージが表示されます
```

---

## 投稿スキップの条件

以下の場合はサマリー投稿をスキップします（セッション終了はブロックしません）:

- トランスクリプトが空のとき
- ユーザー発話が2件未満のとき（短すぎるセッション）
- 必要な環境変数が未設定のとき
- APIエラーが発生したとき

---

## ファイル構成

```
.claude/
├── settings.json                          # Stop hookの設定
├── hooks/
│   └── post-session-to-confluence.py     # hookスクリプト本体
└── skills/
    └── confluence-session-summaries/
        └── SKILL.md                       # このファイル
```

---

## カスタマイズ

### ページタイトルの変更

`post-session-to-confluence.py` の `main()` 関数内で変更できます:

```python
title = f"AI作業ログ {date_str} [{short_id}]"  # ← ここを変更
```

### サマリーの構成変更

`summarize_session()` 関数内の `prompt` を編集することで、
出力するセクションや記述スタイルを変更できます。

### スキップ条件の変更

```python
# 現在: ユーザー発話2件未満はスキップ
if len(user_messages) < 2:
    ...
```

この閾値を変更することで、より短いセッションもキャプチャできます。

---

## トラブルシューティング

| 問題 | 確認事項 |
|------|---------|
| ページが作成されない | 環境変数がすべて設定されているか確認 |
| Confluence APIエラー 401 | `CONFLUENCE_USER` と `CONFLUENCE_API_TOKEN` が正しいか確認 |
| Confluence APIエラー 404 | `CONFLUENCE_BASE_URL` と `CONFLUENCE_SPACE_KEY` が正しいか確認 |
| Anthropic APIエラー | `ANTHROPIC_API_KEY` が正しいか確認 |
| スクリプトが見つからない | `python3` が利用可能か `python3 --version` で確認 |

---

## 関連ファイル

- [`.claude/settings.json`](../../settings.json) — Stop hookの登録設定
- [`.claude/hooks/post-session-to-confluence.py`](../../hooks/post-session-to-confluence.py) — hookスクリプト本体
