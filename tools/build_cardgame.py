#!/usr/bin/env python3
"""ბარათის თამაში „სამი ხაზი“: data/units.json → data/cardgame.json, playtest/cardgame.html (დასაბეჭდი ბარათები და ველი)

იუნიტის ბარათი მონაცემებიდან აიწყობა: ფასი (მარაგი) — მარჩილის ფასიდან, შეტევა და მდგრადობა — იუნიტის შეტევის და
გამძლეობის ფარდობით, ნიშნები — ტეგებიდან. საერთო ბარათები (ბრძანებები და ნაგებობები) — ქვემოთ, COMMON.
ილუსტრაციები — assets/art/<იუნიტის id>.jpg (Kling), სხვაზე — ფრაქციის ფერები.

გაშვება:  python3 tools/build_cardgame.py   (PDF: NODE_PATH=$(npm root -g) node tools/print_playtest.js)
"""
import html
import json
import math
from pathlib import Path

import visuals_data as V

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "assets" / "art"
e = html.escape

KW = {  # ნიშანი → (სახელი, წესი)
    "fly": ("ფრენა", "უტევს ნებისმიერ ხაზზე; ხელჩართული მას ვერ ურტყამს"),
    "anti_air": ("საზენიტო", "+2 შეტევა მფრინავზე"),
    "hunter": ("მონადირე", "+2 შეტევა დიდზე (გროტესკი, გოლიათი)"),
    "shield": ("ფარი", "−1 ყოველ მიღებულ ზიანზე"),
    "breaker": ("მტვრევა", "თხრილის საფარს და მესერს უგულებელყოფს"),
    "scout": ("მზვერავი", "შეიძლება პირდაპირ ნეიტრალურ ზოლში ჩამოვიდეს"),
    "long": ("შორი", "უტევს ზურგიდანაც, თავისი ხაზის ნებისმიერ მტერს"),
    "leader": ("მეთაური", "იმავე ხაზზე შენს სხვა იუნიტებს +1 შეტევა"),
    "healer": ("მკურნალი", "სვლის ბოლოს იმავე ხაზზე ერთ იუნიტს +2 მდგრადობა"),
    "digger": ("მესანგრე", "ჩამოსვლისას ამ ხაზზე უფასოდ თხრის თხრილს"),
    "charge": ("იერიში", "უტევს იმავე სვლაზე, როცა ჩამოვიდა"),
    "regen": ("ამოზრდა", "შენი სვლის დასაწყისში +1 მდგრადობა"),
    "fearless": ("უშიშარი", "მასზე დათრგუნვა არ მოქმედებს"),
    "suppress": ("დათრგუნვა", "სამიზნე მომდევნო სვლაზე ვერ უტევს"),
    "fire": ("ცეცხლი", "სამიზნე თავისი სვლის დასაწყისში 1 ზიანს იღებს"),
    "gas_mask": ("აირწინაღი", "გაზი მასზე არ მოქმედებს"),
    "giant": ("გოლიათი", "ჩამოსვლა მხოლოდ მაშინ, როცა 2 ხაზის ნეიტრალურ ზოლს აკონტროლებ; დასტაში მაქს. 1"),
}
STRONG = {"fly", "scout", "long", "charge", "suppress", "shield", "healer"}   # ძლიერი ნიშნები ძალის ბიუჯეტიდან 1-ს აკლებს

