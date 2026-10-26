"""ინგლისური სახელების ფენა: data/names_en.json.

წყარო — data/names_en.json თავად (ხელით სამართავი). ეს სკრიპტი ამოწმებს სისრულეს:
ყველა ფრაქციას, იუნიტს, იარაღს, ნიშანს, როლს და დონეს უნდა ჰქონდეს ინგლისური სახელი.
გაშვება: python3 tools/build_names_en.py
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def missing():
    d = json.load(open(os.path.join(ROOT, "data/units.json")))
    roles = json.load(open(os.path.join(ROOT, "data/roles.json")))["roles"]
    en = json.load(open(os.path.join(ROOT, "data/names_en.json")))
    out = []
    for f in list(d["factions"]) + list(d["allies"]):
        if f not in en["factions"]:
            out.append(("faction", f))
    for u in d["units"]:
        if u["id"] not in en["units"]:
            out.append(("unit", u["id"]))
        if u["tier"] not in en["tiers"]:
            out.append(("tier", u["tier"]))
        for t in u["tags"]:
            if t not in en["tags"]:
                out.append(("tag", t))
        for w in u["weapons"]:
            if w["name"] not in en["weapons"]:
                out.append(("weapon", w["name"]))
            for t in w["tags"]:
                if t not in en["wtags"]:
                    out.append(("wtag", t))
    for r in roles:
        if r["id"] not in en["roles"]:
            out.append(("role", r["id"]))
    return sorted(set(out))


if __name__ == "__main__":
    m = missing()
    for kind, key in m:
        print(f"აკლია ინგლისური სახელი: {kind} {key}")
    en = json.load(open(os.path.join(ROOT, "data/names_en.json")))
    print(f"data/names_en.json: {len(en['factions'])} ფრაქცია · {len(en['units'])} იუნიტი · "
          f"{len(en['weapons'])} იარაღი · {len(en['tags'])}+{len(en['wtags'])} ნიშანი · აკლია: {len(m)}")
    sys.exit(1 if m else 0)
