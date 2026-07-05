# spec_search_agent — コードから仕様調査を行う Strands Agent

AWS Strands Agents フレームワークを使い、**Agentic Search** でソースコードの実装から
仕様を読み解くサンプルエージェントです。

## Agentic Search とは

ベクトル検索などの一発検索ではなく、エージェント自身が

1. ファイル一覧を見て構成を把握する
2. キーワードや関数名で検索する
3. 該当箇所を実際に読む
4. 根拠が足りなければ 1〜3 をさらに繰り返す

というツール呼び出しのループを、十分な根拠が集まるまで自律的に繰り返す方式です。
Claude Code の Explore サブエージェントが Glob/Grep/Read を繰り返すのと同じ考え方を、
Strands Agents 上で再現しています。

## ディレクトリ構成

```
spec_search_agent/
  tools.py                    # 主実装: glob/grep/read 相当の自作ツール（標準ライブラリのみ）
  agent.py                    # 主実装: 上記ツールを使う Strands Agent
  tools_copilot_search.py     # 実験的サンプル: GitHub Copilot SDK に検索を委譲するツール
  agent_copilot_search.py     # 実験的サンプル: 上記ツールを使う Strands Agent
  requirements.txt            # 主実装用の依存関係
  requirements-copilot.txt    # 実験的サンプル用の追加依存関係
```

## 主実装（推奨）

`tools.py` が提供する3つの探索ツールを、`agent.py` の Strands Agent が組み合わせて使います。

- `list_files(directory, pattern)` — glob でファイル一覧を取得
- `search_code(pattern, directory, file_glob, context_lines, max_matches)` — 正規表現でコード内容を検索（grep 相当）
- `read_file(path, start_line, end_line, max_lines)` — 行番号付きでファイルを読み込み

いずれも `SPEC_SEARCH_BASE_DIR` 環境変数で指定した調査対象ディレクトリの外は参照できないようガードしています（`agent.py` が内部で設定するため、通常は意識する必要はありません）。

### セットアップ

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-api-key"
```

### 実行

```bash
# デモモード: strands_sample を対象に、あらかじめ用意した質問で動作確認する
python agent.py

# インタラクティブモード: 任意のディレクトリを対象に対話的に仕様を質問する
python agent.py interactive [対象ディレクトリ]
```

回答は次の形式でまとめられます。

```
概要
入力
出力・挙動
制約・エラー処理
根拠（file:line）
```

## 実験的サンプル: GitHub Copilot SDK 委譲版

`tools_copilot_search.py` / `agent_copilot_search.py` は、コード探索そのものを
GitHub Copilot SDK (`github-copilot-sdk`) 経由で Copilot CLI のエージェントに委譲する
構成です。Copilot SDK は単体の検索 API を公開しておらず、Copilot CLI のエージェント
実行エンジン全体をプロセスとして起動する設計のため、この方式では「検索」を丸ごと
別のエージェントに委譲する形になります。

**この構成はこのリポジトリの開発環境では未検証です。** 動かすには以下が別途必要です。

- Copilot CLI がインストール済みで PATH から実行できること
- GitHub Copilot サブスクリプションでの認証、または BYOK 用の環境変数（利用する LLM の API キー）

```bash
pip install -r requirements.txt -r requirements-copilot.txt
export ANTHROPIC_API_KEY="your-api-key"   # このエージェント自身のモデル用
# Copilot CLI 側の認証は copilot コマンドのドキュメントに従って別途設定する

python agent_copilot_search.py [対象ディレクトリ]
```

## どちらを使うべきか

| | 主実装 (`agent.py`) | 実験的サンプル (`agent_copilot_search.py`) |
|---|---|---|
| 追加の依存 | なし（`strands-agents`, `anthropic` のみ） | GitHub Copilot SDK + Copilot CLI + サブスクリプション/BYOK |
| 動作確認 | 済み | 未検証（この環境に認証情報がないため） |
| 検索の中身 | 自前の glob/grep/read | Copilot CLI エージェントへの委譲 |

特別な理由がなければ主実装 (`agent.py`) を使ってください。
