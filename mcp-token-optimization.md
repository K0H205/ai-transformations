# はじめに
みなさんはMCP使われてますか？
MCPサーバーが登場してから約1年が経ち、エンジニア以外も気軽に接続してカスタマイズする時代になってきました。ただし、MCPサーバーは接続するだけで多くのトークンを消費するため、繋ぎすぎるとコンテキストウィンドウが枯渇するという課題を抱えています。

自分も当初は便利そうなサーバーを見つけるたびに繋いでいたのですが、MCPを使っていないセッションでもトークンが使われることに違和感を覚えました。次第にMCPサーバーを安易に接続することを避け、CLIやAgent Skillsで代替できないかを先に検討するようになりました。今では少し消極的な向き合い方をしています。

これからもMCPと付き合うためにMCPのコンテキストウィンドウ問題とそれとどう向き合っていくかをまとめたので、参考になれば幸いです。なお、MCPやAgent Skillsの基本的な説明は省いています。

# MCPサーバー接続によるコンテキスト汚染
MCPクライアントがMCPサーバーに接続すると、各ツールの名前・説明文・パラメータのJSON SchemaがAPIリクエストの`tools`パラメータとして毎回送られ、LLMとのやり取りで毎回コンテキストを占有します。

```json
{
  "name": "create_issue",
  "description": "Create a new issue in a repository",
  "inputSchema": {
    "type": "object",
    "properties": {
      "owner": { "type": "string" },
      "repo":  { "type": "string" },
      "title": { "type": "string" }
    }
  }
}
```

そのセッションでツールを一切使わなくても、接続しているだけで全スキーマが常にコンテキスト上に載り続けます。この現象は一般的に**コンテキスト汚染（context pollution）**と呼ばれています。

# なぜ起きるのか
Agent Skillsのlazy-loadingのように「使うツールだけロードすれば良いのでは?」と思いましたが、MCPの設計とLLM APIの制約が組み合わさって問題が発生しています。

#### tools/list は全ツールを返すだけ
MCPクライアントはMCPサーバーに接続した直後、セッション開始時に `tools/list` を呼び出してツール一覧を取得します。クライアントがツールを選択して取得するフィルタリングの方法がMCP仕様に定義されていないため、レスポンスは常に全量返却されるしか選択肢がありません。

クライアントは取得したツール一覧をそのままLLMのAPIリクエストに渡すため、使う予定のないツールのスキーマも毎回送り続けることになります。

```json
// GitHub MCPサーバーへの tools/list レスポンス
{
  "tools": [
    { "name": "get_file_contents",       "description": "...", "inputSchema": { ... } },
    { "name": "create_issue",            "description": "...", "inputSchema": { ... } },
    { "name": "list_pull_requests",      "description": "...", "inputSchema": { ... } },
    { "name": "create_pull_request",     "description": "...", "inputSchema": { ... } },
    { "name": "search_repositories",     "description": "...", "inputSchema": { ... } },
    { "name": "create_or_update_file",   "description": "...", "inputSchema": { ... } }
    // ...今使わないツールも含めて全量
  ]
}
```

#### ツール定義はAPIリクエストの tools 配列に含める必要がある
LLMがツールを呼び出すには、そのツールのスキーマがAPI呼び出し時に渡されている必要があります。プロンプトにテキストとして書くだけでは、モデルは正しくツールを解釈できません。

そして、この `tools` 配列はコンテキストウィンドウの一部としてトークンを消費します。LLMとのやり取りで毎回メッセージ本文とは別に全ツールのスキーマ分のトークンが上乗せされ続けます。

```json
// Anthropic APIへのリクエスト：今回 create_issue しか使わないのに全ツールが必要
{
  "model": "claude-opus-4-7",
  "messages": [{ "role": "user", "content": "issueを作って" }],
  "tools": [
    { "name": "get_file_contents",       "input_schema": { ... } },
    { "name": "create_issue",            "input_schema": { ... } },  // ← 今回使うのはこれだけ
    { "name": "list_pull_requests",      "input_schema": { ... } },
    { "name": "create_pull_request",     "input_schema": { ... } },
    { "name": "search_repositories",     "input_schema": { ... } },
    { "name": "create_or_update_file",   "input_schema": { ... } }
    // ...全ツール分のスキーマが必要
  ]
}
```

まとめると「MCPサーバーから全ツールが返ってくる」かつ「LLMへのAPIリクエストにはスキーマを含める必要がある」という2つの制約が組み合わさってこの問題が起きています。

# 各エージェントの対応状況
今回はClaude CodeとCopilot CLIのみを取り上げています。

### Claude Code
Claude Codeは、今年の1月にリリースされた[Tool Search](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)で課題を解決しています。ツール定義の合計がコンテキストの10%（約10,000トークン）を超えると自動で有効化されます。

MCPからは従来通り `tools/list` で全スキーマを受け取りますが、Claude CodeはそれをローカルにキャッシュしておきLLMへのAPIリクエストには渡しません。セッション開始時はBuilt-inの `tool_search` ツールのみをコンテキストに渡し、Claudeが必要なタイミングでクエリを投げると、キャッシュから該当スキーマを3〜5個取得・展開します。一度取得したツールは会話全体で再利用されます。実際に使うツールのスキーマだけがコンテキストに載るため、コンテキスト汚染を解消できます。

### Copilot CLI
残念ながらCopilot CLIには、動的なlazy-loadingに相当する機能はまだありません。ただし、コンテキストウィンドウ問題を認識されているのか、対策の手段はあります。

#### セッションをまたいだMCPのON/OFF管理
今月リリースされた[v1.0.19](https://github.com/github/copilot-cli/releases/tag/v1.0.19) で `/mcp enable` と `/mcp disable` によるMCPのON/OFFがセッションをまたいで永続化されるようになりました。ツール数の多いMCPサーバーは必要な時だけ有効化しておくことで、不要なセッションでのトークン消費を抑えられます。

# おわりに
たくさんMCPを繋いで便利に使いたいのに繋いだ分だけコンテキストが減るという矛盾をMCPは抱えていると思います。
個人的にはMCPのプロトコル側で根本的に解決してほしい問題だと思っています。lazy-loadingが仕様として標準サポートされる日を待ちたいところです。
