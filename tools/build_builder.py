#!/usr/bin/env python3
"""ბილდერის მონაცემების აწყობა: data/units.json + data/costs.json + data/campaigns/*.json + data/no_mans_land.json → builder/data.js

გაშვება (ბალანსერის შემდეგ):  python3 tools/build_builder.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def campaign_en(md, ka):
    """ნათარგმნი კამპანიის markdown (data/text_en/campaigns.json) → იგივე სტრუქტურა, რაც data/campaigns/*.json (build_campaigns.py-ის შაბლონი).
    თუ სტრუქტურა არ ემთხვევა (სცენარების რაოდენობა და ა.შ.), None — აპი ქართულს აჩვენებს."""
    import re
    m = re.search(r"^# (.+?) — .+?\n+> \*\*Enemy:\*\* (.+?) · \*\*Hero:\*\* (.+?) · \*\*Scenarios:\*\* \d+\n+(.+?)\n+"
                  r"## Sacrifice: (.+?) \((\d+)\)\n+\*\*\"(.+?)\"\.\*\* (.+?)\n+## Scenarios\n+(.+?)\n+## Ending\n+(.+?)\s*$", md.strip(), re.S | re.M)
    if not m:
        return None
    sc = re.findall(r"^### \d+\. (.+?) \((\d+)\)\n+(.+?)\n+- \*\*Objective:\*\* (.+?)\n- \*\*Special rule:\*\* (.+?)\n- \*\*Reward:\*\* (.+?)$",
                    m.group(9), re.S | re.M)
    if len(sc) != len(ka["scenarios"]):
        return None
    out = json.loads(json.dumps(ka))
    out.update(title=m.group(1), enemy=m.group(2), hero=m.group(3), intro=m.group(4), ending=m.group(10))
    out["sacrifice"].update(name=m.group(5), title=m.group(7), text=m.group(8))
    for o, (name, _, story, obj, spec, rew) in zip(out["scenarios"], sc):
        o.update(name=name, story=story, objective=obj, special=spec, reward=rew)
    return out


def app_en(campaigns, files):
    """ინგლისური ასლები აპებისთვის: ინტერფეისის ფრაზები, სცენარები, ნეიტრალური ზოლი, აღჭურვილობა, კამპანიები."""
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from i18n_en import en_texts, en_copy
    T = en_texts()
    out = {"ui": json.loads((ROOT / "data" / "ui_en.json").read_text(encoding="utf-8"))}
    for name, obj in files.items():
        out[name] = en_copy(obj, T, f"app:{name}:")
    out["campaigns"] = {fid: c for fid, c in ((fid, campaign_en(T[f"camp:{fid}"], ka)) for fid, ka in campaigns.items() if f"camp:{fid}" in T) if c}
    return out


def rules_en():
    """ინგლისური წესები ბილდერისთვის (data/text_en/rules.json): ნიშნები, როლები, იუნიტების ძალები."""
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from i18n_en import en_texts, split2
    T = en_texts()
    abil = {}
    for k, v in T.items():
        if k.startswith("abil:"):
            uid, i = k[5:].split("#")
            abil.setdefault(uid, {})[int(i)] = list(split2(v))
    return {"tags": {k[4:]: v for k, v in T.items() if k.startswith("tag:")},
            "roles": {k[5:]: v for k, v in T.items() if k.startswith("role:")},
            "abil": {uid: [d[i] for i in sorted(d)] for uid, d in abil.items()}}


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
           "scenarios": json.loads((ROOT / "data" / "scenarios.json").read_text(encoding="utf-8"))["scenarios"],
           "nml": nml, "tag_rules": json.loads((ROOT / "data" / "abilities.json").read_text(encoding="utf-8"))["tags"], "roles": json.loads((ROOT / "data" / "roles.json").read_text(encoding="utf-8"))["roles"],
           "en": {k: v for k, v in json.loads((ROOT / "data" / "names_en.json").read_text(encoding="utf-8")).items() if k != "_comment"} | {"rules": rules_en()}}
    scen = json.loads((ROOT / "data" / "scenarios.json").read_text(encoding="utf-8"))
    scen.pop("_comment", None)
    out["en"] |= app_en(campaigns, {"scenarios": scen, "no_mans_land": nml, "equipment": equipment})
    # ფრაქციების სახელები ინტერფეისის ლექსიკონშიც (თამაშებში ზოგი სახელი კოდშია ჩაწერილი)
    fac_ka = {**data["factions"], **data.get("allies", {})}
    out["en"]["ui"] = {ka: out["en"]["factions"][k] for k, ka in fac_ka.items() if k in out["en"]["factions"]} | out["en"]["ui"]
    js = "// ავტომატურად გენერირებული: tools/build_builder.py — ხელით ნუ შეცვლი\n"
    js += "window.TW_DATA = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n"
    target = ROOT / "builder" / "data.js"
    target.parent.mkdir(exist_ok=True)
    target.write_text(js, encoding="utf-8")
    (ROOT / "digital" / "data.js").write_text(js, encoding="utf-8")  # ციფრული პროტოტიპიც იგივე მონაცემებს კითხულობს
    (ROOT / "defense" / "data.js").write_text(js, encoding="utf-8")  # „ღარის დაცვაც“
    lang_js = (ROOT / "tools" / "ui_lang.js").read_text(encoding="utf-8")  # KA/EN ინტერფეისი სამივე აპისთვის
    for d in ("builder", "digital", "defense"):
        (ROOT / d / "ui-lang.js").write_text(lang_js, encoding="utf-8")
    print(f"{target.relative_to(ROOT)}: {len(units)} იუნიტი")


if __name__ == "__main__":
    main()
