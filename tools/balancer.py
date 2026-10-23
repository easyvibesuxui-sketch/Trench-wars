#!/usr/bin/env python3
"""ბალანსერი (v0).

კითხულობს data/units.json-ს და:
1. ფორმულით ითვლის თითოეული იუნიტის ფასს მარჩილში (შეტევა × გამძლეობა + ძალების ფასი);
2. Monte Carlo-თი ათამაშებს თანაბარი ფასის რაზმებს ერთმანეთის წინააღმდეგ;
3. წერს ანგარიშს docs/balance-report.md-ში და ფასებს data/costs.json-ში და აჩვენებს ზედმეტად ძლიერ/სუსტ იუნიტებს.

გაშვება:  python3 tools/balancer.py [--sims 400] [--seed 1]
"""
import argparse
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "units.json"
REPORT = ROOT / "docs" / "balance-report.md"
COSTS = ROOT / "data" / "costs.json"  # ფასები ბილდერისთვის

BASE_UNIT = "lashkari"   # ამ იუნიტის ფასი = BASE_COST
BASE_COST = 20           # მარჩილი
SIM_BUDGET = 400         # თანაბარი რაზმის ბიუჯეტი სიმულაციაში
SIM_TIERS = {"I", "II", "III", "IV", "IV+"}
# იუნიტები, რომელთა მთავარი ღირებულება სპეციალურ ძალებშია — სიმულაცია მათ ვერ აფასებს
ABILITY_TAGS = {"leader", "healer", "alchemist", "ritual", "witch", "discord", "stitcher", "supply", "repair", "orders", "song", "weakness"}

# საცნობარო სამიზნეები (წონით): armor, wounds, size, tags
REF_TARGETS = [
    (0.35, dict(armor=1, wounds=1, size=1, tags=())),
    (0.25, dict(armor=3, wounds=2, size=1, tags=())),
    (0.20, dict(armor=4, wounds=3, size=1, tags=("steam",))),
    (0.15, dict(armor=5, wounds=9, size=3, tags=("regen",))),
    (0.05, dict(armor=6, wounds=22, size=4, tags=())),
]
# საცნობარო თავდამსხმელები: skill, power, damage, tags
REF_ATTACKERS = [
    dict(skill=5, power=2, damage=1, tags=()),            # შაშხანა
    dict(skill=6, power=2, damage=1, tags=()),            # ხმალი
    dict(skill=5, power=4, damage=2, tags=()),            # მძიმე იარაღი
    dict(skill=5, power=3, damage=2, tags=("anti_giant",)),  # გოლიათზე მონადირე
    dict(skill=5, power=3, damage=1, tags=("fire",)),     # ცეცხლი
]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def hit_p(skill, target_size=1):
    if skill <= 0:
        return 0.0
    bonus = 1 if target_size >= 3 else 0  # დიდ სამიზნეს ადვილად ხვდები
    return clamp((skill + bonus) / 10, 0.05, 0.95)


def wound_p(power, armor, wtags, target_size):
    tn = 5 + armor - power
    if "anti_giant" in wtags and target_size >= 3:
        tn -= 2
    tn = clamp(tn, 2, 10)
    return (11 - tn) / 10


def weapon_vs(w, skill, target):
    """საშუალო ზიანი ერთ აქტივაციაზე ერთი იარაღით."""
    if w["attacks"] <= 0 or w["damage"] <= 0:
        return 0.0
    p = hit_p(skill, target["size"]) * wound_p(w["power"], target["armor"], w["tags"], target["size"])
    dmg = w["attacks"] * p * min(w["damage"], target["wounds"])
    tags, ttags = w["tags"], target["tags"]
    if "blast" in tags and target["size"] == 1:
        dmg *= 1.5
    if "fire" in tags:
        dmg *= 1.6 if ("regen" in ttags or "fire_weak" in ttags) else 1.2
    if "lightning" in tags:
        dmg *= 1.5 if ("lightning_weak" in ttags or "regen" in ttags) else (1.25 if "steam" in ttags else 1.0)
    if "reload" in tags:
        dmg *= 0.6
    if "once" in tags:
        dmg *= 0.35
    if "charge" in tags:
        dmg *= 1.15
    return dmg


