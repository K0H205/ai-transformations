"""
Agentic Search 用ツール定義（GitHub Copilot SDK 委譲版・実験的サンプル）
========================================================================

【重要: このモジュールは動作未検証です】
GitHub Copilot SDK (`github-copilot-sdk`) は単体の「検索API」を公開しておらず、
Copilot CLI のエージェント実行エンジンをプロセスとして起動し、プロンプトに対する
応答を受け取る設計 (`CopilotClient` -> `create_session` -> `send_and_wait`) になって
います。そのため本ツールは、コード探索そのものを Copilot 側のエージェントに委譲し、
その回答をそのままツール結果として返す構成にしています。

前提条件（この環境では満たされていないため未検証）:
- Copilot CLI がインストール済みで PATH から実行できること
- GitHub Copilot サブスクリプションでの認証、または BYOK 用の環境変数
  （利用する LLM の API キー）が設定されていること
- `pip install -r requirements-copilot.txt` で `github-copilot-sdk` を導入していること
"""

import asyncio
import os

from strands import tool


async def _run_copilot_search(query: str, cwd: str) -> str:
    from copilot import CopilotClient

    client = CopilotClient()
    await client.start()
    try:
        session = await client.create_session({"model": "claude-sonnet-4-6", "cwd": os.path.abspath(cwd)})
        prompt = (
            f"次のディレクトリ配下のコードを調査してください: {os.path.abspath(cwd)}\n"
            f"調査内容: {query}\n"
            "分かったことを、根拠となったファイルパスと行番号 (file:line) を明記して報告してください。"
        )
        response = await session.send_and_wait({"prompt": prompt})
        return response.data.content
    finally:
        await client.stop()


@tool
def copilot_search(query: str, cwd: str = ".") -> str:
    """
    GitHub Copilot SDK 経由でコードベースを調査する（実験的・動作未検証）。
    Copilot 自身のエージェントに探索を委譲し、file:line 付きの調査結果を受け取る。

    Args:
        query: 調査したい内容（例: "calculate 関数の入力・出力・エラー処理"）
        cwd: 調査対象のディレクトリ
    """
    try:
        return asyncio.run(_run_copilot_search(query, cwd))
    except Exception as exc:  # Copilot CLI 未インストール・未認証などをそのまま伝える
        return (
            f"copilot_search の実行に失敗しました: {exc}\n"
            "Copilot CLI のインストールと GitHub Copilot の認証（またはBYOKキー）を確認してください。"
        )
