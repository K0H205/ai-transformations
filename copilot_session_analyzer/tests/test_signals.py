"""signals.py のテスト。"""

from __future__ import annotations

from pathlib import Path

from extractor import discover_sessions
from signals import compute_signals


def test_compute_signals_aggregates_across_sessions(copilot_home: Path) -> None:
    sessions = discover_sessions(copilot_home)
    aggregate = compute_signals(sessions)

    assert aggregate.session_count == 2
    assert aggregate.total_tool_calls == 4  # session-a:3 + session-b:1
    assert aggregate.total_tool_failures == 2
    assert aggregate.tool_failures_by_name["bash"] == 2
    assert aggregate.total_retries == 2
    assert aggregate.total_permission_denials == 1
    assert aggregate.total_follow_ups == 1
    assert aggregate.total_compactions == 1
    assert aggregate.total_input_tokens == 3000
    assert aggregate.total_output_tokens == 1300
    assert abs(aggregate.total_cost - 0.03) < 1e-9
    assert aggregate.total_malformed_events == 1


def test_compute_signals_collects_sample_failures(copilot_home: Path) -> None:
    sessions = discover_sessions(copilot_home)
    aggregate = compute_signals(sessions)

    assert len(aggregate.sample_failures) == 2
    for failure in aggregate.sample_failures:
        assert failure.tool_name == "bash"
        assert "gradle" in failure.error_message
        assert failure.session_id == "session-a"


def test_compute_signals_respects_max_sample_failures(copilot_home: Path) -> None:
    sessions = discover_sessions(copilot_home)
    aggregate = compute_signals(sessions, max_sample_failures=1)
    assert len(aggregate.sample_failures) == 1


def test_compute_signals_empty_sessions() -> None:
    aggregate = compute_signals([])
    assert aggregate.session_count == 0
    assert aggregate.total_tool_calls == 0
    assert aggregate.sample_failures == []
