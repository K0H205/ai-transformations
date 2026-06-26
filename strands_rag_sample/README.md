# Strands RAG + Agent サンプル

Strands Agents SDK と RAG（検索拡張生成）を組み合わせたエージェントのサンプルです。

## アーキテクチャ

```mermaid
flowchart TD
    User(["👤 ユーザー"])
    Agent["🤖 Strands Agent\n(claude-opus-4-8)"]
    RT["🔧 retrieve_documents\n(Strands @tool)"]
    LK["🔧 list_knowledge_base\n(Strands @tool)"]
    RS["📦 RAGStore\n(インメモリ)"]
    DB[("📄 ドキュメント\nコレクション")]
    Embed["📐 埋め込み生成\n(word-hash / 256次元)"]
    Cos["🔢 コサイン類似度\n(Top-K 選択)"]
    LLM["☁️ Anthropic API\nclaude-opus-4-8"]

    User -->|質問| Agent
    Agent -->|ツール呼び出し| RT
    Agent -->|ツール呼び出し| LK
    RT --> RS
    LK --> RS
    RS --> DB
    DB -->|ドキュメント全件| Embed
    Embed -->|クエリ埋め込み| Cos
    Cos -->|Top-K 結果| RT
    RT -->|検索結果テキスト| Agent
    Agent -->|コンテキスト付きプロンプト| LLM
    LLM -->|生成回答| Agent
    Agent -->|回答| User
```

## RAG フロー詳細

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 ユーザー
    participant Agent as 🤖 Agent
    participant Tool as 🔧 retrieve_documents
    participant Store as 📦 RAGStore
    participant API as ☁️ Anthropic API

    User->>Agent: 質問を入力
    Agent->>API: 質問を送信（どのツールを使うか判断）
    API-->>Agent: retrieve_documents を呼び出すよう指示
    Agent->>Tool: query="<質問>", top_k=3
    Tool->>Store: search(query, top_k)
    Store-->>Tool: 類似度上位ドキュメント (Top-K)
    Tool-->>Agent: 検索結果テキスト
    Agent->>API: 質問 + 検索結果コンテキストで再リクエスト
    API-->>Agent: コンテキストに基づいた回答
    Agent-->>User: 回答（参照ドキュメント ID 付き）
```

## ファイル構成

```
strands_rag_sample/
├── agent.py         # エージェント本体・デモ・対話モード
├── rag_store.py     # インメモリ RAG ストア（類似度検索）
├── rag_tools.py     # Strands @tool 定義（retrieve / list）
├── requirements.txt # 依存パッケージ
└── README.md        # 本ファイル
```

## セットアップと実行

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-api-key"

# デモモード
python agent.py

# 対話モード
python agent.py interactive
```

## ドキュメントの追加

`agent.py` の `SAMPLE_DOCUMENTS` リストにエントリを追加するだけです。

```python
{
    "id": "my-doc",
    "text": "追加したいテキスト内容...",
    "metadata": {"category": "my-category"},
}
```

本番環境では `RAGStore._embed()` を Voyage AI や OpenAI Embeddings に差し替え、
ストレージを Pinecone / pgvector 等に切り替えることを推奨します。
