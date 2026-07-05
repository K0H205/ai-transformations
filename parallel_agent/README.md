# parallel_agent — 並列リクエストを受け付ける Strands Agent

[Strands Agents SDK](https://github.com/strands-agents) をラップし、複数のプロンプトを
`asyncio.gather` で同時に実行する `ParallelAgent` のサンプルです。

同時実行中の会話状態の競合を避けるため、リクエストごとに独立した `Agent` インスタンスを
生成してから `invoke_async` を呼び出します。`max_concurrency` を指定すると同時実行数の
上限を設定できます。

直列にしか処理できない `SerialAgent` は [`../serial_agent/`](../serial_agent/) を参照してください。

## ディレクトリ構成

```
parallel_agent/
  agent.py         # ParallelAgent 本体・デモ実行スクリプト
  requirements.txt
  tests/
    test_agent.py  # 並列性を検証するユニットテスト
```

## 使用例

```python
import asyncio
from agent import ParallelAgent

async def main():
    agent = ParallelAgent(system_prompt="簡潔に答えて", max_concurrency=4)
    results = await agent.ainvoke_many(["東京は？", "パリは？", "ベルリンは？"])

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

Strands 実モデルを呼ばずに、並列性の挙動のみを検証します。

```bash
python -m unittest tests.test_agent -v
```
