"""
Agentic Search 用ツール定義（自作・軽量版）
==========================================

grep / glob / read 相当の3つの探索プリミティブを標準ライブラリのみで実装する。
Strands Agent はこれらを何度も組み合わせて呼び出しながら（Agentic Search）、
コードの実装から仕様を読み解いていく。

安全のため、いずれのツールも `SPEC_SEARCH_BASE_DIR` 環境変数で指定された
ディレクトリの外は参照できないようにガードする（未設定の場合はカレント
ディレクトリを起点にする）。
"""

import os
import re
from pathlib import Path

from strands import tool

IGNORED_DIR_NAMES = {".git", "__pycache__", "node_modules", ".venv", "venv", ".mypy_cache"}


def _base_dir() -> Path:
    return Path(os.environ.get("SPEC_SEARCH_BASE_DIR", ".")).resolve()


def _resolve_within_base(path: str) -> Path | str:
    """base_dir 配下に収まるようパスを正規化する。範囲外なら理由の文字列を返す。"""
    base = _base_dir()
    target = (base / path).resolve() if not os.path.isabs(path) else Path(path).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        return f"エラー: '{path}' は調査対象ディレクトリ '{base}' の外を指しているため参照できません。"
    return target


def _is_ignored(path: Path) -> bool:
    return any(part in IGNORED_DIR_NAMES for part in path.parts)


@tool
def list_files(directory: str = ".", pattern: str = "**/*") -> str:
    """
    調査対象ディレクトリ配下のファイル一覧を取得する。ディレクトリ構成の把握や、
    関連ファイルの当たりを付けるために最初に使用する。

    Args:
        directory: 一覧を取得するディレクトリ（調査対象ルートからの相対パス。省略時はルート直下）
        pattern: glob パターン (例: "**/*.py" で Python ファイルのみ再帰的に取得)
    """
    resolved = _resolve_within_base(directory)
    if isinstance(resolved, str):
        return resolved
    if not resolved.is_dir():
        return f"エラー: '{directory}' はディレクトリではありません。"

    files = [
        p for p in resolved.glob(pattern)
        if p.is_file() and not _is_ignored(p.relative_to(_base_dir()))
    ]
    if not files:
        return f"'{directory}' 配下でパターン '{pattern}' に一致するファイルは見つかりませんでした。"

    base = _base_dir()
    rel_paths = sorted(str(p.relative_to(base)) for p in files)
    return f"{len(rel_paths)} 件のファイルが見つかりました:\n" + "\n".join(rel_paths)


@tool
def search_code(pattern: str, directory: str = ".", file_glob: str = "**/*", context_lines: int = 2, max_matches: int = 30) -> str:
    """
    正規表現でコード内容を検索する（grep 相当）。関数名・クラス名・キーワードなど、
    仕様を裏付ける具体的な記述箇所を探すために使用する。

    Args:
        pattern: 検索する正規表現パターン
        directory: 検索対象ディレクトリ（調査対象ルートからの相対パス）
        file_glob: 検索対象を絞り込む glob パターン (例: "**/*.py")
        context_lines: マッチ行の前後何行を一緒に表示するか
        max_matches: 返す最大マッチ件数（超過分は打ち切りを明記）
    """
    resolved = _resolve_within_base(directory)
    if isinstance(resolved, str):
        return resolved
    if not resolved.is_dir():
        return f"エラー: '{directory}' はディレクトリではありません。"

    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return f"エラー: 正規表現が不正です ({exc})"

    base = _base_dir()
    results = []
    truncated = False

    for file_path in sorted(resolved.glob(file_glob)):
        if not file_path.is_file() or _is_ignored(file_path.relative_to(base)):
            continue
        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except (UnicodeDecodeError, OSError):
            continue

        for i, line in enumerate(lines):
            if regex.search(line):
                if len(results) >= max_matches:
                    truncated = True
                    break
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                snippet = "\n".join(f"{n + 1:>5}: {lines[n]}" for n in range(start, end))
                rel_path = file_path.relative_to(base)
                results.append(f"### {rel_path}:{i + 1}\n{snippet}")
        if truncated:
            break

    if not results:
        return f"パターン '{pattern}' に一致する箇所は見つかりませんでした（検索範囲: {directory}/{file_glob}）。"

    header = f"{len(results)} 件ヒットしました" + ("（上限に達したため打ち切りました）" if truncated else "")
    return header + ":\n\n" + "\n\n".join(results)


@tool
def read_file(path: str, start_line: int | None = None, end_line: int | None = None, max_lines: int = 300) -> str:
    """
    ファイルの内容を行番号付きで読み込む。search_code で見つけた箇所の前後の
    文脈や、ファイル全体のロジックを確認するために使用する。

    Args:
        path: 読み込むファイルパス（調査対象ルートからの相対パス）
        start_line: 読み込み開始行（1始まり、省略時は先頭から）
        end_line: 読み込み終了行（省略時は末尾まで、ただし max_lines で打ち切り）
        max_lines: 一度に返す最大行数
    """
    resolved = _resolve_within_base(path)
    if isinstance(resolved, str):
        return resolved
    if not resolved.is_file():
        return f"エラー: '{path}' はファイルではありません。"

    try:
        lines = resolved.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError as exc:
        return f"エラー: ファイルを読み込めません ({exc})"

    start = max(1, start_line or 1)
    end = min(len(lines), end_line or len(lines))
    truncated = False
    if end - start + 1 > max_lines:
        end = start + max_lines - 1
        truncated = True

    numbered = "\n".join(f"{n:>5}: {lines[n - 1]}" for n in range(start, end + 1))
    footer = f"\n\n(以降 {len(lines) - end} 行を省略しました。end_line を指定して続きを読んでください。)" if truncated else ""
    return f"{path} ({start}-{end}行目 / 全{len(lines)}行):\n{numbered}{footer}"
