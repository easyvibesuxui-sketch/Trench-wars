#!/usr/bin/env python3
"""ვიზუალური მიმართულება: tools/visuals_data.py + data/units.json → data/visuals.json, docs/visual-guide.md, playtest/visual-guide.html

ყოველ იუნიტს ეწერება მოკლე ვიზუალური აღწერა (მხატვრისთვის): ზომა დონით, პოზა როლით, იარაღი, ნიშნების ვიზუალური ნიშნები,
ფრაქციის ფერები და მასალა. ხელით დაზუსტებული აღწერა — units.json-ის `visual` ველი (თუ არის, ავტომატურს ანაცვლებს).

გაშვება:  python3 tools/build_visuals.py
"""
import html
import json
from pathlib import Path

import visuals_data as V

ROOT = Path(__file__).resolve().parent.parent
HEADER = "<!-- ავტომატურად გენერირებული: tools/build_visuals.py — შეცვალე tools/visuals_data.py -->\n"

SCALE = {"I": "ადამიანის ზომა", "II": "ადამიანის ზომა, გამორჩეული თავსაბურავით ან მოსასხამით", "III": "მასიური, ჯავშნიანი (~1,2×)",
         "IV": "დიდი მანქანა ან არსება (2–3×)", "IV+": "მავალი ნაგებობა", "V": "გოლიათი — სახლებზე მაღალი", "hero": "სახელიანი გმირი, უნიკალური სახით"}
POSE = {
    "command": "წინ დგას, ხელით მიუთითებს, დროშა ან სასიგნალო საყვირი", "line": "მწკრივში, შაშხანა მხარზე ან ხიშტით წინ",
    "assault": "გაქცევაში, დახრილი, ხელჩართული იარაღი მაღლა", "marksman": "მუხლზე, დამიზნებული", "sniper": "წოლით, შენიღბული, ოპტიკით",
    "scout": "მსუბუქად აღჭურვილი, მოხრილი, ჭოგრიტით", "heavy_weapons": "ორი კაცი — მძიმე იარაღი სადგამზე", "artillery": "ზარბაზანი ან ნაღმმტყორცნი ეკიპაჟით",
    "engineer": "ნიჩაბი/ქანჩის გასაღები, ზურგზე ხელსაწყოები", "support": "ჩანთა, ფლაკონები ან ინსტრუმენტი, ზურგი თანაგუნდელებისკენ",
    "disruptor": "ჩრდილში, სახე დაფარული, ხელში საიდუმლო ნივთი", "heavy_infantry": "ფართო დგომა, ფარი ან ფირფიტები წინ",
    "cavalry": "ცხენზე (ან ფრაქციის სამხედრო ცხოველზე), იერიშში", "flyer": "ჰაერში, ფრთები ან ორთქლის ძრავა", "hunter": "დიდი იარაღი ზემოთ — გოლიათზე ან ურჩხულზე დამიზნებული",
    "armor": "მანქანა/ცოცხალი ტანკი, მძღოლი ან მწყემსი ახლოს", "monster": "ურჩხული, თავისი მითის ფორმით", "giant": "გოლიათი, მის ფეხთან ჯარისკაცები მასშტაბისთვის",
}
TAG_LOOK = {
    "gas_mask": "აირწინაღი", "steam": "ორთქლის ქვაბი/მილები", "shield": "ფარი", "shield_wall": "დიდი ფარი", "fly": "ფრთები", "cavalry": "მხედარი",
    "engineer": "ხელსაწყოები", "digger": "ნიჩაბი", "tunnel": "მაღაროს ფარანი", "scout": "მსუბუქი აღჭურვილობა", "infiltrate": "შენიღბვა",
    "climber": "კაუჭი და თოკი", "giant_hunter": "ჰარპუნი ან დიდი შაშხანა", "monster_hunter": "ხაფანგები და თოკები", "anti_air": "ზემოთ მიმართული ლულა",
    "trench_breaker": "მავთულის საჭრელი", "construct": "ნაჭედი/მექანიკური სხეული", "automaton": "ავტომატის სახსრები", "healer": "სახვევები და ფლაკონები",
    "alchemist": "კოლბები", "artillery": "ზარბაზანი", "fire_guard": "ხანძრის ჩაფხუტი და შლანგი", "song": "მუსიკალური ინსტრუმენტი", "orders": "სასიგნალო დროშა",
    "river": "ნავი ან წყალგაუმტარი ტანსაცმელი", "landing": "ნავის ბაქანი", "winter_born": "ბეწვი", "ice_runner": "ციგურები/თხილამურები", "mountain": "მთის აღჭურვილობა",
    "messenger": "ჩანთა და საყვირი", "rail": "რკინიგზის ბორბლები", "beacon": "ფარანი/სასიგნალო ცეცხლი", "torch": "ჩირაღდანი", "regen": "შეხორცებადი კანი",
    "repair": "ქანჩის გასაღები", "night_sight": "ღამის სათვალე", "huge": "დიდი სილუეტი", "leader": "წოდების ნიშანი",
}
W_LOOK = {"fire": "ცეცხლსაფრქვევი", "suppress": "ტყვიამფრქვევი", "lightning": "ელვის ხვია", "poison": "შხამიანი ფლაკონები", "chain": "ჯაჭვი", "volley": "ზალპის შაშხანა",
          "demolition": "ასაფეთქებელი", "indirect": "ნაღმმტყორცნი", "anti_giant": "გოლიათის საწინააღმდეგო იარაღი"}


