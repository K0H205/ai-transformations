# Playwright CLI Skill

## 概要

Playwright CLI を使用してブラウザ UI を自動操作するための Skill。
Bash ツールでスクリプトを実行することで、フォーム入力・クリック・ナビゲーションなどの操作を行う。

## 前提条件

Playwright がインストールされていること。未インストールの場合は以下を実行:

```bash
npm install -D @playwright/test
npx playwright install chromium
```

バージョン確認:

```bash
npx playwright --version
```

## 基本コマンド

| コマンド | 用途 |
|---------|------|
| `npx playwright open <url>` | ブラウザをインタラクティブに開く |
| `npx playwright codegen <url>` | UI 操作を記録してコードを自動生成 |
| `npx playwright screenshot <url> out.png` | スクリーンショットを取得 |

## スクリプトによる自動化（推奨）

実際の自動化には Node.js スクリプトを作成して Bash で実行する。

### スクリプトのひな型

```javascript
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false }); // true にするとバックグラウンド実行
  const page = await browser.newPage();

  try {
    // URL に移動
    await page.goto('https://example.com');

    // テキストでボタンをクリック
    await page.click('text=ログイン');

    // 入力フォームにテキストを入力
    await page.fill('input[name="username"]', 'user@example.com');
    await page.fill('input[name="password"]', 'secret');

    // ドロップダウンを選択
    await page.selectOption('select[name="project"]', 'ProjectA');

    // フォームを送信
    await page.click('button[type="submit"]');

    // ページ遷移を待機
    await page.waitForNavigation();

    console.log('✅ 操作完了');
  } catch (error) {
    console.error('❌ エラー:', error.message);
    await page.screenshot({ path: '/tmp/error.png' });
  } finally {
    await browser.close();
  }
})();
```

### Bash で実行

```bash
node /tmp/playwright-script.js
```

## よく使うセレクター

| 操作対象 | セレクター例 |
|---------|------------|
| テキストで要素を選択 | `text=ボタンテキスト` |
| CSS セレクター | `input[name="field"]` |
| ラベルから入力欄を選択 | `label:has-text("プロジェクト") >> input` |
| data-testid 属性 | `[data-testid="submit-btn"]` |
| XPath | `//button[@type="submit"]` |
| プレースホルダー | `input[placeholder="時間を入力"]` |

## 待機・タイミング制御

```javascript
// 特定要素が表示されるまで待機
await page.waitForSelector('div.success-message');

// 固定時間待機（ミリ秒）
await page.waitForTimeout(1000);

// ネットワーク通信が落ち着くまで待機
await page.waitForLoadState('networkidle');

// ページ遷移を待機
await page.waitForNavigation();
```

## デバッグ Tips

- `headless: false` にすると実際のブラウザ画面が表示され、動作を視認できる
- `page.screenshot({ path: 'debug.png' })` で任意のタイミングでスクリーンショットを取得
- `PWDEBUG=1 node script.js` でインスペクターモードを起動（`headless: false` と併用）
- セレクターに迷ったら `npx playwright codegen <url>` で操作を録画してコードを参照する

## エラーハンドリングパターン

```javascript
// タイムアウトを指定してクリック
await page.click('button.submit', { timeout: 10000 });

// 要素が存在するか確認してから操作
const btn = page.locator('button.submit');
if (await btn.count() > 0) {
  await btn.click();
} else {
  console.warn('⚠️ ボタンが見つかりませんでした');
}
```

## 注意事項

- Playwright CLI のコマンドや Node.js スクリプトの実行は **必ず Bash ツール** を使うこと
- スクリプトは `/tmp/` 以下に一時ファイルとして作成し、実行後は削除してよい
- ヘッドレスモード (`headless: true`) は CI 環境向け。動作確認は `headless: false` で行う
