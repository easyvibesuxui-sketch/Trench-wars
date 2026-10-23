#!/usr/bin/env python3
"""ბალანსერი (v1).

კითხულობს data/units.json-ს და:
1. ფორმულით ითვლის თითოეული იუნიტის ფასს მარჩილში (შეტევა × გამძლეობა + ძალების ფასი);
2. Monte Carlo-თი ათამაშებს თანაბარი ფასის რაზმებს ერთმანეთის წინააღმდეგ;
3. წერს ანგარიშს docs/balance-report.md-ში და ფასებს data/costs.json-ში და აჩვენებს ზედმეტად ძლიერ/სუსტ იუნიტებს.

გაშვება:  python3 tools/balancer.py [--sims 160] [--calibrate 16] [--faction-sims 300] [--seed 1]

v1: საწყისი მანძილი შემთხვევითია (12/24/36"), ერთნაირი პროფილები ერთად ითვლება, და ბოლოს ფრაქციები ერთმანეთს
შერეული რაზმებით ებრძვიან (ფრაქციის დონის ბალანსი).
"""
import argparse
import json
import math
import multiprocessing
import os
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

GAPS = (12, 24, 36)       # საწყისი მანძილის ვარიანტები სიმულაციაში
FACTION_BUDGET = 500      # ფრაქციების შერეული რაზმების ბიუჯეტი
PIN_TAGS = {"pin", "entangle", "grab"}          # მოხვედრილს შემდეგ აქტივაციაზე მოძრაობა არ შეუძლია
NO_POISON = {"construct", "automaton", "vehicle", "undead", "fortress"}  # შხამი მათზე არ მოქმედებს

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


def weapon_vs(w, skill, target, steam=False):
    """საშუალო ზიანი ერთ აქტივაციაზე ერთი იარაღით."""
    if w["attacks"] <= 0 or w["damage"] <= 0:
        return 0.0
    tags, ttags = w["tags"], target["tags"]
    power = w["power"] + (1 if steam or "steam" in tags else 0)  # ორთქლის წნევა: 1 ჟეტონი
    armor = max(0, target["armor"] - (1 if "armor_break" in tags else 0))
    attacks = w["attacks"] + (1 if "frenzy" in tags else 0)
    p = hit_p(skill, target["size"]) * wound_p(power, armor, tags, target["size"])
    dmg = attacks * p * min(w["damage"], target["wounds"])
    if "poison" in tags and not (set(ttags) & NO_POISON):
        dmg *= 1.25
    if "sweep" in tags and w["mode"] == "melee":
        dmg *= 1.3
    if "volley" in tags:
        dmg *= 1.3
    if "indirect" in tags:
        dmg *= 1.1
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
        val = sum(wt * weapon_vs(w, skill, t, "steam" in u["tags"]) for wt, t in REF_TARGETS)
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
    if "shield_wall" in u["tags"]:
        ehp *= 1.15
    if "steam" in u["tags"]:
        ehp *= 0.93  # გადატვირთვის რისკი
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
        u["_combat"] = k * raw_value(u)  # საბრძოლო ღირებულება — მხოლოდ ამას ამოწმებს სიმულაცია
        u["_cost"] = max(5, round(u["_combat"] + u["ability_points"]))
    return k


# ---------------- Monte Carlo ----------------

class Model:
    __slots__ = ("u", "w", "used_once", "reload", "regen_block", "charged", "pinned", "steam_used", "army")

    def __init__(self, u):
        self.u = u
        self.w = u["wounds"]
        self.used_once = set()
        self.reload = False
        self.regen_block = False
        self.charged = False
        self.pinned = False
        self.steam_used = False