# ინგლისური ვერსია (KA/EN გადამრთველისთვის) — იგივე შაბლონი; იარაღი names_en.json-იდან, ფერები და TC შენიშვნა data/text_en/-იდან
SCALE_EN = {"I": "human-sized", "II": "human-sized, with a distinctive headdress or cloak", "III": "massive, armoured (~1.2×)",
            "IV": "large machine or creature (2–3×)", "IV+": "walking structure", "V": "giant — taller than houses", "hero": "named hero, with a unique face"}
POSE_EN = {
    "command": "stands in front, pointing, with a flag or signal horn", "line": "in a rank, rifle on the shoulder or bayonet forward",
    "assault": "running, crouched, melee weapon raised", "marksman": "kneeling, taking aim", "sniper": "lying prone, camouflaged, with a scope",
    "scout": "lightly equipped, crouching, with field glasses", "heavy_weapons": "two-man crew — heavy weapon on a mount", "artillery": "gun or mortar with crew",
    "engineer": "shovel/spanner, tools on the back", "support": "satchel, vials or instrument, back toward teammates",
    "disruptor": "in shadow, face covered, a secret object in hand", "heavy_infantry": "wide stance, shield or plates forward",
    "cavalry": "mounted (horse or the faction's war beast), charging", "flyer": "airborne, wings or a steam engine", "hunter": "big weapon pointed up — aimed at a giant or monster",
    "armor": "machine/living tank, driver or herder nearby", "monster": "a monster, in its myth's own form", "giant": "a giant, soldiers at its feet for scale",
}
TAG_LOOK_EN = {
    "gas_mask": "gas mask", "steam": "steam boiler/pipes", "shield": "shield", "shield_wall": "large shield", "fly": "wings", "cavalry": "rider",
    "engineer": "tools", "digger": "shovel", "tunnel": "miner's lamp", "scout": "light kit", "infiltrate": "camouflage",
    "climber": "hook and rope", "giant_hunter": "harpoon or big rifle", "monster_hunter": "traps and ropes", "anti_air": "barrel pointed upward",
    "trench_breaker": "wire cutters", "construct": "forged/mechanical body", "automaton": "automaton joints", "healer": "bandages and vials",
    "alchemist": "flasks", "artillery": "cannon", "fire_guard": "fire helmet and hose", "song": "musical instrument", "orders": "signal flag",
    "river": "boat or waterproof clothing", "landing": "boat ramp", "winter_born": "fur", "ice_runner": "skates/skis", "mountain": "mountain gear",
    "messenger": "satchel and horn", "rail": "rail wheels", "beacon": "lantern/signal fire", "torch": "torch", "regen": "self-healing hide",
    "repair": "spanner", "night_sight": "night goggles", "huge": "large silhouette", "leader": "rank badge",
}
W_LOOK_EN = {"fire": "flamethrower", "suppress": "machine gun", "lightning": "lightning coil", "poison": "poison vials", "chain": "chain", "volley": "volley rifle",
             "demolition": "explosives", "indirect": "mortar", "anti_giant": "anti-giant weapon"}


