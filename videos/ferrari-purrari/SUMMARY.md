# Ferrari "Purrari": summary and fact sources

This is the second test of the PS1 low-poly narrated style, after `rolls-royce-pinstripe`. The video is
1080x1920 at 30 fps and runs 28.0 s. It has one narrator (Gemini TTS voice Charon, one call) and 23 literal shots,
so the picture changes about every 1.2 s (longest shot 2.0 s). Captions are small (66 px, the smallest preflight allows) and show one word at a
time; key words are red. No title cards or other graphic overlays. Facts checked 2026-11-24.

## Final narration (92 words)

> Ferrari can refuse to sell you a car, even if you have the money.
> Dealers pick who gets the rare ones.
> Buyers reportedly sign a contract: no reselling in the first year.
> Then Deadmau5 wrapped his Ferrari 458 as a Nyan Cat.
> He called it the Purrari.
> Ferrari did not find it funny.
> He has said it sent him a cease-and-desist.
> Ferrari says it blacklists no one,
> but it picks who gets special editions.
> It's your money. It's their car.
> Should a company be allowed to pick its customers? Yes, or no?

The hook's first word starts at 0.33 s.

## Facts as used

| # | Fact (as used) | Said / shown | Sources |
|---|---|---|---|
| 1 | Ferrari says it does not blacklist anyone from buying, but "reserves the right to decide" who gets its special editions, so some buyers can only buy regular-production models. | "Ferrari can refuse to sell you a car, even if you have the money." "Dealers pick who gets the rare ones." "Ferrari says it blacklists no one, but it picks who gets special editions." | SlashGear, The Truth About Ferrari's Celebrity Bans: https://www.slashgear.com/868276/the-truth-about-ferraris-celebrity-bans ; MotorBiscuit, Official: Ferrari Denies Then Confirms Banning Certain Owners: https://www.motorbiscuit.com/official-ferrari-denies-then-confirms-banning-owners |
| 2 | New-Ferrari sales contracts reportedly include a clause against reselling in the first year (some limited editions reportedly longer). The aim is to stop flipping. | "Buyers reportedly sign a contract: no reselling in the first year." | HotCars: https://www.hotcars.com/rules-ferrari-owners-must-follow-and-the-employees-must-abide-by/ ; SlashGear, The Reason Why Ferrari Won't Let You Sell Your Newly Purchased Car: https://www.slashgear.com/1016130/the-reason-why-ferrari-wont-let-you-sell-your-newly-purchased-car ; MotorBiscuit: https://www.motorbiscuit.com/strict-ferrari-rules-never-break-want-new-ferrari ; Luxury Launches (listed in the brief) |
| 3 | Deadmau5 wrapped his Ferrari 458 in a Nyan Cat livery and called it the "Purrari". | "Then Deadmau5 wrapped his Ferrari 458 as a Nyan Cat. He called it the Purrari." | Techdirt: https://archive.techdirt.com/articles/20140902/11491828395/ferrari-drm-dont-screw-with-our-logos-well-let-you-know-if-its-ok-to-sell-your-car.shtml ; Jalopnik: https://www.jalopnik.com/ferrari-sent-deadmau5-a-cease-and-desist-about-his-purr-1627640534 ; Yahoo Autos (listed in the brief) |
| 4 | Deadmau5 has said Ferrari sent him a cease-and-desist letter over the Purrari. Reports say it targeted the custom "Purrari" badges and floor mats. | "Ferrari did not find it funny. He has said it sent him a cease-and-desist." | Techdirt (as above); Jalopnik (as above); HuffPost Canada: https://www.huffingtonpost.ca/2014/08/28/deadmau5-purrari-cease-and-desist-ferrari_n_5732422.html |

Not claimed: no prices, no celebrity besides Deadmau5, no claim that Deadmau5 was banned, and no claim that the
letter caused him to sell the car. "Ferrari did not find it funny" is the narrator's summary of fact 4.
"It's your money. It's their car." is the punchline and opinion, not a fact.

## Shown but not claimed (art)

- The Ferrari 458 (red, a yellow "special" version, and the wrapped Purrari), the prancing-horse shield, the
  FERRARI wordmark and the hub caps are hand-built low-poly versions. No photos or official artwork were used.
- The wrap is a generic grey cartoon cat with a rainbow trail on navy with stars. It is not the Nyan Cat artwork.
- There is no likeness of Deadmau5. The figure applying the wrap is a generic installer.
- The salesman, buyers, executive, contract, FOR SALE/NO sign, envelope, letter, BLACKLIST clipboard and the
  PURRARI plate are invented props. The BLACKLIST page is blank on purpose.
- Comment bait (never mentioned): a tiny loaf-shaped rainbow cat with its own trail sits on top of the showroom's
  corner pillar in every showroom shot. It also sits by the road in the Purrari night shot and on a shelf in the office.

## Allowed numbers

| Spoken / shown | Fact |
|---|---|
| 458 | 3 |
| first | 2 |
| one ("no one", "rare ones") | 1 |
| 5 (part of the name Deadmau5, not a number) | 3 |

## What changed from the first video to improve engagement

- The video is shorter (28 s instead of 34.4 s) and cuts more often (23 shots, about 1.2 s each).
- The hook shot is the product itself: a spotlight snaps onto the red 458 with a bass hit. The cash is pushed
  back across the desk by 4 s.
- The story turns at the 10 s mark (the cat wrap), where retention usually drops.
- The last shot pulls back to the opening framing, so the short loops cleanly.
- It is lit brighter, with more colour (Ferrari red, rainbow) than the dark pinstripe grade.
- There are sound hits on literal actions (stamp, thump, sparkle) and a quiet synth pulse that drops out under the
  deadpan punchline.
- Captions are small, with red highlight words. The thumbnail promises a conflict: "FERRARI vs THE PURRARI".

## Files

- `out/fp/ferrari_purrari.mp4`, `out/fp/thumbnail.png` (not committed)
- `src/`: `script.py` (narration), `tts.py` (one Gemini call, stops on any HTTP error including 429),
  `align.py`, `retime.py`, `lowpoly.py`, `models.py` (reused from rolls-royce-pinstripe), `fmodels.py` (458, shield,
  wrap, props), `render.py` (shots and captions), `mix.py`, `sfx.py`