def build_army(u, budget, rng):
    # სტოქასტური დამრგვალება: 2.6 მოდელი = 60% შემთხვევაში 3, 40%-ში 2 (ძვირი იუნიტების ნახტომებს არბილებს)
    x = budget / max(3.0, u["_combat"])
    n = int(x) + (1 if rng.random() < x - int(x) else 0)
    army = [Model(u) for _ in range(max(1, n))]
    for m in army:
        m.army = army
    return army


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
    if "indirect" in w["tags"]:
        cover = 0
    skill = (m.u["shoot"] - cover) if w["mode"] == "ranged" else m.u["melee"]
    power = w["power"] + (1 if ("charge" in w["tags"] and not m.charged) else 0)
    if "steam" in m.u["tags"] or "steam" in w["tags"]:
        power += 1  # ორთქლის წნევა (1 ჟეტონი); რაუნდის ბოლოს გადატვირთვის რისკი
        m.steam_used = True
    attacks = w["attacks"] + (1 if "frenzy" in w["tags"] else 0)
    if "volley" in w["tags"] and sum(1 for x in m.army if x.w > 0 and x.u is m.u) >= 2:
        attacks += 1  # ზალპი: ორი ან მეტი მსროლელი ერთად
    if w["mode"] == "melee":
        m.charged = True
    if "once" in w["tags"]:
        m.used_once.add(w["name"])
    if "reload" in w["tags"]:
        m.reload = True
    for _ in range(attacks):
        alive = [e for e in enemies if e.w > 0]
        if not alive:
            return
        t = rng.choice(alive)
        targets = [t]
        if "blast" in w["tags"] and t.u["size"] == 1 and len(alive) > 1 and rng.random() < 0.5:
            targets.append(rng.choice(alive))
        if "sweep" in w["tags"] and w["mode"] == "melee" and len(alive) > 1 and rng.random() < 0.5:
            targets.append(rng.choice(alive))
        for tt in targets:
            if rng.random() >= hit_p(skill, tt.u["size"]):
                continue
            if set(w["tags"]) & PIN_TAGS:
                tt.pinned = True  # ბადე/ჯაჭვი: მოხვედრაც საკმარისია — შემდეგ სვლაზე ვერ მოძრაობს
            armor = tt.u["armor"]
            if "armor_break" in w["tags"]:
                armor = max(0, armor - 1)
            if w["mode"] == "ranged" and "shield" in tt.u["tags"]:
                armor += 1  # ფარი სროლისგან იცავს
            if "shield_wall" in tt.u["tags"] and sum(1 for x in tt.army if x.w > 0 and x.u is tt.u) >= 2:
                armor += 1  # ფარის კედელი: ორი ან მეტი ერთად
            if rng.random() < wound_p(power, armor, w["tags"], tt.u["size"]):
                tt.w -= w["damage"]
                if "fire" in w["tags"] or "lightning" in w["tags"] or "festering" in w["tags"]:
                    tt.regen_block = True
                if "poison" in w["tags"] and tt.w > 0 and not (set(tt.u["tags"]) & NO_POISON) and rng.random() < 0.5:
                    tt.w -= 1  # შხამი
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
    if not state["moved"][side]:
        state["moved"][side] = True
        alive = [x for x in m.army if x.w > 0]
        pinned = sum(1 for x in alive if x.pinned)
        for x in alive:
            x.pinned = False
        # რაზმი ერთად მოძრაობს: ბადით/ჯაჭვით მიბმული მოდელები მთელ რაზმს აჩერებენ (წილობრივად)
        state["gap"] = max(0, gap - m.u["move"] * (1 - pinned / max(1, len(alive))))
    if state["gap"] <= 1 and best_weapon(m, "melee", 0):
        attack(m, best_weapon(m, "melee", 0), enemies, rng)


def battle(ua, ub, budget, rng, max_rounds=8):
    return fight(build_army(ua, budget, rng), build_army(ub, budget, rng), rng, max_rounds)