def _looks(u, tags, wlook):
    looks = [tags[t] for t in u["tags"] if t in tags and t not in ("huge", "leader")]
    looks += [wlook[t] for w in u["weapons"] for t in w["tags"] if t in wlook]
    return list(dict.fromkeys(looks))


def brief_en(u, wnames, palette, tc_note=None):
    """ინგლისური ვიზუალური აღწერა. wnames: {ქართული იარაღი: English}; palette: ინგლისური ფერების სია; tc_note: ნათარგმნი TC შენიშვნა."""
    looks = _looks(u, TAG_LOOK_EN, W_LOOK_EN)
    weapons = ", ".join(wnames.get(w["name"], w["name"]) for w in u["weapons"]) or "—"
    parts = [SCALE_EN.get(u["tier"], ""), POSE_EN.get(u.get("role"), ""), f"weapons: {weapons}"]
    if looks:
        parts.append("marks: " + ", ".join(looks[:5]))
    parts.append("colours: " + ", ".join(palette))
    if tc_note:
        parts.append("⚠️ Difference from TC: " + tc_note)
    return " · ".join(p for p in parts if p)


def brief(u, f):
    if u.get("visual"):
        return u["visual"]
    looks = [TAG_LOOK[t] for t in u["tags"] if t in TAG_LOOK and t not in ("huge", "leader")]
    looks += [W_LOOK[t] for w in u["weapons"] for t in w["tags"] if t in W_LOOK]
    seen, uniq = set(), []
    for x in looks:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    weapons = ", ".join(w["name"] for w in u["weapons"]) or "—"
    pal = ", ".join(n for _, n in f["palette"])
    parts = [SCALE.get(u["tier"], ""), POSE.get(u.get("role"), ""), f"იარაღი: {weapons}"]
    if uniq:
        parts.append("ნიშნები: " + ", ".join(uniq[:5]))
    parts.append(f"ფერები: {pal}")
    if u["id"] in V.TC_NOTES:
        parts.append("⚠️ TC-ისგან განსხვავება: " + V.TC_NOTES[u["id"]])
    return " · ".join(p for p in parts if p)


