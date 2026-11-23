# Rolls-Royce pinstripe — summary and fact sources

Style test: PS1-era low-poly 3D (in the manner of the "Low Poly Shorts" reference), one narrator, a new literal shot
roughly every 1–2 s (25 shots, none longer than 2.2 s), word-by-word captions, 1080x1920, 30 fps, 34.4 s.
No cartoon skit characters. The user's avatar appears (rebuilt low-poly) only to ask the closing question.
Facts checked 2026-11-23.

## Facts as used

| # | Fact (as used) | Said / shown | Source |
|---|---|---|---|
| 1 | Rolls-Royce coachlines are painted by hand by one craftsman, Mark Court. Not called "the only person in the world". | "That stripe on a Rolls-Royce is painted by one man." "His name is Mark Court" | Rolls-Royce press photo "Mark Court painting the coachline" (press.rolls-roycemotorcars.com, P90249066); Supercar Blondie, "The man that hand-painted every Rolls-Royce made in the last 20 years" |
| 2 | He has done it since 2003, i.e. more than two decades. | "he has done it for over twenty years" | Supercar Blondie (joined 2003); Luxe / Outlook India, "Inside Rolls-Royce craftsmanship: how Mark Court creates luxury's most famous pinstripes" |
| 3 | Painted by hand, without guides, no machine and no sticker. | "No machine. No sticker. No guide." | Luxe / Outlook India ("entirely by hand, without guides"); CNN Money (2015-04-30), "Rolls-Royce stripe painter" |
| 4 | He uses a brush made of squirrel hair. | "Just one brush, made of squirrel hair." | Luxe / Outlook India; Supercar Blondie |
| 5 | The coachline is about 3 mm wide (Phantom, Ghost, Cullinan; Spectre is 4 mm). | "about three millimetres wide" | Rolls-Royce press release "The pursuit of perfection: craftsmanship at the home of Rolls-Royce" (press.rolls-roycemotorcars.com, T0449206EN) |
| 6 | It runs the side of the car in one go (about 6 m in total). Only "the whole side… in one go" is said; the 6 m figure is not used. | "it runs the whole side of the car, in one go" | Supercar Blondie (line length increased to about six metres, the length of a Phantom); user brief (verified) |
| 7 | About three hours per side. | "It takes about three hours per side." | Automotive Manufacturing Solutions, "The pursuit of paint perfection" (coachlines "take three hours to complete"); Supercar Blondie ("up to three hours"); user brief (verified) |
| 8 | If he makes a mistake there is no quick and easy fix. | "And if he slips, there is no quick fix." | Supercar Blondie ("if he messes up there's no quick and easy way to fix it") |
| 9 | Before Rolls-Royce he painted signs, including pub signs. | "Before Rolls-Royce, he painted pub signs." | Supercar Blondie (sign painter for village pubs and bars); Luxe / Outlook India (trained as a sign writer) |

Not claimed: no salary or price figures, no "only person in the world", no claim that machines cannot do it.
"Rolls-Royce did not hire a robot. They hired a pub sign painter." is the punchline that sums up facts 3 and 9.
The "Any wobble, and everyone sees it" line describes facts 5 and 8 and is not a separate fact.

## Shown but not claimed (art)

- The Phantom, RR badge (on the grille, the hub caps, office wall and showroom wall) and the Spirit of Ecstasy are
  hand-built low-poly versions; no photos or official artwork were used.
- The painter is a generic low-poly figure, not a likeness of Mark Court.
- "The Squirrel & Brush" pub, the calendar, robot, calipers and eraser are invented props.
- Comment bait (never mentioned): a squirrel in a hi-vis vest drives a forklift behind the painter (0.0–5 s), and a
  cow stands on the pub roof (23.8–26.3 s).

## Allowed numbers

| Spoken / shown | Fact |
|---|---|
| one | 1, 3, 6 |
| twenty | 2 |
| three | 5, 7 |

## Files

- `out/rr/rolls_royce_pinstripe.mp4` — the video (not committed)
- `out/rr/rolls_royce_pinstripe_thumb.png` — thumbnail
- `src/` — `script.py` (narration), `tts.py` (one Gemini call, voice Charon, stops on any HTTP error incl. 429),
  `align.py`, `retime.py`, `lowpoly.py` (PS1 renderer), `models.py`, `render.py` (shots + captions), `mix.py`