def fight(A, B, rng, max_rounds=8):
    nA, nB = len(A), len(B)
    # საწყისი მანძილი შემთხვევითია: ახლო (12"), საშუალო (24") ან შორი (36") — სხვადასხვა რუკა და განლაგება
    state = {"gap": rng.choice(GAPS), "moved": {"A": False, "B": False}}
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
        for army in (A, B):
            for m in army:
                if m.w > 0 and m.steam_used and rng.randint(1, 10) <= 1:
                    m.w -= 1  # გადატვირთვა: d10 ≤ ჟეტონების რაოდენობა (1)
                m.steam_used = False
        for key, army, n in (("A", A, nA), ("B", B, nB)):
            if not tested[key] and sum(1 for m in army if m.w > 0) * 2 < n:
                tested[key] = True
                for m in army:
                    if m.w > 0 and "fearless" not in m.u["tags"] and rng.randint(1, 10) > m.u["nerve"]:
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
        set_pref(u)
    # იდენტური პროფილები (მაგ. მოკავშირეების რიგითები) ერთხელ ითვლება: ერთნაირი მაჩვენებლების იუნიტს ერთი შედეგი აქვს,
    # და მოწინააღმდეგეთა სიაში ის ერთხელ შედის — 37 ერთნაირი რიგითი სხვების შედეგს არ „გადაწონის“
    groups = {}
    for u in pool:
        groups.setdefault(profile_key(u), []).append(u)
    reps = [g[0] for g in groups.values()]
    facs = [{u["faction"] for u in g} for g in groups.values()]
    results = {i: [] for i in range(len(reps))}
    pairs = [(i, j) for i in range(len(reps)) for j in range(i + 1, len(reps)) if not (len(facs[i]) == 1 and facs[i] == facs[j])]
    # ყოველ წყვილს თავისი seed აქვს — შედეგი პროცესების რაოდენობაზე არ არის დამოკიდებული
    jobs = [(i, j, rng.randrange(2**31)) for i, j in pairs]
    global _POOL, _SIMS
    _POOL, _SIMS = reps, sims
    workers = os.cpu_count() or 1
    if workers > 1:
        with multiprocessing.get_context("fork").Pool(workers) as mp:
            scores = mp.map(_pair_score, jobs, chunksize=64)
    else:
        scores = [_pair_score(job) for job in jobs]
    for (i, j, _), score in zip(jobs, scores):
        results[i].append(score)
        results[j].append(1 - score)
    out = {}
    for i, g in enumerate(groups.values()):
        v = results[i]
        for u in g:
            out[u["id"]] = sum(v) / len(v) if v else None
    return out


def set_pref(u):
    r = offense({**u, "weapons": [w for w in u["weapons"] if w["mode"] == "ranged"]}) if any(w["mode"] == "ranged" for w in u["weapons"]) else 0
    mm = offense({**u, "weapons": [w for w in u["weapons"] if w["mode"] == "melee"]}) if any(w["mode"] == "melee" for w in u["weapons"]) else 0
    u["_melee_pref"] = mm > r * 1.2


def profile_key(u):
    """საბრძოლო პროფილი: ყველაფერი, რასაც სიმულაცია ხედავს (სახელების გარეშე)."""
    ws = sorted((w["mode"], w["range"], w["attacks"], w["power"], w["damage"], tuple(sorted(w["tags"]))) for w in u["weapons"])
    return (u["size"], u["move"], u["shoot"], u["melee"], u["armor"], u["wounds"], u["nerve"],
            tuple(sorted(u["tags"])), tuple(ws), round(u["_combat"], 6))


# ---------------- ფრაქციები ერთმანეთის წინააღმდეგ ----------------

def faction_army(roster, budget, rng):
    """შემთხვევითი, მაგრამ კანონიერი რაზმი: ფასები costs-იდან, IV მაქს. 1, ერთ იუნიტზე მაქს. 4 მოდელი."""
    army, left, counts, big = [], budget, {}, False
    while True:
        opts = [u for u in roster if u["_cost"] <= left and counts.get(u["id"], 0) < 4 and not (big and u["tier"] in ("IV", "IV+"))]
        if not opts:
            break
        u = rng.choice(opts)
        counts[u["id"]] = counts.get(u["id"], 0) + 1
        big = big or u["tier"] in ("IV", "IV+")
        left -= u["_cost"]
        army.append(Model(u))
    for m in army:
        m.army = army
    return army


def _faction_score(job):
    a, b, seed = job
    r = random.Random(seed)
    total = 0.0
    for _ in range(_SIMS):
        A, B = faction_army(_ROSTERS[a], FACTION_BUDGET, r), faction_army(_ROSTERS[b], FACTION_BUDGET, r)
        total += fight(A, B, r) if A and B else 0.5
    return total / _SIMS


_ROSTERS = {}


