// „სანგრის რიგის“ ბოტი: მობილიზაცია (ძალა/ფასი, სამეულების შეგროვება), განლაგება, რუკის არჩევანი. smart — რამდენიმე განლაგებას
// ცდის მტრის ხილული რიგის წინააღმდეგ. იყენებს tools/test_run.js (ტესტი, ბალანსი) და tools/tune_factions.js (დოქტრინების შერჩევა).
module.exports = function (TL) {

function botPrep(run, smart) {
  let rolls = 0, guard = 0;
  while (guard++ < 40) {
    let best = -1, bv = 0;
    run.shop.offers.forEach((o, i) => { if (o.sold || o.cost > run.supply) return;
      const cp = TL.all(run).filter(x => x.id === o.id && x.st === 1).length, k = TL.traits(o.id);
      if (!TL.canAdd(run, o.id)) {
        if (k.hero && TL.all(run).some(x => TL.traits(x.id).hero)) return; if (k.giant && TL.all(run).some(x => TL.traits(x.id).giant)) return;
        const weak = TL.all(run).filter(x => x.st === 1 && TL.all(run).filter(y => y.id === x.id).length === 1).sort((p, q) => TL.power(p.id, 1) - TL.power(q.id, 1))[0];
        if (!weak || (cp < 1 && TL.power(o.id, 1) < TL.power(weak.id, 1) * 1.25) || weak.id === o.id) return; TL.sell(run, weak.u); }
      const v = TL.power(o.id, 1) / o.cost + (cp === 2 ? 10 : cp === 1 ? 2.5 : 0); if (v > bv) { bv = v; best = i; } });
    if (best >= 0 && TL.buy(run, best)) continue;
    if (run.free > 0 || (run.supply >= 4 && rolls < 3 + run.act * 3)) { rolls++; TL.reroll(run); continue; }
    break;
  }
  if (run.supply >= run.shop.order.cost + 1) TL.buyOrder(run);
  // საუკეთესო იუნიტები რიგში, გონივრული განლაგება
  const xs = TL.all(run).sort((p, q) => TL.power(q.id, q.st) + q.ba + q.bh - TL.power(p.id, p.st) - p.ba - p.bh);
  let line = TL.arrange(xs.slice(0, TL.slots(run)));
  run.active = run.orders.map((k, i) => i);
  if (smart) {                                       // „მოაზროვნე“ მოთამაშე: რამდენიმე განლაგებას ცდის მტრის ხილული რიგის წინააღმდეგ
    const em = {}; for (const k of run.emods) em[k] = 1; const m = TL.mods(run);
    const val = l => { const r = TL.simulate(l, run.enemy, { terrain: run.node.ter, modsA: m, modsB: em }); return (r.win === 'a' ? 100 : 0) + r.left.a - r.left.b; };
    let bestL = line, bs = val(line);
    let q = (run.seed ^ (run.mus * 2654435761)) >>> 0; const r = () => (q = (Math.imul(q, 1664525) + 1013904223) >>> 0) / 4294967296;   // საკუთარი თესლიანი შემთხვევითობა: იგივე გარბენი — იგივე შედეგი
    for (let t = 0; t < 12 && bs < 100; t++) { const l = line.slice(); const i = Math.floor(r() * l.length), j = Math.floor(r() * l.length); [l[i], l[j]] = [l[j], l[i]]; const s = val(l); if (s > bs) { bs = s; bestL = l; } }
    line = bestL;
  }
  run.line = line; run.res = xs.slice(TL.slots(run));
}
function botRun(f, smart, seed, diff, trace, ok) {
  ok = ok || (() => {});
  return playRun(TL.newRun({ faction: f, diff: diff || 0, seed }), smart === undefined ? true : smart, trace, ok);
}
function playRun(run, smart, trace, ok) {
  ok = ok || (() => {}); if (smart === undefined) smart = true; let guard = 0;
  while (run.phase !== 'over' && guard++ < 400) {
    if (run.phase === 'map') { const o = TL.options(run); let i = 0;
      const want = run.nerve <= 5 ? ['camp', 'event', 'depot', 'battle', 'elite'] : run.nerve >= 9 ? ['elite', 'battle', 'depot', 'event', 'camp'] : ['battle', 'depot', 'event', 'camp', 'elite'];
      for (const t of want) { const j = o.findIndex(x => x.t === t); if (j >= 0) { i = j; break; } } TL.enter(run, i); }
    else if (run.phase === 'prep') { botPrep(run, smart); const idx = run.act * 6 + run.step, t = run.node.t; const pw = l => l.reduce((a, x) => a + TL.power(x.id, x.st) + x.ba + x.bh, 0); const pp = pw(run.line), ep = pw(run.enemy); const out = TL.fight(run); if (trace) trace(idx, t, out, pp, ep); ok(out, 'fight returns'); }
    else if (run.phase === 'retry') TL.retry(run);
    else if (run.phase === 'reward') { const r = run.reward; if (!r.relicDone) TL.takeRelic(run, 0);
      else { let done = false; for (let i = 0; i < 3 && !done; i++) { const p = r.picks[i]; if (p.t === 'unit' && TL.canAdd(run, p.id)) done = TL.takePick(run, i); }
        if (!done) done = TL.takePick(run, 2); if (!done) TL.takePick(run, -1); } }
    else if (run.phase === 'event') { if (!TL.chooseEvent(run, 0)) TL.chooseEvent(run, 1); }
    else if (run.phase === 'camp') { if (run.nerve <= run.maxNerve - 3 || !run.line.length) TL.campRest(run); else TL.campTrain(run, run.line[0].u); }
    else if (run.phase === 'depot') { if (!TL.depotTake(run, 0)) TL.depotTake(run, -1); }
    ok(run.line.length <= TL.slots(run) && run.res.length <= TL.RES && run.orders.length <= 3 && run.supply >= 0, 'run invariants ' + run.phase);
  }
  ok(run.phase === 'over', 'run ends'); return run;
}
  return { botRun, botPrep, playRun: (run, smart) => playRun(run, smart).won };
};
