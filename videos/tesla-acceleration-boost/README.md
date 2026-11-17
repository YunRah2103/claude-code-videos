# Tesla Acceleration Boost — "I paid for the car, why is the speed extra?"

Vertical skit (1080x1920, 30 fps, 42.5 s). Same cast, voices (Orus salesman, Fenrir buyer), word-by-word captions,
camera, whip pans and mix chain as bmw-heated-seats. `src/` is copied from bmw-heated-seats: `tts.py`, `sfx.py`,
`retime.py` unchanged apart from timings; `align.py` maps "$2,000"/"$400"/"4.4"/"3.9" to their spoken words and its
plausibility check is now per spoken token plus voiced audio under the word; `render.py` adds a Tesla Model 3 skin
(Stealth Grey, black glass roof, aero wheels), five sets (Tesla store lot, driveway at night on the Wall Connector,
the Tesla app on a giant phone in a cafe, drag strip with start lights and a launch, finance office), cards, a `thumb` mode
and five adult deadpan oddities. User photos in `assets/` are shown as cards and in the app.

Hook: first word at 0.30 s, camera and buyer already moving on frame 1, no overlay before 3.0 s (`HOOK`).

Background oddities (never mentioned): suit-and-tie man eating cereal standing on a parked car's roof (lot); neighbour
mowing at night in a bathrobe with a head torch and red wine (driveway); scuba diver reading the financial pages over an
espresso (cafe); businessman in a racing helmet riding an office chair on a fire extinguisher (drag strip); banker feeding
cash into a shredder while sipping champagne (finance office).

```bash
source .venv/bin/activate; cd videos/tesla-acceleration-boost/src; C=~/.cache/tesla-acceleration-boost; O=../../../out/tesla-acceleration-boost
python tts.py $C/raw.wav                                       # one two-speaker Gemini call (Orus + Fenrir)
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python align.py $C/raw16.raw $C/raw_words.json
python retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json
python render.py meta $O/meta.json && python render.py thumb $O/thumbnail.png
python render.py video $C/voice.wav $O/tesla_acceleration_boost.mp4
cd ../../..; python tools/preflight.py out/tesla-acceleration-boost/tesla_acceleration_boost.mp4 --meta out/tesla-acceleration-boost/meta.json \
  --words videos/tesla-acceleration-boost/src/words.json --facts videos/tesla-acceleration-boost/FACTS.md --align-pct 99.0
```
Alignment: 102/103 words (99.0%). Preflight: 12/12 passed.