def faction_matrix(units, fids, sims, rng):
    """ფრაქცია ფრაქციის წინააღმდეგ შერეული რაზმებით.
    ლიდერები და ძალების იუნიტები არ შედიან (მათ სიმულაცია ვერ აფასებს); გროტესკები (IV) შედიან ძალებითაც, რადგან ისინი ძირითადად მებრძოლები არიან."""
    global _ROSTERS, _SIMS
    _ROSTERS = {f: [u for u in units if u["faction"] == f and "leader" not in u["tags"]
                    and (u["tier"] == "IV" or (u["tier"] in {"I", "II", "III"} and not (set(u["tags"]) & ABILITY_TAGS)))] for f in fids}
    for r in _ROSTERS.values():
        for u in r:
            set_pref(u)
    _SIMS = sims
    jobs = [(a, b, rng.randrange(2**31)) for i, a in enumerate(fids) for b in fids[i + 1:]]
    workers = os.cpu_count() or 1
    if workers > 1:
        with multiprocessing.get_context("fork").Pool(workers) as mp:
            scores = mp.map(_faction_score, jobs, chunksize=8)
    else:
        scores = [_faction_score(j) for j in jobs]
    m = {f: {} for f in fids}
    for (a, b, _), sc in zip(jobs, scores):
        m[a][b], m[b][a] = sc, 1 - sc
    return m


_POOL, _SIMS = [], 0


