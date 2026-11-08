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
    "hero": ("გმირი", "დასტაში მაქს. 1 გმირი; როცა ეცემა, შენი შტაბი 2 ნებისყოფას კარგავს"),
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
    "colchis": {"units": {"lashkari": 2, "port_brawlers": 2, "dali_hunters": 1, "aznauri": 2, "eristavi": 2, "medea_sisters": 2, "shavkhan_smiths": 2, "kolkhi_riders": 1, "monaspa": 2, "iron_arm_veterans": 2, "khalkotavri": 1},
                "common": {"trench": 2, "wire": 1, "nest": 1, "porter": 1, "barrage": 1, "gas": 2, "raid": 1, "recon": 2}},
    "harness": {"units": {"rebels": 1, "deserter_regulars": 2, "heretic_sappers": 2, "yoke_slaves": 1, "rebel_chief": 2, "blood_priests": 2, "chain_shooters": 2, "kaji_smith": 2, "chained_ones": 2, "kaji_stitched": 1, "gveleshapi": 1},
                "common": {"trench": 1, "palisade": 2, "nest": 1, "porter": 1, "barrage": 1, "gas": 1, "raid": 2, "train": 1, "volley": 1, "recon": 1}},
}


DECK_TWEAKS = {   # ფრაქცია → ავტომატური დასტის შესწორება სიმულაციით (ძლიერი კომპიუტერი, cardgame/index.html): id → რაოდენობა, 0 — ამოღება
    "hell": {"common": {"hospital": 0, "recon": 2}},
    "listeners": {"units": {"listeners_leader": 2, "lock_wagon": 0}, "common": {"raid": 2, "trench": 0}},
    "kajeti": {"units": {"cast_wardens": 2, "silver_sentinel": 1, "stitched_brutes": 2, "walking_furnace": 0, "wind_kaji": 0}},
    "ring": {"units": {"field_sisters": 1, "tribute_cuirassiers": 2}},
    "hellenic": {"units": {"automaton_phalanx": 2, "hellenic_grotesque": 0, "hellenic_regulars": 1, "lens_carriage": 1}},
    "northern": {"units": {"northern_grotesque": 0, "northern_leader": 2, "northern_thugs": 1, "tyr_onehands": 2}, "common": {"porter": 1, "raid": 2}},
    "celtic": {"units": {"celtic_leader": 2, "celtic_regulars": 1, "nuada_silverhands": 2, "sling_carriage": 0}},
    "finnish": {"units": {"finnish_grotesque": 0, "sampo_guards": 2, "sun_lantern": 1, "vainamoinen_singers": 1}, "common": {"gas": 2, "raid": 0}},
    "britain": {"units": {"britain_leader": 2, "britain_thugs": 1, "fen_drainers": 1, "fen_riders": 1, "huscarls": 2, "mere_divers": 2}, "common": {"barrage": 0, "recon": 2}},
    "gaul": {"units": {"gaul_leader": 2, "gaul_thugs": 1}, "common": {"gas": 0, "nest": 2}},
    "italy": {"units": {"hercules_hammers": 2, "praetorians": 2, "vulcan_ballista": 0, "vulcan_gunners": 1}},
    "polianitsy": {"units": {"polianitsa": 2, "polianitsy_grotesque": 1, "polianitsy_leader": 2, "sun_stove": 0, "young_polianitsy": 1, "zmei_slayers": 1}},
    "armenian": {"units": {"armenian_leader": 2, "armenian_thugs": 1, "highland_riflemen": 1, "tork_shieldbearers": 2}, "common": {"hospital": 1, "trench": 0}},
    "oghuz": {"units": {"div_breakers": 2, "korogly_guard": 0, "oghuz_leader": 2, "well_watchers": 1}, "common": {"gas": 2, "porter": 1}},
    "nile": {"units": {"mehen_coil_guard": 2, "nile_thugs": 1}},
    "yellow_river": {"units": {"tripod_cannon": 0, "yellow_river_leader": 2}},
    "japan_isles": {"units": {"japan_isles_regulars": 1, "karakuri_soldiers": 2}},
    "korea": {"units": {"fortress_wall_guard": 2, "korea_grotesque": 0, "korea_leader": 2, "tiger_hunters": 1}, "common": {"gas": 0, "nest": 2}},
    "mongolia": {"units": {"keshig": 0, "mongolia_leader": 2}},
    "pyrenean": {"units": {"cave_shields": 0, "pyrenean_leader": 2}, "common": {"barrage": 2, "recon": 0}},
    "alps": {"units": {"alps_grotesque": 0, "alps_leader": 2}, "common": {"gas": 0, "train": 2}},
    "baltic": {"units": {"amber_alchemists": 0, "amber_lancers": 2, "gate_wardens": 2}, "common": {"barrage": 2, "gas": 0, "nest": 2, "recon": 0}},
    "prussia": {"units": {"blue_dragoons": 1, "grenadiers": 1, "prussia_leader": 2, "shaft_guard": 2}},
    "batavi": {"units": {"batavi_leader": 2, "pump_engineers": 1}, "common": {"gas": 2, "recon": 0}},
    "lechia": {"units": {"lechia_leader": 2, "salt_mine_shields": 2, "uhlans": 1, "utopiec_hunters": 1}, "common": {"barrage": 0, "recon": 2}},
    "byzantium": {"units": {"byzantium_leader": 2, "chain_engineers": 1}},
    "ottoman": {"units": {"bastion_gunners": 2, "city_physicians": 1, "lantern_crawler": 1, "mehter_drummers": 1, "ottoman_grotesque": 0, "sipahis": 2}, "common": {"barrage": 2, "gas": 0, "nest": 2, "recon": 0}},
}


