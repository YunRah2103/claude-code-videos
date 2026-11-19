# Showroom kit — shared engine for the car-twin skits

Used by honda-prologue-is-a-chevy, tesla-fsd-subscription, gr86-vs-brz, outlander-is-a-rogue and blazer-ev-no-carplay.
`engine.py` is built on `bmw-heated-seats/src/render.py` (same buyer, poses, lip sync, captions, cards and -14 LUFS mix).
New: real car photos on a glossy display platform that slide out and in on topic changes, floor reflections of the cars
and both characters, a vivid per-brand showroom (`BRANDS`), a salesman outfit per brand, a light sweep on each topic change,
one background oddity per scene (`oddities.py`, `ODD`), and a `thumb` mode.

Hook rules enforced by the engine: the first car set is already sliding onto the platform on frame 1, the buyer is
mid-gesture and stepping in, `retime.py` puts the first word at 0.30 s, and `overlays()` draws nothing (no card, stamp
or car label) before `CLEAN = 3.0` s; only the word-by-word captions are on screen. The brand name is on the wall.

An episode needs `src/script.py` (LINES = (speaker, text, scene, pose tag); '*' marks a camera-punch word; SPOKEN/DICT
for alignment; optional HOLD/GAPS for pacing) and `src/show.py` (BRAND, SALES outfit, CARS, SCENES with cars/odd/cards,
FINAL_Q, THUMB). `render.py` is a three-line wrapper. Photos: `prep_photos.py` (rembg cut-out; needs `pip install
"rembg[cpu]"` in .venv) writes `~/.cache/showroom/cars/<key>.png` from Commons downloads in `~/.cache/photos`, and
`prep_photos.py credits OUT KEYS` writes CREDITS.txt. Downloads, cut-outs, MP4s, WAVs and PNGs are never committed.
`tts.py` makes one two-speaker Gemini call and stops on any HTTP error (including 429).
