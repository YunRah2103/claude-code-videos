# Gold engine bay (1080x1920, ~21 s)

Shaded 3D "teardown" short. `src/scene.py` ray-traces a generic mid-engine rear section once
(cached in `out/gold-engine-bay/cache/`, ~3 min on 4 cores); `src/render.py` blends its lit layers per
frame (heat, warming carbon, foil wrap, DOF, bloom) and draws the HUD.

**One timing source:** `src/timing.json`. Beats are anchored to words (`timing.py BEATS`), so phase 2 only
replaces the word times:

```bash
cd videos/gold-engine-bay/src
python3 timing.py estimate                      # phase 1: 2.7 words/s
python3 timing.py from-words ../../../out/gold-engine-bay/words.json   # phase 2: aligned voice
python3 render.py still ../../../out/gold-engine-bay/st 0 6 13
python3 render.py video ../../../out/gold-engine-bay/preview.mp4    # quiet placeholder tone
python3 check.py ../../../out/gold-engine-bay/preview.mp4           # probe, sheet, motion, seam, stills
python3 render.py elements 0 6 13                                   # element count per frame
```

Phase 2: set `PREVIEW = False`, mux the voice instead of `audio()`'s placeholder tone.
Layout: text 12-62% height, x < 85% (asserted for pills); tags tiny in the top corners.
