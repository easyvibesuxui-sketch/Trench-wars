#!/usr/bin/env python3
"""ვიკი: ყველა მონაცემი და ტექსტი → wiki/data.js (+ wiki/art/ ილუსტრაციების მსუბუქი ასლები). გვერდი — wiki/index.html.

წყაროები: data/units.json, data/costs.json, data/abilities.json, data/roles.json, data/economy.json, data/visuals.json,
data/cardgame.json, lore/*.md (ფრაქციები, მოკავშირეები, ცალკე ომები, ამბები), units/*.md (იუნიტების აღწერა), campaigns/*.md,
rules/abilities.md (ნიშნების სახელები), assets/art/*.jpg.

გაშვება:  python3 tools/build_wiki.py   (საჭიროა: pip install markdown pillow)
"""
import json
import re
from pathlib import Path

try:
    import markdown
except ImportError:  # pragma: no cover
    raise SystemExit("საჭიროა markdown: pip install markdown")
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "wiki"
LIGHT_CORE, DARK_CORE = ["colchis", "iberia", "ring"], ["hell", "harness", "kajeti", "listeners"]
UNIT_FILES = {"colchis": "colchis.md", "iberia": "iberia.md", "hell": "hell-legions.md", "harness": "grand-harness.md",
              "kajeti": "kajeti.md", "listeners": "listeners.md", "ring": "ring.md"}
STORY_FILES = {"01-colchis.md": "colchis", "02-iberia.md": "iberia", "03-hell-legions.md": "hell", "04-grand-harness.md": "harness",
               "09-arctic.md": "arctic", "10-siberia.md": "siberia", "11-balkans.md": "balkans", "12-pyrenean.md": "pyrenean",
               "13-alps.md": "alps", "14-baltic.md": "baltic", "15-australia.md": "australia"}
LORE_PAGES = ["01-general-lore", "02-chronology", "03-named-battles", "05-characters", "07-gods", "11-sacrifices"]
TIER_NAME = {"I": "ქვეითი", "II": "ელიტა", "III": "ჯავშნიანი", "IV": "გროტესკული", "IV+": "დიდი გროტესკული", "V": "გოლიათი", "hero": "გმირი"}


def md(text):
    text = re.sub(r"\]\((?!https?:)[^)]*\)", "]()", text)   # რეპოს შიდა ბმულები ვიკიში არ მუშაობს
    text = re.sub(r"(?m)^  ([-*] )", r"    \1", text)                     # ჩადგმული სია: python-markdown 4 ჰარს ელის
    text = re.sub(r"(?m)^((?![ \t]*[-*] |[ \t]*\d+\. |\|).+)\n([-*] |\d+\. )", r"\1\n\n\2", text)   # სიის წინ ცარიელი ხაზი
    html = markdown.markdown(text, extensions=["tables", "sane_lists"])
    return html.replace('<a href="">', "<span>").replace("</a>", "</span>") if '<a href="">' in html else html


def sections(text, level):
    """'## სათაური' → {სათაური: ტექსტი} (მომდევნო იმავე ან უფრო მაღალ სათაურამდე)."""
    out, cur, buf = {}, None, []
    pat = re.compile(r"^(#{1,%d}) (.+)$" % level)
    for line in text.split("\n"):
        m = pat.match(line)
        if m:
            if cur:
                out[cur] = "\n".join(buf).strip()
            cur = m.group(2).strip() if len(m.group(1)) == level else None
            buf = []
        elif cur:
            buf.append(line)
    if cur:
        out[cur] = "\n".join(buf).strip()
    return out


def clean(h):
    h = re.sub(r"\*\(.*?\)\*", "", h)
    h = re.sub(r"^\d+\.\s*", "", h)
    return h.strip(" *")


def match(name, heading):
    h = clean(heading)
    return h == name or h.startswith(name + " —") or h.startswith(name + " (") or h.split(" — ")[-1].strip() == name


