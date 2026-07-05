"""直列リクエストのみ受け付けるAIエージェント。

Strands Agents SDK をラップし、同時に1件のリクエストしか処理しない。
後続のリクエストは ``queue`` モードならロック上で待機し、
``reject`` モードなら :class:`AgentBusyError` を送出して即座に失敗する。
単一の ``Agent`` インスタンスを使い回すため、会話履歴を保持したまま
順序が保証された対話を実現できる。

セットアップ:
    pip install -r requirements.txt

実行:
    python agent.py
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Iterable, Literal

from strands import Agent


class AgentBusyError(RuntimeError):
    """他リクエストが処理中のため、即時に受け付けられない場合に送出。"""


OverflowPolicy = Literal["queue", "reject"]


class SerialAgent:
    """同時実行を禁止するAIエージェント。

    Parameters
    ----------
    system_prompt, tools, model, agent_kwargs:
        :class:`strands.Agent` の構築に用いるパラメータ。
    overflow_policy:
        ``"queue"`` なら処理中はロック取得まで待機、
        ``"reject"`` なら即座に :class:`AgentBusyError` を送出する。
    """

    def __init__(
        self,
        system_prompt: str | None = None,
        tools: Iterable[Any] | None = None,
        model: Any | None = None,
        overflow_policy: OverflowPolicy = "queue",
        **agent_kwargs: Any,
    ) -> None:
        if overflow_policy not in ("queue", "reject"):
            raise ValueError(
                f"overflow_policy は 'queue' または 'reject' を指定してください: {overflow_policy!r}"
            )
        self._overflow_policy: OverflowPolicy = overflow_policy
        self._lock = asyncio.Lock()

        kwargs: dict[str, Any] = dict(agent_kwargs)
        if system_prompt is not None:
            kwargs.setdefault("system_prompt", system_prompt)
        if tools:
            kwargs.setdefault("tools", list(tools))
        if model is not None:
            kwargs.setdefault("model", model)
        self._agent = Agent(**kwargs)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def is_busy(self) -> bool:
        """現在リクエスト処理中なら True。"""
        return self._lock.locked()

    async def ainvoke(self, prompt: str) -> Any:
        """1件のプロンプトを直列に実行する。"""
        if self._overflow_policy == "reject" and self._lock.locked():
            raise AgentBusyError(
                "SerialAgent は別リクエストの処理中です。完了後に再試行してください。"
            )
        async with self._lock:
            return await self._agent.invoke_async(prompt)

    def invoke(self, prompt: str) -> Any:
        """同期的に1件のプロンプトを実行する簡易ヘルパ。"""
        return asyncio.run(self.ainvoke(prompt))


# ---------------------------------------------------------------------------
# デモ用ヘルパー
# ---------------------------------------------------------------------------

PROMPTS = [
    "日本の首都はどこですか？短く答えて。",
    "フランスの首都はどこですか？短く答えて。",
    "ドイツの首都はどこですか？短く答えて。",
]


async def run_demo_queue() -> None:
    """queue モード: 後続リクエストはロック解放まで待機する。"""
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


async def run_demo_reject() -> None:
    """reject モード: 処理中の同時投入は即エラーになる。"""
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


async def run_demo() -> None:
    await run_demo_queue()
    await run_demo_reject()


if __name__ == "__main__":
    asyncio.run(run_demo())
