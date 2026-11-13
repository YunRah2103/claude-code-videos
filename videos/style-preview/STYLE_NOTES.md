# Style preview — notes

Output (not committed, in `out/style-preview/`): `preview.mp4` (1080x1920, 30 fps, 24.0 s, 6 x 4.0 s),
`style-1.mp4` … `style-6.mp4`, contact sheets and `checks/checks.txt`. Audio: silent AAC track
(no music path was given; `render.py preview --music PATH` mixes one in, looped, -16 LUFS, 1 s fade).

**Draft notice:** styles 1, 2 and 4 are Blender renders at **720x1280**, upscaled to 1080x1920 in post.
A full-res Cycles test ran at 29.6 s/frame (style 1, 4-core CPU), about 1 h per style, so I used the draft.
Text, streamlines, ribbons, arrows and overlays are drawn at full 1080x1920. Styles 3, 5, 6 are native 1080x1920.

## Toolchain and benchmark
- Blender 4.2.3 LTS downloaded from download.blender.org (not committed). EEVEE-Next runs under Xvfb +
  Mesa llvmpipe but the first frame of a default cube took 34.9 s (shader compile), so I used **Cycles CPU**,
  20–24 samples, OIDN denoise, adaptive sampling. three.js/Remotion was not needed.
- Post: numpy + PIL only (no new pip deps). Text uses system Inter / DejaVu Sans Mono.
- Car: procedural (extruded profile + bevel, tapered greenhouse, 5-spoke wheels). No model download, no logo.
- Times on this 4-core cloud container. "60-frame benchmark" = frames 0–59 of the first pass.
  Styles 3/5/6 were timed while Blender was also running, so their numbers are pessimistic.

| # | Style | Tool | 60-frame benchmark | Full 120 frames (render + post) | Difficulty 1–5 |
|---|---|---|---|---|---|
| 1 | Light tunnel airflow | Cycles + numpy streamlines | 803 s (13.4 s/f) | 1658 s + 75 s ≈ 29 min | 4 |
| 2 | Tilt-shift miniature | Cycles + depth-masked blur | 461 s (24 unique frames, 19 s/f) | 1101 s (48 unique) + 89 s ≈ 20 min | 3 |
| 3 | Satisfying loop | PIL / numpy | 102 s (1.7 s/f, 3 procs) | 213 s ≈ 3.5 min | 2 |
| 4 | Cutaway | Cycles (boolean cut, shell) + PIL arrows | 957 s (16 s/f) | 1783 s + 42 s ≈ 30 min | 4 |
| 5 | Holographic wireframe | numpy projection + PIL + bloom | 96 s (1.6 s/f) | 197 s ≈ 3.3 min | 2 |
| 6 | Kinetic type + light trails | PIL / numpy (car sprite from Cycles) | 50 s (0.84 s/f) | 101 s ≈ 1.7 min | 2 |

## Checks (`python check.py`)
- ffprobe: all 7 files h264 1080x1920 30 fps + AAC; clips 4.00 s / 120 frames, preview 24.02 s / 720 frames.
- No black first frames (frame-0 mean luma 15–210 of 255; styles 1 and 5 are dark by design).
- Motion in the first 2 s: every style has a mean frame difference > 1.5 levels. Style 2 has 36/59
  unchanged frame pairs on purpose (12 fps holds); it still changes on every 12 fps step from frame 0.
- Style 3 loop: frame 120 (the next loop's start, computed without wrapping) equals frame 0 exactly (diff 0.000);
  I render 0–119 so the loop does not show a duplicated frame. "Last = first" is met in that sense.
- Safe area: hook, counter, readouts and tags all sit in 12–62 % height, x 54–918 px. Nothing important below 80 %.

## Self-critique (honest)
1. **Light tunnel** — the strongest look. Weak: the streamlines are a 2D post effect bent over the silhouette,
   not a simulation; air never flows under the car or around the sides, and the wake turbulence is sine noise.
   The car body is dark and mostly reads as a silhouette; the procedural car has a slab-sided, kit-car shape.
   720p upscale shows as softness on the car (the lines are sharp).
2. **Tilt-shift** — reads as a toy instantly and the blur sells the scale. Weak: the headlight strip looks like a
   floating white sticker from the high angle; the scenery is primitive cones/boxes; the ribbons are flat 2D
   lines on top, not in the scene; 12 fps holds make the counter step (intended, but some will read it as lag).
3. **Satisfying loop** — clean and perfectly looping; cheapest to make. Weak: flat vector wheel, no car in shot,
   so "drag" is only told by the bar; the counter goes back down to 100 to close the loop, which slightly fights
   the "DOUBLE THE SPEED?" beat. Motion-blurred spokes still show faint stepping at 200 km/h.
4. **Cutaway** — most "explainer" feel; internals read clearly. Weak: the car is too big for the frame (nose and tail
   touch the edges, tail in the right 15 %), internals are placeholder blocks, the arrows are 2D and do not follow
   the camera orbit in depth, the orange pressure glow looks like a blob. Slowest render.
5. **Holographic wireframe** — fast and on-trend. Weak: the mesh is low-poly so the wireframe is sparse and
   boxy; it's an x-ray (no hidden-line removal) so far-side edges clutter; the scan plane is a flat magenta card;
   lots of empty black between the readouts and the car.
6. **Kinetic type** — the numbers land hard and it's the clearest message. Weak: the car is tiny and only on screen
   for part of the clip; light streaks are random horizontal lines, not tied to the car; looks like a generic
   template more than a branded style.

## Reproduce
```bash
B=/path/to/blender-4.2.3/blender; O=out/style-preview; cd videos/style-preview/src
$B -b -P scene.py -- mesh $O/blender && $B -b -P scene.py -- sprite $O/blender
for s in 1 2 4; do $B -b -P scene.py -- $s $O/blender/s$s --draft; done   # drop --draft for 1080x1920
for s in 1 2 3 4 5 6; do python3 render.py frames $s && python3 render.py encode $s; done
python3 render.py preview [--music PATH] && python3 check.py
```
