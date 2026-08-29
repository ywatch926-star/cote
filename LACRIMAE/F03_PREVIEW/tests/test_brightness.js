const puppeteer = require("puppeteer-core");
const fs = require("fs");
const path = require("path");

const URL = "http://localhost:5173/";
const DL_DIR = "/tmp/opencode/downloads";

(async () => {
  fs.rmSync(DL_DIR, { recursive: true, force: true });
  fs.mkdirSync(DL_DIR, { recursive: true });

  const browser = await puppeteer.launch({
    executablePath: "/usr/bin/chromium",
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    headless: "new",
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 1000 });
  const cdp = await page.createCDPSession();
  await cdp.send("Browser.setDownloadBehavior", { behavior: "allow", downloadPath: DL_DIR });

  let pass = true;
  const fail = (m) => { console.log("FAIL:", m); pass = false; };

  await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForSelector('div[title*="Double-cliquez"]', { timeout: 20000 });
  try {
    await page.waitForFunction(() => {
      const v = document.querySelector("video");
      return v && v.readyState >= 2;
    }, { timeout: 8000 });
  } catch (e) {
    console.log("   (video pas prête — ignoré, test UI uniquement)");
  }
  await new Promise((r) => setTimeout(r, 1500));

  await page.evaluate(() => {
    const tab = [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Effets"));
    if (tab) tab.click();
  });
  await new Promise((r) => setTimeout(r, 300));

  // 1) Défauts
  const def = await page.evaluate(() => {
    const lab = [...document.querySelectorAll("label")].find((l) => l.textContent.includes("Luminosité:"));
    const inp = lab ? lab.nextElementSibling : null;
    const els = [...document.querySelectorAll("div")].filter((d) => d.style && d.style.filter && d.style.filter.includes("contrast"));
    return { label: lab ? lab.textContent.trim() : "n/a", lum: inp ? inp.value : null, filter: els.length ? els[els.length - 1].style.filter : "AUCUN" };
  });
  console.log("1) défauts :", JSON.stringify(def));
  if (!def.label.includes("1.10")) fail("label luminosité défaut != 1.10");
  if (def.lum !== "1.1") fail("slider luminosité défaut != 1.1");
  if (!def.filter.includes("brightness(1.1)")) fail(`filtre initial sans brightness(1.1): ${def.filter}`);

  // 2) Monter luminosité à 1.6 (via le slider suivant le label "Luminosité:")
  await page.evaluate(() => {
    const lab = [...document.querySelectorAll("label")].find((l) => l.textContent.includes("Luminosité:"));
    const inp = lab ? lab.nextElementSibling : null;
    if (!inp) return;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    setter.call(inp, "1.6");
    inp.dispatchEvent(new Event("input", { bubbles: true }));
    inp.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await new Promise((r) => setTimeout(r, 500));

  const after = await page.evaluate(() => {
    const lab = [...document.querySelectorAll("label")].find((l) => l.textContent.includes("Luminosité:"));
    const els = [...document.querySelectorAll("div")].filter((d) => d.style && d.style.filter && d.style.filter.includes("contrast"));
    return { label: lab ? lab.textContent.trim() : "n/a", filter: els.length ? els[els.length - 1].style.filter : "AUCUN" };
  });
  console.log("2) après slider :", JSON.stringify(after));
  if (!after.label.includes("1.60")) fail("label non mis à jour à 1.60");
  if (!after.filter.includes("brightness(1.6)")) fail(`filtre non mis à jour: ${after.filter}`);

  // 3) Export codex
  await page.evaluate(() => {
    const btn = [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Télécharger codex.json"));
    if (btn) btn.click();
  });
  await new Promise((r) => setTimeout(r, 1500));
  const dl = fs.existsSync(DL_DIR) ? fs.readdirSync(DL_DIR) : [];
  if (!dl.length) fail("codex.json non téléchargé");
  else {
    const codex = JSON.parse(fs.readFileSync(path.join(DL_DIR, dl[0]), "utf8"));
    const b = codex.session?.presets?.brightness;
    const c = codex.session?.presets?.contrast;
    console.log("3) export presets : brightness =", b, ", contrast =", c);
    if (b !== 1.6) fail(`brightness attendu 1.6, reçu ${b}`);
    if (c !== 1.3) fail(`contrast doit rester 1.3, reçu ${c}`);
  }

  console.log(pass ? "\n=== PASS ===" : "\n=== FAIL ===");
  await browser.close();
  process.exit(pass ? 0 : 1);
})();
