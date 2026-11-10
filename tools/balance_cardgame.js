// „სამი ხაზის“ ბალანსი ძლიერი კომპიუტერით: ყველა სასტარტო დასტა ყველას წინააღმდეგ cardgame/index.html-ის ძრავში
// (strongAction ორივე მხარეს, უხილავ რეჟიმში). შედეგი — data/cardgame_winrates.json (მას აჩვენებს ვიკი და აპი).
// გაშვება (build_cardgame.py-ის შემდეგ): NODE_PATH=$(npm root -g) node tools/balance_cardgame.js [თამაში წყვილზე, ნაგულისხმევი 20] [პარალელური გვერდები, 4]
// სუსტი (ხარბი) მოთამაშის სწრაფი სიმულაცია — tools/sim_cardgame.py --all.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const N = +(process.argv[2] || 20), W = +(process.argv[3] || 4);
  const url = 'file://' + path.resolve(__dirname, '..', 'cardgame', 'classic.html');
  const b = await chromium.launch();
  const pages = await Promise.all(Array.from({ length: W }, async () => { const p = await b.newPage(); await p.goto(url); await p.waitForTimeout(300); return p; }));
  const fids = await pages[0].evaluate(() => Object.keys(window.CG.starter));
  const pairs = []; fids.forEach((a, i) => fids.slice(i + 1).forEach(z => pairs.push([a, z])));
  const score = Object.fromEntries(fids.map(f => [f, [0, 0]]));
  let next = 0, done = 0;
  await Promise.all(pages.map(async p => {
    while (next < pairs.length) {
      const [a, z] = pairs[next++];
      const wa = await p.evaluate(([a, z, N]) => {
        const C = window.__cg; C.headless(true); let w = 0;
        for (let g = 0; g < N; g++) {
          C.newGame({ me: a, foe: z, mode: 'test', first: g % 2 });
          C.G.p[0].level = C.G.p[1].level = 'hard';
          for (let k = 0; k < 120 && !C.G.over; k++) {
            let i = 0, act;
            while ((act = C.strongAction(C.G.cur)) && i < 60) { act(); i++; if (C.G.over) break; }
            if (!C.G.over) C.endTurn();
          }
          w += C.G.over ? (C.G.over.p === 0 ? 1 : 0) : 0.5;
        }
        return w;
      }, [a, z, N]);
      score[a][0] += wa; score[a][1] += N; score[z][0] += N - wa; score[z][1] += N;
      if (++done % 50 === 0) process.stdout.write(`${done}/${pairs.length}\n`);
    }
  }));
  await b.close();
  const win = Object.fromEntries(fids.map(f => [f, Math.round(score[f][0] / score[f][1] * 100)]));
  fs.writeFileSync(path.resolve(__dirname, '..', 'data', 'cardgame_winrates.json'), JSON.stringify({
    _comment: `balance_cardgame.js: ძლიერი კომპიუტერი ორივე მხარეს, ${N} თამაში წყვილზე — მოგების % ყველა სხვა სასტარტო დასტის წინააღმდეგ`, winrates: win }, null, 1) + '\n');
  const s = Object.entries(win).sort((x, y) => y[1] - x[1]);
  console.log(s.map(([f, v]) => `${f} ${v}%`).join(' · '));
  console.log('data/cardgame_winrates.json');
})();
