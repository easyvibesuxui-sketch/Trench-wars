#!/usr/bin/env python3
"""„სამი ხაზის“ სიმულაცია: ორი სასტარტო დასტა ერთმანეთის წინააღმდეგ, მარტივი (ხარბი) ხელოვნური მოთამაშეებით.

ამოწმებს, რომ წესები სრულდება (თამაში მთავრდება), და აჩვენებს ბალანსს: მოგების %, თამაშის სიგრძე, მოგების გზა.
წესები — rules/cardgame.md (გამარტივებით: ჩიხი/მავთული/შენიღბვა სიმულაციაში არ არის).

გაშვება:  python3 tools/sim_cardgame.py [--games 2000]
"""
import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POS = ("rear", "trench", "nml")


class U:
    def __init__(self, c, owner):
        self.c, self.owner, self.hp = c, owner, c["hp"]
        self.kw = set(c.get("kw", []))
        self.lane = self.pos = None
        self.ready = "charge" in self.kw
        self.sup = self.burn = False


def build(deck, cards, common):
    out = [cards[i] for i, n in deck["units"].items() for _ in range(n)] + [common[i] for i, n in deck["common"].items() for _ in range(n)]
    return [dict(c) for c in out]


class Game:
    def __init__(self, decks, rng):
        self.rng, self.units, self.forts, self.turn = rng, [], {}, 0
        self.p = []
        for d in decks:
            rng.shuffle(d)
            self.p.append({"deck": d, "hand": [d.pop() for _ in range(5)], "hq": 20, "bank": 0, "porters": 0})
        self.p[1]["hand"].append(self.p[1]["deck"].pop())

    def at(self, lane, owner, pos):
        return [u for u in self.units if u.lane == lane and u.owner == owner and u.pos == pos and u.hp > 0]

    def nml_ctrl(self, owner):
        return sum(1 for l in range(3) if self.at(l, owner, "nml") and not self.at(l, 1 - owner, "nml"))

    def dmg(self, src, t, amount):
        if t.c["id"] == "_fort":
            t.hp -= amount
            return
        a = amount + (2 if "hunter" in src.kw and t.c.get("tier") in ("IV", "IV+", "V") else 0) + (2 if "anti_air" in src.kw and "fly" in t.kw else 0)
        if "shield" in t.kw:
            a -= 1
        f = self.forts.get((t.lane, t.owner))
        if t.pos == "trench" and f and f["id"] == "trench" and "breaker" not in src.kw:
            a -= 1
        t.hp -= max(1, a)
        if "suppress" in src.kw and "fearless" not in t.kw:
            t.sup = True
        if "fire" in src.kw:
            t.burn = True

    def targets(self, u):
        e = 1 - u.owner
        if "fly" in u.kw:
            return [x for x in self.units if x.owner == e and x.hp > 0]
        order = [(u.lane, e, "nml"), (u.lane, e, "trench"), (u.lane, e, "rear")]
        if u.pos == "rear" and "long" not in u.kw:
            return []
        if "long" in u.kw:
            return [x for k in order for x in self.at(*k)]
        for k in order:
            xs = self.at(*k)
            if xs:
                return xs
        return []

    def attack(self, u):
        ts = self.targets(u)
        bonus = 1 if any("leader" in x.kw for x in self.at(u.lane, u.owner, "trench") + self.at(u.lane, u.owner, "nml") + self.at(u.lane, u.owner, "rear") if x is not u) else 0
        if ts:
            t = min(ts, key=lambda x: x.hp)
            self.dmg(u, t, u.c["atk"] + bonus)
            adj = abs(POS.index(u.pos) - {"nml": 2, "trench": 3, "rear": 4}[t.pos]) <= 1   # ხელჩართული — მეზობელ ადგილზე
            if t.hp > 0 and "long" not in u.kw and "fly" not in u.kw and adj and not t.sup:
                self.dmg(t, u, t.c["atk"])
        elif u.pos == "nml" and not self.at(u.lane, 1 - u.owner, "trench") and not self.at(u.lane, 1 - u.owner, "rear"):
            self.p[1 - u.owner]["hq"] -= u.c["atk"] + bonus

    def play(self, me):
        P, rng = self.p[me], self.rng
        avail = 3 + P["porters"] + self.nml_ctrl(me) + P["bank"]
        for c in sorted(P["hand"], key=lambda c: -c["cost"]):
            if c["cost"] > avail:
                continue
            if c.get("kind") == "იუნიტი":
                if "giant" in c.get("kw", []) and self.nml_ctrl(me) < 2:
                    continue
                lane = min(range(3), key=lambda l: len(self.at(l, me, "trench")) + len(self.at(l, me, "rear")) - len(self.at(l, 1 - me, "nml")) + rng.random())
                pos = "nml" if "scout" in c.get("kw", []) else ("trench" if len(self.at(lane, me, "trench")) < 2 else "rear")
                if pos == "rear" and len(self.at(lane, me, "rear")) >= 2:
                    continue
                u = U(c, me)
                u.lane, u.pos = lane, pos
                self.units.append(u)
                if "digger" in u.kw and (lane, me) not in self.forts:
                    self.forts[(lane, me)] = {"id": "trench"}
            elif c["id"] == "porter":
                if P["porters"] >= 3:
                    continue
                P["porters"] += 1
            elif c["id"] in ("trench", "palisade", "nest", "tower", "wire"):
                free = [l for l in range(3) if (l, me) not in self.forts]
                if not free:
                    continue
                l = max(free, key=lambda l: len(self.at(l, me, "trench")))
                self.forts[(l, me)] = {"id": c["id"], "hp": c.get("hp", 4), "atk": c.get("atk", 0)}
            elif c["id"] == "barrage":
                l = max(range(3), key=lambda l: len(self.at(l, 1 - me, "trench")))
                if not self.at(l, 1 - me, "trench"):
                    continue
                for t in self.at(l, 1 - me, "trench"):
                    t.hp -= 2
            elif c["id"] == "gas":
                l = max(range(3), key=lambda l: len(self.at(l, 1 - me, "trench") + self.at(l, 1 - me, "nml")) - len(self.at(l, me, "trench") + self.at(l, me, "nml")))
                for t in [x for x in self.units if x.lane == l and x.hp > 0 and "gas_mask" not in x.kw]:
                    t.hp -= 1
            elif c["id"] == "hospital":
                hurt = [x for x in self.units if x.owner == me and 0 < x.hp < x.c["hp"]]
                if not hurt:
                    continue
                t = max(hurt, key=lambda x: x.c["hp"] - x.hp)
                t.hp = min(t.c["hp"], t.hp + 4)
            elif c["id"] == "raid":
                us = [x for x in self.units if x.owner == me and x.hp > 0 and x.pos == "trench"]
                if not us:
                    continue
                u = max(us, key=lambda x: x.c["atk"])
                u.pos = "nml"
                self.attack(u)
            elif c["id"] == "recon":
                for _ in range(2):
                    if P["deck"]:
                        P["hand"].append(P["deck"].pop())
            elif c["id"] == "train":
                avail += 4
            elif c["id"] == "volley":
                continue
            else:
                continue
            avail -= c["cost"]
            P["hand"].remove(c)
        P["bank"] = min(3, max(0, avail))

    def step(self, me):
        P = self.p[me]
        if self.nml_ctrl(me) == 3:
            return "გარღვევა"
        for u in [x for x in self.units if x.owner == me and x.hp > 0]:
            if u.burn:
                u.hp -= 1
                u.burn = False
            if "regen" in u.kw and u.hp > 0:
                u.hp = min(u.c["hp"], u.hp + 1)
        if P["deck"]:
            P["hand"].append(P["deck"].pop())
        else:
            P["hq"] -= 2
        self.play(me)
        for u in [x for x in self.units if x.owner == me and x.hp > 0]:
            if u.sup:
                u.sup = False
                continue
            if not u.ready:          # ახლა ჩამოვიდა
                u.ready = True
                continue
            if self.targets(u) or u.pos == "nml":
                self.attack(u)
            elif u.pos != "nml":      # სამიზნე არ არის — წინ
                nxt = POS[POS.index(u.pos) + 1]
                if nxt != "trench" or len(self.at(u.lane, me, "trench")) < 2:
                    u.pos = nxt
        for (l, o), f in self.forts.items():
            if o == me and f.get("atk"):
                ts = self.at(l, 1 - me, "nml") + self.at(l, 1 - me, "trench")
                if ts:
                    t = min(ts, key=lambda x: x.hp)
                    t.hp -= f["atk"]
                    if f["id"] == "nest" and "fearless" not in t.kw:
                        t.sup = True
        for u in [x for x in self.units if x.owner == me and x.hp > 0 and "healer" in x.kw]:
            hurt = [x for x in self.units if x.owner == me and x.lane == u.lane and 0 < x.hp < x.c["hp"]]
            if hurt:
                t = min(hurt, key=lambda x: x.hp)
                t.hp = min(t.c["hp"], t.hp + 2)
        self.units = [u for u in self.units if u.hp > 0]
        if self.p[1 - me]["hq"] <= 0:
            return "შტაბი"
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=2000)
    args = ap.parse_args()
    d = json.loads((ROOT / "data" / "cardgame.json").read_text(encoding="utf-8"))
    cards = {c["id"]: c for c in d["units"]}
    common = {c["id"]: c for c in d["common"]}
    fids = list(d["starter"])
    rng = random.Random(7)
    wins, turns, how = {f: 0 for f in fids}, [], {}
    for g in range(args.games):
        order = fids if g % 2 == 0 else fids[::-1]
        game = Game([build(d["starter"][f], cards, common) for f in order], rng)
        res = None
        for t in range(60):
            me = t % 2
            res = game.step(me)
            if res:
                wins[order[me]] += 1
                how[res] = how.get(res, 0) + 1
                turns.append(t + 1)
                break
        else:
            turns.append(60)
            how["ფრე"] = how.get("ფრე", 0) + 1
    n = args.games
    print(f"თამაშები: {n} · საშუალო სვლა: {sum(turns) / n:.1f} · " + ", ".join(f"{k}: {v}" for k, v in how.items()))
    for f in fids:
        print(f"  {f}: {wins[f] / n * 100:.1f}%")


if __name__ == "__main__":
    main()
