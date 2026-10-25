#!/usr/bin/env python3
"""სცენარების ნაკრები: data/scenarios.json → rules/scenarios.md და playtest/scenarios.html (რუკებით)

გაშვება:  python3 tools/build_scenarios.py   PDF: NODE_PATH=$(npm root -g) node tools/print_playtest.js
"""
import html
import json
import re
from pathlib import Path

import build_playtest as P

ROOT = Path(__file__).resolve().parent.parent
HEADER = "<!-- ავტომატურად გენერირებული: tools/build_scenarios.py — შეცვალე data/scenarios.json -->\n"
e = html.escape
STYLE = {
    "dz": "background:repeating-linear-gradient(45deg,#e9e1d3,#e9e1d3 2mm,#f6f1e8 2mm,#f6f1e8 4mm);color:#5b5248",
    "trench": "background:#7b6a55", "wire": "border-top:2px dashed #7a1f1a", "ruin": "background:#d9cfbf;border:1px solid #1d1a16",
    "wall": "background:#55504a", "tower": "background:#3a3530;color:#fff;border-radius:1mm", "gate": "background:#8a5a1c;color:#fff",
    "moat": "background:#9cb6c9", "edge": "background:#1d1a16;color:#fff",
}
ROUND = {"obj": ("#fff", "#8a5a1c"), "search": ("#e8efe0", "#4c6a3a"), "cart": ("#efe4d0", "#1d1a16"), "monster": ("#f1d4cf", "#7a1f1a")}


def md(s):
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", e(s)))


def size(table):
    a, b = (int(x) for x in re.findall(r"(\d+)″", table)[:2])
    return a, b


def map_html(sc):
    w, h = size(sc["table"])
    scale = 110 / max(w, h)
    out = [f'<div class="map" style="width:{w * scale:.0f}mm;height:{h * scale:.0f}mm">']
    for el in sc["map"]:
        t, lab = el["type"], e(el.get("label", ""))
        if t in ROUND:
            bg, bd = ROUND[t]
            big = 14 if t == "monster" else 8
            out.append(f'<div style="left:{el["x"]}%;top:{el["y"]}%;width:{big}mm;height:{big}mm;border-radius:50%;background:{bg};'
                       f'border:1.5px solid {bd};font-weight:700;font-size:6pt">{lab}</div>')
        else:
            out.append(f'<div style="left:{el["x"]}%;top:{el["y"]}%;width:{el["w"]}%;height:{el["h"]}%;{STYLE[t]};font-size:6.5pt">{lab}</div>')
    out.append("</div>")
    return "".join(out)


def main():
    d = json.loads((ROOT / "data" / "scenarios.json").read_text(encoding="utf-8"))
    # Markdown
    out = [HEADER, "# სცენარების ნაკრები", "", "> ექვსი უნივერსალური სცენარი ნებისმიერი ფრაქციისთვის. ფრაქციის ომის კამპანიები — `../campaigns/`;",
           "> ნეიტრალური ზოლის ზონები, ძებნა და ღამის ცხრილი — `no-mans-land.md`; კედლები და თხრილები — `core-rules.md`, 7ბ.", "",
           f"**არჩევა:** {d['pick']}", ""]
    for i, sc in enumerate(d["scenarios"], 1):
        out += [f"## {i}. {sc['name']}", "", f"*{sc['story']}*", "",
                f"- **მოთამაშეები:** {sc['players']} · **ბიუჯეტი:** {sc['budget']} · **მაგიდა:** {sc['table']} · **რაუნდები:** {sc['rounds']}",
                f"- **ნეიტრალური ზოლის ზონა (რეკომენდაცია):** {sc['zone']}", "", "**მომზადება**", ""]
        out += [f"- {x}" for x in sc["setup"]] + ["", "**გამარჯვება**", ""] + [f"- {x}" for x in sc["victory"]]
        out += ["", "**სპეციალური წესები**", ""] + [f"- {x}" for x in sc["special"]] + [""]
    out += ["⚠️ არცერთ სცენარში მშვიდობიანი მოსახლეობა მიზანი არ არის: სოფლები ცარიელია, ურმები — ორთქლის მანქანები.", ""]
    (ROOT / "rules" / "scenarios.md").write_text("\n".join(out), encoding="utf-8")
    # HTML
    secs = [f'''<section class="page cover"><p class="muted">სცენარების ნაკრები · სატესტო ვერსია</p><h1>ექვსი ბრძოლა ნეიტრალურ ზოლში</h1>
<p class="lead">უნივერსალური სცენარები ნებისმიერი ფრაქციისთვის: გარღვევა, ღამის რეიდი, სიმაგრის დაცვა, ესკორტი, ურჩხულზე ნადირობა და ორი ალიანსი.</p>
<div class="box">{md(d["pick"])}</div><p class="small muted">წესები: მოკლე წესები (kit.pdf), ნეიტრალური ზოლის ცხრილები, ნიშნების ლექსიკონი (cards-all.pdf).</p></section>''']
    for i, sc in enumerate(d["scenarios"], 1):
        li = lambda xs: "<ul>" + "".join(f"<li>{md(x)}</li>" for x in xs) + "</ul>"
        secs.append(f'''<section class="page"><h2>{i}. {e(sc["name"])}</h2><p><i>{e(sc["story"])}</i></p>
<p class="small"><b>მოთამაშეები:</b> {e(sc["players"])} · <b>ბიუჯეტი:</b> {e(sc["budget"])} · <b>მაგიდა:</b> {e(sc["table"])} · <b>რაუნდები:</b> {sc["rounds"]} ·
<b>ზონა:</b> {e(sc["zone"])}</p>{map_html(sc)}<div class="cols small"><h3>მომზადება</h3>{li(sc["setup"])}<h3>გამარჯვება</h3>{li(sc["victory"])}
<h3>სპეციალური წესები</h3>{li(sc["special"])}</div></section>''')
    (ROOT / "playtest" / "scenarios.html").write_text(P.doc("სცენარების ნაკრები", "".join(secs)), encoding="utf-8")
    print(f"rules/scenarios.md · playtest/scenarios.html: {len(d['scenarios'])} სცენარი")


if __name__ == "__main__":
    main()
