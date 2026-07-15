const fs = require("node:fs");
const path = require("node:path");
const viewerRoot = path.resolve(__dirname, "..");
const { chromium } = require(path.join(viewerRoot, "frontend", "node_modules", "playwright"));


async function openEntityList(page, label) {
  console.error(`open-list:${label}`);
  await page.getByRole("button", { name: label, exact: true }).click();
  await page.getByRole("heading", { name: `${label}一覧`, exact: true }).waitFor({ timeout: 30000 });
  await page.locator(".entity-list-page tbody tr.production-clickable-row").first().waitFor({ timeout: 60000 });
  console.error(`list-ready:${label}`);
}


async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const browserErrors = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));

  await page.goto("http://127.0.0.1:5173/", { waitUntil: "domcontentloaded" });
  console.error("page-ready");

  await openEntityList(page, "製品・装置・ユニット");
  const productRows = page.locator(".entity-list-page tbody tr.production-clickable-row");
  const productRowCount = await productRows.count();
  const firstProductName = (await productRows.first().locator("td").nth(1).innerText()).trim();
  await productRows.first().click();
  console.error("product-clicked");
  await page.getByRole("heading", { name: "製品・装置・ユニット詳細", exact: true }).waitFor({ timeout: 60000 });
  console.error("product-detail-ready");
  const productDetailBody = await page.locator(".entity-page").innerText();

  await page.getByRole("button", { name: "← 戻る" }).click();
  console.error("product-back");
  await openEntityList(page, "部品");
  const partRows = page.locator(".entity-list-page tbody tr.production-clickable-row");
  const partRowCount = await partRows.count();
  const firstPartNumber = (await partRows.first().locator("td").nth(1).innerText()).trim();
  const firstPartName = (await partRows.first().locator("td").nth(2).innerText()).trim();
  await partRows.first().click();
  console.error("part-clicked");
  await page.getByRole("heading", { name: "部品詳細", exact: true }).waitFor({ timeout: 60000 });
  console.error("part-detail-ready");
  const partDetailBody = await page.locator(".entity-page").innerText();

  const screenshotDirectory = path.resolve(
    viewerRoot,
    "..",
    "..",
    "output",
    "knowledge_ui_screenshots_2026-07-15",
  );
  fs.mkdirSync(screenshotDirectory, { recursive: true });
  const screenshotPath = path.join(screenshotDirectory, "icad-part-detail-current-2026-07-15.png");
  await page.screenshot({ path: screenshotPath, fullPage: true });

  const result = {
    productRowCount,
    firstProductName,
    productDetailHasAssemblyType:
      productDetailBody.includes("アセンブリ") || productDetailBody.includes("サブアセンブリ"),
    productDetailHasAttributes: productDetailBody.includes("属性情報"),
    firstPartNumber,
    firstPartName,
    partRowCount,
    partDetailHasMaterial: partDetailBody.includes("材質"),
    partDetailHasTags: partDetailBody.includes("タグ"),
    partDetailHasEvidence: partDetailBody.includes("信頼度") && partDetailBody.includes("取得元"),
    partDetailHasRelations: partDetailBody.includes("関連情報"),
    browserErrors,
    screenshotPath,
  };

  console.log(JSON.stringify(result, null, 2));

  if (
    productRowCount === 0
    || partRowCount === 0
    || !result.productDetailHasAssemblyType
    || !result.partDetailHasMaterial
    || !result.partDetailHasTags
    || browserErrors.length > 0
  ) {
    await browser.close();
    process.exit(1);
  }
  await Promise.race([
    browser.close(),
    new Promise((resolve) => setTimeout(resolve, 5000)),
  ]);
  process.exit(0);
}


main().catch((error) => {
  console.error(error);
  process.exit(1);
});
