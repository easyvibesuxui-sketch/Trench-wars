#!/usr/bin/env python3
"""იუნიტების როლები: data/roles.json + data/units.json → rules/roles.md (როლები, ვინ ვის ჯობნის, ფრაქციების დაფარვა)

გაშვება:  python3 tools/build_roles.py   (ახალ იუნიტებს როლი — tools/assign_roles.py)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADER = "<!-- ავტომატურად გენერირებული: tools/build_roles.py — შეცვალე data/roles.json -->\n"


def main():
    data = json.loads((ROOT / "data" / "units.json").read_text(encoding="utf-8"))
    roles = json.loads((ROOT / "data" / "roles.json").read_text(encoding="utf-8"))["roles"]
    rn = {r["id"]: f"{r['icon']} {r['name']}" for r in roles}
    names = {**data["factions"], **data["allies"]}
    out = [HEADER, "# იუნიტების როლები", "",
           "> 18 როლი — ყოველ იუნიტს ერთი (`role`, `../data/units.json`). როლი ამბობს, **რას აკეთებს** იუნიტი ბრძოლაში, ვის **ჯობნის** და ვინ",
           "> **ჯობნის მას** — ქვა-მაკრატელი-ქაღალდი, როგორც სტრატეგიებში. დათრგუნვის, მფრინავის და საზენიტოს წესები — `core-rules.md`, „7ა+“.", "",
           "| როლი | რას აკეთებს | ჯობნის | მას ჯობნის |", "|---|---|---|---|"]
    for r in roles:
        out.append(f"| **{rn[r['id']]}** | {r['does']} | {', '.join(rn[x] for x in r['counters']) or '—'} | "
                   f"{', '.join(rn[x] for x in r['countered_by']) or '—'} |")
    out += ["", "## ძირითადი ფრაქციები — როლების დაფარვა", "",
            "რიცხვი — რამდენი იუნიტი აქვს ფრაქციას ამ როლში (გმირების და გოლიათის ჩათვლით). ცარიელი უჯრა — ფრაქციას ეს როლი არ აქვს:",
            "ეს მისი სისუსტეა, რომელსაც მოკავშირეებით, ალიანსით ან აღჭურვილობით ავსებს (მაგ. **მსუბუქი ტყვიამფრქვევი** — ნებისმიერ ფრაქციას).", "",
            "| როლი | " + " | ".join(names[f] for f in data["factions"]) + " |", "|---|" + "---|" * len(data["factions"])]
    for r in roles:
        row = []
        for f in data["factions"]:
            n = sum(1 for u in data["units"] if u["faction"] == f and u["role"] == r["id"])
            row.append(str(n) if n else "")
        out.append(f"| {rn[r['id']]} | " + " | ".join(row) + " |")
    out += ["", "## ფრაქციების იუნიტები როლებით", ""]
    for f, fname in names.items():
        fu = [u for u in data["units"] if u["faction"] == f]
        by = {}
        for u in fu:
            by.setdefault(u["role"], []).append(u["name"])
        parts = [f"{rn[r['id']]}: {', '.join(by[r['id']])}" for r in roles if r["id"] in by]
        out.append(f"- **{fname}** — " + " · ".join(parts))
    (ROOT / "rules" / "roles.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"rules/roles.md: {len(roles)} როლი, {len(data['units'])} იუნიტი")


if __name__ == "__main__":
    main()
