"""
Copilot CLI セッション履歴分析ハーネス改善支援ツール
======================================================

GitHub Copilot CLI が ``~/.copilot`` 配下に残すセッション履歴
(``session-store.db`` / ``session-state/*/events.jsonl``)を読み取り、
繰り返し発生する失敗・軌道修正などの「摩擦シグナル」を決定論的に集計する。
オプションで Anthropic API を用いてAGENTS.md追記案などのハーネス改善提案を
生成し、Markdownレポートとして出力する。

セットアップ:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY="your-api-key"   # --no-llm を使わない場合のみ必須

実行例:
    # 決定論集計のみ(APIキー不要)
    python analyzer.py --copilot-home ~/.copilot --no-llm

    # LLM提案つき、直近14日、特定リポジトリに絞り込み
    python analyzer.py --copilot-home ~/.copilot --days 14 --repo myservice-repo

    # ファイルに出力
    python analyzer.py --no-llm --output report.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from extractor import discover_sessions
from report import build_report
from signals import compute_signals


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copilot CLI セッション履歴からハーネス改善提案を生成する"
    )
    parser.add_argument(
        "--copilot-home",
        type=str,
        default=str(Path.home() / ".copilot"),
        help="Copilot CLIのホームディレクトリ(既定: ~/.copilot、COPILOT_HOME相当)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="直近N日以内のセッションのみを対象にする(既定: 全期間)",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="特定のリポジトリ名でセッションを絞り込む",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="LLMを呼び出さず、決定論集計のみのレポートを出力する(APIキー不要)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM提案生成に使うモデルID(既定: claude-sonnet-4-6)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="レポートの出力先ファイルパス(既定: 標準出力)",
    )

    args = parser.parse_args(argv)

    copilot_home = Path(args.copilot_home).expanduser()
    if not copilot_home.exists():
        print(f"エラー: 指定されたディレクトリが存在しません: {copilot_home}", file=sys.stderr)
        return 1

    sessions = discover_sessions(copilot_home, days=args.days, repo=args.repo)
    if not sessions:
        print(
            f"警告: {copilot_home} 配下に分析対象のセッションが見つかりませんでした。",
            file=sys.stderr,
        )

    aggregate = compute_signals(sessions)

    proposals = None
    if not args.no_llm:
        from llm import DEFAULT_MODEL, generate_proposals

        model = args.model or DEFAULT_MODEL
        try:
            proposals = generate_proposals(
                aggregate, model=model, home_dir=str(Path.home())
            )
        except Exception as exc:  # noqa: BLE001 - CLIとしてエラー内容をそのまま提示する
            print(f"エラー: LLM呼び出しに失敗しました: {exc}", file=sys.stderr)
            print("ヒント: --no-llm で決定論集計のみのレポートを出力できます。", file=sys.stderr)
            return 1

    report_text = build_report(
        aggregate,
        copilot_home=str(copilot_home),
        days=args.days,
        repo=args.repo,
        proposals=proposals,
    )

    if args.output:
        Path(args.output).write_text(report_text, encoding="utf-8")
        print(f"レポートを書き出しました: {args.output}", file=sys.stderr)
    else:
        print(report_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
