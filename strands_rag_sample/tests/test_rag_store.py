"""RAGStore のユニットテスト（Anthropic API 呼び出しなし）。"""

import math
from unittest.mock import MagicMock

import pytest

from rag_store import Document, RAGStore


@pytest.fixture
def store():
    client = MagicMock()
    return RAGStore(client=client)


# ---------------------------------------------------------------------------
# _simple_embed
# ---------------------------------------------------------------------------


class TestSimpleEmbed:
    def test_returns_256_dim_vector(self, store):
        vec = store._simple_embed("hello world")
        assert len(vec) == 256

    def test_is_unit_normalized(self, store):
        vec = store._simple_embed("some text here")
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 1e-6

    def test_empty_string_returns_zero_vector(self, store):
        vec = store._simple_embed("")
        assert all(v == 0.0 for v in vec)

    def test_same_text_gives_same_vector(self, store):
        v1 = store._simple_embed("reproducible")
        v2 = store._simple_embed("reproducible")
        assert v1 == v2

    def test_different_texts_give_different_vectors(self, store):
        v1 = store._simple_embed("python programming")
        v2 = store._simple_embed("quantum physics")
        assert v1 != v2


# ---------------------------------------------------------------------------
# _cosine
# ---------------------------------------------------------------------------


class TestCosine:
    def test_identical_vectors_return_1(self, store):
        v = [1.0, 0.0, 0.0]
        assert abs(store._cosine(v, v) - 1.0) < 1e-6

    def test_orthogonal_vectors_return_0(self, store):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(store._cosine(a, b)) < 1e-6

    def test_opposite_vectors_return_minus_1(self, store):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(store._cosine(a, b) - (-1.0)) < 1e-6


# ---------------------------------------------------------------------------
# add_document / add_documents
# ---------------------------------------------------------------------------


class TestAddDocument:
    def test_add_single_document(self, store):
        store.add_document("doc1", "hello world")
        assert len(store.documents) == 1
        assert store.documents[0].id == "doc1"

    def test_add_document_with_metadata(self, store):
        store.add_document("doc1", "text", metadata={"cat": "test"})
        assert store.documents[0].metadata == {"cat": "test"}

    def test_add_document_sets_embedding(self, store):
        store.add_document("doc1", "hello")
        assert store.documents[0].embedding is not None
        assert len(store.documents[0].embedding) == 256

    def test_add_documents_bulk(self, store):
        docs = [
            {"id": "a", "text": "first"},
            {"id": "b", "text": "second", "metadata": {"x": 1}},
        ]
        store.add_documents(docs)
        assert len(store.documents) == 2
        assert store.documents[1].metadata == {"x": 1}


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_empty_store_returns_empty_list(self, store):
        assert store.search("anything") == []

    def test_returns_at_most_top_k(self, store):
        for i in range(5):
            store.add_document(f"doc{i}", f"document number {i}")
        results = store.search("document", top_k=2)
        assert len(results) <= 2

    def test_result_keys(self, store):
        store.add_document("doc1", "hello world")
        results = store.search("hello")
        assert set(results[0].keys()) == {"id", "text", "metadata", "score"}

    def test_most_relevant_ranked_first(self, store):
        store.add_document("rag", "RAG retrieval augmented generation vector search")
        store.add_document("cooking", "recipe pasta tomato sauce cooking kitchen")
        results = store.search("retrieval augmented generation", top_k=2)
        assert results[0]["id"] == "rag"

    def test_score_is_between_minus1_and_1(self, store):
        store.add_document("doc1", "some text")
        results = store.search("some text")
        assert -1.0 <= results[0]["score"] <= 1.0

    def test_exact_match_has_high_score(self, store):
        store.add_document("doc1", "machine learning neural network")
        results = store.search("machine learning neural network")
        assert results[0]["score"] > 0.9
