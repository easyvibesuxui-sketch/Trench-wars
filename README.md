# ქვესკნელის ფრონტი (Underfront)

ქართულენოვანი grimdark სკირმიში თამაში: **I მსოფლიო ომი + სტიმპანკი + მითოლოგია**. 1914 წელი. ქვესკნელის კარიბჭეები მთელ მსოფლიოში
გაიხსნა, და ყოველი ერი სანგრებში თავისი მითოლოგიის ბოროტებას — და საკუთარ ერეტიკოსებს — ებრძვის. მთავარი ფრონტი მცირე კავკასიონშია,
**ამბრის ღარის** გასწვრივ: ღარის, რომელიც გოლიათმა ამბრმა საფლავისკენ მიმავალმა ფეხით მოხნა, როცა თავი შესწირა, რომ დევების მამა
შეეჩერებინა.

## ორი პროდუქტი
| | რა არის | სად |
|---|---|---|
| **A. სამაგიდო თამაში** | d10 სკირმიში: 49 ფრაქცია (7 ძირითადი, 42 მოკავშირე), 447 იუნიტი, კამპანიები, ნეიტრალური ზოლი, სცენარები | `rules/`, `units/`, `campaigns/`, `playtest/`, ბილდერი — `builder/index.html` |
| **A+. ბოლო ზღუდე** | tower defense რეჟიმი: იგივე იუნიტები და d10, მაგიდაზე და ონლაინ | წესები — `rules/defense.md`; ონლაინ პროტოტიპი — `defense/index.html` |
| **B. ციფრული თამაში** | რეალურ დროში სტრატეგია (AoE/AoM-ის მსგავსად): სოფელი-ბაზა, ეკონომიკა, ეპოქები, კედლები და სანგრები | დიზაინი — `docs/digital-game.md`, `docs/architecture.md`; მექანიკების კვლევა და პროდუქტების გეგმა — `docs/mechanics-research.md`; პროტოტიპი — `digital/index.html` |

## სად რა არის
- **ლორი:** `lore/` — ზოგადი ისტორია, ქრონოლოგია, ფრაქციები, 42 ცალკე ომი, ამბები, მსხვერპლნი.
- **წესები:** `rules/core-rules.md` (ძირითადი), `abilities.md` (ძალები და ნიშნების ლექსიკონი), `roles.md` (18 როლი), `campaign.md`,
  `no-mans-land.md` (ნეიტრალური ზოლი), `scenarios.md` (6 სცენარი).
- **მონაცემები:** `data/` — იუნიტები, ფასები (ბალანსერი), ძალები, როლები, კამპანიები, ეკონომიკა, სცენარები. ყველაფერი დანარჩენი მათგან გენერირდება.
- **ვიზუალი:** `docs/visual-guide.md` (ფერადი — `playtest/visual-guide.html`) — სტილი, 49 ფრაქციის ფერები/სილუეტი/ემბლემა, ყოველი იუნიტის მოკლე აღწერა მხატვრისთვის (`tools/build_visuals.py`).
- **ფაქტების შემოწმება:** `docs/fact-check.md` — სახელები, Trench Crusade-თან შედარება, ლორის წყაროები.
- **სათამაშო ნაკრები:** `playtest/kit.pdf` (პირველი თამაში), `cards-all.pdf` (ყველა ბარათი), `scenarios.pdf`.
- **ინსტრუმენტები:** `tools/` — ბალანსერი, ვალიდატორი, ბილდერის, კამპანიების, ნაკრების და სცენარების ამწყობები, ბილდერის ტესტი.

## აწყობა
```
python3 tools/balancer.py --sims 160 --calibrate 6 --mixed-sims 100 --faction-sims 200 --support-sims 400 --warm   # ფასები (~1 სთ)
python3 tools/validate.py
python3 tools/build_campaigns.py && python3 tools/build_abilities.py && python3 tools/build_roles.py && python3 tools/build_no_mans_land.py
python3 tools/build_builder.py          # builder/data.js და digital/data.js
python3 tools/build_playtest.py && python3 tools/build_scenarios.py && NODE_PATH=$(npm root -g) node tools/print_playtest.js
NODE_PATH=$(npm root -g) node tools/test_builder.js
```

## ორიგინალობა
Trench Crusade-ის, Games Workshop-ის, March of Giants-ის და Age of Mythology-ის სახელებს, სიუჟეტებს და ტექსტებს არ ვიყენებთ; ისტორიული
სახელები და საჯარო მითები — კი. რეალური რელიგია, რეალური სისასტიკე და მშვიდობიან მოსახლეობაზე თავდასხმა თამაშში არ არის.
რეპოს სახელი (`Trench-wars`) GitHub-ის პარამეტრებში უნდა შეიცვალოს თამაშის სახელზე (მაგ. `underfront`).
