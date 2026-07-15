const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const { createRequire } = require("node:module");

const frontendRequire = createRequire(path.resolve(__dirname, "..", "frontend", "package.json"));
const { chromium } = frontendRequire("playwright");

async function main() {
  const uploadKind = process.env.CHECK_FRONTEND_UPLOAD_KIND === "3d" ? "3d" : "2d";
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "viewer-local-upload-"));
  const filePath =
    uploadKind === "2d" ? path.join(tempDir, "sample.pdf") : path.join(tempDir, "sample.stl");
  if (uploadKind === "2d") {
    fs.writeFileSync(filePath, "%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n", "utf8");
  } else {
    fs.writeFileSync(
      filePath,
      [
        "solid sample",
        "facet normal 0 0 1",
        "outer loop",
        "vertex 0 0 0",
        "vertex 1 0 0",
        "vertex 0 1 0",
        "endloop",
        "endfacet",
        "endsolid sample",
      ].join("\n"),
      "utf8",
    );
  }

  const browser = await chromium.launch({ channel: "msedge", headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  const networkLog = [];

  page.on("response", async (response) => {
    const url = response.url();
    if (!url.includes("/api/v1/")) {
      return;
    }

    let bodyText = "";
    try {
      bodyText = await response.text();
    } catch {
      bodyText = "";
    }

    networkLog.push({
      url,
      status: response.status(),
      body: bodyText.slice(0, 400),
    });
  });

  try {
    await page.goto("http://localhost:5173/", { waitUntil: "networkidle", timeout: 30000 });
    await page.locator('input[type="file"]').setInputFiles(filePath);
    await page.waitForTimeout(4000);

    const bodyText = (await page.locator("body").innerText()).replace(/\s+/g, " ").trim();
    const screenshotPath = path.resolve(__dirname, "..", "runtime", "frontend-local-upload-check.png");
    await fs.promises.mkdir(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath, fullPage: true });

    console.log(
      JSON.stringify(
        {
          uploadKind,
          url: page.url(),
          bodyPreview: bodyText.slice(0, 1200),
          networkLog,
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
  process.exitCode = 1;
});