def main():
    data = json.loads((ROOT / "data" / "units.json").read_text(encoding="utf-8"))
    names = {**data["factions"], **data["allies"]}
    out = {"direction": V.DIRECTION, "factions": V.F, "tc_notes": V.TC_NOTES,
           "units": {u["id"]: brief(u, V.F[u["faction"]]) for u in data["units"]}}
    (ROOT / "data" / "visuals.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    d = V.DIRECTION
    md = [HEADER, "# ვიზუალური მიმართულება — იუნიტები და ფრაქციები", "",
          "> მხატვრებისთვის, მინიატურების სკულპტორებისთვის და ციფრული თამაშისთვის. ფერადი ვერსია — `playtest/visual-guide.html`.", "",
          "## საერთო პრინციპები", "", f"- **სტილი:** {d['medium']}", f"- **Trench Crusade-ისგან განსხვავება:** {d['not_tc']}",
          f"- **სილუეტი:** {d['silhouette']}", f"- **სისასტიკე:** {d['gore']}", f"- **კონსულტანტები:** {d['advisors']}", "",
          "**დონეები ვიზუალურად:**", ""] + [f"- **{k}** — {v}" for k, v in d["tiers"].items()] + ["", "**არასოდეს:**", ""] + [f"- {x}" for x in d["never"]] + [""]
    md += ["## TC-სთან მგრძნობიარე იუნიტები", "", "> შედარება ოფიციალურ „Warbands of Trench Crusade“-თან (2026 წლის სექტემბრის ვერსია).", ""]
    byid = {u["id"]: u for u in data["units"]}
    md += [f"- **{byid[k]['name']}** — {v}" for k, v in V.TC_NOTES.items()] + [""]
    for fid in list(data["factions"]) + list(data["allies"]):
        f = V.F[fid]
        md += [f"## {names[fid]}", "",
               f"- **ფერები:** " + " · ".join(f"{n} `{h}`" for h, n in f["palette"]),
               f"- **მასალა:** {f['materials']}", f"- **სილუეტი:** {f['silhouette']}", f"- **ემბლემა:** {f['emblem']}", f"- **არ ვიყენებთ:** {f['avoid']}", "",
               "| იუნიტი | დონე | ვიზუალი |", "|---|---|---|"]
        md += [f"| {u['name']} | {u['tier']} | {out['units'][u['id']].replace('|', '/')} |" for u in data["units"] if u["faction"] == fid] + [""]
    (ROOT / "docs" / "visual-guide.md").write_text("\n".join(md), encoding="utf-8")

    e = html.escape
    secs = []
    for fid in list(data["factions"]) + list(data["allies"]):
        f = V.F[fid]
        sw = "".join(f'<span class="sw"><i style="background:{h}"></i>{e(n)} <code>{h}</code></span>' for h, n in f["palette"])
        units = "".join(f"<li><b>{e(u['name'])}</b> <small>{u['tier']}</small> — {e(out['units'][u['id']])}</li>" for u in data["units"] if u["faction"] == fid)
        secs.append(f"<section><h2>{e(names[fid])}</h2><p class=pal>{sw}</p><p><b>მასალა:</b> {e(f['materials'])}<br><b>სილუეტი:</b> {e(f['silhouette'])}<br>"
                    f"<b>ემბლემა:</b> {e(f['emblem'])}<br><b>არ ვიყენებთ:</b> {e(f['avoid'])}</p><details><summary>იუნიტები</summary><ul>{units}</ul></details></section>")
    never = "".join(f"<li>{e(x)}</li>" for x in d["never"])
    page = f"""<!doctype html><html lang="ka"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ქვესკნელის ფრონტის ვიზუალი</title><style>
:root{{--bg:#f4efe3;--ink:#2a241d;--muted:#6b5f4d;--line:#d8cdb6}}
@media (prefers-color-scheme: dark){{:root{{--bg:#2a241d;--ink:#f1e8d6;--muted:#b7a98f;--line:#4d4234}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "Noto Sans Georgian","DejaVu Sans",sans-serif;padding:16px;max-width:980px;margin-inline:auto}}
h1,h2{{font-family:"Noto Serif Georgian","DejaVu Serif",serif}} section{{border-top:1px solid var(--line);padding:8px 0}}
.pal{{display:flex;flex-wrap:wrap;gap:10px}} .sw{{display:inline-flex;align-items:center;gap:6px}} .sw i{{width:28px;height:28px;border-radius:4px;border:1px solid var(--line);display:inline-block}}
code{{color:var(--muted);font-size:.8em}} small{{color:var(--muted)}} li{{margin:4px 0}}
</style></head><body><h1>ქვესკნელის ფრონტი — ვიზუალური მიმართულება</h1>
<p><b>სტილი:</b> {e(d['medium'])}</p><p><b>Trench Crusade-ისგან განსხვავება:</b> {e(d['not_tc'])}</p><p><b>სილუეტი:</b> {e(d['silhouette'])}</p>
<details><summary><b>არასოდეს</b></summary><ul>{never}</ul></details>{''.join(secs)}</body></html>"""
    (ROOT / "playtest" / "visual-guide.html").write_text(page, encoding="utf-8")
    print(f"data/visuals.json · docs/visual-guide.md · playtest/visual-guide.html: {len(data['units'])} იუნიტი, {len(V.F)} ფრაქცია")


if __name__ == "__main__":
    main()
