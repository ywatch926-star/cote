const puppeteer = require("puppeteer-core");
const fs = require("fs");
const path = require("path");

const URL = "http://localhost:5173/";
const DL_DIR = "/tmp/opencode/downloads";
const X = 0.7;
const Y = 0.3;
const TOL = 2;

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
  await cdp.send("Browser.setDownloadBehavior", {
    behavior: "allow",
    downloadPath: DL_DIR,
    eventsEnabled: true,
  });

  const errors = [];
  page.on("pageerror", (e) => errors.push("[pageerror] " + e.message));
  page.on("response", (r) => {
    if (r.status() >= 400) errors.push("[" + r.status() + "] " + r.url().replace(/^.*localhost:5173/, ""));
  });

  let pass = true;
  const fail = (m) => { console.log("FAIL:", m); pass = false; };

  await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForSelector('div[title*="Double-cliquez"]', { timeout: 20000 });
  await page.waitForSelector("video", { timeout: 20000 });
  await new Promise((r) => setTimeout(r, 2500));

  const rect = await page.evaluate(() => {
    const container = document.querySelector('div[title*="Double-cliquez"]');
    const wrapper = container.firstElementChild;
    const r = wrapper.getBoundingClientRect();
    return { x: r.x, y: r.y, w: r.width, h: r.height };
  });
  console.log("wrapper rect:", JSON.stringify(rect));

  const cx = rect.x + rect.w * X;
  const cy = rect.y + rect.h * Y;

  await page.mouse.move(cx, cy);
  await page.mouse.click(cx, cy);
  await new Promise((r) => setTimeout(r, 80));
  await page.mouse.click(cx, cy);

  await page.waitForFunction(
    () => document.body.innerText.includes("Poser le logo ici ?"),
    { timeout: 5000 }
  );
  console.log("1) modal ouverte: OK");

  const marker = await page.evaluate(() => {
    const container = document.querySelector('div[title*="Double-cliquez"]');
    const wrapper = container.firstElementChild;
    const cands = [...wrapper.querySelectorAll("div")].filter((d) => {
      const s = d.style;
      return (
        s.position === "absolute" &&
        /%$/.test(s.left) && /%$/.test(s.top) &&
        s.zIndex === "30"
      );
    });
    if (!cands.length) return null;
    const m = cands[cands.length - 1];
    return { x: parseFloat(m.style.left), y: parseFloat(m.style.top) };
  });
  console.log("2) marqueur:", JSON.stringify(marker));
  if (!marker) fail("marqueur absent");
  else if (Math.abs(marker.x - X * 100) > TOL || Math.abs(marker.y - Y * 100) > TOL)
    fail(`marqueur décalé ${JSON.stringify(marker)} vs ${X * 100}/${Y * 100}`);

  await page.screenshot({ path: "/tmp/opencode/fix_modal.png" });

  await page.evaluate(() => {
    const btn = [...document.querySelectorAll("button")].find((b) => b.textContent.trim() === "Oui");
    if (btn) btn.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  await page.evaluate(() => {
    const tab = [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Fond & Logo"));
    if (tab) tab.click();
  });
  await new Promise((r) => setTimeout(r, 400));

  const selectValue = await page.evaluate(() => {
    const sel = [...document.querySelectorAll("select")].find((s) =>
      [...s.options].some((o) => o.value === "custom")
    );
    return sel ? sel.value : "n/a";
  });
  console.log("3) select position après Oui:", selectValue);
  if (selectValue !== "custom") fail(`select=${selectValue} attendu=custom`);
  else console.log("   select custom: OK");

  await page.evaluate(() => {
    const btn = [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Télécharger codex.json"));
    if (btn) btn.click();
  });
  await new Promise((r) => setTimeout(r, 1500));
  const dlFiles = fs.existsSync(DL_DIR) ? fs.readdirSync(DL_DIR) : [];
  console.log("4) fichiers téléchargés:", dlFiles.join(", "));
  if (dlFiles.length === 0) {
    fail("codex.json non téléchargé");
  } else {
    const codex = JSON.parse(fs.readFileSync(path.join(DL_DIR, dlFiles[0]), "utf8"));
    const logo = codex.session?.logo;
    console.log("   session.logo exporté:", JSON.stringify(logo));
    if (!logo || logo.position !== "custom")
      fail("position non custom dans le codex exporté");
    else console.log("   position custom: OK");
    if (Math.abs((logo.x_pct || 0) - X * 100) > TOL || Math.abs((logo.y_pct || 0) - Y * 100) > TOL)
      fail(`coordonnées exportées ${logo.x_pct}/${logo.y_pct} vs ${X * 100}/${Y * 100}`);
    else console.log("   coordonnées exactes: OK");
  }

  await page.screenshot({ path: "/tmp/opencode/fix_result.png" });
  const realErrors = errors.filter((e) => !e.includes("/favicon.ico"));
  if (realErrors.length) {
    console.log("HTTP/JS problèmes:", realErrors.join("\n"));
    fail("problèmes réseau/JS");
  }

  console.log(pass ? "\n=== PASS: balise corrigée ===" : "\n=== FAIL ===");
  await browser.close();
  process.exit(pass ? 0 : 1);
})();
