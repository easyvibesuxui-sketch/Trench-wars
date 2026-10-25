#!/usr/bin/env python3
"""ძალების ზუსტი წესები: data/abilities.json → rules/abilities.md

გაშვება:  python3 tools/build_abilities.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADER = "<!-- ავტომატურად გენერირებული: tools/build_abilities.py — შეცვალე data/abilities.json -->\n"


def main():
    data = json.loads((ROOT / "data" / "units.json").read_text(encoding="utf-8"))
    ab = json.loads((ROOT / "data" / "abilities.json").read_text(encoding="utf-8"))
    names = {**data["factions"], **data["allies"]}
    out = [HEADER, "# ძალები — ზუსტი წესები", "",
           "> ნიშნების (ლიდერი, ფარი, ზალპი, შხამი…) წესები — `core-rules.md`, „7ა“; აქ — იუნიტის საკუთარი ძალები, რომლებიც ნიშნით არ არის",
           "> აღწერილი. ფასში ძალები `ability_points`-ით შედის (`../data/units.json`). მოკავშირეების ძალები — `../units/allies.md`.", "",
           "## საერთო ტერმინები", ""]
    out += [f"- **{k}:** {v}" for k, v in ab["common"].items()]
    for fid, fname in names.items():
        fu = [u for u in data["units"] if u["faction"] == fid and u["id"] in ab["units"]]
        if not fu:
            continue
        out += ["", f"## {fname}", ""]
        for u in fu:
            out.append(f"**{u['name']}** ({u['tier']})")
            out += [f"- **{n}:** {r}" for n, r in ab["units"][u["id"]]]
            out.append("")
    (ROOT / "rules" / "abilities.md").write_text("\n".join(out), encoding="utf-8")
    print(f"rules/abilities.md: {len(ab['units'])} იუნიტი")


if __name__ == "__main__":
    main()
