# Mercedes acceleration subscription: "Would you pay $60 a month for 60 horsepower?"

Vertical skit (1080x1920, 30 fps, ~43 s). Same cast, voices (Orus salesman, Fenrir buyer), captions, camera, whip pans
and mix chain as bmw-heated-seats. `render.py` was spliced from bmw-heated-seats/src/render.py (cast, captions, camera,
frame and mix kept) with new parts: a shared `car()` for the EQE / Polestar 2 / Tundra profiles, drawn brand marks, a
dealer lot, service bay, dyno room (hp gauge), finance office and Mercedes showroom, and a `thumb` mode for an upload
thumbnail that is not a frame of the video. `align.py` reads spellings from `script.py`; one-letter words ("a") count as
aligned from 30 ms. `retime.py` tightens pauses (first word at 0.3 s). Nothing is shown on screen for the first 3 s.

Background oddities (never mentioned): a goat on a parked car's roof chewing the sale bunting (lot); a penguin in a hard
hat gliding by on a mechanic's creeper (service bay); an octopus in a headset typing on the dyno computer (dyno room); a
raccoon with a coffee slowly spinning in an office chair (finance office); a giraffe's head down through the ceiling
tiles, chewing a plant (showroom).

```bash
source .venv/bin/activate; cd videos/mercedes-acceleration-subscription/src; C=~/.cache/mercedes-acceleration-subscription
python tts.py $C/raw.wav                                       # one two-speaker Gemini call (Orus + Fenrir)
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python align.py $C/raw16.raw $C/raw_words.json
python retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json
O=../../../out/mercedes-acceleration-subscription
python render.py meta $O/meta.json && python render.py thumb $O/thumbnail.png
python render.py video $C/voice.wav $O/mercedes_acceleration_subscription.mp4
cd ../../..; python tools/preflight.py out/mercedes-acceleration-subscription/mercedes_acceleration_subscription.mp4 \
  --meta out/mercedes-acceleration-subscription/meta.json --words videos/mercedes-acceleration-subscription/src/words.json \
  --facts videos/mercedes-acceleration-subscription/FACTS.md --align-pct 98.9
```
Alignment: 92/93 words (98.9%) force-aligned with plausible durations.
