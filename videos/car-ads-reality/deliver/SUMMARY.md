# Car Ads vs Reality: summary

## Status
- **Episode: `car_ads_vs_reality.mp4`, 4:01, 1920x1080, all 8 claim scenes.**
- **Gemini TTS free tier caps at 10 requests per day per model** (quotaId GenerateRequestsPerDayPerProjectPerModel-FreeTier).
  Scenes 0-7 are voiced. Scene 8 (the spoken closing exchange: "I read the asterisk first" / "The asterisk has fine
  print too" / bicycle / "Pedals sold separately" / spoken closing question) could not be voiced today.
  The episode ends on the buyer buried in fine print (sad trombone), then an on-screen end card: "Which claim annoyed
  you the most? Tell us in the comments*", where *comments are subject to fine print. The closing question is on
  screen, not spoken. I didn't switch to another TTS model to get around the cap.
  - Once the quota resets: `python tts.py 8 ...`, align, retime, re-render (see the README). The renderer then adds
    the spoken ending and the salesman's to-camera question automatically.
- **Shorts:** 1 (0-60 rollout + towing + mpg, 84 s), 2 (Fratzonic + EV range, 67 s), 3 (FSD + warranty + Maverick
  price, 80 s). All are vertical, open on a claim line with a hook title, and end on a closing-question card.

## Claims used (mildest to most outrageous) and sources
Each one is phrased as "the ad says X, the spec sheet says Y". Details are in `FACTS.md`.
1. **Ford Maverick, "starting MSRP $28,145"**: Ford's own footnote says it excludes destination/delivery, taxes and
   fees. Source: Ford "What's New: 2026 Ford Maverick". Ford.com blocks automated fetches, so the wording was confirmed
   from the search-indexed text of Ford's page and from Cars.com/TFL pricing coverage.
2. **Toyota Corolla Hybrid, "up to 50 mpg combined"**: EPA rates the SE AWD at 44 combined. Source: toyota.com and
   fueleconomy.gov (EPA's own web service, read directly).
3. **Hyundai "America's Best Warranty", 10 yr/100k powertrain**: original owner only; the next owner gets 5 yr/60k.
   Source: hyundaiusa.com warranty page (read directly).
4. **Tesla Model S Plaid, 0-60 in 1.99 s**: one-foot rollout subtracted; MotorTrend measured 2.28 s from a true
   standstill. Sources: Tesla's footnote as reported by Edmunds, Electrek and InsideEVs (tesla.com blocks fetches).
5. **Ford F-150, 13,500 lbs max towing**: "when properly equipped", which requires the 3.5L EcoBoost, the Tow/Haul
   Package and the optional Max Tow Axle. The standard 2.7L is 8,400 max. Source: Ford 2026 F-150 Towing Guide PDF
   (read directly).
6. **F-150 Lightning, 320 mi EPA estimate**: Consumer Reports at a steady 70 mph got 270 mi. Of 22 EVs, nearly half
   fell short and some beat their estimate. Source: CR press release, Dec 2023, via InsideEVs/Motor1 (CR blocks fetches).
7. **Dodge Charger Daytona, Fratzonic Chambered Exhaust**: the sound comes from an amplifier and tuning chamber, up to
   126 dB (Dodge's comparison: a Hellcat), and there is a Stealth Mode. Source: Stellantis/Dodge press material and an
   Autoblog explainer.
8. **Tesla "Full Self-Driving"**: the full name is "Full Self-Driving (Supervised)". It requires active driver
   supervision, does not make the car autonomous, and the manual says to keep hands on the wheel. Source:
   tesla.com/support/fsd and the owner's manual, via search-indexed text (tesla.com blocks fetches).

## Dropped claims
- "Best-in-class towing": Ford's site uses "best-in-class" only for payload, so the scene uses "max available towing".
- Exact Maverick destination fee: sources conflict ($1,695 vs $1,845), so no number is given.
- Car and Driver/SAE "EVs 12.5% short at 75 mph": I couldn't open the primary article.
- Cold-weather range: I couldn't fetch a primary dataset with model numbers.

## Running gag: the fine print (an asterisk with a face)
0 It hops off the ad stack onto the desk. 1 It drags a scroll of fine print across the gas-station floor. 2 The fine
print unrolls from the showroom ceiling. 3 It's tyre-sized on the start line and "rolls out" exactly 1 FT. 4 The towed
boat is loaded with fine print. 5 Fine print is wound around like a charging cable. 6 The speakers blast fine print.
7 A fine-print avalanche rises around the cast. Payoff: the avalanche buries the buyer to the chin, then the asterisk fills the end card:
"Tell us in the comments*", where *comments are subject to fine print. The asterisk in every parody ad, and the
ad's fine-print strip, also get bigger each scene.

## Background oddities (never mentioned)
0 A pigeon in a hard hat patrolling the window ledge. 1 A raccoon filling up a red toy car at the pump. 2 A goat on a
rotating display plinth, chewing a brochure. 3 A snail in a racing helmet creeping along the start line. 4 A penguin
sunbathing on a lounger in the towed boat. 5 A cow plugged into the EV charger, reading a newspaper. 6 A sheep in
headphones headbanging on the speaker stack. 7 A mime trapped in an invisible box by the cones. (8 is written for the
unvoiced ending scene: the hard-hat pigeon returns with three hard-hatted chicks.)
**Wall easter eggs:** "Employee of the Month: *", "Days since last footnote: 0", a clock with an asterisk for 12,
"No haggling* (*haggling sold separately)", "MPG may vary (mostly downward)", "Timing starts eventually",
"Max tow: ask the axle", "Range: vibes", "Quiet please (126 dB)", "Hands on the wheel, please".

## Other judgement calls
- **Locations:** 7 sets (showroom, gas station, drag strip, tow lot, highway charger, sound stage, test track), with
  each car's real photo on a screen behind the cast. The showroom has a desk and the buyer slams the ad stack on it on
  frame 1, with the salesman already wincing. First spoken word at 0.30 s.
- **Real photos, not video:** I couldn't find Commons video clips with clear licences in the time available, so
  CC-licensed photos are used with slow pans. Brand logos appear as they are on the photographed cars. I didn't place
  standalone logo files in the parody ads, so the ads can't pass for official ones.
- **Salesman:** new look (silver quiff, moustache, gold bow tie, burgundy suit) and a new voice (Gemini "Schedar"),
  built on the series rig. The buyer is the series character with the Fenrir voice.
- **Music:** a different Kevin MacLeod (CC BY 4.0) track per scene, ducked under the dialogue and muted for the
  parody-ad jingles. Elevator music for the deflated ending.
- **Shorts:** 60-100 s each needs 2-3 scenes. Short 1 = 0-60 rollout + towing + mpg (about 85 s); Short 2 = Fratzonic +
  EV range (about 67 s); Short 3 = FSD + warranty + Maverick price (about 80 s). Each opens on the buyer's claim line with a
  hook title and ends on a closing-question card.
- **Jokes that are not factual claims:** "Your driveway charges a fee", "Pedals sold separately", the posters.
