// „სანგრის რიგის“ (v2) ტესტი და ბალანსი (cardgame/engine.js): წესების ინვარიანტები + ბოტი (tools/run_bot.js), რომელიც გარბენებს თამაშობს.
// გაშვება: node tools/test_run.js [გარბენი ფრაქციაზე, 30] [სიმძიმე, 0] [ფრაქციები მძიმით ან all]
// ფრაქციების ბალანსი (ლოჯისტიკა და მოჩვენებების სიძლიერე) — tools/tune_factions.js.
const path = require('path');
global.window = {}; require(path.resolve(__dirname, '..', 'cardgame', 'data.js'));
const CG = window.CG, TL = require(path.resolve(__dirname, '..', 'cardgame', 'engine.js'))(CG), BOT = require('./run_bot.js')(TL);
const N = +(process.argv[2] || 30), DIFF = +(process.argv[3] || 0);
const FS = !process.argv[4] ? ['colchis', 'iberia', 'hell', 'harness', 'listeners', 'kajeti', 'ring', 'finnish', 'italy', 'korea']
  : process.argv[4] === 'all' ? Object.keys(CG.factions) : process.argv[4].split(',');
let fails = 0; const ok = (c, m) => { if (!c) { fails++; console.log('FAIL', m); } };
const L = (...ids) => ids.map(id => typeof id === 'string' ? { id } : id);
const hits = (r, k) => r.ev.filter(e => e.t === 'hit' && e.k === k);

// 1) ტექსტები და მონაცემები
for (const id in CG.units) { const k = Object.keys(TL.traits(id)); ok(k.length > 0, 'no trait ' + id); for (const x of k) ok(TL.KW[x], 'kw ' + x); }
for (const k in TL.KW) for (const n of [1, 2, 3]) { const t = TL.KW[k].t(n); ok(t[0] && t[1] && TL.KW[k].g, 'kw text ' + k); }
for (const k in TL.ITEMS) ok(TL.ITEMS[k].ka && TL.ITEMS[k].en && TL.ITEMS[k].t[1], 'item ' + k);
// 2) ბრძოლა დეტერმინირებულია და მთავრდება
{ const a = { t: L('monaspa', 'aznauri'), r: L('medea_sisters', 'lashkari') }, b = { t: L({ id: 'monaspa', st: 2 }), r: L('lashkari') };
  const r1 = TL.simulate(a, b, {}), r2 = TL.simulate(a, b, {});
  ok(JSON.stringify(r1.ev) === JSON.stringify(r2.ev), 'deterministic'); ok(r1.ev[r1.ev.length - 1].t === 'end' && r1.rounds <= 40, 'ends'); }
// 3) უნარები რიგების მიხედვით
{ let r = TL.simulate({ t: L('aznauri') }, { t: L('port_brawlers') }, {}); ok(hits(r, 'melee').find(e => e.d === 'a0').n === 2, 'shield −1');
  r = TL.simulate({ t: L('aznauri') }, { t: L('shavkhan_smiths') }, {}); ok(hits(r, 'melee').find(e => e.d === 'a0').n === 4, 'breaker ignores shield');
  r = TL.simulate({ t: L('monaspa'), r: L('lashkari') }, { t: L('port_brawlers') }, {}); ok(hits(r, 'support').length >= 1, 'long fires from the rear');
  r = TL.simulate({ t: L('lashkari', 'monaspa') }, { t: L('port_brawlers') }, {}); ok(hits(r, 'support').length === 0, 'long in the trench does not fire from behind');
  r = TL.simulate({ t: L('kolkhi_riders') }, { t: L('monaspa') }, {}); ok(hits(r, 'charge').length === 1, 'charge');
  r = TL.simulate({ t: L('kolkhi_riders') }, { t: L('monaspa') }, { terrain: 'mud' }); ok(hits(r, 'charge').length === 0, 'mud stops charge');
  r = TL.simulate({ t: L('monaspa'), r: L('medea_sisters') }, { t: L('port_brawlers', 'port_brawlers') }, {}); ok(r.ev.some(e => e.t === 'heal' && e.s === 'a1' && e.d === 'a0'), 'rear healer heals the trench front');
  r = TL.simulate({ t: L('port_brawlers'), r: L('eristavi') }, { t: L('monaspa') }, {}); ok(r.ev[0].a.t[0].atk === 3 + 1, 'leader in the rear buffs the trench');
  r = TL.simulate({ t: L('port_brawlers'), r: L('monaspa') }, { t: L({ id: 'monaspa', st: 3 }) }, {}); ok(r.ev.some(e => e.t === 'advance' && e.side === 'a'), 'rear advances when the trench falls');
  r = TL.simulate({ t: L('monaspa'), r: L('fleece_dragon') }, { t: L('monaspa'), r: L('lashkari') }, {}); ok(hits(r, 'air')[0].d === 'b3', 'flyer hits the enemy rear');
  r = TL.simulate({ t: L('monaspa'), r: L('fleece_dragon') }, { t: L('monaspa'), r: L('lashkari') }, { modsB: { camo: 1 } }); ok(hits(r, 'air')[0].d === 'b2', 'camouflage hides the rear');
  r = TL.simulate({ t: L('iron_arm_veterans') }, { t: L('ambri_ox') }, {}); ok(hits(r, 'venge').length === 1, 'last round');
  r = TL.simulate({ t: L('fleece_dragon') }, { t: L('lashkari', 'lashkari') }, {}); ok(hits(r, 'quake').length === 2, 'giant quake');
  r = TL.simulate({ t: L('monaspa') }, { t: L({ id: 'ambri_ox', st: 3 }) }, { modsA: { barrage: 1, wire: 1, trench: 1, palisade: 1, hospital: 1, gas: 1, nest: 1, tower: 1, raid: 1, volley: 1 } });
  ok(hits(r, 'barrage').length === 1 && hits(r, 'nest').length >= 1 && hits(r, 'gas').length >= 2, 'orders'); ok(r.ev[0].a.t[0].id === '_palisade', 'palisade in front'); }
