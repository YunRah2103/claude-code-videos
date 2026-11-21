# Yub batch: "pick a side" skits

All three: 1080x1920, 30 fps, 6 scenes, word-by-word captions, first spoken word at 0.30 s, the buyer is already walking in and talking on frame 1, nothing overlaid on the picture before 3 s. Same buyer (look + Gemini "Fenrir") in every video. Same deadpan salesman voice (Gemini "Orus") in every video, with a new outfit per dealer. One Gemini TTS call per video, no 429s. Your track is the music bed under all three, ducked under the dialogue (it starts at 0.5 s, 20 s and 45 s into the track so the three videos sound different). Photos and logos come from Wikimedia Commons (see each CREDITS.txt). Facts and sources are in `videos/yub-decide/FACTS_*.md`.

| # | Video | Car / year | Hook line (0.3 s) | Twist lands | Background oddity (never mentioned) | Length |
|---|---|---|---|---|---|---|
| 1 | `01_cybertruck/cybertruck.mp4` | Tesla Cybertruck, top Cyberbeast trim, 2026 pricing (photos: 2024 truck) | "A forty-grand Cybertruck? Where?!" | ~25.4 s: "The steel trim panel. It could fall off." (46,096-truck recall) | A cow in a VR headset, in every scene (it rides in the towed boat in the desert) | 42.8 s |
| 2 | `02_range_rover/range_rover.mp4` | 2016 Land Rover Range Rover (L405) vs a new 2026 Corolla | "A Range Rover? Cheaper than a new Corolla?!" | ~23.6 s: "RepairPal rates its reliability two out of five." | A knight in full armour quietly sipping tea, pinky out, in every scene | 44.9 s |
| 3 | `03_civic_vs_golf/civic_vs_golf.mp4` | 2026 Honda Civic Type R vs 2026 VW Golf R | "Fifty grand. One hot hatch. Which one?!" | ~25.0 s: the price reveal ($48,090 vs $50,730) | An octopus on a traffic cone juggling oranges, in every scene | 40.9 s |

Closing questions (spoken by the salesman, straight to camera): "Would you still buy a Cybertruck?" / "Bargain, or trap?" / "Which one are you taking?"

## Claims softened or dropped
**Cybertruck**
- Price: we say "about a hundred grand" for the top Cyberbeast trim. Most 2026 listings show $99,990, and one Nov 2026 report says $109,990. We don't say which trims can be ordered today, because prices changed several times in 2026.
- Range: shown as "EPA rated: ~320 miles". Sources give 301–325 mi depending on trim.
- "Forty-grand" is the buyer's rounding. The salesman corrects it to $39,900.
- Dropped: the total number of Cybertruck recalls (sources disagree) and the 2024 accelerator-pedal recall (not separately checked).

**Range Rover**
- Used price "about eighteen grand": CARFAX's average dealer listing is $18,373. KBB starts at $15,200 for an HSE.
- Air-spring cost "around a thousand dollars, per corner" is a range from shop estimates ($760–$1,442), labelled "typical shop estimate".
- Consumer Reports is softened to "Land Rover among the bottom brands". Land Rover is not last overall (Jeep is).
- Dropped: "V8" (the 2016 base car is a supercharged V6), "last place", and full-system suspension prices.
- Photos: the Corolla photo is a 2020 car of the current generation, labelled only "COROLLA: ~$23K NEW". The "OR TRAP?" grille close-up was taken at a 2014 auto show.

**Civic vs Golf**
- Golf R power is 328 hp (2025–26). The older 315 hp figure was dropped.
- Prices include destination ($48,090 / $50,730) and are labelled "INCL. DEST.".
- The script does not say which car is faster or better. "Love shifting? Civic. Hate rain? Golf." only restates manual-only FWD vs automatic-only AWD.

## Not done / limits
- No real-device check of how the TikTok UI sits over the frame. Oddities stay above y≈950, out of the usual icon column.
- MP4s and audio are kept out of git, per the repo rules. Sources are in `videos/yub-decide/`.
