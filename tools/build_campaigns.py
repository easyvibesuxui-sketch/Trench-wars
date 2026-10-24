#!/usr/bin/env python3
"""ომის კამპანიები: data/campaigns/*.json → campaigns/*.md, campaigns/README.md, lore/11-sacrifices.md

გაშვება:  python3 tools/build_campaigns.py   (ბილდერისთვის data.js-ს tools/build_builder.py აწყობს)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADER = "<!-- ავტომატურად გენერირებული: tools/build_campaigns.py — შეცვალე data/campaigns/*.json -->\n"


def load():
    data = json.loads((ROOT / "data" / "units.json").read_text(encoding="utf-8"))
    names = {**data["factions"], **data.get("allies", {})}
    camps = {}
    for fid in names:
        p = ROOT / "data" / "campaigns" / f"{fid}.json"
        if p.exists():
            camps[fid] = json.loads(p.read_text(encoding="utf-8"))
    return names, camps


def faction_page(fid, name, c):
    s = c["sacrifice"]
    out = [HEADER, f"# {c['title']} — {name}", "",
           f"> **მტერი:** {c['enemy']} · **გმირი:** {c['hero']} · **სცენარები:** {len(c['scenarios'])}", "",
           c["intro"], "",
           f"## მსხვერპლი: {s['name']} ({s['year']})", "", f"**„{s['title']}“.** {s['text']}", "",
           "## სცენარები", ""]
    for i, sc in enumerate(c["scenarios"], 1):
        out += [f"### {i}. {sc['name']} ({sc['year']})", "", sc["story"], "",
                f"- **მიზანი:** {sc['objective']}",
                f"- **სპეციალური წესი:** {sc['special']}",
                f"- **ჯილდო:** {sc['reward']}", ""]
    out += ["## დასასრული", "", c["ending"], ""]
    return "\n".join(out)


def main():
    names, camps = load()
    out_dir = ROOT / "campaigns"
    out_dir.mkdir(exist_ok=True)
    for fid, c in camps.items():
        (out_dir / f"{fid}.md").write_text(faction_page(fid, names[fid], c), encoding="utf-8")

    idx = [HEADER, "# ომის კამპანიები", "",
           "ყოველ ფრაქციას თავისი კამპანია აქვს: შესავალი, ომის გმირი, **მსხვერპლი** — გამოგონილი ადამიანი, რომელმაც თავი შესწირა",
           "დიდი ურჩხულის ან დემონის შემოტევას — და ხუთი სცენარი, რომლებიც ომს დასასრულამდე მიიყვანს. ერთ-ერთი სცენარი ყოველთვის",
           "მსხვერპლის ადგილზე თამაშდება და მის ხსოვნას სპეციალური წესით აბრუნებს.", "",
           "**როგორ ვთამაშობთ:** სტანდარტული ბიუჯეტი 500 მარჩილი; კამპანიის წესები — `../rules/campaign.md`; ბილდერის „კამპანიის“ ჩანართი",
           "სცენარებს თავისით აჩვენებს და გამარჯვებულ სცენარს აღნიშნავს. **მოწინააღმდეგე:** ნათელი ფრაქციის კამპანიაში მეორე მოთამაშე",
           "ჯოჯოხეთის ლეგიონებით ან დიდი უღლით თამაშობს — ომის ურჩხულები მათი იუნიტებით აღინიშნება (I–II — ნაშიერები, IV — დიდი ურჩხული,",
           "V — ომის მთავარი მტერი). ბნელი ფრაქციის კამპანიაში მოწინააღმდეგე ნებისმიერი ნათელი ფრაქციაა.", "",
           "| ფრაქცია | კამპანია | მტერი | მსხვერპლი |", "|---|---|---|---|"]
    for fid, c in camps.items():
        s = c["sacrifice"]
        idx.append(f"| {names[fid]} | [{c['title']}]({fid}.md) | {c['enemy']} | {s['name']} ({s['year']}) |")
    (out_dir / "README.md").write_text("\n".join(idx) + "\n", encoding="utf-8")

    lore = [HEADER, "# მსხვერპლნი — ვინც თავი შესწირა", "",
            "> ყოველ ომს ჰყავს ადამიანი, რომელმაც დიდი ურჩხულის ან დემონის შემოტევა საკუთარი სიცოცხლით შეაჩერა. ისინი გამოგონილი",
            "> ადამიანები არიან — მეხრეები, მესაჭეები, მწყემსები, მეგონგეები — არა მეფეები და არა ღმერთები. ამბრის მსხვერპლის მსგავსად",
            "> (`02-chronology.md`), მათი სახელები ფრონტზე ჩუმად ითქმის. მათი ადგილი ყოველი კამპანიის ერთ სცენარად თამაშდება (`../campaigns/`).", ""]
    for fid, c in sorted(camps.items(), key=lambda kv: kv[1]["sacrifice"]["year"]):
        s = c["sacrifice"]
        lore += [f"## {s['name']} — {s['year']}", "", f"*{names[fid]} · „{s['title']}“ · კამპანია: [{c['title']}](../campaigns/{fid}.md)*", "",
                 s["text"], ""]
    (ROOT / "lore" / "11-sacrifices.md").write_text("\n".join(lore), encoding="utf-8")
    print(f"campaigns/: {len(camps)} კამპანია · lore/11-sacrifices.md")


if __name__ == "__main__":
    main()
