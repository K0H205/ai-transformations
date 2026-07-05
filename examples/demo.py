"""ParallelAgent と SerialAgent の動作デモ。

実行には Strands Agents SDK と、設定済みのモデル資格情報（例: AWS Bedrock）が必要。

    pip install -r requirements.txt
    python examples/demo.py
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents import AgentBusyError, ParallelAgent, SerialAgent  # noqa: E402


PROMPTS = [
    "日本の首都はどこですか？短く答えて。",
    "フランスの首都はどこですか？短く答えて。",
    "ドイツの首都はどこですか？短く答えて。",
]


async def demo_parallel() -> None:
    print("=== ParallelAgent: 3件を同時実行 ===")
    agent = ParallelAgent(
        system_prompt="あなたは簡潔に答えるアシスタントです。",
        max_concurrency=4,
    )
    started = time.perf_counter()
    results = await agent.ainvoke_many(PROMPTS)
    elapsed = time.perf_counter() - started
    for prompt, result in zip(PROMPTS, results):
        print(f"- Q: {prompt}\n  A: {result}")
    print(f"経過時間: {elapsed:.2f}s\n")


async def demo_serial_queue() -> None:
    print("=== SerialAgent(queue): 後続リクエストはロック解放まで待機 ===")
    agent = SerialAgent(
        system_prompt="あなたは簡潔に答えるアシスタントです。",
        overflow_policy="queue",
    )
    started = time.perf_counter()
    # わざと同時に投入しても、内部ロックにより順番に実行される
    results = await asyncio.gather(*(agent.ainvoke(p) for p in PROMPTS))
    elapsed = time.perf_counter() - started
    for prompt, result in zip(PROMPTS, results):
        print(f"- Q: {prompt}\n  A: {result}")
    print(f"経過時間: {elapsed:.2f}s\n")


async def demo_serial_reject() -> None:
    print("=== SerialAgent(reject): 処理中の同時投入は即エラー ===")
    agent = SerialAgent(
        system_prompt="あなたは簡潔に答えるアシスタントです。",
        overflow_policy="reject",
    )
    first = asyncio.create_task(agent.ainvoke(PROMPTS[0]))
    # 1件目が走り始めるまで少し待つ
    await asyncio.sleep(0)
    try:
        await agent.ainvoke(PROMPTS[1])
    except AgentBusyError as exc:
        print(f"期待通りエラー: {exc}")
    print(f"最初のリクエスト結果: {await first}\n")


async def main() -> None:
    await demo_parallel()
    await demo_serial_queue()
    await demo_serial_reject()


if __name__ == "__main__":
    asyncio.run(main())
