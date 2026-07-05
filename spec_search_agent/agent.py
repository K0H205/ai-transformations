"""
仕様調査エージェント（Agentic Search / 自作ツール版）
======================================================

AWS Strands Agents フレームワークを使い、実際のソースコードを対象に
「一覧を見る → キーワードで検索する → 該当箇所を読む」というツール呼び出しを
必要なだけ繰り返しながら（Agentic Search）、仕様を調べ上げて回答するエージェントです。

セットアップ:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY="your-api-key"

実行:
    python agent.py                          # デモモード（strands_sample を調査）
    python agent.py interactive [対象ディレクトリ]   # 対話モード（省略時はカレントディレクトリ）
"""

import os
import sys
from pathlib import Path

from strands import Agent
from strands.models.anthropic import AnthropicModel

from repo_map import build_repo_map
from tools import list_files, read_file, search_code

SYSTEM_PROMPT = (
    "あなたはソースコードの実装を調査し、そこから仕様を読み解く「仕様調査アシスタント」です。\n"
    "\n"
    "調査の進め方（Agentic Search）:\n"
    "1. まず末尾の「調査対象リポジトリの地図」で関連しそうなファイル・関数の当たりを付ける。\n"
    "2. list_files でディレクトリ構成を把握し、search_code でキーワード・関数名・クラス名を検索して該当箇所を特定する。\n"
    "3. read_file で該当箇所とその前後の文脈を実際に読む。\n"
    "4. 根拠が不十分だと感じたら、1〜3を繰り返してさらに深掘りする。1回の検索で終わらせないこと。\n"
    "\n"
    "回答のルール:\n"
    "- 地図はファイル構成とシグネチャのみで実装の中身は含まない。必ず search_code / read_file で実際のコードを確認してから回答すること。\n"
    "- 推測ではなく、実際に読んだコードから読み取れる事実のみを根拠にすること。\n"
    "- 回答には根拠となったファイルパスと行番号（file:line）を必ず明記すること。\n"
    "- 回答は次の形式でまとめること: 「概要 / 入力 / 出力・挙動 / 制約・エラー処理 / 根拠（file:line）」\n"
    "- 調査しても十分な情報が見つからない場合は、正直にその旨を述べること。"
)


def create_agent(base_dir: str) -> Agent:
    """base_dir を調査対象としてエージェントを作成する。

    起動時に base_dir のリポジトリ地図（ファイルツリー + Python シグネチャ）を
    生成し、システムプロンプトに注入する（DevinSearch の Wiki に相当する初動支援）。
    """
    os.environ["SPEC_SEARCH_BASE_DIR"] = base_dir

    model = AnthropicModel(
        client_args={"api_key": os.environ.get("ANTHROPIC_API_KEY")},
        model_id="claude-sonnet-4-6",
        max_tokens=4096,
    )
    return Agent(
        model=model,
        tools=[list_files, search_code, read_file],
        system_prompt=(
            SYSTEM_PROMPT
            + "\n\n## 調査対象リポジトリの地図\n\n"
            + build_repo_map(base_dir)
        ),
    )


def run_demo() -> None:
    """strands_sample を調査対象にして、代表的な仕様調査の質問を試す。"""
    demo_queries = [
        "calculate ツールの仕様（入力・出力・使える関数・エラー処理）を教えてください。",
        "get_weather ツールが対応している都市一覧と、未対応の都市を渡された場合の挙動を教えてください。",
    ]

    agent = create_agent(str(Path(__file__).resolve().parent.parent / "strands_sample"))

    print("=" * 60)
    print("仕様調査エージェント デモ（対象: strands_sample）")
    print("=" * 60)

    for i, query in enumerate(demo_queries, start=1):
        print(f"\n[質問 {i}] {query}")
        print("-" * 40)
        response = agent(query)
        print(response)
        print()


def run_interactive(target_dir: str) -> None:
    """指定ディレクトリを対象に、対話的に仕様を質問できる REPL。"""
    agent = create_agent(target_dir)

    print("=" * 60)
    print(f"仕様調査エージェント インタラクティブモード（対象: {os.path.abspath(target_dir)}）")
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

        print("\n調査結果: ", end="", flush=True)
        response = agent(user_input)
        print(response)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        run_interactive(sys.argv[2] if len(sys.argv) > 2 else ".")
    else:
        run_demo()