def _pair_score(job):
    i, j, seed = job
    r = random.Random(seed)
    return sum(battle(_POOL[i], _POOL[j], SIM_BUDGET, r) for _ in range(_SIMS)) / _SIMS


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
            u["_combat"] *= factor
            u["_calibrated"] = True
        # ნორმალიზაცია: საბაზისო იუნიტი (საბრძოლო ნაწილი + ძალები) ყოველთვის BASE_COST-ია
        base = next(u for u in units if u["id"] == BASE_UNIT)
        norm = (BASE_COST - base["ability_points"]) / base["_combat"]
        for u in units:
            if u.get("_calibrated"):
                u["_combat"] *= norm
                u["_cost"] = max(5, round(u["_combat"] + u["ability_points"]))
    return simulate(units, sims, rng)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=200)
    ap.add_argument("--faction-sims", type=int, default=300, help="ფრაქციების შერეული რაზმების ბრძოლები თითო წყვილზე (0 = გამორთული)")
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
    allies = data.get("allies", {})
    names = {**factions, **allies}
    fids = list(factions) + list(allies)
    fm = faction_matrix(units, fids, args.faction_sims, rng) if args.faction_sims else None

    lines = [
        "# ბალანსის ანგარიში (ავტომატური)",
        "",
        f"> გენერირებულია `tools/balancer.py`-ით. სიმულაციები: {args.sims} თითო წყვილზე, რაზმის ბიუჯეტი {SIM_BUDGET} მარჩილი; საწყისი მანძილი შემთხვევითია ({'/'.join(map(str, GAPS))}\").",
        "> ერთნაირი საბრძოლო პროფილის იუნიტები (მაგ. მოკავშირეების რიგითები) ერთად ითვლება და მოწინააღმდეგეთა სიაში ერთხელ შედის.",
        "> **ფასი** = საბრძოლო ღირებულება (ფორმულა, შემდეგ სიმულაციით კორექტირებული) + **ძალების ფასი** (ability_points, ხელით შეფასებული). საბაზისო: ლაშქარი = 20 მარჩილი.",
        "> სიმულაცია ამოწმებს მხოლოდ ბრძოლას: სიმულაციაში რაზმის ზომა საბრძოლო ღირებულებით ითვლება, რომ სპეციალური ძალების ფასი სიმულაციამ არ „წაშალოს“.",
        "> სიმულაციაში ითვლება: ორთქლის წნევა (1 ჟეტონი), ფარი, ფარის კედელი, ზალპი, ბადე/ჯაჭვი (რაზმს ანელებს), შხამი, ჯავშნის მსხვრევა, ქნევა, ბრაზი, ზემოდან სროლა, ცეცხლი, ელვა, ამოზრდა, შიშის არქონა.",
        "> **ფორმულის ფასი** — პირველადი შეფასება; **ფასი** — სიმულაციით კორექტირებული (რეკომენდებული). **მოგება % (ფორმულით)** აჩვენებს, რამდენად ცდებოდა ფორმულა.",
        "> **მოგების %** — საშუალო შედეგი სხვა ფრაქციების ყველა საბრძოლო იუნიტის წინააღმდეგ, თანაბარი ფასით. იდეალი ≈ 50%.",
        "> ⚠️ = 60%-ზე მეტი (ზედმეტად ძლიერი ფასთან შედარებით) ან 40%-ზე ნაკლები (ზედმეტად სუსტი).",
        "> ლიდერები, მკურნალები, ალქიმიკოსები და რიტუალისტები სიმულაციაში არ შედიან — მათი ღირებულება ძალებშია და **სატესტო თამაში** სჭირდება.",
        "",
    ]
    if fm:
        lines += [f"## ფრაქციები ერთმანეთის წინააღმდეგ (შერეული რაზმები, {FACTION_BUDGET} მარჩილი)", "",
                  f"> ყოველ წყვილზე {args.faction_sims} ბრძოლა; რაზმები შემთხვევით იკრიბება ფრაქციის საბრძოლო იუნიტებიდან კორექტირებული ფასებით",
                  "> (IV მაქს. 1, ერთ იუნიტზე მაქს. 4 მოდელი; ლიდერები და ძალების იუნიტები არ შედიან, გროტესკები — შედიან). იდეალი ≈ 50%; ⚠️ = 40–60%-ს გარეთ.",
                  "> ფრაქცია, რომლის ძალა მკურნალებში, რიტუალებსა და ლიდერშია, აქ სუსტად გამოჩნდება — მისი ცხრილი სატესტო თამაშით უნდა შემოწმდეს.", "",
                  "| ფრაქცია | საშუალო მოგება % | ყველაზე ძნელი მოწინააღმდეგე | ყველაზე ადვილი | შენიშვნა |", "|---|---|---|---|---|"]
        for f in sorted(fids, key=lambda f: -sum(fm[f].values()) / len(fm[f])):
            avg = sum(fm[f].values()) / len(fm[f])
            lo = min(fm[f], key=fm[f].get)
            hi = max(fm[f], key=fm[f].get)
            note = "⚠️ ძლიერი" if avg > 0.6 else ("⚠️ სუსტი" if avg < 0.4 else "✓")
            lines.append(f"| {names[f]} | {avg * 100:.0f}% | {names[lo]} ({fm[f][lo] * 100:.0f}%) | {names[hi]} ({fm[f][hi] * 100:.0f}%) | {note} |")
        lines.append("")
    for fid, fname in list(factions.items()) + [(k, v + " (მოკავშირე)") for k, v in allies.items()]:
        lines += [f"## {fname}", "", "| იუნიტი | დონე | ფორმულის ფასი | მოგება % (ფორმულით) | ძალები | **ფასი** | მოგება % | შენიშვნა |", "|---|---|---|---|---|---|---|---|"]
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
            lines.append(f"| {u['name']} | {u['tier']} | {u['_formula_cost']} | {rws} | {u['ability_points']} | **{u['_cost']}** | {wrs} | {note} |")
        lines.append("")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    COSTS.write_text(json.dumps({u["id"]: u["_cost"] for u in units}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    flagged = [(u["name"], win[u["id"]]) for u in units if win.get(u["id"]) is not None and not 0.4 <= win[u["id"]] <= 0.6]
    print(f"ანგარიში: {REPORT.relative_to(ROOT)}")
    print(f"სიმულირებული იუნიტები: {sum(1 for v in win.values() if v is not None)}; დროშით მონიშნული: {len(flagged)}")
    for name, wr in sorted(flagged, key=lambda x: -x[1]):
        print(f"  {wr * 100:5.1f}%  {name}")
    if fm:
        print("ფრაქციები (შერეული რაზმები):")
        for f in sorted(fids, key=lambda f: -sum(fm[f].values()) / len(fm[f])):
            print(f"  {sum(fm[f].values()) / len(fm[f]) * 100:5.1f}%  {names[f]}")


if __name__ == "__main__":
    main()
