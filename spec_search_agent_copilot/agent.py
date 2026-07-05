"""
仕様調査エージェント（Agentic Search / GitHub Copilot SDK 委譲版・実験的サンプル）
====================================================================================

【重要: このモジュールは動作未検証です】
探索ツール copilot_search の実体は GitHub Copilot CLI のエージェントであり、
Copilot CLI のインストールと GitHub Copilot サブスクリプション（または BYOK）に
よる認証が必要です。この環境には認証情報がないため、実際の実行確認はできて
いません。前提が整った環境で試すためのサンプルとして提供します。

セットアップ:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY="your-api-key"   # このエージェント自身のモデル用
    # Copilot CLI 側の認証は別途 `copilot` コマンドのドキュメントに従うこと

実行:
    python agent.py [対象ディレクトリ]
"""

import os
import sys

from strands import Agent
from strands.models.anthropic import AnthropicModel

from tools import copilot_search

SYSTEM_PROMPT = (
    "あなたはソースコードの実装を調査し、そこから仕様を読み解く「仕様調査アシスタント」です。\n"
    "\n"
    "調査には copilot_search ツールを使います。copilot_search は1回の呼び出しで\n"
    "コードベースの探索を委譲先のエージェントに任せる仕組みです。1回の結果だけで\n"
    "判断せず、疑問点や不足している情報があれば query を変えて copilot_search を\n"
    "繰り返し呼び出し、十分な根拠が集まるまで調査を続けてください（Agentic Search）。\n"
    "\n"
    "回答のルール:\n"
    "- 推測ではなく、copilot_search から得られた事実のみを根拠にすること。\n"
    "- 回答には根拠となったファイルパスと行番号（file:line）を必ず明記すること。\n"
    "- 回答は次の形式でまとめること: 「概要 / 入力 / 出力・挙動 / 制約・エラー処理 / 根拠（file:line）」\n"
    "- 調査しても十分な情報が見つからない場合は、正直にその旨を述べること。"
)


def create_agent() -> Agent:
    model = AnthropicModel(
        client_args={"api_key": os.environ.get("ANTHROPIC_API_KEY")},
        model_id="claude-sonnet-4-6",
        max_tokens=4096,
    )
    return Agent(
        model=model,
        tools=[copilot_search],
        system_prompt=SYSTEM_PROMPT,
    )


def run_interactive(target_dir: str) -> None:
    agent = create_agent()

    print("=" * 60)
    print("仕様調査エージェント インタラクティブモード（Copilot SDK 委譲版・実験的）")
    print(f"対象: {os.path.abspath(target_dir)}")
    print("終了するには 'quit' または Ctrl+C を入力してください。")
    print("=" * 60)

    while True:
        try:
            user_input = input("\n質問: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n終了します。")
            break

        if user_input.lower() in {"quit", "exit", "終了"}:
            print("終了します。")
            break

        if not user_input:
            continue

        response = agent(f"対象ディレクトリ: {os.path.abspath(target_dir)}\n質問: {user_input}")
        print(response)


if __name__ == "__main__":
    run_interactive(sys.argv[1] if len(sys.argv) > 1 else ".")
