const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(path.join(process.cwd(), "node_modules", "playwright"));

async function main() {
  const probePath = path.join(process.env.TEMP || "C:\\TMP", "browser_icad_probe.icd");
  fs.writeFileSync(probePath, "browser-probe", "utf8");

  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage();
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
  await page.setInputFiles('input[type="file"][accept=".icd"]', probePath);
  await page.getByRole("button", { name: "タグ・属性取得へ進む" }).click();
  await page.waitForSelector("text=ICADタグ・属性取得", { timeout: 15000 });
  await page.waitForSelector("text=登録しました。抽出開始または条件付き再抽出を実行できます。", {
    timeout: 15000,
  });

  const body = await page.locator("body").innerText();
  const result = {
    hasReview: body.includes("レビュー"),
    hasReextract: body.includes("抽出・再抽出") && body.includes("再抽出"),
    hasManual: body.includes("手直し"),
    hasSystemTitle: body.includes("タグ自動取得設定"),
  };

  await page.getByRole("button", { name: "図面管理に戻る" }).click();
  await page.waitForSelector("text=図面を開く", { timeout: 10000 });
  const afterBackBody = await page.locator("body").innerText();

  await browser.close();
  console.log(
    JSON.stringify(
      {
        ...result,
        afterBackUrl: page.url(),
        hasDrawingOpen: afterBackBody.includes("図面を開く"),
      },
      null,
      2,
    ),
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
