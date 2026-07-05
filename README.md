# Strandsベースの並列／直列AIエージェント

[Strands Agents SDK](https://github.com/strands-agents) をラップし、
並列リクエストに対応するエージェントと、直列処理のみ受け付けるエージェントを提供します。

## 構成

- `src/agents/parallel_agent.py` — **ParallelAgent**
  - 複数のプロンプトを `asyncio.gather` で同時に実行
  - リクエスト毎に独立した `Agent` インスタンスを生成し、会話状態の競合を回避
  - `max_concurrency` で上限を設定可能
- `src/agents/serial_agent.py` — **SerialAgent**
  - `asyncio.Lock` で同時実行を1件に制限
  - `overflow_policy="queue"`（既定）: ロック解放まで待機
  - `overflow_policy="reject"`: 処理中なら `AgentBusyError` で即エラー
  - 単一の `Agent` を使い回すため、会話履歴を保持した直列対話が可能

## 使用例

```python
import asyncio
from agents import ParallelAgent, SerialAgent

async def main():
    parallel = ParallelAgent(system_prompt="簡潔に答えて", max_concurrency=4)
    results = await parallel.ainvoke_many(["東京は？", "パリは？", "ベルリンは？"])

    serial = SerialAgent(system_prompt="簡潔に答えて", overflow_policy="queue")
    r1 = await serial.ainvoke("こんにちは")
    r2 = await serial.ainvoke("前回の挨拶を覚えていますか？")

asyncio.run(main())
```

## セットアップ

```bash
pip install -r requirements.txt
python examples/demo.py
```

Strands が使用するモデル（例: AWS Bedrock）の資格情報は環境変数等で別途設定してください。

## テスト

Strands 実モデルを呼ばずに、並列性・直列性の挙動のみを検証します。

```bash
python -m unittest tests.test_agents -v
```
