# The New Car Trap

TikTok explainer (37.9s, 1080x1920, 60fps): why a new car loses ~20% of its value in year one.
Final cut: `new_car_trap.mp4`.

## How it's built
- `src/voiceover.mp3` - the TTS voiceover.
- `src/align.py` - forced-aligns the script to the voiceover with pocketsphinx, writing word timings to `words.json`.
- `src/pix.py` - pixel-art assets (car, tags, stamps, weight, money, freshener, etc.) and expression variants of `characters/main-guy`.
- `src/sfx.py` - synthesised sound effects (pops, whooshes, dings, crashes, cha-ching...).
- `src/render.py` - scene timeline, camera punch-ins and shake, word-by-word captions, audio mix and encode.

## Rebuild
```bash
pip install pillow numpy pocketsphinx
cd src
ffmpeg -i voiceover.mp3 -ar 16000 -ac 1 -f s16le vo16k.raw
python align.py vo16k.raw words.json            # only needed if the voiceover changes
python render.py still stills 1.0 8.5 13.3      # preview frames (make the stills dir first)
python render.py video voiceover.mp3 out.mp4    # full render
```
To change the script, edit `SCRIPT` in `align.py`, re-align, and adjust the scene timings in `render.py`.
