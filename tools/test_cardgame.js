// „სამი ხაზის“ ბრაუზერის ვერსიის ტესტი: cardgame/index.html-ში კომპიუტერი კომპიუტერს ეთამაშება (ყველა წყვილი არ — 5 წყვილი × 40 თამაში).
// ამოწმებს: JS შეცდომები არ არის, ყველა თამაში მთავრდება, მოქმედებების ციკლი არ იჭედება, პირველი სვლის უპირატესობა ზომიერია.
// გაშვება: NODE_PATH=$(npm root -g) node tools/test_cardgame.js
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://' + path.resolve(__dirname, '..', 'cardgame', 'index.html')); await p.waitForTimeout(300);
  const r = await p.evaluate(() => {
    const C = window.__cg, out = { games: 0, over: 0, stuck: 0, first: 0, turns: 0 };
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
    return out;
  });
  await b.close();
  const firstPct = r.first / r.over * 100;
  console.log(`თამაშები: ${r.games} · დასრულდა: ${r.over} · საშუალო სვლა: ${(r.turns / r.games).toFixed(1)} · პირველი იგებს: ${firstPct.toFixed(0)}% · გაჭედვა: ${r.stuck}`);
  const bad = errs.length || r.over < r.games || r.stuck || firstPct > 65 || firstPct < 35;
  if (errs.length) console.log('შეცდომები:', errs.slice(0, 5));
  process.exit(bad ? 1 : 0);
})();
