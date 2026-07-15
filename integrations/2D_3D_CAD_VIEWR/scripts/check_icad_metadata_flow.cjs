const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(path.join(__dirname, "..", "frontend", "node_modules", "playwright"));

async function main() {
  const probePath = path.join(process.env.TEMP || "C:\\TMP", "browser_icad_probe.icd");
  fs.writeFileSync(probePath, "browser-probe", "utf8");

  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(15000);
    const browserErrors = [];
    page.on("console", (message) => {
      if (message.type() === "error" && !message.location().url.endsWith("/favicon.ico")) {
        browserErrors.push({ text: message.text(), location: message.location() });
      }
    });
    page.on("pageerror", (error) => browserErrors.push({ text: error.message, location: null }));
    console.log("page-open");
    await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded", timeout: 15000 });
    console.log("file-select");
    await page.setInputFiles('input[type="file"][accept=".icd"]', probePath, { timeout: 15000 });
    console.log("metadata-launch");
    await page.getByRole("button", { name: "タグ・属性取得へ進む" }).click({ timeout: 15000 });
    await page.waitForSelector("text=ICADタグ・属性取得");
    await page.waitForSelector("text=登録しました。抽出開始または条件付き再抽出を実行できます。");
    console.log("review-ready");

    const screenshotPath = path.resolve(
      __dirname,
      "..",
      "..",
      "..",
      "output",
      "knowledge_ui_screenshots_2026-07-15",
      "icad-extraction-review-current-2026-07-15.png",
    );
    await page.screenshot({ path: screenshotPath, fullPage: true });

    const body = await page.locator("body").innerText();
    const result = {
      hasReview: body.includes("レビュー"),
      hasReextract: body.includes("抽出・再抽出") && body.includes("再抽出"),
      hasManual: body.includes("手直し"),
      hasSystemTitle: body.includes("タグ自動取得設定"),
    };

    await page.getByRole("button", { name: "図面管理に戻る" }).click();
    await page.waitForSelector("text=図面を開く");
    const afterBackBody = await page.locator("body").innerText();
    const afterBackUrl = page.url();

    console.log(
      JSON.stringify(
        {
          ...result,
          afterBackUrl,
          hasDrawingOpen: afterBackBody.includes("図面を開く"),
          browserErrors,
          screenshotPath,
        },
        null,
        2,
      ),
    );
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
