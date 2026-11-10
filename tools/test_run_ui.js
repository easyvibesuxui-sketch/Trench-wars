// „სანგრის რიგის“ ბრაუზერის ტესტი: ბოტი ღილაკებით სრულ გარბენს თამაშობს cardgame/index.html-ში (ტელეფონის სიგანეზე) და ამოწმებს,
// რომ არც ერთი ეკრანი არ ტყდება, გვერდი ჰორიზონტალურად არ გადის და გარბენი ბოლომდე მიდის.
// გაშვება: NODE_PATH=$(npm root -g) node tools/test_run_ui.js [სკრინშოტების საქაღალდე]
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch(); const errs = []; const S = process.argv[2] ? process.argv[2] + '/' : null;
  const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  p.on('pageerror', e => errs.push(String(e))); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto('file://' + path.resolve(__dirname, '..', 'cardgame', 'index.html')); await p.waitForTimeout(400);
  await p.click('[data-act="pick"]'); await p.click('[data-act="start"]');
  const shots = {}; let guard = 0;
  const shot = async name => { if (S && !shots[name]) { shots[name] = 1; await p.screenshot({ path: S + 'p-' + name + '.png', fullPage: true }); } };
  while (guard++ < 300) {
    const ph = await p.evaluate(() => __tl.V.screen === 'battle' ? 'battle' : __tl.R.phase);
    if (ph === 'over') { await shot('over'); break; }
    if (ph === 'map') { await shot('map' + (await p.evaluate(() => __tl.R.act))); const n = await p.$$('[data-act="enter"]'); await n[Math.floor(Math.random() * n.length)].click(); }
    else if (ph === 'prep') {
      for (let k = 0; k < 12; k++) {
        const ok = await p.evaluate(() => { const R = __tl.R, TL = __tl.TL; let best = -1, bv = 0;
          R.shop.offers.forEach((o, i) => { if (o.sold || o.cost > R.supply || !TL.canAdd(R, o.id)) return; const cp = TL.all(R).filter(x => x.id === o.id && x.st === 1).length; const v = TL.power(o.id, 1) / o.cost + cp * 3; if (v > bv) { bv = v; best = i; } }); return best; });
        if (ok < 0) { const rr = await p.$('[data-act="reroll"]:not([disabled])'); const sup = await p.evaluate(() => __tl.R.supply); if (rr && sup >= 4 && k < 6) { await rr.click(); continue; } break; }
        await p.click(`[data-act="offer"][data-i="${ok}"]`); const bb = await p.$('[data-act="buy"]:not([disabled])'); if (bb) await bb.click(); else break; }
      const so = await p.$('[data-act="shopord"]:not(.sold)'); if (so) { await so.click(); const bo = await p.$('[data-act="buyord"]:not([disabled])'); if (bo) await bo.click(); }
      { const n = await p.locator('[data-act="order"]').count(); for (let i = 0; i < n; i++) await p.click(`[data-act="order"][data-i="${i}"]`); }
      const idx = await p.evaluate(() => __tl.R.act * 6 + __tl.R.step); if (idx === 9 || idx === 16) await shot('prep' + idx);
      await p.click('[data-act="fight"]'); await p.waitForTimeout(idx === 9 && S ? 2600 : 150); if (idx === 9) await shot('battle9');
      await p.click('[data-act="skip"]'); await p.waitForTimeout(80); await p.click('[data-act="bnext"]'); }
    else if (ph === 'reward') { await shot('reward' + (await p.evaluate(() => __tl.R.reward.relicDone ? 'p' : 'r'))); const r = await p.$('[data-act="relicpick"]'); if (r) await r.click(); else { const c = await p.$$('[data-act="rpick"]:not([disabled])'); await c[0].click(); } }
    else if (ph === 'event') { await shot('event'); const c = await p.$$('[data-act="event"]:not([disabled])'); await c[0].click(); }
    else if (ph === 'camp') { await shot('camp'); const low = await p.evaluate(() => __tl.R.nerve < __tl.R.maxNerve - 2); const u = await p.$('[data-act="train"]'); if (low || !u) await p.click('[data-act="rest"]'); else await u.click(); }
    else if (ph === 'depot') { await shot('depot'); const c = await p.$$('[data-act="depot"]:not([disabled])'); await c[0].click(); }
    await p.waitForTimeout(30);
    const ov = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth); if (ov > 0) { errs.push(ph + ' horizontal overflow ' + ov); await shot('overflow-' + ph); }
  }
  console.log(await p.evaluate(() => JSON.stringify({ won: __tl.R.won, act: __tl.R.act, step: __tl.R.step, stats: __tl.R.stats, lvl: __tl.M.lvl, xp: __tl.M.xp, seen: Object.keys(__tl.M.seen).length })));
  const over = await p.evaluate(() => __tl.R.phase === 'over'); if (!over) errs.push('run did not finish');
  await p.click('[data-act="home"]'); await p.waitForTimeout(100); if (S) await p.screenshot({ path: S + 'p-home.png', fullPage: true });
  await p.click('[data-act="meta"]'); if (S) await p.screenshot({ path: S + 'p-meta.png', fullPage: true }); await p.click('[data-act="home"]');
  await p.click('[data-act="codex"]'); if (S) await p.screenshot({ path: S + 'p-codex.png', fullPage: true });
  await p.click('[data-act="rules"]'); if (S) await p.screenshot({ path: S + 'p-rules.png' });
  await p.click('[data-act="close"]');
  for (const l of ['en', 'ka']) await p.click(`.lang button[data-lang="${l}"]`);
  await b.close(); const u = [...new Set(errs)]; console.log(u.join('\n') || 'OK', '· steps', guard); process.exit(u.length ? 1 : 0);
})();
