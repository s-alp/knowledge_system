const path = require("node:path");
const { chromium } = require(path.join(
  process.cwd(),
  "integrations",
  "2D_3D_CAD_VIEWR",
  "frontend",
  "node_modules",
  "playwright",
));

function hasSecretKeyField(value) {
  if (!value || typeof value !== "object") {
    return false;
  }
  return Object.entries(value).some(([key, child]) => {
    const normalized = key.replace(/[^a-z]/gi, "").toLowerCase();
    return normalized === "apikey" || normalized === "geminiapikey" || hasSecretKeyField(child);
  });
}

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(15000);
    const browserErrors = [];
    const ignoredAssetErrors = [];
    const failedResponses = [];
    page.on("console", (message) => {
      if (message.type() === "error") {
        const error = { text: message.text(), location: message.location() };
        if (error.location.url.endsWith("/favicon.ico")) {
          ignoredAssetErrors.push(error);
        } else {
          browserErrors.push(error);
        }
      }
    });
    page.on("pageerror", (error) => browserErrors.push({ text: error.message, location: null }));
    page.on("response", (response) => {
      if (response.status() >= 400) {
        failedResponses.push({ status: response.status(), url: response.url() });
      }
    });

    await page.goto("http://127.0.0.1:5173/", {
      waitUntil: "domcontentloaded",
      timeout: 15000,
    });
    const settingsResponsePromise = page.waitForResponse(
      (response) =>
        response.request().method() === "GET" && response.url().includes("drawing-metadata/settings/tag-automation"),
    );
    await page.getByRole("button", { name: "システム設定" }).click();
    const settingsResponse = await settingsResponsePromise;
    const apiResponse = await settingsResponse.json();
    await page.getByRole("heading", { name: "タグ自動取得設定" }).waitFor();
    await page.getByText("Gemini APIキー").waitFor();
    await page.getByText("設定済み", { exact: true }).waitFor();

    const body = await page.locator("body").innerText();
    const serializedResponse = JSON.stringify(apiResponse);
    const screenshotPath = path.join(
      process.cwd(),
      "output",
      "knowledge_ui_screenshots_2026-07-15",
      "tag-automation-settings-current-2026-07-15.png",
    );
    await page.screenshot({ path: screenshotPath, fullPage: true });

    console.log(
      JSON.stringify(
        {
          hasConfiguredStatus: body.includes("設定済み"),
          hasTemperatureZero: body.includes("温度") && body.includes("0.0"),
          hasDatabaseBoundary: body.includes("登録・変更・削除は行わず"),
          hasReviewActions: body.includes("候補を確定") || body.includes("要手直し"),
          exposesApiKeyField: hasSecretKeyField(apiResponse),
          exposesGeminiKeyPrefix: serializedResponse.includes("AIza"),
          browserErrors,
          ignoredAssetErrors,
          failedResponses,
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
