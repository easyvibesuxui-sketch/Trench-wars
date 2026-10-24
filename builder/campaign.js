// კამპანიის რეჟიმი — იხ. rules/campaign.md
(function () {
  const B = window.TWB;
  if (!B) return;
  const { D, byId, esc } = B;
  const STORE = "tw-campaign-v1";

  const CURRENCY = { colchis: "სახელი", iberia: "სახელი", hell: "წოდება", harness: "სისხლი" };
  const INCOME = { win: [60, 3], draw: [40, 2], loss: [30, 1] };
  const RESULT = { win: "გამარჯვება", draw: "ფრე", loss: "მარცხი" };
  const XP_STEPS = [3, 6, 10, 15, 21];
  const ADV = {
    shoot: ["+1 სროლა", u => u.shoot < 9], melee: ["+1 ხელჩართული", u => u.melee < 9],
    nerve: ["+1 ნებისყოფა", u => u.nerve < 10], wounds: ["+1 სიცოცხლე", () => true], move: ["+1\" მოძრაობა", u => u.move < 12],
  };
  const PRISONER = {
    light: [["ransom", "გამოსასყიდი: +15 მარჩილი"], ["interrogate", "დაკითხვა: +1 სახელი"]],
    hell: [["labor", "ციხის მშენებლობა: +10 მარჩილი და +1 წოდება"]],
    harness: [["sacrifice", "სამსხვერპლო: +2 სისხლი"]],
  };
  const SHOP = {
    light: [["living_water", "ცოცხალი წყალი (ერთი სიკვდილის გაუქმება)", 3], ["renown", "სახელოვანი: მოდელს +1 ნებისყოფა", 2]],
    hell: [["rank", "წოდების ამაღლება: მოდელს +1 ხელჩართული", 2], ["flask", "ახალი კოლბა: 2 ახალწვეული უფასოდ", 3]],
    harness: [["devi_blood", "დევის სისხლი: მოდელს +1 ხელჩართული (სიგიჟის რისკი)", 1], ["stitch", "ქაჯის ნაკერი: 1 ქაჯების ნაკერი უფასოდ", 5]],
  };
  const SIDE_OF = { colchis: "light", iberia: "light", hell: "hell", harness: "harness" };
  const SIDE = new Proxy(SIDE_OF, { get: (o, f) => o[f] || "light" });  // მოკავშირე ფრაქციები ნათელი მხარეა
  const CURRENCY_OF = (f) => CURRENCY[f] || "სახელი";
  const fname = (f) => D.factions[f] || (D.allies || {})[f] || f;

  let camp = load();
  let mode = "build";
  let lastRolls = [];

  function load() { try { return JSON.parse(localStorage.getItem(STORE)); } catch (e) { return null; } }
  function save() { try { localStorage.setItem(STORE, JSON.stringify(camp)); } catch (e) { /* ბრაუზერი ბლოკავს — ექსპორტი მაინც მუშაობს */ } }
  const d10 = () => 1 + Math.floor(Math.random() * 10);
  const $ = id => document.getElementById(id);

  function eff(m) { // მოდელის მიმდინარე მაჩვენებლები წინსვლებით და ჭრილობებით
    const u = { ...byId[m.unit] };
    for (const a of m.adv) u[a] += 1;
    for (const i of m.inj) u[i] = Math.max(i === "move" ? 3 : 1, u[i] - 1);
    return u;
  }
  function advEarned(m) { return XP_STEPS.filter(x => m.xp >= x).length; }
  function rating() {
    return camp.models.filter(m => m.status !== "dead").reduce((s, m) => s + B.unitCost(byId[m.unit]) + 5 * m.adv.length, 0);
  }
  function hasLeader() { return camp.models.some(m => m.status !== "dead" && m.status !== "captured" && byId[m.unit].tags.includes("leader")); }

  function start() {
    const st = B.getState();
    const bad = B.checks().filter(([c]) => c === "bad");
    if (bad.length) { B.setStatus("კამპანიის დასაწყებად რაზმი წესებს უნდა აკმაყოფილებდეს: " + bad.map(b => b[1]).join("; ")); return; }
    let n = 0;
    const models = [];
    for (const [id, cnt] of B.picks()) for (let i = 0; i < cnt; i++) models.push({ uid: ++n, unit: id, name: `${byId[id].name} ${i + 1}`, xp: 0, status: "ok", adv: [], inj: [], miss: false });
    camp = { name: st.name || "უსახელო რაზმი", faction: st.faction, startBudget: st.budget, treasury: st.budget - B.spent(),
      currency: 0, models, nextUid: n + 1, stash: Object.fromEntries(B.gearPicks()), battles: [] };
    save(); setMode("campaign");
  }

  function setMode(m) {
    mode = m;
    $("tabBuild").setAttribute("aria-selected", m === "build");
    $("tabCampaign").setAttribute("aria-selected", m === "campaign");
    $("buildView").hidden = m !== "build";
    $("campaignView").hidden = m !== "campaign";
    if (m === "campaign") render();
  }

  function modelCard(m) {
    const u = eff(m), base = byId[m.unit];
    const status = { ok: "მზადაა", injured: "დაჭრილი — გამოტოვებს შემდეგ ბრძოლას", dead: "დაიღუპა", captured: "ტყვედაა" }[m.status];
    const pending = advEarned(m) - m.adv.length;
    const adv = m.adv.map(a => ADV[a][0]).concat(m.inj.map(i => `−1 ${{ shoot: "სროლა", melee: "ხელჩართული", nerve: "ნებისყოფა", move: "მოძრაობა" }[i] || i}`));
    return `<li class="model ${m.status === "dead" ? "dead" : ""}">
      <div class="model-top"><input type="text" id="mname-${m.uid}" data-mname="${m.uid}" value="${esc(m.name)}" aria-label="მოდელის სახელი" ${m.status === "dead" ? "disabled" : ""}>
        <span class="status-chip ${m.status}">${status}</span></div>
      <div class="model-meta"><span>${esc(base.name)} · ${base.tier}</span><span>გამოცდ.: <b>${m.xp}</b></span>
        <span>მოძ ${u.move}" · სრ ${u.shoot} · ხჩ ${u.melee} · ჯავ ${u.armor} · სიც ${u.wounds} · ნებ ${u.nerve}</span>
        ${adv.length ? `<span>${esc(adv.join(", "))}</span>` : ""}</div>
      ${m.status === "dead" ? (camp.stash.living_water ? `<div class="model-actions"><button type="button" data-revive="${m.uid}">ცოცხალი წყალი — აღდგენა</button></div>` : "")
        : `<div class="model-actions">
        ${pending > 0 ? `<select id="adv-${m.uid}" aria-label="წინსვლა">${Object.entries(ADV).filter(([, [, ok]]) => ok(u)).map(([k, [t]]) => `<option value="${k}">${t}</option>`).join("")}</select>
          <button type="button" class="primary" data-adv="${m.uid}">წინსვლა (${pending})</button>` : ""}
        ${m.status === "captured" ? `<button type="button" data-rescue="${m.uid}">გამოსყიდვა / გადარჩენა (30 მარჩილი)</button>` : ""}
        <button type="button" data-retire="${m.uid}">რაზმიდან გაშვება</button></div>`}
    </li>`;
  }

  // ომის კამპანია (data/campaigns): სცენარები, მსხვერპლი, დასასრული
  const STORY = (f) => (D.campaigns || {})[f];
  function storyPanel(f, done) {
    const c = STORY(f);
    if (!c) return "";
    done = done || [];
    const next = c.scenarios.findIndex((_, i) => !done.includes(i));
    const s = c.sacrifice;
    return `<div class="panel story"><h3>ომის კამპანია: ${esc(c.title)}</h3>
      <p class="sub"><b>მტერი:</b> ${esc(c.enemy)} · <b>გმირი:</b> ${esc(c.hero)}</p>
      <p>${esc(c.intro)}</p>
      <details><summary>მსხვერპლი: ${esc(s.name)} (${s.year}) — „${esc(s.title)}“</summary><p>${esc(s.text)}</p></details>
      <ol class="scenarios">${c.scenarios.map((sc, i) => `<li class="${done.includes(i) ? "done" : (i === next ? "next" : "")}">
        <details ${i === next ? "open" : ""}><summary><b>${esc(sc.name)}</b> ${done.includes(i) ? "✓" : (i === next ? "— შემდეგი" : "")}</summary>
        <p>${esc(sc.story)}</p><p><b>მიზანი:</b> ${esc(sc.objective)}</p><p><b>სპეციალური წესი:</b> ${esc(sc.special)}</p><p><b>ჯილდო:</b> ${esc(sc.reward)}</p></details></li>`).join("")}</ol>
      ${next === -1 ? `<p class="ending"><b>დასასრული.</b> ${esc(c.ending)}</p>` : ""}</div>`;
  }

  function render() {
    const view = $("campaignView");
    if (!camp) {
      view.innerHTML = `<div class="camp"><div class="panel"><h2>კამპანია ჯერ არ დაწყებულა</h2>
        <p class="sub">ააწყვე რაზმი „რაზმის აწყობის“ ჩანართში (წესების შესაბამისად) და დააჭირე ქვემოთ ღილაკს. რაზმის ყოველი მოდელი ცალკე
        მეომარი გახდება: დააგროვებს გამოცდილებას, მიიღებს ჭრილობებს და შეიძლება დაიღუპოს. დარჩენილი მარჩილი ხაზინაში გადავა.</p>
        <div class="form-row"><button type="button" class="primary" id="startCamp">კამპანიის დაწყება მიმდინარე რაზმით</button>
        <button type="button" id="importBtn">კამპანიის ჩატვირთვა ტექსტიდან</button></div>
        <textarea class="export" id="importBox" hidden aria-label="კამპანიის ტექსტი" placeholder="ჩასვი ადრე ექსპორტირებული კამპანია"></textarea>
        <span class="status" id="campStatus" role="status"></span></div>
        ${storyPanel(B.getState().faction, [])}</div>`;
      return;
    }
    camp.storyDone = camp.storyDone || [];
    const cur = CURRENCY_OF(camp.faction);
    const active = camp.models.filter(m => m.status !== "dead");
    const side = SIDE[camp.faction];
    const recruitable = D.units.filter(u => (u.faction === camp.faction || (u.allied && side === "light" && !u.tags.includes("leader")))
      && !["V", "hero"].includes(u.tier));
    view.innerHTML = `<div class="camp">
      <div class="camp-head"><h2>${esc(camp.name)} · ${esc(fname(camp.faction))}</h2>
        <div class="camp-stats">
          <div class="stat-pill"><b>${camp.treasury}</b><span>ხაზინა (მარჩილი)</span></div>
          <div class="stat-pill"><b>${camp.currency}</b><span>${cur}</span></div>
          <div class="stat-pill"><b>${rating()}</b><span>რაზმის რეიტინგი</span></div>
          <div class="stat-pill"><b>${camp.battles.length}</b><span>ბრძოლა</span></div>
        </div></div>
      ${hasLeader() ? "" : `<p class="checks"><span class="bad">✕ რაზმს ლიდერი არ ჰყავს — დაიქირავე ახალი ლიდერი ხაზინიდან.</span></p>`}
      ${storyPanel(camp.faction, camp.storyDone)}
      <div class="camp-grid">
        <div class="panel"><h3>მეომრები (${active.length})</h3><ul class="models">${camp.models.map(modelCard).join("")}</ul></div>
        <div class="camp" style="gap:16px">
          <form class="panel" id="battleForm"><h3>ბრძოლის ჩაწერა</h3>
            <div class="form-row"><label for="bResult">შედეგი</label>
              <select id="bResult"><option value="win">გამარჯვება</option><option value="draw">ფრე</option><option value="loss">მარცხი</option></select>
              <label for="bStory">სცენარი</label><select id="bStory">${(STORY(camp.faction) ? STORY(camp.faction).scenarios : []).map((sc, i) => `<option value="${i}" ${i === (STORY(camp.faction).scenarios.findIndex((_, j) => !camp.storyDone.includes(j))) ? "selected" : ""}>${i + 1}. ${esc(sc.name)}${camp.storyDone.includes(i) ? " ✓" : ""}</option>`).join("")}<option value="-1" ${STORY(camp.faction) && camp.storyDone.length >= STORY(camp.faction).scenarios.length ? "selected" : ""}>სხვა სცენარი</option></select>
              <input type="text" id="bScenario" maxlength="60" placeholder="სხვა სცენარის სახელი" aria-label="სხვა სცენარის სახელი"></div>
            <div class="form-row"><label for="bPrisoners">აყვანილი ტყვეები</label><input type="number" id="bPrisoners" min="0" max="10" value="0" style="width:4em">
              <select id="bPrisonerUse" aria-label="ტყვეების ბედი">${(PRISONER[side] || []).map(([k, t]) => `<option value="${k}">${t}</option>`).join("")}</select></div>
            <fieldset><legend>ვინ დაეცა ბრძოლაში / ვინ გამოიჩინა გმირობა</legend>
              ${camp.models.filter(m => m.status === "ok").map(m => `<div class="battle-row"><span>${esc(m.name)}</span>
                <label><input type="checkbox" data-down="${m.uid}"> დაეცა</label><label><input type="checkbox" data-hero="${m.uid}"> გმირობა</label></div>`).join("") || `<span class="empty">ბრძოლისთვის მზად მეომარი არ არის.</span>`}
            </fieldset>
            <button type="submit" class="primary">ბრძოლის შედეგის ჩაწერა</button>
            ${lastRolls.length ? `<div><b>კამათლები:</b><ul class="log">${lastRolls.map(r => `<li>${esc(r)}</li>`).join("")}</ul></div>` : ""}
          </form>
          <div class="panel"><h3>დაქირავება ხაზინიდან</h3>
            <div class="form-row"><select id="recruitSel" aria-label="იუნიტი">${recruitable.map(u => `<option value="${u.id}">${esc(u.name)} — ${B.unitCost(u)}${u.allied ? " (მოკავშირე)" : ""}</option>`).join("")}</select>
            <button type="button" class="primary" id="recruitBtn">დაქირავება</button></div></div>
          <div class="panel"><h3>${cur}ს დახარჯვა</h3>
            ${(SHOP[side] || []).map(([k, t, c]) => `<div class="form-row"><span>${t} — <b>${c}</b> ${cur}</span>
              ${["renown", "rank", "devi_blood"].includes(k) ? `<select id="shop-${k}" aria-label="მოდელი">${active.filter(m => m.status !== "captured").map(m => `<option value="${m.uid}">${esc(m.name)}</option>`).join("")}</select>` : ""}
              <button type="button" data-shop="${k}" data-price="${c}" ${camp.currency < c ? "disabled" : ""}>ყიდვა</button></div>`).join("")}
            ${Object.keys(camp.stash).length ? `<p class="sub">მარაგი: ${Object.entries(camp.stash).filter(([, n]) => n > 0).map(([id, n]) => `${n}× ${esc((B.itemById[id] || {}).name || (id === "living_water" ? "ცოცხალი წყალი" : id))}`).join(", ")}</p>` : ""}</div>
          <div class="panel"><h3>ბრძოლების ჟურნალი</h3>
            <ul class="log">${camp.battles.slice().reverse().map(b => `<li class="${b.result}"><b>${b.n}. ${RESULT[b.result]}</b>${b.scenario ? " · " + esc(b.scenario) : ""}
              <small>+${b.income} მარჩილი · +${b.gain} ${cur}${b.notes.length ? " · " + esc(b.notes.join("; ")) : ""}</small></li>`).join("") || `<li>ჯერ ბრძოლა არ ჩაწერილა.</li>`}</ul></div>
          <div class="panel"><div class="form-row">
            <button type="button" id="exportCamp">ექსპორტი ტექსტად</button>
            <button type="button" id="endCamp">კამპანიის დასრულება</button></div>
            <div id="endConfirm" hidden class="form-row"><span>ნამდვილად წაიშალოს ეს კამპანია ამ ბრაუზერიდან?</span>
              <button type="button" id="endYes">დიახ, წაშალე</button><button type="button" id="endNo">არა</button></div>
            <textarea class="export" id="campExport" readonly hidden aria-label="კამპანია ტექსტად"></textarea>
            <span class="status" id="campStatus" role="status"></span></div>
        </div>
      </div></div>`;
  }

  function status(t) { const el = $("campStatus"); if (el) el.textContent = t; }
  function model(uid) { return camp.models.find(m => m.uid === Number(uid)); }

  function recordBattle() {
    const result = $("bResult").value;
    const [inc, gain0] = INCOME[result];
    let income = inc, gain = gain0;
    const notes = []; lastRolls = [];
    const side = SIDE[camp.faction];
    const pris = Math.max(0, Math.min(10, Number($("bPrisoners").value) || 0));
    const use = $("bPrisonerUse") ? $("bPrisonerUse").value : "";
    if (pris) {
      if (use === "ransom") income += 15 * pris;
      if (use === "interrogate") gain += pris;
      if (use === "labor") { income += 10 * pris; gain += pris; }
      if (use === "sacrifice") gain += 2 * pris;
      notes.push(`${pris} ტყვე`);
    }
    // ვინც ამ ბრძოლას გამოტოვებდა, ახლა ჯანმრთელდება
    for (const m of camp.models) if (m.status === "injured") { m.status = "ok"; }
    const downs = new Set([...document.querySelectorAll("[data-down]:checked")].map(x => Number(x.dataset.down)));
    const heroes = new Set([...document.querySelectorAll("[data-hero]:checked")].map(x => Number(x.dataset.hero)));
    for (const m of camp.models) {
      if (m.status === "dead" || m.status === "captured") continue;
      if (heroes.has(m.uid)) m.xp += 1;
      if (result === "win" && byId[m.unit].tags.includes("leader")) m.xp += 1;
      if (!downs.has(m.uid)) { m.xp += 1; continue; }
      const r = d10();
      let txt;
      if (r === 1) { m.status = "dead"; txt = "დაიღუპა"; }
      else if (r === 2) { m.status = "captured"; txt = "ტყვედ ჩავარდა"; }
      else if (r <= 4) {
        const stat = ["shoot", "melee", "nerve", "move"][d10() % 4];
        m.inj.push(stat); m.status = "injured"; txt = "მძიმედ დაიჭრა (მუდმივი −1) და შემდეგ ბრძოლას გამოტოვებს";
      } else if (r <= 9) txt = "გამოჯანმრთელდა";
      else { m.xp += 1; txt = "გადარჩა და ისწავლა (+1 გამოცდილება)"; }
      lastRolls.push(`${m.name}: d10 = ${r} — ${txt}`);
    }
    camp.treasury += income; camp.currency += gain;
    const story = STORY(camp.faction), si = $("bStory") ? Number($("bStory").value) : -1;
    const scName = si >= 0 && story ? story.scenarios[si].name : $("bScenario").value.trim();
    if (si >= 0 && result === "win" && !camp.storyDone.includes(si)) {
      camp.storyDone.push(si);
      notes.push("სცენარის ჯილდო: " + story.scenarios[si].reward);
    }
    camp.battles.push({ n: camp.battles.length + 1, result, scenario: scName, income, gain, notes });
    save(); render(); status(`ჩაიწერა: +${income} მარჩილი, +${gain} ${CURRENCY_OF(camp.faction)}.`);
  }

  function buy(kind, price) {
    if (camp.currency < price) return;
    const sel = $("shop-" + kind);
    const m = sel ? model(sel.value) : null;
    if (["renown", "rank", "devi_blood"].includes(kind) && !m) { status("აირჩიე მოდელი."); return; }
    camp.currency -= price;
    if (kind === "living_water") camp.stash.living_water = (camp.stash.living_water || 0) + 1;
    if (kind === "renown") m.adv.push("nerve");
    if (kind === "rank" || kind === "devi_blood") m.adv.push("melee");
    if (kind === "flask") for (let i = 0; i < 2; i++) addModel("recruits");
    if (kind === "stitch") addModel("kaji_stitched");
    save(); render(); status("შეძენილია.");
  }

  function addModel(id) {
    const n = camp.models.filter(m => m.unit === id).length + 1;
    camp.models.push({ uid: camp.nextUid++, unit: id, name: `${byId[id].name} ${n}`, xp: 0, status: "ok", adv: [], inj: [], miss: false });
  }

  function exportText() {
    return JSON.stringify(camp);
  }

  document.addEventListener("click", e => {
    const t = e.target;
    if (t.closest("[data-mode]")) { setMode(t.closest("[data-mode]").dataset.mode); return; }
    if (t.id === "startCamp") { start(); return; }
    if (t.id === "importBtn") { const box = $("importBox"); if (box.hidden) { box.hidden = false; t.textContent = "ჩატვირთვა"; return; }
      try { const c = JSON.parse(box.value); if (!c.models || !c.faction) throw 0; camp = c; save(); render(); } catch (err) { status("ტექსტი ვერ წავიკითხე: ჩასვი ზუსტად ის, რაც „ექსპორტმა“ მოგცა."); } return; }
    if (!camp || mode !== "campaign") return;
    if (t.dataset.adv) { const m = model(t.dataset.adv); m.adv.push($("adv-" + m.uid).value); save(); render(); return; }
    if (t.dataset.revive) { const m = model(t.dataset.revive); camp.stash.living_water -= 1; m.status = "ok"; save(); render(); status(`${m.name} ცოცხალმა წყალმა დააბრუნა.`); return; }
    if (t.dataset.rescue) { if (camp.treasury < 30) { status("ხაზინაში 30 მარჩილი არ არის."); return; } const m = model(t.dataset.rescue); camp.treasury -= 30; m.status = "ok"; save(); render(); return; }
    if (t.dataset.retire) { const m = model(t.dataset.retire); camp.models = camp.models.filter(x => x !== m); save(); render(); status(`${m.name} რაზმიდან წავიდა.`); return; }
    if (t.dataset.shop) { buy(t.dataset.shop, Number(t.dataset.price)); return; }
    if (t.id === "recruitBtn") { const u = byId[$("recruitSel").value]; const c = B.unitCost(u);
      if (camp.treasury < c) { status(`ხაზინაში ${c} მარჩილი არ არის.`); return; }
      if (u.tags.includes("leader") && hasLeader()) { status("რაზმს უკვე ჰყავს ლიდერი."); return; }
      camp.treasury -= c; addModel(u.id); save(); render(); status(`${u.name} დაქირავებულია.`); return; }
    if (t.id === "exportCamp") { const box = $("campExport"); box.value = exportText(); box.hidden = false; box.select();
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(box.value).then(() => status("კოპირებულია. შეინახე ეს ტექსტი — მისით კამპანიას სხვა მოწყობილობაზეც ჩატვირთავ."), () => status("მონიშნულია — დააკოპირე ხელით."));
      return; }
    if (t.id === "endCamp") { $("endConfirm").hidden = false; return; }
    if (t.id === "endNo") { $("endConfirm").hidden = true; return; }
    if (t.id === "endYes") { camp = null; try { localStorage.removeItem(STORE); } catch (err) {} render(); return; }
  });
  document.addEventListener("submit", e => { if (e.target.id === "battleForm") { e.preventDefault(); recordBattle(); } });
  document.addEventListener("input", e => { const id = e.target.dataset && e.target.dataset.mname; if (id && camp) { model(id).name = e.target.value; save(); } });
})();