def offense(u):
    ranged = melee = 0.0
    for w in u["weapons"]:
        skill = u["shoot"] if w["mode"] == "ranged" else u["melee"]
        val = sum(wt * weapon_vs(w, skill, t) for wt, t in REF_TARGETS)
        if w["mode"] == "ranged":
            val *= 0.6 + 0.4 * min(w["range"], 36) / 36
            ranged = max(ranged, val)
        else:
            reach = 0.55 + 0.45 * min(u["move"], 10) / 10
            if "fly" in u["tags"]:
                reach = 1.0
            melee = max(melee, val * reach)
    return max(ranged, melee) + 0.35 * min(ranged, melee)


def durability(u):
    taken = []
    for a in REF_ATTACKERS:
        p = hit_p(a["skill"], u["size"]) * wound_p(a["power"], u["armor"], a["tags"], u["size"])
        d = p * a["damage"]
        if "fire" in a["tags"] and ("regen" in u["tags"] or "fire_weak" in u["tags"]):
            d *= 1.6
        taken.append(d)
    avg = sum(taken) / len(taken)
    ehp = u["wounds"] / max(avg, 0.02)
    if "regen" in u["tags"]:
        ehp *= 1.25
    if "shield" in u["tags"]:
        ehp *= 1.1
    ehp *= 0.85 + 0.3 * u["nerve"] / 10
    return ehp


def raw_value(u):
    mob = 1 + (u["move"] - 6) * 0.03 + (0.1 if "fly" in u["tags"] else 0)
    return math.sqrt(offense(u) * durability(u)) * mob


def compute_costs(units):
    base = next(u for u in units if u["id"] == BASE_UNIT)
    k = (BASE_COST - base["ability_points"]) / raw_value(base)
    for u in units:
        u["_offense"] = offense(u)
        u["_ehp"] = durability(u)
        u["_cost"] = max(5, round(k * raw_value(u) + u["ability_points"]))
    return k


# ---------------- Monte Carlo ----------------

class Model:
    __slots__ = ("u", "w", "used_once", "reload", "regen_block", "charged", "pinned")

    def __init__(self, u):
        self.u = u
        self.w = u["wounds"]
        self.used_once = set()
        self.reload = False
        self.regen_block = False
        self.charged = False
        self.pinned = False


def build_army(u, budget, rng):
    # სტოქასტური დამრგვალება: 2.6 მოდელი = 60% შემთხვევაში 3, 40%-ში 2 (ძვირი იუნიტების ნახტომებს არბილებს)
    x = budget / u["_cost"]
    n = int(x) + (1 if rng.random() < x - int(x) else 0)
    return [Model(u) for _ in range(max(1, n))]


def best_weapon(m, mode, gap):
    best, best_val = None, -1
    for w in m.u["weapons"]:
        if w["mode"] != mode or w["attacks"] <= 0 or w["damage"] <= 0:
            continue
        if mode == "ranged" and w["range"] < gap:
            continue
        if "once" in w["tags"] and w["name"] in m.used_once:
            continue
        if "reload" in w["tags"] and m.reload:
            continue
        val = w["attacks"] * w["power"] * w["damage"]
        if val > best_val:
            best, best_val = w, val
    return best


def attack(m, w, enemies, rng, cover=0):
    skill = (m.u["shoot"] - cover) if w["mode"] == "ranged" else m.u["melee"]
    power = w["power"] + (1 if ("charge" in w["tags"] and not m.charged) else 0)
    if w["mode"] == "melee":
        m.charged = True
    if "once" in w["tags"]:
        m.used_once.add(w["name"])
    if "reload" in w["tags"]:
        m.reload = True
    for _ in range(w["attacks"]):
        alive = [e for e in enemies if e.w > 0]
        if not alive:
            return
        t = rng.choice(alive)
        targets = [t]
        if "blast" in w["tags"] and t.u["size"] == 1 and len(alive) > 1 and rng.random() < 0.5:
            targets.append(rng.choice(alive))
        for tt in targets:
            if rng.random() >= hit_p(skill, tt.u["size"]):
                continue
            if "pin" in w["tags"]:
                tt.pinned = True  # ბადე/ჯაჭვი: მოხვედრაც საკმარისია — შემდეგ აქტივაციაზე ვერ მოძრაობს
            if rng.random() < wound_p(power, tt.u["armor"], w["tags"], tt.u["size"]):
                tt.w -= w["damage"]
                if "fire" in w["tags"] or "lightning" in w["tags"]:
                    tt.regen_block = True
                if "fire" in w["tags"] and tt.w > 0 and rng.random() < 0.5:
                    tt.w -= 1  # წვა


