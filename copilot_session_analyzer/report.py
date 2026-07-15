"""
出力層
======================================================

決定論集計(signals.AggregateSignals)とLLM提案(llm.ProposalReport, 任意)から
Markdownレポートを組み立てる。
"""

from __future__ import annotations

from signals import AggregateSignals

try:
    from llm import ProposalReport
except ImportError:  # anthropic未インストール環境でもレポート生成自体は動かす
    ProposalReport = None  # type: ignore[assignment,misc]


def build_report(
    aggregate: AggregateSignals,
    copilot_home: str,
    days: int | None,
    repo: str | None,
    proposals: "ProposalReport | None" = None,
) -> str:
    """Markdownレポートのテキストを組み立てる。"""
    lines: list[str] = []

    lines.append("# Copilot CLI セッション履歴分析レポート")
    lines.append("")
    lines.append("## 対象範囲")
    lines.append(f"- 分析対象ディレクトリ: `{copilot_home}`")
    lines.append(f"- 期間: {'直近' + str(days) + '日' if days is not None else '全期間'}")
    lines.append(f"- リポジトリフィルタ: {repo if repo else '(指定なし)'}")
    lines.append(f"- 分析セッション数: {aggregate.session_count}")
    if aggregate.total_malformed_events:
        lines.append(
            f"- 警告: パース不能なイベント行が {aggregate.total_malformed_events} 件ありました"
            "(スキーマ変更・破損データの可能性)"
        )
    lines.append("")

    lines.append("## 決定論集計(摩擦シグナル)")
    lines.append("")
    lines.append("| 指標 | 値 |")
    lines.append("|---|---|")
    lines.append(f"| 総ツール呼び出し数 | {aggregate.total_tool_calls} |")
    lines.append(f"| 総ツール失敗数 | {aggregate.total_tool_failures} |")
    lines.append(f"| 総再試行数 | {aggregate.total_retries} |")
    lines.append(f"| 総権限拒否数 | {aggregate.total_permission_denials} |")
    lines.append(f"| 総軌道修正(follow-up)数 | {aggregate.total_follow_ups} |")
    lines.append(f"| 総コンテキスト圧縮回数 | {aggregate.total_compactions} |")
    lines.append(f"| 総入力トークン数 | {aggregate.total_input_tokens} |")
    lines.append(f"| 総出力トークン数 | {aggregate.total_output_tokens} |")
    lines.append(f"| 総コスト(USD概算) | {aggregate.total_cost:.4f} |")
    lines.append("")

    if aggregate.tool_failures_by_name:
        lines.append("### ツール別失敗回数(上位10件)")
        lines.append("")
        lines.append("| ツール | 失敗回数 |")
        lines.append("|---|---|")
        for tool_name, count in aggregate.tool_failures_by_name.most_common(10):
            lines.append(f"| {tool_name} | {count} |")
        lines.append("")

    if proposals is not None:
        lines.append("## ハーネス改善提案")
        lines.append("")
        if not proposals.proposals:
            lines.append("(LLMからの提案はありませんでした)")
        for i, p in enumerate(proposals.proposals, start=1):
            lines.append(f"### 提案{i}: {p.title} [対象: {p.target} / 信頼度: {p.confidence}]")
            lines.append("")
            lines.append(f"**検出**: {p.rationale}")
            lines.append("")
            lines.append(f"**根拠セッション**: {', '.join(p.evidence_session_ids) or '(なし)'}")
            lines.append("")
            lines.append("**追記案**:")
            lines.append("")
            lines.append("```")
            lines.append(p.suggested_text)
            lines.append("```")
            lines.append("")
    else:
        lines.append("## ハーネス改善提案")
        lines.append("")
        lines.append(
            "(`--no-llm` モードのため、LLMによる改善提案はスキップされました。"
            "上記の決定論集計から手動でパターンを確認してください。)"
        )
        lines.append("")

    return "\n".join(lines)
