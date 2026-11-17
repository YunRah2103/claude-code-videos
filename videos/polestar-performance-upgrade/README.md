# Polestar performance upgrade: "Is 68 horsepower worth twelve hundred dollars?"

Vertical skit (1080x1920, 30 fps, ~42 s). Same cast, voices (Orus salesman, Fenrir buyer), captions, camera, whip pans
and mix chain as mercedes-acceleration-subscription (same splice of bmw-heated-seats/src/render.py and shared `car()`), with a
driveway, Polestar showroom (over-the-air download bar), drag strip (timing board 4.45 s -> 4.2 s, the car launches),
cashier's office (receipt printing) and an underground charging garage. `thumb` makes the upload thumbnail (tilted gold
band, real car photo), not a frame of the video. The user's frunk photo is stored with the number plate cropped out.

Background oddities (never mentioned): a kangaroo bouncing above the neighbour's fence (driveway); a cat in VR goggles
swatting at nothing on the gallery bench (showroom); a tortoise in a racing helmet creeping off the start line (drag
strip); a parrot feeding receipts into a shredder, confetti everywhere (cashier's office); a crocodile in a paddling
pool reading the newspaper (charging garage).

```bash
source .venv/bin/activate; cd videos/polestar-performance-upgrade/src; C=~/.cache/polestar-performance-upgrade
python tts.py $C/raw.wav                                       # one two-speaker Gemini call (Orus + Fenrir)
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python align.py $C/raw16.raw $C/raw_words.json
python retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json
O=../../../out/polestar-performance-upgrade
python render.py meta $O/meta.json && python render.py thumb $O/thumbnail.png
python render.py video $C/voice.wav $O/polestar_performance_upgrade.mp4
cd ../../..; python tools/preflight.py out/polestar-performance-upgrade/polestar_performance_upgrade.mp4 \
  --meta out/polestar-performance-upgrade/meta.json --words videos/polestar-performance-upgrade/src/words.json \
  --facts videos/polestar-performance-upgrade/FACTS.md --align-pct 100
```
Alignment: 93/93 words (100%) force-aligned with plausible durations.