def main():
    data = json.loads((ROOT / "data/units.json").read_text(encoding="utf-8"))
    costs = json.loads((ROOT / "data/costs.json").read_text(encoding="utf-8"))
    abil = json.loads((ROOT / "data/abilities.json").read_text(encoding="utf-8"))
    roles = {r["id"]: r for r in json.loads((ROOT / "data/roles.json").read_text(encoding="utf-8"))["roles"]}
    econ = json.loads((ROOT / "data/economy.json").read_text(encoding="utf-8")).get("factions", {})
    vis = json.loads((ROOT / "data/visuals.json").read_text(encoding="utf-8"))
    cg = {c["id"]: c for c in json.loads((ROOT / "data/cardgame.json").read_text(encoding="utf-8"))["units"]}
    names = {**data["factions"], **data["allies"]}
    tagname = dict((m.group(2), m.group(1)) for m in re.finditer(r"- \*\*(.+?)\*\* \(`([a-z_]+)`\)", (ROOT / "rules/abilities.md").read_text(encoding="utf-8")))

    lore = {p.stem: p.read_text(encoding="utf-8") for p in (ROOT / "lore").glob("*.md")}
    fac_md = {}
    for src, lvl in (("04-factions", 2), ("06-european-allies", 3), ("08-southern-eastern-allies", 2)):
        for h, body in sections(lore[src], lvl).items():
            for fid, nm in names.items():
                if match(nm, h) and fid not in fac_md:
                    fac_md[fid] = body
    wars = {}
    for h, body in sections(lore["09-separate-wars"], 2).items():
        for fid, nm in names.items():
            if match(nm, h):
                wars[fid] = (clean(h).split(" — ")[0], body)
    stories = {}
    for p in sorted((ROOT / "lore/10-stories").glob("*.md")):
        if p.name == "README.md":
            continue
        t = p.read_text(encoding="utf-8")
        if p.name in STORY_FILES:
            stories.setdefault(STORY_FILES[p.name], []).append(t.split("\n", 1)[1] if t.startswith("#") else t)
            continue
        for h, body in sections(t, 2).items():
            for fid, nm in names.items():
                if match(nm, h):
                    stories.setdefault(fid, []).append(body)

    udesc = {}
    for fid, fn in UNIT_FILES.items():
        secs = sections((ROOT / "units" / fn).read_text(encoding="utf-8"), 3)
        for u in data["units"]:
            if u["faction"] == fid:
                for h, body in secs.items():
                    if clean(h) == u["name"] or clean(h).endswith(u["name"]):
                        udesc[u["id"]] = body
    allies_md = (ROOT / "units/allies.md").read_text(encoding="utf-8")
    for m in re.finditer(r"^- \*\*(.+?)\*\*(?: \((.+?)\))? — (.+(?:\n  .+)*)", allies_md, re.M):
        for u in data["units"]:
            if u["name"] == m.group(1) and u["id"] not in udesc and (not m.group(2) or m.group(2) == u["tier"] or m.group(2) in names.get(u["faction"], "")):
                udesc[u["id"]] = m.group(3).replace("\n  ", " ")

    art_dir = OUT / "art"
    art_dir.mkdir(parents=True, exist_ok=True)
    arts = set()
    for p in (ROOT / "assets/art").glob("*.jpg"):
        dst = art_dir / p.name
        if not dst.exists() or dst.stat().st_mtime < p.stat().st_mtime:
            Image.open(p).convert("RGB").resize((480, 720), Image.LANCZOS).save(dst, quality=78, optimize=True)
        arts.add(p.stem)

    side = lambda f: "light" if f in LIGHT_CORE or f in data["allies"] else "dark"
    W = {"factions": [], "units": [], "lore": [], "tiers": TIER_NAME,
         "roles": {k: {"name": r["name"], "icon": r.get("icon", ""), "does": r.get("does", "")} for k, r in roles.items()}}
    for fid, nm in names.items():
        e = econ.get(fid, {})
        arch = {k: e.get(k) for k in ("vernacular", "history", "house", "great", "unique", "bonus") if e.get(k)}
        dfn = e.get("defense") or {}
        camp = ROOT / "campaigns" / f"{fid}.md"
        W["factions"].append({
            "id": fid, "name": nm, "side": side(fid), "core": fid in data["factions"],
            "lore": md(fac_md[fid]) if fid in fac_md else "",
            "war": {"title": wars[fid][0], "html": md(wars[fid][1])} if fid in wars else None,
            "stories": md("\n\n".join(stories.get(fid, []))) if stories.get(fid) else "",
            "campaign": md(camp.read_text(encoding="utf-8").split("\n", 1)[1]) if camp.exists() else "",
            "arch": {k: md(v) for k, v in arch.items()}, "defense": {k: md(v) for k, v in dfn.items() if isinstance(v, str)},
            "visual": vis["factions"].get(fid), "art": f"art/{next((u['id'] for u in data['units'] if u['faction'] == fid and u['id'] in arts), '')}.jpg"
                      if any(u["faction"] == fid and u["id"] in arts for u in data["units"]) else None,
        })
    for u in data["units"]:
        c = cg.get(u["id"])
        W["units"].append({
            "id": u["id"], "f": u["faction"], "name": u["name"], "tier": u["tier"], "size": u.get("size", 1),
            "st": [u["move"], u["shoot"], u["melee"], u["armor"], u["wounds"], u["nerve"]], "cost": costs.get(u["id"], u.get("cost")),
            "role": u.get("role"), "weapons": u["weapons"], "tags": [[t, tagname.get(t, t), abil["tags"].get(t, "")] for t in u["tags"]],
            "abil": abil["units"].get(u["id"], []), "desc": md(udesc[u["id"]]) if u["id"] in udesc else "",
            "visual": vis["units"].get(u["id"], ""), "art": f"art/{u['id']}.jpg" if u["id"] in arts else None,
            "card": {"cost": c["cost"], "atk": c["atk"], "hp": c["hp"]} if c else None,
        })
    for key in LORE_PAGES:
        t = lore[key]
        title = t.split("\n", 1)[0].lstrip("# ").strip()
        W["lore"].append({"id": key, "title": title, "html": md(t.split("\n", 1)[1])})
    W["visual"] = vis["direction"]
    (OUT / "data.js").write_text("window.WIKI = " + json.dumps(W, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    n_desc = sum(1 for u in W["units"] if u["desc"])
    print(f"wiki/data.js: {len(W['factions'])} ფრაქცია ({len(fac_md)} ლორით, {len(wars)} ომით, {len(stories)} ამბებით) · "
          f"{len(W['units'])} იუნიტი ({n_desc} აღწერით, {len(arts)} სურათი) · {len(W['lore'])} ლორის გვერდი")


if __name__ == "__main__":
    main()
