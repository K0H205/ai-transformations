"""report.py のテスト。"""

from __future__ import annotations

from pathlib import Path

from extractor import discover_sessions
from report import build_report
from signals import compute_signals


def test_build_report_no_llm_mode(copilot_home: Path) -> None:
    sessions = discover_sessions(copilot_home)
    aggregate = compute_signals(sessions)

    text = build_report(
        aggregate,
        copilot_home=str(copilot_home),
        days=None,
        repo=None,
        proposals=None,
    )

    assert "# Copilot CLI セッション履歴分析レポート" in text
    assert "分析セッション数: 2" in text
    assert "総ツール失敗数 | 2" in text
    assert "総再試行数 | 2" in text
    assert "bash | 2" in text
    assert "--no-llm" in text  # LLMスキップの説明が含まれる
    assert "パース不能なイベント行が 1 件" in text


def test_build_report_with_days_and_repo_filters(copilot_home: Path) -> None:
    sessions = discover_sessions(copilot_home, repo="myservice-repo")
    aggregate = compute_signals(sessions)

    text = build_report(
        aggregate,
        copilot_home=str(copilot_home),
        days=14,
        repo="myservice-repo",
        proposals=None,
    )

    assert "直近14日" in text
    assert "myservice-repo" in text


def test_build_report_embeds_llm_markdown(copilot_home: Path) -> None:
    sessions = discover_sessions(copilot_home)
    aggregate = compute_signals(sessions)

    llm_markdown = "### 提案1: AGENTS.mdにテストコマンドを明記 [対象: agents_md / 信頼度: high]\n\n本文"
    text = build_report(
        aggregate,
        copilot_home=str(copilot_home),
        days=None,
        repo=None,
        proposals=llm_markdown,
    )

    assert "## ハーネス改善提案" in text
    assert llm_markdown in text
    assert "--no-llm" not in text  # LLM経路なのでスキップ説明は出ない


def test_build_report_empty_aggregate() -> None:
    from signals import AggregateSignals

    aggregate = AggregateSignals()
    text = build_report(aggregate, copilot_home="/tmp/nowhere", days=None, repo=None, proposals=None)

    assert "分析セッション数: 0" in text
    assert "全期間" in text
    assert "(指定なし)" in text
