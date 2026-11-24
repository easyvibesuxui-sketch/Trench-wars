// „სანგრის რიგის“ (v2) ბოტი: მაღაზიაში იგივე ავტომატური მოთამაშეა, რაც მოჩვენებებს (TL.autoShop), smart — ამას გარდა მტრის ხილული
// ჯარის წინააღმდეგ რამდენიმე განლაგებას ცდის. რუკაზე: ცოტა სიცოცხლისას ბანაკი, თორემ რჩეული რაზმი. იყენებს tools/test_run.js და tools/tune_factions.js.
module.exports = function (TL) {
  function prep(run, smart) {
    TL.autoShop(run); run.phase = 'prep';
    while (run.pending.length) TL.takeDiscover(run, run.pending[0].findIndex(id => TL.canAdd(run, id)));
    if (!smart) return;
    const em = {}; for (const k of run.enemy.mods) em[k] = 1; const m = TL.mods(run);
    const val = b => { const r = TL.simulate(b, run.enemy, { terrain: run.ter, modsA: m, modsB: em }); return (r.win === 'a' ? 100 : r.win === 'draw' ? 50 : 0) + r.left.a - r.left.b; };
    let q = (run.seed ^ Math.imul(run.round, 2654435761)) >>> 0; const rnd = () => (q = (Math.imul(q, 1664525) + 1013904223) >>> 0) / 4294967296;
    let best = { t: run.board.t.slice(), r: run.board.r.slice() }, bs = val(best);
    for (let i = 0; i < 16 && bs < 100; i++) {
      const b = { t: best.t.slice(), r: best.r.slice() }, xs = b.t.concat(b.r);
      if (xs.length < 2) break;
      const a = xs[Math.floor(rnd() * xs.length)], c = xs[Math.floor(rnd() * xs.length)]; if (a === c) continue;
      const ra = b.t.includes(a) ? b.t : b.r, rc = b.t.includes(c) ? b.t : b.r, ia = ra.indexOf(a), ic = rc.indexOf(c);
      ra[ia] = c; rc[ic] = a;
      if (!b.t.length) continue;
      const s = val(b); if (s > bs) { bs = s; best = b; }
    }
    run.board = best;
  }
  function playRun(run, smart, trace, ok) {
    ok = ok || (() => {}); if (smart === undefined) smart = true; let guard = 0;
    while (run.phase !== 'over' && guard++ < 300) {
      if (run.phase === 'prep') { prep(run, smart); const out = TL.fight(run); ok(out, 'fight returns'); if (trace && out) trace(out, run); }
      else if (run.phase === 'map') { const want = run.lives <= 2 ? ['camp', 'depot', 'event', 'elite'] : ['elite', 'depot', 'camp', 'event'];
        let i = 0; for (const t of want) { const j = run.map.findIndex(n => n.t === t); if (j >= 0) { i = j; break; } } TL.choose(run, i); }
      else if (run.phase === 'reward') TL.takeRelic(run, 0);
      else if (run.phase === 'event') { if (!TL.chooseEvent(run, 0)) TL.chooseEvent(run, 1); }
      else if (run.phase === 'camp') { if (run.lives < run.maxLives) TL.campRest(run); else { const x = TL.field(run)[0]; if (!x || !TL.campTrain(run, x.u)) TL.campRest(run) || (run.phase = 'over'); } }
      else if (run.phase === 'depot') TL.depotTake(run, 0);
      ok(run.board.t.length <= TL.T_CAP && run.board.r.length <= TL.R_CAP && run.bench.length <= TL.B_CAP && run.supply >= 0 && run.lives >= 0, 'run invariants ' + run.phase);
    }
    ok(run.phase === 'over', 'run ends'); return run;
  }
  const botRun = (f, smart, seed, diff, trace, ok) => playRun(TL.newRun({ faction: f, diff: diff || 0, seed }), smart, trace, ok);
  return { botRun, playRun, prep };
};
