# "The real [Brand] dealership experience" — videos 1 and 2

Same buyer (brown skin, glasses, messy hair, navy suit; Gemini voice **Fenrir**) as every earlier skit. The salesman keeps the
series face but changes outfit and accent per brand. Format: ~100 s, 8 scenes, a gag every 5–15 s, a running gag, a late
confession, and a deflated closing line. 1080x1920 @30 fps, word-by-word captions, the supplied "original sound" track
looped under the dialogue (ducked), synthesised SFX, mixed to -14 LUFS. Real car photos and logos from Wikimedia Commons
(see each CREDITS.txt). One Gemini TTS generation per video, no 429s.

**v2 (quality pass):** every showroom is now a full one-point-perspective dealership — light-panel ceiling, side walls with
street windows, glossy tiled floor mirroring the back wall, brand fascia, desks/kiosks/plants/reception — and the hero cars
are the **real photos cut out** (hand-traced outline + colour matting, `src/cutout.py`) standing on turntables with mirrored
floor reflections, contact shadows and ceiling light cones. Screens get a glass sheen; characters get contact shadows;
captions moved to the top so the cars stay visible.

## 01 — The real Tesla dealership experience (~107.5 s)
Salesman: charcoal zip jacket over a black tee, red T badge, deadpan Californian tech-bro (Orus).

| # | Scene / location | Real car or photo shown |
|---|---|---|
| 1 | Tesla "gallery" showroom | Real Model Y (2025, white) on a turntable + Model 3 Highland behind; Model Y (red) on the screen; Tesla T logo |
| 2 | Cybertruck bay (stainless panels) | Real Cybertruck on the floor; Cyberbeast on the screen; cutaway: stainless body |
| 3 | Gallery, interior display | Real Model 3 Highland Performance on the floor; cabin, touchscreen and Model 3 on the screen; cutaway: Model 3 cabin |
| 4 | Test drive (cabin, road in the rear window) | Model 3 Highland on the car's centre screen |
| 5 | Parked at the kerb | Cutaway: Tesla flush door handle (Model S) |
| 6 | Roadster "Coming soon" stage | Real Roadster (2nd gen prototype) on a spotlit turntable |
| 7 | Confession: the "dealership" is his garage | His Model Y parked in the garage; Model Y printout taped to the wall |
| 8 | Driveway, closing | Model Y on the driveway; Model 3 Highland on an "ORDER ONLINE" billboard |

- **Running gag:** everything is "in the app" — 6 times (lines 2, 6, 21, 43, 49, 50), each with the salesman holding out a glowing phone and a notification ding. Pay-off: "A guy who really likes the app."
- **Twist:** "I don't work for Tesla... Tesla sells direct. This is my garage." — the camera pulls back from the white gallery into a breeze-block garage with a cardboard TESLA DEALERSHIP sign and a lawn mower.
- **Closing:** "No. I'm buying a Toyota." / "Boring." / **"Boring has door handles."** (sets up video 2)
- **Background oddity (never mentioned):** a penguin plugged into a Tesla-style wall charger, battery bar slowly filling on its belly; it's still charging in the garage (on an extension lead) and waddles across the driveway at the end.
- **Easter eggs:** "EMPLOYEE OF THE MONTH" frame holding a smartphone; a "DELIVERY ESTIMATE" clock with no hands.
- **Softened:** Cybertruck price said as "Nearly double" (no current figure; 2026 reports vary $74,990–$82,490); Roadster production "2028. Reportedly."; China door-handle rule "plans to ban" (final vs draft status unclear); phantom braking only "The government investigated" (no complaint count).
- **Dropped:** Autopilot naming (California DMV ruling) — verified but cut for length; panel-gap jokes — no verifiable figure; spoken "Cool." trimmed from the TTS take so the hook lands inside 3 s.

## 02 — The real Toyota dealership experience (~98.5 s)
Salesman: grey suit, red tie, Toyota badge, calm and polite with a light Japanese accent (Charon).

| # | Scene / location | Real car or photo shown |
|---|---|---|
| 1 | Toyota showroom | Real Corolla (2024) on a turntable, bZ4X behind, reception desk; Corolla on the screen; Toyota logo |
| 2 | GR stage (black/red) | Real GR Supra (2025) under spotlights; cutaway: engine bay (BMW B58); screen split Supra / BMW Z4 M40i |
| 3 | Twins corner (Toyota red / Subaru blue wall) | Real GR86 and Subaru BRZ side by side on turntables; GR86, then twins photo on the screen |
| 4 | Electrified corner | Real bZ4X next to a charger; bZ4X on the screen; cartoon wheel rolls across the floor |
| 5 | Outside the dealership, queue | Real Land Cruiser 300 displayed behind the showroom window |
| 6 | Prius test drive (cabin) | Prius (2023) on the centre screen; cutaway: Prius (2023) |
| 7 | After hours, confession | Real Corolla on the floor (lights dimmed); screen: 1998–2000 Corolla (his car), flash of the Supra |
| 8 | Showroom, closing | Real Corolla on the turntable |

- **Running gag:** "Have you considered a Corolla?" — 3 times (lines 4, 16, 31), each with the Corolla card sliding in and a chime; the Corolla is also the employee of the month. Pay-off: his own car.
- **Twist:** "What do you drive?" — "A 1998 Corolla... I've been trying to kill it for years. It won't die." "Why kill it?!" "So I can buy a Supra. Too late now." (Consumer Reports No. 1 card)
- **Closing:** "Fine. One Corolla." / "Congratulations. It will outlive you." / **"Good. Something should."**
- **Background oddity (never mentioned):** a cow in a buzzing massage chair reading a newspaper (asleep after hours).
- **Easter eggs:** "EMPLOYEE OF THE MONTH" frame holding a Corolla photo; a "SINCE 1937" plaque.
- **Softened:** Supra end shown only as "DISCONTINUED" (spoken "ended in March" — several reports say March 2026); GR86/BRZ "Different bumper" (they also differ in tuning).
- **Dropped:** dealer add-ons and Land Cruiser dealer markups — no solid source found; "Sir," trimmed from the TTS take so the hook lands inside 3 s.

Sources for every claim: `tesla/FACTS.md`, `toyota/FACTS.md`.