def auto_deck(fid, units):
    """სასტარტო დასტა (30) ფრაქციის ბარათებიდან: 20 იუნიტი + 10 საერთო ბარათი; ერთ ბარათს მაქს. 2 ასლი, IV — 1, IV+/გოლიათი — არა."""
    pool = [c for c in units if c["faction"] == fid]
    by = {t: sorted((c for c in pool if c["tier"] == t), key=lambda c: c["cost"]) for t in ("I", "II", "III", "IV")}
    deck = {}
    if by["IV"]:
        deck[max(by["IV"], key=lambda c: (c["atk"] + c["hp"]) / c["cost"])["id"]] = 1
    for c in by["I"][:5]:
        deck[c["id"]] = 2
    for c in by["III"][:2] + by["II"]:
        deck[c["id"]] = 1
    order = by["II"] + by["I"] + by["III"]                       # შევსება: ჯერ II-ის მეორე ასლები
    while sum(deck.values()) < 20:
        c = next((c for c in order if deck.get(c["id"], 0) < 2 and "leader" not in c["kw"]), None)
        if not c:
            break
        deck[c["id"]] = deck.get(c["id"], 0) + 1
    while sum(deck.values()) > 20:                              # ზედმეტი: ყველაზე ძვირი II/III ერთეული
        c = max((c for c in by["II"] + by["III"] if deck.get(c["id"]) and "leader" not in c["kw"]), key=lambda c: c["cost"])
        deck[c["id"]] -= 1
        if not deck[c["id"]]:
            del deck[c["id"]]
    kws = {k for c in pool if c["id"] in deck for k in c["kw"]}
    common = {"trench": 2, "porter": 2, "nest": 1, "barrage": 1, "raid": 1, "hospital": 1, "recon": 1, "gas": 1}
    if "digger" in kws:
        common["trench"], common["palisade"] = 1, 1
    if "healer" in kws:
        del common["hospital"]
        common["train"] = 1
    tw = DECK_TWEAKS.get(fid, {})
    for k in ("units", "common"):
        tgt = deck if k == "units" else common
        for i, n in tw.get(k, {}).items():
            if n:
                tgt[i] = n
            else:
                tgt.pop(i, None)
    return {"units": deck, "common": common}


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
    if u["tier"] == "hero":
        kws = kws + ["hero"]   # გმირის ნიშანი ბიუჯეტს არ აკლებს: მისი ფასი დაცემისას შტაბის −2 ნებისყოფაა
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
.decks { columns: 3; column-gap: 5mm; font-size: 6.6pt; line-height: 1.25; } .decks .deck { break-inside: avoid; margin-bottom: 2.5mm; }
.decks h3 { font-size: 8pt; margin: 0 0 .5mm; } .decks p { margin: 0; } .decks .cm { color: #6a6158; }
.rules { columns: 2; column-gap: 6mm; font-size: 8.6pt; } .rules h3 { margin: 2mm 0 1mm; font-size: 9.5pt; }
"""


def main():
    data = json.loads((ROOT / "data" / "units.json").read_text(encoding="utf-8"))
    costs = json.loads((ROOT / "data" / "costs.json").read_text(encoding="utf-8"))
    names = {**data["factions"], **data["allies"]}
    units = []
    for u in data["units"]:
        units.append(unit_card({**u, "cost": costs.get(u["id"], u.get("cost", 20))}, V.F[u["faction"]]["palette"]))
    common = [{"id": i, "kind": k, "name": n, "cost": c, "text": t, **({"atk": s[0], "hp": s[1]} if s else {}),
               "art": f"card_{i}.jpg" if (ART / f"card_{i}.jpg").exists() else None} for i, k, n, c, t, s in COMMON]
    byid0 = {c["id"]: c for c in units}
    starter = dict(STARTER)
    for fid in names:
        if fid not in starter:
            starter[fid] = auto_deck(fid, units)
    for fid, d in starter.items():
        n = sum(d["units"].values()) + sum(d["common"].values())
        assert n == 30, (fid, n)
        assert max(list(d["units"].values()) + list(d["common"].values())) <= 2, (fid, "ერთ ბარათს მაქს. 2 ასლი")
        assert all(k == 1 for i, k in d["units"].items() if byid0[i]["tier"] in ("IV", "IV+", "V")), (fid, "IV დონე და გოლიათი — 1 ასლი")
    (ROOT / "data" / "cardgame.json").write_text(json.dumps({"keywords": {k: {"name": v[0], "rule": v[1]} for k, v in KW.items()},
        "units": units, "common": common, "starter": starter}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    byid = {c["id"]: c for c in units}
    cbyid = {c["id"]: c for c in common}
    pages = [f'<section class="page"><h1>სამი ხაზი — ბარათის თამაში</h1><p>„ქვესკნელის ფრონტის“ ბარათის თამაში ორი მოთამაშისთვის, 20–30 წუთი. '
             f'ამ ფაილში: მოკლე წესები, ველი, სხვა ფრაქციების სასტარტო დასტების სია, კოლხეთისა და დიდი უღლის დასტები ბარათებად (30–30) და ზურგები. სრული წესები — <code>rules/cardgame.md</code>.</p>'
             f'{RULES_HTML}</section>',
             '<section class="page"><h2>ველი (თითო მოთამაშეს — თავისი ნახევარი)</h2><table class="board">'
             '<tr><td>მტრის ზურგი</td><td>მტრის ზურგი</td><td>მტრის ზურგი</td></tr><tr><td>მტრის სანგარი</td><td>მტრის სანგარი</td><td>მტრის სანგარი</td></tr>'
             '<tr class="nml"><td>ნეიტრალური ზოლი<br>მარცხენა ფლანგი</td><td>ნეიტრალური ზოლი<br>ცენტრი</td><td>ნეიტრალური ზოლი<br>მარჯვენა ფლანგი</td></tr>'
             '<tr class="mine"><td>შენი სანგარი (+ ნაგებობა)</td><td>შენი სანგარი (+ ნაგებობა)</td><td>შენი სანგარი (+ ნაგებობა)</td></tr>'
             '<tr class="mine"><td>შენი ზურგი</td><td>შენი ზურგი</td><td>შენი ზურგი</td></tr></table>'
             '<p>თითო ადგილზე მაქს. 2 იუნიტი. შტაბის ნებისყოფა: 20 (მთვლელი ან კამათელი). მზიდავები — შტაბის გვერდით.</p></section>']
    others = [f for f in starter if f not in STARTER]
    if others:   # დანარჩენი ფრაქციების დასტები — სიად (ბარათები: cards-all.pdf / ვიკი)
        lst = "".join(f'<div class="deck"><h3>{e(names[f])}</h3><p>' + ", ".join(f'{e(byid[i]["name"])} ×{n}' for i, n in starter[f]["units"].items())
                      + '</p><p class="cm">' + ", ".join(f'{e(cbyid[i]["name"])} ×{n}' for i, n in starter[f]["common"].items()) + "</p></div>" for f in others)
        pages.append(f'<section class="page"><h2>სხვა ფრაქციების სასტარტო დასტები ({len(others)})</h2><div class="decks">{lst}</div></section>')
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
    write_app(data, names, units, common, starter)
    arts = sum(1 for c in units if c["art"])
    print(f"data/cardgame.json: {len(units)} იუნიტის ბარათი ({arts} ილუსტრაციით) + {len(common)} საერთო · playtest/cardgame.html")


def write_app(data, names, units, common, starter):
    """ბრაუზერის ვერსიის მონაცემები: cardgame/data.js (window.CG). ილუსტრაციები — ვიკის სპრაიტ-ფურცლები (wiki/sheets/)."""
    from build_wiki import sheet_layout, LIGHT_CORE
    from i18n_en import en_texts, split2
    T = en_texts()
    NE = json.loads((ROOT / "data" / "names_en.json").read_text(encoding="utf-8"))
    _, _, pos, cpos = sheet_layout(data, names, common)
    wr = ROOT / "data" / "cardgame_winrates.json"
    win = json.loads(wr.read_text(encoding="utf-8"))["winrates"] if wr.exists() else {}
    two = lambda k, a, b: split2(T[k]) if k in T else (a, b)
    app = {
        "factions": {f: {"ka": n, "en": NE["factions"].get(f, n), "core": f in data["factions"],
                         "side": "light" if f in LIGHT_CORE or f in data["allies"] else "dark", "pal": V.F[f]["palette"]} for f, n in names.items()},
        "units": {c["id"]: {"f": c["faction"], "ka": c["name"], "en": NE["units"].get(c["id"], c["name"]), "tier": c["tier"], "cost": c["cost"],
                            "atk": c["atk"], "hp": c["hp"], "kw": c["kw"], "art": pos.get(c["id"])} for c in units},
        "common": {c["id"]: {"kind": c["kind"], "ka": c["name"], "en": two(f"cgc:{c['id']}", c["name"], c["text"])[0], "cost": c["cost"],
                             "tka": c["text"], "ten": two(f"cgc:{c['id']}", c["name"], c["text"])[1], "atk": c.get("atk"), "hp": c.get("hp"),
                             "art": cpos.get(c["id"])} for c in common},
        "kw": {k: dict(zip(("ka", "rka"), v)) | dict(zip(("en", "ren"), two(f"cgkw:{k}", *v))) for k, v in KW.items()},
        "starter": starter, "win": win,
    }
    out = ROOT / "cardgame" / "data.js"
    out.parent.mkdir(exist_ok=True)
    out.write_text("window.CG = " + json.dumps(app, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")


RULES_HTML = """<div class="rules">
<h3>მიზანი</h3><p>მოწინააღმდეგის შტაბის <b>ნებისყოფა 20-დან 0-მდე</b> ჩამოიყვანე, ან შენი სვლის დასაწყისში <b>სამივე ხაზის ნეიტრალური ზოლი</b> გეჭიროს (გარღვევა).</p>
<h3>მომზადება</h3><p>დასტა 30 ბარათი. აირიე, აიღე 5. ვინც მეორე იწყებს, +1 ბარათს და პირველ სვლაზე +2 მარაგს იღებს.</p>
<h3>სვლა</h3><ol><li><b>აიღე</b> 1 ბარათი.</li><li><b>მარაგი:</b> 3 + მზიდავები (მაქს. +3) + ნეიტრალური ზოლები, რომლებიც გიჭირავს. გამოუყენებელი ინახება (მაქს. 3).</li>
<li><b>ჩამოიყვანე</b> იუნიტები შენს ზურგში ან სანგარში (ფასი — მარცხენა ზედა წრე); ნაგებობა — სანგრის ადგილზე; ბრძანება — მაშინვე.</li>
<li><b>გადაადგილება:</b> ყოველი იუნიტი 1 ნაბიჯით წინ (ზურგი → სანგარი → ნეიტრალური ზოლი) ან უკან. ახლა ჩამოსული ადგილზე რჩება; ვინც გადაადგილდა ან ახლა ჩამოვიდა, ვერ უტევს (გარდა <b>იერიშისა</b>).</li>
<li><b>შეტევა:</b> ყოველი იუნიტი ერთხელ. სანგრიდან ან ნეიტრალური ზოლიდან — თავისი ხაზის <b>უახლოეს</b> მტერს (ნეიტრალური ზოლი → სანგარი → ზურგი);
<b>შორი</b> — ზურგიდანაც, ხაზის ნებისმიერ მტერს. თუ ხაზზე მტერი არ არის, ნეიტრალურ ზოლში მდგომი <b>შტაბს</b> ურტყამს შეტევის ტოლ ზიანს.</li></ol>
<h3>ზიანი</h3><p>შემტევი სამიზნეს აყენებს <b>შეტევის</b> ტოლ ზიანს; 0 მდგრადობაზე იუნიტი ეცემა. <b>ხელჩართული</b> (მეზობელ ადგილებზე, არა „შორი“) —
სამიზნე პასუხს სცემს თავისი შეტევით. სანგარში მყოფს <b>თხრილი</b> იცავს (−1).</p>
<h3>შეზღუდვები</h3><p>ერთ ბარათს მაქს. 2 ასლი; IV დონე — 1; გოლიათი — 1. მოკავშირე იმავე მხრიდან — მაქს. 9 ბარათი.
მშვიდობიანი მოსახლეობა სამიზნე არ არის; მზიდავებზე თავდასხმა არ შეიძლება.</p></div>"""


if __name__ == "__main__":
    main()
