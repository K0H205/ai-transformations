"""
マスキング層
======================================================

LLMへ送信するテキストから機密情報を除去する最小限の正規表現ベースのマスカー。
MVPスコープでは Presidio 等の高度なPIIマスキングは導入せず、
資格情報・トークン・メールアドレス・ホームディレクトリパスの代表パターンのみを扱う。
"""

from __future__ import annotations

import re

_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9_\-.=]{10,}", re.IGNORECASE)),
    (
        "kv_secret",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-./+=]{6,}['\"]?"
        ),
    ),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
]


def mask_text(text: str, home_dir: str | None = None) -> str:
    """テキスト中の機密情報をプレースホルダに置換する。

    Args:
        text: マスク対象のテキスト。
        home_dir: 検出したホームディレクトリの絶対パス(例: ``/home/user``)。
            指定された場合、そのパスを ``~`` に正規化する。
    """
    masked = text

    if home_dir:
        stripped = home_dir.rstrip("/")
        # home_dir が "/" 等で空文字になると re.sub("", ...) が全文字間に "~" を
        # 挿入してテキストを破壊するため、空パターンは置換しない。
        if stripped:
            masked = re.sub(re.escape(stripped), "~", masked)

    for label, pattern in _PATTERNS:
        masked = pattern.sub(f"[MASKED:{label}]", masked)

    return masked
