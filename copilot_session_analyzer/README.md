# Copilot CLI セッション履歴分析ツール

[GitHub Copilot CLI](https://github.com/github/copilot-cli) が `~/.copilot` 配下に残す
セッション履歴(`session-store.db` + `session-state/*/events.jsonl`)を分析し、
「繰り返し出る指示・失敗パターン」(摩擦シグナル)を検出して、
AGENTS.md追記案などのハーネス改善提案をMarkdownレポートとして出力するCLIツールです。

## アーキテクチャ

```
extractor.py  → 抽出層: session-store.db(SQLite, read-only) + events.jsonl を読み取る
signals.py    → 決定論集計層: ツール失敗率・再試行・権限拒否・軌道修正・コストをLLM無しで算出
masking.py    → マスキング層: LLM送信前に資格情報・トークン・メールアドレス等を正規表現で除去
llm.py        → LLM層: Anthropic API で改善提案を自由文Markdownとして生成(1回のreduce呼び出し)
report.py     → 出力層: Markdownレポートを組み立てる
analyzer.py   → CLIエントリポイント
```

パイプラインは「ローカルの決定論的集計」と「LLM呼び出し」を明確に分離しています。
`--no-llm` を指定すればAPIキーなしで決定論集計のみのレポートを取得できます
(企画書の推奨する「まず摩擦シグナルが実際に取れるか検証する」フェーズに対応)。

## セットアップ

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-api-key"   # --no-llm を使わない場合のみ必須
```

## 使い方

```bash
# 決定論集計のみ(APIキー不要)
python analyzer.py --copilot-home ~/.copilot --no-llm

# LLM提案つき、直近14日、特定リポジトリに絞り込み
python analyzer.py --copilot-home ~/.copilot --days 14 --repo myservice-repo

# モデルを指定し、ファイルに出力
python analyzer.py --model claude-opus-4-8 --output report.md
```

### 主なオプション

| オプション | 説明 |
|---|---|
| `--copilot-home` | Copilot CLIのホームディレクトリ(既定: `~/.copilot`。`COPILOT_HOME`相当) |
| `--days N` | 直近N日以内のセッションのみを対象にする |
| `--repo NAME` | 特定のリポジトリ名でセッションを絞り込む |
| `--no-llm` | LLMを呼び出さず、決定論集計のみのレポートを出力する(APIキー不要) |
| `--model ID` | LLM提案生成に使うモデルID(既定: `claude-sonnet-5`) |
| `--output PATH` | レポートの出力先ファイルパス(既定: 標準出力) |

## 検出する摩擦シグナル

| シグナル | 検出方法 |
|---|---|
| ツール失敗 | `tool.execution_complete` の `success=false` をツール名別に集計 |
| 再試行 | 直前に失敗したツールと同名のツールが連続で呼び出された回数 |
| 権限拒否 | `permission.completed` の `result.kind` が `denied-*` |
| 軌道修正(follow-up) | セッション内の `user.message` 数(最初の指示を除く) |
| コンテキスト逼迫 | `session.compaction_start` の発生回数 |
| コスト | `assistant.usage` の inputTokens / outputTokens / cost 合計 |

`--no-llm` を付けない場合、これらの集計とマスク済みの代表的失敗メッセージのみを
Anthropic APIに送信し、AGENTS.md追記案・Agent Skill化候補などの改善提案を
自由文Markdownとして受け取り、レポートにそのまま埋め込みます。
**生のevents.jsonl全文は送信しません。**

提案の見出し形式(`### 提案N: <タイトル> [対象: ... / 信頼度: ...]`)はシステム
プロンプトで指示していますが、structured outputs による型固定は行っていないため、
出力形式は厳密には保証されません。その代わりモデルの制約が無く任意のモデルを
`--model` で指定できます。

## テスト

実際のCopilot CLI環境が無くても、合成fixture(`tests/conftest.py`)で
オフラインテストできます。

```bash
pytest tests/ -v
```

## 既知の制約

- `session-store.db` と `events.jsonl` のスキーマは**非公式・未ドキュメント化**です。
  CLIのバージョンによってイベント型やDBの列が変わりうるため、本ツールは
  「存在する列/フィールドだけを使う」緩いパースを行い、壊れた行やスキーマの揺れを
  エラーにせず読み飛ばします(パース不能な行数はレポートに警告として表示されます)。
- `session-store.db` は他プロセス(Copilot CLI本体)からロックされている可能性があるため、
  一時ディレクトリにコピーしてから read-only で開きます。
- マスキングは正規表現ベースの最小実装です。Presidio等の高度なPII検出は導入していません。
  本番運用では機密情報の混入リスクを別途評価してください。
- LLM提案は決定論集計とサンプルメッセージのみを根拠とするため、根拠セッション数が少ない
  場合は `confidence: low` として提案されます。人間によるレビューを前提とした設計です。
