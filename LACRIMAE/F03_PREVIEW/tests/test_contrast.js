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
  await page.waitForFunction(() => {
    const v = document.querySelector("video");
    return v && v.readyState >= 2;
  }, { timeout: 20000 });
  await new Promise((r) => setTimeout(r, 2000));

  // Onglet Effets
  await page.evaluate(() => {
    const tab = [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Effets"));
    if (tab) tab.click();
  });
  await new Promise((r) => setTimeout(r, 300));

  // 1) Valeur par défaut du slider contraste
  const def = await page.evaluate(() => {
    const lab = [...document.querySelectorAll("label")].find((l) => l.textContent.includes("Contraste:"));
    const inp = [...document.querySelectorAll('input[type="range"]')].find((i) => i.min === "0.5" && i.max === "2");
    return { label: lab ? lab.textContent.trim() : "n/a", slider: inp ? inp.value : null };
  });
  console.log("1) défaut contraste :", JSON.stringify(def));
  if (!def.label || !def.label.includes("1.30")) fail("label défaut != 1.30");
  if (def.slider !== "1.3") fail(`slider défaut != 1.3 (reçu ${def.slider})`);

  // Filtre appliqué sur la scène au chargement
  const filterBefore = await page.evaluate(() => {
    const els = [...document.querySelectorAll("div")].filter((d) => d.style && d.style.filter && d.style.filter.includes("contrast"));
    return els.length ? els[els.length - 1].style.filter : "AUCUN";
  });
  console.log("   filtre scène :", filterBefore);
  if (!filterBefore.includes("contrast(1.3)")) fail("filtre initial sans contrast(1.3)");

  // 2) Monter le slider à 1.75
  await page.evaluate(() => {
    const inp = [...document.querySelectorAll('input[type="range"]')].find((i) => i.min === "0.5" && i.max === "2");
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    setter.call(inp, "1.75");
    inp.dispatchEvent(new Event("input", { bubbles: true }));
    inp.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await new Promise((r) => setTimeout(r, 500));

  const after = await page.evaluate(() => {
    const lab = [...document.querySelectorAll("label")].find((l) => l.textContent.includes("Contraste:"));
    const els = [...document.querySelectorAll("div")].filter((d) => d.style && d.style.filter && d.style.filter.includes("contrast"));
    return { label: lab ? lab.textContent.trim() : "n/a", filter: els.length ? els[els.length - 1].style.filter : "AUCUN" };
  });
  console.log("2) après slider :", JSON.stringify(after));
  if (!after.label.includes("1.75")) fail("label non mis à jour à 1.75");
  if (!after.filter.includes("contrast(1.75)")) fail(`filtre non mis à jour: ${after.filter}`);

  // 3) Export codex : presets.contrast persisté
  await page.evaluate(() => {
    const btn = [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Télécharger codex.json"));
    if (btn) btn.click();
  });
  await new Promise((r) => setTimeout(r, 1500));
  const dl = fs.existsSync(DL_DIR) ? fs.readdirSync(DL_DIR) : [];
  if (!dl.length) fail("codex.json non téléchargé");
  else {
    const codex = JSON.parse(fs.readFileSync(path.join(DL_DIR, dl[0]), "utf8"));
    const c = codex.session?.presets?.contrast;
    console.log("3) presets.contrast exporté :", c);
    if (c !== 1.75) fail(`presets.contrast attendu 1.75, reçu ${c}`);
  }

  await page.screenshot({ path: "/tmp/opencode/fix_contrast.png" });
  console.log(pass ? "\n=== PASS ===" : "\n=== FAIL ===");
  await browser.close();
  process.exit(pass ? 0 : 1);
})();
