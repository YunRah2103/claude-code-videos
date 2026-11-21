# Yub series: five car skits (Nov 2026)

All five use the same pipeline as the earlier skits (bmw-heated-seats/platform-ladder): Gemini two-speaker TTS (Buyer =
Fenrir, Salesman = Orus, one call per video), PocketSphinx forced alignment, word-by-word captions, the same cartoon
cast, whip pans, camera punches and the −14 LUFS mix chain. The shared renderer is `src/engine.py` and each video folder
holds `cfg.py` (script, six sets, cards, oddity), `words.json`, `FACTS.md`, `CREDITS.txt`, `script.txt`, `captions.txt` and
`assets/` (Wikimedia Commons photos + logo). Every video: 6 scenes on 6 different sets, first word at 0.30 s, no overlays
before 3 s, the salesman's closing question to camera, end card, and the user's track ("it was never about the brand")
mixed under the dialogue and ducked while anyone speaks. Renders, thumbnails and caption/script copies are in
`out/yub/<folder>/`.

| # | Folder | Car / year | Topic | Background oddity (never mentioned) | Softened or dropped |
|---|---|---|---|---|---|
| 1 | 01_toyota_corolla | Toyota Corolla (1968, 2020/2021 photos; nameplate since 1966) | Why the most boring car is the best seller | A penguin mopping the floor beside a wet-floor sign, in every scene | "Best-selling car" became "Toyota calls it the world's best-selling nameplate". Total kept as "over fifty million" (Toyota's July 2021 milestone; I found no newer verified total). Reliability and running costs are stated as reputation, with no figures. |
| 2 | 02_mach_e | Ford Mustang Mach-E (revealed 2019, 2021/2022 photos; 1965 Mustang for contrast) | Is it really a Mustang? | A small horse plugged into a charging cable, battery icon filling over its head | 0–60 in 3.5 s is said as "Ford says" and shown as "Ford estimate" (GT Performance Edition, 480 hp). I dropped "two motors" because it isn't true of every trim. Purist backlash is soft ("Some did."). |
| 3 | 03_bugatti_veyron | Bugatti Veyron 16.4 (2005) | The car that lost money on every sale | A pig in a bow tie feeding banknotes into a paper shredder | The loss is "reportedly" / "analysts estimated millions per car" and is stamped DISPUTED, since Bugatti called the figures not plausible. I dropped the exact figure because sources give €4 m, €4.6 m or $6.24 m. Price is "over a million euros". 1,001 PS and 253 mph (407 km/h type-approved) are verified. |
| 4 | 04_lamborghini | Lamborghini (tractors from 1948, Automobili Lamborghini 1963; 1951/1965 tractors, 1965 350 GT photos) | How an angry tractor maker created a supercar brand | A chicken driving a tiny orange tractor across every scene | The clutch story and Enzo's "stick to tractors" line are framed as "the story goes" / "reportedly", with an on-screen "Never proven" and "UNPROVEN". The video ends "Legend or myth?". Dropped: "out of spite", the lire clutch prices and the founding month (sources differ). |
| 5 | 05_porsche_911 | Porsche 911 (shown 1963 as the 901; 1964 cars, 928 photo) | Why is the engine in the wrong place? | A snail with a jet engine strapped to its back (rear-mounted), crawling | The 928-as-replacement story is "Reportedly". Early handling is stated as reputation. The traction and braking points are attributed to Porsche. Dropped: the US rear-engine-ban speculation. Voice sped up 5% (pitch kept) to land near 45 s. |

Fact sources and the allowed-number tables are in each folder's `FACTS.md`. `tools/preflight.py` checks every number
spoken or shown against that table.
