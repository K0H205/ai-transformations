"""
RAG ツール定義
==============

Strands の @tool デコレータで定義した RAG 検索ツールです。
エージェントはこのツールを呼び出してナレッジベースを参照します。
"""

from strands import tool

# グローバルで RAGStore を保持（エージェント作成前に set_store() で登録）
_store = None


def set_store(store) -> None:
    global _store
    _store = store


@tool
def retrieve_documents(query: str, top_k: int = 3) -> str:
    """ナレッジベースからクエリに関連するドキュメントを検索して返す。

    Args:
        query: 検索クエリ文字列
        top_k: 返すドキュメントの最大件数（デフォルト 3）

    Returns:
        関連ドキュメントの内容（見つからない場合はその旨を返す）
    """
    if _store is None:
        return "エラー: ナレッジベースが初期化されていません。"

    results = _store.search(query, top_k=top_k)
    if not results:
        return "関連するドキュメントが見つかりませんでした。"

    lines = [f"検索結果 ({len(results)} 件):"]
    for i, r in enumerate(results, 1):
        meta_str = ", ".join(f"{k}={v}" for k, v in r["metadata"].items()) if r["metadata"] else ""
        lines.append(f"\n[{i}] ID: {r['id']} (類似度: {r['score']}){' | ' + meta_str if meta_str else ''}")
        lines.append(r["text"])
    return "\n".join(lines)


@tool
def list_knowledge_base() -> str:
    """ナレッジベースに登録されているすべてのドキュメントの一覧を返す。

    Returns:
        ドキュメント ID とメタデータの一覧
    """
    if _store is None:
        return "エラー: ナレッジベースが初期化されていません。"

    if not _store.documents:
        return "ナレッジベースにドキュメントがありません。"

    lines = [f"登録ドキュメント数: {len(_store.documents)}"]
    for doc in _store.documents:
        meta_str = ", ".join(f"{k}={v}" for k, v in doc.metadata.items()) if doc.metadata else "なし"
        lines.append(f"  - {doc.id} (メタデータ: {meta_str})")
    return "\n".join(lines)
