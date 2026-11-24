// „სანგრის რიგი“ (v2) — ძრავა. რაუნდები: მობილიზაცია (მაღაზია) → ავტომატური ბრძოლა „მოჩვენება“ ჯართან, რომელიც იმავე წესებით
// და იმავე მაღაზიით აწყობილი. ველი: სანგარი (4, ხელჩართული) და ზურგი (3, მსროლელები, მკურნალები, მეთაურები), სათადარიგო (3).
// მიზანი: 10 გამარჯვება, სანამ 5 სიცოცხლეს დახარჯავ. ყოველი მესამე რაუნდის შემდეგ — ფრონტის რუკა (რჩეული რაზმი, ბანაკი, საწყობი,
// ხდომილება). ბრძოლაში შემთხვევითობა არ არის. ბრაუზერში window.TL, node-ში require('./engine.js')(CG). წესები — rules/trench-line.md.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory;
  else root.TL = factory(root.CG);
})(typeof self !== 'undefined' ? self : this, function (CG) {
  'use strict';
  const U = CG.units, F = CG.factions;
  const T_CAP = 4, R_CAP = 3, B_CAP = 3, LIVES = 5, GOAL = 10, SUPPLY = 10, COST = 3, MERC = 4;
  const LVL = { I: 1, II: 2, III: 3, IV: 4, 'IV+': 5, hero: 5, V: 6 };   // ბარათის დონე → მაღაზიის დონე, საიდანაც ჩნდება
  const SHOP_N = [0, 3, 4, 4, 5, 5, 6];                // იუნიტები მაღაზიაში დონის მიხედვით
  const UP = [0, 0, 5, 7, 8, 9, 10];                    // დონის ამაღლების საწყისი ფასი; ყოველ რაუნდში 1-ით იაფდება
  const CURVE = [0, 0, 2, 4, 6, 8, 10];                 // მოჩვენებები ამ რაუნდიდან ამაღლებენ დონეს
  const MULT = [0, 1, 2, 3];                            // ★, ★★, ★★★
  const LARGE = { IV: 1, 'IV+': 1, V: 1 };
  // ფრაქციის ლოჯისტიკა: დამატებითი მარაგი ყოველ რაუნდში (წილადი ნაწილდება რაუნდებზე). ირჩევს tools/tune_factions.js.
  const DOC = /*DOC*/{"iberia":0.75,"hell":-1.5,"harness":3,"listeners":-0.25,"kajeti":-1.5,"hellenic":-0.25,"finnish":-0.25,"britain":-0.5,"gaul":-0.25,"polianitsy":-0.25,"armenian":0.25,"oghuz":-1.25,"yellow_river":0.75,"japan_isles":-0.75,"korea":-0.5,"balkans":-1.25,"alps":0.75,"baltic":-0.25,"batavi":1.25,"byzantium":0.5,"ottoman":-0.5}/*/DOC*/;
  // მოჩვენებების ზოგადი სიძლიერე: დამატებითი მარაგი რაუნდში (tools/tune_factions.js).
  const GB = /*GB*/0/*/GB*/;
  const doc = f => DOC[f] || 0;
  const frac = (d, n) => Math.floor(n * d + 1e-9) - Math.floor((n - 1) * d + 1e-9);

  // ---- უნარები. g — ხატულა ბარათზე; t(n) — ტექსტი n ვარსკვლავისთვის [ka, en]; shop — მობილიზაციის უნარი ----
  const KW = {
    long: { g: '➶', ka: 'შორი', en: 'Long', t: n => ['ზურგიდან ყოველ რაუნდში მტრის სანგრის პირველ იუნიტს თავისი შეტევის ნახევარს აყენებს.', 'From the rear, hits the first enemy in the trench for half its attack every round.'] },
    shield: { g: '▣', ka: 'ფარი', en: 'Shield', t: n => [`ყოველ დარტყმაზე −${n} ზიანი (მინ. 1).`, `Takes −${n} from every hit (min. 1).`] },
    breaker: { g: '⚒', ka: 'მტვრევა', en: 'Breaker', t: n => ['მისი დარტყმა უგულებელყოფს ფარს, თხრილს და საფარს.', 'Its hits ignore shields, trenches and cover.'] },
    charge: { g: '»', ka: 'იერიში', en: 'Charge', t: n => ['ბრძოლის დასაწყისში მტრის სანგრის პირველ იუნიტს თავის შეტევას აყენებს.', 'At the start of battle, hits the first enemy in the trench for its attack.'] },
    scout: { g: '◎', ka: 'მზვერავი', en: 'Scout', t: n => [`ბრძოლის დასაწყისში მტრის ბოლო იუნიტს ${2 * n} ზიანს აყენებს.`, `At the start of battle, deals ${2 * n} damage to the enemy's last unit.`] },
    leader: { g: '✦', ka: 'მეთაური', en: 'Leader', t: n => [`სადაც არ უნდა იდგეს, შენი სანგრის ყველა სხვა იუნიტს +${n} შეტევა.`, `Wherever it stands, every other unit in your trench gets +${n} attack.`] },
    healer: { g: '⚕', ka: 'მკურნალი', en: 'Healer', t: n => [`რაუნდის ბოლოს ${n + 1} მდგრადობას უბრუნებს: ზურგიდან — სანგრის პირველ იუნიტს, სანგარში — მის წინ მდგომს.`, `At the end of a round restores ${n + 1} resilience: from the rear to the first unit in the trench, in the trench to the unit in front of it.`] },
    digger: { g: '⛏', ka: 'მესანგრე', en: 'Digger', t: n => [`ბრძოლის დასაწყისში შენი სანგრის პირველ იუნიტს +${2 * n} საფარი.`, `At the start of battle, the first unit in your trench gets +${2 * n} cover.`] },
    fire: { g: '♨', ka: 'ცეცხლი', en: 'Fire', t: n => [`დარტყმული მტერი იწვის: რაუნდის ბოლოს ${n} ზიანი.`, `An enemy it hits burns: ${n} damage at the end of each round.`] },
    suppress: { g: '⊘', ka: 'დათრგუნვა', en: 'Suppress', t: n => ['დარტყმული მტერი ბრძოლის ბოლომდე −1 შეტევას იღებს (მაქს. −3).', 'An enemy it hits gets −1 attack for the rest of the battle (max. −3).'] },
    fearless: { g: '◆', ka: 'უშიშარი', en: 'Fearless', t: n => ['დათრგუნვა მასზე არ მოქმედებს.', 'Cannot be suppressed.'] },
    hunter: { g: '⌖', ka: 'მონადირე', en: 'Hunter', t: n => [`+${3 * n} ზიანი დიდ მტერზე (IV დონე და ზემოთ).`, `+${3 * n} damage against large enemies (tier IV and up).`] },
    fly: { g: '✈', ka: 'ფრენა', en: 'Flying', t: n => ['ზურგიდან ყოველ რაუნდში მტრის ბოლო იუნიტს თავის შეტევას აყენებს.', 'From the rear, hits the enemy\'s last unit for its attack every round.'] },
    anti_air: { g: '⇡', ka: 'საზენიტო', en: 'Anti-air', t: n => [`ყოველ რაუნდში მტრის პირველ მფრინავს ${2 * n} ზიანს აყენებს.`, `Every round deals ${2 * n} damage to the first enemy flyer.`] },
    regen: { g: '❀', ka: 'ამოზრდა', en: 'Regrowth', t: n => [`რაუნდის ბოლოს +${n} მდგრადობა.`, `+${n} resilience at the end of each round.`] },
    giant: { g: '⛰', ka: 'გოლიათი', en: 'Giant', t: n => [`როცა სანგრის პირველი ხდება, ყველა მტერს ${2 * n} ზიანს აყენებს. მაქს. 1.`, `When it becomes first in the trench, deals ${2 * n} damage to every enemy. Max. 1.`] },
    hero: { g: '♔', ka: 'გმირი', en: 'Hero', t: n => ['ყოველი მოგებული ბრძოლის შემდეგ სამუდამოდ +1/+1. მაქს. 1; არ ერთიანდება.', 'Permanently +1/+1 after every battle won. Max. 1; does not merge.'] },
    vengeance: { g: '☠', ka: 'ბოლო ტყვია', en: 'Last Round', t: n => ['დაღუპვისას მტრის სანგრის პირველ იუნიტს თავისი შეტევის ნახევარს აყენებს.', 'When it falls, hits the first enemy in the trench for half its attack.'] },
    stubborn: { g: '⚓', ka: 'ჯიუტი', en: 'Stubborn', t: n => ['პირველ სასიკვდილო დარტყმას 1 მდგრადობით გადაურჩება.', 'Survives its first lethal blow with 1 resilience.'] },
    brother: { g: '∞', ka: 'ძმობა', en: 'Brotherhood', t: n => [`როცა მოკავშირე ეცემა, +${n}/+${n}.`, `Gets +${n}/+${n} whenever an ally falls.`] },
    alchemist: { g: '⚗', shop: 1, ka: 'ალქიმია', en: 'Alchemy', t: n => [`აყვანისას: შენს ორ შემთხვევით იუნიტს +${n}/+${n} სამუდამოდ.`, `When recruited: two random units of yours get +${n}/+${n} for good.`] },
    orders: { g: '✉', shop: 1, ka: 'ბრძანება', en: 'Dispatch', t: n => ['აყვანისას: შემდეგ ბრძოლაში უფასო შემთხვევითი ბრძანება.', 'When recruited: a free random order for the next battle.'] },
    song: { g: '♪', shop: 1, ka: 'სიმღერა', en: 'Song', t: n => [`მოგებული ბრძოლის შემდეგ: შენს შემთხვევით სხვა იუნიტს +${n}/+${n} სამუდამოდ.`, `After a battle won: another random unit of yours gets +${n}/+${n} for good.`] },
    repair: { g: '⚙', shop: 1, ka: 'შეკეთება', en: 'Repair', t: n => [`ბრძოლაში გასვლისას: მის მეზობლებს (იმავე რიგში) +${n} მდგრადობა სამუდამოდ.`, `When you march to battle: its neighbours in the same row get +${n} resilience for good.`] }
  };
  const _tr = {};
  function traits(id) {                              // ბარათის უნარები; უუნარო ბარათი ხასიათს სტატებიდან იღებს
    if (_tr[id]) return _tr[id];
    const d = U[id], o = {};
    if (d) { for (const k of d.kw) if (KW[k]) o[k] = 1; for (const k of d.sh || []) if (KW[k]) o[k] = 1;
      if (!Object.keys(o).some(k => k !== 'hero' && k !== 'giant' && !KW[k].shop)) o[d.atk > d.hp ? 'vengeance' : d.hp > d.atk ? 'stubborn' : 'brother'] = 1; }
    return _tr[id] = o;
  }
  const traitsX = x => { const o = Object.assign({}, traits(x.id)); for (const k of x.k || []) o[k] = 1; return o; };
  const SPECIAL = {
    _sparti: { ka: 'სპარტი', en: 'Sown Warrior', atk: 3, hp: 3, tier: 'I', f: null, kw: [], art: null },
    _palisade: { ka: 'მესერი', en: 'Palisade', atk: 0, hp: 6, tier: 'I', f: null, kw: [], art: CG.common.palisade.art }
  };
  const def = id => U[id] || SPECIAL[id];

  // ---- მარაგის ბარათები: სამუდამო გამაძლიერებლები (unit/all) და ბრძანებები ერთი ბრძოლისთვის (order). ფასი 3 ----
  const ITEMS = {
    ration: { lv: 1, kind: 'unit', g: '◍', ka: 'ულუფა', en: 'Rations', t: ['ერთ იუნიტს +1/+1 სამუდამოდ.', 'One unit gets +1/+1 for good.'] },
    crate: { lv: 2, kind: 'all', g: '▤', ka: 'მარაგის ყუთი', en: 'Supply crate', t: ['შენს ორ შემთხვევით იუნიტს +1/+1 სამუდამოდ.', 'Two random units of yours get +1/+1 for good.'] },
    ammo: { lv: 2, kind: 'unit', g: '⁂', ka: 'ტყვია-წამალი', en: 'Ammunition', t: ['ერთ იუნიტს +2 შეტევა სამუდამოდ.', 'One unit gets +2 attack for good.'] },
    plate: { lv: 3, kind: 'unit', g: '▦', ka: 'ჯავშნის ფირფიტა', en: 'Armour plate', t: ['ერთ იუნიტს +3 მდგრადობა სამუდამოდ.', 'One unit gets +3 resilience for good.'] },
    helmet: { lv: 3, kind: 'unit', g: '◓', ka: 'ფოლადის ჩაფხუტი', en: 'Steel helmet', t: ['იუნიტი „ჯიუტი“ ხდება: პირველ სასიკვდილო დარტყმას 1 მდგრადობით გადაურჩება.', 'The unit becomes Stubborn: it survives its first lethal blow with 1 resilience.'] },
    medal: { lv: 4, kind: 'unit', g: '✪', ka: 'მედალი', en: 'Medal', t: ['ერთ იუნიტს +2/+2 სამუდამოდ.', 'One unit gets +2/+2 for good.'] },
    kitchen: { lv: 5, kind: 'all', g: '♨', ka: 'საველე სამზარეულო', en: 'Field kitchen', t: ['შენს ყველა იუნიტს ველზე +1/+1 სამუდამოდ.', 'Every unit of yours on the field gets +1/+1 for good.'] },
    prosthesis: { lv: 6, kind: 'unit', g: '⚙', ka: 'ორთქლის პროთეზი', en: 'Steam prosthesis', t: ['ერთ იუნიტს +4/+4 სამუდამოდ.', 'One unit gets +4/+4 for good.'] },
    trench: { lv: 1, kind: 'order', t: ['შემდეგ ბრძოლაში შენი სანგრის პირველი იუნიტი ყოველ დარტყმაზე −1 ზიანს იღებს (მინ. 1).', 'Next battle, the first unit in your trench takes −1 from every hit (min. 1).'] },
    wire: { lv: 1, kind: 'order', t: ['შემდეგ ბრძოლაში, პირველ რაუნდში, მტრის სანგრის პირველი იუნიტი ვერ ურტყამს.', 'Next battle, in the first round, the first enemy in the trench cannot strike.'] },
    camo: { lv: 1, kind: 'order', t: ['შემდეგ ბრძოლაში შენს ზურგს ვერ ესვრიან: მფრინავები, მზვერავები და კოშკი სანგრის ბოლო იუნიტს ურტყამენ.', 'Next battle your rear cannot be shot: flyers, scouts and towers hit the last unit in your trench.'] },
    palisade: { lv: 2, kind: 'order', t: ['შემდეგ ბრძოლაში შენი სანგრის წინ მესერი (0/6) დგას: მტერმა ჯერ ის უნდა დაანგრიოს.', 'Next battle a palisade (0/6) stands in front of your trench: the enemy must tear it down first.'] },
    volley: { lv: 2, kind: 'order', t: ['შემდეგ ბრძოლაში შენს ყველა იუნიტს +1 შეტევა.', 'Next battle all your units get +1 attack.'] },
    raid: { lv: 2, kind: 'order', t: ['შემდეგი ბრძოლის დასაწყისში შენი ბოლო იუნიტი მტრის ბოლო იუნიტს ურტყამს.', 'At the start of the next battle, your last unit strikes the enemy\'s last unit.'] },
    gas: { lv: 2, kind: 'order', t: ['შემდეგ ბრძოლაში, პირველი 3 რაუნდის ბოლოს, ყველა იუნიტს 1 ზიანი — შენსაც. ფარი და საფარი არ შველის.', 'Next battle, at the end of the first 3 rounds, 1 damage to every unit — yours too. Shields and cover do not help.'] },
    tower: { lv: 2, kind: 'order', t: ['შემდეგ ბრძოლაში ყოველ რაუნდში მტრის ბოლო იუნიტს 1 ზიანი.', 'Next battle, 1 damage to the enemy\'s last unit every round.'] },
    barrage: { lv: 3, kind: 'order', t: ['შემდეგი ბრძოლის დასაწყისში ყველა მტერს 2 ზიანი.', 'At the start of the next battle, 2 damage to every enemy.'] },
    hospital: { lv: 3, kind: 'order', t: ['შემდეგ ბრძოლაში შენი პირველი დაღუპული იუნიტი ნახევარი მდგრადობით ბრუნდება სანგრის ბოლოში.', 'Next battle your first fallen unit returns to the back of your trench with half its resilience.'] },
    nest: { lv: 4, kind: 'order', t: ['შემდეგ ბრძოლაში ყოველ რაუნდში მტრის სანგრის პირველ იუნიტს 2 ზიანი.', 'Next battle, 2 damage to the first enemy in the trench every round.'] }
  };
  for (const k in ITEMS) if (ITEMS[k].kind === 'order') { const c = CG.common[k]; ITEMS[k].ka = c.ka; ITEMS[k].en = c.en; ITEMS[k].art = c.art; }
  // ---- რელიქვიები (მთელი გარბენი) ----
  const REL = {
    rib: ['ამბრის ნეკნი', 'Ambri\'s Rib', 'შენი სანგრის პირველი იუნიტი ყოველ ბრძოლას +3 საფარით იწყებს.', 'The first unit in your trench starts every battle with +3 cover.'],
    chain: ['ხვამლის ჯაჭვი', 'Chain of Khvamli', 'ბრძოლის დასაწყისში მტრის სანგრის პირველი იუნიტი დათრგუნულია (−1 შეტევა).', 'At the start of battle, the first enemy in the trench is suppressed (−1 attack).'],
    cauldron: ['მედეას ქვაბი', 'Medea\'s Cauldron', 'ყოველ ბრძოლაში შენი პირველი დაღუპული იუნიტი 1 მდგრადობით ცოცხლდება.', 'In every battle, your first fallen unit revives with 1 resilience.'],
    tooth: ['დრაკონის კბილი', 'Dragon\'s Tooth', 'ყოველი ბრძოლის დასაწყისში სანგრის ბოლოს ამოიზრდება სპარტი (3/3).', 'At the start of every battle, a Sown Warrior (3/3) sprouts at the back of your trench.'],
    fleece: ['საწმისის ნაგლეჯი', 'Scrap of the Fleece', '+1 მარაგი ყოველ რაუნდში.', '+1 supply every round.'],
    hammer: ['შავხანის ჩაქუჩი', 'Shavkhan\'s Hammer', '★★ და ★★★ იუნიტებს +2 შეტევა.', '★★ and ★★★ units get +2 attack.'],
    horn: ['დალის ყანწი', 'Dali\'s Horn', 'შენი ყველა იუნიტი +2 ზიანს აყენებს დიდ მტერს.', 'All your units deal +2 damage to large enemies.'],
    collar: ['ყურშას საყელო', 'Qursha\'s Collar', 'შენი ზურგის იუნიტებს +1/+1.', 'Units in your rear get +1/+1.'],
    coil: ['მეხის ხვია', 'Thunder Coil', 'ბრძოლის დასაწყისში ყველა მტერს 1 ზიანი.', 'At the start of battle, 1 damage to every enemy.'],
    water: ['ცოცხალი წყალი', 'Water of Life', 'ერთხელ: როცა სიცოცხლეები ამოგეწურება, 2 ბრუნდება. შემდეგ რელიქვია ქრება.', 'Once: when your lives run out, 2 come back. The relic is then spent.'],
    deadwater: ['მკვდარი წყალი', 'Water of Death', 'შენი მკურნალები +1-ით მეტს კურნავენ.', 'Your healers restore 1 more.'],
    yoke: ['მზიდავის უღელი', 'Porter\'s Yoke', 'დანაზოგის სარგებელი მაქს. +4 (ნაცვლად +2-ისა).', 'Savings interest is capped at +4 (instead of +2).'],
    chart: ['საველე რუკა', 'Field Chart', 'ყოველ რაუნდში 1 უფასო განახლება.', 'One free reroll every round.'],
    shovel: ['სანგრის ნიჩაბი', 'Trench Spade', 'პირველ ორ რაუნდში შენი სანგრის პირველი იუნიტი ყოველ დარტყმაზე −1 ზიანს იღებს.', 'In the first two rounds, the first unit in your trench takes −1 from every hit.'],
    ring: ['ერისთავის ბეჭედი', 'Eristavi\'s Signet', 'შენი მეთაურები კიდევ +1 შეტევას აძლევენ.', 'Your leaders give +1 more attack.'],
    boiler: ['ორთქლის ქვაბი', 'Steam Boiler', 'შენს დიდ იუნიტებს (IV დონე და ზემოთ) +3 მდგრადობა.', 'Your large units (tier IV and up) get +3 resilience.'],
    scope: ['მსროლელის ჭოგრიტი', 'Marksman\'s Glass', 'შორი იუნიტების ცეცხლი ზურგიდან +1 ზიანი.', 'Long units firing from the rear deal +1 damage.'],
    oath: ['ძმობის ფიცი', 'Oath of Brothers', 'როცა შენი იუნიტი ეცემა, მისი ადგილის დამკავებელი +1 შეტევას იღებს.', 'When one of your units falls, the one taking its place gets +1 attack.']
  };
  // ---- რელიეფი: [ka, en, ტექსტი ka, ტექსტი en, წონა] ----
  const TER = {
    plain: ['ველი', 'Open field', 'განსაკუთრებული წესი არ არის.', 'No special rule.', 30],
    mud: ['ტალახი', 'Mud', 'იერიში არ მუშაობს.', 'Charge does not work.', 15],
    snow: ['თოვლი', 'Snow', 'ყოველი მე-3 რაუნდის ბოლოს ყველა იუნიტს 1 ზიანი (ყინვა).', 'At the end of every 3rd round, 1 damage to every unit (frost).', 15],
    coast: ['სანაპირო', 'Coast', 'მფრინავები +2 ზიანს აყენებენ.', 'Flyers deal +2 damage.', 14],
    fog: ['ნისლი', 'Fog', 'პირველ ორ რაუნდში ზურგიდან ვერ ისვრიან.', 'In the first two rounds, nobody can fire from the rear.', 13],
    ruins: ['ნანგრევები', 'Ruins', 'ორივე სანგრის პირველი იუნიტი +2 საფარით იწყებს.', 'The first unit in both trenches starts with +2 cover.', 13]
  };
  // ---- რჩეული რაზმის დამატებითი წესები ----
  const EMOD = {
    drill: ['წვრთნა', 'Drilled', 'მტრის ყველა იუნიტს +1 შეტევა.', 'Every enemy unit gets +1 attack.'],
    armor: ['ჯავშანი', 'Armoured', 'მტრის ყველა იუნიტი +2 საფარით იწყებს.', 'Every enemy unit starts with +2 cover.'],
    barrage: ['არტილერია', 'Artillery', 'ბრძოლის დასაწყისში შენს ყველა იუნიტს 2 ზიანი.', 'At the start of battle, 2 damage to all your units.'],
    nest: ['ტყვიამფრქვევი', 'Machine gun', 'ყოველ რაუნდში შენი სანგრის პირველ იუნიტს 2 ზიანი.', 'Every round, 2 damage to the first unit in your trench.'],
    wire: ['მავთული', 'Wire', 'პირველ რაუნდში შენი სანგრის პირველი იუნიტი ვერ ურტყამს.', 'In the first round, the first unit in your trench cannot strike.']
  };
  // ---- ხდომილებები: [ka, en, ტექსტი ka, ტექსტი en, [[არჩევანი ka, en], ...]] ----
  const EVT = {
    deserters: ['დეზერტირები', 'Deserters', 'გზაზე მშიერი ჯარისკაცები გხვდებიან. იარაღი ჯერ კიდევ ხელში უჭირავთ.', 'Hungry soldiers meet you on the road. They still hold their rifles.',
      [['რიგში ჩააყენე: უფასო იუნიტი შენი მაღაზიის დონიდან', 'Fall them in: a free unit from your muster level'], ['საგზალი წაართვი: +3 მარაგი', 'Take their rations: +3 supply']]],
    depot: ['მიტოვებული ვაგონი', 'Abandoned wagon', 'ლიანდაგზე ცარიელი ეშელონი დგას. ერთი ვაგონი დალუქულია.', 'An empty train stands on the rails. One wagon is still sealed.',
      [['გატეხე ლუქი: შემთხვევითი ბრძანება შემდეგი ბრძოლისთვის', 'Break the seal: a random order for the next battle'], ['ჩამოხსენი სპილენძი: +3 მარაგი', 'Strip the copper: +3 supply']]],
    wounded: ['დაჭრილთა კოლონა', 'Column of wounded', 'ფრონტიდან დაჭრილები მოჰყავთ. საკაცეები არ ჰყოფნით.', 'The wounded are coming back from the front. There are not enough stretchers.',
      [['დაეხმარე: −3 მარაგი, +1 სიცოცხლე', 'Help them: −3 supply, +1 life'], ['გაიარე: შემთხვევით იუნიტს +1/+1', 'March on: a random unit gets +1/+1']]],
    bargain: ['ქაჯის გარიგება', 'The Kaji\'s bargain', 'ღამით კოცონთან ვერცხლისთვალება მჭედელი ჯდება და რაღაცას გთავაზობს.', 'At night a silver-eyed smith sits down by your fire and makes an offer.',
      [['დათანხმდი: −1 სიცოცხლე, რელიქვია', 'Accept: −1 life, a relic'], ['გააგდე', 'Send him away']]],
    forge: ['ძველი სამჭედლო', 'The old forge', 'ნანგრევებში ქურა ჯერ კიდევ თბილია.', 'In the ruins the furnace is still warm.',
      [['გამოჭედე: შენი სანგრის პირველ იუნიტს +2 შეტევა', 'Forge: the first unit in your trench gets +2 attack'], ['შეაკეთე: შენი სანგრის პირველ იუნიტს +3 მდგრადობა', 'Mend: the first unit in your trench gets +3 resilience']]],
    song: ['სანგრის სიმღერა', 'Trench song', 'ვიღაც ჩუმად მღერის. მთელი ასეული აჰყვება.', 'Someone sings quietly. The whole company joins in.',
      [['იმღერეთ: +1 სიცოცხლე', 'Sing: +1 life'], ['ივარჯიშეთ: ველზე ყველა იუნიტს +1 მდგრადობა', 'Drill instead: every unit on the field gets +1 resilience']]],
    prisoner: ['ტყვე მზვერავი', 'Captured scout', 'გუშაგებმა მტრის მზვერავი დაიჭირეს.', 'Your sentries have caught an enemy scout.',
      [['დაკითხე: შემდეგ ბრძოლაში მტრის ყველა იუნიტს −1 შეტევა', 'Question him: in the next battle every enemy unit gets −1 attack'], ['გაცვალე: +4 მარაგი', 'Exchange him: +4 supply']]],
    crossroads: ['ნისლიანი გზაჯვარედინი', 'Foggy crossroads', 'მოკლე გზა ნაღმებით არის სავსე. გრძელზე მარაგის ურემი ჩანს.', 'The short road is mined. On the long one stands a supply cart.',
      [['გარისკე: 50% +6 მარაგი, 50% −1 სიცოცხლე', 'Risk it: 50% +6 supply, 50% −1 life'], ['ფრთხილად: +1 მარაგი', 'Go carefully: +1 supply']]]
  };
  const DEPOT = [['+6 მარაგი ახლავე', '+6 supply now'], ['4 უფასო განახლება', '4 free rerolls'], ['მაღაზიის დონის ამაღლება 3-ით იაფდება', 'Raising the muster level costs 3 less']];

  const BYF = {};
  for (const id in U) { const u = U[id]; ((BYF[u.f] = BYF[u.f] || {})[u.tier] = BYF[u.f][u.tier] || []).push(id); }

  // ================= ბრძოლა =================
  // A, B: { t: [სანგარი], r: [ზურგი] }, თითო იუნიტი { id, st, ba, bh, k: [დამატებითი უნარები], u: იდენტიფიკატორი }
  function simulate(A0, B0, opt) {
    opt = opt || {};
    const terrain = opt.terrain || 'plain';
    const S = { a: { t: [], r: [], m: opt.modsA || {}, k: 'a' }, b: { t: [], r: [], m: opt.modsB || {}, k: 'b' } };
    const ev = []; let uidc = 0, round = 0;
    const other = s => s === S.a ? S.b : S.a, units = s => s.t.concat(s.r), front = s => s.t[0] || null;
    function inst(x, s) {
      const d = def(x.id), st = x.st || 1, kw = U[x.id] ? traitsX(x) : {};
      let atk = Math.round(d.atk * MULT[st]) + (x.ba || 0), hp = Math.round(d.hp * MULT[st]) + (x.bh || 0);
      if (s.m.hammer && st >= 2) atk += 2;
      if (s.m.boiler && LARGE[d.tier]) hp += 3;
      if (s.m.drill && atk > 0) atk += 1;
      return { uid: s.k + (uidc++), ref: x.u || null, id: x.id, st, side: s.k, atk, hp, max: hp, kw, large: !!LARGE[d.tier],
        cover: 0, burn: 0, sup: 0, stub: !!kw.stubborn, quaked: false, noRev: !U[x.id] };
    }
    function last(s) { if (s.m.camo && s.t.length) return s.t[s.t.length - 1]; return s.r.length ? s.r[s.r.length - 1] : s.t[s.t.length - 1] || null; }
    function eatk(u, s) {
      if (!u || u.atk <= 0) return 0;
      let a = u.atk;
      if (s.t.includes(u)) for (const v of units(s)) if (v !== u && v.kw.leader) a += v.st + (s.m.ring ? 1 : 0);
      if (s.m.volley) a += 1;
      return Math.max(1, a - u.sup);
    }
    let pend = [];
    const hit = (src, dst, base, kind) => { if (dst && base > 0) pend.push({ src, dst, base, kind }); };
    function flush() {
      const q = pend; pend = [];
      for (const h of q) {
        const src = h.src, dst = h.dst, kind = h.kind; let n = h.base, abs = 0;
        if (dst.hp <= 0 && !dst.stub) continue;
        const ds = S[dst.side];
        if (kind !== 'burn' && kind !== 'gas' && kind !== 'frost' && kind !== 'fatigue') {
          if (src) { if (dst.large) n += src.kw.hunter ? 3 * src.st : S[src.side].m.horn ? 2 : 0; if (terrain === 'coast' && src.kw.fly) n += 2; }
          if (!(src && src.kw.breaker)) {
            let red = dst.kw.shield ? dst.st : 0;
            if (dst === front(ds)) red += (ds.m.trench ? 1 : 0) + (ds.m.shovel && round <= 2 ? 1 : 0);
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
    function remove(s, u) { let i = s.t.indexOf(u); if (i >= 0) { s.t.splice(i, 1); return [s.t, i]; } i = s.r.indexOf(u); s.r.splice(i, 1); return [s.r, i]; }
    function revive(u, s, hp, why) { u.hp = hp; u.max = Math.max(u.max, hp); u.burn = 0; u.sup = 0; u.cover = 0; u.noRev = true; s.t.push(u); ev.push({ t: 'revive', d: u.uid, hp, k: why }); }
    function cleanup() {
      let again = true, guard = 0;
      while (again && guard++ < 80) {
        again = false;
        for (const s of [S.a, S.b]) for (const u of units(s)) {
          if (u.hp > 0) continue;
          if (u.stub) { u.stub = false; u.hp = 1; ev.push({ t: 'stub', d: u.uid }); continue; }
          const [row, i] = remove(s, u); ev.push({ t: 'die', d: u.uid }); again = true;
          const o = other(s);
          if (u.kw.vengeance && front(o)) hit(u, front(o), Math.ceil(Math.max(1, u.atk - u.sup) / 2), 'venge');
          for (const v of units(s)) if (v.kw.brother && v.hp > 0) { v.atk += v.st; v.hp += v.st; v.max += v.st; ev.push({ t: 'buff', d: v.uid, k: 'brother' }); }
          if (s.m.oath && row[i] && row[i].atk > 0) { row[i].atk += 1; ev.push({ t: 'buff', d: row[i].uid, k: 'oath' }); }
          if (!u.noRev) {
            if (s.m.hospital && !s.hosp) { s.hosp = 1; revive(u, s, Math.ceil(u.max / 2), 'hospital'); }
            else if (s.m.cauldron && !s.caul) { s.caul = 1; revive(u, s, 1, 'cauldron'); }
          }
        }
        if (pend.length) { flush(); again = true; }
        for (const s of [S.a, S.b]) if (!s.t.length && s.r.length) { s.t = s.r; s.r = []; ev.push({ t: 'advance', side: s.k }); again = true; }
        for (const s of [S.a, S.b]) { const f = front(s);
          if (f && f.hp > 0 && f.kw.giant && !f.quaked && units(other(s)).length) { f.quaked = true; ev.push({ t: 'quake', s: f.uid });
            for (const v of units(other(s))) hit(f, v, 2 * f.st, 'quake'); flush(); again = true; } }
      }
    }
    const snap1 = (u, s) => ({ uid: u.uid, ref: u.ref, id: u.id, st: u.st, atk: eatk(u, s), hp: u.hp, max: u.max, cover: u.cover, burn: u.burn, sup: u.sup });
    const snap = s => ({ t: s.t.map(u => snap1(u, s)), r: s.r.map(u => snap1(u, s)) });
    const sync = () => ev.push({ t: 'sync', a: snap(S.a), b: snap(S.b) });
    const over = () => !units(S.a).length || !units(S.b).length;

    for (const k of ['a', 'b']) { const s = S[k], src = k === 'a' ? A0 : B0;
      for (const x of src.t || []) s.t.push(inst(x, s));
      for (const x of src.r || []) s.r.push(inst(x, s));
      if (s.m.collar) for (const u of s.r) { u.atk += 1; u.hp += 1; u.max += 1; }
      if (s.m.palisade) s.t.unshift(inst({ id: '_palisade' }, s));
      if (s.m.tooth) s.t.push(inst({ id: '_sparti' }, s));
      if (!s.t.length && s.r.length) { s.t = s.r; s.r = []; } }
    ev.push({ t: 'init', terrain, a: snap(S.a), b: snap(S.b) });
    // 1) მომზადება
    for (const s of [S.a, S.b]) { const o = other(s), f = front(s);
      if (f) { if (terrain === 'ruins') f.cover += 2; if (s.m.rib) f.cover += 3;
        for (const u of units(s)) if (u.kw.digger) { f.cover += 2 * u.st; ev.push({ t: 'fx', s: u.uid, d: f.uid, k: 'digger' }); } }
      if (s.m.armor) for (const u of units(s)) u.cover += 2;
      const of = front(o); if (s.m.chain && of && !of.kw.fearless) of.sup = Math.min(3, of.sup + 1);
      if (s.m.intel) for (const u of units(o)) if (!u.kw.fearless) u.sup = Math.min(3, u.sup + 1); }
    sync();
    // 2) გახსნის ცეცხლი
    ev.push({ t: 'phase', k: 'open' });
    for (const s of [S.a, S.b]) { const o = other(s);
      for (const u of units(s)) if (u.kw.scout) hit(u, last(o), 2 * u.st, 'scout');
      if (s.m.raid) { const r = s.r.length ? s.r[s.r.length - 1] : s.t[s.t.length - 1]; if (r) hit(r, last(o), eatk(r, s), 'raid'); }
      if (s.m.barrage) for (const v of units(o)) hit(null, v, 2, 'barrage');
      if (s.m.coil) for (const v of units(o)) hit(null, v, 1, 'coil'); }
    flush(); cleanup(); sync();
    // 3) იერიში
    if (terrain !== 'mud' && !over()) {
      for (const s of [S.a, S.b]) { const o = other(s); for (const u of units(s)) if (u.kw.charge) hit(u, front(o), eatk(u, s), 'charge'); }
      if (pend.length) { ev.push({ t: 'phase', k: 'charge' }); flush(); cleanup(); sync(); }
    }
    let gas = (S.a.m.gas || S.b.m.gas) ? 3 : 0;
    while (!over() && round < 40) {
      round++; ev.push({ t: 'round', n: round });
      // ზურგის ცეცხლი, ბუდე, კოშკი
      for (const s of [S.a, S.b]) { const o = other(s);
        if (!(terrain === 'fog' && round <= 2)) for (const u of s.r) if (u.kw.long && u.atk > 0) hit(u, front(o), Math.ceil(eatk(u, s) / 2) + (s.m.scope ? 1 : 0), 'support');
        if (s.m.nest) hit(null, front(o), 2, 'nest');
        if (s.m.tower) hit(null, last(o), 1, 'tower'); }
      if (pend.length) { flush(); cleanup(); sync(); if (over()) break; }
      // ჰაერი
      for (const s of [S.a, S.b]) { const o = other(s);
        if (!(terrain === 'fog' && round <= 2)) for (const u of s.r) if (u.kw.fly && u.atk > 0) hit(u, last(o), eatk(u, s), 'air');
        for (const u of units(s)) if (u.kw.anti_air) { const t = units(o).find(v => v.kw.fly); if (t) hit(u, t, 2 * u.st, 'aa'); } }
      if (pend.length) { flush(); cleanup(); sync(); if (over()) break; }
      // ხელჩართული: სანგრის პირველი — სანგრის პირველს
      const fa = front(S.a), fb = front(S.b);
      if (!(round === 1 && S.b.m.wire)) hit(fa, fb, eatk(fa, S.a), 'melee');
      if (!(round === 1 && S.a.m.wire)) hit(fb, fa, eatk(fb, S.b), 'melee');
      flush(); cleanup(); sync(); if (over()) break;
      // რაუნდის ბოლო
      for (const s of [S.a, S.b]) for (const u of units(s)) {
        if (u.burn) hit(null, u, u.burn, 'burn');
        if (gas > 0) hit(null, u, 1, 'gas');
        if (terrain === 'snow' && round % 3 === 0) hit(null, u, 1, 'frost');
        if (round >= 12) hit(null, u, round - 11, 'fatigue'); }
      flush();
      for (const s of [S.a, S.b]) {
        const heal = (u, t, n) => { if (t && t.hp > 0 && t.hp < t.max) { n = Math.min(n, t.max - t.hp); t.hp += n; ev.push({ t: 'heal', s: u.uid, d: t.uid, n }); } };
        for (const u of s.r) if (u.hp > 0 && u.kw.healer) heal(u, front(s), u.st + 1 + (s.m.deadwater ? 1 : 0));
        s.t.forEach((u, i) => { if (u.hp > 0 && u.kw.healer && i > 0) heal(u, s.t[i - 1], u.st + 1 + (s.m.deadwater ? 1 : 0)); });
        for (const u of units(s)) if (u.hp > 0 && u.kw.regen) heal(u, u, u.st);
      }
      cleanup(); if (gas > 0) gas--; sync();
    }
    const la = units(S.a).length, lb = units(S.b).length;
    const win = la && !lb ? 'a' : lb && !la ? 'b' : 'draw';
    ev.push({ t: 'end', win });
    return { ev, win, rounds: round, left: { a: la, b: lb }, alive: units(S.a).map(u => u.ref).filter(Boolean) };
  }

  // ================= გარბენი =================
  function rnd(run) { let t = run.rs = (run.rs + 0x6D2B79F5) | 0; t = Math.imul(t ^ t >>> 15, t | 1); t ^= t + Math.imul(t ^ t >>> 7, t | 61); return ((t ^ t >>> 14) >>> 0) / 4294967296; }
  const pick = (run, a) => a[Math.floor(rnd(run) * a.length)];
  function wpick(run, w) { let tot = 0; for (const k in w) tot += w[k]; let r = rnd(run) * tot; for (const k in w) { r -= w[k]; if (r < 0) return k; } return Object.keys(w)[0]; }
  function shuffle(run, a) { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd(run) * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
  const hash = s => { let h = 2166136261; s = String(s); for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };

  const stats = x => { const d = def(x.id), st = x.st || 1; return { atk: Math.round(d.atk * MULT[st]) + (x.ba || 0), hp: Math.round(d.hp * MULT[st]) + (x.bh || 0) }; };
  const power = (id, st) => { const d = def(id); return (d.atk + d.hp) * MULT[st || 1]; };
  function value(x) { const s = stats(x), k = traitsX(x); return s.atk + s.hp + 1.5 * Object.keys(k).filter(q => q !== 'vengeance' && q !== 'stubborn' && q !== 'brother').length + (k.stubborn ? 1 : 0); }
  const field = run => run.board.t.concat(run.board.r);
  const all = run => field(run).concat(run.bench);
  const find = (run, uid) => all(run).find(x => x.u === uid);
  const owns = (run, kw) => all(run).some(x => traitsX(x)[kw]);
  const space = run => run.board.t.length < T_CAP || run.board.r.length < R_CAP || run.bench.length < B_CAP;
  const sideOf = f => F[f].side;
  const allies = f => Object.keys(F).filter(k => F[k].side === sideOf(f) && k !== f);
  const foesOf = f => Object.keys(F).filter(k => F[k].side !== sideOf(f));

  function blank(o) {
    return Object.assign({ v: 2, round: 0, mus: 0, lvl: 1, upCost: UP[2] + 1, supply: 0, board: { t: [], r: [] }, bench: [], shop: null, orders: [], relics: [],
      pending: [], free: 0, intel: 0, uidc: 1, bonus: 0, seen: {}, stats: { battles: 0, wins: 0, losses: 0, draws: 0, merges: 0, elites: 0, flawless: 0, relics: 0, nodes: 0, tier: 1 } }, o);
  }
  function newRun(o) {
    const seed = (o.seed == null ? Math.floor(Math.random() * 4294967296) : o.seed) >>> 0;
    const diff = Math.max(0, Math.min(8, o.diff | 0));
    const run = blank({ seed, rs: seed, f: o.faction, diff, daily: o.daily || null, wins: 0, lives: LIVES - (diff >= 4 ? 1 : 0), ter: 'plain', elite: false, phase: 'prep', won: false });
    run.maxLives = run.lives;
    run.foe = pick(run, foesOf(run.f));
    startRound(run); return run;
  }
  function income(run) {
    const cap = run.relics.includes('yoke') ? 4 : 2;
    const o = { base: SUPPLY - (run.diff >= 5 ? 1 : 0), doc: frac(doc(run.f), run.mus), relic: run.relics.includes('fleece') ? 1 : 0,
      interest: Math.min(cap, Math.floor(run.supply / 5)), bonus: run.bonus || 0 };
    o.total = Math.max(1, o.base + o.doc + o.relic + o.interest + o.bonus); return o;
  }
  function startRound(run) {
    run.round++; run.mus++;
    if (run.lvl < 6) run.upCost = Math.max(0, run.upCost - 1);
    run.income = income(run); run.supply += run.income.total; run.bonus = 0;
    if (run.relics.includes('chart')) run.free += 1;
    run.enemy = makeEnemy(run);
    rollShop(run, true); run.phase = 'prep';
  }

  // ---- მოჩვენება-ჯარი: იგივე მაღაზია და იგივე წესები, ავტომატური მოთამაშე ----
  function ghost(f, rounds, seed, bias) {
    const g = blank({ f, rs: seed >>> 0, seed, ghost: true, diff: 0 });
    for (let k = 1; k <= rounds; k++) {
      g.round = k; g.mus = k; if (g.lvl < 6) g.upCost = Math.max(0, g.upCost - 1);
      g.supply += SUPPLY + frac(bias, k);                // ლოჯისტიკა მხოლოდ მოთამაშის ჯარს ეხება — ფრაქციები ერთმანეთზე არ მოქმედებენ
      rollShop(g, true); autoShop(g); march(g);
    }
    return { t: g.board.t, r: g.board.r, lvl: g.lvl };
  }
  function makeEnemy(run) {
    const elite = !!run.elite, rounds = run.round + (elite ? 1 : 0) + Math.floor(run.diff / 3);
    const g = ghost(run.foe, rounds, hash(run.seed + ':' + run.round + ':' + run.foe), GB + .35 * run.diff + (elite ? .5 : 0));
    const mods = [];
    if (elite) mods.push(pick(run, Object.keys(EMOD)));
    if (run.diff >= 6 && elite && !mods.includes('nest')) mods.push('nest');
    return { f: run.foe, t: g.t, r: g.r, lvl: g.lvl, mods, elite };
  }

  // ---- მაღაზია ----
  function offerUnit(run, f, merc) {
    const pool = BYF[f], w = {};
    for (const t in pool) { const l = LVL[t]; if (l > run.lvl) continue;
      if (t === 'hero' && owns(run, 'hero')) continue; if (t === 'V' && owns(run, 'giant')) continue;
      for (const id of pool[t]) w[id] = l === run.lvl ? 2 : 1; }
    const id = Object.keys(w).length ? wpick(run, w) : pool.I[0];
    run.seen[id] = Math.max(run.seen[id] || 0, 0);
    return { id, cost: merc ? MERC : COST, merc: !!merc, hold: false, sold: false };
  }
  function offerItem(run) { const w = {}; for (const k in ITEMS) if (ITEMS[k].lv <= run.lvl) w[k] = ITEMS[k].kind === 'order' ? 1 : 1.3; return { key: wpick(run, w), cost: COST, hold: false, sold: false }; }
  function rollShop(run, fresh) {
    const old = run.shop, n = SHOP_N[run.lvl], ni = run.lvl >= 4 ? 2 : 1, units = [], items = [];
    const kept = old ? old.units.filter(o => o.hold && !o.sold) : [], keptI = old ? old.items.filter(o => o.hold && !o.sold) : [];
    for (const o of kept) if (units.length < n) units.push(o);
    while (units.length < n) units.push(units.length === n - 1 && n >= 4 && rnd(run) < .5 ? offerUnit(run, pick(run, allies(run.f)), true) : offerUnit(run, run.f, false));
    for (const o of keptI) if (items.length < ni) items.push(o);
    while (items.length < ni) items.push(offerItem(run));
    run.shop = { units, items };
  }
  function reroll(run) {
    if (run.phase !== 'prep') return false;
    if (run.free > 0) run.free--; else if (run.supply >= 1) run.supply--; else return false;
    rollShop(run, false); return true;
  }
  function hold(run, kind, i) { const o = run.shop[kind === 'item' ? 'items' : 'units'][i]; if (o && !o.sold) o.hold = !o.hold; }
  function levelUp(run) {
    if (run.phase !== 'prep' || run.lvl >= 6 || run.supply < run.upCost) return false;
    run.supply -= run.upCost; run.lvl++; run.upCost = run.lvl < 6 ? UP[run.lvl + 1] : 0;
    run.stats.tier = Math.max(run.stats.tier, run.lvl); return true;
  }
  function canAdd(run, id) {
    const k = traits(id);
    if (k.hero && owns(run, 'hero')) return false;
    if (k.giant && owns(run, 'giant')) return false;
    return space(run) || (!k.hero && all(run).filter(x => x.id === id && x.st === 1).length >= 2);
  }
  function put(run, x, zone, idx) {                  // ცარიელ ადგილზე ჩასმა: სასურველი ზონა, შემდეგ სანგარი → ზურგი → სათადარიგო
    const Z = { t: [run.board.t, T_CAP], r: [run.board.r, R_CAP], b: [run.bench, B_CAP] };
    const order = (zone ? [zone] : []).concat(['t', 'r', 'b'].filter(z => z !== zone));
    for (const z of order) { const [arr, cap] = Z[z]; if (arr.length < cap) { arr.splice(z === zone && idx != null ? Math.min(idx, arr.length) : arr.length, 0, x); return true; } }
    return false;
  }
  function detach(run, x) { for (const arr of [run.board.t, run.board.r, run.bench]) { const i = arr.indexOf(x); if (i >= 0) { arr.splice(i, 1); return true; } } return false; }
  function randUnits(run, n, not) { return shuffle(run, field(run).filter(x => x !== not)).slice(0, n); }
  function addUnit(run, id, zone, idx) {
    if (!canAdd(run, id)) return null;
    const x = { u: run.uidc++, id, st: 1, ba: 0, bh: 0, k: [] };
    const twins = all(run).filter(y => y.id === id && y.st === 1);
    if (!(twins.length >= 2 && !traits(id).hero) || space(run)) { if (!put(run, x, zone, idx)) return null; }
    else { run.bench.push(x); }                         // სამეული ადგილს არ საჭიროებს: მაშინვე ერთიანდება
    run.seen[id] = Math.max(run.seen[id] || 0, 1);
    const k = traits(id), res = { unit: x, merged: false, gifts: [] };
    if (k.alchemist) for (const y of randUnits(run, 2, x)) { y.ba += 1; y.bh += 1; res.gifts.push(y.u); }
    if (k.orders) { const os = Object.keys(ITEMS).filter(q => ITEMS[q].kind === 'order' && ITEMS[q].lv <= run.lvl && !run.orders.includes(q)); if (os.length) { const q = pick(run, os); run.orders.push(q); res.order = q; } }
    res.merged = merge(run);
    return res;
  }
  function merge(run) {                              // სამი ერთნაირი (იგივე ★) → ერთი, ერთი ★-ით მეტი; + ბარათის არჩევა შემდეგი დონიდან
    let did = false, again = true;
    while (again) { again = false;
      const g = {}; for (const x of all(run)) if (x.st < 3 && !traits(x.id).hero) (g[x.id + ':' + x.st] = g[x.id + ':' + x.st] || []).push(x);
      for (const key in g) if (g[key].length >= 3) {
        const grp = g[key].slice(0, 3).sort((p, q) => (run.bench.includes(p) ? 1 : 0) - (run.bench.includes(q) ? 1 : 0));
        const [keep, b, c] = grp;
        keep.st++; keep.ba += b.ba + c.ba; keep.bh += b.bh + c.bh; keep.k = [...new Set(keep.k.concat(b.k, c.k))];
        detach(run, b); detach(run, c);
        run.stats.merges++; run.seen[keep.id] = Math.max(run.seen[keep.id] || 0, keep.st);
        run.pending.push(discover(run)); did = again = true; break; } }
    return did;
  }
  function discover(run) {
    const L = Math.min(6, run.lvl + 1), pool = [run.f].concat(allies(run.f).slice(0, 0));
    let ids = []; for (const f of pool) for (const t in BYF[f]) if (LVL[t] === L) ids = ids.concat(BYF[f][t]);
    ids = ids.filter(id => !(traits(id).hero && owns(run, 'hero')) && !(traits(id).giant && owns(run, 'giant')));
    if (ids.length < 3) for (const t in BYF[run.f]) if (LVL[t] < L) ids = ids.concat(BYF[run.f][t]);
    return shuffle(run, [...new Set(ids)]).slice(0, 3);
  }
  function takeDiscover(run, i) {                    // i < 0: უარი, +3 მარაგი
    const opts = run.pending[0]; if (!opts) return false;
    if (i < 0 || !opts[i]) { run.pending.shift(); run.supply += 3; return true; }
    if (!canAdd(run, opts[i])) return false;
    run.pending.shift(); addUnit(run, opts[i]); return true;
  }
  function buy(run, i, zone, idx) {
    if (run.phase !== 'prep' || run.pending.length) return null;
    const o = run.shop.units[i]; if (!o || o.sold || run.supply < o.cost) return null;
    const r = addUnit(run, o.id, zone, idx); if (!r) return null;
    run.supply -= o.cost; o.sold = true; o.hold = false; return r;
  }
  function applyItem(run, key, x) {
    const it = ITEMS[key];
    if (it.kind === 'order') { if (run.orders.includes(key)) return false; run.orders.push(key); return true; }
    if (it.kind === 'all') { const xs = key === 'crate' ? randUnits(run, 2) : field(run); if (!xs.length) return false; for (const y of xs) { y.ba += 1; y.bh += 1; } return true; }
    if (!x) return false;
    if (key === 'ration') { x.ba += 1; x.bh += 1; } else if (key === 'ammo') x.ba += 2; else if (key === 'plate') x.bh += 3;
    else if (key === 'helmet') { if (traitsX(x).stubborn) return false; x.k.push('stubborn'); } else if (key === 'medal') { x.ba += 2; x.bh += 2; }
    else if (key === 'prosthesis') { x.ba += 4; x.bh += 4; }
    return true;
  }
  function buyItem(run, i, uid) {
    if (run.phase !== 'prep') return false;
    const o = run.shop.items[i]; if (!o || o.sold || run.supply < o.cost) return false;
    if (!applyItem(run, o.key, uid != null ? find(run, uid) : null)) return false;
    run.supply -= o.cost; o.sold = true; o.hold = false; return true;
  }
  const refund = x => x.st || 1;
  function sell(run, uid) {
    if (run.phase !== 'prep') return false;
    const x = find(run, uid); if (!x) return false;
    detach(run, x); run.supply += refund(x); return true;
  }
  function move(run, uid, zone, idx) {               // გადაადგილება ან გაცვლა: zone 't' | 'r' | 'b'
    const x = find(run, uid); if (!x) return false;
    const Z = { t: [run.board.t, T_CAP], r: [run.board.r, R_CAP], b: [run.bench, B_CAP] }, [to, cap] = Z[zone];
    const from = [run.board.t, run.board.r, run.bench].find(a => a.includes(x)), fi = from.indexOf(x);
    if (from === to) { from.splice(fi, 1); to.splice(Math.min(idx, to.length), 0, x); return true; }
    const y = to[idx];
    if (y) { to[idx] = x; from[fi] = y; return true; }
    if (to.length >= cap) return false;
    from.splice(fi, 1); to.push(x); return true;
  }
  function march(run) {                              // ბრძოლაში გასვლა: „შეკეთების“ უნარები
    for (const row of [run.board.t, run.board.r]) row.forEach((x, i) => { if (traitsX(x).repair) for (const y of [row[i - 1], row[i + 1]]) if (y) y.bh += x.st; });
  }

  // ---- ავტომატური მოთამაშე (მოჩვენებები და ტესტის ბოტი) ----
  function frontScore(x) { const k = traitsX(x), s = stats(x);
    return s.hp + (k.shield ? 3 * x.st : 0) + (k.stubborn ? 2 : 0) + (k.giant ? 6 : 0) + (k.vengeance ? 1 : 0) - (k.long ? 4 : 0) - (k.healer ? 6 : 0) - (k.fly ? 6 : 0) - (k.leader ? 2 : 0) - (k.brother ? 3 : 0); }
  function rearScore(x) { const k = traitsX(x), s = stats(x);
    return (k.long ? s.atk + 3 : 0) + (k.fly ? s.atk * 2 + 3 : 0) + (k.healer ? 8 + 3 * x.st : 0) + (k.leader ? 4 : 0) - (k.shield ? 4 : 0) - (k.stubborn ? 2 : 0) - (k.giant ? 8 : 0); }
  function arrange(xs) {
    const rs = xs.map(x => [x, rearScore(x)]).filter(p => p[1] > 0).sort((p, q) => q[1] - p[1]);
    let r = rs.slice(0, R_CAP).map(p => p[0]), t = xs.filter(x => !r.includes(x));
    if (!t.length && r.length) t.push(r.pop());
    t.sort((p, q) => frontScore(q) - frontScore(p));
    while (t.length > T_CAP) { if (r.length < R_CAP) r.push(t.pop()); else break; }
    return { t: t.slice(0, T_CAP), r, rest: t.slice(T_CAP) };
  }
  function autoShop(g) {
    if (g.lvl < 6 && g.supply >= g.upCost && (g.round >= CURVE[g.lvl + 1] || g.upCost <= 1)) levelUp0(g);
    let rolls = 0, guard = 0;
    const weakest = () => all(g).filter(x => !(x.st === 1 && all(g).filter(y => y.id === x.id && y.st === 1).length >= 2)).sort((p, q) => value(p) - value(q))[0];
    while (guard++ < 40) {
      while (g.pending.length) { const o = g.pending[0]; let bi = -1, bv = -1; o.forEach((id, i) => { if (canAdd(g, id) && power(id, 1) > bv) { bv = power(id, 1); bi = i; } }); takeDiscover(g, bi); }
      let best = -1, bv = 0, sellFirst = null;
      g.shop.units.forEach((o, i) => { if (o.sold || o.cost > g.supply) return;
        const k = traits(o.id); if ((k.hero && owns(g, 'hero')) || (k.giant && owns(g, 'giant'))) return;
        const cp = all(g).filter(x => x.id === o.id && x.st === 1).length;
        let v = (power(o.id, 1) + 1.5 * Object.keys(k).length) / o.cost + (cp === 2 ? 12 : cp === 1 ? 2 : 0), sf = null;
        if (!space(g) && cp < 2) { const w = weakest(); if (!w || power(o.id, 1) + 1.5 * Object.keys(k).length <= value(w) * 1.25) return; sf = w; v -= 1; }
        if (v > bv) { bv = v; best = i; sellFirst = sf; } });
      if (best >= 0) { if (sellFirst) { detach(g, sellFirst); g.supply += refund(sellFirst); } g.phase = 'prep'; buy(g, best); continue; }
      const it = g.shop.items.findIndex(o => !o.sold && g.supply >= o.cost && field(g).length && !(ITEMS[o.key].kind === 'order' && g.orders.includes(o.key)));
      if (it >= 0 && g.supply >= COST) { const tgt = field(g).slice().sort((p, q) => value(q) - value(p)).find(x => !(g.shop.items[it].key === 'helmet' && traitsX(x).stubborn));
        if (buyItem0(g, it, tgt && tgt.u)) continue; }
      if (g.supply >= 1 + COST && rolls < 3 + Math.floor(g.round / 3)) { rolls++; g.phase = 'prep'; reroll(g); continue; }
      break;
    }
    const xs = all(g).sort((p, q) => value(q) - value(p)), a = arrange(xs.slice(0, T_CAP + R_CAP));
    g.board = { t: a.t, r: a.r }; g.bench = xs.slice(T_CAP + R_CAP).concat(a.rest).slice(0, B_CAP);
  }
  function levelUp0(g) { const ph = g.phase; g.phase = 'prep'; const r = levelUp(g); g.phase = ph; return r; }
  function buyItem0(g, i, uid) { const ph = g.phase; g.phase = 'prep'; const r = buyItem(g, i, uid); g.phase = ph; return r; }

  // ---- ბრძოლა გარბენში ----
  function mods(run) {
    const m = {}; for (const r of run.relics) m[r] = 1;
    for (const o of run.orders) m[o] = 1;
    if (run.intel) m.intel = 1; return m;
  }
  function fight(run) {
    if (run.phase !== 'prep' || !field(run).length || run.pending.length) return null;
    march(run);
    const em = {}; for (const k of run.enemy.mods) em[k] = 1;
    const sim = simulate(run.board, run.enemy, { terrain: run.ter, modsA: mods(run), modsB: em });
    run.orders = []; run.intel = 0; run.stats.battles++;
    const out = { sim, result: sim.win === 'a' ? 'win' : sim.win === 'b' ? 'lose' : 'draw', elite: run.enemy.elite, life: 0, round: run.round };
    if (out.result === 'win') {
      run.wins++; run.stats.wins++; if (out.elite) run.stats.elites++;
      if (sim.left.a >= field(run).length) run.stats.flawless++;
      for (const x of field(run)) { const k = traitsX(x);
        if (k.hero) { x.ba++; x.bh++; }
        if (k.song) { const y = randUnits(run, 1, x)[0]; if (y) { y.ba += x.st; y.bh += x.st; } } }
    } else if (out.result === 'lose') {
      run.stats.losses++; run.lives -= 1; out.life = 1;
      if (run.lives <= 0) { const i = run.relics.indexOf('water'); if (i >= 0) { run.relics.splice(i, 1); run.lives = 2; out.saved = true; } }
    } else run.stats.draws++;
    const wasElite = run.elite; run.elite = false;
    if (run.wins >= GOAL) { run.won = true; run.phase = 'over'; out.final = true; return out; }
    if (run.lives <= 0) { run.lives = 0; run.phase = 'over'; return out; }
    if (wasElite && out.result === 'win') { run.reward = { relics: relicChoices(run, 3) }; run.phase = 'reward'; return out; }
    after(run); return out;
  }
  function after(run) { if (run.round % 3 === 0) genMap(run); else startRound(run); }
  function relicChoices(run, n) { return shuffle(run, Object.keys(REL).filter(k => !run.relics.includes(k))).slice(0, n); }
  function takeRelic(run, i) { if (run.phase !== 'reward') return false; const k = run.reward.relics[i]; if (!k) return false;
    run.relics.push(k); run.stats.relics++; run.reward = null; after(run); return true; }
  const terrainRoll = run => { const w = {}; for (const k in TER) w[k] = TER[k][4]; return wpick(run, w); };
  function genMap(run) {
    const kinds = shuffle(run, ['camp', 'depot', 'event']).slice(0, 2), foes = shuffle(run, foesOf(run.f));
    run.map = ['elite'].concat(kinds).map((t, i) => ({ t, ter: terrainRoll(run), foe: foes[i % foes.length] }));
    run.phase = 'map';
  }
  function choose(run, i) {
    if (run.phase !== 'map') return false;
    const n = run.map[i]; if (!n) return false;
    run.ter = n.ter; run.foe = n.foe; run.stats.nodes++; run.map = null;
    if (n.t === 'elite') { run.elite = true; startRound(run); }
    else if (n.t === 'camp') run.phase = 'camp';
    else if (n.t === 'depot') run.phase = 'depot';
    else { run.phase = 'event'; run.event = pick(run, Object.keys(EVT)); }
    return true;
  }
  function campRest(run) { if (run.phase !== 'camp' || run.lives >= run.maxLives) return false; run.lives++; startRound(run); return true; }
  function campTrain(run, uid) { if (run.phase !== 'camp') return false; const x = find(run, uid); if (!x) return false; x.ba += 2; x.bh += 2; startRound(run); return true; }
  function depotTake(run, i) {
    if (run.phase !== 'depot') return false;
    if (i === 0) run.bonus += 6; else if (i === 1) run.free += 4; else if (i === 2) run.cheap = 3; else return false;
    startRound(run); if (run.cheap) { run.upCost = Math.max(0, run.upCost - run.cheap); run.cheap = 0; } return true;
  }
  function chooseEvent(run, opt) {
    if (run.phase !== 'event') return null;
    const e = run.event; let msg = {};
    const front = run.board.t[0] || field(run)[0];
    if (e === 'deserters') { if (opt === 0) { const ids = []; for (const t in BYF[run.f]) if (LVL[t] <= run.lvl && t !== 'hero' && t !== 'V') ids.push(...BYF[run.f][t]);
        const id = pick(run, ids); if (canAdd(run, id)) { addUnit(run, id); msg.unit = id; } else run.supply += 3; } else run.supply += 3; }
    else if (e === 'depot') { if (opt === 0) { const os = Object.keys(ITEMS).filter(q => ITEMS[q].kind === 'order' && !run.orders.includes(q)); const q = pick(run, os); run.orders.push(q); msg.order = q; } else run.supply += 3; }
    else if (e === 'wounded') { if (opt === 0) { if (run.supply < 3 || run.lives >= run.maxLives) return null; run.supply -= 3; run.lives++; } else { const y = randUnits(run, 1)[0]; if (y) { y.ba++; y.bh++; msg.unit = y.id; } } }
    else if (e === 'bargain') { if (opt === 0) { if (run.lives <= 1) return null; run.lives--; const k = relicChoices(run, 1)[0]; if (k) { run.relics.push(k); run.stats.relics++; msg.relic = k; } } }
    else if (e === 'forge') { if (front) { if (opt === 0) front.ba += 2; else front.bh += 3; msg.unit = front.id; } }
    else if (e === 'song') { if (opt === 0) { if (run.lives >= run.maxLives) return null; run.lives++; } else for (const y of field(run)) y.bh += 1; }
    else if (e === 'prisoner') { if (opt === 0) run.intel = 1; else run.supply += 4; }
    else if (e === 'crossroads') { if (opt === 0) { if (rnd(run) < .5) { run.supply += 6; msg.good = true; } else { run.lives = Math.max(1, run.lives - 1); msg.good = false; } } else run.supply += 1; }
    const intel = run.intel; run.event = null; startRound(run); run.intel = intel; return msg;
  }

  const xpFor = run => Math.round((run.stats.wins * 8 + run.round * 2 + run.stats.elites * 15 + (run.won ? 100 : 0)) * (1 + .25 * run.diff));
  function dailySeed(date) { const h = hash('tl-' + date); const fs = Object.keys(F); return { seed: h, faction: fs[h % fs.length], date }; }

  return { KW, ITEMS, REL, TER, EMOD, EVT, DEPOT, DOC, GB, LVL, SHOP_N, UP, MULT, LARGE, T_CAP, R_CAP, B_CAP, LIVES, GOAL, SUPPLY, COST, MERC, BYF, SPECIAL,
    doc, traits, traitsX, def, stats, power, value, simulate, newRun, income, startRound, ghost, makeEnemy, rollShop, reroll, hold, levelUp, canAdd,
    addUnit, merge, takeDiscover, buy, buyItem, applyItem, sell, refund, move, march, arrange, autoShop, mods, fight, takeRelic, choose, campRest,
    campTrain, depotTake, chooseEvent, xpFor, dailySeed, hash, all, field, find, owns, space, rnd };
});
