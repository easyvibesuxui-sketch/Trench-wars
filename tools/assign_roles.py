#!/usr/bin/env python3
"""იუნიტებს როლს ანიჭებს (data/roles.json): მხოლოდ იმათ, ვისაც role ჯერ არ აქვს, ან ყველას — --all.

გაშვება:  python3 tools/assign_roles.py [--all]
წესი თანმიმდევრობითაა — პირველი დამთხვევა იგებს. ხელით გადაწყვეტილი შემთხვევები — OVERRIDES.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUPPORT = {"healer", "alchemist", "song", "ritual", "supply", "repair", "stitcher", "orders", "interpreter", "messenger"}
DISRUPT = {"witch", "discord", "assassin", "planted", "weakness", "convert"}
OVERRIDES = {
    # ხელით: ფუნქცია ნიშნებზე უფრო ზუსტია
    "medea_sisters": "support", "ekimbashi": "support", "dali_hunters": "hunter", "chain_shooters": "hunter",
    "glasya_killers": "disruptor", "andras_whisperers": "disruptor", "halphas_fortifiers": "engineer",
    "malphas_wreckers": "hunter", "lightning_gunners": "hunter", "yoke_slaves": "line", "kaji_smith": "support",
    "skuba_trappers": "hunter", "grenadiers": "assault", "janissaries": "marksman", "mehter_drummers": "support",
    "standard_fortress": "armor", "lightning_castle": "armor", "chain_wagon": "armor", "steam_ibex": "artillery",
}


def is_suppress(w):
    return w["mode"] == "ranged" and "suppress" in w["tags"]


def role_of(u):
    t, tier = set(u["tags"]), u["tier"]
    ranged = [w for w in u["weapons"] if w["mode"] == "ranged" and w["attacks"] > 0]
    if u["id"] in OVERRIDES:
        return OVERRIDES[u["id"]]
    if tier == "V":
        return "giant"
    if "leader" in t:
        return "command"
    if "monster" in t:
        return "monster"
    if "fly" in t:
        return "flyer"
    if any(is_suppress(w) for w in u["weapons"]):
        return "armor" if "vehicle" in t else "heavy_weapons"
    if "vehicle" in t or "fortress" in t:
        if any("indirect" in w["tags"] for w in ranged):
            return "artillery"
        return "armor"
    if "artillery" in t or any("indirect" in w["tags"] or ("blast" in w["tags"] and w["range"] >= 24) for w in ranged):
        return "artillery"
    if t & {"giant_hunter", "anti_air", "monster_hunter"}:
        return "hunter"
    if t & DISRUPT:
        return "disruptor"
    if t & SUPPORT:
        return "support"
    if t & {"engineer", "digger"}:
        return "engineer"
    if "cavalry" in t:
        return "cavalry"
    if any(w["range"] >= 30 for w in ranged) and u["shoot"] >= 6:
        return "sniper"
    if t & {"scout", "infiltrate"} and tier in ("I", "II"):
        return "scout"
    if "brawler" in t or (tier in ("I", "II") and u["melee"] >= u["shoot"] + 2 and "line" not in t):
        return "assault"
    if tier in ("III", "IV", "IV+") or t & {"shield_wall"}:
        return "heavy_infantry"
    if "line" in t:
        return "line"
    if tier == "hero":
        return "assault" if u["melee"] > u["shoot"] else "marksman"
    if ranged and u["shoot"] >= 6:
        return "marksman"
    if ranged and u["shoot"] >= u["melee"]:
        return "line" if tier == "I" else "marksman"
    return "assault"


def main():
    p = ROOT / "data" / "units.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    roles = {r["id"] for r in json.loads((ROOT / "data" / "roles.json").read_text(encoding="utf-8"))["roles"]}
    redo = "--all" in sys.argv
    n = 0
    for u in data["units"]:
        if redo or u.get("role") not in roles:
            u["role"] = role_of(u)
            n += 1
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"როლი მიენიჭა: {n} იუნიტს")


if __name__ == "__main__":
    main()
