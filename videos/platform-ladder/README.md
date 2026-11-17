# Platform ladder — "How much is the car and how much is the badge?"

Vertical skit (1080x1920, 30 fps, ~41 s). Same cast, voices, captions, camera, whip pans and mix chain as tesla-locked /
aston-cygnet / urus-rsq8 / supra-z4. `src/script.py`, `tts.py`, `align.py`, `retime.py` come from supra-z4 (retime adds
reveal holds after each price line); `src/render.py` is built on `urus-rsq8/src/render.py` (branch `ccr-39b55cd6-nh196m`)
with four SUV skins on one shared stance, five showrooms (VW, Porsche, Bentley, Lamborghini, VW) and a price-ladder shot.
`src/sfx.py` is unchanged. Photos in `assets/` were supplied by the user.

Background oddities (never mentioned): penguin behind the Touareg; car parked upside down on the Porsche ceiling;
inflatable-dinosaur costume sipping tea at Bentley; astronaut drifting past the Lamborghini wall; giraffe head through
the VW ceiling.

```bash
source .venv/bin/activate; cd videos/platform-ladder/src; C=~/.cache/platform-ladder
python tts.py $C/raw.wav                                       # one two-speaker Gemini call (Orus + Fenrir)
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python align.py $C/raw16.raw $C/raw_words.json
python retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json
python render.py meta ../../../out/platform-ladder/meta.json
python render.py video $C/voice.wav ../../../out/platform-ladder/platform_ladder.mp4
cd ../../..; python tools/preflight.py out/platform-ladder/platform_ladder.mp4 --meta out/platform-ladder/meta.json \
  --words videos/platform-ladder/src/words.json --facts videos/platform-ladder/FACTS.md --align-pct 100
```
`--align-pct 100`: all 71 words force-aligned in order. The stricter duration heuristic in `align.py` reports 94.4%
(four reduced "a"/"A" articles at 30–50 ms, below its 60 ms floor).
