"""SerialAgent の直列挙動をモックで検証する。

Strands SDK の実モデルを呼ばずに、``Agent.invoke_async`` を差し替えて
直列性だけを確認する。
"""

from __future__ import annotations

import asyncio
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


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

from agent import AgentBusyError, SerialAgent  # noqa: E402
from strands import Agent as StubAgent  # noqa: E402


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
