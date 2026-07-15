const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');

const frontendRequire = createRequire(path.resolve(__dirname, '..', 'frontend', 'package.json'));
const { chromium } = frontendRequire('playwright');

const baseUrl = process.env.PLAYWRIGHT_BASE_URL || 'http://210.165.3.139/web/';
const drawingUrl = process.env.PLAYWRIGHT_DRAWING_URL || 'http://210.165.3.139/web/drawing';
const runtimeDir = path.resolve(__dirname, '..', 'runtime');
const userDataDir = path.join(runtimeDir, 'playwright-edge-profile');
const screenshotPath = path.join(runtimeDir, 'drawing-page.png');
const summaryPath = path.join(runtimeDir, 'drawing-page-summary.json');

fs.mkdirSync(runtimeDir, { recursive: true });

async function clickIfVisible(page, selectors) {
  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    if (await locator.count()) {
      try {
        if (await locator.isVisible({ timeout: 1000 })) {
          await locator.click();
          return selector;
        }
      } catch (error) {
        // Continue trying the next selector.
      }
    }
  }
  return null;
}

async function collectTextList(page, selectors, limit = 20) {
  for (const selector of selectors) {
    const locator = page.locator(selector);
    const count = await locator.count();
    if (!count) {
      continue;
    }

    const values = [];
    for (let index = 0; index < Math.min(count, limit); index += 1) {
      const item = locator.nth(index);
      const text = (await item.innerText()).replace(/\s+/g, ' ').trim();
      if (text) {
        values.push(text);
      }
    }

    if (values.length) {
      return { selector, values };
    }
  }

  return { selector: null, values: [] };
}

async function isLoginFormVisible(page) {
  const emailInput = page.locator('input[placeholder="メールアドレス *"]').first();
  if (!await emailInput.count()) {
    return false;
  }

  try {
    return await emailInput.isVisible({ timeout: 500 });
  } catch (error) {
    return false;
  }
}

async function main() {
  const context = await chromium.launchPersistentContext(userDataDir, {
    channel: 'msedge',
    headless: false,
    slowMo: 150,
    viewport: { width: 1440, height: 960 },
  });
  const existingPage = context.pages()[0];
  const page = existingPage || await context.newPage();

  try {
    await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(2000);

    if (await isLoginFormVisible(page)) {
      console.log('開いた Edge で手動ログインしてください。完了後に自動で drawing ページへ進みます。');

      const deadline = Date.now() + 300000;
      while (Date.now() < deadline) {
        await page.waitForTimeout(1000);
        if (!await isLoginFormVisible(page)) {
          break;
        }
      }
    }

    await page.goto(drawingUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => null);
    await page.waitForTimeout(3000);

    if (await isLoginFormVisible(page)) {
      throw new Error('ログイン状態を維持したまま drawing ページへ遷移できませんでした。');
    }

    const clickedSelector = await clickIfVisible(page, [
      'text=図面管理',
      '[role="link"]:has-text("図面管理")',
      '[role="button"]:has-text("図面管理")',
      'a:has-text("図面管理")',
      'button:has-text("図面管理")',
    ]);

    if (clickedSelector) {
      await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => null);
      await page.waitForTimeout(2000);
    }

    const headings = await collectTextList(page, ['h1', 'h2', 'h3', '[role="heading"]']);
    const links = await collectTextList(page, ['a', 'button'], 40);
    const tables = await collectTextList(page, ['table tr', '[role="row"]'], 30);
    const bodyText = (await page.locator('body').innerText()).replace(/\s+/g, ' ').trim();

    await page.screenshot({ path: screenshotPath, fullPage: true });

    const summary = {
      url: page.url(),
      title: await page.title(),
      clickedSelector,
      headings,
      links,
      tables,
      bodyPreview: bodyText.slice(0, 1500),
      screenshotPath,
    };

    fs.writeFileSync(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
    console.log(JSON.stringify(summary, null, 2));

    await page.waitForTimeout(15000);
  } finally {
    await context.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
