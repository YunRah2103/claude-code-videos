# Dodge Charger fake exhaust — "My ELECTRIC Dodge has a fake exhaust that's as loud as a Hellcat?!"

Vertical skit (1080x1920, 30 fps, 44.5 s, first word at 0.3 s). It uses the same cast, voices (Fenrir buyer, Orus salesman),
captions, camera, whip pans and mix chain as bmw-heated-seats. The salesman wears Dodge colours: a black suit with a
red tie, red lapel piping, a red pocket square and a red badge. `src/` was copied from bmw-heated-seats. `tts.py`,
`sfx.py` and `retime.py` are unchanged apart from gap and hold values. `align.py` adds Hellcat, Fratzonic and Fratzog.
`render.py` adds the drawn Charger (EV and gas versions), six layered locations, the cards and a synthesised V8-style rumble.

Scenes: 1 Dodge showroom (street windows with traffic, red wall with a live waveform screen); 2 garage (car on the
lift with no tailpipes, speaker rig on the bench); 3 night car meet (skyline, string lights, food truck, crowd with
phones); 4 recording studio (vocal booth, live DAW waveform, mixing desk); 5 suburban street at dawn (sleeping
neighbours wake on the rev, birds scatter, dog barks, Stealth puts them back to sleep); 6 drag strip at night
(floodlights, grandstand, starting lights, EV vs gas race, scoreboard WIN).

Background oddities (never mentioned): a penguin pushing a trolley of fish; a chicken in headphones; a grandma doing
a mobility-scooter burnout; a cow singing in the vocal booth; a horse in a nightcap at an upstairs window; a giraffe in
ear defenders in the grandstand.

Photo: `assets/charger.jpg` is optional. When it is present it appears as the one real car (scene 1 card and thumbnail).
See `assets/CREDITS.txt`.

```bash
source .venv/bin/activate; cd videos/dodge-charger-fake-exhaust/src; C=~/.cache/dodge
python tts.py $C/raw.wav                                       # one two-speaker Gemini call
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python align.py $C/raw16.raw $C/raw_words.json
python retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json
python render.py meta ../../../out/dodge/meta.json
python render.py video $C/voice.wav ../../../out/dodge/dodge_charger_fake_exhaust.mp4
python render.py thumb ../../../out/dodge/dodge_charger_fake_exhaust_thumb.png
cd ../../..; python tools/preflight.py out/dodge/dodge_charger_fake_exhaust.mp4 --meta out/dodge/meta.json \
  --words videos/dodge-charger-fake-exhaust/src/words.json --facts videos/dodge-charger-fake-exhaust/FACTS.md --align-pct 100
```
Alignment: all 119 words were force-aligned. 110 of 119 (92.4%) pass `align.py`'s duration check. The 9 that don't
are single short function words ("a", "it", "I", "to") at 30–60 ms, which is plausible for fast speech.
