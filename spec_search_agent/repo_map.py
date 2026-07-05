"""
リポジトリ地図（簡易Wiki）の生成
================================

調査対象リポジトリの全体像を、エージェント起動時にシステムプロンプトへ注入する
ためのテキストとして生成する。DevinSearch における Wiki と同じく「どこを見るべきか」
の初動の当たり付けを支援するのが目的。

LLM は使わず、標準ライブラリ `ast` による静的抽出のみで構成する:
- 全ファイルの相対パス一覧（ファイルツリー）
- Python ファイルはモジュール docstring の先頭行と、トップレベルの
  関数/クラスのシグネチャ + docstring 先頭行

LLM 不要のため生成は高速・無料・決定的で、キャッシュ管理も不要（毎回生成する）。
"""

import ast
from pathlib import Path

from tools import IGNORED_DIR_NAMES


def _first_docstring_line(node: ast.AST) -> str | None:
    doc = ast.get_docstring(node)
    if not doc:
        return None
    return doc.strip().splitlines()[0]


def _format_args(args: ast.arguments) -> str:
    names = [a.arg for a in args.posonlyargs + args.args]
    if args.vararg:
        names.append(f"*{args.vararg.arg}")
    names.extend(a.arg for a in args.kwonlyargs)
    if args.kwarg:
        names.append(f"**{args.kwarg.arg}")
    return ", ".join(names)


def _summarize_python(path: Path) -> list[str]:
    """Python ファイルからシグネチャと docstring 先頭行を抽出する。"""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return []

    lines = []
    module_doc = _first_docstring_line(tree)
    if module_doc:
        lines.append(f"  # {module_doc}")

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            lines.append(f"  {prefix} {node.name}({_format_args(node.args)})")
            doc = _first_docstring_line(node)
            if doc:
                lines.append(f"      # {doc}")
        elif isinstance(node, ast.ClassDef):
            lines.append(f"  class {node.name}")
            doc = _first_docstring_line(node)
            if doc:
                lines.append(f"      # {doc}")
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    prefix = "async def" if isinstance(item, ast.AsyncFunctionDef) else "def"
                    lines.append(f"      {prefix} {item.name}({_format_args(item.args)})")
    return lines


def build_repo_map(base_dir: str, max_chars: int = 8000) -> str:
    """
    base_dir 配下のファイルツリーと Python シグネチャ一覧をテキストで返す。
    max_chars を超える場合は打ち切り、その旨を末尾に明記する。
    """
    base = Path(base_dir).resolve()
    files = sorted(
        p for p in base.glob("**/*")
        if p.is_file() and not any(part in IGNORED_DIR_NAMES for part in p.relative_to(base).parts)
    )
    if not files:
        return "（対象ディレクトリにファイルが見つかりませんでした）"

    sections = []
    for p in files:
        rel = p.relative_to(base)
        section = [str(rel)]
        if p.suffix == ".py":
            section.extend(_summarize_python(p))
        sections.append("\n".join(section))

    result = "\n".join(sections)
    if len(result) > max_chars:
        result = result[:max_chars] + "\n…(リポジトリ地図はここで打ち切りました。全体は list_files で確認してください)"
    return result
