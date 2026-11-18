# origin-kit: brand-origin showroom skits

Shared renderer for lamborghini-tractor-origin, toyota-loom-origin, subaru-aircraft-origin, porsche-beetle-origin and
miata-best-seller. Same cast, voices (Orus salesman, Fenrir buyer), captions, lip sync and mix chain as bmw-heated-seats.
A video is just `src/script.py`, `src/words.json`, `assets/*.jpg` and `FACTS.md`.

- **Layout:** one brand showroom with the name on the wall. A real photo exhibit sits on a glossy platform, with a label hanging above it, and slides out and in when the story moves on. The buyer and the brand-dressed salesman stand in front. Cars and people are mirrored on the glossy floor.
- **Background gags:** each scene has one never-mentioned oddity in the showroom windows (`oddities.py`).
- **Photos:** `cutout.py` cuts each photo out with rembg (`isnet-general-use`), blanks the plates, applies one grade to all, and resamples every exhibit to the same display resolution so sharpness matches.
- **Hook:** the first word is at 0.3 s, frame 1 is already moving, and chips appear only after 3 s. Captions follow the layout rule: centred at x=459, inside 12–62 % of the height and the left 85 % of the width.

```bash
source .venv/bin/activate; V=lamborghini-tractor-origin; C=~/.cache/$V; K=videos/origin-kit
python $K/cutout.py videos/$V $C/cut                        # cut-outs (PNG cache, not committed)
python $K/tts.py videos/$V $C/raw.wav                       # ONE two-speaker Gemini call; stops on any HTTP error
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python $K/align.py videos/$V $C/raw16.raw $C/raw_words.json
python $K/retime.py videos/$V $C/raw.wav $C/raw_words.json $C/voice.wav videos/$V/src/words.json
python $K/engine.py videos/$V meta out/$V/meta.json
python $K/engine.py videos/$V video $C/voice.wav out/$V/$V.mp4
python $K/engine.py videos/$V thumb out/$V/$V-thumb.png
python tools/preflight.py out/$V/$V.mp4 --meta out/$V/meta.json --words videos/$V/src/words.json --facts videos/$V/FACTS.md --align-pct N
```
`align.py VIDEO check` lists dialogue words missing from the pocketsphinx dictionary; add them to `PHONES` in the script.
