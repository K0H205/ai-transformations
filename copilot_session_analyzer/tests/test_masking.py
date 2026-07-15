"""masking.py のテスト。"""

from __future__ import annotations

from masking import mask_text


def test_masks_aws_access_key() -> None:
    text = "key is AKIAABCDEFGHIJKLMNOP end"
    masked = mask_text(text)
    assert "AKIAABCDEFGHIJKLMNOP" not in masked
    assert "[MASKED:aws_access_key]" in masked


def test_masks_github_token() -> None:
    text = "token=ghp_1234567890abcdefghijklmnopqrst"
    masked = mask_text(text)
    assert "ghp_1234567890abcdefghijklmnopqrst" not in masked
    assert "[MASKED:github_token]" in masked


def test_masks_anthropic_key() -> None:
    text = "ANTHROPIC_API_KEY=sk-ant-api03-abcdefghijklmnopqrstuvwxyz"
    masked = mask_text(text)
    assert "sk-ant-api03-abcdefghijklmnopqrstuvwxyz" not in masked
    assert "[MASKED:anthropic_key]" in masked


def test_masks_openai_key() -> None:
    text = "OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456"
    masked = mask_text(text)
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in masked
    assert "[MASKED:openai_key]" in masked


def test_masks_bearer_token() -> None:
    text = "Authorization: Bearer abcdef1234567890.xyz"
    masked = mask_text(text)
    assert "abcdef1234567890.xyz" not in masked
    assert "[MASKED:bearer_token]" in masked


def test_masks_kv_secret() -> None:
    text = 'password: "supersecret123"'
    masked = mask_text(text)
    assert "supersecret123" not in masked
    assert "[MASKED:kv_secret]" in masked


def test_masks_email() -> None:
    text = "contact hrswkhd@gmail.com for details"
    masked = mask_text(text)
    assert "hrswkhd@gmail.com" not in masked
    assert "[MASKED:email]" in masked


def test_normalizes_home_dir() -> None:
    text = "file at /home/user/project/secret.txt was read"
    masked = mask_text(text, home_dir="/home/user")
    assert "/home/user" not in masked
    assert "~/project/secret.txt" in masked


def test_root_home_dir_does_not_corrupt_text() -> None:
    # home_dir が "/" だと rstrip 後に空文字となり、無防備だと re.sub が
    # 全文字間に "~" を挿入してテキストを破壊する。ガードされていることを確認。
    text = "error at /etc/passwd"
    masked = mask_text(text, home_dir="/")
    assert masked == text


def test_leaves_clean_text_unchanged() -> None:
    text = "this is a normal error message with no secrets"
    masked = mask_text(text)
    assert masked == text
