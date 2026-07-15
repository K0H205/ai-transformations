"""
LLM層(reduce)
======================================================

決定論集計層(signals.py)の出力とマスク済みの代表的失敗メッセージを入力として、
Anthropic API でハーネス改善提案を自由文Markdownとして生成する。

生成されたMarkdownは report.py がそのままレポートに埋め込む。structured outputs
(型固定)は使わないため、対応モデルの制約が無く任意のモデルを指定できる。

生の events.jsonl 全文は送信しない。コンテキスト長・コスト・プライバシーの
いずれの観点からも、決定論集計とサンプルメッセージだけを渡す設計とする。
"""

from __future__ import annotations

from masking import mask_text
from signals import AggregateSignals

DEFAULT_MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = (
    "あなたはGitHub Copilot CLIのセッション履歴から「ハーネス改善提案」を作る"
    "アシスタントです。与えられる決定論的な集計データ(ツール失敗頻度・再試行・"
    "権限拒否・軌道修正回数など)と代表的なエラーメッセージのサンプルだけを根拠に、"
    "AGENTS.md追記案・Agent Skill化候補・カスタムエージェント化候補・MCPサーバー"
    "導入候補などを提案してください。\n"
    "\n"
    "出力形式(Markdown):\n"
    "- 提案ごとに次の見出しを付けること: "
    "`### 提案N: <タイトル> [対象: <agents_md|skill|subagent|mcp|instructions> / "
    "信頼度: <high|medium|low>]`\n"
    "- 各提案には「検出したパターンの説明」「根拠セッションID」「追記文案(コードブロック)」"
    "を含めること。\n"
    "- レポートに直接埋め込むため、全体を囲む見出し(## など)や前置き・後置きの挨拶は書かないこと。\n"
    "\n"
    "ルール:\n"
    "- 提案は必ず与えられたデータに基づくこと。データにない推測をしないこと。\n"
    "- 十分な根拠(同じ失敗パターンの反復)がない提案は信頼度を low にすること。\n"
    "- 有用な提案が無ければ、その旨を1行で述べること。"
)


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
) -> str:
    """Anthropic API を呼び出し、改善提案の自由文Markdownを取得する。"""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    llm_input = build_llm_input(aggregate, home_dir=home_dir)

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": llm_input}],
    )

    text = "\n".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()

    if not text:
        # 拒否・打ち切り等でテキストが得られなかった場合。空文字のまま返すと
        # report.py が空の提案セクションを出すため、CLIがエラー提示できるよう失敗させる。
        raise RuntimeError(
            f"LLMから提案テキストを取得できませんでした(stop_reason={response.stop_reason})"
        )

    return text