def activate(m, enemies, state, side, rng):
    m.reload = False if m.reload and rng.random() < 0.5 else m.reload
    gap = state["gap"]
    if gap <= 1:
        w = best_weapon(m, "melee", 0)
        if w:
            attack(m, w, enemies, rng)
        return
    ranged = best_weapon(m, "ranged", gap)
    prefers_melee = m.u["_melee_pref"]
    if ranged and not prefers_melee:
        # სანგრების ომი: შორ მანძილზე სამიზნე საფარშია (-1 სროლაზე)
        attack(m, ranged, enemies, rng, cover=1 if gap > 6 else 0)
        return
    # მიახლოება: რაზმი ერთად მოძრაობს — მანძილი რაუნდში ერთხელ მცირდება (უსწრაფესი მოდელის სვლით)
    if m.pinned:
        m.pinned = False
        return
    if not state["moved"][side]:
        state["moved"][side] = True
        state["gap"] = max(0, gap - m.u["move"])
    if state["gap"] <= 1 and best_weapon(m, "melee", 0):
        attack(m, best_weapon(m, "melee", 0), enemies, rng)


def morale(army, start_n, rng):
    alive = [m for m in army if m.w > 0]
    if len(alive) * 2 < start_n and not getattr(army, "_tested", False):
        for m in alive:
            if rng.randint(1, 10) > m.u["nerve"]:
                m.w = 0
        return True
    return False


def battle(ua, ub, budget, rng, max_rounds=8):
    A, B = build_army(ua, budget, rng), build_army(ub, budget, rng)
    nA, nB = len(A), len(B)
    state = {"gap": 24, "moved": {"A": False, "B": False}}
    tested = {"A": False, "B": False}
    for _ in range(max_rounds):
        for army in (A, B):
            for m in army:
                if m.w > 0 and "regen" in m.u["tags"] and not m.regen_block and m.w < m.u["wounds"]:
                    m.w += 1
                m.regen_block = False
        state["moved"] = {"A": False, "B": False}
        order = [("A", m) for m in A] + [("B", m) for m in B]
        rng.shuffle(order)
        for side, m in order:
            if m.w <= 0:
                continue
            enemies = B if side == "A" else A
            if not any(e.w > 0 for e in enemies):
                break
            activate(m, enemies, state, side, rng)
        for key, army, n in (("A", A, nA), ("B", B, nB)):
            if not tested[key] and sum(1 for m in army if m.w > 0) * 2 < n:
                tested[key] = True
                for m in army:
                    if m.w > 0 and rng.randint(1, 10) > m.u["nerve"]:
                        m.w = 0
        if not any(m.w > 0 for m in A) or not any(m.w > 0 for m in B):
            break
    # შედეგი: დარჩენილი ძალის წილი საწყისთან შედარებით
    va = sum(m.w / m.u["wounds"] for m in A if m.w > 0) / nA
    vb = sum(m.w / m.u["wounds"] for m in B if m.w > 0) / nB
    if va > vb:
        return 1.0
    if vb > va:
        return 0.0
    return 0.5


def simulate(units, sims, rng):
    pool = [u for u in units if u["tier"] in SIM_TIERS and not (set(u["tags"]) & ABILITY_TAGS)]
    for u in pool:
        r = max((offense({**u, "weapons": [w for w in u["weapons"] if w["mode"] == "ranged"]}) if any(w["mode"] == "ranged" for w in u["weapons"]) else 0), 0)
        mm = offense({**u, "weapons": [w for w in u["weapons"] if w["mode"] == "melee"]}) if any(w["mode"] == "melee" for w in u["weapons"]) else 0
        u["_melee_pref"] = mm > r * 1.2
    results = {u["id"]: [] for u in pool}
    for i, a in enumerate(pool):
        for b in pool[i + 1:]:
            if a["faction"] == b["faction"]:
                continue
            score = sum(battle(a, b, SIM_BUDGET, rng) for _ in range(sims)) / sims
            results[a["id"]].append(score)
            results[b["id"]].append(1 - score)
    return {k: (sum(v) / len(v) if v else None) for k, v in results.items()}


