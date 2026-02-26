#!/usr/bin/env python3
"""
Claude Code Stop Hook: セッションサマリーをConfluenceへ投稿するスクリプト

必要な環境変数:
  CONFLUENCE_BASE_URL    Confluenceのベースurl (例: https://yourcompany.atlassian.net)
  CONFLUENCE_USER        ConfluenceユーザーのEmail
  CONFLUENCE_API_TOKEN   Confluence APIトークン
  CONFLUENCE_SPACE_KEY   投稿先のスペースキー (例: TEAM)
  CONFLUENCE_PARENT_ID   親ページID (任意)
  ANTHROPIC_API_KEY      AnthropicのAPIキー (サマリー生成用)
"""

import json
import sys
import os
import base64
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional


# -------- 環境変数 --------

def get_env(key: str, required: bool = True) -> Optional[str]:
    value = os.environ.get(key)
    if required and not value:
        print(f"[confluence-hook] 環境変数 {key} が未設定のためスキップします", file=sys.stderr)
        sys.exit(0)  # セッション終了をブロックしないよう 0 で終了
    return value


# -------- サマリー生成 --------

def build_transcript_text(transcript: list) -> str:
    """トランスクリプトをプレーンテキストに変換（Claudeへの入力用）"""
    lines = []
    for message in transcript:
        role = message.get("role", "unknown").upper()
        content = message.get("content", "")

        if isinstance(content, str):
            if content.strip():
                lines.append(f"[{role}]\n{content}")
        elif isinstance(content, list):
            parts = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type", "")
                if btype == "text":
                    text = block.get("text", "").strip()
                    if text:
                        parts.append(text)
                elif btype == "tool_use":
                    name = block.get("name", "")
                    inp = block.get("input", {})
                    # ファイルパスなど重要な情報だけ抽出
                    summary_parts = []
                    for k in ("command", "file_path", "pattern", "path", "query"):
                        if k in inp:
                            summary_parts.append(f"{k}={str(inp[k])[:120]}")
                    inp_str = ", ".join(summary_parts) if summary_parts else json.dumps(inp, ensure_ascii=False)[:150]
                    parts.append(f"[Tool:{name}] {inp_str}")
                # tool_result は省略（ノイズになりやすい）
            if parts:
                lines.append(f"[{role}]\n" + "\n".join(parts))

    return "\n\n---\n\n".join(lines)


