# Mercedes "Acceleration Increase": "Would you pay $1,200 a year to be 0.9 seconds faster?"

Vertical skit (1080x1920, 30 fps, 47.2 s). Same buyer (Fenrir), salesman voice (Orus), captions, camera, whip pans and mix
chain as bmw-heated-seats; a new salesman look (silver hair, moustache, EQ-blue tie). Six scenes: Mercedes showroom, dyno
cell (gauge locked between 288 and 349 hp), store screen, night drag strip, backlash room, showroom. Real EQE 350 4MATIC
photos (Wikimedia Commons, CC BY-SA 4.0, Damian B Oh). The star is drawn in code to the real logo's geometry. Facts and
sources: `SUMMARY.md`. Background oddity (never mentioned): a cow in a racing helmet in every scene.

`src/`: `script.py` (lines + `SAY` spoken forms shared by TTS and the aligner), `tts.py` (one call, exits on any HTTP
error, including 429), `align.py`, `retime.py` (also splits long pauses inside a line), `render.py`, `thumb.py`, `sfx.py`.

```bash
source .venv/bin/activate; cd videos/mercedes-acceleration/src; C=~/.cache/mercedes-acceleration
python tts.py $C/raw.wav
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python align.py $C/raw16.raw $C/raw_words.json
ffmpeg -i $C/raw.wav -af atempo=1.17 -ar 24000 -ac 1 $C/raw_fast.wav     # word times divided by 1.17 -> $C/fast_words.json
python retime.py $C/raw_fast.wav $C/fast_words.json $C/voice.wav words.json
python render.py meta ../../../out/mercedes-acceleration/meta.json
python render.py video $C/voice.wav ../../../out/mercedes-acceleration/mercedes_acceleration.mp4
python thumb.py $C/voice.wav ../../../out/mercedes-acceleration/mercedes_acceleration_thumbnail.png
cd ../../..; python tools/preflight.py out/mercedes-acceleration/mercedes_acceleration.mp4 --meta out/mercedes-acceleration/meta.json \
  --words videos/mercedes-acceleration/src/words.json --facts videos/mercedes-acceleration/SUMMARY.md --align-pct 96
```
Alignment: 119/124 words plausible (96%). The 5 flagged words are very short "a"s. Preflight: 12/12 passed.
