# Soft energy (pixel-art loop)

From-scratch, procedural pixel-art recreation of a short 3-scene "chill vibes" clip:
1. rainy roadside store under a giant tower, flooded-street reflection (0–2.5 s)
2. neon ramen shop facade with animated signs (2.5–5.53 s)
3. rainy cyber depot: tower "05", conveyor bridge, green neon, truck, kiosk (5.53–8.2 s)

720x682, 30 fps, 8.2 s. Original lo-fi music bed (`src/music.py`), no samples.

```bash
cd videos/soft-energy/src
python render.py ../../../out/soft-energy/soft_energy.mp4   # full render (~20 s)
python render.py --still 4.6 ../../../out/soft-energy/f.png # single frame
```

Scenes are drawn at native resolution (scene 1: 240x228 at 3x, scenes 2–3: 360x341 at 2x)
with nearest-neighbour upscaling, then bloom + vignette.
