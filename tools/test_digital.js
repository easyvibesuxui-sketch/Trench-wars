// ციფრული პროტოტიპის შემოწმება: გაწელვა, შენების დრო, მშენებლები, კამერა, კომპიუტერის შენება
const { chromium } = require("playwright");
const path = require("path");
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  // TW_LANG=en — იგივე ტესტი ინგლისურ რეჟიმში (KA/EN გადამრთველი)
  if (process.env.TW_LANG) await page.addInitScript(l => { try { localStorage.setItem("tw-lang", l); } catch (e) {} }, process.env.TW_LANG);
  const errors = [];
  page.on("pageerror", e => errors.push(e.message));
  await page.goto("file://" + path.resolve(__dirname, "../digital/index.html"));
  await page.click("#startBtn");
  const ok = (cond, msg) => { if (!cond) { console.error("FAIL:", msg); process.exitCode = 1; } else console.log("ok:", msg); };
  const box = await page.locator("#cv").boundingBox();
  // სამყაროს წერტილი → ეკრანის წერტილი (კამერის მიხედვით)
  const at = (x, y) => page.evaluate(([x, y]) => { const c = window.TW_CAM, cv = document.getElementById("cv"), r = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    return { x: r.left + ((x - c.x) * c.z + cv.width / 2) / dpr, y: r.top + ((y - c.y) * c.z + cv.height / 2) / dpr }; }, [x, y]);
  const zoom = () => page.evaluate(() => window.TW_CAM.z);
  // 1) გაწელვა: ხის მესერი
  await page.click("#b_palisade");
  const p0 = await at(330, 330), p1 = await at(330, 560);
  await page.mouse.move(p0.x, p0.y); await page.mouse.down(); await page.mouse.move(p1.x, p1.y, { steps: 8 }); await page.mouse.up();
  let st = await page.evaluate(() => { const S = window.TW_GAME(); const segs = S.ents.filter(b => b.kind === "b" && b.side === "p" && b.type === "palisade");
    return { n: segs.length, grp: new Set(segs.map(b => b.grp)).size, built: segs.filter(b => b.built).length, builders: S.ents.filter(e => e.kind === "porter" && e.side === "p" && e.job).length, coal: S.side.p.coal }; });
  ok(st.n > 5 && st.grp === 1, `გაწელვამ ერთი ხაზი შექმნა (${st.n} მონაკვეთი)`);
  ok(st.built === 0, "მონაკვეთები საძირკვლად იწყება");
  ok(st.builders === 2, "2 მშენებელი გაიგზავნა");
  ok(st.coal === 200 - st.n * 3, "ფასი თითო მონაკვეთზე");
  // 2) დრო: ~ n*2.5*3/4 წამი + სიარული
  await page.evaluate(() => { window.TW_GAME().t0 = window.TW_GAME().t; });
  await page.waitForFunction(() => { const S = window.TW_GAME(); return S.ents.filter(b => b.type === "palisade" && b.side === "p").every(b => b.built); }, null, { timeout: 90000 });
  await page.waitForTimeout(300);
  st = await page.evaluate(() => { const S = window.TW_GAME(); return { dt: S.t - S.t0, idle: S.ents.filter(e => e.kind === "porter" && e.side === "p" && e.job).length }; });
  ok(st.dt > 5, `ხაზი აშენდა ${st.dt.toFixed(1)} წამში (არა მყისიერად)`);
  ok(st.idle === 0, "მშენებლები შეგროვებას დაუბრუნდნენ");
  // 3) ერთი შენება: ყაზარმა საძირკვლიდან
  await page.evaluate(() => { const S = window.TW_GAME(); S.side.p.coal = 500; });
  await page.click("#b_barracks"); const bp = await at(245, 520); await page.mouse.click(bp.x, bp.y);
  st = await page.evaluate(() => { const S = window.TW_GAME(); const b = S.ents.find(e => e.type === "barracks" && e.side === "p"); return b && { built: b.built, hp: b.hp, max: b.maxhp }; });
  ok(st && !st.built && st.hp < st.max, "ყაზარმა საძირკვლად დაიდო");
  const armyDisabled = await page.locator("#t_lashkari").isDisabled();
  ok(armyDisabled, "დაუმთავრებელი ყაზარმა ჯარს არ წვრთნის");
  // 4) კამერა: ბორბალი, მთელი რუკა, სოფელი
  const z0 = await zoom();
  await page.mouse.move(box.x + 640, box.y + 300); await page.mouse.wheel(0, 400); await page.waitForTimeout(100);
  const z1 = await zoom();
  ok(z1 < z0, "ბორბალი აშორებს კამერას");
  await page.click("#camAll"); await page.waitForTimeout(100);
  const zAll = await zoom();
  await page.click("#camHome"); await page.waitForTimeout(100);
  const zHome = await zoom();
  ok(zAll < zHome, "მთელი რუკა / სოფელი");
  // 5) კომპიუტერი წელავს ძელებს და აშენებს
  await page.evaluate(() => { window.TW_GAME().t = 31; });
  await page.waitForFunction(() => window.TW_GAME().ents.some(b => b.side === "e" && b.grp && b.built), null, { timeout: 60000 });
  ok(true, "კომპიუტერის ძელების ხაზი შენდება");
  ok(!errors.length, "JS შეცდომები არ არის " + errors.join(" | "));
  await browser.close();
})();
