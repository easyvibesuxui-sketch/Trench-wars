#!/usr/bin/env python3
"""ინგლისური ტექსტების ფენა (აღწერები, წესები, ლორი). სახელები — data/names_en.json.

თარგმანები ინახება data/text_en/<ჯგუფი>.json-ში: {გასაღები: {"h": ქართული წყაროს ჰეში, "en": თარგმანი}}.
თუ ქართული წყარო შეიცვალა, ჰეში აღარ ემთხვევა და თარგმანი „მოძველებულია“ (validate.py აფრთხილებს).

    python3 tools/i18n_en.py status                     # რამდენია თარგმნილი, რა აკლია, რა მოძველდა
    python3 tools/i18n_en.py dump units --max 30000     # სათარგმნი ქართული ტექსტი (=== გასაღები / ტექსტი)
    python3 tools/i18n_en.py load file.txt               # თარგმანის შეტანა იმავე ფორმატით

წყვილი მნიშვნელობები (ძალა, ომი, ლორის გვერდი, საერთო წესი) ორ ნაწილადაა: პირველი ხაზი — სახელი/სათაური, დანარჩენი — ტექსტი.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "text_en"
GROUPS = ["rules", "units", "factions", "lore", "wars", "stories", "campaigns", "visuals"]


def _h(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]


def sources():
    """გასაღები → (ჯგუფი, ქართული ტექსტი)."""
    sys.path.insert(0, str(ROOT / "tools"))
    from build_wiki import extract
    X = extract()
    out = {}
    for k, v in X["abil"]["tags"].items():
        out[f"tag:{k}"] = ("rules", v)
    for k, v in X["abil"]["common"].items():
        out[f"common:{k}"] = ("rules", f"{k}\n{v}")
    for uid, lst in X["abil"]["units"].items():
        for i, (n, t) in enumerate(lst):
            out[f"abil:{uid}#{i}"] = ("rules", f"{n}\n{t}")
    for k, r in X["roles"].items():
        if r.get("does"):
            out[f"role:{k}"] = ("rules", r["does"])
    for u in X["data"]["units"]:
        if u["id"] in X["udesc"]:
            out[f"udesc:{u['id']}"] = ("units", X["udesc"][u["id"]])
    for fid in X["names"]:
        if fid in X["fac_md"]:
            out[f"flore:{fid}"] = ("factions", X["fac_md"][fid])
        e = X["econ"].get(fid, {})
        for k in ("vernacular", "history", "house", "great", "unique", "bonus"):
            if e.get(k):
                out[f"farch:{fid}:{k}"] = ("factions", e[k])
        for k, v in (e.get("defense") or {}).items():
            if isinstance(v, str):
                out[f"fdef:{fid}:{k}"] = ("factions", v)
        if fid in X["wars"]:
            out[f"war:{fid}"] = ("wars", f"{X['wars'][fid][0]}\n{X['wars'][fid][1]}")
        if X["stories"].get(fid):
            out[f"story:{fid}"] = ("stories", X["stories"][fid])
        if fid in X["camps"]:
            out[f"camp:{fid}"] = ("campaigns", X["camps"][fid])
    for key, (title, body) in X["lore_pages"].items():
        out[f"lore:{key}"] = ("lore", f"{title}\n{body}")
    for k in ("medium", "not_tc"):
        out[f"dir:{k}"] = ("visuals", X["vis"]["direction"][k])
    for fid, v in X["vis"]["factions"].items():
        if fid not in X["names"]:
            continue
        for k in ("materials", "silhouette", "emblem", "avoid"):
            if v.get(k):
                out[f"fvis:{fid}:{k}"] = ("visuals", v[k])
        out[f"fvis:{fid}:palette"] = ("visuals", " | ".join(n for _, n in v["palette"]))
    for uid, v in X["vis"]["units"].items():
        if v:
            out[f"vis:{uid}"] = ("visuals", v)
    return out


def load_store():
    st = {}
    for g in GROUPS:
        p = STORE / f"{g}.json"
        if p.exists():
            st.update(json.loads(p.read_text(encoding="utf-8")))
    return st


def save_store(st, src):
    STORE.mkdir(parents=True, exist_ok=True)
    order = {k: i for i, k in enumerate(src)}
    for g in GROUPS:
        part = {k: st[k] for k in sorted(st, key=lambda k: order.get(k, 1e9)) if (src.get(k, (None,))[0] or k.split(":")[0]) == g}
        if part:
            (STORE / f"{g}.json").write_text(json.dumps(part, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def status(src=None, st=None):
    src = src or sources()
    st = st if st is not None else load_store()
    rep = {}
    for k, (g, ka) in src.items():
        r = rep.setdefault(g, {"total": 0, "done": 0, "stale": 0, "ka_chars": 0, "todo_chars": 0})
        r["total"] += 1
        r["ka_chars"] += len(ka)
        if k in st:
            r["done"] += 1
            if st[k]["h"] != _h(ka):
                r["stale"] += 1
        else:
            r["todo_chars"] += len(ka)
    orphans = [k for k in st if k not in src]
    return rep, orphans


def en_texts():
    """გასაღები → ინგლისური ტექსტი (მოძველებულიც შედის — ქართულზე უკეთესია ინგლისელი მკითხველისთვის)."""
    return {k: v["en"] for k, v in load_store().items()}


def split2(s):
    a, _, b = s.partition("\n")
    return a.strip(), b.strip()


def main(argv):
    cmd = argv[0] if argv else "status"
    if cmd == "status":
        rep, orphans = status()
        for g in GROUPS:
            if g in rep:
                r = rep[g]
                print(f"{g:10} {r['done']:4}/{r['total']:<4} მოძველებული: {r['stale']:<3} დარჩა: {r['todo_chars']:>7} სიმბოლო")
        if orphans:
            print("ზედმეტი გასაღებები:", ", ".join(orphans[:20]))
    elif cmd == "dump":
        group = argv[1]
        mx = int(argv[argv.index("--max") + 1]) if "--max" in argv else 10 ** 9
        src, st = sources(), load_store()
        n, buf = 0, []
        for k, (g, ka) in src.items():
            if g != group or (k in st and st[k]["h"] == _h(ka)):
                continue
            if buf and n + len(ka) > mx:
                break
            buf.append(f"=== {k}\n{ka}\n")
            n += len(ka)
        sys.stdout.write("\n".join(buf))
    elif cmd == "load":
        src, st = sources(), load_store()
        text = Path(argv[1]).read_text(encoding="utf-8")
        added, bad = 0, []
        for block in text.split("\n=== ")[0:]:
            block = block[4:] if block.startswith("=== ") else block
            key, _, body = block.partition("\n")
            key, body = key.strip(), body.strip()
            if not key:
                continue
            if key not in src:
                bad.append(key)
                continue
            st[key] = {"h": _h(src[key][1]), "en": body}
            added += 1
        save_store(st, src)
        print(f"შეტანილია: {added}" + (f" · უცნობი გასაღები: {', '.join(bad)}" if bad else ""))
        if bad:
            sys.exit(1)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
