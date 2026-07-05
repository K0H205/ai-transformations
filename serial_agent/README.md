# serial_agent — 直列処理のみ受け付ける Strands Agent

[Strands Agents SDK](https://github.com/strands-agents) をラップし、同時に1件のリクエストしか
処理しない `SerialAgent` のサンプルです。

`asyncio.Lock` により同時実行を1件に制限します。

- `overflow_policy="queue"`（既定）: 処理中はロック解放まで待機
- `overflow_policy="reject"`: 処理中なら `AgentBusyError` を即座に送出

単一の `Agent` インスタンスを使い回すため、会話履歴を保持した直列対話が可能です。

並列に処理できる `ParallelAgent` は [`../parallel_agent/`](../parallel_agent/) を参照してください。

## ディレクトリ構成

```
serial_agent/
  agent.py         # SerialAgent 本体・デモ実行スクリプト
  requirements.txt
  tests/
    test_agent.py  # 直列性を検証するユニットテスト
```

## 使用例

```python
import asyncio
from agent import SerialAgent

async def main():
    agent = SerialAgent(system_prompt="簡潔に答えて", overflow_policy="queue")
    r1 = await agent.ainvoke("こんにちは")
    r2 = await agent.ainvoke("前回の挨拶を覚えていますか？")

asyncio.run(main())
```

## セットアップ

```bash
pip install -r requirements.txt
```

Strands が使用するモデル（例: AWS Bedrock）の資格情報は環境変数等で別途設定してください。

## 実行

```bash
python agent.py
```

## テスト

Strands 実モデルを呼ばずに、直列性の挙動のみを検証します。

```bash
python -m unittest tests.test_agent -v
```
