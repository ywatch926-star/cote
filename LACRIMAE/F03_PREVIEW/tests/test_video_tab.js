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
  await cdp.send("Browser.setDownloadBehavior", { behavior: "allow", downloadPath: DL_DIR });

  let pass = true;
  const fail = (m) => { console.log("FAIL:", m); pass = false; };

  await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForSelector('div[title*="Double-cliquez"]', { timeout: 20000 });
  await page.waitForSelector("video", { timeout: 20000 });
  await page.waitForFunction(() => {
    const v = document.querySelector("video");
    return v && v.readyState >= 2;
  }, { timeout: 20000 });
  await new Promise((r) => setTimeout(r, 2000));

  const rect = await page.evaluate(() => {
    const c = document.querySelector('div[title*="Double-cliquez"]').firstElementChild;
    const r = c.getBoundingClientRect();
    return { x: r.x, y: r.y, w: r.width, h: r.height };
  });
  const cx = rect.x + rect.w * X, cy = rect.y + rect.h * Y;

  // 1) Balise (régression) — avec retry si la modal ne s'ouvre pas
  async function doDoubleClick() {
    await page.mouse.move(cx, cy);
    await page.mouse.click(cx, cy);
    await new Promise((r) => setTimeout(r, 80));
    await page.mouse.click(cx, cy);
  }
  let modalOk = false;
  for (let i = 0; i < 3 && !modalOk; i++) {
    await doDoubleClick();
    try {
      await page.waitForFunction(
        () => document.body.innerText.includes("Poser le logo ici ?"),
        { timeout: 4000 }
      );
      modalOk = true;
    } catch (e) {
      console.log(`   retry balise n°${i + 1}`);
    }
  }
  console.log("1) balise (modal) :", modalOk ? "OK" : "ABSENTE");
  if (!modalOk) fail("modal balise absente");
  await page.evaluate(() => {
    const b = [...document.querySelectorAll("button")].find((x) => x.textContent.trim() === "Oui");
    if (b) b.click();
  });
  await new Promise((r) => setTimeout(r, 600));

  // 2) Onglet Vidéo + slider offset_y
  await page.evaluate(() => {
    const tab = [...document.querySelectorAll("button")].find((b) => b.textContent.includes("🎬 Vidéo") || b.textContent.includes("Vid\u00e9o"));
    if (tab) tab.click();
  });
  await new Promise((r) => setTimeout(r, 300));
  const hasVideoTab = await page.evaluate(() =>
    document.body.innerText.includes("Position verticale")
  );
  console.log("2) onglet Vidéo présent :", hasVideoTab);
  if (!hasVideoTab) fail("onglet Vidéo introuvable");

  const offsetVal = await page.evaluate(() => {
    const labels = [...document.querySelectorAll("label")];
    const lab = labels.find((l) => l.textContent.includes("Position verticale"));
    return lab ? lab.textContent.trim() : "n/a";
  });
  console.log("   valeur offset initiale :", offsetVal);

  // déplacer le slider à -12.5
  await page.evaluate(() => {
    const inputs = [...document.querySelectorAll('input[type="range"]')];
    const target = inputs.find((i) => i.min === "-20" && i.max === "20");
    if (!target) return false;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    setter.call(target, "-12.5");
    target.dispatchEvent(new Event("input", { bubbles: true }));
    target.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  });
  await new Promise((r) => setTimeout(r, 400));
  const offsetAfter = await page.evaluate(() => {
    const labels = [...document.querySelectorAll("label")];
    const lab = labels.find((l) => l.textContent.includes("Position verticale"));
    return lab ? lab.textContent.trim() : "n/a";
  });
  console.log("   offset après slider :", offsetAfter);
  if (!offsetAfter.includes("-12.5")) fail("slider offset_y non mis à jour");

  // 3) Slider logo max = 90
  await page.evaluate(() => {
    const tab = [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Fond & Logo"));
    if (tab) tab.click();
  });
  await new Promise((r) => setTimeout(r, 300));
  const logoSlider = await page.evaluate(() => {
    const inputs = [...document.querySelectorAll('input[type="range"]')];
    const t = inputs.find((i) => i.min === "5" && i.max === "90");
    return t ? { min: t.min, max: t.max } : null;
  });
  console.log("3) slider logo (min/max) :", JSON.stringify(logoSlider));
  if (!logoSlider || logoSlider.max !== "90") fail("max slider logo != 90");

  // 4) Export codex : session.video.offset_y + session.logo custom
  await page.evaluate(() => {
    const btn = [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Télécharger codex.json"));
    if (btn) btn.click();
  });
  await new Promise((r) => setTimeout(r, 1500));
  const dl = fs.existsSync(DL_DIR) ? fs.readdirSync(DL_DIR) : [];
  if (!dl.length) {
    fail("codex.json non téléchargé");
  } else {
    const codex = JSON.parse(fs.readFileSync(path.join(DL_DIR, dl[0]), "utf8"));
    const logo = codex.session?.logo;
    const vo = codex.session?.video;
    console.log("   session.logo :", JSON.stringify(logo));
    console.log("   session.video :", JSON.stringify(vo));
    if (!logo || logo.position !== "custom") fail("logo non custom dans le codex");
    if (Math.abs((logo.x_pct || 0) - X * 100) > TOL) fail(`x_pct ${logo.x_pct}`);
    if (Math.abs((logo.y_pct || 0) - Y * 100) > TOL) fail(`y_pct ${logo.y_pct}`);
    if (!vo || vo.offset_y !== -12.5) fail(`session.video.offset_y attendu -12.5, reçu ${vo?.offset_y}`);
  }

  await page.screenshot({ path: "/tmp/opencode/fix_video_tab.png" });
  console.log(pass ? "\n=== PASS ===" : "\n=== FAIL ===");
  await browser.close();
  process.exit(pass ? 0 : 1);
})();
