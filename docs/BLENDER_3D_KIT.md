# Blender 3D kit (cars, track, environment, overlays)

Reusable pieces from `videos/stops-first` for any 3D car / race / road video. Output style: Cycles shaded
flat-colour models, black Freestyle ink on the hero cars, pale technical track, lively low-poly roadside,
2D text and technical overlays composited in Python (PIL).

## Setup (once per container)

```bash
python3.11 -m venv out/bpyenv && out/bpyenv/bin/pip install bpy==4.2.0 numpy   # Blender as a Python module
```
Renders run on the CPU here (no GPU in the cloud container); on a PC with an NVIDIA GPU Cycles is 20-50x faster.

## Pieces

| Need | File | Notes |
|---|---|---|
| Hero cars (lofted body, booleans, wheels, decals, mirrors) | `videos/stops-first/src/blend_cars.py` | `SPEC[key]` = profile curves (metres, x from tail). `build(key)` returns car root, body, wheel hubs, curves, materials. `V3 = True` switches to the redesigned front opening + side line. |
| Body detail on the real surface | `blend_cars.decal / tube / plate / fin` | `decal(name, poly, 'side'/'top'/'front'/'rear', bvh, mat, L)` ray-casts a 2D outline onto the body. |
| Brake glow, heat paint, aero streamlines | `blend_cars.brake_material / heat_material / aero_lines` | Each exposes a Value node you keyframe. |
| Race scene: two cars, lane-scrolling track, orbit camera | `videos/stops-first/src/blend_race.py` | Ground is static; its shader scrolls each lane by that car's distance (`sr`, `sb`), so a stopped car's lane stops. Kerbs, lane lines, grid, brake zone (`bz`, `u0r`, `u0b`), chequered start line, grass, horizon fade. |
| Fast ink | `blend_race.ink_layer(scene, exclude)` | Freestyle runs on a second view layer with only the hero cars; composited over the shaded layer. Keeps 30-35 s/frame at 1080x1920 even with hundreds of props. |
| Lively roadside | `tools/blender3d/envkit.py` | Trees, people (standing, seated crowd, wavers with driver-animated arms), simple parked cars, grandstands, tyre walls, see-through catch fence with plain banners, start gantry, marshal posts, light towers, cones. `build_track_env(edge, period, seed, lines, nolines)` + `animate(env, d_left, d_right, frame)`. Strips repeat every `period` m, so scrolling never jumps. No logos, no text, no downloaded assets. |
| Timing, curves, states, overlays, audio | `videos/stops-first/src/render_v3.py` | Word-anchored beats (`wt()`), schematic speed curves, `states` JSON for Blender, `cam(t)` orbit, 2D text with a paper scrim, technical traces, speed lines, shake, VO + music (18 dB under) + SFX beds, -14 LUFS. |
| Word timings | `videos/stops-first/src/align.py` | faster-whisper + fuzzy alignment to `script.json`, fails under 95 %. |

## Workflow

```bash
cd videos/<topic>/src
python3 render_v3.py states ../../../out/<topic>/states.json            # per-frame car/camera/track values
../../../out/bpyenv/bin/python blend_race.py still STATES OUTDIR 0 180 390   # 3D stills (about 35 s each + build)
V3FRAMES=<dir> python3 render_v3.py still OUTDIR 0 6 13                  # composite text on those stills
../../../out/bpyenv/bin/python blend_race.py preview STATES OUTDIR 0 276 # low-res motion preview (run two halves
../../../out/bpyenv/bin/python blend_race.py preview STATES OUTDIR 276 552  #  in parallel: Freestyle is single-threaded)
V3FRAMES=<dir> python3 render_v3.py video OUT.mp4                       # preview or final MP4 with audio
../../../out/bpyenv/bin/python blend_race.py STATES OUTDIR [i0 i1]      # full-quality frames (split across processes)
```

Always: stills first, then a low-res preview with audio, then the full render. Keep renders in `out/`; never
commit MP4/WAV/frames.

## Reusing for a new video

1. Copy `videos/stops-first/src/{render_v3.py,blend_race.py}` to `videos/<topic>/src/`, keep `blend_cars.py`
   imported from stops-first (or copy it if the cars change), and import `tools/blender3d/envkit.py` as is.
2. New cars: add a `SPEC` entry (profile curves) plus a `features()` branch for the details.
3. New story: change the anchors and curves at the top of `render_v3.py`; the states, camera and overlays follow.
4. New location: change `envkit.build_side()` (what goes in a roadside tile) or the `PALETTE`.

## Gotchas

- Freestyle visibility is the slow part and scales with all visible geometry; keep props out of the ink layer.
- `ShaderNodeMath` has no SMOOTHSTEP; use a Map Range node with SMOOTHSTEP interpolation.
- Floors overexposed by emission ignore base-colour darkening; darken with a Mix Shader instead.
- A camera orbiting the cars must stay inside the roadside props (`edge + 5.6` tyre wall); `cam(t)` keeps the side
  radius under that.
- Building hundreds of people with operators is slow; `envkit.merge_instances` merges meshes with bmesh instead.
