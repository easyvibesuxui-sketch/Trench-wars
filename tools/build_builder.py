#!/usr/bin/env python3
"""ბილდერის მონაცემების აწყობა: data/units.json + data/costs.json → builder/data.js

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
    units = []
    for u in data["units"]:
        units.append({k: u[k] for k in ("id", "faction", "name", "tier", "size", "move", "shoot", "melee",
                                        "armor", "wounds", "nerve", "weapons", "tags")} | {"cost": costs[u["id"]]})
    out = {"factions": data["factions"], "units": units}
    js = "// ავტომატურად გენერირებული: tools/build_builder.py — ხელით ნუ შეცვლი\n"
    js += "window.TW_DATA = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n"
    target = ROOT / "builder" / "data.js"
    target.parent.mkdir(exist_ok=True)
    target.write_text(js, encoding="utf-8")
    print(f"{target.relative_to(ROOT)}: {len(units)} იუნიტი")


if __name__ == "__main__":
    main()
