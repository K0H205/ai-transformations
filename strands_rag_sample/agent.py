"""
Strands RAG + Agent サンプル
============================

Strands Agents フレームワーク + RAG（検索拡張生成）を組み合わせた
エージェントのサンプルです。

セットアップ:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY="your-api-key"

実行:
    python agent.py           # デモモード
    python agent.py interactive  # 対話モード

構成:
    rag_store.py   - インメモリ RAG ストア（類似度検索）
    rag_tools.py   - Strands @tool で定義した RAG 検索ツール
    agent.py       - エージェント本体とデモ実行スクリプト
"""

import os

import anthropic
from strands import Agent
from strands.models.anthropic import AnthropicModel

from rag_store import RAGStore
from rag_tools import list_knowledge_base, retrieve_documents, set_store

# ---------------------------------------------------------------------------
# ナレッジベースのサンプルドキュメント
# ---------------------------------------------------------------------------

SAMPLE_DOCUMENTS = [
    {
        "id": "strands-overview",
        "text": (
            "Strands Agents は AWS が開発したオープンソースの Python 製 AI エージェントフレームワークです。"
            "@tool デコレータでカスタムツールを簡単に定義でき、Amazon Bedrock や Anthropic など"
            "複数のモデルバックエンドをサポートします。ストリーミング、マルチエージェント構成、"
            "メモリ管理などの機能を内蔵しています。"
        ),
        "metadata": {"category": "framework", "language": "ja"},
    },
    {
        "id": "rag-concept",
        "text": (
            "RAG（Retrieval-Augmented Generation）は、大規模言語モデルの回答精度を高める手法です。"
            "ユーザーの質問に対して関連ドキュメントをベクトル検索で取得し、そのコンテキストとともに"
            "LLM へ入力することで、ハルシネーションを抑えつつ最新・専門情報に基づく回答を生成します。"
        ),
        "metadata": {"category": "concept", "language": "ja"},
    },
    {
        "id": "anthropic-claude",
        "text": (
            "Anthropic の Claude は高度な言語理解と推論能力を持つ大規模言語モデルです。"
            "Claude Opus 4.8 は Anthropic 最新かつ最高性能のモデルで、アダプティブ思考機能により"
            "複雑な推論タスクに優れています。安全性と有用性を両立した Constitutional AI で訓練されています。"
        ),
        "metadata": {"category": "model", "language": "ja"},
    },
    {
        "id": "vector-search",
        "text": (
            "ベクトル検索（Vector Search）は、テキストや画像を高次元ベクトルに変換し、"
            "コサイン類似度やユークリッド距離で意味的に近いアイテムを高速に検索する技術です。"
            "Pinecone, pgvector, Weaviate, Qdrant などのベクトルデータベースがよく使われます。"
        ),
        "metadata": {"category": "technology", "language": "ja"},
    },
    {
        "id": "agent-tools",
        "text": (
            "AI エージェントはツール（関数）を呼び出すことで外部システムと連携します。"
            "Strands では @tool デコレータを使い、型ヒントと docstring から自動的にツールスキーマを"
            "生成します。エージェントは質問に応じて適切なツールを選択・実行し、結果を踏まえて回答します。"
        ),
        "metadata": {"category": "concept", "language": "ja"},
    },
]

# ---------------------------------------------------------------------------
# 初期化
# ---------------------------------------------------------------------------

anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# RAG ストアを構築してサンプルドキュメントを登録
rag = RAGStore(client=anthropic_client)
rag.add_documents(SAMPLE_DOCUMENTS)
set_store(rag)

# Strands モデル設定
model = AnthropicModel(
    client_args={"api_key": os.environ.get("ANTHROPIC_API_KEY")},
    model_id="claude-opus-4-8",
    max_tokens=4096,
)

# ---------------------------------------------------------------------------
# エージェント作成
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """あなたはナレッジベースを活用する日本語のリサーチアシスタントです。

ユーザーの質問に答える際は、必ず以下の手順を踏んでください:
1. retrieve_documents ツールでナレッジベースを検索する
2. 取得したドキュメントを根拠にして回答する
3. ナレッジベースに情報がない場合はその旨を明示し、一般知識で補足する

回答は日本語で、丁寧かつ簡潔に行ってください。
根拠となったドキュメントの ID を回答の末尾に記載してください。"""

agent = Agent(
    model=model,
    tools=[retrieve_documents, list_knowledge_base],
    system_prompt=SYSTEM_PROMPT,
)

# ---------------------------------------------------------------------------
# デモ
# ---------------------------------------------------------------------------


def run_demo() -> None:
    """代表的な質問でエージェントの RAG 動作を確認します。"""
    demo_queries = [
        "Strands Agents とはどんなフレームワークですか？",
        "RAG の仕組みと利点を説明してください。",
        "ベクトル検索に使われるデータベースにはどんなものがありますか？",
        "登録されているドキュメントの一覧を教えてください。",
    ]

    print("=" * 65)
    print("Strands RAG + Agent サンプルデモ")
    print("=" * 65)
    print(f"ナレッジベース: {len(SAMPLE_DOCUMENTS)} ドキュメント登録済み\n")

    for i, query in enumerate(demo_queries, 1):
        print(f"[質問 {i}] {query}")
        print("-" * 50)
        response = agent(query)
        print(response)
        print()


# ---------------------------------------------------------------------------
# 対話モード
# ---------------------------------------------------------------------------


def run_interactive() -> None:
    """ユーザーと対話しながら RAG エージェントを使います。"""
    print("=" * 65)
    print("Strands RAG + Agent インタラクティブモード")
    print("終了: 'quit' または Ctrl+C")
    print(f"ナレッジベース: {len(SAMPLE_DOCUMENTS)} ドキュメント登録済み")
    print("=" * 65)

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
