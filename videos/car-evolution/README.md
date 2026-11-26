# car-evolution — "How the car was made" (64 s vertical, cinematic low-poly 3D)

One car on a glowing turntable gains one invention per stage (scan-plane upgrade): Benz 1886 → hand crank → 1912 Cadillac starter →
Ford Model T + assembly line → 1959 Volvo three-point belt → 1977 Oldsmobile microprocessor → today's Tesla (code vs Boeing 737, $2,000 boost).
Yub from `characters/yub-3d`, renderer/engine from `lib/cine3d`. Facts, narration, sources, credits: `SUMMARY.md`.

`src/eras.py` = six era worlds (1886 cobblestone street, brass-era garage, 1910s town, 1959 Swedish coast, 1977 neon city, modern plaza)
and `world_wipe()`, which sweeps the whole world into the next era with the scan plane.
`src/world.py` = stage, the evolving car `car(stage, ...)`, `modern()`, `wipe()` scan upgrade, brand badges, props, llama oddity.
`src/car.py` = shots (36), captions, top labels, SFX; subclasses the engine for 0.2 s cross-dissolves + optional motion-blur sub-frames.

```bash
cd videos/car-evolution/src; C=../../../out/ce
python tts.py car $C/car_raw.wav                       # ONE Gemini call; exits on any HTTP error incl. 429
ffmpeg -i $C/car_raw.wav -ar 16000 -ac 1 -f s16le $C/car16.raw && python align.py car $C/car16.raw $C/car_rw.json
TARGET=64 python retime.py car $C/car_raw.wav $C/car_rw.json $C/car_voice.wav car_words.json
python car.py check; python car.py sheet $C/sheet.png
python car.py video $C/car_voice.wav $C/music_ext.wav $C/car.mp4      # ~1 h on 4 cores
```
Music: Kevin MacLeod "Hot Swing" (incompetech, CC BY 4.0) extended to 100 s by a phrase-aligned loop (bars 0-22, 6-22, 6-28 at 144 BPM).
