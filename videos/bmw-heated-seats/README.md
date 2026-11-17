# BMW heated seats — "Would you pay a monthly fee for something your car already has?"

Vertical skit (1080x1920, 30 fps, ~43 s). Same cast, voices (Orus salesman, Fenrir buyer), captions, camera, whip pans
and mix chain as tesla-locked / aston-cygnet / urus-rsq8 / supra-z4 / platform-ladder. `src/` is copied from
platform-ladder: `tts.py`, `sfx.py` unchanged; `align.py` adds "2022"/"BMW" spellings and "hardware's"; `retime.py`
trims raw pauses and starts the first word at 0.3 s; `render.py` adds a BMW coupe-SUV skin, map room, subscription
screen and press-conference sets, info cards and five new oddities.

Background oddities (never mentioned, kept off-centre): a snowman soaking in a steaming hot tub with a mug, melting
(showroom); a flamingo riding a robot vacuum (map room); two sheep stacked on a filing cabinet (subscription office); a
llama with a press pass taking selfies on a stick (press conference); a mother duck driving a tiny red ride-on car,
ducklings waddling behind (showroom again). Camera adds a hard cut closer on the car, a drift across the map and a
handheld jolt on "outrageous".

```bash
source .venv/bin/activate; cd videos/bmw-heated-seats/src; C=~/.cache/bmw-heated-seats
python tts.py $C/raw.wav                                       # one two-speaker Gemini call (Orus + Fenrir)
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python align.py $C/raw16.raw $C/raw_words.json
python retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json
python render.py meta ../../../out/bmw-heated-seats/meta.json
python render.py video $C/voice.wav ../../../out/bmw-heated-seats/bmw_heated_seats.mp4
cd ../../..; python tools/preflight.py out/bmw-heated-seats/bmw_heated_seats.mp4 --meta out/bmw-heated-seats/meta.json \
  --words videos/bmw-heated-seats/src/words.json --facts videos/bmw-heated-seats/FACTS.md --align-pct 100
```
Alignment: 79/79 words force-aligned and plausible by `align.py`'s duration check (100%).
