# Time Tracker 工数入力 Skill

## 概要

Outlook カレンダーの指定日予定を取得し、Time Tracker へ工数を自動入力する。

**フロー**: 日付ヒアリング → Outlook 予定取得 → プロジェクトマッピング → ユーザー確認 → Playwright CLI で入力

---

## Time Tracker URL

```
YOUR_TIMETRACKER_URL
```

> ⚠️ 上記を実際の Time Tracker の URL に書き換えてください。

---

## プロジェクトマッピングルール

カレンダー予定タイトルに含まれるキーワードで Time Tracker のプロジェクト／タスクを決定する。
**上から順に評価し、最初にマッチしたルールを適用する。**

| 予定タイトルのキーワード（部分一致） | Time Tracker プロジェクト | タスク |
|--------------------------------------|--------------------------|--------|
| 朝会 / デイリー / Stand-up / standup | 社内MTG | ミーティング |
| 1on1 / 1 on 1 / 面談 / 1:1         | 社内MTG | 1on1 |
| 設計 / デザイン / アーキ             | ProjectA | 設計・レビュー |
| レビュー / Review / PR              | ProjectA | コードレビュー |
| 開発 / 実装 / コーディング / Dev     | ProjectA | 開発 |
| テスト / QA / 検証                  | ProjectA | テスト |
| 打ち合わせ / MTG / Meeting           | 社内MTG | ミーティング |
| （上記に該当しない）                 | 未分類 | その他 |

> ⚠️ 上記はサンプルです。実際の予定タイトルとプロジェクト名に合わせて編集してください。

---

## 実行手順

### Step 1: 対象日付のヒアリング（必須・最初に行うこと）

Skill 起動直後に、ユーザーへ以下を確認する:

```
工数を入力する日付を教えてください。
（例: 今日、昨日、2026-02-20 など。通常は平日を指定してください。）
```

- ユーザーの回答を解釈して ISO 形式（YYYY-MM-DD）の日付に変換する
  - 「今日」→ 実行時の日付
  - 「昨日」→ 実行時の前日
  - 「YYYY-MM-DD」形式 → そのまま使用
- 確定した日付が**土曜（weekday=6）または日曜（weekday=0）の場合**は以下の警告を出す:

```
⚠️ 指定された日付 YYYY-MM-DD は週末（土/日）です。
このまま続行しますか？
```

- ユーザーが続行を選択した場合のみ次のステップへ進む
- 確定した日付（`TARGET_DATE`）を以降のすべてのステップで使用する

---

### Step 2: Outlook 予定を取得

ms-365-mcp-server を使用して `TARGET_DATE` の予定一覧を取得する。

```
mcp__ms365__get_events を呼び出し、
start: TARGET_DATE の 00:00:00、end: TARGET_DATE の 23:59:59 の範囲で予定を取得してください。
```

各予定から以下を抽出する:
- 予定タイトル (`subject`)
- 開始時刻 (`start.dateTime`)
- 終了時刻 (`end.dateTime`)
- 所要時間（時間単位、小数点第1位まで）

---

### Step 3: マッピングとデータ整理

上記のマッピングルールに従い、各予定を Time Tracker のエントリに変換する。

整理後のデータを以下の表形式でまとめる:

```
日付: TARGET_DATE

| 予定タイトル     | 開始  | 終了  | 時間  | プロジェクト | タスク         |
|----------------|-------|-------|-------|------------|---------------|
| 朝会           | 09:00 | 09:30 | 0.5h  | 社内MTG     | ミーティング    |
| 設計レビュー    | 10:00 | 12:00 | 2.0h  | ProjectA   | 設計・レビュー  |
| 開発           | 13:00 | 17:00 | 4.0h  | ProjectA   | 開発           |
| ...            | ...   | ...   | ...   | ...         | ...           |

合計: X.X 時間
```

---

### Step 4: ユーザーへの確認（必須・スキップ禁止）

**以下をユーザーに提示し、明示的な承認を得ること。承認前に Playwright CLI を実行してはいけない。**

1. Step 3 で整理した表を表示する
2. 合計時間を明示する
3. 合計が **8 時間を超える場合** は以下の警告を表示する:

```
⚠️ 警告: 合計時間が X.X 時間です（8 時間を超えています）。
入力内容を確認・調整してから続行してください。
```

