# Playwright ブラウザ自動化 Skill

## 概要

Playwright を使用してブラウザ UI を自動操作するための **再利用可能な Skill**。
他の Skill からこの Skill を参照し、ブラウザ自動化が必要な場面で共通パターンを利用する。

---

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

---

## 使い方（他の Skill から参照する場合）

この Skill は **直接呼び出すものではなく、他の Skill がブラウザ自動化を行う際の共通リファレンス** として機能する。

### 呼び出し元の Skill が行うこと

1. **入力データを準備する** — 操作に必要なデータ（URL、入力値、セレクターなど）を確定する
2. **この Skill のテンプレートを使ってスクリプトを生成する**
3. **Bash ツールで実行する**

---

## スクリプトテンプレート

### 基本テンプレート

すべてのブラウザ自動化スクリプトはこの構造に従う:

```javascript
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    await page.goto('TARGET_URL');

    // === 操作をここに記述 ===

    console.log('✅ 操作完了');
  } catch (error) {
    console.error('❌ エラー:', error.message);
    await page.screenshot({ path: '/tmp/error.png' });
    console.error('スクリーンショットを /tmp/error.png に保存しました');
  } finally {
    await browser.close();
  }
})();
```

### ループ入力テンプレート（複数エントリの一括操作）

データ配列をループして繰り返しフォーム入力を行うパターン:

```javascript
const { chromium } = require('playwright');

const entries = [
  // 呼び出し元の Skill がデータを埋める
];

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    await page.goto('TARGET_URL');

    // ログインが必要な場合
    // await page.fill('INPUT_SELECTOR', 'VALUE');
    // await page.click('SUBMIT_SELECTOR');
    // await page.waitForNavigation();

    for (const entry of entries) {
      console.log(`入力中: ${JSON.stringify(entry)}`);

      // === 呼び出し元の Skill がフォーム操作を定義 ===

      await page.waitForTimeout(1000);
    }

    console.log('✅ 全エントリの入力が完了しました');
  } catch (error) {
    console.error('❌ エラーが発生しました:', error.message);
    await page.screenshot({ path: '/tmp/error.png' });
    console.error('スクリーンショットを /tmp/error.png に保存しました');
  } finally {
    await browser.close();
  }
})();
```

---

## 操作リファレンス

### セレクター

| 操作対象 | セレクター例 |
|---------|------------|
| テキストで要素を選択 | `text=ボタンテキスト` |
| CSS セレクター | `input[name="field"]` |
| ラベルから入力欄を選択 | `label:has-text("ラベル名") >> input` |
| data-testid 属性 | `[data-testid="submit-btn"]` |
| XPath | `//button[@type="submit"]` |
| プレースホルダー | `input[placeholder="入力してください"]` |

### フォーム操作

```javascript
// テキスト入力
await page.fill('input[name="field"]', 'value');

// ドロップダウン選択
await page.selectOption('select[name="field"]', 'value');

// ボタンクリック
await page.click('button[type="submit"]');

// チェックボックス
await page.check('input[type="checkbox"]');
await page.uncheck('input[type="checkbox"]');
```

### 待機・タイミング制御

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

### エラーハンドリング

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

---

## 実行ルール

| ルール | 内容 |
|-------|------|
| **実行方法** | スクリプトを `/tmp/` に作成し、`node /tmp/<script>.js` を Bash ツールで実行 |
| **表示モード** | 動作確認は `headless: false`、CI 環境は `headless: true` |
| **エラー時** | スクリーンショットを `/tmp/error.png` に保存し、ユーザーに共有 |
| **後片付け** | 実行後のスクリプトは削除してよい |

## デバッグ Tips

- `headless: false` にすると実際のブラウザ画面が表示され、動作を視認できる
- `page.screenshot({ path: 'debug.png' })` で任意のタイミングでスクリーンショットを取得
- `PWDEBUG=1 node script.js` でインスペクターモードを起動
- セレクターに迷ったら `npx playwright codegen <url>` で操作を録画してコードを参照する

## 基本コマンド

| コマンド | 用途 |
|---------|------|
| `npx playwright open <url>` | ブラウザをインタラクティブに開く |
| `npx playwright codegen <url>` | UI 操作を記録してコードを自動生成 |
| `npx playwright screenshot <url> out.png` | スクリーンショットを取得 |
