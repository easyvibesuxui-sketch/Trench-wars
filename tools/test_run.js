// „სანგრის რიგის“ ტესტი და ბალანსი (cardgame/engine.js): ინვარიანტები + ბოტი, რომელიც გარბენებს თამაშობს.
// გაშვება: node tools/test_run.js [გარბენი ფრაქციაზე, ნაგულისხმევი 30] [სიმძიმე, 0] [ფრაქციები მძიმით ან all] [save]
// save: მოაზროვნე ბოტის მოგების % ფრაქციებით → data/run_winrates.json და cardgame/balance.js. ფრაქციების დოქტრინის შერჩევა — tools/tune_factions.js.
// ბოტი — tools/run_bot.js.
const path = require('path');
global.window = {}; require(path.resolve(__dirname, '..', 'cardgame', 'data.js'));
const CG = window.CG, TL = require(path.resolve(__dirname, '..', 'cardgame', 'engine.js'))(CG);
const N = +(process.argv[2] || 30), DIFF = +(process.argv[3] || 0);
const FS = !process.argv[4] ? ['colchis', 'iberia', 'hell', 'harness', 'listeners', 'kajeti', 'ring', 'finnish', 'italy', 'korea']
  : process.argv[4] === 'all' ? Object.keys(CG.factions) : process.argv[4].split(',');
let fails = 0; const ok = (c, m) => { if (!c) { fails++; console.log('FAIL', m); } };

// 1) ყველა უნარს აქვს ტექსტი; ყველა ბარათს აქვს მინიმუმ ერთი უნარი; ტექსტი ორ ენაზეა
for (const id in CG.units) { const k = Object.keys(TL.traits(id)); ok(k.length > 0, 'no trait ' + id); for (const x of k) ok(TL.KW[x], 'kw ' + x); }
for (const k in TL.KW) for (const n of [1, 2, 3]) { const t = TL.KW[k].t(n); ok(t[0] && t[1], 'kw text ' + k); }
for (const k in TL.ORD) ok(CG.common[k], 'order art ' + k);
// 2) ბრძოლა დეტერმინირებულია და ყოველთვის მთავრდება
{ const a = [{ id: 'monaspa', st: 2 }, { id: 'medea_sisters' }, { id: 'lashkari' }], b = [{ id: 'monaspa', st: 2 }, { id: 'medea_sisters' }, { id: 'lashkari' }];
  const r1 = TL.simulate(a, b, {}), r2 = TL.simulate(a, b, {});
  ok(JSON.stringify(r1.ev) === JSON.stringify(r2.ev), 'deterministic'); ok(r1.ev[r1.ev.length - 1].t === 'end', 'ends'); ok(r1.rounds <= 40, 'round cap'); }
// 3) უნარების წერტილოვანი შემოწმება (ტექსტი = მოქმედება)
const hits = (r, k) => r.ev.filter(e => e.t === 'hit' && e.k === k);
{ let r = TL.simulate([{ id: 'aznauri' }], [{ id: 'port_brawlers' }], {}); ok(hits(r, 'melee').find(e => e.d === 'a0').n === 2, 'shield −1');
  r = TL.simulate([{ id: 'aznauri' }], [{ id: 'shavkhan_smiths' }], {}); ok(hits(r, 'melee').find(e => e.d === 'a0').n === 4, 'breaker ignores shield');
  r = TL.simulate([{ id: 'aznauri' }, { id: 'lashkari' }], [{ id: 'monaspa' }], {}); ok(hits(r, 'support')[0].n === 1, 'long support = half, shield min 1');
  r = TL.simulate([{ id: 'kolkhi_riders' }], [{ id: 'monaspa' }], {}); ok(hits(r, 'charge').length === 1, 'charge');
  r = TL.simulate([{ id: 'kolkhi_riders' }], [{ id: 'monaspa' }], { terrain: 'mud' }); ok(hits(r, 'charge').length === 0, 'mud stops charge');
  r = TL.simulate([{ id: 'monaspa' }, { id: 'medea_sisters' }], [{ id: 'port_brawlers' }, { id: 'port_brawlers' }], {}); ok(r.ev.some(e => e.t === 'heal' && e.n === 2), 'healer +2');
  r = TL.simulate([{ id: 'iron_arm_veterans' }], [{ id: 'ambri_ox' }], {}); ok(hits(r, 'venge').length === 1, 'last round');
  r = TL.simulate([{ id: 'ambri_ox' }], [{ id: 'iron_arm_veterans', st: 3 }], {}); ok(r.ev.some(e => e.t === 'stub'), 'stubborn');
  r = TL.simulate([{ id: 'fleece_dragon' }], [{ id: 'lashkari' }, { id: 'lashkari' }], {}); ok(hits(r, 'quake').length === 2, 'giant quake');
  r = TL.simulate([{ id: 'monaspa' }, { id: 'fleece_dragon' }], [{ id: 'monaspa' }, { id: 'lashkari' }], {}); ok(hits(r, 'air')[0].d === 'b3', 'flyer hits the rear');
  r = TL.simulate([{ id: 'monaspa' }], [{ id: 'ambri_ox', st: 3 }], { modsA: { barrage: 1, wire: 1, trench: 1, palisade: 1, hospital: 1, gas: 1, nest: 1, tower: 1, raid: 1, volley: 1, camo: 1 } });
  ok(hits(r, 'barrage').length === 1 && hits(r, 'nest').length >= 1 && hits(r, 'gas').length >= 2, 'orders'); ok(r.ev[0].a[0].id === '_palisade', 'palisade in front'); }
