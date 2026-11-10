// „სანგრის რიგი“ — ძრავა. ავტომატური ბრძოლა რიგში (წინა იუნიტი წინას ებრძვის, უკანანი ეხმარებიან), მობილიზაცია (მაღაზია),
// სამი ერთნაირის შერწყმა, გარბენის რუკა სამი ფრონტით, რელიეფი, ბრძანებები, რელიქვიები. არანაირი შემთხვევითობა ბრძოლაში:
// ერთი და იგივე რიგი ერთსა და იმავე მტერთან ყოველთვის ერთნაირად მთავრდება. გამოიყენება ბრაუზერში (window.TL) და node-ში
// (require('./engine.js')(CG)). ბარათების მონაცემები — cardgame/data.js (tools/build_cardgame.py).
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory;
  else root.TL = factory(root.CG);
})(typeof self !== 'undefined' ? self : this, function (CG) {
  'use strict';
  const U = CG.units, F = CG.factions;
  const price = id => { const c = (U[id] || { cost: 2 }).cost; return c <= 3 ? c : Math.min(7, Math.ceil(c / 2) + 1); };   // მობილიზაციის ფასი ბარათის სიძლიერიდან: 1–7
  const LARGE = { IV: 1, 'IV+': 1, V: 1 };
  const MULT = [0, 1, 2, 3.5];                       // ვარსკვლავების მამრავლი: ★, ★★, ★★★
  const SLOTS = [0, 3, 4, 5, 6, 6, 6];               // რიგის ადგილები წოდების მიხედვით
  const RES = 3;                                     // რეზერვის ადგილები
  const ODDS = [null,                                // რომელი დონის ბარათებს გთავაზობს მობილიზაცია, წოდებით
    { I: 100 }, { I: 65, II: 35 }, { I: 40, II: 40, III: 20 }, { I: 25, II: 35, III: 25, IV: 10, hero: 5 },
    { I: 15, II: 30, III: 25, IV: 15, 'IV+': 8, hero: 7 }, { I: 10, II: 22, III: 25, IV: 18, 'IV+': 10, V: 7, hero: 8 }];
  const STEPS = 6, ACTS = 3;

  // ---- უნარები: ტექსტი და მოქმედება ერთ ადგილას; n — ვარსკვლავების რაოდენობა ----
  const KW = {
    long: { ka: 'შორი', en: 'Long', t: n => ['მე-2 ან მე-3 ადგილიდან ყოველ რაუნდში მტრის წინა იუნიტს თავისი შეტევის ნახევარს აყენებს.', 'From the 2nd or 3rd place, hits the enemy front for half its attack every round.'] },
    shield: { ka: 'ფარი', en: 'Shield', t: n => [`ყოველ დარტყმაზე −${n} ზიანი (მინ. 1).`, `Takes −${n} from every hit (min. 1).`] },
    breaker: { ka: 'მტვრევა', en: 'Breaker', t: n => ['მისი დარტყმა უგულებელყოფს ფარს, თხრილს და საფარს.', 'Its hits ignore shields, trenches and cover.'] },
    charge: { ka: 'იერიში', en: 'Charge', t: n => ['ბრძოლის დასაწყისში მტრის წინა იუნიტს თავის შეტევას აყენებს.', 'At the start of battle, hits the enemy front for its attack.'] },
    scout: { ka: 'მზვერავი', en: 'Scout', t: n => [`ბრძოლის დასაწყისში მტრის ბოლო იუნიტს ${2 * n} ზიანს აყენებს.`, `At the start of battle, deals ${2 * n} damage to the enemy's last unit.`] },
    leader: { ka: 'მეთაური', en: 'Leader', t: n => [`მეზობელ იუნიტებს +${n} შეტევა.`, `Neighbouring units get +${n} attack.`] },
    healer: { ka: 'მკურნალი', en: 'Healer', t: n => [`რაუნდის ბოლოს მის წინ მდგომს ${n + 1} მდგრადობას უბრუნებს.`, `At the end of a round, restores ${n + 1} resilience to the unit in front of it.`] },
    digger: { ka: 'მესანგრე', en: 'Digger', t: n => [`ბრძოლის დასაწყისში შენს წინა იუნიტს +${2 * n} საფარი.`, `At the start of battle, your front unit gets +${2 * n} cover.`] },
    fire: { ka: 'ცეცხლი', en: 'Fire', t: n => [`დარტყმული მტერი იწვის: რაუნდის ბოლოს ${n} ზიანი.`, `An enemy it hits burns: ${n} damage at the end of each round.`] },
    suppress: { ka: 'დათრგუნვა', en: 'Suppress', t: n => ['დარტყმული მტერი ბრძოლის ბოლომდე −1 შეტევას იღებს (მაქს. −3).', 'An enemy it hits gets −1 attack for the rest of the battle (max. −3).'] },
    fearless: { ka: 'უშიშარი', en: 'Fearless', t: n => ['დათრგუნვა მასზე არ მოქმედებს.', 'Cannot be suppressed.'] },
    hunter: { ka: 'მონადირე', en: 'Hunter', t: n => [`+${3 * n} ზიანი დიდ მტერზე (IV დონე და ზემოთ).`, `+${3 * n} damage against large enemies (tier IV and up).`] },
    fly: { ka: 'ფრენა', en: 'Flying', t: n => ['უკანა ადგილიდან ყოველ რაუნდში მტრის ბოლო იუნიტს ურტყამს.', 'From behind the front, strikes the enemy\'s last unit every round.'] },
    anti_air: { ka: 'საზენიტო', en: 'Anti-air', t: n => [`ყოველ რაუნდში მტრის პირველ მფრინავს ${2 * n} ზიანს აყენებს.`, `Every round deals ${2 * n} damage to the first enemy flyer.`] },
    regen: { ka: 'ამოზრდა', en: 'Regrowth', t: n => [`რაუნდის ბოლოს +${n} მდგრადობა.`, `+${n} resilience at the end of each round.`] },
    giant: { ka: 'გოლიათი', en: 'Giant', t: n => [`როცა წინა ადგილზე გადის, ყველა მტერს ${2 * n} ზიანს აყენებს. რიგში მაქს. 1.`, `When it steps to the front, deals ${2 * n} damage to every enemy. Max. 1 in the line.`] },
    hero: { ka: 'გმირი', en: 'Hero', t: n => ['ყოველი მოგებული ბრძოლის შემდეგ სამუდამოდ +1/+1. რიგში მაქს. 1; არ ერთიანდება.', 'Permanently +1/+1 after every battle won. Max. 1 in the line; does not merge.'] },
    vengeance: { ka: 'ბოლო ტყვია', en: 'Last Round', t: n => ['დაღუპვისას მტრის წინა იუნიტს თავისი შეტევის ნახევარს აყენებს.', 'When it falls, hits the enemy front for half its attack.'] },
    stubborn: { ka: 'ჯიუტი', en: 'Stubborn', t: n => ['პირველ სასიკვდილო დარტყმას 1 მდგრადობით გადაურჩება.', 'Survives its first lethal blow with 1 resilience.'] },
    brother: { ka: 'ძმობა', en: 'Brotherhood', t: n => [`როცა მოკავშირე ეცემა, +${n}/+${n}.`, `Gets +${n}/+${n} whenever an ally falls.`] }
  };
  const _tr = {};
  function traits(id) {                              // ბარათის უნარები; უუნარო ბარათი თავის ხასიათს სტატებიდან იღებს
    if (_tr[id]) return _tr[id];
    const d = U[id], o = {};
    if (d) { for (const k of d.kw) if (KW[k]) o[k] = 1;
      if (!Object.keys(o).some(k => k !== 'hero' && k !== 'giant')) o[d.atk > d.hp ? 'vengeance' : d.hp > d.atk ? 'stubborn' : 'brother'] = 1; }
    return _tr[id] = o;
  }
  const SPECIAL = {
    _sparti: { ka: 'სპარტი', en: 'Sown Warrior', atk: 3, hp: 3, tier: 'I', f: null, art: null },
    _palisade: { ka: 'მესერი', en: 'Palisade', atk: 0, hp: 6, tier: 'I', f: null, art: CG.common.palisade.art }
  };
  const def = id => U[id] || SPECIAL[id];

  // ---- ბრძანებები (ერთჯერადი ბარათები) ----
  const ORD = {
    trench: { cost: 1, t: ['ამ ბრძოლაში შენი წინა იუნიტი ყოველ დარტყმაზე −1 ზიანს იღებს (მინ. 1).', 'This battle, your front unit takes −1 from every hit (min. 1).'] },
    wire: { cost: 1, t: ['პირველ რაუნდში მტრის წინა იუნიტი ვერ ურტყამს.', 'In the first round, the enemy front cannot strike.'] },
    palisade: { cost: 2, t: ['რიგის წინ დგება მესერი (0/6): მტერმა ჯერ ის უნდა დაანგრიოს.', 'A palisade (0/6) stands in front of your line: the enemy must tear it down first.'] },
    nest: { cost: 3, t: ['ყოველ რაუნდში მტრის წინა იუნიტს 2 ზიანი.', 'Every round, 2 damage to the enemy front.'] },
    tower: { cost: 2, t: ['ყოველ რაუნდში მტრის ბოლო იუნიტს 1 ზიანი.', 'Every round, 1 damage to the enemy\'s last unit.'] },
    porter: { cost: 3, now: 1, t: ['მუდმივად +1 მარაგი ყოველ მობილიზაციაზე (მაქს. 3).', 'Permanently +1 supply at every muster (max. 3).'] },
    barrage: { cost: 3, t: ['ბრძოლის დასაწყისში ყველა მტერს 2 ზიანი.', 'At the start of battle, 2 damage to every enemy.'] },
    gas: { cost: 2, t: ['პირველი 3 რაუნდის ბოლოს ყველა იუნიტს 1 ზიანი — შენსაც. ფარი და საფარი არ შველის.', 'At the end of the first 3 rounds, 1 damage to every unit — yours too. Shields and cover do not help.'] },
    raid: { cost: 2, t: ['ბრძოლის დასაწყისში შენი ბოლო იუნიტი მტრის ბოლო იუნიტს ურტყამს.', 'At the start of battle, your last unit strikes the enemy\'s last unit.'] },
    hospital: { cost: 2, t: ['შენი პირველი დაღუპული იუნიტი ნახევარი მდგრადობით ბრუნდება რიგის ბოლოში.', 'Your first fallen unit returns to the back of the line with half its resilience.'] },
    recon: { cost: 1, now: 1, t: ['მაშინვე: 2 უფასო განახლება.', 'At once: 2 free rerolls.'] },
    train: { cost: 2, now: 1, t: ['მაშინვე: +4 მარაგი.', 'At once: +4 supply.'] },
    volley: { cost: 2, t: ['ამ ბრძოლაში შენს ყველა იუნიტს +1 შეტევა.', 'This battle, all your units get +1 attack.'] },
    camo: { cost: 1, t: ['ამ ბრძოლაში შენს ბოლო ორ იუნიტს უკნიდან ვერ ურტყამენ (მფრინავი, მზვერავი, რეიდი, კოშკი).', 'This battle, your last two units cannot be struck from behind (flyers, scouts, raids, towers).'] }
  };
  // ---- რელიქვიები (მთელი გარბენის განმავლობაში მოქმედებს) ----
  const REL = {
    rib: ['ამბრის ნეკნი', 'Ambri\'s Rib', 'შენი წინა იუნიტი ყოველ ბრძოლას +3 საფარით იწყებს.', 'Your front unit starts every battle with +3 cover.'],
    chain: ['ხვამლის ჯაჭვი', 'Chain of Khvamli', 'ბრძოლის დასაწყისში მტრის წინა იუნიტი დათრგუნულია (−1 შეტევა).', 'At the start of battle, the enemy front is suppressed (−1 attack).'],
    cauldron: ['მედეას ქვაბი', 'Medea\'s Cauldron', 'ყოველ ბრძოლაში შენი პირველი დაღუპული იუნიტი 1 მდგრადობით ცოცხლდება.', 'In every battle, your first fallen unit revives with 1 resilience.'],
    tooth: ['დრაკონის კბილი', 'Dragon\'s Tooth', 'ყოველი ბრძოლის დასაწყისში რიგის ბოლოს ამოიზრდება სპარტი (3/3).', 'At the start of every battle, a Sown Warrior (3/3) sprouts at the back of your line.'],
    fleece: ['საწმისის ნაგლეჯი', 'Scrap of the Fleece', '+1 მარაგი ყოველ მობილიზაციაზე.', '+1 supply at every muster.'],
    hammer: ['შავხანის ჩაქუჩი', 'Shavkhan\'s Hammer', '★★ და ★★★ იუნიტებს +2 შეტევა.', '★★ and ★★★ units get +2 attack.'],
    horn: ['დალის ყანწი', 'Dali\'s Horn', 'შენი ყველა იუნიტი +2 ზიანს აყენებს დიდ მტერს.', 'All your units deal +2 damage to large enemies.'],
    collar: ['ყურშას საყელო', 'Qursha\'s Collar', 'შენი რიგის ბოლო იუნიტი +2/+2.', 'The last unit in your line gets +2/+2.'],
    coil: ['მეხის ხვია', 'Thunder Coil', 'ბრძოლის დასაწყისში ყველა მტერს 1 ზიანი.', 'At the start of battle, 1 damage to every enemy.'],
    water: ['ცოცხალი წყალი', 'Water of Life', 'ერთხელ: როცა ნებისყოფა ამოგეწურება, 4-ზე ბრუნდება. შემდეგ რელიქვია ქრება.', 'Once: when your nerve runs out, it returns to 4. The relic is then spent.'],
    deadwater: ['მკვდარი წყალი', 'Water of Death', 'შენი მკურნალები +1-ით მეტს კურნავენ.', 'Your healers restore 1 more.'],
    yoke: ['მზიდავის უღელი', 'Porter\'s Yoke', 'დანაზოგის სარგებელი მაქს. +4 (ნაცვლად +2-ისა).', 'Savings interest is capped at +4 (instead of +2).'],
    chart: ['საველე რუკა', 'Field Chart', 'ყოველ მობილიზაციაზე 1 უფასო განახლება.', 'One free reroll at every muster.'],
    shovel: ['სანგრის ნიჩაბი', 'Trench Spade', 'პირველ ორ რაუნდში შენი წინა იუნიტი ყოველ დარტყმაზე −1 ზიანს იღებს.', 'In the first two rounds, your front unit takes −1 from every hit.'],
    ring: ['ერისთავის ბეჭედი', 'Eristavi\'s Signet', 'შენი მეთაურები მეზობლებს კიდევ +1 შეტევას აძლევენ.', 'Your leaders give neighbours +1 more attack.'],
    boiler: ['ორთქლის ქვაბი', 'Steam Boiler', 'შენს დიდ იუნიტებს (IV დონე და ზემოთ) +3 მდგრადობა.', 'Your large units (tier IV and up) get +3 resilience.'],
    scope: ['მსროლელის ჭოგრიტი', 'Marksman\'s Glass', 'შორი იუნიტების დახმარების ცეცხლი +1 ზიანი.', 'Long units\' supporting fire deals +1 damage.'],
    oath: ['ძმობის ფიცი', 'Oath of Brothers', 'როცა შენი იუნიტი ეცემა, მის უკან მდგომი +1 შეტევას იღებს.', 'When one of your units falls, the one behind it gets +1 attack.']
  };
  // ---- რელიეფი ----
  const TER = {
    plain: ['ველი', 'Open field', 'განსაკუთრებული წესი არ არის.', 'No special rule.', 30],
    mud: ['ტალახი', 'Mud', 'იერიში არ მუშაობს.', 'Charge does not work.', 15],
    snow: ['თოვლი', 'Snow', 'ყოველი მე-3 რაუნდის ბოლოს ყველა იუნიტს 1 ზიანი (ყინვა).', 'At the end of every 3rd round, 1 damage to every unit (frost).', 15],
    coast: ['სანაპირო', 'Coast', 'მფრინავები +2 ზიანს აყენებენ.', 'Flyers deal +2 damage.', 14],
    fog: ['ნისლი', 'Fog', 'პირველ ორ რაუნდში შორი იუნიტები უკნიდან ვერ ისვრიან.', 'In the first two rounds, Long units cannot fire from behind.', 13],
    ruins: ['ნანგრევები', 'Ruins', 'ორივე მხარის წინა იუნიტი +2 საფარით იწყებს.', 'Both front units start with +2 cover.', 13]
  };
  // ---- მტრის დამატებითი წესები (რჩეული რაზმები და ბოსები) ----
  const EMOD = {
    drill: ['წვრთნა', 'Drilled', 'მტრის ყველა იუნიტს +1 შეტევა.', 'Every enemy unit gets +1 attack.'],
    armor: ['ჯავშანი', 'Armoured', 'მტრის ყველა იუნიტი +2 საფარით იწყებს.', 'Every enemy unit starts with +2 cover.'],
    barrage: ['არტილერია', 'Artillery', 'ბრძოლის დასაწყისში შენს ყველა იუნიტს 2 ზიანი.', 'At the start of battle, 2 damage to all your units.'],
    nest: ['ტყვიამფრქვევი', 'Machine gun', 'ყოველ რაუნდში შენს წინა იუნიტს 2 ზიანი.', 'Every round, 2 damage to your front unit.'],
    wire: ['მავთული', 'Wire', 'პირველ რაუნდში შენი წინა იუნიტი ვერ ურტყამს.', 'In the first round, your front unit cannot strike.']
  };
  // ---- ხდომილებები ----
  const EVT = {
    deserters: ['დეზერტირები', 'Deserters', 'გზაზე მშიერი ჯარისკაცები გხვდებიან. იარაღი ჯერ კიდევ ხელში უჭირავთ.', 'Hungry soldiers meet you on the road. They still hold their rifles.',
      [['რიგში ჩააყენე: უფასო I დონის იუნიტი', 'Fall them in: a free tier I unit'], ['საგზალი წაართვი: +3 მარაგი', 'Take their rations: +3 supply']]],
    depot: ['მიტოვებული ვაგონი', 'Abandoned wagon', 'ლიანდაგზე ცარიელი ეშელონი დგას. ერთი ვაგონი დალუქულია.', 'An empty train stands on the rails. One wagon is still sealed.',
      [['გატეხე ლუქი: შემთხვევითი ბრძანება', 'Break the seal: a random order'], ['ჩამოხსენი სპილენძი: +3 მარაგი', 'Strip the copper: +3 supply']]],
    wounded: ['დაჭრილთა კოლონა', 'Column of wounded', 'ფრონტიდან დაჭრილები მოჰყავთ. საკაცეები არ ჰყოფნით.', 'The wounded are coming back from the front. There are not enough stretchers.',
      [['დაეხმარე: −3 მარაგი, +2 ნებისყოფა', 'Help them: −3 supply, +2 nerve'], ['გაიარე: შემთხვევით იუნიტს +1/+1', 'March on: a random unit gets +1/+1']]],
    bargain: ['ქაჯის გარიგება', 'The Kaji\'s bargain', 'ღამით კოცონთან ვერცხლისთვალება მჭედელი ჯდება და რაღაცას გთავაზობს.', 'At night a silver-eyed smith sits down by your fire and makes an offer.',
      [['დათანხმდი: −2 ნებისყოფა, რელიქვია', 'Accept: −2 nerve, a relic'], ['გააგდე', 'Send him away']]],
    forge: ['ძველი სამჭედლო', 'The old forge', 'ნანგრევებში ქურა ჯერ კიდევ თბილია.', 'In the ruins the furnace is still warm.',
      [['გამოჭედე: შენს წინა იუნიტს +2 შეტევა', 'Forge: your front unit gets +2 attack'], ['შეაკეთე: შენს წინა იუნიტს +3 მდგრადობა', 'Mend: your front unit gets +3 resilience']]],
    song: ['სანგრის სიმღერა', 'Trench song', 'ვიღაც ჩუმად მღერის. მთელი ასეული აჰყვება.', 'Someone sings quietly. The whole company joins in.',
      [['იმღერეთ: +2 ნებისყოფა', 'Sing: +2 nerve'], ['ივარჯიშეთ: ყველა იუნიტს +1 მდგრადობა', 'Drill instead: every unit gets +1 resilience']]],
    prisoner: ['ტყვე მზვერავი', 'Captured scout', 'გუშაგებმა მტრის მზვერავი დაიჭირეს.', 'Your sentries have caught an enemy scout.',
      [['დაკითხე: შემდეგ ბრძოლაში მტრის ყველა იუნიტს −1 შეტევა', 'Question him: in the next battle every enemy unit gets −1 attack'], ['გაცვალე: +4 მარაგი', 'Exchange him: +4 supply']]],
    crossroads: ['ნისლიანი გზაჯვარედინი', 'Foggy crossroads', 'მოკლე გზა ნაღმებით არის სავსე. გრძელზე მარაგის ურემი ჩანს.', 'The short road is mined. On the long one stands a supply cart.',
      [['გარისკე: 50% +6 მარაგი, 50% −2 ნებისყოფა', 'Risk it: 50% +6 supply, 50% −2 nerve'], ['ფრთხილად: +1 მარაგი', 'Go carefully: +1 supply']]]
  };

  // ---- ფრაქციების ინდექსი ----
  const BYF = {};
  for (const id in U) { const u = U[id]; ((BYF[u.f] = BYF[u.f] || {})[u.tier] = BYF[u.f][u.tier] || []).push(id); }

  // ================= ბრძოლა =================
  function simulate(A0, B0, opt) {
    opt = opt || {};
    const terrain = opt.terrain || 'plain';
    const S = { a: { u: [], m: opt.modsA || {}, k: 'a' }, b: { u: [], m: opt.modsB || {}, k: 'b' } };
    const ev = []; let uidc = 0, round = 0;
    const other = s => s === S.a ? S.b : S.a;
    function inst(x, s) {
      const d = def(x.id), st = x.st || 1, kw = traits(x.id);
      let atk = Math.round(d.atk * MULT[st]) + (x.ba || 0), hp = Math.round(d.hp * MULT[st]) + (x.bh || 0);
      if (s.m.hammer && st >= 2) atk += 2;
      if (s.m.boiler && LARGE[d.tier]) hp += 3;
      if (s.m.drill && atk > 0) atk += 1;
      return { uid: s.k + (uidc++), ref: x.u || null, id: x.id, st, side: s.k, atk, hp, max: hp, kw, large: !!LARGE[d.tier],
        cover: 0, burn: 0, sup: 0, stub: !!kw.stubborn, quaked: false, dead: false, noRev: !U[x.id] };
    }
    function rear(s) { const n = s.u.length; if (!n) return null; if (s.m.camo) return n > 2 ? s.u[n - 3] : s.u[0]; return s.u[n - 1]; }
    function eatk(u, s) {
      if (u.atk <= 0) return 0;
      let a = u.atk; const i = s.u.indexOf(u);
      if (i >= 0) for (const j of [i - 1, i + 1]) { const v = s.u[j]; if (v && v.kw.leader) a += v.st + (s.m.ring ? 1 : 0); }
      if (s.m.volley) a += 1;
      return Math.max(1, a - u.sup);
    }
    let pend = [];
    const hit = (src, dst, base, kind) => { if (dst && base > 0) pend.push({ src, dst, base, kind }); };
    function flush() {
      const q = pend; pend = [];
      for (const h of q) {
        const src = h.src, dst = h.dst, kind = h.kind; let n = h.base, abs = 0;
        const ds = S[dst.side];
        if (kind !== 'burn' && kind !== 'gas' && kind !== 'frost' && kind !== 'fatigue') {
          if (src) {
            if (dst.large) n += src.kw.hunter ? 3 * src.st : S[src.side].m.horn ? 2 : 0;
            if (terrain === 'coast' && src.kw.fly) n += 2;
          }
          if (!(src && src.kw.breaker)) {
            let red = dst.kw.shield ? dst.st : 0;
            if (dst === ds.u[0]) red += (ds.m.trench ? 1 : 0) + (ds.m.shovel && round <= 2 ? 1 : 0);
            if (red) n = Math.max(1, n - red);
            abs = Math.min(dst.cover, n); dst.cover -= abs; n -= abs;
          }
        }
        dst.hp -= n;
        if (src && (kind === 'melee' || kind === 'support' || kind === 'air' || kind === 'charge')) {
          if (src.kw.fire) dst.burn = Math.max(dst.burn, src.st);
          if (src.kw.suppress && !dst.kw.fearless && dst.sup < 3) dst.sup++;
        }
        ev.push({ t: 'hit', s: src ? src.uid : null, d: dst.uid, n, c: abs, k: kind });
      }
    }
    function revive(u, s, hp, why) { u.dead = false; u.hp = hp; u.burn = 0; u.sup = 0; u.cover = 0; u.noRev = true; s.u.push(u); ev.push({ t: 'revive', d: u.uid, hp, k: why }); }
    function cleanup() {
      let again = true, guard = 0;
      while (again && guard++ < 60) {
        again = false;
        for (const s of [S.a, S.b]) for (const u of s.u.slice()) {
          if (u.hp > 0) continue;
          if (u.stub) { u.stub = false; u.hp = 1; ev.push({ t: 'stub', d: u.uid }); continue; }
          const i = s.u.indexOf(u); s.u.splice(i, 1); u.dead = true; ev.push({ t: 'die', d: u.uid }); again = true;
          const o = other(s);
          if (u.kw.vengeance && o.u[0]) hit(u, o.u[0], Math.ceil(Math.max(1, u.atk - u.sup) / 2), 'venge');
          for (const v of s.u) if (v.kw.brother && v.hp > 0) { v.atk += v.st; v.hp += v.st; v.max += v.st; ev.push({ t: 'buff', d: v.uid, k: 'brother' }); }
          if (s.m.oath && s.u[i] && s.u[i].atk > 0) { s.u[i].atk += 1; ev.push({ t: 'buff', d: s.u[i].uid, k: 'oath' }); }
          if (!u.noRev) {
            if (s.m.hospital && !s.hosp) { s.hosp = 1; revive(u, s, Math.ceil(u.max / 2), 'hospital'); }
            else if (s.m.cauldron && !s.caul) { s.caul = 1; revive(u, s, 1, 'cauldron'); }
          }
        }
        if (pend.length) { flush(); again = true; }
        for (const s of [S.a, S.b]) { const f = s.u[0];
          if (f && f.hp > 0 && f.kw.giant && !f.quaked && other(s).u.length) { f.quaked = true; ev.push({ t: 'quake', s: f.uid });
            for (const v of other(s).u) hit(f, v, 2 * f.st, 'quake'); flush(); again = true; } }
      }
    }
    const snap = s => s.u.map(u => ({ uid: u.uid, atk: eatk(u, s), hp: u.hp, max: u.max, cover: u.cover, burn: u.burn, sup: u.sup }));
    const sync = () => ev.push({ t: 'sync', a: snap(S.a), b: snap(S.b) });
    const over = () => !S.a.u.length || !S.b.u.length;

    for (const k of ['a', 'b']) { const s = S[k];
      for (const x of (k === 'a' ? A0 : B0)) s.u.push(inst(x, s));
      if (s.m.collar && s.u.length) { const r = s.u[s.u.length - 1]; r.atk += 2; r.hp += 2; r.max += 2; }
      if (s.m.palisade) s.u.unshift(inst({ id: '_palisade' }, s));
      if (s.m.tooth) s.u.push(inst({ id: '_sparti' }, s)); }
    const full = s => s.u.map(u => ({ uid: u.uid, ref: u.ref, id: u.id, st: u.st, atk: eatk(u, s), hp: u.hp, max: u.max, cover: 0 }));
    ev.push({ t: 'init', a: full(S.a), b: full(S.b), terrain });
    // 1) მომზადება: საფარი, დათრგუნვა
    for (const s of [S.a, S.b]) { const o = other(s), f = s.u[0];
      if (f) { if (terrain === 'ruins') f.cover += 2; if (s.m.rib) f.cover += 3;
        for (const u of s.u) if (u.kw.digger) { f.cover += 2 * u.st; ev.push({ t: 'fx', s: u.uid, d: f.uid, k: 'digger' }); } }
      if (s.m.armor) for (const u of s.u) u.cover += 2;
      if (s.m.chain && o.u[0] && !o.u[0].kw.fearless) o.u[0].sup = Math.min(3, o.u[0].sup + 1);
      if (s.m.intel) for (const u of o.u) if (!u.kw.fearless) u.sup = Math.min(3, u.sup + 1); }
    sync();
    // 2) გახსნის ცეცხლი: მზვერავები, რეიდი, არტილერია, მეხის ხვია — ერთდროულად
    ev.push({ t: 'phase', k: 'open' });
    for (const s of [S.a, S.b]) { const o = other(s);
      for (const u of s.u) if (u.kw.scout) hit(u, rear(o), 2 * u.st, 'scout');
      if (s.m.raid && s.u.length) { const r = s.u[s.u.length - 1]; hit(r, rear(o), eatk(r, s), 'raid'); }
      if (s.m.barrage) for (const v of o.u) hit(null, v, 2, 'barrage');
      if (s.m.coil) for (const v of o.u) hit(null, v, 1, 'coil'); }
    flush(); cleanup(); sync();
    // 3) იერიში
    if (terrain !== 'mud' && !over()) {
      for (const s of [S.a, S.b]) { const o = other(s); for (const u of s.u) if (u.kw.charge) hit(u, o.u[0], eatk(u, s), 'charge'); }
      if (pend.length) { ev.push({ t: 'phase', k: 'charge' }); flush(); cleanup(); sync(); }
    }
    let gas = (S.a.m.gas || S.b.m.gas) ? 3 : 0;
    while (!over() && round < 40) {
      round++; ev.push({ t: 'round', n: round });
      // დახმარების ცეცხლი, ბუდე, კოშკი
      for (const s of [S.a, S.b]) { const o = other(s);
        if (!(terrain === 'fog' && round <= 2)) for (let i = 1; i <= 2; i++) { const u = s.u[i]; if (u && u.kw.long && u.atk > 0) hit(u, o.u[0], Math.ceil(eatk(u, s) / 2) + (s.m.scope ? 1 : 0), 'support'); }
        if (s.m.nest) hit(null, o.u[0], 2, 'nest');
        if (s.m.tower) hit(null, rear(o), 1, 'tower'); }
      if (pend.length) { flush(); cleanup(); sync(); if (over()) break; }
      // ჰაერი
      for (const s of [S.a, S.b]) { const o = other(s);
        s.u.forEach((u, i) => { if (i > 0 && u.kw.fly && u.atk > 0) hit(u, rear(o), eatk(u, s), 'air'); });
        for (const u of s.u) if (u.kw.anti_air) { const t = o.u.find(v => v.kw.fly); if (t) hit(u, t, 2 * u.st, 'aa'); } }
      if (pend.length) { flush(); cleanup(); sync(); if (over()) break; }
      // ხელჩართული: წინა წინას
      const fa = S.a.u[0], fb = S.b.u[0];
      if (!(round === 1 && S.b.m.wire)) hit(fa, fb, eatk(fa, S.a), 'melee');
      if (!(round === 1 && S.a.m.wire)) hit(fb, fa, eatk(fb, S.b), 'melee');
      flush(); cleanup(); sync(); if (over()) break;
      // რაუნდის ბოლო: ცეცხლი, გაზი, ყინვა, გამოფიტვა; შემდეგ მკურნალობა
      for (const s of [S.a, S.b]) for (const u of s.u) {
        if (u.burn) hit(null, u, u.burn, 'burn');
        if (gas > 0) hit(null, u, 1, 'gas');
        if (terrain === 'snow' && round % 3 === 0) hit(null, u, 1, 'frost');
        if (round >= 12) hit(null, u, round - 11, 'fatigue'); }
      flush();
      for (const s of [S.a, S.b]) s.u.forEach((u, i) => { if (u.hp <= 0) return;
        if (u.kw.regen && u.hp < u.max) { const n = Math.min(u.st, u.max - u.hp); u.hp += n; ev.push({ t: 'heal', s: u.uid, d: u.uid, n }); }
        if (u.kw.healer && i > 0) { const t = s.u[i - 1]; if (t.hp > 0 && t.hp < t.max) { const n = Math.min(u.st + 1 + (s.m.deadwater ? 1 : 0), t.max - t.hp); t.hp += n; ev.push({ t: 'heal', s: u.uid, d: t.uid, n }); } } });
      cleanup(); if (gas > 0) gas--; sync();
    }
    const win = S.a.u.length && !S.b.u.length ? 'a' : S.b.u.length && !S.a.u.length ? 'b' : 'draw';
    ev.push({ t: 'end', win });
    return { ev, win, rounds: round, left: { a: S.a.u.length, b: S.b.u.length }, alive: S.a.u.map(u => u.ref).filter(Boolean) };
  }

  // ================= გარბენი =================
  function rnd(run) { let t = run.rs = (run.rs + 0x6D2B79F5) | 0; t = Math.imul(t ^ t >>> 15, t | 1); t ^= t + Math.imul(t ^ t >>> 7, t | 61); return ((t ^ t >>> 14) >>> 0) / 4294967296; }
  const pick = (run, a) => a[Math.floor(rnd(run) * a.length)];
  function wpick(run, w) { let tot = 0; for (const k in w) tot += w[k]; let r = rnd(run) * tot; for (const k in w) { r -= w[k]; if (r < 0) return k; } return Object.keys(w)[0]; }
  function shuffle(run, a) { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd(run) * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
  const hash = s => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };

  const rank = run => Math.min(6, run.act * 2 + (run.step >= 3 ? 2 : 1));
  const slots = run => SLOTS[rank(run)];
  const power = (id, st) => { const d = def(id); return (d.atk + d.hp) * MULT[st || 1]; };
  const stats = x => { const d = def(x.id), st = x.st || 1; return { atk: Math.round(d.atk * MULT[st]) + (x.ba || 0), hp: Math.round(d.hp * MULT[st]) + (x.bh || 0) }; };
  const all = run => run.line.concat(run.res);
  const find = (run, uid) => all(run).find(x => x.u === uid);

  function newRun(o) {
    const seed = (o.seed == null ? Math.floor(Math.random() * 4294967296) : o.seed) >>> 0;
    const diff = Math.max(0, Math.min(8, o.diff | 0));
    const run = { v: 1, seed, rs: seed, f: o.faction, diff, daily: o.daily || null, act: 0, step: 0, nerve: 12 - (diff >> 1), supply: 0,
      line: [], res: [], orders: [], active: [], relics: [], porters: 0, uidc: 1, free: 0, phase: 'map', node: null, enemy: null, emods: [],
      shop: null, reward: null, won: false, intel: 0, winBonus: 0,
      stats: { nodes: 0, battles: 0, wins: 0, losses: 0, elites: 0, bosses: 0, merges: 0, flawless: 0, relics: 0 }, seen: {} };
    run.maxNerve = run.nerve;
    const side = F[o.faction].side;
    const foes = shuffle(run, Object.keys(F).filter(k => F[k].side !== side));
    run.map = [];
    for (let a = 0; a < ACTS; a++) run.map.push({ foe: foes[a % foes.length], steps: genAct(run, a) });
    return run;
  }
  function terrainRoll(run) { const w = {}; for (const k in TER) w[k] = TER[k][4]; return wpick(run, w); }
  function genAct(run, a) {
    const steps = [[{ t: 'battle', ter: a === 0 ? 'plain' : terrainRoll(run) }]];
    for (let s = 1; s < STEPS - 1; s++) {
      const n = s === 3 ? 3 : 2, opts = [];
      const first = (s >= 2 && !(a === 0 && s < 3) && rnd(run) < .4) ? 'elite' : 'battle';
      opts.push({ t: first, ter: terrainRoll(run) });
      const pool = { event: 34, camp: s >= 2 ? 26 : 8, depot: 22, battle: 10, elite: (a > 0 || s >= 3) && first !== 'elite' ? 14 : 0 };
      while (opts.length < n) { const t = wpick(run, pool); if (opts.some(x => x.t === t) && t !== 'battle') continue;
        opts.push(t === 'battle' || t === 'elite' ? { t, ter: terrainRoll(run) } : { t }); }
      steps.push(opts);
    }
    steps.push([{ t: 'boss', ter: terrainRoll(run) }]);
    return steps;
  }
  const options = run => run.phase === 'map' ? run.map[run.act].steps[run.step] : [];

  function enter(run, i) {
    if (run.phase !== 'map') return false;
    const node = run.map[run.act].steps[run.step][i]; if (!node) return false;
    run.node = node; run.enemy = null;
    if (node.t === 'event') { run.phase = 'event'; run.event = pick(run, Object.keys(EVT)); }
    else if (node.t === 'camp') run.phase = 'camp';
    else if (node.t === 'depot') { run.phase = 'depot'; run.depot = shuffle(run, Object.keys(ORD)).slice(0, 3); }
    else startPrep(run);
    return true;
  }
  function income(run) {
    const cap = run.relics.includes('yoke') ? 4 : 2;
    const o = { base: 6 + 2 * run.act - (run.diff >= 5 ? 1 : 0), porters: run.porters, relic: run.relics.includes('fleece') ? 1 : 0,
      win: run.winBonus, interest: Math.min(cap, Math.floor(run.supply / 5)) };
    o.total = o.base + o.porters + o.relic + o.win + o.interest; return o;
  }
  function startPrep(run) {
    run.income = income(run); run.supply += run.income.total; run.winBonus = 0;
    if (run.relics.includes('chart')) run.free += 1;
    if (!run.enemy) genEnemy(run);
    run.active = []; rollShop(run, true); run.phase = 'prep';
  }

  // ---- მტრის რაზმი ----
  const BUD = [8, 13, 18, 24, 28, 30, 44, 50, 56, 66, 74, 80, 90, 96, 102, 108, 114, 118];   // მტრის ძალა კვანძით (tools/test_run.js-ით დაკალიბრებული)
  const budget = idx => BUD[Math.min(idx, BUD.length - 1)];
  function frontScore(x) { const k = traits(x.id), s = stats(x); return s.hp + (k.shield ? 3 * x.st : 0) + (k.stubborn ? 2 : 0) + (k.giant ? 6 : 0) - (k.long ? 5 : 0) - (k.healer ? 8 : 0) - (k.fly ? 7 : 0) - (k.leader ? 3 : 0) - (k.brother ? 4 : 0); }
  function arrange(list) {                           // გონივრული განლაგება: მტკიცე წინ, მკურნალი და მსროლელები მის უკან
    const xs = list.slice(), out = [];
    const take = f => { let b = -1, bv = -1e9; xs.forEach((x, i) => { const v = f(x); if (v > bv) { bv = v; b = i; } }); return b < 0 || bv === -1e9 ? null : xs.splice(b, 1)[0]; };
    const f = take(frontScore); if (f) out.push(f);
    const h = take(x => traits(x.id).healer ? stats(x).hp : -1e9); if (h) out.push(h);
    while (out.length < 3) { const l = take(x => traits(x.id).long ? stats(x).atk : -1e9); if (!l) break; out.push(l); }
    xs.sort((p, q) => frontScore(q) - frontScore(p));
    return out.concat(xs);
  }
  function genEnemy(run) {
    const node = run.node, idx = run.act * STEPS + run.step, r = rank(run), foe = run.map[run.act].foe, pool = BYF[foe];
    let B = budget(idx) * (1 + .07 * run.diff) * (node.t === 'elite' ? 1.2 : 1);
    const list = [], n = SLOTS[r], add = (id, st) => { list.push({ id, st: st || 1, ba: 0, bh: 0 }); B -= power(id, st || 1); };
    const mods = [];
    if (node.t === 'boss') {
      if (run.act === 0) add(pick(run, pool.IV), 1);
      else if (run.act === 1) { add(pool['IV+'][0], 1); add(pick(run, pool.hero), 1); }
      else { add(pool.V[0], 1); add(pick(run, pool.hero), 1); add(pick(run, pool.IV), 1); }
      mods.push(['drill', 'armor', 'barrage'][run.act]); if (run.diff >= 6) mods.push('nest');
    } else if (node.t === 'elite') mods.push(pick(run, Object.keys(EMOD)));
    const odds = Object.assign({}, ODDS[r]); delete odds.hero; delete odds.V;
    let tries = 0;
    while (list.length < n && tries++ < 60) { const t = wpick(run, odds); if (!pool[t]) continue; const id = pick(run, pool[t]);
      if (power(id, 1) <= B * 1.1 || !list.length) add(id, 1); else if (B < 4) break; }
    tries = 0;
    while (B > 3 && tries++ < 60) { const x = pick(run, list); if (x.st >= (run.act >= 2 ? 3 : 2) || traits(x.id).hero || traits(x.id).giant) continue;
      const c = power(x.id, x.st + 1) - power(x.id, x.st); if (c <= B * 1.1) { x.st++; B -= c; } }
    if (B > 1) { const x = list[0]; const b = Math.round(B / 2); x.ba += Math.floor(b / 2); x.bh += Math.ceil(b / 2); }
    run.enemy = arrange(list); run.emods = mods;
  }

  // ---- მობილიზაცია (მაღაზია) ----
  function owns(run, kw) { return all(run).some(x => traits(x.id)[kw]); }
  function offerUnit(run, f, merc) {
    const r = rank(run), pool = BYF[f];
    for (let i = 0; i < 30; i++) { const t = wpick(run, ODDS[r]); if (!pool[t]) continue;
      if (t === 'hero' && owns(run, 'hero')) continue; if (t === 'V' && owns(run, 'giant')) continue;
      const id = pick(run, pool[t]); return { id, cost: price(id) + (merc ? 1 : 0), merc: !!merc, lock: false, sold: false }; }
    return { id: pool.I[0], cost: price(pool.I[0]) + (merc ? 1 : 0), merc: !!merc, lock: false, sold: false };
  }
  function rollShop(run, fresh) {
    const old = run.shop, side = F[run.f].side, offers = [];
    for (let i = 0; i < 4; i++) {
      const o = old && old.offers[i];
      if (o && o.lock && !o.sold) { offers.push(o); continue; }
      if (i < 3) offers.push(offerUnit(run, run.f, false));
      else { const fs = Object.keys(F).filter(k => F[k].side === side && k !== run.f); offers.push(offerUnit(run, pick(run, fs), true)); }
    }
    let ord = old && old.order;
    if (fresh || !ord || ord.sold) { let k = pick(run, Object.keys(ORD)); if (k === 'porter' && run.porters >= 3) k = 'recon'; ord = { key: k, cost: ORD[k].cost, sold: false }; }
    run.shop = { offers, order: ord };
    for (const o of offers) run.seen[o.id] = Math.max(run.seen[o.id] || 0, 0);
  }
  function reroll(run) {
    if (run.phase !== 'prep') return false;
    if (run.free > 0) run.free--; else if (run.supply >= 1) run.supply--; else return false;
    rollShop(run, false); return true;
  }
  function merge(run) {                              // სამი ერთნაირი (იგივე ვარსკვლავით) → ერთი, ერთი ვარსკვლავით მეტი
    let did = false, again = true;
    while (again) { again = false;
      const g = {}; for (const x of all(run)) if (x.st < 3 && !traits(x.id).hero) (g[x.id + ':' + x.st] = g[x.id + ':' + x.st] || []).push(x);
      for (const k in g) if (g[k].length >= 3) { const [keep, b, c] = g[k];
        keep.st++; keep.ba += b.ba + c.ba; keep.bh += b.bh + c.bh;
        for (const z of [b, c]) { let i = run.line.indexOf(z); if (i >= 0) run.line.splice(i, 1); else run.res.splice(run.res.indexOf(z), 1); }
        run.stats.merges++; run.seen[keep.id] = Math.max(run.seen[keep.id] || 0, keep.st); did = again = true; break; } }
    return did;
  }
  function canAdd(run, id) {
    const k = traits(id);
    if (k.hero && owns(run, 'hero')) return false;
    if (k.giant && owns(run, 'giant')) return false;
    if (run.line.length < slots(run) || run.res.length < RES) return true;
    return !k.hero && all(run).filter(x => x.id === id && x.st === 1).length >= 2;
  }
  function addUnit(run, id) {
    if (!canAdd(run, id)) return null;
    const x = { u: run.uidc++, id, st: 1, ba: 0, bh: 0 };
    if (run.line.length < slots(run)) run.line.push(x); else run.res.push(x);
    run.seen[id] = Math.max(run.seen[id] || 0, 1);
    const m = merge(run); return { unit: x, merged: m };
  }
  function buy(run, i) {
    if (run.phase !== 'prep') return null;
    const o = run.shop.offers[i]; if (!o || o.sold || run.supply < o.cost) return null;
    const r = addUnit(run, o.id); if (!r) return null;
    run.supply -= o.cost; o.sold = true; o.lock = false; return r;
  }
  function gainOrder(run, key) {
    if (key === 'porter') { if (run.porters >= 3) return false; run.porters++; return true; }
    if (key === 'recon') { run.free += 2; return true; }
    if (key === 'train') { run.supply += 4; return true; }
    if (run.orders.length >= 3) return false;
    run.orders.push(key); return true;
  }
  function buyOrder(run) {
    if (run.phase !== 'prep') return false;
    const o = run.shop.order; if (!o || o.sold || run.supply < o.cost) return false;
    if (!gainOrder(run, o.key)) return false;
    run.supply -= o.cost; o.sold = true; return true;
  }
  const refund = x => Math.max(1, Math.floor(price(x.id) / 2)) * [0, 1, 3, 9][x.st];
  function sell(run, uid) {
    const x = find(run, uid); if (!x || (run.phase !== 'prep')) return false;
    let i = run.line.indexOf(x); if (i >= 0) run.line.splice(i, 1); else run.res.splice(run.res.indexOf(x), 1);
    run.supply += refund(x); return true;
  }
  function place(run, uid, zone, idx) {              // გადაადგილება რიგსა და რეზერვში; დაკავებულ ადგილზე — გაცვლა
    const x = find(run, uid); if (!x) return false;
    const from = run.line.includes(x) ? run.line : run.res, to = zone === 'line' ? run.line : run.res, cap = zone === 'line' ? slots(run) : RES;
    const fi = from.indexOf(x);
    if (from === to) { from.splice(fi, 1); to.splice(Math.min(idx, to.length), 0, x); return true; }
    if (idx < to.length && (to.length >= cap || idx >= 0)) {
      if (to.length >= cap) { const y = to[idx]; to[idx] = x; from[fi] = y; return true; }
      from.splice(fi, 1); to.splice(idx, 0, x); return true;
    }
    if (to.length >= cap) return false;
    from.splice(fi, 1); to.push(x); return true;
  }
  function toggleLock(run, i) { const o = run.shop && run.shop.offers[i]; if (o && !o.sold) o.lock = !o.lock; }
  function toggleOrder(run, i) { const j = run.active.indexOf(i); if (j >= 0) run.active.splice(j, 1); else if (i < run.orders.length) run.active.push(i); }
  function fixLine(run) { while (run.line.length > slots(run)) { const x = run.line.pop(); if (run.res.length < RES) run.res.push(x); else run.supply += refund(x); } }

  // ---- ბრძოლა გარბენში ----
  function mods(run) {
    const m = {}; for (const r of run.relics) m[r] = 1;
    for (const i of run.active) m[run.orders[i]] = 1;
    if (run.intel) m.intel = 1; return m;
  }
  function fight(run) {
    if (run.phase !== 'prep' || !run.line.length) return null;
    const node = run.node, em = {}; for (const k of run.emods) em[k] = 1;
    const sim = simulate(run.line, run.enemy, { terrain: node.ter, modsA: mods(run), modsB: em });
    run.orders = run.orders.filter((k, i) => !run.active.includes(i)); run.active = []; run.intel = 0;
    run.stats.battles++;
    const out = { sim, win: sim.win === 'a', boss: node.t === 'boss', elite: node.t === 'elite', nerve: 0, final: false };
    if (out.win) {
      run.stats.wins++; if (out.elite) run.stats.elites++; if (out.boss) run.stats.bosses++;
      if (sim.left.a === run.line.length + (run.relics.includes('tooth') ? 1 : 0)) run.stats.flawless++;
      for (const x of run.line) if (traits(x.id).hero) { x.ba++; x.bh++; }
      run.winBonus = 1; run.enemy = null;
      if (out.boss) run.nerve = Math.min(run.maxNerve, run.nerve + 2);
      if (out.boss && run.act === ACTS - 1) { run.stats.nodes++; run.won = true; run.phase = 'over'; out.final = true; return out; }
      genReward(run, out); run.phase = 'reward';
    } else {
      run.stats.losses++;
      out.nerve = 1 + Math.min(3, sim.left.b) + (out.boss ? 1 : 0); run.nerve -= out.nerve;
      if (run.nerve <= 0) { const i = run.relics.indexOf('water');
        if (i >= 0) { run.relics.splice(i, 1); run.nerve = 4; out.saved = true; } else { run.nerve = 0; run.phase = 'over'; return out; } }
      if (out.boss) { run.phase = 'retry'; } else { run.enemy = null; advance(run); }
    }
    return out;
  }
  function retry(run) { if (run.phase === 'retry') startPrep(run); }
  function relicChoices(run, n) { return shuffle(run, Object.keys(REL).filter(k => !run.relics.includes(k))).slice(0, n); }
  function genReward(run, out) {
    const side = F[run.f].side, picks = [];
    for (let i = 0; i < 2; i++) { const o = offerUnit(run, i ? pick(run, Object.keys(F).filter(k => F[k].side === side)) : run.f, false); picks.push({ t: 'unit', id: o.id }); }
    picks.push({ t: 'order', key: pick(run, Object.keys(ORD).filter(k => k !== 'porter' || run.porters < 3)) });
    run.reward = { picks, relics: out.boss ? relicChoices(run, 3) : out.elite ? relicChoices(run, 2) : [], relicDone: false, pickDone: false };
    if (!run.reward.relics.length) run.reward.relicDone = true;
  }
  function takeRelic(run, i) { const r = run.reward; if (!r || r.relicDone) return false; const k = r.relics[i]; if (!k) return false;
    run.relics.push(k); run.stats.relics++; r.relicDone = true; rewardDone(run); return true; }
  function takePick(run, i) {                        // i = −1: უარი, +2 მარაგი
    const r = run.reward; if (!r || r.pickDone) return false;
    if (i < 0) run.supply += 2;
    else { const p = r.picks[i]; if (!p) return false;
      if (p.t === 'unit') { if (!addUnit(run, p.id)) return false; } else if (!gainOrder(run, p.key)) return false; }
    r.pickDone = true; rewardDone(run); return true;
  }
  function rewardDone(run) { const r = run.reward; if (r && r.relicDone && r.pickDone) { run.reward = null; advance(run); } }
  function advance(run) {
    run.stats.nodes++; run.step++;
    if (run.step >= STEPS) { run.step = 0; run.act++; }
    run.node = null; run.phase = 'map'; fixLine(run);
  }

  // ---- ხდომილება, ბანაკი, საწყობი ----
  function chooseEvent(run, opt) {
    if (run.phase !== 'event') return null;
    const e = run.event; let msg = null;
    const bump = (x, a, h) => { x.ba += a; x.bh += h; };
    if (e === 'deserters') { if (opt === 0) { const id = pick(run, BYF[run.f].I); if (!addUnit(run, id)) run.supply += 2; else msg = { unit: id }; } else run.supply += 3; }
    else if (e === 'depot') { if (opt === 0) { const k = pick(run, Object.keys(ORD).filter(k => k !== 'porter' || run.porters < 3)); if (!gainOrder(run, k)) run.supply += 2; else msg = { order: k }; } else run.supply += 3; }
    else if (e === 'wounded') { if (opt === 0) { if (run.supply < 3) return null; run.supply -= 3; run.nerve = Math.min(run.maxNerve, run.nerve + 2); } else { const xs = all(run); if (xs.length) { const x = pick(run, xs); bump(x, 1, 1); msg = { unit: x.id }; } } }
    else if (e === 'bargain') { if (opt === 0) { if (run.nerve <= 2) return null; run.nerve -= 2; const k = relicChoices(run, 1)[0]; if (k) { run.relics.push(k); run.stats.relics++; msg = { relic: k }; } } }
    else if (e === 'forge') { const x = run.line[0]; if (x) { if (opt === 0) bump(x, 2, 0); else bump(x, 0, 3); msg = { unit: x.id }; } }
    else if (e === 'song') { if (opt === 0) run.nerve = Math.min(run.maxNerve, run.nerve + 2); else for (const x of all(run)) bump(x, 0, 1); }
    else if (e === 'prisoner') { if (opt === 0) run.intel = 1; else run.supply += 4; }
    else if (e === 'crossroads') { if (opt === 0) { if (rnd(run) < .5) { run.supply += 6; msg = { good: true }; } else { run.nerve = Math.max(1, run.nerve - 2); msg = { good: false }; } } else run.supply += 1; }
    run.event = null; advance(run); return msg || {};
  }
  function campRest(run) { if (run.phase !== 'camp') return false; run.nerve = Math.min(run.maxNerve, run.nerve + 3); advance(run); return true; }
  function campTrain(run, uid) { if (run.phase !== 'camp') return false; const x = find(run, uid); if (!x) return false; x.ba += 2; x.bh += 2; advance(run); return true; }
  function depotTake(run, i) { if (run.phase !== 'depot') return false;
    if (i < 0) run.supply += 3; else { const k = run.depot[i]; if (!k || !gainOrder(run, k)) return false; run.supply += 1; }
    run.depot = null; advance(run); return true; }

  const xpFor = run => Math.round((run.stats.nodes * 6 + run.stats.wins * 4 + run.stats.bosses * 25 + (run.won ? 100 : 0)) * (1 + .25 * run.diff));
  function dailySeed(date) { const h = hash('tl-' + date); const fs = Object.keys(F); return { seed: h, faction: fs[h % fs.length], date }; }

  return { KW, ORD, REL, TER, EMOD, EVT, price, MULT, SLOTS, RES, ODDS, STEPS, ACTS, LARGE, SPECIAL, BYF,
    traits, def, stats, power, simulate, newRun, rank, slots, options, enter, income, startPrep, budget, arrange, genEnemy,
    reroll, buy, buyOrder, sell, place, toggleLock, toggleOrder, canAdd, addUnit, gainOrder, refund, mods, fight, retry,
    takeRelic, takePick, chooseEvent, campRest, campTrain, depotTake, advance, xpFor, dailySeed, hash, all, find, rnd };
});