def summarize_session(transcript: list) -> Optional[str]:
    """Anthropic APIを使ってセッション内容をサマライズ"""
    api_key = get_env("ANTHROPIC_API_KEY")

    conversation_text = build_transcript_text(transcript)

    # 長すぎる場合は切り詰め（APIのコンテキスト制限対策）
    max_chars = 80_000
    if len(conversation_text) > max_chars:
        conversation_text = conversation_text[:max_chars] + "\n\n...(以降省略)"

    prompt = f"""以下はClaudeとユーザーのセッションのトランスクリプトです。
後から振り返りやすいよう、日本語で構造化されたサマリーを作成してください。

以下のMarkdown形式でまとめてください（該当しない項目はそのまま「なし」と記載）:

## 背景・目的
（セッションで取り組んだ課題や背景）

## 実施した作業
（実際に行った作業を箇条書きで）

## 作成・変更したファイル
（ファイルパスと変更内容の概要を箇条書きで）

## 主要な決定事項・判断
（重要な設計判断や技術的な選択）

## 成果・結果
（セッションで達成されたこと）

## 次のステップ・残課題
（未完了のタスクや今後検討すべき事項）

---

トランスクリプト:
{conversation_text}
"""

    request_body = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=request_body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read())
            return result["content"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[confluence-hook] Anthropic APIエラー: {e.code} - {body[:300]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[confluence-hook] サマリー生成エラー: {e}", file=sys.stderr)
        return None


# -------- Markdown → Confluence Storage Format 変換 --------

def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _inline(text: str) -> str:
    """インラインのbold/italic/codeを変換"""
    import re
    # `code`
    text = re.sub(r"`([^`]+)`", lambda m: f"<code>{_esc(m.group(1))}</code>", text)
    # **bold**
    text = re.sub(r"\*\*(.+?)\*\*", lambda m: f"<strong>{_esc(m.group(1))}</strong>", text)
    # *italic*
    text = re.sub(r"\*(.+?)\*", lambda m: f"<em>{_esc(m.group(1))}</em>", text)
    return text


def markdown_to_confluence_storage(md: str) -> str:
    """MarkdownをConfluence Storage Format (XHTML) に変換"""
    import re
    lines = md.split("\n")
    html = []
    in_ul = False
    in_code = False
    code_lang = ""
    code_buf = []

    def close_list():
        nonlocal in_ul
        if in_ul:
            html.append("</ul>")
            in_ul = False

    for line in lines:
        # コードブロック開始/終了
        m = re.match(r"^```(\w*)", line)
        if m:
            if not in_code:
                close_list()
                in_code = True
                code_lang = m.group(1)
                code_buf = []
            else:
                # コードブロック終了
                lang_attr = f' language="{_esc(code_lang)}"' if code_lang else ""
                code_html = "\n".join(
                    line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    for line in code_buf
                )
                html.append(
                    f'<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">{_esc(code_lang) if code_lang else "none"}</ac:parameter>'
                    f"<ac:plain-text-body><![CDATA[{chr(10).join(code_buf)}]]></ac:plain-text-body></ac:structured-macro>"
                )
                in_code = False
                code_lang = ""
                code_buf = []
            continue

        if in_code:
            code_buf.append(line)
            continue

        # 見出し
        if re.match(r"^### ", line):
            close_list()
            html.append(f"<h3>{_inline(_esc(line[4:]))}</h3>")
        elif re.match(r"^## ", line):
            close_list()
            html.append(f"<h2>{_inline(_esc(line[3:]))}</h2>")
        elif re.match(r"^# ", line):
            close_list()
            html.append(f"<h1>{_inline(_esc(line[2:]))}</h1>")
        # リスト
        elif re.match(r"^[-*] ", line):
            if not in_ul:
                html.append("<ul>")
                in_ul = True
            html.append(f"<li>{_inline(_esc(line[2:]))}</li>")
        elif re.match(r"^  [-*] ", line):
            html.append(f"<li>{_inline(_esc(line[4:]))}</li>")
        # 水平線
        elif line.strip() in ("---", "***", "___"):
            close_list()
            html.append("<hr/>")
        # 空行
        elif line.strip() == "":
            close_list()
        # 通常テキスト
        else:
            close_list()
            html.append(f"<p>{_inline(_esc(line))}</p>")

    close_list()

    # 未閉のコードブロックのフォールバック
    if in_code and code_buf:
        html.append(f"<pre>{_esc(chr(10).join(code_buf))}</pre>")

    return "\n".join(html)


# -------- Confluence投稿 --------

def post_to_confluence(title: str, summary_md: str, session_id: str) -> bool:
    base_url = get_env("CONFLUENCE_BASE_URL").rstrip("/")
    user = get_env("CONFLUENCE_USER")
    token = get_env("CONFLUENCE_API_TOKEN")
    space_key = get_env("CONFLUENCE_SPACE_KEY")
    parent_id = get_env("CONFLUENCE_PARENT_ID", required=False)

    credentials = base64.b64encode(f"{user}:{token}".encode()).decode()

    # セッションIDをメタ情報として追加
    meta_html = (
        f'<ac:structured-macro ac:name="info">'
        f"<ac:rich-text-body>"
        f"<p><strong>Session ID:</strong> {_esc(session_id)}</p>"
        f"<p><strong>生成日時:</strong> {_esc(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</p>"
        f"</ac:rich-text-body></ac:structured-macro>"
    )

    body_html = meta_html + "\n" + markdown_to_confluence_storage(summary_md)

    page_data = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": body_html,
                "representation": "storage",
            }
        },
    }
    if parent_id:
        page_data["ancestors"] = [{"id": parent_id}]

    request_body = json.dumps(page_data).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url}/wiki/rest/api/content",
        data=request_body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            page_id = result.get("id", "")
            page_url = f"{base_url}/wiki/spaces/{space_key}/pages/{page_id}"
            print(f"[confluence-hook] ✅ Confluenceページを作成しました: {page_url}")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[confluence-hook] Confluence APIエラー: {e.code} - {body[:400]}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[confluence-hook] 投稿エラー: {e}", file=sys.stderr)
        return False


# -------- エントリーポイント --------

def main():
    # stdinからセッションデータを読み込む
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        print(f"[confluence-hook] JSONパースエラー: {e}", file=sys.stderr)
        sys.exit(0)

    # 再帰的なStop hookの無限ループを防ぐ
    if data.get("stop_hook_active"):
        sys.exit(0)

    session_id = data.get("session_id", "unknown")
    transcript = data.get("transcript", [])

    if not transcript:
        print("[confluence-hook] トランスクリプトが空のためスキップ", file=sys.stderr)
        sys.exit(0)

    # ユーザー発話が2件未満の場合はスキップ（試行錯誤のみのセッションを除外）
    user_messages = [m for m in transcript if m.get("role") == "user"]
    if len(user_messages) < 2:
        print("[confluence-hook] セッション内容が短いためスキップ", file=sys.stderr)
        sys.exit(0)

    print("[confluence-hook] セッションサマリーを生成中...", file=sys.stderr)
    summary = summarize_session(transcript)
    if not summary:
        print("[confluence-hook] サマリー生成に失敗しました", file=sys.stderr)
        sys.exit(0)

    # ページタイトル: 日付 + セッションIDの先頭8文字
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    short_id = session_id[:8] if len(session_id) >= 8 else session_id
    title = f"AI作業ログ {date_str} [{short_id}]"

    post_to_confluence(title, summary, session_id)
    sys.exit(0)


if __name__ == "__main__":
    main()
