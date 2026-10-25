// „ღარის დაცვის“ შემოწმება: ლაბირინთის წესი, ხაზის გაწელვა, ტალღები, ჩიხი, ავტომატური თამაში რამდენიმე ტალღაზე
const { chromium } = require("playwright");
const path = require("path");
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on("pageerror", e => errors.push(e.message));
  await page.goto("file://" + path.resolve(__dirname, "../defense/index.html"));
  const ok = (cond, msg) => { if (!cond) { console.error("FAIL:", msg); process.exitCode = 1; } else console.log("ok:", msg); };
  await page.selectOption("#selF", "colchis"); await page.selectOption("#selE", "harness");
  if (process.env.TD_LAST) await page.evaluate(([l, s]) => { window.TD_LAST = l; window.TD_SPEED = s; }, [process.env.TD_LAST, process.env.TD_SPEED || 3]);
  await page.click("#startBtn");
  // 1) გაწელვა: მესრის ხაზი
  const cell = (x, y) => page.evaluate(([x, y]) => { const cv = document.getElementById("cv"), r = cv.getBoundingClientRect(), S = window.TD_GAME();
    const k = r.width / (28 * 32), kh = r.height / (16 * 32), s = Math.min(k, kh), ox = (r.width - 28 * 32 * s) / 2, oy = (r.height - 16 * 32 * s) / 2;
    return { x: r.left + ox + (x * 32 + 16) * s, y: r.top + oy + (y * 32 + 16) * s }; }, [x, y]);
  await page.click("#b_palisade");
  let a = await cell(20, 0), b = await cell(20, 13);
  await page.mouse.move(a.x, a.y); await page.mouse.down(); await page.mouse.move(b.x, b.y, { steps: 10 }); await page.mouse.up();
  let st = await page.evaluate(() => { const S = window.TD_GAME(); let n = 0; for (let y = 0; y < 16; y++) if (S.grid[y * 28 + 20] === 2) n++; return { n, gold: S.gold, open: window.TD_API.pathOpen() }; });
  ok(st.n === 14 && st.gold === 120 - 28, `მესრის ხაზი გაიწელა (${st.n} უჯრა, მარჩილი ${st.gold})`);
  ok(st.open, "გზა ღიაა");
  // 2) ლაბირინთის წესი: ბოლო ხვრელის ჩაკეტვა აკრძალულია
  a = await cell(20, 14); b = await cell(20, 15);
  await page.mouse.move(a.x, a.y); await page.mouse.down(); await page.mouse.move(b.x, b.y, { steps: 4 }); await page.mouse.up();
  st = await page.evaluate(() => { const S = window.TD_GAME(); return { c14: S.grid[14 * 28 + 20], c15: S.grid[15 * 28 + 20], open: window.TD_API.pathOpen() }; });
  ok((st.c14 !== 2 || st.c15 !== 2) && st.open, "ბოლო გასასვლელი არ ჩაიკეტა");
  // 3) რაზმი და ტალღები: ავტომატური მოთამაშე
  await page.keyboard.press("Escape");
  const res = await page.evaluate(async () => {
    const S = window.TD_GAME(), A = window.TD_API;
    S.speed = +(window.TD_SPEED || 3);
    const spots = [[21, 14], [19, 14], [19, 12], [23, 14], [19, 10], [18, 14], [17, 14], [19, 8], [16, 14], [19, 6], [15, 14], [22, 13], [14, 14], [19, 4], [13, 14], [24, 13]];
    let held = false, waveSeen = 0;
    const buy = () => { for (const [x, y] of spots) { const i = A.idx(x, y); if (S.occ.has(i)) continue;
      const k = S.defs.length < 1 && S.gold >= 20 ? "port_brawlers" : S.gold >= 70 && !S.defs.some(d => d.b && d.b.gun.suppress) ? "nest" : S.gold >= 65 ? "monaspa" : S.gold >= 35 ? "dali_hunters" : S.gold >= 20 ? "lashkari" : null;
      if (!k) return; A.placeAt(i, k); } };
    // ჩიხის შესამოწმებლად: მოჩხუბრები მტრის გზის გვერდით (გზა — ველის მიხედვით ნაპრალიდან)
    const route = []; { let i = S.spawnI[0]; for (let n = 0; n < 400 && !S.goalI.includes(i); n++) { route.push(i);
      const x = i % 28, y = (i - x) / 28; let best = -1, bv = S.F.foot[i];
      for (const [nx, ny] of [[x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]]) { if (nx < 0 || ny < 0 || nx > 27 || ny > 15) continue; const j = A.idx(nx, ny); if (S.F.foot[j] < bv) { bv = S.F.foot[j]; best = j; } }
      if (best < 0) break; i = best; } }
    for (const i of route.slice(4)) { const x = i % 28, y = (i - x) / 28;
      if ([[x, y - 1], [x, y + 1]].some(([nx, ny]) => ny >= 0 && ny < 16 && !route.includes(A.idx(nx, ny)) && A.placeAt(A.idx(nx, ny), "port_brawlers"))) break; }
    buy(); A.startWave();
    const t0 = performance.now();
    const LAST = +(window.TD_LAST || 8);
    while (!S.over && S.wave <= LAST && performance.now() - t0 < 600000) {
      await new Promise(r => setTimeout(r, 200));
      if (S.holds) held = true;
      if (S.phase === "build") { buy(); if (S.wave < LAST) A.startWave(); else break; }
      waveSeen = S.wave;
    }
    return { wave: S.wave, seal: S.seal, gold: S.gold, kills: S.kills, held, defs: S.defs.length, over: S.over };
  });
  console.log("ავტომატური თამაში:", JSON.stringify(res));
  ok(res.kills > 10, "მტრები კვდებიან და ბაუნტი ირიცხება");
  ok(res.held, "ქვეითი მტერს აჩერებს (ჩიხი)");
  ok(res.wave >= 5, "ბოსის (მე-5) ტალღამდე მიაღწია");
  ok(!errors.length, "JS შეცდომები არ არის " + errors.join(" | "));
  await page.screenshot({ path: process.argv[2] || "/tmp/defense.png" });
  await browser.close();
})();
