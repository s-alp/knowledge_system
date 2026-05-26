// knowledge-system-screenshot - Playwright auto-capture for Cowork
const path = require('path');
const fs = require('fs');

const SKILL_DIR   = process.env.KS_SKILL_DIR || __dirname;
const RUNTIME_DIR = '/tmp/ks-screenshot';

// Tiny .env loader
(() => {
  const envPath = path.join(SKILL_DIR, '.env');
  if (!fs.existsSync(envPath)) return;
  for (const raw of fs.readFileSync(envPath, 'utf8').split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const m = line.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!m) continue;
    let val = m[2];
    if ((val.startsWith('"') && val.endsWith('"')) ||
        (val.startsWith("'") && val.endsWith("'"))) val = val.slice(1, -1);
    if (!(m[1] in process.env)) process.env[m[1]] = val;
  }
})();

const playwrightPath = path.join(RUNTIME_DIR, 'node_modules', 'playwright');
if (!fs.existsSync(playwrightPath)) {
  console.error('[ERROR] Playwright not installed. Run: bash setup.sh');
  process.exit(1);
}
const { chromium } = require(playwrightPath);

const ID    = process.env.KNOW_ID || '';
const PW    = process.env.KNOW_PW || '';
const BASE  = (process.env.KNOW_BASE_URL || 'http://210.165.3.139/web').replace(/\/+$/, '');
const SAVE  = path.join(SKILL_DIR, 'screenshots');

if (!ID || !PW) {
  console.error('[ERROR] KNOW_ID / KNOW_PW not set in .env');
  process.exit(1);
}
if (!fs.existsSync(SAVE)) fs.mkdirSync(SAVE, { recursive: true });

const pages = [
  [BASE + '/',                       '01_home.png',           null],
  [BASE + '/chat',                   '02_ai_search.png',      null],
  [BASE + '/drawing/similar_search', '03_similar_search.png', null],
  [BASE + '/drawing',                '04_drawings.png',       null],
  [BASE + '/product',                '05_products.png',       null],
  [BASE + '/system_setting',         '06_workflow.png',       null],
  [BASE + '/system_setting',         '07_crawl.png',          'クロール設定'],
];

async function main() {
  console.log('[INFO] BASE = ' + BASE);
  console.log('[INFO] OUT  = ' + SAVE);
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  console.log('[STEP] Opening base URL...');
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2500);

  const onLogin = await page.locator('input[type="password"]').first().isVisible().catch(() => false);
  if (onLogin) {
    console.log('[STEP] Login form detected, signing in...');
    await page.locator('input').first().fill(ID);
    await page.locator('input[type="password"]').first().fill(PW);
    await Promise.race([
      page.locator('button[type="submit"]').first().click().catch(() => {}),
      page.getByRole('button', { name: /ログイン|サインイン|Login/i }).click().catch(() => {}),
    ]);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(2000);
    console.log('[STEP] After login URL: ' + page.url());
  } else {
    console.log('[STEP] Already authenticated.');
  }

  for (const [url, fn, clickLabel] of pages) {
    console.log('[CAPTURE] -> ' + url + '  (' + fn + ')');
    await page.goto(url, { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(3000);
    if (clickLabel) {
      try {
        await page.getByText(clickLabel, { exact: true }).click({ timeout: 5000 });
        await page.waitForTimeout(2500);
      } catch (e) {
        console.warn('[WARN] click skipped: ' + e.message.slice(0, 80));
      }
    }
    await page.screenshot({ path: path.join(SAVE, fn), fullPage: false });
    console.log('[CAPTURE]    saved ' + fn);
  }

  await browser.close();
  console.log('[DONE] Screenshots saved to: ' + SAVE);
}

main().catch(function (err) {
  console.error('[FATAL] ' + err.message);
  console.error(err.stack);
  process.exit(1);
});