4. 「このまま Time Tracker に入力しますか？」と確認を求める
5. ユーザーが「はい」と回答した場合のみ Step 5 に進む
6. ユーザーが修正を求めた場合は内容を修正して再確認する

---

### Step 5: Playwright CLI で Time Tracker に入力

ユーザー承認後に以下を実行する。

#### 5-1. 入力スクリプトを生成

Step 3 のデータを使って `/tmp/timetracker-entry.js` を作成する。
`date` フィールドには Step 1 で確定した `TARGET_DATE` を使用すること:

```javascript
const { chromium } = require('playwright');

// Step 3 で確定したエントリデータ（date には Step 1 で確定した TARGET_DATE を使用）
const entries = [
  { project: '社内MTG',  task: 'ミーティング',   hours: 0.5, date: 'TARGET_DATE' },
  { project: 'ProjectA', task: '設計・レビュー', hours: 2.0, date: 'TARGET_DATE' },
  { project: 'ProjectA', task: '開発',           hours: 4.0, date: 'TARGET_DATE' },
  // 実際のエントリに置き換える
];

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    await page.goto('YOUR_TIMETRACKER_URL');

    // ログインが必要な場合はここに追加
    // await page.fill('input[name="email"]', 'your@email.com');
    // await page.fill('input[name="password"]', 'yourpassword');
    // await page.click('button[type="submit"]');
    // await page.waitForNavigation();

    for (const entry of entries) {
      console.log(`入力中: ${entry.project} / ${entry.task} / ${entry.hours}h`);

      // ---- Time Tracker のフォームに合わせてセレクターを調整 ----
      await page.click('text=新規入力');                            // 新規入力ボタン
      await page.fill('input[name="date"]', entry.date);           // 日付
      await page.selectOption('select[name="project"]', entry.project); // プロジェクト
      await page.selectOption('select[name="task"]', entry.task);       // タスク
      await page.fill('input[name="hours"]', String(entry.hours)); // 時間
      await page.click('button[type="submit"]');                   // 保存
      // ---- ここまで調整 ----

      await page.waitForTimeout(1000); // 次エントリ前に 1 秒待機
    }

    console.log('✅ 全エントリの入力が完了しました');
  } catch (error) {
    console.error('❌ エラーが発生しました:', error.message);
    await page.screenshot({ path: '/tmp/timetracker-error.png' });
    console.error('スクリーンショットを /tmp/timetracker-error.png に保存しました');
  } finally {
    await browser.close();
  }
})();
```

#### 5-2. Bash ツールでスクリプトを実行

```bash
node /tmp/timetracker-entry.js
```

#### 5-3. 実行結果の確認

- **成功時**: ターミナル出力に `✅ 全エントリの入力が完了しました` が表示される。ユーザーに完了を報告する。
- **エラー時**: エラーメッセージと `/tmp/timetracker-error.png` の内容をユーザーに共有し、手動対応を促す。

---

## 注意事項

| 項目 | 内容 |
|------|------|
| **日付ヒアリング** | Step 1 の日付確認を必ず最初に行うこと。省略禁止 |
| **入力前の確認** | Step 4 のユーザー承認を必ずとること。省略・スキップ禁止 |
| **8 時間超過の警告** | 合計工数が 8h を超える場合は必ず警告メッセージを表示 |
| **Playwright の実行** | `node /tmp/timetracker-entry.js` を Bash ツールで実行すること |
| **セレクターの調整** | Time Tracker の実際の UI に合わせてセレクターを変更すること |
| **ログイン処理** | 認証が必要な場合はスクリプト内にログイン処理を追加すること |

---

## トラブルシューティング

| 問題 | 対処法 |
|------|--------|
| 要素が見つからない | `headless: false` でブラウザを表示し、実際の DOM を確認してセレクターを修正 |
| タイムアウト | `{ timeout: 10000 }` のようにタイムアウトを延長 |
| ログインが必要 | スクリプトのログインコメントアウト部分を有効化して認証情報を設定 |
| 入力が反映されない | `waitForNavigation()` や `waitForLoadState('networkidle')` を追加 |
| エラー画像を確認したい | `/tmp/timetracker-error.png` を確認する |

---

## 関連 Skill

- [`playwright-cli`](.claude/commands/playwright-cli.md) — Playwright CLI の基本操作リファレンス