def calibrate(units, sims, rng, iterations):
    """ფასების ავტომატური კორექცია: ძლიერი იუნიტი ძვირდება, სუსტი — იაფდება."""
    history = []
    for _ in range(iterations):
        win = simulate(units, sims, rng)
        history.append(win)
        for u in units:
            wr = win.get(u["id"])
            if wr is None:
                continue
            factor = clamp((max(wr, 0.02) / 0.5) ** 0.35, 0.85, 1.15)
            u["_exact"] = u.get("_exact", u["_cost"]) * factor
        # ნორმალიზაცია: საბაზისო იუნიტი ყოველთვის BASE_COST-ია
        base = next(u for u in units if u["id"] == BASE_UNIT)
        norm = BASE_COST / base.get("_exact", base["_cost"])
        for u in units:
            if "_exact" in u:
                u["_exact"] *= norm
                u["_cost"] = max(5, round(u["_exact"]))
    return simulate(units, sims, rng)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--calibrate", type=int, default=8, help="ფასების კორექციის იტერაციები (0 = გამორთული)")
    args = ap.parse_args()
    data = json.loads(DATA.read_text(encoding="utf-8"))
    units = data["units"]
    factions = data["factions"]
    compute_costs(units)
    for u in units:
        u["_formula_cost"] = u["_cost"]
    rng = random.Random(args.seed)
    raw_win = simulate(units, args.sims, rng)
    win = calibrate(units, args.sims, rng, args.calibrate) if args.calibrate else raw_win

    lines = [
        "# ბალანსის ანგარიში (ავტომატური)",
        "",
        f"> გენერირებულია `tools/balancer.py`-ით. სიმულაციები: {args.sims} თითო წყვილზე, რაზმის ბიუჯეტი {SIM_BUDGET} მარჩილი.",
        "> **ფასი** = ფორმულა (შეტევა × გამძლეობა × მობილობა) + სპეციალური ძალების ფასი. საბაზისო: ლაშქარი = 20 მარჩილი.",
        "> **ფორმულის ფასი** — პირველადი შეფასება; **ფასი** — სიმულაციით კორექტირებული (რეკომენდებული). **მოგება % (ფორმულით)** აჩვენებს, რამდენად ცდებოდა ფორმულა.",
        "> **მოგების %** — საშუალო შედეგი სხვა ფრაქციების ყველა საბრძოლო იუნიტის წინააღმდეგ, თანაბარი ფასით. იდეალი ≈ 50%.",
        "> ⚠️ = 60%-ზე მეტი (ზედმეტად ძლიერი ფასთან შედარებით) ან 40%-ზე ნაკლები (ზედმეტად სუსტი).",
        "> ლიდერები, მკურნალები, ალქიმიკოსები და რიტუალისტები სიმულაციაში არ შედიან — მათი ღირებულება ძალებშია და **სატესტო თამაში** სჭირდება.",
        "",
    ]
    allies = data.get("allies", {})
    for fid, fname in list(factions.items()) + [(k, v + " (მოკავშირე)") for k, v in allies.items()]:
        lines += [f"## {fname}", "", "| იუნიტი | დონე | ფორმულის ფასი | მოგება % (ფორმულით) | **ფასი** | მოგება % | შენიშვნა |", "|---|---|---|---|---|---|---|"]
        for u in [x for x in units if x["faction"] == fid]:
            wr = win.get(u["id"])
            if wr is None:
                note = "სიმულაციის გარეშე (ძალები / სუპერიუნიტი)"
                wrs = "—"
            else:
                wrs = f"{wr * 100:.0f}%"
                note = "⚠️ ძლიერი" if wr > 0.6 else ("⚠️ სუსტი" if wr < 0.4 else "✓")
            rw = raw_win.get(u["id"])
            rws = f"{rw * 100:.0f}%" if rw is not None else "—"
            lines.append(f"| {u['name']} | {u['tier']} | {u['_formula_cost']} | {rws} | **{u['_cost']}** | {wrs} | {note} |")
        lines.append("")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    COSTS.write_text(json.dumps({u["id"]: u["_cost"] for u in units}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    flagged = [(u["name"], win[u["id"]]) for u in units if win.get(u["id"]) is not None and not 0.4 <= win[u["id"]] <= 0.6]
    print(f"ანგარიში: {REPORT.relative_to(ROOT)}")
    print(f"სიმულირებული იუნიტები: {sum(1 for v in win.values() if v is not None)}; დროშით მონიშნული: {len(flagged)}")
    for name, wr in sorted(flagged, key=lambda x: -x[1]):
        print(f"  {wr * 100:5.1f}%  {name}")


if __name__ == "__main__":
    main()
