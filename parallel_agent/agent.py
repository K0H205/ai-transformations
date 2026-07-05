"""並列リクエストを受け付けるAIエージェント。

Strands Agents SDK をラップし、複数リクエストを並行実行する。
共有可変状態（会話履歴など）の競合を避けるため、リクエストごとに
独立した ``Agent`` インスタンスを生成してから ``invoke_async`` を実行する。

セットアップ:
    pip install -r requirements.txt

実行:
    python agent.py
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Iterable, Sequence

from strands import Agent


class ParallelAgent:
    """並列呼び出しを許可するAIエージェント。

    Parameters
    ----------
    system_prompt:
        エージェントに渡すシステムプロンプト。
    tools:
        Strandsに登録するツール関数の列。
    model:
        Strandsに渡すモデル（省略時は SDK のデフォルト）。
    max_concurrency:
        同時に実行可能なリクエスト数。 ``None`` なら無制限。
    agent_kwargs:
        Agent 生成時に追加で渡すキーワード引数。
    """

    def __init__(
        self,
        system_prompt: str | None = None,
        tools: Iterable[Any] | None = None,
        model: Any | None = None,
        max_concurrency: int | None = None,
        **agent_kwargs: Any,
    ) -> None:
        self._system_prompt = system_prompt
        self._tools = list(tools) if tools else []
        self._model = model
        self._agent_kwargs = agent_kwargs
        self._semaphore: asyncio.Semaphore | None = (
            asyncio.Semaphore(max_concurrency) if max_concurrency else None
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_agent(self) -> Agent:
        """リクエスト毎に独立したAgentを生成する。

        会話履歴や中間状態を他リクエストと共有しないことで
        安全に並列実行できるようにする。
        """
        kwargs: dict[str, Any] = dict(self._agent_kwargs)
        if self._system_prompt is not None:
            kwargs.setdefault("system_prompt", self._system_prompt)
        if self._tools:
            kwargs.setdefault("tools", list(self._tools))
        if self._model is not None:
            kwargs.setdefault("model", self._model)
        return Agent(**kwargs)

    async def _invoke_one(self, prompt: str) -> Any:
        agent = self._build_agent()
        if self._semaphore is None:
            return await agent.invoke_async(prompt)
        async with self._semaphore:
            return await agent.invoke_async(prompt)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def ainvoke(self, prompt: str) -> Any:
        """単一プロンプトを非同期に実行する。"""
        return await self._invoke_one(prompt)

    async def ainvoke_many(self, prompts: Sequence[str]) -> list[Any]:
        """複数プロンプトを並列実行し、入力順に結果を返す。"""
        tasks = [asyncio.create_task(self._invoke_one(p)) for p in prompts]
        return await asyncio.gather(*tasks)

    def invoke(self, prompt: str) -> Any:
        """同期的に単一プロンプトを実行する簡易ヘルパ。"""
        return asyncio.run(self.ainvoke(prompt))

    def invoke_many(self, prompts: Sequence[str]) -> list[Any]:
        """同期的に複数プロンプトを並列実行する簡易ヘルパ。"""
        return asyncio.run(self.ainvoke_many(prompts))


# ---------------------------------------------------------------------------
# デモ用ヘルパー
# ---------------------------------------------------------------------------

PROMPTS = [
    "日本の首都はどこですか？短く答えて。",
    "フランスの首都はどこですか？短く答えて。",
    "ドイツの首都はどこですか？短く答えて。",
]


async def run_demo() -> None:
    """複数プロンプトを同時実行し、経過時間を確認します。"""
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


if __name__ == "__main__":
    asyncio.run(run_demo())
