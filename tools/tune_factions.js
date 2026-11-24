// „სანგრის რიგის“ (v2) ბალანსი. ორი სახელური cardgame/engine.js-ში:
//   GB  — მოჩვენება-ჯარების დამატებითი მარაგი რაუნდში (ყველასთვის): საშუალო მოგება სამიზნესთან (50%) მიჰყავს;
//   DOC — ფრაქციის ლოჯისტიკა: დამატებითი მარაგი რაუნდში მხოლოდ მოთამაშის ჯარს (წილადი, −3…+5, ნაბიჯი 0.25) — ფრაქციებს ათანაბრებს.
// „მოაზროვნე“ ბოტი (tools/run_bot.js, დეტერმინირებული) ყველა ფრაქციით თამაშობს ერთსა და იმავე თესლებზე; სახელურები სამიზნიდან
// გადახრის პროპორციულად იცვლება (ჩახშობით). ბოლოს — შემოწმება ახალ თესლებზე → data/run_winrates.json, cardgame/balance.js.
// გაშვება: node tools/tune_factions.js [გარბენი ფრაქციაზე, 80] [იტერაციები, 8]
const fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..'), ENG = path.join(ROOT, 'cardgame', 'engine.js');
global.window = {}; require(path.join(ROOT, 'cardgame', 'data.js')); const CG = window.CG;
const N = +(process.argv[2] || 80), IT = +(process.argv[3] || 8), TARGET = 50, BAND = 6, SLOPE = 35;   // ≈35% მოგება = 1 მარაგი რაუნდში
const FS = Object.keys(CG.factions);
const load = () => { delete require.cache[ENG]; return require(ENG)(CG); };
const q4 = x => Math.round(x * 4) / 4;
const src = () => fs.readFileSync(ENG, 'utf8');
function write(D, gb) {
  const doc = {}; for (const f of FS) if (D[f]) doc[f] = D[f];
  fs.writeFileSync(ENG, src().replace(/\/\*DOC\*\/[\s\S]*?\/\*\/DOC\*\//, '/*DOC*/' + JSON.stringify(doc) + '/*/DOC*/').replace(/\/\*GB\*\/[\s\S]*?\/\*\/GB\*\//, '/*GB*/' + gb + '/*/GB*/'));
}
function measure(n, off) {
  const TL = load(), bot = require('./run_bot.js')(TL), w = {};
  for (const f of FS) { let k = 0; for (let i = 0; i < n; i++) if (bot.botRun(f, true, off + i * 31 + TL.hash(f) % 997, 0).won) k++; w[f] = Math.round(k / n * 100); }
  return w;
}
const D = JSON.parse((src().match(/\/\*DOC\*\/([\s\S]*?)\/\*\/DOC\*\//) || [, '{}'])[1]);
let gb = +((src().match(/\/\*GB\*\/([\s\S]*?)\/\*\/GB\*\//) || [, '0'])[1]);
for (const f of FS) D[f] = D[f] || 0;
let w;
for (let it = 0; it < IT; it++) {
  const t0 = Date.now(); w = measure(N, 7000);
  const avg = FS.reduce((a, f) => a + w[f], 0) / FS.length;
  // GB: საშუალოსთვის (მოჩვენება ძლიერდება → მოგება მცირდება); DOC: ფრაქციის გადახრა საშუალოდან
  const ngb = q4(gb + .5 * (avg - TARGET) / SLOPE); let moved = ngb !== gb ? 1 : 0; gb = ngb;
  for (const f of FS) { const err = avg - w[f]; if (Math.abs(w[f] - TARGET) <= BAND && Math.abs(err) <= BAND) continue;
    const nd = Math.max(-3, Math.min(5, q4(D[f] + .5 * err / SLOPE))); if (nd !== D[f]) { D[f] = nd; moved++; } }
  const out = FS.filter(f => Math.abs(w[f] - TARGET) > BAND).length;
  console.log(`იტერაცია ${it + 1} (${((Date.now() - t0) / 1000).toFixed(0)} წმ): საშუალო ${avg.toFixed(0)}% · GB ${gb} · ±${BAND}%-ს გარეთ ${out}/${FS.length} · ` + FS.map(f => `${f} ${w[f]}` + (D[f] ? `(${D[f] > 0 ? '+' : ''}${D[f]})` : '')).join(' · '));
  write(D, gb); if (!moved) break;
}
w = measure(N * 2, 90000);
const v = Object.values(w), avg = v.reduce((a, b) => a + b, 0) / v.length;
console.log(`\nშემოწმება (${N * 2} ახალი გარბენი): საშუალო ${avg.toFixed(0)}% · მინ ${Math.min(...v)}% · მაქს ${Math.max(...v)}% · GB ${gb}`);
console.log(FS.map(f => `${f} ${w[f]}% (${D[f] > 0 ? '+' : ''}${D[f]})`).join(' · '));
const c = `tune_factions.js: მოაზროვნე ბოტი, ${N * 2} გარბენი ფრაქციაზე (შემოწმების თესლები), სიმძიმე 0 — გარბენის მოგების %`;
fs.writeFileSync(path.join(ROOT, 'data', 'run_winrates.json'), JSON.stringify({ _comment: c, winrates: w, doctrine: D, ghost_bias: gb }, null, 1) + '\n');
fs.writeFileSync(path.join(ROOT, 'cardgame', 'balance.js'), '// ' + c + '\nwindow.TLBAL = ' + JSON.stringify(w) + ';\n');
console.log('cardgame/engine.js (DOC, GB) · data/run_winrates.json · cardgame/balance.js');
