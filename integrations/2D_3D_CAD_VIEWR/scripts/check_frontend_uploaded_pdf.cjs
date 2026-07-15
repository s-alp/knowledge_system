const fs = require("node:fs");
const path = require("node:path");
const { createRequire } = require("node:module");

const frontendRequire = createRequire(path.resolve(__dirname, "..", "frontend", "package.json"));
const { chromium } = frontendRequire("playwright");

const filePath = process.env.CHECK_FRONTEND_UPLOAD_FILE;
const screenshotPath = path.resolve(__dirname, "..", "runtime", "frontend-actual-pdf-check.png");
const summaryPath = path.resolve(__dirname, "..", "runtime", "frontend-actual-pdf-check.json");
const zoomClicks = Number.parseInt(process.env.CHECK_FRONTEND_ZOOM_CLICKS ?? "0", 10);

if (!filePath) {
  throw new Error("CHECK_FRONTEND_UPLOAD_FILE is required.");
}

async function main() {
  await fs.promises.mkdir(path.dirname(screenshotPath), { recursive: true });

  const browser = await chromium.launch({ channel: "msedge", headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });

  try {
    await page.goto("http://localhost:5173/", { waitUntil: "networkidle", timeout: 30000 });
    await page.locator('input[type="file"]').setInputFiles(filePath);
    await page.waitForTimeout(3000);

    for (let index = 0; index < zoomClicks; index += 1) {
      await page.getByLabel("拡大").click();
      await page.waitForTimeout(1200);
    }

    await page.screenshot({ path: screenshotPath, fullPage: true });
    const bodyText = (await page.locator("body").innerText()).replace(/\s+/g, " ").trim();

    const summary = {
      filePath,
      zoomClicks,
      url: page.url(),
      bodyPreview: bodyText.slice(0, 1200),
      screenshotPath,
    };
    await fs.promises.writeFile(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, "utf8");
    console.log(JSON.stringify(summary, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
