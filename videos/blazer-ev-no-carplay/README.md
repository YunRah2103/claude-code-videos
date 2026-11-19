# Blazer EV, no CarPlay — "A 2024 electric car with no CarPlay?"

Vertical skit (1080x1920, 30 fps, ~46 s, 6 scenes) on the shared showroom engine `videos/showroom-kit/` (same buyer,
Fenrir/Orus voices, captions and mix chain as bmw-heated-seats). Chevrolet showroom; the real Blazer EV (and the Prologue) sit on a
glossy platform and slide out/in on each topic change. Hook: the car is already sliding on frame 1, the first word lands at
0.30 s, and nothing but captions is on screen before 3 s. `src/script.py` holds the lines, `src/show.py` the cars,
cards and gags. Background gags (never mentioned): a duck driving a ride-on car, an astronaut drifting past,
a horse typing at a desk, a cactus on a skateboard, a goldfish bowl on a leash, a bedsheet ghost.

```bash
source .venv/bin/activate; K=videos/showroom-kit; C=~/.cache/blazer-ev-no-carplay; O=out/blazer-ev-no-carplay
python $K/prep_photos.py chevy_blazer_ev honda_prologue                      # once: cut-outs -> ~/.cache/showroom/cars
cd videos/blazer-ev-no-carplay/src
python ../../showroom-kit/tts.py $C/raw.wav                                   # ONE two-speaker Gemini call
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python ../../showroom-kit/align.py $C/raw16.raw $C/raw_words.json
python ../../showroom-kit/retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json
python render.py meta ../../../$O/meta.json
python render.py video $C/voice.wav ../../../$O/blazer_ev_no_carplay.mp4
python render.py thumb ../../../$O/blazer_ev_no_carplay_thumb.png
cd ../../..; python tools/preflight.py $O/blazer_ev_no_carplay.mp4 --meta $O/meta.json \
  --words videos/blazer-ev-no-carplay/src/words.json --facts videos/blazer-ev-no-carplay/FACTS.md --align-pct 100
python $K/prep_photos.py credits $O/CREDITS.txt chevy_blazer_ev honda_prologue
```
Alignment: 109/109 words plausible by `align.py`'s token-aware duration check (100%). `script.py` sets TEMPO = 1.1 (pitch-preserving).
