# spec_search_agent — コードから仕様調査を行う Strands Agent

AWS Strands Agents フレームワークを使い、**Agentic Search** でソースコードの実装から
仕様を読み解くサンプルエージェントです。

検索を自前の軽量ツール（標準ライブラリのみ）で行う主実装です。GitHub Copilot SDK に
検索を委譲する実験的サンプルは [`../spec_search_agent_copilot/`](../spec_search_agent_copilot/) を参照してください。

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
  tools.py         # glob/grep/read 相当の自作ツール（標準ライブラリのみ）
  agent.py         # 上記ツールを使う Strands Agent
  requirements.txt
```

## 探索ツール

- `list_files(directory, pattern)` — glob でファイル一覧を取得
- `search_code(pattern, directory, file_glob, context_lines, max_matches)` — 正規表現でコード内容を検索（grep 相当）
- `read_file(path, start_line, end_line, max_lines)` — 行番号付きでファイルを読み込み

いずれも `SPEC_SEARCH_BASE_DIR` 環境変数で指定した調査対象ディレクトリの外は参照できないようガードしています（`agent.py` が内部で設定するため、通常は意識する必要はありません）。

## セットアップ

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-api-key"
```

## 実行

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
