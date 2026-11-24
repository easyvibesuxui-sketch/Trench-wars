// „სანგრის რიგის“ (v2) ბრაუზერის ტესტი: ბოტი ღილაკებით სრულ გარბენს თამაშობს cardgame/index.html-ში ტელეფონის ზომაზე (390×844)
// და ამოწმებს: შეცდომები არ არის, გვერდი ჰორიზონტალურად არ გადის, მომზადების და ბრძოლის ეკრანი ერთ ეკრანზე ეტევა, გარბენი მთავრდება.
// გაშვება: NODE_PATH=$(npm root -g) node tools/test_run_ui.js [სკრინშოტების საქაღალდე]
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch(); const errs = []; const S = process.argv[2] ? process.argv[2] + '/' : null;
  const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  p.on('pageerror', e => errs.push(String(e))); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto('file://' + path.resolve(__dirname, '..', 'cardgame', 'index.html')); await p.waitForTimeout(400);
  if (S) await p.screenshot({ path: S + 'v2-home.png' });
  await p.click('[data-act="pick"]'); await p.click('[data-act="start"]');
  const shots = {}; let guard = 0;
  const shot = async (name, full) => { if (S && !shots[name]) { shots[name] = 1; await p.screenshot({ path: S + 'v2-' + name + '.png', fullPage: !!full }); } };
  const fits = async name => { const o = await p.evaluate(() => document.documentElement.scrollHeight - innerHeight); if (o > 2) errs.push(`${name}: does not fit one screen (+${o}px)`); };
  while (guard++ < 400) {
    const ph = await p.evaluate(() => __tl.V.screen === 'battle' ? 'battle' : __tl.R.phase);
    if (ph === 'over') { await shot('over', 1); break; }
    if (ph === 'prep') {
      const st = await p.evaluate(() => ({ r: __tl.R.round, s: __tl.R.supply, lvl: __tl.R.lvl, up: __tl.R.upCost }));
      if (st.r === 1) await shot('prep1');
      if (st.lvl < 6 && st.s >= st.up && st.r >= [0, 0, 2, 4, 6, 8, 10][st.lvl + 1]) await p.click('[data-act="levelup"]');
      for (let k = 0; k < 10; k++) {
        if (await p.$('#sheet:not([hidden]) [data-act="disc"]')) { await shot('discover'); await p.click('[data-act="disc"][data-i="0"]'); continue; }
        const i = await p.evaluate(() => { const R = __tl.R, TL = __tl.TL; let best = -1, bv = 0;
          R.shop.units.forEach((o, i) => { if (o.sold || o.cost > R.supply || !TL.canAdd(R, o.id)) return; const c = TL.all(R).filter(x => x.id === o.id && x.st === 1).length; const v = TL.power(o.id, 1) + c * 6; if (v > bv) { bv = v; best = i; } }); return best; });
        if (i < 0) break;
        await p.click(`[data-act="offer"][data-i="${i}"]`); if (st.r === 2 && k === 0) await shot('sheet');
        const bb = await p.$('[data-act="buy"]:not([disabled])'); if (bb) await bb.click(); else { await p.click('[data-act="close"]'); break; }
      }
      if (await p.$('#sheet:not([hidden]) [data-act="disc"]')) await p.click('[data-act="disc"][data-i="0"]');
      const s2 = await p.evaluate(() => __tl.R.supply);
      if (s2 >= 3) { const it = await p.evaluate(() => __tl.R.shop.items.findIndex(o => !o.sold && __tl.TL.ITEMS[o.key].kind !== 'unit'));
        if (it >= 0) { await p.click(`[data-act="item"][data-i="${it}"]`); const u = await p.$('[data-act="useitem"]:not([disabled])'); if (u) await u.click(); else await p.click('[data-act="close"]'); } }
      // ერთი გადაადგილება: სათადარიგოდან ველზე, თუ ადგილია
      const mv = await p.evaluate(() => { const R = __tl.R; return R.bench.length && R.board.t.length < 4 ? R.bench[0].u : null; });
      if (mv) { await p.click(`[data-act="own"][data-u="${mv}"]`); await p.click('[data-act="slot"][data-z="t"]'); }
      if (st.r === 5) { await shot('prep5'); await fits('prep'); }
      await p.click('[data-act="fight"]'); await p.waitForTimeout(st.r === 5 && S ? 2400 : 120);
      if (st.r === 5) { await shot('battle'); await fits('battle'); }
      await p.click('[data-act="skip"]'); await p.waitForTimeout(60); if (st.r === 5) await shot('battle-end');
      await p.click('[data-act="bnext"]');
    }
    else if (ph === 'map') { await shot('map', 1); const n = await p.$$('[data-act="node"]'); await n[guard % n.length].click(); }
    else if (ph === 'reward') { await shot('reward', 1); await p.click('[data-act="relic"]'); }
    else if (ph === 'event') { await shot('event', 1); const c = await p.$$('[data-act="event"]:not([disabled])'); await c[0].click(); }
    else if (ph === 'camp') { await shot('camp', 1); const r = await p.$('[data-act="rest"]:not([disabled])'); if (r) await r.click(); else await p.click('[data-act="train"]'); }
    else if (ph === 'depot') { await shot('depot', 1); await p.click('[data-act="depot"]'); }
    await p.waitForTimeout(20);
    const ov = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth); if (ov > 0) errs.push(ph + ' horizontal overflow ' + ov);
  }
  console.log(await p.evaluate(() => JSON.stringify({ won: __tl.R.won, wins: __tl.R.wins, lives: __tl.R.lives, round: __tl.R.round, lvl: __tl.R.lvl, stats: __tl.R.stats, meta: __tl.M.lvl + '/' + __tl.M.xp })));
  if (!(await p.evaluate(() => __tl.R.phase === 'over'))) errs.push('run did not finish');
  await p.click('[data-act="home"]'); await p.click('[data-act="meta"]'); if (S) await p.screenshot({ path: S + 'v2-meta.png', fullPage: true });
  await p.click('[data-act="home"]'); await p.click('[data-act="codex"]');
  await p.click('[data-act="rules"]'); if (S) await p.screenshot({ path: S + 'v2-rules.png' }); await p.click('[data-act="closedlg"]');
  for (const l of ['en', 'ka']) await p.click(`[data-lang="${l}"]`);
  await b.close(); const u = [...new Set(errs)]; console.log(u.join('\n') || 'OK', '· steps', guard); process.exit(u.length ? 1 : 0);
})();
