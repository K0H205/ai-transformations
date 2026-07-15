"""
決定論集計層(LLM非依存)
======================================================

events.jsonl から「摩擦シグナル」を機械的に集計する。ここで算出する数値は
LLMを一切使わずに得られるため、``--no-llm`` モードでもそのまま提示できる。

対象イベント型(Copilot CLI実測を含む):
- ``tool.execution_start`` / ``tool.execution_complete``: ツール呼び出しと成否
- ``permission.requested`` / ``permission.completed``: 権限確認と結果
- ``user.message``: ユーザー発話(軌道修正の検出に使用)
- ``session.compaction_start`` / ``session.compaction_complete``: コンテキスト圧縮
- ``assistant.usage``: トークン使用量・コスト
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from extractor import SessionInfo

_DENIED_PERMISSION_KINDS = {
    "denied-by-rules",
    "denied-interactively-by-user",
    "denied",
}


@dataclass
class ToolFailure:
    """ツール失敗1件分の記録。"""

    session_id: str
    tool_name: str
    error_message: str


@dataclass
class SessionSignals:
    """1セッション分の摩擦シグナル集計。"""

    session_id: str
    repo: str | None
    tool_call_count: int = 0
    tool_failure_count: int = 0
    tool_failures_by_name: Counter = field(default_factory=Counter)
    retry_count: int = 0
    permission_denied_count: int = 0
    follow_up_count: int = 0
    compaction_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    malformed_event_count: int = 0


@dataclass
class AggregateSignals:
    """複数セッションを横断した集計結果。"""

    session_count: int = 0
    total_tool_calls: int = 0
    total_tool_failures: int = 0
    tool_failures_by_name: Counter = field(default_factory=Counter)
    total_retries: int = 0
    total_permission_denials: int = 0
    total_follow_ups: int = 0
    total_compactions: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    total_malformed_events: int = 0
    sample_failures: list[ToolFailure] = field(default_factory=list)
    sessions: list[SessionSignals] = field(default_factory=list)


def compute_signals(sessions: list[SessionInfo], max_sample_failures: int = 20) -> AggregateSignals:
    """複数セッションのイベント列から摩擦シグナルを算出する。"""
    aggregate = AggregateSignals()

    for session in sessions:
        sig = _compute_session_signals(session)
        aggregate.sessions.append(sig)
        aggregate.session_count += 1
        aggregate.total_tool_calls += sig.tool_call_count
        aggregate.total_tool_failures += sig.tool_failure_count
        aggregate.tool_failures_by_name.update(sig.tool_failures_by_name)
        aggregate.total_retries += sig.retry_count
        aggregate.total_permission_denials += sig.permission_denied_count
        aggregate.total_follow_ups += sig.follow_up_count
        aggregate.total_compactions += sig.compaction_count
        aggregate.total_input_tokens += sig.input_tokens
        aggregate.total_output_tokens += sig.output_tokens
        aggregate.total_cost += sig.cost
        aggregate.total_malformed_events += sig.malformed_event_count

    for session in sessions:
        for failure in _collect_failures(session):
            if len(aggregate.sample_failures) >= max_sample_failures:
                break
            aggregate.sample_failures.append(failure)

    return aggregate


def _compute_session_signals(session: SessionInfo) -> SessionSignals:
    sig = SessionSignals(
        session_id=session.session_id,
        repo=session.repo,
        malformed_event_count=session.malformed_event_count,
    )

    # toolCallId -> toolName (tool.execution_start で登録)
    tool_names_by_call_id: dict[str, str] = {}
    # 直近に失敗した toolName の連続回数(同名ツールの再試行検出用)
    last_failed_tool: str | None = None

    for event in session.events:
        event_type = event.get("type")
        data = event.get("data")
        if not isinstance(data, dict):
            data = {}

        if event_type == "tool.execution_start":
            sig.tool_call_count += 1
            call_id = data.get("toolCallId")
            tool_name = data.get("toolName", "unknown")
            if call_id is not None:
                tool_names_by_call_id[call_id] = tool_name

            if last_failed_tool is not None and tool_name == last_failed_tool:
                sig.retry_count += 1

        elif event_type == "tool.execution_complete":
            call_id = data.get("toolCallId")
            tool_name = tool_names_by_call_id.get(call_id, data.get("toolName", "unknown"))
            success = data.get("success", True)

            if success is False:
                sig.tool_failure_count += 1
                sig.tool_failures_by_name[tool_name] += 1
                last_failed_tool = tool_name
            else:
                last_failed_tool = None

        elif event_type == "permission.completed":
            result = data.get("result")
            kind = None
            if isinstance(result, dict):
                kind = result.get("kind")
            elif isinstance(result, str):
                kind = result
            if kind in _DENIED_PERMISSION_KINDS:
                sig.permission_denied_count += 1

        elif event_type == "user.message":
            # 直前のイベントがツール失敗またはassistant応答であれば「軌道修正」とみなす
            sig.follow_up_count += 1

        elif event_type in ("session.compaction_start", "session.compaction_complete"):
            if event_type == "session.compaction_start":
                sig.compaction_count += 1

        elif event_type == "assistant.usage":
            sig.input_tokens += _safe_int(data.get("inputTokens"))
            sig.output_tokens += _safe_int(data.get("outputTokens"))
            cost = data.get("cost")
            if isinstance(cost, (int, float)):
                sig.cost += float(cost)

    # follow_up_count は「最初のuser.message」を除いた方が「軌道修正」の実態に近いが、
    # MVPでは単純化して user.message 総数から1引く(最初の指示分)にとどめる。
    if sig.follow_up_count > 0:
        sig.follow_up_count -= 1

    return sig


def _collect_failures(session: SessionInfo) -> list[ToolFailure]:
    """代表的な失敗メッセージを抽出する(LLM入力用サンプル)。"""
    failures: list[ToolFailure] = []
    tool_names_by_call_id: dict[str, str] = {}

    for event in session.events:
        event_type = event.get("type")
        data = event.get("data")
        if not isinstance(data, dict):
            continue

        if event_type == "tool.execution_start":
            call_id = data.get("toolCallId")
            if call_id is not None:
                tool_names_by_call_id[call_id] = data.get("toolName", "unknown")

        elif event_type == "tool.execution_complete" and data.get("success") is False:
            call_id = data.get("toolCallId")
            tool_name = tool_names_by_call_id.get(call_id, data.get("toolName", "unknown"))
            error = data.get("error")
            message = ""
            if isinstance(error, dict):
                message = str(error.get("message", ""))
            elif isinstance(error, str):
                message = error
            if message:
                failures.append(
                    ToolFailure(
                        session_id=session.session_id,
                        tool_name=tool_name,
                        error_message=message,
                    )
                )

    return failures


def _safe_int(value: object) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    return 0
