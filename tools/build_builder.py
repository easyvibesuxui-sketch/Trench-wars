#!/usr/bin/env python3
"""ბილდერის მონაცემების აწყობა: data/units.json + data/costs.json + data/campaigns/*.json + data/no_mans_land.json → builder/data.js

გაშვება (ბალანსერის შემდეგ):  python3 tools/build_builder.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    data = json.loads((ROOT / "data" / "units.json").read_text(encoding="utf-8"))
    costs = json.loads((ROOT / "data" / "costs.json").read_text(encoding="utf-8"))
    missing = [u["id"] for u in data["units"] if u["id"] not in costs]
    if missing:
        raise SystemExit(f"ფასი არ აქვს: {', '.join(missing)} — ჯერ გაუშვი tools/balancer.py")
    abilities = json.loads((ROOT / "data" / "abilities.json").read_text(encoding="utf-8"))["units"]
    units = []
    for u in data["units"]:
        units.append({k: u[k] for k in ("id", "faction", "name", "tier", "size", "move", "shoot", "melee",
                                        "armor", "wounds", "nerve", "weapons", "tags", "role")} | {"cost": costs[u["id"]], "allied": bool(u.get("allied"))}
                     | ({"abilities": abilities[u["id"]]} if u["id"] in abilities else {}))
    equipment = json.loads((ROOT / "data" / "equipment.json").read_text(encoding="utf-8"))
    equipment.pop("_comment", None)
    campaigns = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "data" / "campaigns").glob("*.json"))}
    nml = json.loads((ROOT / "data" / "no_mans_land.json").read_text(encoding="utf-8"))
    nml.pop("_comment", None)
    out = {"factions": data["factions"], "allies": data.get("allies", {}), "units": units, "equipment": equipment, "campaigns": campaigns,
           "nml": nml, "roles": json.loads((ROOT / "data" / "roles.json").read_text(encoding="utf-8"))["roles"]}
    js = "// ავტომატურად გენერირებული: tools/build_builder.py — ხელით ნუ შეცვლი\n"
    js += "window.TW_DATA = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n"
    target = ROOT / "builder" / "data.js"
    target.parent.mkdir(exist_ok=True)
    target.write_text(js, encoding="utf-8")
    print(f"{target.relative_to(ROOT)}: {len(units)} იუნიტი")


if __name__ == "__main__":
    main()
