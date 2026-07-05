"""rag_tools のユニットテスト。"""

from unittest.mock import MagicMock, patch

import pytest

import rag_tools


@pytest.fixture(autouse=True)
def reset_store():
    """各テスト前後でグローバルストアをリセットする。"""
    original = rag_tools._store
    yield
    rag_tools._store = original


@pytest.fixture
def mock_store():
    return MagicMock()


# ---------------------------------------------------------------------------
# retrieve_documents
# ---------------------------------------------------------------------------


class TestRetrieveDocuments:
    def test_returns_error_when_store_not_set(self):
        rag_tools._store = None
        result = rag_tools.retrieve_documents("query")
        assert "エラー" in result

    def test_returns_no_results_message_when_empty(self, mock_store):
        mock_store.search.return_value = []
        rag_tools.set_store(mock_store)
        result = rag_tools.retrieve_documents("query")
        assert "見つかりませんでした" in result

    def test_formats_results_correctly(self, mock_store):
        mock_store.search.return_value = [
            {"id": "doc1", "text": "テスト内容", "metadata": {"cat": "test"}, "score": 0.95}
        ]
        rag_tools.set_store(mock_store)
        result = rag_tools.retrieve_documents("query")
        assert "doc1" in result
        assert "テスト内容" in result
        assert "0.95" in result

    def test_passes_top_k_to_store(self, mock_store):
        mock_store.search.return_value = []
        rag_tools.set_store(mock_store)
        rag_tools.retrieve_documents("query", top_k=5)
        mock_store.search.assert_called_once_with("query", top_k=5)

    def test_result_count_in_header(self, mock_store):
        mock_store.search.return_value = [
            {"id": f"doc{i}", "text": f"text{i}", "metadata": {}, "score": 0.9 - i * 0.1}
            for i in range(3)
        ]
        rag_tools.set_store(mock_store)
        result = rag_tools.retrieve_documents("query")
        assert "3 件" in result


# ---------------------------------------------------------------------------
# list_knowledge_base
# ---------------------------------------------------------------------------


class TestListKnowledgeBase:
    def test_returns_error_when_store_not_set(self):
        rag_tools._store = None
        result = rag_tools.list_knowledge_base()
        assert "エラー" in result

    def test_returns_empty_message_when_no_docs(self, mock_store):
        mock_store.documents = []
        rag_tools.set_store(mock_store)
        result = rag_tools.list_knowledge_base()
        assert "ありません" in result

    def test_lists_all_document_ids(self, mock_store):
        from rag_store import Document

        mock_store.documents = [
            Document(id="doc-a", text="text a", metadata={"cat": "x"}),
            Document(id="doc-b", text="text b", metadata={}),
        ]
        rag_tools.set_store(mock_store)
        result = rag_tools.list_knowledge_base()
        assert "doc-a" in result
        assert "doc-b" in result

    def test_shows_document_count(self, mock_store):
        from rag_store import Document

        mock_store.documents = [Document(id=f"d{i}", text="t") for i in range(4)]
        rag_tools.set_store(mock_store)
        result = rag_tools.list_knowledge_base()
        assert "4" in result
