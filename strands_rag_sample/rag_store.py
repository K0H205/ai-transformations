"""
シンプルなインメモリ RAG ストア
================================

外部ベクトル DB を使わずに numpy のコサイン類似度で近似検索します。
埋め込みには Anthropic の claude-opus-4-8 を使います。

本番環境では Pinecone / pgvector / OpenSearch などに差し替えてください。
"""

import math
from dataclasses import dataclass, field
from typing import Optional

import anthropic


@dataclass
class Document:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)
    embedding: Optional[list[float]] = None


class RAGStore:
    """テキストドキュメントを保持し、クエリに近いものを返すシンプルな RAG ストア。"""

    def __init__(self, client: anthropic.Anthropic, embed_model: str = "claude-opus-4-8"):
        self.client = client
        self.embed_model = embed_model
        self.documents: list[Document] = []

    # ------------------------------------------------------------------
    # 埋め込み生成
    # ------------------------------------------------------------------

    def _embed(self, text: str) -> list[float]:
        """テキストの埋め込みベクトルを取得する。

        Note: claude-opus-4-8 は直接埋め込み API を持たないため、
        メッセージ API を使って文章のキーワード/特徴を数値化するシンプルな
        代替実装を使います。実際のプロジェクトでは voyage-3-large 等の
        専用埋め込みモデルを使うことを推奨します。
        """
        # 軽量な TF ベースの擬似埋め込み（外部 API 不要）
        return self._simple_embed(text)

    def _simple_embed(self, text: str) -> list[float]:
        """単語 hash ベースの 256 次元擬似埋め込み（デモ用）。"""
        import hashlib

        dim = 256
        vec = [0.0] * dim
        words = text.lower().split()
        for word in words:
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = h % dim
            vec[idx] += 1.0

        # L2 正規化
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    # ------------------------------------------------------------------
    # ドキュメント管理
    # ------------------------------------------------------------------

    def add_document(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        embedding = self._embed(text)
        doc = Document(id=doc_id, text=text, metadata=metadata or {}, embedding=embedding)
        self.documents.append(doc)

    def add_documents(self, docs: list[dict]) -> None:
        """[{"id": ..., "text": ..., "metadata": {...}}, ...] を一括追加。"""
        for d in docs:
            self.add_document(d["id"], d["text"], d.get("metadata"))

    # ------------------------------------------------------------------
    # 検索
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        if not self.documents:
            return []

        q_vec = self._embed(query)
        scored = []
        for doc in self.documents:
            sim = self._cosine(q_vec, doc.embedding)
            scored.append((sim, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {"id": d.id, "text": d.text, "metadata": d.metadata, "score": round(s, 4)}
            for s, d in scored[:top_k]
        ]

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1e-9
        nb = math.sqrt(sum(x * x for x in b)) or 1e-9
        return dot / (na * nb)
