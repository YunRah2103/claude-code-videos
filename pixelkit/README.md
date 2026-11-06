# pixelkit: native-grid pixel-art video

Free, code-only pipeline: Python 3 + Pillow + NumPy + ffmpeg (libx264). Every
frame is drawn as **palette indices at 180x320** and upscaled ×6 by ffmpeg
`scale=…:flags=neighbor` to 1080x1920. No sub-pixel motion, antialiasing,
alpha blending, smooth scaling or interpolation.

## Commands (run from the repository root)

```bash
python tools/video.py doctor                                   # ffmpeg, PIL, numpy
python -m unittest tests.test_pixelkit                         # engine tests

# 1. preview sheet (7 key moments, native frames ×2)
python episodes/cold-battery/episode.py preview out/cold-battery/sheet.png

# 2. full render: upload MP4 (yuv420p) + yuv444p master + native PNGs
python tools/video.py run --log out/logs/render.log -- \
  python episodes/cold-battery/episode.py render out/cold-battery

# 3. verify (exit 1 if OUR video, the first one, fails any check)
python -m pixelkit.verify out/cold-battery/cold-battery.mp4 \
  REFERENCE.mp4 MINE.mp4 --labels Ours Reference Mine \
  --native-dir out/cold-battery/native --heatmap out/verify
```

Outputs: `out/cold-battery/cold-battery.mp4` (upload),
`cold-battery_master444.mp4` (master), `native/` (one PNG per unique frame +
`frames.json`). Renders take ~15 s; verify takes ~1 min per 13 s clip.

## Module map (`pixelkit/core.py`)

| Need | API |
|---|---|
| Palette loader | `Palette("endesga32" \| "pico8")`, `pal.remap({src: dst})` (palette swap LUT), `pal.ffmpeg_palette_png()` (256-px palette for `paletteuse`) |
| Sprites / tilemap | `sprite(ascii, key)`, `outline()`, `flip()`, `recolor()`, `Canvas.rect/box/line/ellipse/poly/blit/remap`, `tilemap()` |
| Pixel-font text | `PixelFont(size)` (Pixelify Sans, `fontmode="1"`), `BitmapFont()` (hand-coded 3x5), `Canvas.text(..., outline_c, shadow_c, align)` |
| Integer camera | `Camera(x, y).view(world, w, h, shake)`, `shake(step)` |
| Particles on the grid | `Particles.emit/step/draw` (whole pixels per step, `every=n` for slow drift) |
| Stepped clock | `StepClock(duration, 30, holds)` (uneven holds → ~10 unique fps), `cycle(t, durations)`, `tween_int()` |
| Pre-baked rotation | `scale2x()`, `rotsprite()` (Scale2x ×3 → nearest rotate → /8), `bake_rotations(spr, 16)`, `angle_index()` |
| Render | `render(scene, clock, palette, out, scale=6, master=…, native_dir=…, crf=14)` |

`pixelkit/cozyroom.py` is the reusable set (room, props, pet, palette-swap
lighting, HUD). An episode (`episodes/<name>/episode.py`) only defines the
headline, timed captions, beats, car art and speed/battery/light/camera curves.
For a new episode copy `episodes/cold-battery/episode.py` and edit `EPISODE`;
pass `car_art`/`car_key` for a different car (16 angles are baked automatically).
For 8x (135x240) build a 135x240 scene and call `render(..., scale=8)`.

## Encode settings

libx264 `-preset slow -tune animation -crf 14`, High profile, yuv420p,
`bt709` matrix/primaries/transfer, TV range, `+faststart`, 30 fps. Master:
yuv444p, High 4:4:4, CRF 10. The input is split **before** scaling so each
branch does RGB→YUV inside the single nearest-neighbour scale (an earlier
version scaled once and let ffmpeg auto-convert 420→444 bicubically, which put
0.35% non-uniform blocks into the master; now 0.000%). 6 px blocks are even, so
4:2:0 chroma never straddles two art pixels. No dithering. `paletteuse` is not
needed because frames are already palette indices.

## Verify checks (`pixelkit/verify.py`)

* grid: block size/phase found from edge energy folded modulo 2..16 px
* block uniformity: a block fails if its core (1 px trimmed) spans >24 in any
  channel. Hard limit ≤0.5 %
* held frames: consecutive frames identical when no native pixel (block mean)
  moves >28. Hard limit ≥40 % of pairs
* pre-encode colours from `--native-dir` ≤ `--palette-size` (32)
* output exactly 1080x1920
* info: unique frames/s, hold lengths, % animated blocks, decoded palette estimate

Tolerances absorb codec noise. They were calibrated on the decoded Reference
(HEVC) and on our own x264 renders of flat blocks.

## Analysis and results (2026-11-06)

| metric | Ours | Reference | Mine |
|---|---|---|---|
| source | h264 30 fps | HEVC 30 fps | h264 60 fps |
| grid / native res | 6 px / 180x320 | 8 px / 135x240 | 6 px / 180x320 |
| non-uniform blocks (≤0.5%) | **0.001%** | 0.025% | 0.933% FAIL |
| held pairs (≥40%) | **65.8%** | 27.1% FAIL | 0.0% FAIL |
| unique frames/s | 10.3 | 21.9 | 60.0 |
| hold lengths (frames×count) | 2×34 3×78 4×22 | 1×150 2×57 3×12 | 1×1080 |
| decoded palette estimate | 34 | 263 | 297 |
| pre-encode colours (≤32) | **31** | n/a | n/a |
| verify | PASS | FAIL (held) | FAIL |

What the Reference does and Mine doesn't:

* The Reference is almost entirely on its 8 px grid. Its only off-grid blocks
  sit in the small monitor screens. Mine has a 6 px grid, but its off-grid
  heatmap shows glowing neon bars and tubes, the glowing handle text, the
  monitor glow frame, sparkle bursts and soft light-gradient edges.
* Mine is 60 unique fps (every frame differs). The Reference holds frames.
  Most of its 3.7% animated blocks update about once per second, and the room
  itself is static.
* Honest caveat: the Reference fails the 40% held-pair rule as a whole frame.
  Its animated monitor screens change on about 2 of every 3 frames, so only 27%
  of pairs are fully identical. Individual elements are held, but the screens
  are not. Our output beats it on that metric.
* Neither reference's palette can be measured exactly from a lossy decode.
  Codec noise inflates the 263/297 estimates. The Reference also uses
  translucent light-beam overlays. We use hard-edged palette-swap regions
  (moon beam, lamp pool, night-light pool) for the same effect.

## Licences

* Palette: ENDESGA 32 (Endesga, lospec.com, free to use).
* Font: Pixelify Sans Medium, SIL OFL 1.1 (`fonts/PixelifySans-OFL.txt`).
  Bundled from a local copy; Press Start 2P was not installed.
* 3x5 bitmap font, all sprites, props, room and car: drawn procedurally in this
  repo. No third-party art.

## Known limits

* Godot, Pixelorama and LibreSprite are not installed, so sprites are ASCII/procedural.
  No CC0 car pack was downloaded (no network installs).
* No audio track yet. Mux SFX/voice later with `-c:v copy`.
* At CRF 14 the flat art encodes to ~0.4 Mbps, well under 15–25 Mbps. That is
  expected for flat colour. If a platform needs a minimum bitrate, raise it with
  `crf` or add `-b:v`.
