#!/usr/bin/env python3
"""სათამაშო ნაკრები: მოკლე წესები, პირველი სცენარი ორი მზა რაზმით, იუნიტების ბარათები, ნეიტრალური ზოლის ფურცელი, ჟეტონები.

data/*.json + units/*.md → playtest/kit.html (ნაკრები) და playtest/cards-all.html (ყველა იუნიტის ბარათი)
PDF:  NODE_PATH=$(npm root -g) node tools/print_playtest.js
გაშვება (ბალანსერის შემდეგ):  python3 tools/build_playtest.py
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "playtest"
BUDGET = 300
# პირველი თამაშის რაზმები: (იუნიტის id, რაოდენობა)
WARBANDS = {
    "colchis": ("ღარის საგუშაგო", [("eristavi", 1), ("lashkari", 4), ("port_brawlers", 2), ("aznauri", 1), ("dali_hunters", 1), ("medea_sisters", 1)]),
    "harness": ("ღამის რეიდი", [("rebel_chief", 1), ("rebels", 5), ("deserter_regulars", 2), ("heretic_sappers", 1), ("yoke_slaves", 2),
                                 ("kudiani", 1), ("blood_priests", 1), ("chain_shooters", 1)]),
}
TIER_NAME = {"I": "ქვეითი", "II": "ელიტა", "III": "ჯავშნიანი", "IV": "გროტესკული", "IV+": "დიდი გროტესკული", "V": "გოლიათი", "hero": "გმირი"}
e = html.escape


def load():
    data = json.loads((ROOT / "data/units.json").read_text(encoding="utf-8"))
    costs = json.loads((ROOT / "data/costs.json").read_text(encoding="utf-8"))
    nml = json.loads((ROOT / "data/no_mans_land.json").read_text(encoding="utf-8"))
    page = (ROOT / "builder/index.html").read_text(encoding="utf-8")
    tags = {}
    for block in ("const TAG = {", "const WTAG = {"):
        i = page.index(block)
        tags.update(re.findall(r'\b([a-z_]+): "([^"]+)"', page[i:page.index("};", i)]))
    docs = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / "units").glob("*.md")}
    docs["_abilities"] = json.loads((ROOT / "data/abilities.json").read_text(encoding="utf-8"))["units"]
    return data, costs, nml, tags, docs


def clean(s):
    s = re.sub(r"\*\*?([^*]+)\*\*?", r"\1", s)
    return re.sub(r"`([^`]+)`", r"\1", s).strip()


def powers(u, docs):
    """ძალები და სისუსტე units/*.md-დან: ### სათაური (ძირითადი ფრაქციები) ან „- **სახელი** —“ (მოკავშირეები)."""
    name = u["name"]
    rules = docs.get("_abilities", {}).get(u["id"])
    if rules:  # ზუსტი წესები (data/abilities.json)
        weak = " ".join(r for n, r in rules if n.startswith("სისუსტე"))
        return " · ".join(f"{n}: {r}" for n, r in rules if not n.startswith("სისუსტე")), weak
    for text in (v for k, v in docs.items() if not k.startswith("_")):
        m = re.search(r"^### " + re.escape(name) + r"\b.*?$(.*?)(?=^#{2,3} |\Z)", text, re.S | re.M)
        if not m:
            continue
        body, out, weak, mode = m.group(1), [], "", None
        for line in body.splitlines():
            s = line.strip()
            if mode == "p" and line.startswith("  - "):
                out.append(clean(s[2:]))
            elif s.startswith("- **ძალები:**"):
                mode = "p"
                rest = clean(s[len("- **ძალები:**"):])
                if rest:
                    out.append(rest)
            elif s.startswith("- **სისუსტე:**"):
                weak, mode = clean(s[len("- **სისუსტე:**"):]), None
            elif s.startswith("- "):
                mode = None
        return " · ".join(out), weak
    for text in (v for k, v in docs.items() if not k.startswith("_")):
        m = re.search(r"^- \*\*" + re.escape(name) + r"\*\*(?: \([^)]*\))? — (.*?)$((?:\n  .*$)*)", text, re.M)
        if m:
            full = clean(m.group(1) + " " + " ".join(x.strip() for x in m.group(2).splitlines()))
            weak = ""
            if "სისუსტე:" in full:
                full, weak = full.split("სისუსტე:", 1)
            return full.strip(), weak.strip()
    return "", ""


def short(s, n):
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def card(u, cost, fname, tags, docs):
    pw, weak = powers(u, docs)
    stats = [("მოძ", f'{u["move"]}"'), ("სრ", u["shoot"] or "—"), ("ხჩ", u["melee"]), ("ჯავ", u["armor"]), ("სიც", u["wounds"]), ("ნებ", u["nerve"])]
    weapons = []
    for w in u["weapons"]:
        rng = "ხჩ" if w["mode"] == "melee" else f'{w["range"]}"'
        t = ", ".join(tags.get(x, x) for x in w["tags"])
        weapons.append(f'<tr><td>{e(w["name"])}</td><td>{rng}</td><td>{w["attacks"]}</td><td>{w["power"]}</td><td>{w["damage"]}</td>'
                       f'<td class="wt">{e(t)}</td></tr>')
    chips = "".join(f'<span class="chip">{e(tags[x])}</span>' for x in u["tags"] if x in tags)
    boxes = "".join('<i></i>' for _ in range(min(u["wounds"], 24)))
    return f'''<article class="card t{u["tier"].replace("+", "p")}">
  <header><b>{e(u["name"])}</b><span class="cost">{cost}</span></header>
  <div class="sub">{e(fname)} · {u["tier"]} {TIER_NAME[u["tier"]]}</div>
  <div class="stats">{"".join(f"<div><b>{v}</b><span>{k}</span></div>" for k, v in stats)}</div>
  <table class="wp"><tr><th>იარაღი</th><th>მან</th><th>შ</th><th>ძ</th><th>ზ</th><th></th></tr>{"".join(weapons)}</table>
  <div class="chips">{chips}</div>
  <p class="pw">{e(short(pw, 330))}</p>
  {f'<p class="weak">სისუსტე: {e(short(weak, 90))}</p>' if weak else ""}
  <div class="wounds">{boxes}</div>
</article>'''


CSS = """
@page { size: A4; margin: 8mm; }
:root { --ink:#1d1a16; --muted:#6a6158; --line:#b9ad9c; --bronze:#8a5a1c; --blood:#7a1f1a; --paper:#fbf8f2; }
* { box-sizing: border-box; }
body { margin:0; font-family:"Noto Sans Georgian","DejaVu Sans",sans-serif; color:var(--ink); background:#fff; font-size:9.6pt; line-height:1.38; }
h1,h2,h3 { font-family:"Noto Serif Georgian","DejaVu Serif",serif; margin:0 0 4mm; line-height:1.2; }
h1 { font-size:24pt; } h2 { font-size:14pt; color:var(--bronze); border-bottom:1.5px solid var(--bronze); padding-bottom:1mm; }
h3 { font-size:11pt; margin:3mm 0 1.5mm; }
p { margin:0 0 2mm; }
.page { page-break-after: always; break-after: page; }
.page:last-child { page-break-after: auto; }
.cols { column-count:2; column-gap:7mm; }
.cols h3 { break-after: avoid; }
.box { border:1px solid var(--line); background:var(--paper); padding:2.5mm 3mm; margin:0 0 3mm; break-inside: avoid; }
table { border-collapse:collapse; width:100%; margin:0 0 3mm; }
td, th { border:1px solid var(--line); padding:1mm 1.5mm; vertical-align:top; text-align:left; }
th { background:var(--paper); font-weight:700; }
.small { font-size:8.4pt; } .muted { color:var(--muted); }
ul { margin:0 0 2mm; padding-left:5mm; } li { margin:0 0 .8mm; }
.cover { display:flex; flex-direction:column; justify-content:center; min-height:270mm; }
.cover .lead { font-size:12pt; max-width:150mm; }
.cards { display:grid; grid-template-columns: repeat(3, 63mm); grid-auto-rows: 88mm; gap:2mm; justify-content:center; }
.card { border:1.2px solid var(--ink); border-radius:2.5mm; padding:2mm 2.4mm; display:flex; flex-direction:column; gap:1mm; overflow:hidden;
  font-size:7pt; line-height:1.25; break-inside: avoid; background:#fff; }
.card header { display:flex; justify-content:space-between; gap:2mm; font-family:"Noto Serif Georgian","DejaVu Serif",serif; font-size:9.4pt; }
.card .cost { color:var(--bronze); font-weight:700; white-space:nowrap; }
.card .sub { color:var(--muted); font-size:6.6pt; }
.card .stats { display:grid; grid-template-columns:repeat(6,1fr); text-align:center; border:1px solid var(--line); }
.card .stats div { border-right:1px solid var(--line); padding:.4mm 0; } .card .stats div:last-child { border-right:0; }
.card .stats b { display:block; font-size:9pt; } .card .stats span { font-size:5.8pt; color:var(--muted); }
.card .wp { font-size:6.4pt; margin:0; } .card .wp td, .card .wp th { padding:.3mm .6mm; } .card .wp .wt { font-size:5.8pt; }
.card .chips { display:flex; flex-wrap:wrap; gap:.6mm; }
.chip { border:1px solid var(--bronze); color:var(--bronze); border-radius:1mm; padding:0 .8mm; font-size:5.9pt; }
.card .pw { margin:0; font-size:6.1pt; flex:1; overflow:hidden; } .card .weak { margin:0; font-size:6.1pt; color:var(--blood); }
.card .wounds { display:flex; flex-wrap:wrap; gap:.6mm; } .card .wounds i { width:2.6mm; height:2.6mm; border:1px solid var(--ink); display:inline-block; }
.tV, .tIVp { border-width:2px; } .thero { border-color:var(--bronze); border-width:2px; }
.tokens { display:flex; flex-wrap:wrap; gap:3mm; align-items:center; }
.tok { width:16mm; height:16mm; border-radius:50%; border:1.2px solid var(--ink); display:flex; align-items:center; justify-content:center;
  text-align:center; font-size:6.6pt; line-height:1.1; padding:1mm; }
.tok.w { background:#f3dcd8; } .tok.f { background:#fbe3c4; } .tok.p { background:#e6e6e6; } .tok.s { background:#e8efe0; width:22mm; height:22mm; }
.tmpl { width:152.4mm; height:152.4mm; border-radius:50%; border:1.5px dashed var(--ink); display:flex; align-items:center; justify-content:center;
  color:var(--muted); margin:4mm auto; }
.roster td:last-child, .roster th:last-child { text-align:right; }
.map { width:105mm; height:105mm; border:1.5px solid var(--ink); position:relative; margin:2mm auto 3mm; background:var(--paper); font-size:7pt; }
.map div { position:absolute; display:flex; align-items:center; justify-content:center; text-align:center; }
.dz { left:0; right:0; height:20mm; background:repeating-linear-gradient(45deg,#e9e1d3,#e9e1d3 2mm,#f6f1e8 2mm,#f6f1e8 4mm); }
.ruin { width:16mm; height:12mm; border:1px solid var(--ink); background:#d9cfbf; }
.mark { width:8mm; height:8mm; border-radius:50%; border:1.5px solid var(--bronze); background:#fff; font-weight:700; }
.trench { height:3mm; background:#7b6a55; }
.feedback td { height:9mm; }
"""

FONTS = '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Georgian:wght@400;700&family=Noto+Serif+Georgian:wght@400;700&display=swap" rel="stylesheet">'


def doc(title, body):
    return f'''<!doctype html>
<html lang="ka"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>{FONTS}<style>{CSS}</style></head><body>
{body}
</body></html>
'''


QUICK_RULES = """
<section class="page"><h2>მოკლე წესები (1/2)</h2><div class="cols">
<h3>რა გჭირდება</h3>
<ul><li>2–4 ათწახნაგა კამათელი (<b>d10</b>), საზომი დუიმებში, ჟეტონები (ბოლო ფურცელი).</li>
<li>მაგიდა 36″×36″ (90×90 სმ), 6–8 რელიეფი: ნანგრევები, თხრილები, ჭა.</li>
<li>მოდელები: ნებისმიერი მინიატურა ან ბარათი — <b>ზომა</b>: ქვეითი 25–32 მმ ძირზე, ცხენოსანი 25×50 მმ.</li></ul>
<h3>ტესტი</h3>
<p>აგორე d10. <b>შედეგი ≤ მაჩვენებელი</b> — წარმატება. <b>ბუნებრივი 1</b> — ყოველთვის წარმატება (შეტევაზე — კრიტიკული, +1 ზიანი).
<b>ბუნებრივი 10</b> — ყოველთვის მარცხი.</p>
<h3>მაჩვენებლები</h3>
<p><b>მოძ</b> — მოძრაობა (″) · <b>სრ</b> — სროლა · <b>ხჩ</b> — ხელჩართული · <b>ჯავ</b> — ჯავშანი · <b>სიც</b> — სიცოცხლე (ჭრილობები) ·
<b>ნებ</b> — ნებისყოფა. იარაღი: <b>მან</b> — მანძილი, <b>შ</b> — შეტევები, <b>ძ</b> — ძალა, <b>ზ</b> — ზიანი.</p>
<h3>რაუნდი</h3>
<ol><li>ორივე აგორებს d10-ს; <b>დაბალი</b> შედეგი ირჩევს, ვინ იწყებს (ტოლობა — ვინც წინა რაუნდში მეორე იყო).</li>
<li>მოთამაშეები <b>რიგრიგობით აქტივირებენ თითო მოდელს</b>, სანამ ყველა არ იმოქმედებს.</li>
<li>აქტივირებულ მოდელს <b>2 მოქმედება</b> აქვს: მოძრაობა · სროლა · ბრძოლა · თხრა · ძალა · ძებნა.
ორი მოძრაობა = სირბილი (მის შემდეგ ვერ ისვრი).</li></ol>
<h3>სროლა</h3>
<ol><li><b>მოხვედრა:</b> d10 ≤ სრ, მოდიფიკატორებით: საფარი −1 · მძიმე საფარი (თხრილი, კედელი, ნანგრევი) −2 ·
იარაღის მანძილის ნახევარზე შორს −1 · სამიზნე ზომა 3–4 +1.</li>
<li><b>დაჭრა:</b> d10 ≥ <b>5 + ჯავშანი − ძალა</b> (მინ. 2, მაქს. 10).</li>
<li><b>ზიანი:</b> სამიზნე კარგავს „ზ“ რაოდენობის ჭრილობას. 0 სიცოცხლეზე მოდელი <b>ეცემა</b> (მოიხსენი).</li></ol>
<p>ხედვა: მოდელის „თვალიდან“ ხედავ სამიზნის ნაწილს? — ესვრი. კონტაქტში მყოფი მოდელი ვერ ისვრის (პისტოლეტის გარდა).</p>
<h3>ხელჩართული</h3>
<p><b>იერიში:</b> მოძრაობა, რომელიც მოწინააღმდეგესთან კონტაქტით მთავრდება; მისი მეორე მოქმედება — <b>ბრძოლა</b>.
მოხვედრა d10 ≤ ხჩ; დაჭრა — როგორც სროლაში. „იერიშის“ იარაღს პირველ დარტყმაზე +1 ძალა. კონტაქტიდან გასვლა — მოძრაობის მოქმედება,
მოწინააღმდეგე კი ერთ უფასო დარტყმას გაძლევს.</p>
<h3>მორალი</h3>
<p>როცა რაზმმა საწყისი მოდელების <b>ნახევარი</b> დაკარგა, ყოველი მოდელი თავის აქტივაციაზე აგორებს: d10 > ნებ → <b>უკან იხევს</b>
(ტოვებს ბრძოლას). ლიდერის 6″-ში +1.</p>
<h3>რელიეფი</h3>
<p><b>ნანგრევი, თხრილი, კედელი</b> — მძიმე საფარი. <b>თხრილის</b> კვეთა — მოძრაობის ნახევარი. <b>თხრა:</b> ინჟინერი ერთი მოქმედებით
3″-იან თხრილს თხრის. კედლები, კოშკები, თხრილები — სრული წესი: core-rules, 7ბ.</p>
</div></section>
<section class="page"><h2>მოკლე წესები (2/2) — ნიშნები ამ ნაკრების რაზმებში</h2><div class="cols small">
<h3>საერთო</h3>
<ul><li><b>ლიდერი:</b> რაზმში 1; 6″-ში მოკავშირეებს მორალის ტესტზე +1.</li>
<li><b>მწკრივი:</b> ორი ან მეტი ამ იუნიტის მოდელი ერთმანეთის 1″-ში — შორი მანძილის ჯარიმა მათ არ მოქმედებს.</li>
<li><b>ფარი:</b> სროლის წინააღმდეგ +1 ჯავშანი.</li>
<li><b>აირწინაღი:</b> გაზის ღრუბელში ჭრილობა მხოლოდ d10 = 1-ზე (აირწინაღის გარეშე — 1–3).</li>
<li><b>სანგრის ჩხუბი:</b> თხრილში, ნანგრევში ან შენობაში ხელჩართულისას +1 ხჩ.</li>
<li><b>ბრაზი:</b> ხელჩართულში +1 შეტევა. <b>იერიში:</b> იერიშის შემდეგ პირველ დარტყმაზე +1 ძალა.</li>
<li><b>შხამი:</b> დაჭრილი მოდელი d10 ≤ 5-ზე კიდევ 1 ჭრილობას კარგავს.</li>
<li><b>აფეთქება:</b> მოხვედრისას სამიზნის 2″-ში მყოფი ერთი სხვა მოდელი — d10 ≤ 5-ზე მასაც იგივე დაჭრის ტესტი.</li>
<li><b>ჩასაფრება:</b> განლაგების შემდეგ დგება ნებისმიერ ადგილას, მოწინააღმდეგის 12″-ზე შორს და მისი ხედვის გარეთ.</li>
<li><b>გოლიათზე მონადირე / გოლიათზე:</b> ზომა 3–4 სამიზნეზე დაჭრის რიცხვი −2.</li>
<li><b>ინჟინერი, თხრის თხრილს:</b> ერთი მოქმედება — 3″ თხრილი (მძიმე საფარი). <b>გვირაბი:</b> ერთხელ ბრძოლაში მოდელი იხსნება
და მომდევნო აქტივაციაზე ნებისმიერ ნანგრევთან ან თხრილთან ჩნდება.</li></ul>
<h3>კოლხეთი</h3>
<ul><li><b>ძველი ფიცი:</b> ერთხელ ბრძოლაში კოლხი თავად იღებს 1 ჭრილობას და ერთ ტესტს ავტომატურად გადის.</li>
<li><b>მკურნალი</b> (მედეას დები): მოქმედება — 6″-ში მოკავშირეს 1 სიცოცხლე უბრუნდება (საწყისზე მეტი არა).</li>
<li><b>ალქიმია:</b> პირველ თამაშში არ გამოიყენება (აღჭურვილობა — მეორე თამაშიდან, ბილდერში).</li></ul>
<h3>დიდი უღელი</h3>
<ul><li><b>სიგიჟე:</b> როცა ბელადი დაეცემა, ყოველ ერეტიკოსს +1 ხჩ, მაგრამ ყოველ აქტივაციაზე უახლოესი მოწინააღმდეგისკენ უნდა იმოძრაოს ან უტიოს.</li>
<li><b>ჯაჭვის ჯგუფი, ცოცხალი კედელი</b> (უღლის მონები): მონები ერთმანეთის 1″-ში მოძრაობენ; მათ უკან მყოფ ერეტიკოსს მსუბუქი საფარი აქვს.</li>
<li><b>შეიძლება გათავისუფლდეს:</b> კოლხი მონასთან კონტაქტში ერთი მოქმედებით ჯაჭვს ჭრის: d10 ≤ 5 → მონა თავისუფალია და მაგიდიდან
მიდის (კოლხეთს +1 ქულა). მონებს არავინ ესვრის სიამოვნებით — მაგრამ წესი ამას არ კრძალავს.</li>
<li><b>ხლართავს:</b> მოხვედრილი მოდელი შემდეგ აქტივაციაზე ვერ მოძრაობს.</li>
<li><b>რიტუალი</b> (სისხლის ქურუმები): 6″-ში ერეტიკოსებს ხელჩართულში +1 ძალა. <b>ტყვე</b> (მათი დანა): ამ იარაღით დაცემული ტყვეა (+1 ქულა).</li>
<li><b>ჯადოქარი, წყევლა</b> (კუდიანები): მოქმედება — 12″-ში ხილული მოწინააღმდეგე: d10 ≤ სრ → რაუნდის ბოლომდე −1 სრ და ხჩ.
<b>ბურუსი:</b> ერთხელ ბრძოლაში 12″-ში 3″ ბურუსი — მასში ვერავინ ხედავს და ვერ ისვრის.</li>
<li><b>დატენვა</b> (ჯაჭვის მსროლელები): გასროლის შემდეგ ხელახლა სროლამდე ერთი მოქმედება — დატენვა. <b>ჯაჭვი:</b> მოხვედრილი ზომა 3+ ნახევარ
მოძრაობას აკეთებს. <b>ცის ჩამოგდება:</b> მფრინავებზე +1 სრ.</li></ul>
<div class="box"><b>ბარათზე:</b> ჩარჩოში ჩასმული <b>ნიშნები</b> — ზემოთ აღწერილი წესებია; ქვემოთ დაწერილი <b>ძალები</b> — იუნიტის საკუთარი
ზუსტი წესები (სრულად: rules/abilities.md). <b>დათესილი მეომარი:</b> მოძ 5, ხჩ 5, ჯავ 1, სიც 1, ნებ 10, ხმალი (1 შეტევა, ძალა 2); ბრძოლის
ბოლოს იშლება; თავის აქტივაციაზე d10 = 1 → უახლოესს უტევს. <b>წაქცეული:</b> შემდეგ აქტივაციაზე 1 მოქმედება.</div>
<p class="muted">სრული წესები: rules/core-rules.md · ფასები: docs/balance-report.md · ბილდერი: builder/index.html</p>
</div></section>
"""


def scenario(rosters):
    return f"""
<section class="page"><h2>სცენარი 1 — „ღამე დამწვარ სოფელში“</h2>
<p><i>1914 წლის შემოდგომა. ფრონტმა დამწვარ სოფელს გადაუარა, რომლის მცხოვრებლებიც დიდი ხანია ზურგში წავიდნენ. დიდი უღლის ამბოხებულებს
ტყვეები სჭირდებათ სამსხვერპლოსთვის და სოფლის ნანგრევებში რეიდზე მოდიან; ღარის საგუშაგოს კოლხები მათ ჭასთან ხვდებიან.</i></p>
<div class="map">
  <div class="dz" style="top:0">დიდი უღლის განლაგება (6″)</div>
  <div class="dz" style="bottom:0">კოლხეთის განლაგება (6″)</div>
  <div class="trench" style="left:14mm;width:30mm;bottom:23mm"></div><div class="trench" style="right:14mm;width:30mm;bottom:23mm"></div>
  <div class="trench" style="left:30mm;width:24mm;top:23mm"></div>
  <div class="ruin" style="left:18mm;top:38mm">ნანგრ.</div><div class="ruin" style="right:18mm;top:44mm">ნანგრ.</div>
  <div class="ruin" style="left:40mm;top:64mm">ნანგრ.</div><div class="ruin" style="right:36mm;top:62mm">ნანგრ.</div>
  <div class="mark" style="left:56mm;top:48mm">ჭა</div>
  <div class="mark" style="left:14mm;top:48mm">1</div><div class="mark" style="right:14mm;top:48mm">2</div>
</div>
<div class="cols">
<h3>მომზადება</h3>
<ul><li>მაგიდა 36″×36″; განლაგება — 6″ საკუთარი კიდიდან. ორივე მხარეს 2 თხრილის მონაკვეთი (3″) განლაგების ზონის კიდეზე.</li>
<li>4–6 ნანგრევი (მძიმე საფარი) შუა ზოლში. <b>ჭა</b> — მაგიდის ცენტრში; <b>ძებნის მარკერები 1 და 2</b> — შუა ხაზზე, ცენტრიდან 12″-ზე.</li>
<li>პირველი განლაგდება დიდი უღელი; შემდეგ რიგრიგობით თითო იუნიტი. ჩასაფრებულები — ბოლოს.</li></ul>
<h3>ხანგრძლივობა: 6 რაუნდი</h3>
<h3>გამარჯვების ქულები</h3>
<ul><li><b>1</b> — ყოველი გაჩხრეკილი ძებნის მარკერი (ჭის ჩათვლით: ერთი მარკერი — ერთხელ; ძებნა — ცხრილი ნეიტრალური ზოლის ფურცელზე).</li>
<li><b>2</b> — მე-6 რაუნდის ბოლოს ჭის 3″-ში შენი მოდელია და მოწინააღმდეგის — არა.</li>
<li><b>1</b> — მოწინააღმდეგის ლიდერი დაეცა.</li>
<li><b>კოლხეთი: +1</b> — ყოველი გათავისუფლებული უღლის მონა. <b>დიდი უღელი: +1</b> — ყოველი ტყვე (ქურუმების დანა).</li></ul>
<h3>სპეციალური წესები</h3>
<ul><li><b>დამწვარი სოფლები:</b> ჭასთან მდგომი მოდელი ერთხელ ბრძოლაში 1 ჭრილობას იხსნის. სოფელში მცხოვრებლები არ არიან.</li>
<li><b>მეორე თამაში:</b> ღამის ცხრილი (ყოველი რაუნდის დასაწყისში) და მოხეტიალე მძორის ძაღლები.</li></ul>
</div>
</section>
<section class="page"><h2>მზა რაზმები ({BUDGET} მარჩილი)</h2>
<p>ორივე რაზმი ბილდერითაა აწყობილი და წესებს აკმაყოფილებს. ფასები — ბალანსერის ბოლო გაშვებიდან. მეორე თამაშიდან რაზმი თავად ააწყვე
(builder/index.html) — იგივე ბიუჯეტით.</p>
<div class="cols">{rosters}</div>
<h3>ტაქტიკური რჩევები პირველი თამაშისთვის</h3>
<ul><li><b>კოლხეთი:</b> ლაშქარი თხრილში და მწკრივში; დალის მონადირე — ჩასაფრებით ჭის მიმართულებით; აზნაური და ერისთავი — ჭისკენ;
მოჩხუბრები ნანგრევებში; მედეას დები — ერისთავის უკან.</li>
<li><b>დიდი უღელი:</b> მონები წინ (ცოცხალი კედელი), ამბოხებულები მათ უკან; განდგომილები მწკრივში ისვრიან; კუდიანი წყევლით ასუსტებს
აზნაურს; ქურუმი ტყვეებს ეძებს; მესანგრე გვირაბით ძებნის მარკერისკენ.</li></ul>
</section>
"""


def roster(fid, title, picks, units, costs, names):
    rows, total, models = [], 0, 0
    for uid, n in picks:
        u = units[uid]
        rows.append(f"<tr><td>{n}×</td><td>{e(u['name'])}</td><td>{u['tier']}</td><td>{costs[uid] * n}</td></tr>")
        total += costs[uid] * n
        models += n
    return (f"<div class='box'><h3>{e(names[fid])} — „{e(title)}“</h3><table class='roster'><tr><th></th><th>იუნიტი</th><th>დონე</th><th>ფასი</th></tr>"
            f"{''.join(rows)}<tr><th></th><th>{models} მოდელი</th><th></th><th>{total}</th></tr></table></div>", total)


def nml_sheet(nml):
    beasts = {b["id"]: b["name"] for b in nml["beasts"]}
    zones = "".join(f"<tr><td>{i + 1}</td><td><b>{e(z['name'])}</b></td><td>{'★' * z['danger']}</td><td>{e(re.sub(r'[*`]', '', z['rule']))}</td>"
                    f"<td>{e(beasts[z['monster']])}</td></tr>" for i, z in enumerate(nml["zones"]))
    search = "".join(f"<tr><td>{s['roll']}</td><td><b>{e(s['name'])}</b> — {e(s['text'])}</td></tr>" for s in nml["search"])
    night = "".join(f"<tr><td>{s['roll']}</td><td><b>{e(s['name'])}</b> — {e(s['text'])}</td></tr>" for s in nml["night"])
    beast_rows = "".join(f"<tr><td><b>{e(b['name'])}</b> ×{b['count']}</td><td>{b['move']}″</td><td>{b['melee']}</td><td>{b['armor']}</td>"
                         f"<td>{b['wounds']}</td><td>{e(b['attack'])}. {e(b['rule'])}</td></tr>" for b in nml["beasts"])
    return f"""
<section class="page small"><h2>ნეიტრალური ზოლი — ძებნა და ღამე</h2>
<div class="cols">
<h3>ძებნა (d10 + ზონა; მზვერავი +1; ბუნებრივი 1 — ხაფანგი)</h3><table>{search}</table>
<h3>ღამის ცხრილი (რაუნდის დასაწყისში)</h3><table>{night}</table>
</div></section>
<section class="page small"><h2>ნეიტრალური ზოლი — ზონები და ურჩხულები</h2>
<table><tr><th>d10</th><th>ზონა</th><th>საფრთხე</th><th>წესი</th><th>ურჩხული</th></tr>{zones}<tr><td>9–10</td><td colspan="4">თავად აირჩიე</td></tr></table>
<h3>მოხეტიალე ურჩხულები</h3>
<p>{e(nml['monster_rules'])}</p>
<table><tr><th>ურჩხული</th><th>მოძ</th><th>ხჩ</th><th>ჯავ</th><th>სიც</th><th>შეტევა და წესი</th></tr>{beast_rows}</table>
</section>"""


TOKENS = """
<section class="page"><h2>ჟეტონები და შაბლონი</h2>
<p class="small muted">ამოჭერი. ჭრილობის ჟეტონი — დაკარგული სიცოცხლე; ცეცხლი — ანთებული მოდელი; წნევა — ორთქლის წნევა; ძებნა — ძებნის მარკერი.</p>
<div class="tokens">""" + "".join('<div class="tok w">ჭრილობა</div>' for _ in range(12)) + \
    "".join('<div class="tok f">ცეცხლი</div>' for _ in range(6)) + "".join('<div class="tok p">წნევა</div>' for _ in range(6)) + \
    "".join(f'<div class="tok s">ძებნა<br>{x}</div>' for x in ("ჭა", "1", "2")) + "".join('<div class="tok">ტყვე</div>' for _ in range(3)) + \
    "".join('<div class="tok">თავისუფალი</div>' for _ in range(3)) + """</div>
<div class="tmpl">გაზი / ბურუსი — 3″ რადიუსი (6″ დიამეტრი)</div>
</section>
<section class="page"><h2>სატესტო თამაშის ფურცელი</h2>
<p>ეს ნაკრები სატესტოა: ყველაფერი შეიძლება შეიცვალოს. თამაშის შემდეგ შეავსე და გამოგვიგზავნე — ბალანსერი ფასებს შენი თამაშებითაც გაასწორებს.</p>
<table class="feedback"><tr><th style="width:45%">კითხვა</th><th>პასუხი</th></tr>
<tr><td>ვინ მოიგო და რა ქულით? რამდენი რაუნდი?</td><td></td></tr>
<tr><td>რამდენ ხანს გაგრძელდა თამაში?</td><td></td></tr>
<tr><td>რომელი წესი იყო გაუგებარი?</td><td></td></tr>
<tr><td>რომელი იუნიტი იყო ძალიან ძლიერი? რატომ?</td><td></td></tr>
<tr><td>რომელი იუნიტი იყო ზედმეტი ან სუსტი?</td><td></td></tr>
<tr><td>სცენარი: ჭა და ძებნა საინტერესო იყო?</td><td></td></tr>
<tr><td>უღლის მონების გათავისუფლება — მუშაობს?</td><td></td></tr>
<tr><td>რა დაამატებდი ან ამოიღებდი?</td><td></td></tr>
</table>
</section>"""


def main():
    data, costs, nml, tags, docs = load()
    units = {u["id"]: u for u in data["units"]}
    names = {**data["factions"], **data["allies"]}
    OUT.mkdir(exist_ok=True)
    rost, cards = [], []
    for fid, (title, picks) in WARBANDS.items():
        r, total = roster(fid, title, picks, units, costs, names)
        if total > BUDGET:
            raise SystemExit(f"{fid}: რაზმი {total} > {BUDGET} — შეცვალე WARBANDS")
        rost.append(r)
        cards += [card(units[uid], costs[uid], names[fid], tags, docs) for uid, _ in picks]
    cover = f"""<section class="page cover">
<p class="muted">სათამაშო ნაკრები · სატესტო ვერსია</p>
<h1>ამბრის ღარი — პირველი ღამე</h1>
<p class="lead">სკირმიში d10-ით: ორი მზა რაზმი ({BUDGET} მარჩილი) — <b>კოლხეთი</b> და <b>დიდი უღელი</b> — ერთი სცენარი ნეიტრალურ ზოლში,
მოკლე წესები, იუნიტების ბარათები, ნეიტრალური ზოლის ცხრილები და ჟეტონები. პირველი თამაში ~60–90 წუთი.</p>
<div class="box"><b>შიგთავსი:</b> 1. მოკლე წესები (2 გვ.) · 2. სცენარი და რაზმები · 3. იუნიტების ბარათები · 4. ნეიტრალური ზოლის ცხრილები ·
5. ჟეტონები და შაბლონი · 6. სატესტო ფურცელი</div>
<p class="small muted">ბეჭდვა: A4, მასშტაბი 100% (შაბლონი და ბარათები ზომაშია). ყველა ფრაქციის ბარათები — cards-all.pdf.</p>
</section>"""
    body = cover + QUICK_RULES + scenario("".join(rost)) + \
        f'<section class="page"><h2>იუნიტების ბარათები</h2><div class="cards">{"".join(cards)}</div></section>' + \
        nml_sheet(nml) + TOKENS
    (OUT / "kit.html").write_text(doc("სათამაშო ნაკრები", body), encoding="utf-8")
    # ყველა ფრაქციის ბარათი: ფრაქცია — ახალი გვერდიდან
    secs = []
    for fid, fname in names.items():
        fu = [u for u in data["units"] if u["faction"] == fid]
        secs.append(f'<section class="page"><h2>{e(fname)}</h2><div class="cards">'
                    + "".join(card(u, costs.get(u["id"], "—"), fname, tags, docs) for u in fu) + "</div></section>")
    (OUT / "cards-all.html").write_text(doc("იუნიტების ბარათები", "".join(secs)), encoding="utf-8")
    print(f"playtest/kit.html · playtest/cards-all.html ({len(data['units'])} ბარათი, {len(names)} ფრაქცია)")


if __name__ == "__main__":
    main()
