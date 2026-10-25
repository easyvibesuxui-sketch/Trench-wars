#!/usr/bin/env python3
"""ბალანსერი (v3).

კითხულობს data/units.json-ს და:
1. ფორმულით ითვლის თითოეული იუნიტის ფასს მარჩილში (შეტევა × გამძლეობა + ძალების ფასი);
2. Monte Carlo-თი ათამაშებს თანაბარი ფასის რაზმებს ერთმანეთის წინააღმდეგ;
3. წერს ანგარიშს docs/balance-report.md-ში და ფასებს data/costs.json-ში და აჩვენებს ზედმეტად ძლიერ/სუსტ იუნიტებს.

გაშვება:  python3 tools/balancer.py [--sims 160] [--calibrate 16] [--mixed-sims 100] [--faction-sims 300] [--warm] [--seed 1]

v1: საწყისი მანძილი შემთხვევითია (12/24/36"), ერთნაირი პროფილები ერთად ითვლება, და ბოლოს ფრაქციები ერთმანეთს
შერეული რაზმებით ებრძვიან (ფრაქციის დონის ბალანსი).
v2: ყოველ მოდელს თავისი პოზიცია აქვს ხაზზე — მსროლელები ადგილზე რჩებიან, ხელჩართულის მოყვარულები წინ მიდიან და
უახლოეს მოწინააღმდეგესთან ჩერდებიან (წინა რიგი ზურგს ფარავს); ბადე/ჯაჭვი ცალკე მოდელს აჩერებს.
v3: მხარდაჭერის ძალები სიმულირდება (ლიდერი, ბრძანებები, მკურნალი, აღდგენა, უთანხმოება, სუსტი ადგილი, სიმღერა, მარაგი,
რიტუალი, წყევლა); მხარდაჭერის იუნიტების ფასს მხარდაჭერის ტესტი ადგენს; შერეულ რაზმებს ყოველთვის ჰყავს ლიდერი.
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
# v3: მხარდაჭერის ძალები, რომლებსაც სიმულაცია თამაშობს (ავრები და მოქმედებები)
SUPPORT = {"leader", "orders", "healer", "repair", "discord", "weakness", "song", "supply", "ritual", "witch"}
UNSIM_AP = {"alchemist": 6, "stitcher": 6}   # მხოლოდ კამპანიის ძალები — ფასს ხელით ემატება
MECH = {"construct", "vehicle", "automaton", "steam", "fortress"}
SUP_BASE = 300            # მხარდაჭერის ტესტის საბაზისო რაზმი (საბრძოლო ღირებულებით)
LEADER_FLOOR = 40         # ლიდერის მინიმალური ფასი: სავალდებულოა და ბრძანება/კამპანიის ღირებულებაც აქვს, რასაც სიმულაცია ვერ ხედავს
FACTION_BUDGET = 500      # ფრაქციების შერეული რაზმების ბიუჯეტი
MIX_WEIGHT = (0.7, 0.3)   # კალიბრაცია: ერთი იუნიტის რაზმის და შერეული რაზმის სიგნალების წონები
PIN_TAGS = {"pin", "entangle", "grab"}          # მოხვედრილს შემდეგ აქტივაციაზე მოძრაობა არ შეუძლია
NO_POISON = {"construct", "automaton", "vehicle", "undead", "fortress"}  # შხამი მათზე არ მოქმედებს
NO_SUPPRESS = {"fearless", "vehicle", "construct", "automaton", "fortress", "giant", "monster", "undead"}  # დათრგუნვა მათზე არ მოქმედებს

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
    if "suppress" in tags:
        dmg *= 1.15  # დათრგუნვა: ქვეითს აწვენს და აჩერებს
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
        u["_sup"] = frozenset(set(u["tags"]) & SUPPORT)
        u["_unsim"] = sum(UNSIM_AP.get(t, 0) for t in u["tags"])
        u["_sup_price"] = max(5.0, u["_cost"] - u["_unsim"]) if is_support(u) else None
    return k


# ---------------- Monte Carlo ----------------

class Model:
    __slots__ = ("u", "w", "used_once", "reload", "regen_block", "charged", "pinned", "steam_used", "army", "x",
                 "sup", "stunned", "exposed", "cursed", "suppressed")

    def __init__(self, u):
        self.u = u
        self.w = u["wounds"]
        self.used_once = set()
        self.reload = False
        self.regen_block = False
        self.charged = False
        self.pinned = False
        self.steam_used = False
        self.x = 0.0  # პოზიცია ხაზზე (ინჩებში)
        self.sup = u.get("_sup", frozenset())
        self.stunned = self.exposed = self.cursed = self.suppressed = False


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


def aura(army, tag, x, r=6):
    """არის თუ არა ამ რაზმში ცოცხალი მოდელი ამ ძალით r ინჩში."""
    return any(a.w > 0 and tag in a.sup and abs(a.x - x) <= r for a in army)


def sim_price(u):
    """სიმულაციის ფასი: მხარდაჭერის იუნიტს — მთელი (ძალებით), დანარჩენს — საბრძოლო ღირებულება."""
    return u.get("_sup_price") or u["_combat"]


def attack(m, w, targets, rng, pool):
    """targets — ვისაც ეს იარაღი სწვდება; pool — ყველა ცოცხალი მოწინააღმდეგე (აფეთქების მეორე სამიზნისთვის)."""
    power = w["power"] + (1 if ("charge" in w["tags"] and not m.charged) else 0)
    if w["mode"] == "melee" and aura(m.army, "ritual", m.x):
        power += 1  # სისხლის რიტუალი: 6"-ში მოკავშირეები +1 ძალა ხელჩართულში
    skill_mod = -1 if m.cursed else 0  # წყევლა
    if w["mode"] == "melee" and aura(pool, "song", m.x):
        skill_mod -= 1  # მოწინააღმდეგის სიმღერა 6"-ში: −1 ხელჩართული
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
        alive = [e for e in targets if e.w > 0]
        if not alive:
            return
        t = rng.choice(alive)
        tl = [t]
        if "blast" in w["tags"] and t.u["size"] == 1 and rng.random() < 0.5:
            near = [e for e in pool if e.w > 0 and e is not t and abs(e.x - t.x) <= 2]
            if near:
                tl.append(rng.choice(near))
        if "sweep" in w["tags"] and w["mode"] == "melee" and len(alive) > 1 and rng.random() < 0.5:
            tl.append(rng.choice([e for e in alive if e is not t]))
        for tt in tl:
            if w["mode"] == "ranged":
                # სანგრების ომი: 6"-ზე შორს სამიზნე საფარშია (-1 სროლაზე); „ზემოდან“ საფარს უგულებელყოფს
                cover = 1 if abs(tt.x - m.x) > 6 and "indirect" not in w["tags"] else 0
                if tt.suppressed:
                    cover += 1  # დაბლა წოლილი: კიდევ −1
                aa = "anti_air" in m.u["tags"]
                if "fly" in tt.u["tags"]:
                    cover += -1 if aa else 1  # მფრინავზე: საზენიტოს +1, სხვას −1
                if "suppress" in w["tags"] and tt.u["size"] == 1 and not (set(tt.u["tags"]) & NO_SUPPRESS):
                    tt.suppressed = True  # დათრგუნვა: ცეცხლის ქვეშ — მოხვედრაც არ სჭირდება
                skill = m.u["shoot"] - cover + skill_mod
            else:
                skill = m.u["melee"] + skill_mod
            if rng.random() >= hit_p(skill, tt.u["size"]):
                continue
            if set(w["tags"]) & PIN_TAGS:
                tt.pinned = True  # ბადე/ჯაჭვი: მოხვედრაც საკმარისია — შემდეგ სვლაზე ვერ მოძრაობს
            armor = tt.u["armor"]
            if aura(tt.army, "orders", tt.x):
                armor += 1  # ბრძანება „წყობა“: 6"-ში მოკავშირეებს +1 ჯავშანი
            if tt.exposed:
                armor = max(0, armor - 1)  # სუსტი ადგილი ნაჩვენებია
            if "armor_break" in w["tags"]:
                armor = max(0, armor - 1)
            if w["mode"] == "ranged" and "shield" in tt.u["tags"]:
                armor += 1  # ფარი სროლისგან იცავს
            if "shield_wall" in tt.u["tags"] and sum(1 for x in tt.army if x.w > 0 and x.u is tt.u) >= 2:
                armor += 1  # ფარის კედელი: ორი ან მეტი ერთად
            pw = power + (1 if w["mode"] == "ranged" and "fly" in tt.u["tags"] and "anti_air" in m.u["tags"] else 0)
            if rng.random() < wound_p(pw, armor, w["tags"], tt.u["size"]):
                tt.w -= w["damage"]
                if "fire" in w["tags"] or "lightning" in w["tags"] or "festering" in w["tags"]:
                    tt.regen_block = True
                if "poison" in w["tags"] and tt.w > 0 and not (set(tt.u["tags"]) & NO_POISON) and rng.random() < 0.5:
                    tt.w -= 1  # შხამი
                if "fire" in w["tags"] and tt.w > 0 and rng.random() < 0.5:
                    tt.w -= 1  # წვა


def activate(m, enemies, rng):
    """v2: ყოველ მოდელს თავისი პოზიცია აქვს ხაზზე. ხელჩართულის მოყვარული წინ მიდის, მსროლელი ადგილზე რჩება და ისვრის,
    თუ სამიზნე მანძილშია; მოძრავი მოდელი უახლოეს მოწინააღმდეგესთან ჩერდება — ასე წინა რიგი ზურგს ფარავს."""
    if m.stunned:  # უთანხმოება: ეს აქტივაცია დაკარგულია
        m.stunned = False
        return
    down = False
    if m.suppressed:  # დათრგუნვა: ნებისყოფის ტესტი (ლიდერი 6"-ში +1) — ჩავარდნა: დაბლა, მხოლოდ 1 მოქმედება
        m.suppressed = False
        bonus = 1 if aura(m.army, "leader", m.x) else 0
        down = rng.randint(1, 10) > m.u["nerve"] + bonus
    m.reload = False if m.reload and (rng.random() < 0.5 or aura(m.army, "supply", m.x)) else m.reload
    alive = [e for e in enemies if e.w > 0]
    if not alive:
        return
    near = min(alive, key=lambda e: abs(e.x - m.x))
    dn = abs(near.x - m.x)
    if dn > 1.0 and m.sup and support_action(m, alive, rng):
        return
    if dn <= 1.0:  # ხელჩართულში ჩაბმული
        w = best_weapon(m, "melee", 0)
        if w:
            attack(m, w, [e for e in alive if abs(e.x - m.x) <= 1.0], rng, alive)
        m.pinned = False
        return
    if not m.u["_melee_pref"]:
        w = best_weapon(m, "ranged", dn)
        if w:
            attack(m, w, [e for e in alive if abs(e.x - m.x) <= w["range"]], rng, alive)
            m.pinned = False
            return
    if m.pinned or down:  # ბადე/ჯაჭვი ან დათრგუნვა: ამ სვლაზე ვერ მოძრაობს და ვერ უტევს
        m.pinned = False
        return
    hold = 8.0 if (m.sup - {"leader", "orders", "ritual", "supply"}) and m.u["tier"] not in ("IV", "IV+") else 1.0
    step = max(0.0, min(m.u["move"], dn - hold))  # მხარდაჭერა უკან რჩება (8")
    m.x += step if near.x > m.x else -step
    if dn - step <= 1.0:  # იერიში: მივიდა და იმავე სვლაზე ურტყამს
        w = best_weapon(m, "melee", 0)
        if w:
            attack(m, w, [e for e in alive if abs(e.x - m.x) <= 1.0], rng, alive)


def support_action(m, alive, rng):
    """მხარდაჭერის მოქმედება შეტევის ნაცვლად. True — თუ მოქმედება შესრულდა."""
    sup = m.sup
    if sup & {"healer", "repair"}:
        need = 2 if m.u["tier"] in ("IV", "IV+") else 1
        hurt = [a for a in m.army if a.w > 0 and a is not m and a.u["wounds"] - a.w >= need and abs(a.x - m.x) <= 6
                and ("healer" in sup or set(a.u["tags"]) & MECH)]
        if hurt:
            max(hurt, key=lambda a: a.u["wounds"] - a.w).w += 1  # მკურნალობა / აღდგენა: +1 სიცოცხლე
            return True
    in12 = [e for e in alive if abs(e.x - m.x) <= 12]
    if "discord" in sup and in12 and not ("leader" in sup and best_weapon(m, "ranged", abs(min(in12, key=lambda e: abs(e.x - m.x)).x - m.x))):
        t = min((e for e in in12 if not e.stunned), key=lambda e: abs(e.x - m.x), default=None)
        if t:
            if "fearless" not in t.u["tags"] and rng.randint(1, 10) > t.u["nerve"]:
                t.stunned = True  # უთანხმოება: შემდეგი აქტივაცია დაკარგულია
            return True
    if "weakness" in sup and in12:
        t = max((e for e in in12 if not e.exposed), key=lambda e: (e.u["size"], -abs(e.x - m.x)), default=None)
        if t:
            t.exposed = True  # სუსტი ადგილი: ამ რაუნდში ჯავშანი −1
            return True
    if "witch" in sup and in12:
        t = min((e for e in in12 if not e.cursed), key=lambda e: abs(e.x - m.x), default=None)
        if t:
            t.cursed = True  # წყევლა: −1 სროლა და ხელჩართული
            return True
    return False


def battle(ua, ub, budget, rng, max_rounds=8):
    return fight(build_army(ua, budget, rng), build_army(ub, budget, rng), rng, max_rounds)


def fight(A, B, rng, max_rounds=8):
    nA, nB = len(A), len(B)
    # საწყისი მანძილი შემთხვევითია: ახლო (12"), საშუალო (24") ან შორი (36") — სხვადასხვა რუკა და განლაგება
    gap = rng.choice(GAPS)
    for m in A:
        m.x = 0.0
    for m in B:
        m.x = float(gap)
    tested = {"A": False, "B": False}
    for _ in range(max_rounds):
        for army in (A, B):
            for m in army:
                m.exposed = False
                if m.w > 0 and "regen" in m.u["tags"] and not m.regen_block and m.w < m.u["wounds"]:
                    m.w += 1
                m.regen_block = False
        order = [("A", m) for m in A] + [("B", m) for m in B]
        rng.shuffle(order)
        for side, m in order:
            if m.w <= 0:
                continue
            enemies = B if side == "A" else A
            if not any(e.w > 0 for e in enemies):
                break
            activate(m, enemies, rng)
        for army in (A, B):
            for m in army:
                if m.w > 0 and m.steam_used and rng.randint(1, 10) <= 1:
                    m.w -= 1  # გადატვირთვა: d10 ≤ ჟეტონების რაოდენობა (1)
                m.steam_used = False
        for key, army, n in (("A", A, nA), ("B", B, nB)):
            if not tested[key] and sum(1 for m in army if m.w > 0) * 2 < n:
                tested[key] = True
                for m in army:
                    bonus = 1 if (aura(army, "leader", m.x) or aura(army, "song", m.x)) else 0  # ლიდერი / სიმღერა 6"-ში
                    if m.w > 0 and "fearless" not in m.u["tags"] and rng.randint(1, 10) > m.u["nerve"] + bonus:
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
    # გროტესკები (IV) სიმულაციაში შედიან ძალებითაც (მაგ. აღდგენა) — ისინი ძირითადად მებრძოლები არიან
    pool = [u for u in units if u["tier"] in SIM_TIERS and "leader" not in u["tags"]
            and (u["tier"] in ("IV", "IV+") or not (set(u["tags"]) & ABILITY_TAGS))]
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


def stat_key(u):
    """მაჩვენებლები: ყველაფერი, რასაც სიმულაცია ხედავს (სახელების და ფასის გარეშე)."""
    ws = sorted((w["mode"], w["range"], w["attacks"], w["power"], w["damage"], tuple(sorted(w["tags"]))) for w in u["weapons"])
    return (u["size"], u["move"], u["shoot"], u["melee"], u["armor"], u["wounds"], u["nerve"], u["tier"],
            tuple(sorted(u["tags"])), tuple(ws))


def profile_key(u):
    return stat_key(u) + (round(u["_combat"], 6),)


# ---------------- ფრაქციები ერთმანეთის წინააღმდეგ ----------------

def faction_units(roster, budget, rng, leaders=()):
    """შემთხვევითი, მაგრამ კანონიერი რაზმის შემადგენლობა: 1 ლიდერი (თუ არის), IV მაქს. 1, ერთ იუნიტზე მაქს. 4 მოდელი.
    ბიუჯეტი სიმულაციის ფასით ითვლება (მებრძოლებს — საბრძოლო ღირებულება, მხარდაჭერას — ძალებით)."""
    out, left, counts, big = [], budget, {}, False
    if leaders:
        ld = rng.choice(leaders)
        out.append(ld)
        left -= sim_price(ld)
    while True:
        opts = [u for u in roster if sim_price(u) <= left and counts.get(u["id"], 0) < 4 and not (big and u["tier"] in ("IV", "IV+"))]
        if not opts:
            break
        u = rng.choice(opts)
        counts[u["id"]] = counts.get(u["id"], 0) + 1
        big = big or u["tier"] in ("IV", "IV+")
        left -= sim_price(u)
        out.append(u)
    return out


def make_army(units):
    army = [Model(u) for u in units]
    for m in army:
        m.army = army
    return army


def faction_army(roster, budget, rng, leaders=()):
    return make_army(faction_units(roster, budget, rng, leaders))


def _faction_score(job):
    """აბრუნებს: A-ს საშუალო შედეგს და იუნიტების „წვლილს“ — შერეული რაზმის შედეგი, აწონილი იუნიტის წილით ბიუჯეტში."""
    a, b, seed = job
    r = random.Random(seed)
    total, contrib = 0.0, {}
    for _ in range(_SIMS):
        A = faction_army(_ROSTERS[a], FACTION_BUDGET, r, _LEADERS[a])
        B = faction_army(_ROSTERS[b], FACTION_BUDGET, r, _LEADERS[b])
        res = fight(A, B, r) if A and B else 0.5
        total += res
        for army, sc in ((A, res), (B, 1 - res)):
            spent = sum(sim_price(m.u) for m in army) or 1
            for m in army:
                k = stat_key(m.u)
                c = contrib.setdefault(k, [0.0, 0.0])
                c[0] += sc * sim_price(m.u) / spent
                c[1] += sim_price(m.u) / spent
    return total / _SIMS, contrib


_ROSTERS, _LEADERS = {}, {}


def is_support(u):
    """მხარდაჭერის იუნიტი (I–III): ფასდება მხარდაჭერის ტესტით და არა ერთი იუნიტის რაზმით."""
    return bool(u.get("_sup")) and u["tier"] in ("I", "II", "III")


def combat_roster(units, f):
    return [u for u in units if u["faction"] == f and not is_support(u)
            and (u["tier"] == "IV" or (u["tier"] in {"I", "II", "III"} and not (set(u["tags"]) & ABILITY_TAGS)))]


# ---------------- მხარდაჭერის ტესტი ----------------
# ორი იდენტური რაზმი (ფრაქციის მებრძოლები, SUP_BASE): A-ს ემატება მხარდაჭერის იუნიტი, B-ს — იმავე ფასის რიგითები.
# მოგება ≈ 50% ნიშნავს, რომ მხარდაჭერა თავის ფასს ზუსტად ამართლებს.
_SUP, _BASE, _REG = [], {}, {}


def _support_score(job):
    i, seed = job
    u = _SUP[i]
    r = random.Random(seed)
    reg = _REG[u["faction"]]
    total = 0.0
    for _ in range(_SIMS):
        comp = faction_units(_BASE[u["faction"]], SUP_BASE, r)
        x = sim_price(u) / max(3.0, reg["_cost"])
        n = int(x) + (1 if r.random() < x - int(x) else 0)
        total += fight(make_army(comp + [u]), make_army(comp + [reg] * n), r)
    return total / _SIMS


def support_test(units, sims, rng):
    global _SUP, _BASE, _REG, _SIMS
    _SUP = [u for u in units if is_support(u)]
    fs = {u["faction"] for u in _SUP}
    _BASE = {f: [u for u in combat_roster(units, f) if u["tier"] != "IV"] for f in fs}
    _REG = {f: next(u for u in units if u["faction"] == f and u["tier"] == "I" and {"line", "gas_mask"} <= set(u["tags"])) for f in fs}
    for u in units:
        if u["tier"] in SIM_TIERS:
            set_pref(u)
    _SIMS = sims
    jobs = [(i, rng.randrange(2**31)) for i in range(len(_SUP))]
    workers = os.cpu_count() or 1
    if workers > 1:
        with multiprocessing.get_context("fork").Pool(workers) as mp:
            scores = mp.map(_support_score, jobs, chunksize=2)
    else:
        scores = [_support_score(j) for j in jobs]
    return {u["id"]: sc for u, sc in zip(_SUP, scores)}


def faction_matrix(units, fids, sims, rng):
    """ფრაქცია ფრაქციის წინააღმდეგ შერეული რაზმებით.
    ლიდერები და ძალების იუნიტები არ შედიან (მათ სიმულაცია ვერ აფასებს); გროტესკები (IV) შედიან ძალებითაც, რადგან ისინი ძირითადად მებრძოლები არიან."""
    global _ROSTERS, _LEADERS, _SIMS
    # v3: რაზმს ყოველთვის ჰყავს ლიდერი, და მხარდაჭერის იუნიტებიც შედის (მათი ძალები ახლა სიმულირდება)
    _ROSTERS = {f: combat_roster(units, f) + [u for u in units if u["faction"] == f and is_support(u) and "leader" not in u["tags"]] for f in fids}
    _LEADERS = {f: [u for u in units if u["faction"] == f and is_support(u) and "leader" in u["tags"]] for f in fids}
    for u in units:
        if u["tier"] in SIM_TIERS:
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
    contrib = {}
    for (a, b, _), (sc, cb) in zip(jobs, scores):
        m[a][b], m[b][a] = sc, 1 - sc
        for k, (x, w) in cb.items():
            c = contrib.setdefault(k, [0.0, 0.0])
            c[0] += x
            c[1] += w
    # ერთნაირი მაჩვენებლების იუნიტებს (სხვადასხვა ფრაქციაში) ერთი წვლილი აქვთ
    mixed = {u["id"]: contrib[stat_key(u)][0] / contrib[stat_key(u)][1]
             for r in _ROSTERS.values() for u in r if contrib.get(stat_key(u), (0, 0))[1] > 0}
    return m, mixed


_POOL, _SIMS = [], 0


def _pair_score(job):
    i, j, seed = job
    r = random.Random(seed)
    return sum(battle(_POOL[i], _POOL[j], SIM_BUDGET, r) for _ in range(_SIMS)) / _SIMS


def calibrate_support(units, sims, rng):
    sw = support_test(units, sims, rng)
    for u in units:
        wr = sw.get(u["id"])
        if wr is None:
            continue
        u["_sup_price"] *= clamp((max(wr, 0.02) / 0.5) ** 0.5, 0.85, 1.15)
        if "leader" in u["tags"]:
            u["_sup_price"] = max(u["_sup_price"], LEADER_FLOOR - u["_unsim"])
        u["_cost"] = max(5, round(u["_sup_price"] + u["_unsim"]))
    return sw


def calibrate(units, sims, rng, iterations, fids=(), fsims=0, ssims=0):
    """ფასების ავტომატური კორექცია: ძლიერი იუნიტი ძვირდება, სუსტი — იაფდება.
    ორი სიგნალი: (1) ერთი იუნიტის რაზმი ყველა სხვის წინააღმდეგ; (2) წვლილი ფრაქციების შერეულ რაზმებში.
    ორივეს აწონილი გეომეტრიული საშუალო (MIX_WEIGHT) — ასე იუნიტი ცალკეც დაბალანსებულია და ფრაქციის შემადგენლობაშიც.
    შერეულ სიგნალს ნაკლები წონა აქვს: მასში თანაგუნდელების ძალაც ერევა (ცუდი შემადგენლობის ფრაქციაში კარგი იუნიტიც „სუსტად“ ჩანს)."""
    sup_win = {}
    for _ in range(iterations):
        if ssims:
            sup_win = calibrate_support(units, ssims, rng)
        win = simulate(units, sims, rng)
        mixed = faction_matrix(units, list(fids), fsims, rng)[1] if fsims else {}
        for u in units:
            wr, mx = win.get(u["id"]), mixed.get(u["id"])
            if wr is None:
                continue  # მხოლოდ შერეული სიგნალით ფასი არ იცვლება (მასში თანაგუნდელების ძალაც ერევა)
            # დაცვა: თუ იუნიტი ცალკე 45–55%-ს გარეთაა, მხოლოდ ცალკე შედეგი ითვლება — შერეულმა სიგნალმა
            # (რომელშიც თანაგუნდელების ძალაც ერევა) იუნიტი ცალკე ბალანსიდან არ უნდა გამოიყვანოს
            if wr is not None and (mx is None or not 0.45 <= wr <= 0.55):
                score = max(wr, 0.02)
            else:
                score = max(wr, 0.02) ** MIX_WEIGHT[0] * max(mx, 0.02) ** MIX_WEIGHT[1]
            factor = clamp((score / 0.5) ** 0.35, 0.85, 1.15)
            u["_combat"] *= factor
            u["_calibrated"] = True
        # ნორმალიზაცია: საბაზისო იუნიტი (საბრძოლო ნაწილი + ძალები) ყოველთვის BASE_COST-ია
        base = next(u for u in units if u["id"] == BASE_UNIT)
        norm = (BASE_COST - base["ability_points"]) / base["_combat"]
        for u in units:
            if u.get("_calibrated"):
                u["_combat"] *= norm
                u["_cost"] = max(5, round(u["_combat"] + u["ability_points"]))
    return simulate(units, sims, rng), (support_test(units, ssims, rng) if ssims else sup_win)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=200)
    ap.add_argument("--faction-sims", type=int, default=300, help="ფრაქციების შერეული რაზმების ბრძოლები თითო წყვილზე (0 = გამორთული)")
    ap.add_argument("--mixed-sims", type=int, default=100, help="შერეული რაზმების ბრძოლები კალიბრაციის ყოველ იტერაციაზე (0 = მხოლოდ ერთი იუნიტის რაზმები)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--support-sims", type=int, default=400, help="მხარდაჭერის ტესტის ბრძოლები თითო იუნიტზე (0 = ძალები ხელით)")
    ap.add_argument("--warm", action="store_true", help="კალიბრაცია data/costs.json-ის ფასებიდან დაიწყოს (ახალი იუნიტები — ფორმულით)")
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
    if args.warm and COSTS.exists():
        # თბილი სტარტი: კალიბრაცია წინა ფასებიდან იწყება (ცვლილებების შემდეგ ნაკლები იტერაცია სჭირდება)
        prev = json.loads(COSTS.read_text(encoding="utf-8"))
        for u in units:
            if u["id"] in prev and u["tier"] in SIM_TIERS:
                if is_support(u):
                    u["_sup_price"] = max(5.0, prev[u["id"]] - u["_unsim"])
                else:
                    u["_combat"] = max(3.0, prev[u["id"]] - u["ability_points"])
                u["_cost"] = prev[u["id"]]
    allies = data.get("allies", {})
    names = {**factions, **allies}
    fids = list(factions) + list(allies)
    if args.calibrate:
        win, sup_win = calibrate(units, args.sims, rng, args.calibrate, fids, args.mixed_sims, args.support_sims)
    else:
        win, sup_win = raw_win, (support_test(units, args.support_sims, rng) if args.support_sims else {})
    fm, mixed = faction_matrix(units, fids, args.faction_sims, rng) if args.faction_sims else (None, {})

    lines = [
        "# ბალანსის ანგარიში (ავტომატური)",
        "",
        f"> გენერირებულია `tools/balancer.py`-ით. სიმულაციები: {args.sims} თითო წყვილზე, რაზმის ბიუჯეტი {SIM_BUDGET} მარჩილი; საწყისი მანძილი შემთხვევითია ({'/'.join(map(str, GAPS))}\").",
        "> **v2 — პოზიციები:** ყოველ მოდელს თავისი ადგილი აქვს ხაზზე. მსროლელი ადგილზე რჩება და ისვრის, თუ სამიზნე მანძილშია (6\"-ზე შორს — საფარი, −1);",
        "> ხელჩართულის მოყვარული უახლოეს მოწინააღმდეგესთან მიდის და მიღწევისას იმავე სვლაზე ურტყამს; ჩაბმული მოდელი მხოლოდ ხელჩართულში იბრძვის.",
        "> ასე წინა რიგი ზურგს ფარავს: მსროლელამდე მისასვლელად ჯერ მის წინ მდგომი უნდა დაამარცხო.",
        "> ერთნაირი საბრძოლო პროფილის იუნიტები (მაგ. მოკავშირეების რიგითები) ერთად ითვლება და მოწინააღმდეგეთა სიაში ერთხელ შედის.",
        "> **ფასი** = საბრძოლო ღირებულება (ფორმულა, შემდეგ სიმულაციით კორექტირებული) + **ძალების ფასი** (ability_points, ხელით შეფასებული). საბაზისო: ლაშქარი = 20 მარჩილი.",
        "> სიმულაცია ამოწმებს მხოლოდ ბრძოლას: სიმულაციაში რაზმის ზომა საბრძოლო ღირებულებით ითვლება, რომ სპეციალური ძალების ფასი სიმულაციამ არ „წაშალოს“.",
        "> სიმულაციაში ითვლება: ორთქლის წნევა (1 ჟეტონი), ფარი, ფარის კედელი, ზალპი, ბადე/ჯაჭვი (მოდელს აჩერებს), შხამი, ჯავშნის მსხვრევა, ქნევა, ბრაზი, ზემოდან სროლა, ცეცხლი, ელვა, ამოზრდა, შიშის არქონა.",
        "> **ფორმულის ფასი** — პირველადი შეფასება; **ფასი** — სიმულაციით კორექტირებული (რეკომენდებული). **მოგება % (ფორმულით)** აჩვენებს, რამდენად ცდებოდა ფორმულა.",
        "> **მოგების %** — საშუალო შედეგი სხვა ფრაქციების ყველა საბრძოლო იუნიტის წინააღმდეგ, თანაბარი ფასით. იდეალი ≈ 50%.",
        "> **შერეულ რაზმში %** — იუნიტის წვლილი ფრაქციების შერეულ რაზმებში (რაზმის შედეგი, აწონილი იუნიტის წილით ბიუჯეტში). კალიბრაცია ორივე სიგნალს ითვალისწინებს.",
        "> ⚠️ = 60%-ზე მეტი (ზედმეტად ძლიერი ფასთან შედარებით) ან 40%-ზე ნაკლები (ზედმეტად სუსტი).",
        "> **v3 — მხარდაჭერა:** ლიდერი (6\"-ში +1 ნებისყოფა), ბრძანებები (+1 ჯავშანი), მკურნალი და აღდგენა (+1 სიცოცხლე), უთანხმოება (აქტივაციის დაკარგვა),",
        "> სუსტი ადგილი (−1 ჯავშანი), სიმღერა (მტერს −1 ხელჩართული, მოკავშირეებს +1 ნებისყოფა), მარაგი (დატენვა), რიტუალი (+1 ძალა), წყევლა (−1 სროლა/ხელჩართული) — სიმულირდება.",
        "> მხარდაჭერის იუნიტის ფასს **მხარდაჭერის ტესტი** ადგენს: ორი იდენტური რაზმი, ერთს ემატება ეს იუნიტი, მეორეს — იმავე ფასის რიგითები; იდეალი ≈ 50%.",
        "> მხოლოდ კამპანიის ძალები (ალქიმია, ნაკერი სხეულები) არ სიმულირდება — მათ ფასს +6 ემატება თითოზე. შერეულ რაზმებს ყოველთვის ჰყავს ლიდერი.",
        f"> ლიდერის ფასის ქვედა ზღვარი — {LEADER_FLOOR} მარჩილი (სავალდებულოა; ბრძანებების და კამპანიის ღირებულება სიმულაციის მიღმაა). ასეთ ლიდერს მხარდაჭერის ტესტი 40%-ზე დაბლა შეიძლება აჩვენებდეს.",
        "",
    ]
    if fm:
        lines += [f"## ფრაქციები ერთმანეთის წინააღმდეგ (შერეული რაზმები, {FACTION_BUDGET} მარჩილი)", "",
                  f"> ყოველ წყვილზე {args.faction_sims} ბრძოლა; რაზმები შემთხვევით იკრიბება ფრაქციის საბრძოლო იუნიტებიდან საბრძოლო ღირებულებით (ძალების ფასის გარეშე)",
                  "> (IV მაქს. 1, ერთ იუნიტზე მაქს. 4 მოდელი; ლიდერები და ძალების იუნიტები არ შედიან, გროტესკები — შედიან). იდეალი ≈ 50%; ⚠️ = 40–60%-ს გარეთ.",
                  "> ფრაქცია, რომლის ძალა მკურნალებში, რიტუალებსა და ლიდერშია, აქ სუსტად გამოჩნდება — მისი ცხრილი სატესტო თამაშით უნდა შემოწმდეს.",
                  "> სიმულაციაში ყოველ მოდელს თავისი პოზიცია აქვს (წინა რიგი ზურგს ფარავს), მაგრამ რელიეფი და მიზნები არ არის. ეს ცხრილი",
                  "> ფრაქციის **შემადგენლობის** სიგნალია (რა აკლია რაზმს), და არა ფასების — ფასები ზედა სვეტებით ფასდება.", "",
                  "| ფრაქცია | საშუალო მოგება % | ყველაზე ძნელი მოწინააღმდეგე | ყველაზე ადვილი | შენიშვნა |", "|---|---|---|---|---|"]
        for f in sorted(fids, key=lambda f: -sum(fm[f].values()) / len(fm[f])):
            avg = sum(fm[f].values()) / len(fm[f])
            lo = min(fm[f], key=fm[f].get)
            hi = max(fm[f], key=fm[f].get)
            note = "⚠️ ძლიერი" if avg > 0.6 else ("⚠️ სუსტი" if avg < 0.4 else "✓")
            lines.append(f"| {names[f]} | {avg * 100:.0f}% | {names[lo]} ({fm[f][lo] * 100:.0f}%) | {names[hi]} ({fm[f][hi] * 100:.0f}%) | {note} |")
        lines.append("")
    for fid, fname in list(factions.items()) + [(k, v + " (მოკავშირე)") for k, v in allies.items()]:
        lines += [f"## {fname}", "", "| იუნიტი | დონე | ფორმულის ფასი | მოგება % (ფორმულით) | ძალები | **ფასი** | მოგება % | შერეულ რაზმში % | შენიშვნა |", "|---|---|---|---|---|---|---|---|---|"]
        for u in [x for x in units if x["faction"] == fid]:
            wr = win.get(u["id"])
            if wr is None and u["id"] in sup_win:
                sw = sup_win[u["id"]]
                wrs = f"{sw * 100:.0f}% (მხარდაჭერა)"
                note = "⚠️ ძლიერი" if sw > 0.6 else ("⚠️ სუსტი" if sw < 0.4 else "✓")
            elif wr is None:
                note = "სიმულაციის გარეშე (კამპანიის ძალები / სუპერიუნიტი)"
                wrs = "—"
            else:
                wrs = f"{wr * 100:.0f}%"
                note = "⚠️ ძლიერი" if wr > 0.6 else ("⚠️ სუსტი" if wr < 0.4 else "✓")
            rw = raw_win.get(u["id"])
            rws = f"{rw * 100:.0f}%" if rw is not None else "—"
            mx = mixed.get(u["id"])
            mxs = f"{mx * 100:.0f}%" if mx is not None else "—"
            if mx is not None and not 0.35 <= mx <= 0.65:
                note += " · ⚠️ შერეულში"
            lines.append(f"| {u['name']} | {u['tier']} | {u['_formula_cost']} | {rws} | {u['ability_points']} | **{u['_cost']}** | {wrs} | {mxs} | {note} |")
        lines.append("")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    COSTS.write_text(json.dumps({u["id"]: u["_cost"] for u in units}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    flagged = [(u["name"], win[u["id"]]) for u in units if win.get(u["id"]) is not None and not 0.4 <= win[u["id"]] <= 0.6]
    flagged += [(u["name"] + " (მხარდაჭერა)", sup_win[u["id"]]) for u in units if u["id"] in sup_win and not 0.4 <= sup_win[u["id"]] <= 0.6
                and not ("leader" in u["tags"] and u["_cost"] <= LEADER_FLOOR and sup_win[u["id"]] < 0.4)]
    print(f"ანგარიში: {REPORT.relative_to(ROOT)}")
    print(f"სიმულირებული იუნიტები: {sum(1 for v in win.values() if v is not None)} + მხარდაჭერა {len(sup_win)}; დროშით მონიშნული: {len(flagged)}")
    for name, wr in sorted(flagged, key=lambda x: -x[1]):
        print(f"  {wr * 100:5.1f}%  {name}")
    if fm:
        print("ფრაქციები (შერეული რაზმები):")
        for f in sorted(fids, key=lambda f: -sum(fm[f].values()) / len(fm[f])):
            print(f"  {sum(fm[f].values()) / len(fm[f]) * 100:5.1f}%  {names[f]}")


if __name__ == "__main__":
    main()