COMMON = [  # საერთო ბარათები: (id, სახეობა, სახელი, ფასი, ტექსტი, [შეტევა, მდგრადობა])
    ("trench", "ნაგებობა", "თხრილი", 1, "ამ ხაზზე შენს სანგარში მდგომი იუნიტები ყოველ ზიანზე −1-ს იღებენ (მინ. 1).", None),
    ("wire", "ნაგებობა", "მავთული", 2, "მტრის იუნიტი, რომელიც ამ ხაზის ნეიტრალურ ზოლში შემოდის, ამ სვლაზე ვეღარ უტევს.", None),
    ("palisade", "ნაგებობა", "მესერი", 2, "4 მდგრადობა. სანამ დგას, მტრის ხელჩართული ამ ხაზზე შენს სანგარს ვერ ურტყამს — ჯერ მესერი უნდა დაანგრიოს.", None),
    ("nest", "ნაგებობა", "ტყვიამფრქვევის ბუდე", 4, "შენი სვლის ბოლოს ურტყამს ამ ხაზის ნეიტრალურ ზოლში ან სანგარში მყოფ მტერს. დათრგუნვა.", [2, 4]),
    ("tower", "ნაგებობა", "საგუშაგო კოშკი", 3, "შენი სვლის ბოლოს ურტყამს ამ ხაზის ნებისმიერ მტერს. შორი.", [1, 5]),
    ("porter", "მარაგი", "მზიდავები", 2, "მუდმივად +1 მარაგი ყოველ სვლაზე (მაქს. 3 ბარათი). შტაბთან დგანან — მათზე თავდასხმა არ შეიძლება.", None),
    ("barrage", "ბრძანება", "საარტილერიო მომზადება", 4, "2 ზიანი მტრის ყველა იუნიტს ერთი ხაზის სანგარში.", None),
    ("gas", "ბრძანება", "გაზის ღრუბელი", 3, "1 ზიანი ერთი ხაზის ყველა იუნიტს — შენსაც. აირწინაღიანებს არ ეხება.", None),
    ("raid", "ბრძანება", "ღამის რეიდი", 2, "შენი ერთი იუნიტი გადადის ნეიტრალურ ზოლში და მაშინვე უტევს.", None),
    ("hospital", "ბრძანება", "საველე ჰოსპიტალი", 2, "ერთ იუნიტს +4 მდგრადობა (თავდაპირველზე მეტი არა).", None),
    ("recon", "ბრძანება", "დაზვერვა", 1, "აიღე 2 ბარათი.", None),
    ("train", "ბრძანება", "მარაგის მატარებელი", 2, "ამ სვლაზე +4 მარაგი.", None),
    ("volley", "ბრძანება", "ზალპი", 2, "ამ სვლაზე ერთი ხაზის ყველა შენს იუნიტს +1 შეტევა.", None),
    ("camo", "ბრძანება", "შენიღბვა", 1, "ერთი იუნიტი შენს მომდევნო სვლამდე სამიზნე ვერ იქნება.", None),
]
STARTER = {   # სასტარტო დასტები (30): იუნიტები × რაოდენობა + საერთო ბარათები × რაოდენობა
    "colchis": {"units": {"lashkari": 3, "port_brawlers": 3, "dali_hunters": 2, "aznauri": 1, "eristavi": 1, "medea_sisters": 2,
                          "shavkhan_smiths": 2, "kolkhi_riders": 2, "monaspa": 1, "iron_arm_veterans": 1, "khalkotavri": 1},
                "common": {"trench": 2, "wire": 1, "nest": 1, "porter": 2, "barrage": 1, "gas": 1, "raid": 1, "hospital": 1, "recon": 1}},
    "harness": {"units": {"rebels": 3, "deserter_regulars": 2, "heretic_sappers": 2, "yoke_slaves": 1, "rebel_chief": 1, "blood_priests": 1, "devi_spawn": 1,
                          "chain_shooters": 2, "kaji_smith": 1, "chained_ones": 2, "kaji_stitched": 1, "gveleshapi": 1},
                "common": {"trench": 1, "palisade": 2, "nest": 1, "porter": 2, "barrage": 1, "gas": 1, "raid": 1, "train": 1, "volley": 1, "recon": 1}},
}


def supply(cost):
    return max(1, min(12, round(2 * math.log2(max(cost, 10) / 10))))


def keywords(u):
    k, wt = [], {t for w in u["weapons"] for t in w["tags"]}
    rng = max([w["range"] for w in u["weapons"] if w["mode"] == "ranged"] or [0])
    melee_pref = u["melee"] >= u["shoot"] + 2 or rng <= 10
    add = lambda x: x not in k and k.append(x)
    if "giant" in u["tags"] and u["tier"] == "V":
        add("giant")
    if "fly" in u["tags"]:
        add("fly")
    if "suppress" in wt:
        add("suppress")
    if "leader" in u["tags"]:
        add("leader")
    if {"healer", "repair"} & set(u["tags"]):
        add("healer")
    if {"giant_hunter", "monster_hunter"} & set(u["tags"]) or "anti_giant" in wt:
        add("hunter")
    if "anti_air" in u["tags"] or "anti_air" in wt:
        add("anti_air")
    if "fire" in wt:
        add("fire")
    if "trench_breaker" in u["tags"] or "demolition" in wt:
        add("breaker")
    if {"shield", "shield_wall"} & set(u["tags"]):
        add("shield")
    if {"scout", "infiltrate"} & set(u["tags"]):
        add("scout")
    if not melee_pref and (rng >= 24 or "artillery" in u["tags"] or "indirect" in wt):
        add("long")
    if "cavalry" in u["tags"] or "charge" in wt:
        add("charge")
    if {"engineer", "digger"} & set(u["tags"]):
        add("digger")
    if "regen" in u["tags"]:
        add("regen")
    if "fearless" in u["tags"]:
        add("fearless")
    return k[:3]


