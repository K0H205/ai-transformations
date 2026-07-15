"""extractor.py のテスト。"""

from __future__ import annotations

from pathlib import Path

from extractor import discover_sessions


def test_discover_sessions_reads_db_and_events(copilot_home: Path) -> None:
    sessions = discover_sessions(copilot_home)
    assert len(sessions) == 2

    by_id = {s.session_id: s for s in sessions}
    assert set(by_id.keys()) == {"session-a", "session-b"}

    session_a = by_id["session-a"]
    assert session_a.repo == "myservice-repo"
    assert session_a.malformed_event_count == 1  # "{not valid json" の1行
    assert len(session_a.events) == 10  # 空行と壊れた行は events に含まれない

    session_b = by_id["session-b"]
    assert session_b.repo == "myservice-repo"
    assert session_b.malformed_event_count == 0
    assert len(session_b.events) == 6


def test_discover_sessions_filters_by_repo(copilot_home: Path) -> None:
    sessions = discover_sessions(copilot_home, repo="other-repo")
    assert sessions == []

    sessions = discover_sessions(copilot_home, repo="myservice-repo")
    assert len(sessions) == 2


def test_discover_sessions_fallback_without_db(tmp_path: Path) -> None:
    """session-store.db が無い場合でも session-state/ を直接走査できる。"""
    import json

    home = tmp_path / "copilot-home-no-db"
    session_dir = home / "session-state" / "orphan-session"
    session_dir.mkdir(parents=True)
    events_path = session_dir / "events.jsonl"
    events_path.write_text(
        json.dumps({"id": "e1", "timestamp": "2026-07-01T00:00:00Z", "type": "user.message", "data": {}})
        + "\n"
    )

    sessions = discover_sessions(home)
    assert len(sessions) == 1
    assert sessions[0].session_id == "orphan-session"
    assert sessions[0].repo is None


def test_discover_sessions_missing_home_returns_empty(tmp_path: Path) -> None:
    sessions = discover_sessions(tmp_path / "does-not-exist")
    assert sessions == []
