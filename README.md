# Strandsベースの並列／直列AIエージェント

[Strands Agents SDK](https://github.com/strands-agents) をラップした AI エージェントのサンプル集です。
それぞれ独立したディレクトリに、エージェント本体・README・依存関係・テストをまとめています。

- [`parallel_agent/`](parallel_agent/) — **ParallelAgent**
  - 複数のプロンプトを `asyncio.gather` で同時に実行
  - リクエスト毎に独立した `Agent` インスタンスを生成し、会話状態の競合を回避
  - `max_concurrency` で上限を設定可能
- [`serial_agent/`](serial_agent/) — **SerialAgent**
  - `asyncio.Lock` で同時実行を1件に制限
  - `overflow_policy="queue"`（既定）: ロック解放まで待機
  - `overflow_policy="reject"`: 処理中なら `AgentBusyError` で即エラー
  - 単一の `Agent` を使い回すため、会話履歴を保持した直列対話が可能

セットアップ・実行・テスト方法は各ディレクトリの README を参照してください。