// 4) გარბენი: მაღაზია, სამეული, ნივთები, თესლი
{ const a = TL.newRun({ faction: 'colchis', seed: 7 }), b = TL.newRun({ faction: 'colchis', seed: 7 }); ok(JSON.stringify(a) === JSON.stringify(b), 'seeded run');
  ok(JSON.stringify(JSON.parse(JSON.stringify(a))) === JSON.stringify(a), 'serialisable');
  ok(a.supply === 10 && a.shop.units.length === 3 && a.lives === 5, 'round 1 setup');
  const r = TL.newRun({ faction: 'colchis', seed: 1 }); r.supply = 99;
  for (let i = 0; i < 3; i++) TL.addUnit(r, 'lashkari');
  ok(TL.all(r).filter(x => x.id === 'lashkari').length === 1 && TL.all(r)[0].st === 2 && r.pending.length === 1, 'triple merges and offers a discovery');
  ok(TL.takeDiscover(r, 0) && TL.all(r).length === 2, 'discovery adds a unit');
  const up = r.upCost; ok(TL.levelUp(r) && r.lvl === 2 && r.supply === 99 - up, 'level up');
  r.shop.items = [{ key: 'medal', cost: 3 }]; const x = TL.all(r)[0], s0 = TL.stats(x); TL.buyItem(r, 0, x.u); ok(TL.stats(x).atk === s0.atk + 2, 'medal');
  ok(TL.sell(r, x.u) && !TL.find(r, x.u), 'sell'); }
// 5) ბოტი გარბენებს თამაშობს
for (const smart of [false, true]) {
  const by = {}; let wins = 0, tot = 0; const perF = {};
  for (const f of FS) { let w = 0; for (let i = 0; i < N; i++) {
    const r = BOT.botRun(f, smart, 1000 + i * 31 + TL.hash(f) % 997, DIFF, (out, run) => { const b = by[out.round] = by[out.round] || [0, 0]; b[1]++; if (out.result === 'win') b[0]++; }, ok);
    tot++; if (r.won) { wins++; w++; } } perF[f] = Math.round(w / N * 100); }
  console.log(`\n${smart ? 'მოაზროვნე' : 'მარტივი'} ბოტი · სიმძიმე ${DIFF} · გარბენი ${tot}: მოგება ${Math.round(wins / tot * 100)}%`);
  console.log(Object.entries(perF).map(([f, v]) => f + ' ' + v + '%').join(' · '));
  console.log('ბრძოლის მოგება რაუნდით: ' + Object.keys(by).map(k => `${k}:${Math.round(by[k][0] / by[k][1] * 100)}%`).join(' '));
}
console.log(fails ? `\n${fails} FAILED` : '\nOK'); process.exit(fails ? 1 : 0);