def unit_card(u, palette):
    c = supply(u["cost"])
    off = max([w["attacks"] * w["power"] * max(1, w["damage"]) for w in u["weapons"]] or [1])
    dur = u["wounds"] * (1 + u["armor"] / 3) * (u.get("size") or 1) ** 0.5
    kws = keywords(u)
    budget = 2 * c + 1 - sum(1 for k in kws if k in STRONG)
    share = min(0.65, max(0.3, off / (off + dur)))   # შეტევის წილი ძალის ბიუჯეტში
    atk = max(1, min(budget - 1, round(budget * share)))
    return {"id": u["id"], "kind": "იუნიტი", "faction": u["faction"], "name": u["name"], "tier": u["tier"], "cost": c,
            "atk": atk, "hp": max(1, budget - atk), "kw": kws, "art": f"{u['id']}.jpg" if (ART / f"{u['id']}.jpg").exists() else None,
            "palette": [h for h, _ in palette]}


def card_html(c, names):
    pal = c.get("palette") or ["#8b7d5a", "#c8913e", "#4a5a6a"]
    art = (f'<div class="art" style="background-image:url(../assets/art/{c["art"]})"></div>' if c.get("art")
           else f'<div class="art blank" style="background:linear-gradient(160deg,{pal[0]},{pal[2]})"><span>{e(c["name"])}</span></div>')
    kws = "".join(f'<li><b>{e(KW[k][0])}</b> — {e(KW[k][1])}</li>' for k in c.get("kw", []))
    text = f'<p class="txt">{e(c["text"])}</p>' if c.get("text") else ""
    stats = (f'<div class="stats"><span class="atk" title="შეტევა">⚔ {c["atk"]}</span><span class="hp" title="მდგრადობა">⛨ {c["hp"]}</span></div>'
             if c.get("atk") is not None else "")
    sub = f'{e(names.get(c.get("faction"), "საერთო"))} · {e(c["kind"])}' + (f' · {c["tier"]}' if c.get("tier") else "")
    return (f'<div class="card" style="--a:{pal[1]};--d:{pal[0]}"><div class="head"><span class="cost">{c["cost"]}</span><span class="nm">{e(c["name"])}</span></div>'
            f'{art}<div class="sub">{sub}</div><ul class="kw">{kws}</ul>{text}{stats}</div>')


CSS = """
@page { size: A4; margin: 6mm; }
* { box-sizing: border-box; }
body { margin: 0; font: 9pt/1.3 "Noto Sans Georgian", "DejaVu Sans", sans-serif; color: #1d1a16; background: #fff; }
h1, h2 { font-family: "Noto Serif Georgian", serif; margin: 0 0 3mm; }
.page { page-break-after: always; padding: 2mm; }
.grid { display: grid; grid-template-columns: repeat(3, 63mm); gap: 2mm; justify-content: center; }
.card { width: 63mm; height: 88mm; border: 2.2mm solid var(--d); border-radius: 3mm; background: #f6f0e2; display: flex; flex-direction: column; overflow: hidden; position: relative; }
.head { display: flex; align-items: center; gap: 1.5mm; padding: 1mm 1.5mm; background: var(--d); color: #f6f0e2; }
.cost { width: 6.5mm; height: 6.5mm; border-radius: 50%; background: var(--a); color: #1d1a16; display: grid; place-items: center; font-weight: 700; flex: none; }
.nm { font-family: "Noto Serif Georgian", serif; font-weight: 700; font-size: 8.5pt; line-height: 1.1; }
.art { height: 40mm; background-size: cover; background-position: center 25%; border-bottom: .6mm solid var(--d); }
.art.blank { display: grid; place-items: center; color: #f6f0e2cc; font: 700 9pt "Noto Serif Georgian", serif; text-align: center; padding: 3mm; }
.sub { font-size: 6.5pt; color: #6a6158; padding: .8mm 1.5mm 0; }
.kw { list-style: none; margin: .5mm 0 0; padding: 0 1.5mm; font-size: 6.6pt; line-height: 1.2; }
.kw li { margin-bottom: .6mm; }
.txt { margin: .8mm 1.5mm; font-size: 7pt; }
.stats { margin-top: auto; display: flex; justify-content: space-between; padding: 1mm 1.5mm; font-weight: 700; font-size: 10pt; }
.atk { color: #7a1f1a; } .hp { color: #2f5d50; }
.back { width: 63mm; height: 88mm; border-radius: 3mm; background: url(../assets/art/card_back.jpg) center/cover; }
.board { width: 100%; border-collapse: collapse; margin-top: 4mm; } .board td { border: .5mm solid #b9ad9c; height: 34mm; text-align: center; color: #6a6158; width: 33%; }
.board tr.nml td { background: #efe6d2; } .board tr.mine td { background: #f8f3e8; }
.rules { columns: 2; column-gap: 6mm; font-size: 8.6pt; } .rules h3 { margin: 2mm 0 1mm; font-size: 9.5pt; }
"""


