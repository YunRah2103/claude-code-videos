# Recipe: rainy neon pixel-art loop (reference-matched, original art)

Target: 8.2 s, 720x720, 30 fps, 3 hard-cut scenes, rain, neon flicker, slow drift, lo-fi ambient audio.
The reference clip is another artist's work (credited "Kirby_pixel"); this recipe copies its
*structure, timing and palette*, never its pixels. Draw original scenes and signage.

## Steps (an AI can follow these 1:1)
1. Measure the reference: `python videos/neon-street-pixel/src/analyze_reference.py REF.mp4 spec.json`
   (duration, size, fps, motion per second, palette). Committed result: `src/reference_spec.json`.
2. Find cuts: `ffmpeg -i REF.mp4 -vf "select='gt(scene,0.2)',showinfo" -f null -` -> 2.50 s and 5.53 s.
3. Look at one frame per scene (`ffmpeg -ss T -i REF.mp4 -frames:v 1 f.png`); write a scene function per shot.
4. Work at 180x180, scale x4 nearest-neighbour. Per scene: gradient sky, silhouettes, 2-3 neon accents,
   lit windows, ground; draw a wider canvas (240 px) so the camera can drift ~6 px/s.
5. Wet ground = flipped copy of the scene above the waterline, wobbled by sine, darkened, tinted.
6. Motion: rain streaks (seeded), neon flicker (`flicker()`), drift, vignette, 4% scanlines.
7. Audio: pad chords (Am9 / G / Fmaj7), soft pluck arpeggio, filtered-noise rain, vinyl crackle, fades.
8. Preview, then full render:
```bash
python tools/video.py doctor
python videos/neon-street-pixel/src/render.py still out/neon 1.0 3.5 6.5   # then view a hstack of the three
python tools/video.py run --log out/logs/render.log -- python videos/neon-street-pixel/src/render.py video out/neon-street.mp4
python tools/video.py probe out/neon-street.mp4
```
Palette per scene: teal dusk (#0e5a74-#2f95a8, red ring, warm windows) / near-black blue with red
disc sign + yellow window / deep blue (#07204a) with green neon. Tune by editing the scene functions.
