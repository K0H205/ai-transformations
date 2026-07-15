# Strandsベースの AI エージェント サンプル集

[Strands Agents SDK](https://github.com/strands-agents) をラップした AI エージェントのサンプル集です。
それぞれ独立したディレクトリに、エージェント本体・README・依存関係・テストをまとめています。

- [`strands_sample/`](strands_sample/) — **基本サンプル**
  - Strands Agents フレームワークを使った最小構成のエージェント例
- [`parallel_agent/`](parallel_agent/) — **ParallelAgent**
  - 複数のプロンプトを `asyncio.gather` で同時に実行
  - リクエスト毎に独立した `Agent` インスタンスを生成し、会話状態の競合を回避
  - `max_concurrency` で上限を設定可能
- [`serial_agent/`](serial_agent/) — **SerialAgent**
  - `asyncio.Lock` で同時実行を1件に制限
  - `overflow_policy="queue"`（既定）: ロック解放まで待機
  - `overflow_policy="reject"`: 処理中なら `AgentBusyError` で即エラー
  - 単一の `Agent` を使い回すため、会話履歴を保持した直列対話が可能
- [`strands_rag_sample/`](strands_rag_sample/) — **RAG サンプル**
  - Strands Agents SDK と RAG（検索拡張生成）を組み合わせたエージェント
  - インメモリの `RAGStore` に対して埋め込み生成・コサイン類似度検索を行うツールを実装
- [`spec_search_agent/`](spec_search_agent/) — **仕様調査エージェント**
  - Agentic Search（ファイル一覧の把握 → キーワード検索 → 該当箇所の読解 → 繰り返し）で
    ソースコードの実装から仕様を読み解くサンプル
  - 検索は標準ライブラリのみの軽量ツールで自前実装
- [`spec_search_agent_copilot/`](spec_search_agent_copilot/) — **GitHub Copilot SDK 委譲版（実験的・動作未検証）**
  - `spec_search_agent` と同じ仕様調査を、探索処理そのものを GitHub Copilot SDK 経由で
    Copilot CLI のエージェントに委譲する構成で実現
  - このリポジトリの開発環境では未検証。Copilot CLI のインストールと認証が別途必要
- [`copilot_session_analyzer/`](copilot_session_analyzer/) — **Copilot CLI セッション履歴分析ツール**
  - Copilot CLI が `~/.copilot` に残すセッション履歴（SQLite + events.jsonl）から
    ツール失敗・再試行・権限拒否などの「摩擦シグナル」を決定論的に集計
  - Anthropic API（structured outputs）でAGENTS.md追記案などのハーネス改善提案を生成
  - `--no-llm` でAPIキー無しでも決定論集計のみのレポートを取得可能

セットアップ・実行・テスト方法は各ディレクトリの README を参照してください。
