# BMW new M3 vs old — "Old M3 or new M3?"

Vertical skit (1080x1920, 30 fps, ~57 s, 7 scenes). Same cast, voices (Orus salesman, Fenrir buyer), caption system, camera
and mix chain as bmw-heated-seats. One flat, vivid BMW showroom; a real M3 photo sits on a display platform with a model
plaque above it and slides off/on when the topic changes (E46 → G80 → E92 → E46 → G80). All cars are side-on, facing right,
same width, with a contact shadow so they sit on the platform. Stat panels appear only after 3 s.

Background oddities (never mentioned, one per scene): a giraffe's head hanging through a ceiling tile chewing a brochure; a
snail in sunglasses on a skateboard; a bedsheet ghost reading a newspaper on a bench; a penguin sweating in an ice bucket; a
giant rubber duck in a paddling pool; a crab in a tie carrying a briefcase; a cactus in sunglasses jogging on a treadmill.

Car photos (raw files kept in `~/.cache/bmw-new-m3-vs-old/`, not in git; cut-outs in `assets/` made by `src/prep_cars.py`):
- `e46.png` — Wikimedia Commons, "BMW M3 - IMG 5084 - Flickr - Adam Woodford.jpg", CC BY 2.0 (Adam Woodford)
- `e92.png` — Wikimedia Commons, "Bmw m3 v8 e92 seite.jpg", CC BY-SA 3.0
- `g80_side.png` — side-profile image supplied by the user (2026-11-18); flipped to face right in `render.py`

```bash
source .venv/bin/activate; cd videos/bmw-new-m3-vs-old/src; C=~/.cache/bmw-new-m3-vs-old
python tts.py $C/raw.wav                                         # one two-speaker Gemini call (Orus + Fenrir)
ffmpeg -i $C/raw.wav -af atempo=1.04 -ar 24000 -ac 1 $C/rawt.wav  # 4% tighter, pitch kept
ffmpeg -i $C/rawt.wav -ar 16000 -ac 1 -f s16le $C/rawt16.raw && python align.py $C/rawt16.raw $C/rawt_words.json
python retime.py $C/rawt.wav $C/rawt_words.json $C/voice.wav words.json
python3 prep_cars.py $C/raw_img e46 e92; python3 prep_cars.py $C/raw_g80 g80_side   # system python (rembg)
python render.py meta ../../../out/bmw-new-m3-vs-old/meta.json
python render.py video $C/voice.wav ../../../out/bmw-new-m3-vs-old/bmw_new_m3_vs_old.mp4
cd ../../..; python tools/preflight.py out/bmw-new-m3-vs-old/bmw_new_m3_vs_old.mp4 --meta out/bmw-new-m3-vs-old/meta.json \
  --words videos/bmw-new-m3-vs-old/src/words.json --facts videos/bmw-new-m3-vs-old/FACTS.md --align-pct 98.7
```
Alignment: 156/158 words force-aligned and plausible by `align.py`'s duration check (98.7%).
