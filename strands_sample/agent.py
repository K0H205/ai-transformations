"""
Strands Agents サンプル AI エージェント
======================================

AWS Strands Agents フレームワークを使ったシンプルなエージェントの例です。

セットアップ:
    pip install -r requirements.txt

    # Anthropic API キーを環境変数にセット
    export ANTHROPIC_API_KEY="your-api-key"

実行:
    python agent.py

Strands Agents について:
    https://github.com/strands-agents/sdk-python
"""

import os
from strands import Agent
from strands.models.anthropic import AnthropicModel

from tools import calculate, get_current_datetime, get_weather, summarize_text

# ---------------------------------------------------------------------------
# モデル設定
# ---------------------------------------------------------------------------
# AnthropicModel を使う場合は ANTHROPIC_API_KEY 環境変数が必要です。
# AWS Bedrock を使う場合は BedrockModel に切り替えてください:
#   from strands.models import BedrockModel
#   model = BedrockModel(model_id="anthropic.claude-3-5-sonnet-20241022-v2:0")
# ---------------------------------------------------------------------------

model = AnthropicModel(
    client_args={"api_key": os.environ.get("ANTHROPIC_API_KEY")},
    model_id="claude-sonnet-4-6",
    max_tokens=4096,
)

# ---------------------------------------------------------------------------
# エージェント作成
# ---------------------------------------------------------------------------
agent = Agent(
    model=model,
    tools=[get_current_datetime, calculate, get_weather, summarize_text],
    system_prompt=(
        "あなたは日本語で会話する親切なアシスタントです。\n"
        "利用可能なツールを活用して、ユーザーの質問に正確かつ丁寧に答えてください。\n"
        "計算が必要な場合は必ず calculate ツールを使い、現在時刻が必要な場合は "
        "get_current_datetime ツールを使ってください。"
    ),
)


# ---------------------------------------------------------------------------
# デモ用ヘルパー
# ---------------------------------------------------------------------------

def run_demo() -> None:
    """いくつかの代表的な質問でエージェントの動作を確認します。"""
    demo_queries = [
        "今何時ですか？",
        "東京と大阪の天気を教えてください。",
        "123 × 456 を計算してください。また √2 の値も教えてください。",
        (
            "次の文章を2文で要約してください：\n"
            "Strands Agents は AWS が開発したオープンソースの AI エージェントフレームワークです。"
            "Python で書かれており、カスタムツールを @tool デコレータで簡単に定義できます。"
            "Amazon Bedrock や Anthropic など複数のモデルバックエンドに対応しています。"
            "ストリーミングレスポンス、マルチエージェント構成、メモリ管理などの機能を備えています。"
        ),
    ]

    print("=" * 60)
    print("Strands Agents サンプルデモ")
    print("=" * 60)

    for i, query in enumerate(demo_queries, start=1):
        print(f"\n[質問 {i}] {query[:60]}{'...' if len(query) > 60 else ''}")
        print("-" * 40)
        response = agent(query)
        print(response)
        print()


# ---------------------------------------------------------------------------
# インタラクティブ REPL
# ---------------------------------------------------------------------------

def run_interactive() -> None:
    """ユーザーと対話しながらエージェントを使います。Ctrl+C または 'quit' で終了。"""
    print("=" * 60)
    print("Strands Agents インタラクティブモード")
    print("終了するには 'quit' または Ctrl+C を入力してください。")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nあなた: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n終了します。")
            break

        if user_input.lower() in {"quit", "exit", "終了"}:
            print("終了します。")
            break

        if not user_input:
            continue

        print("\nエージェント: ", end="", flush=True)
        response = agent(user_input)
        print(response)


# ---------------------------------------------------------------------------
# エントリーポイント
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "demo"

    if mode == "interactive":
        run_interactive()
    else:
        run_demo()
