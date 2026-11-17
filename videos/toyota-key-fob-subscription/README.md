# Toyota key-fob subscription: "Would you pay $8 a month to start your own truck?"

Vertical skit (1080x1920, 30 fps, ~39 s). Same cast, voices (Orus salesman, Fenrir buyer), captions, camera, whip pans
and mix chain as mercedes-acceleration-subscription (same splice of bmw-heated-seats/src/render.py and shared `car()`), with a
snowy driveway (fob presses that fizzle), Toyota showroom, server room (fob -> truck -> connected services -> refused),
Toyota press room and a frozen car park at night with snow; buyer shivers and holds the fob. `thumb` makes the upload
thumbnail (red headline band, real fob photo), not a frame of the video. `align.py` reads spellings from `script.py`; one-letter words ("a") count as
aligned from 30 ms. `retime.py` tightens pauses (first word at 0.3 s). Nothing is shown on screen for the first 3 s.

Background oddities (never mentioned): a moose with its tongue stuck to a frozen mailbox (driveway); a seal balancing a
beach ball on a display plinth (showroom); a carrier pigeon with a letter flying in and out of the server racks (server
room); a sloth hanging from the stage light, taking notes (press room); a polar bear sunbathing in a deck chair with
sunglasses and a cocktail (frozen car park).

```bash
source .venv/bin/activate; cd videos/toyota-key-fob-subscription/src; C=~/.cache/toyota-key-fob-subscription
python tts.py $C/raw.wav                                       # one two-speaker Gemini call (Orus + Fenrir)
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python align.py $C/raw16.raw $C/raw_words.json
python retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json
O=../../../out/toyota-key-fob-subscription
python render.py meta $O/meta.json && python render.py thumb $O/thumbnail.png
python render.py video $C/voice.wav $O/toyota_key_fob_subscription.mp4
cd ../../..; python tools/preflight.py out/toyota-key-fob-subscription/toyota_key_fob_subscription.mp4 \
  --meta out/toyota-key-fob-subscription/meta.json --words videos/toyota-key-fob-subscription/src/words.json \
  --facts videos/toyota-key-fob-subscription/FACTS.md --align-pct 99.0
```
Alignment: 96/97 words (99.0%) force-aligned with plausible durations.
