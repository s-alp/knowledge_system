import { chromium } from "playwright";
import fs from "node:fs/promises";

const url = process.argv[2] ?? "http://210.165.3.139/web/chat";
const outJson =
  process.argv[3] ??
  "C:/Users/s-iwata/Desktop/knowledge_system/output/playwright_rag_probe.json";
const outShot =
  process.argv[4] ??
  "C:/Users/s-iwata/Desktop/knowledge_system/output/playwright_rag_probe.png";

const browser = await chromium.launch({
  channel: "msedge",
  headless: false,
  args: [
    "--auth-server-whitelist=210.165.3.139",
    "--auth-negotiate-delegate-whitelist=210.165.3.139",
  ],
});

const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
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
console.log(JSON.stringify(summary, null, 2));

await browser.close();
