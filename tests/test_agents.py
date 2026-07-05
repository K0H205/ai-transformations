"""ParallelAgent / SerialAgent の並行挙動をモックで検証する。

Strands SDK の実モデルを呼ばずに、``Agent.invoke_async`` を差し替えて
並列性・直列性だけを確認する。
"""

from __future__ import annotations

import asyncio
import sys
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _install_strands_stub() -> None:
    """Strands SDK が未インストールでもテストを回すためのスタブ。"""
    if "strands" in sys.modules:
        return

    class _StubAgent:
        def __init__(self, *args, **kwargs):
            self._kwargs = kwargs

        async def invoke_async(self, prompt: str):  # pragma: no cover - 上書きされる
            return f"stub:{prompt}"

    module = types.ModuleType("strands")
    module.Agent = _StubAgent
    sys.modules["strands"] = module


_install_strands_stub()

from agents import AgentBusyError, ParallelAgent, SerialAgent  # noqa: E402
from strands import Agent as StubAgent  # noqa: E402


class ParallelAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_runs_concurrently(self) -> None:
        delay = 0.1

        async def fake_invoke(self, prompt: str) -> str:
            await asyncio.sleep(delay)
            return f"ok:{prompt}"

        with patch.object(StubAgent, "invoke_async", fake_invoke, create=True):
            agent = ParallelAgent()
            started = time.perf_counter()
            results = await agent.ainvoke_many(["a", "b", "c", "d"])
            elapsed = time.perf_counter() - started

        self.assertEqual(results, ["ok:a", "ok:b", "ok:c", "ok:d"])
        # 直列なら 4 * delay = 0.4s 以上かかるはず。並列なら概ね delay 程度。
        self.assertLess(elapsed, delay * 2)

    async def test_respects_max_concurrency(self) -> None:
        in_flight = 0
        peak = 0
        lock = asyncio.Lock()

        async def fake_invoke(self, prompt: str) -> str:
            nonlocal in_flight, peak
            async with lock:
                in_flight += 1
                peak = max(peak, in_flight)
            await asyncio.sleep(0.05)
            async with lock:
                in_flight -= 1
            return prompt

        with patch.object(StubAgent, "invoke_async", fake_invoke, create=True):
            agent = ParallelAgent(max_concurrency=2)
            await agent.ainvoke_many(["1", "2", "3", "4", "5"])

        self.assertLessEqual(peak, 2)


class SerialAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_queue_mode_serializes_requests(self) -> None:
        in_flight = 0
        peak = 0

        async def fake_invoke(self, prompt: str) -> str:
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            await asyncio.sleep(0.05)
            in_flight -= 1
            return prompt

        with patch.object(StubAgent, "invoke_async", fake_invoke, create=True):
            agent = SerialAgent(overflow_policy="queue")
            results = await asyncio.gather(*(agent.ainvoke(p) for p in "abcd"))

        self.assertEqual(results, list("abcd"))
        self.assertEqual(peak, 1)

    async def test_reject_mode_raises_when_busy(self) -> None:
        started = asyncio.Event()

        async def fake_invoke(self, prompt: str) -> str:
            started.set()
            await asyncio.sleep(0.05)
            return prompt

        with patch.object(StubAgent, "invoke_async", fake_invoke, create=True):
            agent = SerialAgent(overflow_policy="reject")
            first = asyncio.create_task(agent.ainvoke("first"))
            await started.wait()
            with self.assertRaises(AgentBusyError):
                await agent.ainvoke("second")
            self.assertEqual(await first, "first")


if __name__ == "__main__":
    unittest.main()