// 4) გარბენი: მდგომარეობა JSON-ად ინახება და იგივე თესლი იმავე რუკას იძლევა
{ const a = TL.newRun({ faction: 'colchis', seed: 7 }), b = TL.newRun({ faction: 'colchis', seed: 7 }); ok(JSON.stringify(a) === JSON.stringify(b), 'seeded run');
  ok(JSON.stringify(JSON.parse(JSON.stringify(a))) === JSON.stringify(a), 'serialisable'); }

const { botRun: _botRun } = require('./run_bot.js')(TL);
const botRun = (f, smart, seed, trace) => { const r = _botRun(f, smart, seed, DIFF, trace, ok); return r; };
const SAVE = process.argv[5] === 'save';
for (const smart of SAVE ? [true] : [false, true]) {
  const byIdx = {}; let wins = 0, tot = 0, acts = 0; const perF = {};
  for (const f of FS) { let w = 0; for (let i = 0; i < N; i++) { const r = botRun(f, smart, 1000 + i * 31 + TL.hash(f) % 997, (idx, t, out, pp, ep) => { const b = byIdx[idx] = byIdx[idx] || [0, 0, 0, 0]; b[1]++; if (out.win) b[0]++; b[2] += pp; b[3] += ep; });
    tot++; if (r.won) { wins++; w++; } acts += r.act + (r.won ? 0 : r.step / 6); } perF[f] = Math.round(w / N * 100); }
  console.log(`\n${smart ? 'მოაზროვნე' : 'მარტივი'} ბოტი · სიმძიმე ${DIFF} · გარბენი ${tot}: მოგება ${Math.round(wins / tot * 100)}% · საშ. ფრონტი ${(acts / tot).toFixed(2)}`);
  console.log(Object.entries(perF).map(([f, v]) => f + ' ' + v + '%').join(' · '));
  console.log('ბრძოლის მოგება კვანძით (მოგება% შენი/მტრის ძალა): ' + Object.keys(byIdx).map(k => `${k}:${Math.round(byIdx[k][0] / byIdx[k][1] * 100)}%(${Math.round(byIdx[k][2] / byIdx[k][1])}/${Math.round(byIdx[k][3] / byIdx[k][1])})`).join(' '));
  if (SAVE && smart) { const fs = require('fs'), c = `test_run.js: მოაზროვნე ბოტი, ${N} გარბენი ფრაქციაზე, სიმძიმე ${DIFF} — გარბენის მოგების %`;
    fs.writeFileSync(path.resolve(__dirname, '..', 'data', 'run_winrates.json'), JSON.stringify({ _comment: c, winrates: perF }, null, 1) + '\n');
    fs.writeFileSync(path.resolve(__dirname, '..', 'cardgame', 'balance.js'), '// ' + c + '\nwindow.TLBAL = ' + JSON.stringify(perF) + ';\n'); console.log('data/run_winrates.json · cardgame/balance.js'); }
}
console.log(fails ? `\n${fails} FAILED` : '\nOK'); process.exit(fails ? 1 : 0);
