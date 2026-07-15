"""
LLM層(reduce)
======================================================

決定論集計層(signals.py)の出力とマスク済みの代表的失敗メッセージを入力として、
Anthropic API の structured outputs でハーネス改善提案を生成する。

生の events.jsonl 全文は送信しない。コンテキスト長・コスト・プライバシーの
いずれの観点からも、決定論集計とサンプルメッセージだけを渡す設計とする。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from masking import mask_text
from signals import AggregateSignals

DEFAULT_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = (
    "あなたはGitHub Copilot CLIのセッション履歴から「ハーネス改善提案」を作る"
    "アシスタントです。与えられる決定論的な集計データ(ツール失敗頻度・再試行・"
    "権限拒否・軌道修正回数など)と代表的なエラーメッセージのサンプルだけを根拠に、"
    "AGENTS.md追記案・Agent Skill化候補・カスタムエージェント化候補・MCPサーバー"
    "導入候補などを提案してください。\n"
    "\n"
    "ルール:\n"
    "- 提案は必ず与えられたデータに基づくこと。データにない推測をしないこと。\n"
    "- 根拠となったセッションIDを evidence_session_ids に列挙すること。\n"
    "- 十分な根拠(同じ失敗パターンの反復)がない提案は confidence を low にすること。\n"
    "- 有用な提案が無ければ、無理に proposals を埋めず空リストで返すこと。"
)


class Proposal(BaseModel):
    """1件のハーネス改善提案。"""

    target: Literal["agents_md", "skill", "subagent", "mcp", "instructions"] = Field(
        description="改善提案の適用先"
    )
    title: str = Field(description="提案の短いタイトル")
    rationale: str = Field(description="この提案をした理由(検出したパターンの説明)")
    suggested_text: str = Field(description="AGENTS.md等への追記案・具体的な文案")
    evidence_session_ids: list[str] = Field(description="根拠となったセッションIDの一覧")
    confidence: Literal["high", "medium", "low"] = Field(description="提案の信頼度")


class ProposalReport(BaseModel):
    """LLMが生成する提案レポート全体。"""

    proposals: list[Proposal] = Field(description="ハーネス改善提案の一覧")


def build_llm_input(aggregate: AggregateSignals, home_dir: str | None = None) -> str:
    """決定論集計とサンプル失敗メッセージから、LLMに渡すマスク済みテキストを組み立てる。"""
    lines: list[str] = []
    lines.append(f"対象セッション数: {aggregate.session_count}")
    lines.append(f"総ツール呼び出し数: {aggregate.total_tool_calls}")
    lines.append(f"総ツール失敗数: {aggregate.total_tool_failures}")
    lines.append(f"総再試行数: {aggregate.total_retries}")
    lines.append(f"総権限拒否数: {aggregate.total_permission_denials}")
    lines.append(f"総軌道修正(follow-up)数: {aggregate.total_follow_ups}")
    lines.append(f"総コンテキスト圧縮回数: {aggregate.total_compactions}")
    lines.append("")
    lines.append("## ツール別失敗回数")
    for tool_name, count in aggregate.tool_failures_by_name.most_common(10):
        lines.append(f"- {tool_name}: {count}回")
    lines.append("")
    lines.append("## 代表的な失敗メッセージ(マスク済み)")
    for failure in aggregate.sample_failures:
        masked_message = mask_text(failure.error_message, home_dir=home_dir)
        lines.append(f"- [session={failure.session_id}] {failure.tool_name}: {masked_message}")

    return "\n".join(lines)


def generate_proposals(
    aggregate: AggregateSignals,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    home_dir: str | None = None,
) -> ProposalReport:
    """Anthropic API を呼び出し、構造化された改善提案レポートを取得する。"""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    llm_input = build_llm_input(aggregate, home_dir=home_dir)

    response = client.messages.parse(
        model=model,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": llm_input}],
        output_format=ProposalReport,
    )

    return response.parsed_output
