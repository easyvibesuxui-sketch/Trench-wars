// ყველა ფრაქციის ავტომატური ტესტი: ძირითადი 4 + ყველა მოკავშირე
// გაშვება: NODE_PATH=$(npm root -g) node tools/test_builder.js   (საჭიროა playwright და chromium)
const { chromium } = require('playwright');
const path = require('path');
const PAGE = 'file://' + path.resolve(__dirname, '..', 'builder', 'index.html');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(PAGE); await p.waitForTimeout(400);
  const D = await p.evaluate(() => ({ factions: window.TW_DATA.factions, allies: window.TW_DATA.allies, units: window.TW_DATA.units }));
  const fails = [];
  const D2 = await p.evaluate(() => ({ campaigns: window.TW_DATA.campaigns || {} }));
  for (const f of [...Object.keys(D.factions), ...Object.keys(D.allies)]) {
    const c = D2.campaigns[f];
    if (!c || c.scenarios.length < 5 || !c.sacrifice || !c.ending) fails.push(`${f}: ომის კამპანია არასრულია`);
  }
  const checks = () => p.$$eval('#checks li', l => l.map(x => x.className + '|' + x.textContent.trim()));
  const clickAdd = async id => { const btn = await p.$(`#catalog [data-add="${id}"]`); if (!btn || await btn.isDisabled()) return false; await btn.click(); return true; };
  const all = [...Object.keys(D.factions).map(f => [f, false]), ...Object.keys(D.allies).map(f => [f, true])];
  for (const [f, ally] of all) {
    await p.click('#clearBtn');
    await p.selectOption('#budget', '500');
    if (await p.isChecked('#scenario')) await p.click('#scenario');
    if (ally) await p.selectOption('#allySel', f); else await p.click(`[data-f="${f}"]`);
    await p.click('#clearBtn');
    const own = D.units.filter(u => u.faction === f);
    const heads = await p.$$eval('#catalog > section.tier:not(.allies):not(.alliance):not(.gear) h2', h => h.map(x => x.textContent));
    for (const t of ['II', 'IV', 'V']) if (!heads.some(h => h.startsWith(t + '.'))) fails.push(`${f}: კატალოგში ${t} დონე არ ჩანს`);
    // რეგულარული ჯარი: აირწინაღიანი რიგითები და სანგრის მოჩხუბრები ყველას ჰყავს და კატალოგში ჩანს
    for (const [tag, what] of [['gas_mask', 'რიგითები/აირწინაღი'], ['brawler', 'მოჩხუბრები']]) {
      const u = own.find(x => x.tier === 'I' && x.tags.includes(tag));
      if (!u || !await p.$(`#catalog > section.tier [data-add="${u.id}"]`)) fails.push(`${f}: ${what} კატალოგში არ ჩანს`);
    }
    // ლიდერი + იაფი იუნიტები 500-ში
    const leader = own.find(u => u.tags.includes('leader') && ['I', 'II', 'III'].includes(u.tier));
    if (!leader || !await clickAdd(leader.id)) { fails.push(`${f}: ლიდერი ვერ დაემატა`); continue; }
    const cheap = own.filter(u => ['I', 'II'].includes(u.tier) && !u.tags.includes('leader')).sort((a, c) => a.cost - c.cost)[0];
    for (let i = 0; i < 3; i++) await clickAdd(cheap.id);
    let c = await checks();
    if (c.some(x => x.startsWith('bad'))) fails.push(`${f}: 500-იანი რაზმი არასწორია: ${c.filter(x => x.startsWith('bad')).join('; ')}`);
    // გროტესკი 1000-ში; მეორე IV დაბლოკილია
    await p.selectOption('#budget', '1000');
    const iv = own.find(u => u.tier === 'IV');
    if (!await clickAdd(iv.id)) fails.push(`${f}: IV ვერ დაემატა 1000-ში`);
    const iv2 = await p.$(`#catalog [data-add="${iv.id}"]`);
    if (iv2 && !await iv2.isDisabled()) fails.push(`${f}: მეორე IV არ დაიბლოკა`);
    // გოლიათი მხოლოდ სცენარით
    const v = own.find(u => u.tier === 'V');
    const vb = await p.$(`#catalog [data-add="${v.id}"]`);
    if (vb && !await vb.isDisabled()) fails.push(`${f}: გოლიათი სცენარის გარეშე ხელმისაწვდომია`);
    await p.click('#scenario');
    if (!await clickAdd(v.id)) fails.push(`${f}: გოლიათი სცენარით ვერ დაემატა`);
    c = await checks();
    const bad = c.filter(x => x.startsWith('bad') && !x.includes('ბიუჯეტი'));
    if (bad.length) fails.push(`${f}: სცენარის რაზმი: ${bad.join('; ')}`);
    // დაქირავების სექცია: მხოლოდ კოლხეთსა და იბერიაში
    const hasAllies = !!(await p.$('#catalog section.allies'));
    if (hasAllies !== ['colchis', 'iberia', 'ring'].includes(f)) fails.push(`${f}: დაქირავების სექცია ${hasAllies ? 'ჩანს' : 'არ ჩანს'}`);
    // მოკავშირედ თამაშისას საკუთარი იუნიტები არ ძვირდება
    if (ally) {
      const price = await p.$eval(`#catalog [data-add="${cheap.id}"]`, b => b.closest('.card').querySelector('.cost').textContent);
      if (price.includes('+20%')) fails.push(`${f}: საკუთარ იუნიტს დაქირავების ფასი აქვს`);
    }
    // ექსპორტი ტექსტად
    await p.click('#copyBtn');
    const txt = await p.$eval('#exportBox', x => x.value);
    if (!txt.includes(ally ? D.allies[f] : D.factions[f])) fails.push(`${f}: ექსპორტში ფრაქციის სახელი არ არის`);
  }
  // რაოდენობის ლიმიტი: 500-ზე I დონე მაქს. 10
  await p.click('[data-f="colchis"]'); await p.click('#clearBtn'); await p.selectOption('#budget', '500');
  for (let i = 0; i < 10; i++) await clickAdd('lashkari');
  const lb = await p.$('#catalog [data-add="lashkari"]');
  if (!lb || !await lb.isDisabled()) fails.push('რაოდენობის ლიმიტი: მე-11 ლაშქარი არ დაიბლოკა');
  // რგოლის ბატალიონი: ხარკი — 50%, ფასნამატის გარეშე
  await p.click('[data-f="ring"]'); await p.click('#clearBtn'); await p.selectOption('#budget', '500');
  if (await p.isChecked('#scenario')) await p.click('#scenario');
  const hel = D.units.find(u => u.id === 'automaton_phalanx');
  const rp = await p.$eval('#catalog section.allies [data-add="automaton_phalanx"]', b => b.closest('.card').querySelector('.cost').textContent.trim());
  if (rp !== String(hel.cost)) fails.push(`რგოლის ბატალიონი: მოკავშირის ფასი ${rp} ≠ ${hel.cost}`);
  const capTxt = await p.$eval('#catalog section.allies .tier-note', x => x.textContent);
  if (!capTxt.includes('50%') || !capTxt.includes('250')) fails.push('რგოლის ბატალიონი: დაქირავების ლიმიტი 50% (250) არ ჩანს');
  // დაქირავება კოლხეთში: ლიდერი დაბლოკილია, IV/V წესები
  await p.click('[data-f="colchis"]'); await p.click('#clearBtn'); await p.selectOption('#budget', '1000');
  if (await p.isChecked('#scenario')) await p.click('#scenario');
  const allyLeaders = await p.$$('#catalog section.allies [data-add$="_leader"]');
  if (allyLeaders.length) fails.push('დაქირავების სიაში მოკავშირე ლიდერები ჩანს');
  const ownIv = D.units.find(u => u.faction === 'colchis' && u.tier === 'IV');
  await clickAdd(ownIv.id);
  const hiredIv = await p.$('#catalog section.allies [data-add="armenian_grotesque"]');
  if (hiredIv && !await hiredIv.isDisabled()) fails.push('საკუთარი IV-ის შემდეგ დაქირავებული IV არ დაიბლოკა');
  const hiredV = await p.$('#catalog section.allies [data-add="armenian_giant"]');
  if (hiredV && !await hiredV.isDisabled()) fails.push('დაქირავებული გოლიათი სცენარის გარეშე ხელმისაწვდომია');
  // ალიანსი: პრუსია + კოლხეთი + ოსმალები; კონტინგენტი 30%, ფასნამატის გარეშე, პარტნიორის ლიდერი არ ჩანს
  await p.selectOption('#allySel', 'prussia'); await p.click('#clearBtn'); await p.selectOption('#budget', '500');
  if (await p.isChecked('#scenario')) await p.click('#scenario');
  const darkOpts = await p.$$eval('#allianceA option', o => o.map(x => x.value));
  if (darkOpts.includes('hell') || darkOpts.includes('harness')) fails.push('ალიანსი: ნათელ ფრაქციას ბნელი პარტნიორი სთავაზობს');
  await p.selectOption('#allianceA', 'colchis'); await p.selectOption('#allianceB', 'ottoman');
  if (!await p.$('#catalog section.alliance')) fails.push('ალიანსის კონტინგენტი არ ჩანს');
  if (await p.$('#catalog section.alliance [data-add="eristavi"]')) fails.push('ალიანსში პარტნიორის ლიდერი ჩანს');
  const jan = D.units.find(u => u.id === 'janissaries');
  const jp = await p.$eval('#catalog section.alliance [data-add="janissaries"]', b => b.closest('.card').querySelector('.cost').textContent.trim());
  if (jp !== String(jan.cost)) fails.push(`ალიანსი: იანიჩრების ფასი ${jp} ≠ ${jan.cost}`);
  await clickAdd('prussia_leader');
  let added = 0; while (await clickAdd('janissaries')) added++;
  if (added * jan.cost > 150 || (added < 6 && (added + 1) * jan.cost <= 150)) fails.push(`ალიანსის ლიმიტი (150) არ მუშაობს: ${added} იანიჩარი`);
  let ac = await checks();
  if (!ac.some(x => x.startsWith('good') && x.includes('ალიანსი'))) fails.push('ალიანსის შემოწმება არ ჩანს');
  await p.click('#copyBtn');
  if (!(await p.$eval('#exportBox', x => x.value)).includes('ალიანსი: კოლხეთი')) fails.push('ექსპორტში ალიანსი არ ჩანს');
  // ალიანსის დაშლა პარტნიორის იუნიტებს რაზმიდან აშორებს
  await p.selectOption('#allianceB', '');
  if ((await p.$$eval('#roster li', l => l.map(x => x.textContent).join('|'))).includes('იანიჩრები')) fails.push('ალიანსის დაშლის შემდეგ იანიჩრები რაზმში დარჩა');
  // ბნელი ალიანსი: ლეგიონები + დიდი უღელი
  await p.click('[data-f="hell"]'); await p.click('#clearBtn');
  const hellOpts = await p.$$eval('#allianceA option', o => o.map(x => x.value));
  if (!hellOpts.includes('harness') || hellOpts.includes('colchis')) fails.push('ბნელი ალიანსის პარტნიორები არასწორია');
  await p.selectOption('#allianceA', 'harness');
  if (!await p.$('#catalog section.alliance')) fails.push('ბნელი ალიანსის კონტინგენტი არ ჩანს');
  ac = await checks();
  if (!ac.some(x => x.includes('შიდა ომი'))) fails.push('ბნელ ალიანსს შიდა ომის წესი არ აქვს');
  // კამპანია მოკავშირე ფრაქციით
  await p.selectOption('#allySel', 'gulf'); await p.click('#clearBtn');
  await clickAdd('gulf_leader'); await clickAdd('pearl_divers');
  await p.click('#tabCampaign'); await p.waitForTimeout(200);
  if (await p.$eval('#buildView', v => getComputedStyle(v).display !== 'none')) fails.push('კამპანიის ჩანართზე აწყობის ხედი ისევ ჩანს');
  const brief = await p.$eval('#campaignView', v => v.textContent);
  if (!brief.includes(D2.campaigns.gulf.title)) fails.push('კამპანიამდე ფრაქციის ომის კამპანია არ ჩანს');
  const startBtn = await p.$('#campaignView button');
  if (startBtn) { await startBtn.click(); await p.waitForTimeout(200); }
  const campHead = await p.$eval('#campaignView', v => v.textContent.slice(0, 200));
  if (!campHead.includes('ყურისა')) fails.push('კამპანიაში მოკავშირე ფრაქციის სახელი არ ჩანს: ' + campHead.slice(0, 80));
  // ბაზა: ბლინდაჟის აშენება ლიმიტს ზრდის და ხაზინას ამცირებს
  const capBefore = await p.$eval('#campaignView .base .sub', x => x.textContent);
  const dug = await p.$('#campaignView [data-build="dugout"]');
  if (!dug) fails.push('ბაზის პანელი (ბლინდაჟი) არ ჩანს');
  else if (!await dug.isDisabled()) {
    await dug.click(); await p.waitForTimeout(150);
    const capAfter = await p.$eval('#campaignView .base .sub', x => x.textContent);
    if (capAfter === capBefore || !capAfter.includes('18')) fails.push(`ბლინდაჟმა ლიმიტი არ გაზარდა: ${capAfter}`);
  }
  // ომის კამპანია: პირველი სცენარის მოგება მას აღნიშნავს
  await p.selectOption('#bResult', 'win');
  await p.click('#battleForm button[type="submit"]'); await p.waitForTimeout(200);
  const doneCount = await p.$$eval('#campaignView .scenarios li.done', l => l.length);
  if (doneCount !== 1) fails.push(`მოგებული სცენარი არ აღინიშნა (${doneCount})`);
  const log = await p.$eval('#campaignView', v => v.textContent);
  if (!log.includes(D2.campaigns.gulf.scenarios[0].name)) fails.push('ჟურნალში სცენარის სახელი არ ჩაიწერა');
  // ტელეფონის სიგანე
  const m = await b.newPage({ viewport: { width: 390, height: 800 } });
  await m.goto(PAGE); await m.waitForTimeout(300);
  if (await m.evaluate(() => document.documentElement.scrollWidth > innerWidth)) fails.push('ტელეფონზე ჰორიზონტალური გადახვევა');
  console.log(`ფრაქციები: ${all.length} · ჩავარდნები: ${fails.length} · JS შეცდომები: ${errs.length}`);
  fails.forEach(x => console.log('✕', x)); errs.forEach(x => console.log('JS', x));
  await b.close();
  process.exit(fails.length || errs.length ? 1 : 0);
})();
