const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');

const frontendRequire = createRequire(path.resolve(__dirname, '..', 'frontend', 'package.json'));
const { chromium } = frontendRequire('playwright');

const drawingUrl = process.env.PLAYWRIGHT_DRAWING_URL || 'http://210.165.3.139/web/drawing';
const runtimeDir = path.resolve(__dirname, '..', 'runtime');
const userDataDir = path.join(runtimeDir, 'playwright-edge-profile');
const screenshotPath = path.join(runtimeDir, 'drawing-page.png');
const summaryPath = path.join(runtimeDir, 'drawing-page-summary.json');

fs.mkdirSync(runtimeDir, { recursive: true });

async function collectTextList(page, selectors, limit = 30) {
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
    return await emailInput.isVisible({ timeout: 1000 });
  } catch {
    return false;
  }
}

async function main() {
  const context = await chromium.launchPersistentContext(userDataDir, {
    channel: 'msedge',
    headless: false,
    slowMo: 100,
    viewport: { width: 1440, height: 960 },
  });

  const page = context.pages()[0] || await context.newPage();

  try {
    await page.goto(drawingUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => null);
    await page.waitForTimeout(3000);

    if (await isLoginFormVisible(page)) {
      throw new Error('保存済みセッションで drawing に入れず、ログイン画面に戻されました。');
    }

    const headings = await collectTextList(page, ['h1', 'h2', 'h3', '[role="heading"]']);
    const buttonsAndLinks = await collectTextList(page, ['button', 'a', '[role="button"]'], 50);
    const rows = await collectTextList(page, ['table tr', '[role="row"]', 'li'], 50);
    const bodyText = (await page.locator('body').innerText()).replace(/\s+/g, ' ').trim();

    const summary = {
      url: page.url(),
      title: await page.title(),
      headings,
      buttonsAndLinks,
      rows,
      bodyPreview: bodyText.slice(0, 2000),
      screenshotPath,
    };

    await page.screenshot({ path: screenshotPath, fullPage: true });
    fs.writeFileSync(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
    console.log(JSON.stringify(summary, null, 2));

    await page.waitForTimeout(5000);
  } finally {
    await context.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
