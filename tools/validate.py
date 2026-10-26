#!/usr/bin/env python3
"""მონაცემების შემოწმება: data/units.json, data/costs.json, data/equipment.json, builder/index.html, units/*.md

გაშვება:  python3 tools/validate.py   (შეცდომაზე exit code 1)
"""
import os, json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIERS = {"I", "II", "III", "IV", "IV+", "V", "hero"}
COMBAT_TIERS = {"I", "II", "III", "IV", "IV+"}


def main():
    data = json.loads((ROOT / "data" / "units.json").read_text(encoding="utf-8"))
    costs = json.loads((ROOT / "data" / "costs.json").read_text(encoding="utf-8"))
    equipment = json.loads((ROOT / "data" / "equipment.json").read_text(encoding="utf-8"))
    html = (ROOT / "builder" / "index.html").read_text(encoding="utf-8")
    docs = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "units").glob("*.md"))
    factions, allies, units = data["factions"], data.get("allies", {}), data["units"]
    errors, warnings = [], []

    ids = [u["id"] for u in units]
    for i in sorted({i for i in ids if ids.count(i) > 1}):
        errors.append(f"გამეორებული id: {i}")
    by_id = {u["id"]: u for u in units}

    labels = set(re.findall(r"\b([a-z_]+): \"", html))
    m = re.search(r"const ALLY_NOTE = \{(.*?)\};", html, re.S)
    ally_notes = set(re.findall(r"\b([a-z_]+): \"", m.group(1))) if m else set()

    for u in units:
        uid = u["id"]
        if u["faction"] not in factions and u["faction"] not in allies:
            errors.append(f"{uid}: უცნობი ფრაქცია {u['faction']}")
        if bool(u.get("allied")) != (u["faction"] in allies):
            errors.append(f"{uid}: allied დროშა არ ემთხვევა ფრაქციას")
        if u["tier"] not in TIERS:
            errors.append(f"{uid}: უცნობი დონე {u['tier']}")
        checks = [("size", 1, 4), ("move", 0, 16), ("shoot", 0, 10), ("melee", 0, 10),
                  ("armor", 0, 7), ("wounds", 1, 40), ("nerve", 1, 10)]
        for key, lo, hi in checks:
            if not lo <= u[key] <= hi:
                errors.append(f"{uid}: {key}={u[key]} დიაპაზონს გარეთაა ({lo}–{hi})")
        if not u["weapons"]:
            errors.append(f"{uid}: იარაღი არ აქვს")
        for w in u["weapons"]:
            if w["mode"] not in ("ranged", "melee"):
                errors.append(f"{uid}/{w['name']}: უცნობი mode {w['mode']}")
            if w["attacks"] == 0 and "aura" in w["tags"]:
                continue  # ძალის ჩანაწერი იარაღის სახით (მაგ. დროშის ავრა)
            if w["mode"] == "ranged" and w["range"] < 3:
                errors.append(f"{uid}/{w['name']}: სასროლს მანძილი {w['range']}")
            if w["mode"] == "ranged" and u["shoot"] == 0:
                errors.append(f"{uid}/{w['name']}: სასროლი აქვს, მაგრამ სროლა 0")
            if w["mode"] == "melee" and w["range"] > 3:
                errors.append(f"{uid}/{w['name']}: ხელჩართულის მანძილი {w['range']}")
            for k in ("attacks", "power", "damage"):
                if w[k] < 0:
                    errors.append(f"{uid}/{w['name']}: {k} < 0")
            for t in w["tags"]:
                if t not in labels:
                    errors.append(f"{uid}/{w['name']}: იარაღის ნიშანს '{t}' ბილდერში სახელი არ აქვს")
        for t in u["tags"]:
            if t not in labels:
                errors.append(f"{uid}: ნიშანს '{t}' ბილდერში სახელი არ აქვს")
        if uid not in costs:
            errors.append(f"{uid}: ფასი არ აქვს (data/costs.json)")
        if u["name"] not in docs:
            warnings.append(f"{uid}: სახელი „{u['name']}“ units/*.md-ში არ ჩანს")

    roles = {r["id"] for r in json.loads((ROOT / "data" / "roles.json").read_text(encoding="utf-8"))["roles"]}
    for u in units:
        if u.get("role") not in roles:
            errors.append(f"{u['id']}: როლი არ აქვს ან უცნობია ({u.get('role')}) — გაუშვი tools/assign_roles.py")

    for k in costs:
        if k not in by_id:
            warnings.append(f"costs.json: ზედმეტი ჩანაწერი {k}")

    # ყველა ფრაქციას (ძირითადს და მოკავშირეს) სჭირდება: ლიდერი, ელიტა, გროტესკი და გოლიათი
    for fid, fname in list(factions.items()) + list(allies.items()):
        fu = [u for u in units if u["faction"] == fid]
        if not any("leader" in u["tags"] and u["tier"] in COMBAT_TIERS for u in fu):
            errors.append(f"{fname}: სტანდარტულ თამაშში ლიდერი არ ჰყავს")
        if not any(u["tier"] in {"I", "II"} and "leader" not in u["tags"] for u in fu):
            errors.append(f"{fname}: ქვეითი ან ელიტა (I–II) არ ჰყავს")
        if not any(u["tier"] in {"II", "III"} and "leader" not in u["tags"] for u in fu):
            errors.append(f"{fname}: ელიტა ან ჯავშნიანი (II–III) არ ჰყავს")
        if not any(u["tier"] in {"IV", "IV+"} for u in fu):
            errors.append(f"{fname}: გროტესკი (IV) არ ჰყავს")
        if not any(u["tier"] == "V" for u in fu):
            errors.append(f"{fname}: გოლიათი (V) არ ჰყავს")
        # რეგულარული ჯარი: აირწინაღიანი რიგითები და სანგრის მოჩხუბრები (thugs)
        if not any(u["tier"] == "I" and {"line", "gas_mask"} <= set(u["tags"]) for u in fu):
            errors.append(f"{fname}: აირწინაღიანი რიგითები (I, მწკრივი + აირწინაღი) არ ჰყავს")
        if not any(u["tier"] == "I" and "brawler" in u["tags"] for u in fu):
            errors.append(f"{fname}: სანგრის მოჩხუბრები (I, სანგრის ჩხუბი) არ ჰყავს")
        # დონე/ფასი: დაბალი დონის საბრძოლო იუნიტი არ უნდა იყოს ძვირი შემდეგი დონის ყველაზე იაფზე ორჯერ მეტად
        order = ["I", "II", "III", "IV", "IV+"]
        for a, b in zip(order, order[1:]):
            ca = [costs.get(u["id"], 0) for u in fu if u["tier"] == a]
            cb = [costs.get(u["id"], 0) for u in fu if u["tier"] == b]
            if ca and cb and max(ca) > 2 * min(cb):
                warnings.append(f"{fname}: {a} დონის უძვირესი ({max(ca)}) {b} დონის უიაფესზე ({min(cb)}) ორჯერ ძვირია")

    # ომის კამპანია: ყველა ფრაქციას — შესავალი, მსხვერპლი (გამოგონილი გმირი ≤ 1914), 5+ სცენარი, დასასრული
    for fid, fname in list(factions.items()) + list(allies.items()):
        cp = ROOT / "data" / "campaigns" / f"{fid}.json"
        if not cp.exists():
            errors.append(f"{fname}: ომის კამპანია არ აქვს (data/campaigns/{fid}.json)")
            continue
        c = json.loads(cp.read_text(encoding="utf-8"))
        for k in ("title", "enemy", "hero", "intro", "ending"):
            if not c.get(k):
                errors.append(f"{fname}: კამპანიას '{k}' აკლია")
        sac = c.get("sacrifice") or {}
        if not all(sac.get(k) for k in ("name", "year", "title", "text")) or not 1800 <= int(sac.get("year") or 0) <= 1914:
            errors.append(f"{fname}: კამპანიას მსხვერპლი (სახელი, წელი ≤ 1914, ამბავი) აკლია")
        scen = c.get("scenarios") or []
        if len(scen) < 5:
            errors.append(f"{fname}: კამპანიას 5 სცენარი სჭირდება ({len(scen)})")
        for i, sc in enumerate(scen, 1):
            for k in ("name", "year", "story", "objective", "special", "reward"):
                if not sc.get(k):
                    errors.append(f"{fname}: სცენარ {i}-ს '{k}' აკლია")

    # ძალების ზუსტი წესები: ყოველი ჩანაწერი არსებულ იუნიტს ეკუთვნის
    ab = json.loads((ROOT / "data" / "abilities.json").read_text(encoding="utf-8"))
    used = {t for u in units for t in u["tags"]} | {t for u in units for w in u["weapons"] for t in w["tags"]}
    for t in sorted(used - set(ab.get("tags", {}))):
        errors.append(f"abilities.json: ნიშანს '{t}' ზუსტი წესი (tags) არ აქვს")
    for uid, rules in ab["units"].items():
        if uid not in by_id:
            errors.append(f"abilities.json: უცნობი იუნიტი {uid}")
        if not rules or any(len(r) != 2 or not r[0] or not r[1] for r in rules):
            errors.append(f"abilities.json: {uid} — ჩანაწერი [სახელი, წესი] უნდა იყოს")

    # ნეიტრალური ზოლი: ზონები, ცხრილები (d10 — 1-დან 10-მდე), ურჩხულები, აღჭურვილობა
    nml = json.loads((ROOT / "data" / "no_mans_land.json").read_text(encoding="utf-8"))
    beast_ids = {b["id"] for b in nml["beasts"]}
    gear_ids = {it["id"] for it in equipment["items"]}
    for z in nml["zones"]:
        if z["monster"] not in beast_ids:
            errors.append(f"ნეიტრალური ზოლი {z['id']}: უცნობი ურჩხული {z['monster']}")
        if z["find"] and z["find"]["effect"].get("gear") and z["find"]["effect"]["gear"] not in gear_ids:
            errors.append(f"ნეიტრალური ზოლი {z['id']}: უცნობი აღჭურვილობა {z['find']['effect']['gear']}")
    for tbl in ("search", "night"):
        if sorted(r["roll"] for r in nml[tbl]) != list(range(1, 11)):
            errors.append(f"ნეიტრალური ზოლი: ცხრილი {tbl} 1–10 არ ფარავს")
    for r in nml["search"]:
        if r["effect"].get("gear") and r["effect"]["gear"] not in gear_ids:
            errors.append(f"ნეიტრალური ზოლი: უცნობი აღჭურვილობა {r['effect']['gear']}")
    raid = sorted(nml["raid"], key=lambda r: r["min"])
    if any(a["max"] + 1 != b["min"] for a, b in zip(raid, raid[1:])):
        errors.append("ნეიტრალური ზოლი: დაზვერვის ცხრილს ხვრელი აქვს")

    for aid in allies:
        if not any(u["faction"] == aid for u in units):
            errors.append(f"მოკავშირე {aid}: იუნიტები არ აქვს")
        if aid not in ally_notes:
            warnings.append(f"მოკავშირე {aid}: ბილდერში ALLY_NOTE არ აქვს")

    sides = {"all", "light", "dark", *factions}
    for it in equipment["items"]:
        for s in it["sides"]:
            if s not in sides:
                errors.append(f"აღჭურვილობა {it['id']}: უცნობი მხარე {s}")
        for r in it.get("requires_units", []):
            if r not in by_id:
                errors.append(f"აღჭურვილობა {it['id']}: უცნობი იუნიტი {r}")
        if it["category"] not in equipment["categories"]:
            errors.append(f"აღჭურვილობა {it['id']}: უცნობი კატეგორია")

    # ინგლისური სახელები (KA/EN)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from build_names_en import missing as en_missing
    for kind, key in en_missing():
        errors.append(f"names_en.json: აკლია ინგლისური სახელი — {kind} {key}")

    for w in warnings:
        print("⚠️ ", w)
    for e in errors:
        print("❌", e)
    print(f"იუნიტები: {len(units)} · ფრაქციები: {len(factions)} · მოკავშირეები: {len(allies)} · შეცდომები: {len(errors)} · გაფრთხილებები: {len(warnings)}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