def main():
    data = json.loads((ROOT / "data" / "units.json").read_text(encoding="utf-8"))
    costs = json.loads((ROOT / "data" / "costs.json").read_text(encoding="utf-8"))
    names = {**data["factions"], **data["allies"]}
    units = []
    for u in data["units"]:
        if u["tier"] == "hero":
            continue
        units.append(unit_card({**u, "cost": costs.get(u["id"], u.get("cost", 20))}, V.F[u["faction"]]["palette"]))
    common = [{"id": i, "kind": k, "name": n, "cost": c, "text": t, **({"atk": s[0], "hp": s[1]} if s else {}),
               "art": f"card_{i}.jpg" if (ART / f"card_{i}.jpg").exists() else None} for i, k, n, c, t, s in COMMON]
    (ROOT / "data" / "cardgame.json").write_text(json.dumps({"keywords": {k: {"name": v[0], "rule": v[1]} for k, v in KW.items()},
        "units": units, "common": common, "starter": STARTER}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    byid = {c["id"]: c for c in units}
    cbyid = {c["id"]: c for c in common}
    pages = [f'<section class="page"><h1>სამი ხაზი — ბარათის თამაში</h1><p>„ქვესკნელის ფრონტის“ ბარათის თამაში ორი მოთამაშისთვის, 20–30 წუთი. '
             f'ამ ფაილში: მოკლე წესები, ველი, ორი სასტარტო დასტა (კოლხეთი და დიდი უღელი, 30–30 ბარათი) და ზურგები. სრული წესები — <code>rules/cardgame.md</code>.</p>'
             f'{RULES_HTML}</section>',
             '<section class="page"><h2>ველი (თითო მოთამაშეს — თავისი ნახევარი)</h2><table class="board">'
             '<tr><td>მტრის ზურგი</td><td>მტრის ზურგი</td><td>მტრის ზურგი</td></tr><tr><td>მტრის სანგარი</td><td>მტრის სანგარი</td><td>მტრის სანგარი</td></tr>'
             '<tr class="nml"><td>ნეიტრალური ზოლი<br>მარცხენა ფლანგი</td><td>ნეიტრალური ზოლი<br>ცენტრი</td><td>ნეიტრალური ზოლი<br>მარჯვენა ფლანგი</td></tr>'
             '<tr class="mine"><td>შენი სანგარი (+ ნაგებობა)</td><td>შენი სანგარი (+ ნაგებობა)</td><td>შენი სანგარი (+ ნაგებობა)</td></tr>'
             '<tr class="mine"><td>შენი ზურგი</td><td>შენი ზურგი</td><td>შენი ზურგი</td></tr></table>'
             '<p>თითო ადგილზე მაქს. 2 იუნიტი. შტაბის ნებისყოფა: 20 (მთვლელი ან კამათელი). მზიდავები — შტაბის გვერდით.</p></section>']
    for fid, deck in STARTER.items():
        cards = [byid[i] for i, n in deck["units"].items() for _ in range(n)] + [cbyid[i] for i, n in deck["common"].items() for _ in range(n)]
        assert len(cards) == 30, (fid, len(cards))
        for i in range(0, len(cards), 9):
            pages.append(f'<section class="page"><h2>{e(names[fid])} — სასტარტო დასტა ({i // 9 + 1})</h2><div class="grid">'
                         + "".join(card_html(c, names) for c in cards[i:i + 9]) + "</div></section>")
    in_decks = {i for d in STARTER.values() for i in d["units"]}
    extra = [c for c in units if c["art"] and c["id"] not in in_decks]
    if extra:
        pages.append('<section class="page"><h2>სხვა ფრაქციები — ილუსტრირებული ბარათების ნიმუშები</h2><div class="grid">'
                     + "".join(card_html(c, names) for c in extra[:9]) + "</div></section>")
    pages.append('<section class="page"><h2>ზურგები</h2><div class="grid">' + '<div class="back"></div>' * 9 + "</div></section>")
    page = (f'<!doctype html><html lang="ka"><head><meta charset="utf-8"><title>სამი ხაზი</title>'
            f'<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Georgian:wght@400;700&family=Noto+Serif+Georgian:wght@700&display=swap" rel="stylesheet">'
            f'<style>{CSS}</style></head><body>{"".join(pages)}</body></html>')
    (ROOT / "playtest" / "cardgame.html").write_text(page, encoding="utf-8")
    arts = sum(1 for c in units if c["art"])
    print(f"data/cardgame.json: {len(units)} იუნიტის ბარათი ({arts} ილუსტრაციით) + {len(common)} საერთო · playtest/cardgame.html")


RULES_HTML = """<div class="rules">
<h3>მიზანი</h3><p>მოწინააღმდეგის შტაბის <b>ნებისყოფა 20-დან 0-მდე</b> ჩამოიყვანე, ან შენი სვლის დასაწყისში <b>სამივე ხაზის ნეიტრალური ზოლი</b> გეჭიროს (გარღვევა).</p>
<h3>მომზადება</h3><p>დასტა 30 ბარათი. აირიე, აიღე 5. ვინც მეორე იწყებს, +1 ბარათს იღებს.</p>
<h3>სვლა</h3><ol><li><b>აიღე</b> 1 ბარათი.</li><li><b>მარაგი:</b> 3 + მზიდავები (მაქს. +3) + ნეიტრალური ზოლები, რომლებიც გიჭირავს. გამოუყენებელი ინახება (მაქს. 3).</li>
<li><b>ჩამოიყვანე</b> იუნიტები შენს ზურგში ან სანგარში (ფასი — მარცხენა ზედა წრე); ნაგებობა — სანგრის ადგილზე; ბრძანება — მაშინვე.</li>
<li><b>გადაადგილება:</b> ყოველი იუნიტი 1 ნაბიჯით წინ (ზურგი → სანგარი → ნეიტრალური ზოლი) ან უკან. ვინც გადაადგილდა, ამ სვლაზე ვერ უტევს (გარდა <b>იერიშისა</b>).</li>
<li><b>შეტევა:</b> ყოველი იუნიტი ერთხელ. სანგრიდან ან ნეიტრალური ზოლიდან — თავისი ხაზის <b>უახლოეს</b> მტერს (ნეიტრალური ზოლი → სანგარი → ზურგი);
<b>შორი</b> — ზურგიდანაც, ხაზის ნებისმიერ მტერს. თუ ხაზზე მტერი არ არის, ნეიტრალურ ზოლში მდგომი <b>შტაბს</b> ურტყამს შეტევის ტოლ ზიანს.</li></ol>
<h3>ზიანი</h3><p>შემტევი სამიზნეს აყენებს <b>შეტევის</b> ტოლ ზიანს; 0 მდგრადობაზე იუნიტი ეცემა. <b>ხელჩართული</b> (მეზობელ ადგილებზე, არა „შორი“) —
სამიზნე პასუხს სცემს თავისი შეტევით. სანგარში მყოფს <b>თხრილი</b> იცავს (−1).</p>
<h3>შეზღუდვები</h3><p>ერთ ბარათს მაქს. 2 ასლი; IV დონე — 1; გოლიათი — 1. მოკავშირე იმავე მხრიდან — მაქს. 9 ბარათი.
მშვიდობიანი მოსახლეობა სამიზნე არ არის; მზიდავებზე თავდასხმა არ შეიძლება.</p></div>"""


if __name__ == "__main__":
    main()
