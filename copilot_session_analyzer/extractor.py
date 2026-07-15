"""
抽出層(ローカル・LLM非依存)
======================================================

GitHub Copilot CLI がセッションごとに永続化するデータを読み取る。

- ``~/.copilot/session-store.db``: セッション横断のSQLiteインデックス
  (sessions / turns / checkpoints / session_files / session_refs / search_index)
- ``~/.copilot/session-state/<uuid>/events.jsonl``: セッション内の全イベントログ

両者のスキーマは非公式・未ドキュメント化であり、CLIのバージョンによって
列やイベント型が増減しうる(例: issue #3520 の ``ephemeral`` フィールド欠落)。
そのため、本モジュールは「存在する列/フィールドだけを使う」緩いパースに徹し、
壊れた行やスキーマの揺れをエラーにせず読み飛ばす。
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SessionInfo:
    """1セッション分のメタ情報とイベント列。"""

    session_id: str
    repo: str | None
    events_path: Path | None
    events: list[dict] = field(default_factory=list)
    malformed_event_count: int = 0


def discover_sessions(
    copilot_home: Path,
    days: int | None = None,
    repo: str | None = None,
) -> list[SessionInfo]:
    """copilot_home 配下からセッション一覧を発見し、イベントを読み込む。

    session-store.db が読める場合はそこからセッションID・repo情報を取得し、
    読めない/存在しない場合は session-state/ ディレクトリを直接走査する。
    """
    session_meta = _read_session_store(copilot_home)

    session_state_dir = copilot_home / "session-state"
    sessions: list[SessionInfo] = []

    if session_meta:
        candidate_ids = list(session_meta.keys())
    elif session_state_dir.is_dir():
        candidate_ids = [p.name for p in session_state_dir.iterdir() if p.is_dir()]
    else:
        candidate_ids = []

    cutoff_ts = None
    if days is not None:
        import time

        cutoff_ts = time.time() - days * 86400

    for session_id in candidate_ids:
        meta = session_meta.get(session_id, {})
        session_repo = meta.get("repo")

        if repo is not None and session_repo is not None and session_repo != repo:
            continue

        events_path = session_state_dir / session_id / "events.jsonl"
        events, malformed = _read_events_jsonl(events_path)

        if cutoff_ts is not None and events:
            last_ts = _extract_timestamp(events[-1])
            if last_ts is not None and last_ts < cutoff_ts:
                continue

        sessions.append(
            SessionInfo(
                session_id=session_id,
                repo=session_repo,
                events_path=events_path if events_path.exists() else None,
                events=events,
                malformed_event_count=malformed,
            )
        )

    return sessions


def _read_session_store(copilot_home: Path) -> dict[str, dict]:
    """session-store.db を read-only でコピーして開き、sessions テーブルを読む。

    DBが存在しない・破損している・sessions テーブルが無い場合は空辞書を返す
    (events.jsonl 直接走査へのフォールバックを呼び出し側に委ねる)。
    """
    db_path = copilot_home / "session-store.db"
    if not db_path.exists():
        return {}

    result: dict[str, dict] = {}
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_db = Path(tmp_dir) / "session-store.db"
        try:
            shutil.copy2(db_path, tmp_db)
        except OSError:
            return {}

        try:
            conn = sqlite3.connect(f"file:{tmp_db}?mode=ro", uri=True)
        except sqlite3.OperationalError:
            return {}

        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
            )
            if cur.fetchone() is None:
                return {}

            cur.execute("PRAGMA table_info(sessions)")
            columns = {row[1] for row in cur.fetchall()}

            id_col = "id" if "id" in columns else None
            if id_col is None:
                return {}
            repo_col = "repo" if "repo" in columns else None

            select_cols = [id_col] + ([repo_col] if repo_col else [])
            cur.execute(f"SELECT {', '.join(select_cols)} FROM sessions")
            for row in cur.fetchall():
                sid = row[0]
                repo_val = row[1] if repo_col else None
                result[sid] = {"repo": repo_val}
        except sqlite3.DatabaseError:
            return {}
        finally:
            conn.close()

    return result


def _read_events_jsonl(path: Path) -> tuple[list[dict], int]:
    """events.jsonl を1行ずつ読み、壊れた行はスキップしてカウントする。"""
    events: list[dict] = []
    malformed = 0

    if not path.exists():
        return events, malformed

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if not isinstance(event, dict):
                malformed += 1
                continue
            events.append(event)

    return events, malformed


def _extract_timestamp(event: dict) -> float | None:
    """イベントの ISO8601 timestamp を UNIX epoch 秒に変換する。"""
    ts = event.get("timestamp")
    if not isinstance(ts, str):
        return None
    try:
        from datetime import datetime

        normalized = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return None
