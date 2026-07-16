import { chromium } from "../integrations/2D_3D_CAD_VIEWR/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs/promises";


const baseUrl = process.argv[2] ?? "http://127.0.0.1:5173/";
const outputDirectory = process.argv[3] ?? "C:/Users/s-iwata/Desktop/knowledge_system/output/entity_ui_2026-07-16";
await fs.mkdir(outputDirectory, { recursive: true });

const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 1708, height: 920 } });
page.setDefaultTimeout(30000);
const browserErrors = [];
page.on("console", (message) => {
  if (message.type() === "error" && !message.text().includes("Failed to load resource")) {
    browserErrors.push(`console: ${message.text()}`);
  }
});
page.on("pageerror", (error) => browserErrors.push(`page: ${error.message}`));
page.on("response", (response) => {
  if (response.status() >= 400 && !response.url().endsWith("/favicon.ico")) {
    browserErrors.push(`http ${response.status()}: ${response.url()}`);
  }
});

async function openFirstDetail(menuLabel, expectedTitle, screenshotName) {
  await page.locator(".sidebar-link", { hasText: menuLabel }).click();
  await page.getByRole("heading", { name: `${expectedTitle}一覧` }).waitFor();
  const row = page.locator(".production-table tbody .production-clickable-row").first();
  await row.waitFor();
  await row.click();
  await page.getByRole("heading", { name: `${expectedTitle}詳細` }).waitFor();
  await page.getByRole("heading", { name: "基本情報" }).waitFor();
  await page.screenshot({ path: `${outputDirectory}/${screenshotName}`, fullPage: true });
}

async function assertBusinessDetailSignals(expectedTitle, tagScreenshotName) {
  const tagItems = page.locator(".production-tag-list span");
  const tagCount = await tagItems.count();
  if (tagCount === 0) {
    throw new Error(`${expectedTitle}詳細に検索・分類用タグが表示されていません。`);
  }
  await page.getByRole("heading", { name: "変更履歴" }).waitFor();
  const historyRows = page.locator(".production-history-section tbody tr");
  await historyRows.first().waitFor();
  const historyText = await historyRows.first().innerText();
  if (!/\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2}/.test(historyText)) {
    throw new Error(`${expectedTitle}詳細の変更履歴に日時が表示されていません: ${historyText}`);
  }
  await page.screenshot({ path: `${outputDirectory}/${tagScreenshotName}`, fullPage: true });
}

async function verifyDrawingManagementEntry() {
  await page.locator(".sidebar-link", { hasText: "図面管理" }).click();
  await page.getByRole("heading", { name: "図面管理" }).waitFor();
  await page.getByRole("heading", { name: "ICADからタグ・属性を取得" }).waitFor();
  await page.getByLabel("ICAD原本パス").waitFor();
  const proceedButton = page.getByRole("button", { name: "タグ・属性取得へ進む" });
  await proceedButton.waitFor();
  if (!(await proceedButton.isDisabled())) {
    throw new Error("ICAD未選択の状態でタグ・属性取得へ進むボタンが有効になっています。");
  }
  await page.screenshot({ path: `${outputDirectory}/drawing-management-icad-entry.png`, fullPage: true });
}

