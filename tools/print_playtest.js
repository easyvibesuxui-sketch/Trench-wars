// სათამაშო ნაკრების PDF: playtest/kit.html → kit.pdf, playtest/cards-all.html → cards-all.pdf
// გაშვება (build_playtest.py-ის შემდეგ): NODE_PATH=$(npm root -g) node tools/print_playtest.js
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  for (const name of ['kit', 'cards-all', 'scenarios']) {
    await p.goto('file://' + path.resolve(__dirname, '..', 'playtest', name + '.html'), { waitUntil: 'networkidle' });
    await p.evaluate(() => document.fonts.ready);
    await p.pdf({ path: path.resolve(__dirname, '..', 'playtest', name + '.pdf'), format: 'A4', printBackground: true, preferCSSPageSize: true });
    console.log('playtest/' + name + '.pdf');
  }
  await b.close();
})();
