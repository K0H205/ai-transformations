# spec_search_agent_copilot — GitHub Copilot SDK 委譲版（実験的サンプル・動作未検証）

[`../spec_search_agent/`](../spec_search_agent/) と同じく、AWS Strands Agents で
コードの仕様調査を行うエージェントですが、こちらは探索そのものを
GitHub Copilot SDK (`github-copilot-sdk`) 経由で Copilot CLI のエージェントに委譲する
構成です。

Copilot SDK は単体の「検索API」を公開しておらず、Copilot CLI のエージェント実行
エンジン全体をプロセスとして起動する設計 (`CopilotClient` → `create_session` →
`send_and_wait`) のため、この方式では「検索」を丸ごと別のエージェントに委譲する形に
なります。

**この構成はこのリポジトリの開発環境では未検証です。** 動かすには以下が別途必要です。

- Copilot CLI がインストール済みで PATH から実行できること
- GitHub Copilot サブスクリプションでの認証、または BYOK 用の環境変数（利用する LLM の API キー）

## ディレクトリ構成

```
spec_search_agent_copilot/
  tools.py         # copilot_search: Copilot CLI エージェントに探索を委譲するツール
  agent.py         # 上記ツールを使う Strands Agent
  requirements.txt
```

## セットアップ

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-api-key"   # このエージェント自身のモデル用
# Copilot CLI 側の認証は copilot コマンドのドキュメントに従って別途設定する
```

## 実行

```bash
python agent.py [対象ディレクトリ]
```

## `spec_search_agent` との違い

| | [`spec_search_agent`](../spec_search_agent/)（推奨） | `spec_search_agent_copilot`（本ディレクトリ） |
|---|---|---|
| 追加の依存 | なし（`strands-agents`, `anthropic` のみ） | GitHub Copilot SDK + Copilot CLI + サブスクリプション/BYOK |
| 動作確認 | 済み | 未検証（この環境に認証情報がないため） |
| 検索の中身 | 自前の glob/grep/read | Copilot CLI エージェントへの委譲 |

特別な理由がなければ [`spec_search_agent`](../spec_search_agent/) を使ってください。
