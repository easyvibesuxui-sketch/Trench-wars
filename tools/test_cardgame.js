// „სამი ხაზის“ ბრაუზერის ვერსიის ტესტი: cardgame/index.html-ში კომპიუტერი კომპიუტერს ეთამაშება (ყველა წყვილი არ — 5 წყვილი × 40 თამაში).
// ამოწმებს: JS შეცდომები არ არის, ყველა თამაში მთავრდება, მოქმედებების ციკლი არ იჭედება, პირველი სვლის უპირატესობა ზომიერია,
// ძლიერი კომპიუტერი (strongAction) მარტივს (aiAction) 100-დან 60-ზე მეტს უგებს.
// გაშვება: NODE_PATH=$(npm root -g) node tools/test_cardgame.js
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://' + path.resolve(__dirname, '..', 'cardgame', 'index.html')); await p.waitForTimeout(300);
  const r = await p.evaluate(() => {
    const C = window.__cg, out = { games: 0, over: 0, stuck: 0, first: 0, turns: 0 };
    C.headless(true);   // ხატვის, ხმის და ანიმაციის გარეშე — 10-ჯერ სწრაფია
    const pairs = [['colchis', 'harness'], ['iberia', 'hell'], ['kajeti', 'listeners'], ['ring', 'ottoman'], ['hellenic', 'byzantium']];
    for (const [a, z] of pairs) for (let g = 0; g < 40; g++) {
      C.newGame({ me: g % 2 ? a : z, foe: g % 2 ? z : a, mode: 'test', first: (g >> 1) % 2 });
      const first = C.G.cur;
      for (let n = 0; n < 400 && !C.G.over; n++) {
        let k = 0, act;
        while ((act = C.aiAction(C.G.cur)) && k < 200) { act(); k++; if (C.G.over) break; }
        if (k >= 200) out.stuck++;
        if (!C.G.over) C.endTurn();
      }
      out.games++; out.turns += C.G.turn;
      if (C.G.over) { out.over++; if (C.G.over.p === first) out.first++; }
    }
    // ძლიერი კომპიუტერი მარტივის წინააღმდეგ (ადგილები და პირველი სვლა მონაცვლეობით)
    const fs = Object.keys(window.CG.starter); out.strong = 0; out.sgames = 100;
    for (let g = 0; g < out.sgames; g++) {
      C.newGame({ me: fs[(g * 7) % fs.length], foe: fs[(g * 11 + 3) % fs.length], mode: 'test', first: (g >> 1) % 2 });
      const hs = g % 2; C.G.p[hs].level = 'hard'; C.G.p[1 - hs].level = 'easy';
      for (let n = 0; n < 120 && !C.G.over; n++) {
        let k = 0, act;
        while ((act = C.G.p[C.G.cur].level === 'easy' ? C.aiAction(C.G.cur) : C.strongAction(C.G.cur)) && k < 60) { act(); k++; if (C.G.over) break; }
        if (!C.G.over) C.endTurn();
      }
      if (C.G.over && C.G.over.p === hs) out.strong++;
    }
    return out;
  });
  await b.close();
  const firstPct = r.first / r.over * 100;
  console.log(`თამაშები: ${r.games} · დასრულდა: ${r.over} · საშუალო სვლა: ${(r.turns / r.games).toFixed(1)} · პირველი იგებს: ${firstPct.toFixed(0)}% · გაჭედვა: ${r.stuck}`);
  console.log(`ძლიერი კომპიუტერი მარტივს უგებს: ${r.strong}/${r.sgames}`);
  const bad = errs.length || r.over < r.games || r.stuck || firstPct > 65 || firstPct < 35 || r.strong < r.sgames * 0.6;
  if (errs.length) console.log('შეცდომები:', errs.slice(0, 5));
  process.exit(bad ? 1 : 0);
})();
