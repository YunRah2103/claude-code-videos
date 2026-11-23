# Mercedes Acceleration Increase — "Would you pay $1,200 a year for 0.9 seconds?"

Vertical skit (1080x1920, 30 fps, ~25 s). Same buyer (Fenrir), captions, camera, whip pans and mix chain as
bmw-heated-seats; new salesman (Charon). `src/` copied from bmw-heated-seats: `tts.py`, `sfx.py` unchanged; `script.py`
adds a `SAY` map (numbers spoken in words, shown as digits) used by `align.py`; `retime.py` holds for the expiry and stall;
`render.py` adds the Mercedes star, an EQE 350 sedan drawn to real proportions, Mercedes showroom, road set with
scrolling world / stall / buyer seen through the glass, online-store set, penguin-with-lawn-mower oddity, and the user's
music bed (tape-stop on expiry). `thumb.py` makes the thumbnail. Facts: `FACTS.md`; summary with sources: `SUMMARY.md`.

```bash
source .venv/bin/activate; cd videos/mercedes-acceleration/src; C=~/.cache/mercedes-acceleration
cp <user music>.mp3 $C/music.mp3                                # background track (not committed)
python tts.py $C/raw.wav                                       # one two-speaker Gemini call (Charon + Fenrir)
ffmpeg -i $C/raw.wav -af atempo=1.2 -ar 24000 -ac 1 $C/rawf.wav
ffmpeg -i $C/rawf.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python align.py $C/raw16.raw $C/raw_words.json
python retime.py $C/rawf.wav $C/raw_words.json $C/voice.wav words.json
python render.py meta ../../../out/mercedes-acceleration/meta.json
python render.py video $C/voice.wav ../../../out/mercedes-acceleration/mercedes_acceleration_short.mp4
python thumb.py ../../../out/mercedes-acceleration/mercedes_acceleration_thumbnail.png
cd ../../..; python tools/preflight.py out/mercedes-acceleration/mercedes_acceleration_short.mp4 --meta out/mercedes-acceleration/meta.json \
  --words videos/mercedes-acceleration/src/words.json --facts videos/mercedes-acceleration/FACTS.md --align-pct 95.6
```
Alignment: 65/68 words plausible by `align.py`'s duration check (95.6%); the 3 short ones are "a"/"A" at fast pace.
Preflight: 12/12 pass.
