"""
テスト用の合成fixture
======================================================

実際の Copilot CLI 環境が無くてもテストできるよう、``~/.copilot`` 相当の
ディレクトリツリー(session-store.db + session-state/*/events.jsonl)を
一時ディレクトリに合成する。
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _write_events(path: Path, events: list[dict], extra_lines: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")
        for line in extra_lines or []:
            f.write(line + "\n")


def _tool_start(call_id: str, tool_name: str, ts: str) -> dict:
    return {
        "id": f"evt-{call_id}-start",
        "timestamp": ts,
        "type": "tool.execution_start",
        "data": {"toolCallId": call_id, "toolName": tool_name},
    }


def _tool_complete(call_id: str, tool_name: str, ts: str, success: bool, error_message: str | None = None) -> dict:
    data: dict = {"toolCallId": call_id, "toolName": tool_name, "success": success}
    if not success:
        data["error"] = {"message": error_message or "unknown error"}
    return {
        "id": f"evt-{call_id}-complete",
        "timestamp": ts,
        "type": "tool.execution_complete",
        "data": data,
    }


def _user_message(msg_id: str, ts: str, content: str) -> dict:
    return {
        "id": msg_id,
        "timestamp": ts,
        "type": "user.message",
        "data": {"content": content},
    }


def _permission_completed(evt_id: str, ts: str, kind: str) -> dict:
    return {
        "id": evt_id,
        "timestamp": ts,
        "type": "permission.completed",
        "data": {"result": {"kind": kind}},
    }


def _assistant_usage(evt_id: str, ts: str, input_tokens: int, output_tokens: int, cost: float) -> dict:
    return {
        "id": evt_id,
        "timestamp": ts,
        "type": "assistant.usage",
        "ephemeral": True,
        "data": {"inputTokens": input_tokens, "outputTokens": output_tokens, "cost": cost},
    }


@pytest.fixture
def copilot_home(tmp_path: Path) -> Path:
    """session-store.db + 2セッション分の events.jsonl を持つ偽 ~/.copilot を構築する。"""
    home = tmp_path / "copilot-home"
    home.mkdir()

    # --- session-store.db ---
    db_path = home / "session-store.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE sessions (id TEXT PRIMARY KEY, repo TEXT, summary TEXT, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO sessions (id, repo, summary, created_at) VALUES (?, ?, ?, ?)",
        ("session-a", "myservice-repo", "gradle test failures", "2026-07-01T00:00:00Z"),
    )
    conn.execute(
        "INSERT INTO sessions (id, repo, summary, created_at) VALUES (?, ?, ?, ?)",
        ("session-b", "myservice-repo", "clean run", "2026-07-02T00:00:00Z"),
    )
    conn.commit()
    conn.close()

    # --- session-a: gradle失敗が2回続いた後、正しいコマンドで成功。follow-upとpermission denyあり ---
    session_a_events = [
        _user_message("m1", "2026-07-01T00:00:00Z", "run the tests"),
        _tool_start("c1", "bash", "2026-07-01T00:00:01Z"),
        _tool_complete("c1", "bash", "2026-07-01T00:00:02Z", success=False, error_message="gradle: command not found"),
        _tool_start("c2", "bash", "2026-07-01T00:00:03Z"),
        _tool_complete("c2", "bash", "2026-07-01T00:00:04Z", success=False, error_message="gradle: command not found"),
        _user_message("m2", "2026-07-01T00:00:05Z", "use ./gradlew instead"),
        _tool_start("c3", "bash", "2026-07-01T00:00:06Z"),
        _tool_complete("c3", "bash", "2026-07-01T00:00:07Z", success=True),
        _permission_completed("p1", "2026-07-01T00:00:08Z", "denied-interactively-by-user"),
        _assistant_usage("u1", "2026-07-01T00:00:09Z", 1000, 500, 0.01),
    ]
    _write_events(
        home / "session-state" / "session-a" / "events.jsonl",
        session_a_events,
        extra_lines=["{not valid json", ""],
    )

    # --- session-b: 全て成功、圧縮イベントあり ---
    session_b_events = [
        _user_message("m3", "2026-07-02T00:00:00Z", "add a helper function"),
        _tool_start("c4", "edit", "2026-07-02T00:00:01Z"),
        _tool_complete("c4", "edit", "2026-07-02T00:00:02Z", success=True),
        {
            "id": "comp1",
            "timestamp": "2026-07-02T00:00:03Z",
            "type": "session.compaction_start",
            "data": {},
        },
        {
            "id": "comp2",
            "timestamp": "2026-07-02T00:00:04Z",
            "type": "session.compaction_complete",
            "data": {},
        },
        _assistant_usage("u2", "2026-07-02T00:00:05Z", 2000, 800, 0.02),
    ]
    _write_events(home / "session-state" / "session-b" / "events.jsonl", session_b_events)

    return home
