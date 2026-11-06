# Cozy Creator (no-talk aesthetic loop)

12s, 1080x1920, 30fps seamless loop. Main guy edits a car clip at his desk on a rainy
night (ring light + phone recording, monitor timeline, neon car sign, sleeping cat,
lightning at 2.5s/5.9s), looks up at 7.25s and waves until 10s, then goes back to editing.
Audio: synthesised lo-fi (80 BPM, Fmaj7-Em7-Dm7-Cmaj7), rain, thunder, synced key clicks.

Native canvas 135x240, nearest-neighbour x8. Reuses `../new-car-trap/src/pix.py` (sprite,
new seated poses registered at runtime) and `sfx.py`.

```bash
python tools/video.py preview --src videos/cozy-creator/src --out out/cozy-creator
cd videos/cozy-creator/src && python render.py video ../../../out/cozy-creator.mp4
```
