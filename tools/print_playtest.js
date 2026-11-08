// სათამაშო ნაკრების PDF: playtest/<name>.html → <name>.pdf (kit, cards-all, scenarios, cardgame, warbands); არგუმენტით — მხოლოდ ესენი
// გაშვება (build_playtest.py-ის შემდეგ): NODE_PATH=$(npm root -g) node tools/print_playtest.js
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  const all = ['kit', 'cards-all', 'scenarios', 'cardgame', 'warbands'], only = process.argv.slice(2);   // არგუმენტით — მხოლოდ ეს ფაილები
  for (const name of only.length ? all.filter(n => only.includes(n)) : all) {
    await p.goto('file://' + path.resolve(__dirname, '..', 'playtest', name + '.html'), { waitUntil: 'networkidle' });
    await p.emulateMedia({ media: 'print' });
    // CSS ფონის სურათები Chromium-ში მხოლოდ საჭიროებისას იტვირთება — ბეჭდვამდე ყველა წინასწარ ჩავტვირთოთ და გავშიფროთ
    const n = await p.evaluate(async () => {
      await document.fonts.ready;
      const urls = new Set();
      for (const el of document.querySelectorAll('*'))
        for (const m of getComputedStyle(el).backgroundImage.matchAll(/url\("?([^")]+)"?\)/g)) urls.add(m[1]);
      document.querySelectorAll('img').forEach(i => urls.add(i.src));
      for (const u of urls) {  // თანმიმდევრულად: ერთდროული decode() დიდ სურათებზე ზოგჯერ ვარდება
        const i = new Image();
        await new Promise((ok, bad) => { i.onload = ok; i.onerror = () => bad(new Error('სურათი ვერ ჩაიტვირთა: ' + u)); i.src = u; });
        await i.decode().catch(() => {});
        window.__keep = (window.__keep || []).concat(i);
      }
      return urls.size;
    });
    await p.waitForTimeout(500);
    // შემოწმება: PDF-ში ყველა უნიკალური სურათი უნდა იყოს ჩაწერილი, თორემ თავიდან ვბეჭდავთ
    for (let attempt = 1; ; attempt++) {
      const buf = await p.pdf({ format: 'A4', printBackground: true, preferCSSPageSize: true });
      const imgs = (buf.toString('latin1').match(/\/Subtype\s*\/Image/g) || []).length;
      if (imgs >= n) { fs.writeFileSync(path.resolve(__dirname, '..', 'playtest', name + '.pdf'), buf); break; }
      if (attempt >= 3) throw new Error(name + '.pdf: ' + imgs + '/' + n + ' სურათი — ბეჭდვა არასრულია');
      console.log(name + '.pdf: ' + imgs + '/' + n + ' სურათი, თავიდან ვცდი');
      await p.waitForTimeout(2000);
    }
    console.log('playtest/' + name + '.pdf (' + n + ' სურათი)');
  }
  await b.close();
})();
