// „სანგრის რიგის“ ფრაქციების ბალანსი. ყოველ ფრაქციას აქვს დოქტრინა — დამატებითი მარაგი ყოველ მობილიზაციაზე (წილადი, −2…+4, ნაბიჯი 0.25).
// „მოაზროვნე“ ბოტი (tools/run_bot.js, დეტერმინირებული) ყველა ფრაქციით თამაშობს ერთსა და იმავე თესლებზე; დოქტრინა მოგების
// სამიზნისგან (50%) გადახრის პროპორციულად იცვლება (≈25% მოგება = 1 მარაგი; ნაბიჯი ჩახშობილია, რომ არ ირხეოდეს).
// შედეგი: cardgame/engine.js-ის DOC ცხრილი; ბოლო გაზომვა — data/run_winrates.json და cardgame/balance.js (აპის „ადვილი/საშუალო/რთული“).
// გაშვება: node tools/tune_factions.js [გარბენი ფრაქციაზე, 150] [იტერაციები, 8]
const fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..'), ENG = path.join(ROOT, 'cardgame', 'engine.js');
global.window = {}; require(path.join(ROOT, 'cardgame', 'data.js')); const CG = window.CG;
const N = +(process.argv[2] || 150), IT = +(process.argv[3] || 8), TARGET = 50, BAND = 5, SLOPE = 25;
const FS = Object.keys(CG.factions);
const load = () => { delete require.cache[ENG]; return require(ENG)(CG); };
const q4 = x => Math.round(x * 4) / 4;
function writeDoc(D) {
  const doc = {}; for (const f of FS) if (D[f]) doc[f] = D[f];
  fs.writeFileSync(ENG, fs.readFileSync(ENG, 'utf8').replace(/\/\*DOC\*\/[\s\S]*?\/\*\/DOC\*\//, '/*DOC*/' + JSON.stringify(doc) + '/*/DOC*/'));
}
function measure(n, off) {
  const TL = load(), bot = require('./run_bot.js')(TL), w = {};
  for (const f of FS) { let k = 0; for (let i = 0; i < n; i++) if (bot.botRun(f, true, off + i * 31 + TL.hash(f) % 997, 0).won) k++; w[f] = Math.round(k / n * 100); }
  return w;
}
const D = JSON.parse((fs.readFileSync(ENG, 'utf8').match(/\/\*DOC\*\/([\s\S]*?)\/\*\/DOC\*\//) || [, '{}'])[1]);
for (const f of FS) D[f] = D[f] || 0;
let w;
for (let it = 0; it < IT; it++) {
  w = measure(N, 7000); let moved = 0;
  for (const f of FS) { const err = TARGET - w[f]; if (Math.abs(err) <= BAND) continue;
    const nd = Math.max(-2, Math.min(4, q4(D[f] + .7 * err / SLOPE))); if (nd !== D[f]) { D[f] = nd; moved++; } }
  const out = FS.filter(f => Math.abs(w[f] - TARGET) > BAND).length;
  console.log(`იტერაცია ${it + 1}: ±${BAND}%-ს გარეთ ${out}/${FS.length} · ` + FS.map(f => `${f} ${w[f]}` + (D[f] ? `(${D[f] > 0 ? '+' : ''}${D[f]})` : '')).join(' · '));
  writeDoc(D); if (!moved) break;
}
w = measure(N * 2, 90000);                          // შემოწმება სხვა თესლებზე, რომ ბალანსი თესლებზე „არ მოერგოს“
const v = Object.values(w), avg = v.reduce((a, b) => a + b, 0) / v.length;
console.log(`\nშემოწმება (${N * 2} ახალი გარბენი): საშუალო ${avg.toFixed(0)}% · მინ ${Math.min(...v)}% · მაქს ${Math.max(...v)}%`);
console.log(FS.map(f => `${f} ${w[f]}% (${D[f] > 0 ? '+' : ''}${D[f]})`).join(' · '));
const c = `tune_factions.js: მოაზროვნე ბოტი, ${N * 2} გარბენი ფრაქციაზე, სიმძიმე 0, დოქტრინებით — გარბენის მოგების %`;
fs.writeFileSync(path.join(ROOT, 'data', 'run_winrates.json'), JSON.stringify({ _comment: c, winrates: w, doctrine: D }, null, 1) + '\n');
fs.writeFileSync(path.join(ROOT, 'cardgame', 'balance.js'), '// ' + c + '\nwindow.TLBAL = ' + JSON.stringify(w) + ';\n');
console.log('cardgame/engine.js (DOC) · data/run_winrates.json · cardgame/balance.js');
