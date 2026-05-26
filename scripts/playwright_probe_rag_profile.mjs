import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";

const sourceUserDataDir = "C:/Users/s-iwata/AppData/Local/Microsoft/Edge/User Data";
const profileName = "Default";
const url = process.argv[2] ?? "http://210.165.3.139/web/chat";
const outJson =
  process.argv[3] ??
  "C:/Users/s-iwata/Desktop/knowledge_system/output/playwright_rag_profile_probe.json";
const outShot =
  process.argv[4] ??
  "C:/Users/s-iwata/Desktop/knowledge_system/output/playwright_rag_profile_probe.png";

const tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), "edge-playwright-profile-"));
const tempUserDataDir = path.join(tempRoot, "User Data");
const tempProfileDir = path.join(tempUserDataDir, profileName);

const copyIfExists = async (src, dest) => {
  try {
    await fs.cp(src, dest, { recursive: true, force: true });
  } catch (error) {
    console.error(`copy failed: ${src}: ${error.message}`);
  }
};

await fs.mkdir(tempProfileDir, { recursive: true });
await copyIfExists(path.join(sourceUserDataDir, "Local State"), path.join(tempUserDataDir, "Local State"));
await copyIfExists(path.join(sourceUserDataDir, profileName, "Preferences"), path.join(tempProfileDir, "Preferences"));
await copyIfExists(path.join(sourceUserDataDir, profileName, "Secure Preferences"), path.join(tempProfileDir, "Secure Preferences"));
await copyIfExists(path.join(sourceUserDataDir, profileName, "Network"), path.join(tempProfileDir, "Network"));
await copyIfExists(path.join(sourceUserDataDir, profileName, "Local Storage"), path.join(tempProfileDir, "Local Storage"));
await copyIfExists(path.join(sourceUserDataDir, profileName, "Session Storage"), path.join(tempProfileDir, "Session Storage"));
await copyIfExists(path.join(sourceUserDataDir, profileName, "IndexedDB"), path.join(tempProfileDir, "IndexedDB"));

const context = await chromium.launchPersistentContext(tempUserDataDir, {
  channel: "msedge",
  headless: false,
  args: [
    "--auth-server-whitelist=210.165.3.139",
    "--auth-negotiate-delegate-whitelist=210.165.3.139",
  ],
  viewport: { width: 1440, height: 1200 },
});

const page = context.pages()[0] ?? (await context.newPage());
page.setDefaultTimeout(120000);

await page.goto(url, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(8000);

const summary = await page.evaluate(() => {
  const text = (el) => (el?.textContent || "").replace(/\s+/g, " ").trim();
  const inputs = Array.from(document.querySelectorAll("textarea, input, [role='textbox']")).map(
    (el) => ({
      tag: el.tagName,
      type: el.getAttribute("type"),
      placeholder: el.getAttribute("placeholder"),
      ariaLabel: el.getAttribute("aria-label"),
      text: text(el).slice(0, 200),
      disabled: el.matches(":disabled"),
    }),
  );
  const buttons = Array.from(document.querySelectorAll("button")).map((el) => ({
    text: text(el).slice(0, 200),
    ariaLabel: el.getAttribute("aria-label"),
    title: el.getAttribute("title"),
    disabled: el.matches(":disabled"),
  }));
  return {
    title: document.title,
    url: location.href,
    bodyText: text(document.body).slice(0, 4000),
    inputs,
    buttons,
  };
});

await page.screenshot({ path: outShot, fullPage: true });
await fs.writeFile(outJson, JSON.stringify(summary, null, 2), "utf8");
console.log(JSON.stringify({ tempUserDataDir, summary }, null, 2));

await context.close();
