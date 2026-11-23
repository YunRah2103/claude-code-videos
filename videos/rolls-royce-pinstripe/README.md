# Rolls-Royce pinstripe — PS1 low-poly style test

Vertical short (1080x1920, 30 fps, 34.4 s) in a PS1-era low-poly 3D look modelled on the user's "Low Poly Shorts"
reference (kept locally as `out/rr/reference_low_poly_shorts.mp4`, not committed). One narrator (Gemini TTS voice
Charon, one call, lo-fi "PS1" processing in `mix.py`), 25 literal shots (max 2.2 s each), word-by-word yellow captions,
no other overlays. Facts and sources: `SUMMARY.md`. The user's avatar (glasses, spiky hair, navy blazer) is rebuilt
low-poly for the closing question. Comment bait: forklift-driving squirrel in hi-vis (0–5 s), cow on the pub roof.

Renderer: `src/lowpoly.py` is a small numpy software rasteriser (z-buffer, flat shading, affine texture warp,
integer vertex snap, near-plane clipping, per-vertex (Gouraud) coloured point lights, a grime texture on every
untextured face, depth fog, dark grade with vignette and static grain, 15-bit dithered colour, 270x480 upscaled 4x). Models and
hand-drawn textures (Phantom, RR badge, Spirit of Ecstasy, people, squirrel...) are in `src/models.py`.

```bash
source .venv/bin/activate; cd videos/rolls-royce-pinstripe/src; C=~/.cache/rr-pinstripe
python tts.py $C/raw.wav                                   # one Gemini call; stops on any HTTP error incl. 429
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python align.py $C/raw16.raw $C/raw_words.json
python retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json   # tight gaps, atempo to 34.4 s, first word 0.33 s
python render.py sheet ../../../out/rr/sheet.png           # one still per shot
python render.py meta ../../../out/rr/meta.json; python render.py thumb ../../../out/rr/rolls_royce_pinstripe_thumb.png
python render.py video $C/voice.wav ../../../out/rr/rolls_royce_pinstripe.mp4   # ~2.5 min on 4 cores
cd ../../..; python tools/preflight.py out/rr/rolls_royce_pinstripe.mp4 --meta out/rr/meta.json \
  --words videos/rolls-royce-pinstripe/src/words.json --facts videos/rolls-royce-pinstripe/SUMMARY.md --align-pct 97.3
```
Alignment: 112 words, 109 plausible by duration (97.3%); the 3 short ones are the word "a". Preflight 12/12.
