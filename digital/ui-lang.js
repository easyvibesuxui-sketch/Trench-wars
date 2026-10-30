// KA/EN ინტერფეისი ბილდერისთვის და თამაშებისთვის — tools/build_builder.py აკოპირებს builder/, digital/, defense/ საქაღალდეებში (ui-lang.js).
// ლექსიკონი: data/ui_en.json (ქართული ფრაზა → ინგლისური) → TW_DATA.en.ui. EN რეჟიმში DOM-ის ტექსტს, placeholder/aria-label/title-ს,
// canvas-ის ტექსტს და alert/confirm-ს თარგმნის; ქართულზე დაბრუნებისას ორიგინალს აღადგენს. რაც ლექსიკონში არ არის, ქართულად რჩება.
(function () {
  const D = window.TW_DATA || {}, UI = (D.en && D.en.ui) || {};
  const GE = "\\u10D0-\\u10FF", HAS = new RegExp("[" + GE + "]");
  const keys = Object.keys(UI).sort((a, b) => b.length - a.length).map(k => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  // ფრაზა მხოლოდ მთლიანი სიტყვით ითარგმნება: წინ და უკან ქართული ასო არ უნდა იყოს
  const RE = keys.length ? new RegExp("(?<![" + GE + "])(?:" + keys.join("|") + ")(?![" + GE + "])", "g") : null;
  const cache = new Map(), orig = new WeakMap(), ATTRS = ["placeholder", "aria-label", "title"];
  let on = false, kaTitle = null;

  function tr(s) {
    if (!on || !RE || typeof s !== "string" || !HAS.test(s)) return s;
    let r = cache.get(s);
    if (r === undefined) {
      r = s.replace(RE, m => UI[m]);
      if (cache.size > 5000) cache.clear();
      cache.set(s, r);
    }
    return r;
  }

  function fix(n) {
    if (n.nodeType === 3) {
      const p = n.parentNode;
      if (!p || /^(SCRIPT|STYLE|TEXTAREA)$/.test(p.nodeName)) return;
      const v = n.nodeValue, o = orig.get(n);
      if (on) {
        if (HAS.test(v)) { const t = tr(v); if (t !== v) { orig.set(n, { ka: v, en: t }); n.nodeValue = t; } }
      } else if (o && v === o.en) n.nodeValue = o.ka;
    } else if (n.nodeType === 1) {
      let o = orig.get(n);
      for (const a of ATTRS) {
        const v = n.getAttribute(a);
        if (v == null) continue;
        if (on) {
          if (HAS.test(v)) { const t = tr(v); if (t !== v) { (o = o || {})[a] = { ka: v, en: t }; n.setAttribute(a, t); } }
        } else if (o && o[a] && v === o[a].en) n.setAttribute(a, o[a].ka);
      }
      if (o) orig.set(n, o);
    }
  }

  function walk(root) {
    fix(root);
    if (root.nodeType !== 1) return;
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    for (let n; (n = w.nextNode());) fix(n);
  }

  new MutationObserver(ms => {
    if (!on) return;
    for (const m of ms) {
      if (m.type === "childList") m.addedNodes.forEach(walk);
      else fix(m.target);
    }
  }).observe(document.documentElement, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS });

  // canvas-ის წარწერები და დიალოგები
  const C2 = window.CanvasRenderingContext2D && CanvasRenderingContext2D.prototype;
  if (C2) ["fillText", "strokeText", "measureText"].forEach(f => { const o = C2[f]; C2[f] = function (t, ...a) { return o.call(this, tr(t), ...a); }; });
  ["alert", "confirm", "prompt"].forEach(f => { const o = window[f]; if (o) window[f] = (m, ...a) => o.call(window, tr(m), ...a); });

  function setLang(l) {
    if (kaTitle === null) kaTitle = document.title;
    on = l === "en";
    document.title = on ? tr(kaTitle) : kaTitle;
    walk(document.body || document.documentElement);
  }

  window.TW_UI = { tr, setLang };
})();