try {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await verifyDrawingManagementEntry();

  await page.locator(".sidebar-link", { hasText: "プロジェクト" }).click();
  await page.getByRole("heading", { name: "プロジェクト詳細", level: 1 }).waitFor();
  if ((await page.getByText(/PRJ-OP30|OP30 カセット|TR1D9K99027 ブラケット/).count()) > 0) {
    throw new Error("プロジェクト画面に旧固定サンプルデータが表示されています。");
  }

  await openFirstDetail("製品・装置・ユニット", "製品・装置・ユニット", "product-detail.png");
  await assertBusinessDetailSignals("製品・装置・ユニット", "product-tags-history.png");
  await page.getByRole("heading", { name: "2D/3D照合" }).waitFor();
  await page.getByRole("columnheader", { name: "採用候補" }).waitFor();

  if ((await page.getByText("確認待ち", { exact: true }).count()) > 0) {
    throw new Error("利用者向け詳細に抽出状態『確認待ち』が表示されています。");
  }
  for (const tab of ["プロジェクト", "親製品・装置・ユニット", "子製品・装置・ユニット", "部品", "図面", "文書", "会話ログ"]) {
    await page.getByRole("tab", { name: tab, exact: true }).waitFor();
  }

  await page.getByRole("button", { name: "取得根拠を見る" }).click();
  await page.getByRole("dialog", { name: "取得元・採用根拠" }).waitFor();
  await page.getByRole("columnheader", { name: "信頼度" }).waitFor();
  await page.getByRole("columnheader", { name: "採用理由" }).waitFor();
  const provenanceDialog = page.getByRole("dialog", { name: "取得元・採用根拠" });
  if ((await provenanceDialog.getByText(/抽出結果:|確認待ち|未確認|レビュー待ち|手直し待ち/).count()) > 0) {
    throw new Error("取得根拠ダイアログに抽出レビューの内部状態が表示されています。");
  }
  await page.screenshot({ path: `${outputDirectory}/product-provenance.png`, fullPage: true });
  await page.getByRole("button", { name: "閉じる" }).click();

  await page.getByRole("tab", { name: "図面", exact: true }).click();
  await page.getByRole("button", { name: "図面を紐づける" }).click();
  await page.getByRole("dialog", { name: "図面を紐づける" }).waitFor();
  const drawingOptionCheckboxes = page.locator('.production-link-table input[type="checkbox"]');
  await drawingOptionCheckboxes.first().waitFor();
  const drawingOptionCount = await drawingOptionCheckboxes.count();
  if (drawingOptionCount === 0) {
    throw new Error("図面紐づけ候補が1件も取得できませんでした。");
  }
  await page.screenshot({ path: `${outputDirectory}/product-drawing-link.png`, fullPage: true });
  await page.getByRole("button", { name: "閉じる" }).click();

  await page.getByRole("button", { name: "編集" }).click();
  await page.getByRole("dialog", { name: "登録情報を編集" }).waitFor();
  await page.getByLabel("製品・装置・ユニット名").waitFor();
  await page.screenshot({ path: `${outputDirectory}/product-edit.png`, fullPage: true });
  await page.getByRole("button", { name: "閉じる" }).click();

  await openFirstDetail("部品", "部品", "part-detail.png");
  await assertBusinessDetailSignals("部品", "part-tags-history.png");
  await page.getByRole("heading", { name: "2D/3D照合" }).waitFor();
  await page.getByRole("columnheader", { name: "採用候補" }).waitFor();
  for (const tab of ["製品・装置・ユニット", "図面", "文書", "会話ログ"]) {
    await page.getByRole("tab", { name: tab, exact: true }).waitFor();
  }
  await page.getByRole("button", { name: "取得根拠を見る" }).click();
  await page.getByRole("dialog", { name: "取得元・採用根拠" }).waitFor();
  const partProvenanceDialog = page.getByRole("dialog", { name: "取得元・採用根拠" });
  if ((await partProvenanceDialog.getByText(/抽出結果:|確認待ち|未確認|レビュー待ち|手直し待ち/).count()) > 0) {
    throw new Error("部品の取得根拠ダイアログに抽出レビューの内部状態が表示されています。");
  }
  await page.getByRole("button", { name: "閉じる" }).click();
  await page.getByRole("button", { name: "編集" }).click();
  await page.getByRole("dialog", { name: "登録情報を編集" }).waitFor();
  await page.getByLabel("部品番号").waitFor();
  await page.screenshot({ path: `${outputDirectory}/part-edit.png`, fullPage: true });
  await page.getByRole("button", { name: "閉じる" }).click();

  await page.locator(".sidebar-link", { hasText: "システム設定" }).click();
  await page.getByRole("heading", { name: "ICADタグ・属性管理" }).waitFor();
  await page.locator(".settings-management-link", { hasText: "API仕様・連携仕様" }).click();
  await page.getByRole("heading", { name: "API仕様・連携仕様" }).waitFor();
  await page.getByText(/対象範囲: 固定manifest/).waitFor();
  await page.getByText("登録図面").waitFor();
  await page.getByText("/api/v1/drawing-metadata/handoff-summary").waitFor();
  await page.getByText(/\/api\/v1\/drawings\//).first().waitFor();
  if ((await page.getByText(/ユーザー画面には表示しません|通常画面へ出さず/).count()) > 0) {
    throw new Error("システム設定に旧説明文言が表示されています。");
  }
  if (page.url().includes("/drawing-metadata/")) {
    throw new Error(`システム設定から旧Django画面へ遷移しています: ${page.url()}`);
  }
  await page.screenshot({ path: `${outputDirectory}/system-settings.png`, fullPage: true });
  await page.locator(".settings-management-link", { hasText: "ICAD抽出管理" }).click();
  await page.getByRole("heading", { name: "ICAD抽出管理" }).waitFor();
  await page.getByRole("columnheader", { name: "ICADファイル" }).waitFor();
  await page.getByRole("columnheader", { name: "snapshot" }).waitFor();
  if (page.url().includes("/drawing-metadata/")) {
    throw new Error(`ICAD抽出管理から旧Django画面へ遷移しています: ${page.url()}`);
  }

  const result = {
    baseUrl,
    projectPlaceholderVerified: true,
    productAndPartDetailsVerified: true,
    provenanceVerified: true,
    reconciliationVerified: true,
    drawingLinkScreenVerified: true,
    drawingLinkOptionCount: drawingOptionCount,
    editFormsVerified: true,
    drawingManagementIcadEntryVerified: true,
    businessTagsVerified: true,
    historyTimestampVerified: true,
    systemSettingsVerified: true,
    extractionReviewHiddenFromBusinessStatus: true,
    browserErrors,
  };
  await fs.writeFile(`${outputDirectory}/result.json`, JSON.stringify(result, null, 2), "utf8");
  if (browserErrors.length) throw new Error(browserErrors.join("\n"));
  console.log(JSON.stringify(result, null, 2));
} finally {
  await Promise.race([
    browser.close(),
    new Promise((resolve) => setTimeout(resolve, 3000)),
  ]);
}
process.exit(0);
