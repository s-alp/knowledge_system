import { chromium } from "playwright";

const url = process.argv[2] ?? "http://210.165.3.139/web/chat/";
const screenshotPath =
  process.argv[3] ?? "C:/Users/s-iwata/Desktop/knowledge_system/output/rag_chat_explore.png";

const browser = await chromium.launch({ channel: "msedge", headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } });

await page.goto(url, { waitUntil: "networkidle", timeout: 120000 });
await page.screenshot({ path: screenshotPath, fullPage: true });

const summary = await page.evaluate(() => {
  const pick = (elements, mapFn) => Array.from(elements).slice(0, 30).map(mapFn);

  const inputs = pick(
    document.querySelectorAll("textarea, input, [role='textbox']"),
    (el) => ({
      tag: el.tagName,
      type: el.getAttribute("type"),
      placeholder: el.getAttribute("placeholder"),
      ariaLabel: el.getAttribute("aria-label"),
      text: el.textContent?.trim().slice(0, 120),
    }),
  );

  const buttons = pick(document.querySelectorAll("button"), (el) => ({
    text: el.textContent?.trim().slice(0, 120),
    ariaLabel: el.getAttribute("aria-label"),
    title: el.getAttribute("title"),
    disabled: el.hasAttribute("disabled"),
  }));

  const headings = pick(document.querySelectorAll("h1, h2, h3"), (el) => el.textContent?.trim());
  const mainTexts = pick(document.querySelectorAll("main, [role='main'], .App, #root"), (el) =>
    el.textContent?.trim().replace(/\s+/g, " ").slice(0, 2000),
  );

  return {
    title: document.title,
    url: location.href,
    headings,
    inputs,
    buttons,
    mainTexts,
  };
});

console.log(JSON.stringify(summary, null, 2));

await browser.close();
