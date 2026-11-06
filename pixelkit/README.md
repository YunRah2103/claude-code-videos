# pixelkit: native-grid pixel-art video

Free, code-only pipeline: Python 3 + Pillow + NumPy + ffmpeg (libx264). Every
frame is drawn as **palette indices at 135x240** and upscaled ×8 by ffmpeg
`scale=…:flags=neighbor` to 1080x1920 (the engine also does 180x320 ×6). No
sub-pixel motion, antialiasing, alpha blending, smooth scaling or interpolation.

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
| Organic detail | `wobble_mask()` (irregular silhouettes, chipped corners), `blob_mask()`, `shade(mask, ramp)` (clustered 4-tone hue-shifted ramp), `texture(kind=noise\|grain\|weave\|dither\|wrinkle\|specks)`, `rotate_nn()` (nearest rotation at native res), `curve_points()`/`cable()` (pixel-perfect curves), `scatter()` (3-8 px clutter) |
| Render | `render(scene, clock, palette, out, scale=8, master=…, native_dir=…, crf=14)` |

`pixelkit/cozyroom.py` is the reusable set (room, props, pet, palette-swap
lighting, HUD). An episode (`episodes/<name>/episode.py`) only defines the
headline, timed captions, beats, car art and speed/battery/light/camera curves.
For a new episode copy `episodes/cold-battery/episode.py` and edit `EPISODE`;
pass `car_art`/`car_key` for a different car (16 angles are baked automatically).

## Organic detail rules (how the set follows them)

* Hero objects (bed, blanket, rug, desk, dresser, cushion, beanbag, panels) are
  `wobble_mask`/`blob_mask` shapes. Edges jog by 1-2 px every 3-9 px, corners
  are chipped and the blanket hangs over with depth-2 folds.
* Diagonals: the rug (-4°), poster (-7°), keyboard, laptop (18°), pizza box
  (27°), t-shirts, books, sneakers, controller and pillow are rotated with
  `rotate_nn` at native resolution. Cables are curves (`cable`).
* Every surface is textured: board grain and broken seams, weave on fabrics,
  wrinkles on cloth, specks on walls, asphalt and the HUD panels.
* Shading uses 4-tone ramps with cool shadows and warm highlights (e.g. floor
  `3e2731→733e39→b86f50→c28569`, blanket `68386c→b55088→f6757a→e8b796`) in
  clustered bands that follow each silhouette. NIGHT/MOON/WARM are index
  remaps that keep ramp tones distinct, so the texture survives the dark.
* Clutter is concentrated, not sprinkled. An open wardrobe on the back wall
  is packed with hanging clothes, with folded piles on its floor and a hoodie
  over the door. About 13 garments (jeans, hoodies, tees, towels), socks, a shoe
  and an overflowing laundry basket spill out of it in a heap that thins
  across the floor (`wardrobe()`). The only other mess is the coder's: paper
  balls round the bin, a pizza box and empty energy cans by the chair.
* A person coding: `CODER` (main-guy palette, seen from behind) types in
  stepped alternating poses at a desk with two monitors. The left monitor
  shows syntax-coloured code that types and scrolls at ~11 chars/s with a
  blinking cursor; the right one shows the battery graph. There is an RGB
  keyboard, a mug with steam, energy drinks, a rubber duck and sticky notes.
  The coder turns to look when the car cranks, and is lit by screen glow at
  night.
* Large-area shapes that run off-frame (walls, front wall) extend 3 px past it,
  so their straight outer shading band is never visible.

## Perspective (`pixelkit/persp.py`): real top-down 3D, still pixel-perfect

The camera sits above the room centre and looks straight down. World x/y are
floor pixels and z is height. A point at height z moves away from the centre
by f/(f-z), so walls become slanted faces and tall props lean outward.

* `Persp.P(x, y, z)` projects a world point to the screen.
* `Persp.warp(c, img, plane, k, a0, a1, b0, b1)` paints a flat pixel-art
  texture onto a floor, wall or box face. Each covered screen pixel is
  inverse-mapped to the nearest texture pixel (no blending), so edges come
  out as staircases.
* `Persp.box(...)` draws the faces turned toward the camera plus the top,
  with dashed lit edges, rims and floor contact shadows.
* `Persp.extrude(...)` handles blob footprints such as beanbags.
* `core.nick_edges` is a final pass that chips one pixel every 12 px along
  any edge running straight for more than 14 px. Perspective keeps
  axis-aligned box edges ruler-straight, and this adds the irregularity an
  artist would add by hand.

## Lighting & shading (what makes it read as 3D)

* **Stepped light levels:** a light field (ambient minus corner/junction
  occlusion and a vignette, plus monitor, lamp and window light) is
  quantised into 4 bands: deep shadow, shadow, normal, lit. Each band is a
  palette swap (`DIM2`/`DIM`/`LIT`) with a 1 px dithered seam between bands.
  Shadows shift cool (to navy) rather than crushing to black, so seams and
  texture survive. The static room is lit once. Characters use the same map
  without dither, so they get clean bands.
* **Cast shadows:** furniture throws shadows across the floor away from the
  window (footprint swept along the light direction by its height).
* **Round volume shading:** `core.shade_round` treats a mask as a
  half-ellipsoid with Lambert light from the top-left, in 4 clean bands plus
  an optional glint. It is used for the beanbag, bear, plush, pillow, dog,
  and the player's hair and hoodie.
* **Face lighting:** faces turned toward the window are lighter, faces turned
  away are darker. Lit top edges are dashed.

## Gamer-room wallpaper (`pixelkit/gameroom.py`)

A 10 s seamless loop (no captions) that follows the composition and mood of
the reference wallpaper: tall top-down room, console shelf, three monitors,
a cheering player, a dog on a purple rug, plushies on a beanbag, the bed, a
window light beam with dust, posters, a game box, a pizza box and crates.
Everything is drawn in code. The reference's characters, logos and artwork
(the plush character, console brands, posters) are **not** reproduced.
Original stand-ins are used instead: a round grey bear, unbranded consoles,
car-themed posters and box art.

```bash
python episodes/gamer-room/episode.py preview out/gamer-room/sheet.png
python tools/video.py run --log out/logs/gamer.log -- \
  python episodes/gamer-room/episode.py render out/gamer-room
python -m pixelkit.verify out/gamer-room/gamer-room.mp4 --native-dir out/gamer-room/native
```

* Calm rebuild. The flat-area rule is met with **structure**, not texture:
  floor planks, wall panels, desk planks, quilt seams and rug bands every
  9-10 px, each with a 1 px gap every 16 px. Props are outlined in their own
  darkest tone; only the characters get black outlines. Clutter is cut to
  two small items.
* Light: a soft moonbeam palette swap with a brighter streak inside (two
  clean bands, no dither) and a warm lamp. The desk is plum with mauve lit
  edges.
* There is no olive in ENDESGA 32; the earlier checker-mixed olive floor was
  dropped for plain dark planks.
* Loop-safe animation: every cycle divides 10 s. Gamer cheer (5 s), dog tail
  (1 s) and breathing (2 s), clouds on the monitor, 4 game scenes, one city
  light blinking, and dust motes drifting 60 px per loop. Frame 0 equals
  t = 10 s (tested).
* Result: PASS 7/7. Edges 19 px, flat 12x12, 30 colours, held 75%, median
  brightness 43 (Reference 47).

## Cozy pass (calm, not overstimulating)

Measured as "animated blocks": the share of the frame that changes at least
once a second. It went from 15% to **1.9%**; the Reference is 3.7%.

* Camera locked; no pans and no shake (the Reference never moves its camera).
* One warm light family: string lights are steady amber and pink with a
  single slow twinkle. The desk lamp and night-light are larger warm pools.
* Neon cut down to one soft sign (salmon/mauve) with a single blink as it
  warms up, a dim steady LED strip, and cyan only on the code screen. No RGB
  keyboard wave and no glowing kerbs.
* Slower motion: the car laps about 35% slower, with typing, cursor, cat
  breathing/blinking and snow all on longer holds.
* Car drawn with a `SOFT` swap (no pure white, cyan or hot pink).
* HUD in warm cream/salmon/tan on quiet navy-bordered panels.

## Refinement pass (clean, designed detail)

* Surfaces use `pattern()` (core): deterministic lattices instead of random
  specks:
  * board grain on the floor and furniture
  * offset weave on the rug and fabrics
  * diagonal quilting on the blanket
  * quiet dot lattices on the asphalt, infield, wardrobe interior and panels

  Every pattern has a period under 12 px, so the flat-region rule holds
  without noise. Cloth keeps a few folds (`wrinkle` at half the old density).
* Floor: uniform 8 px boards with a nail gap every 16 px, a lit edge, and
  butt joints every 48 px staggered per board.
* Silhouettes: `wobble_mask` uses longer runs on long sides (up to 17 px
  between 1 px jogs), so big shapes read as hand-drawn rather than ragged.
* Light pools have a 4 px 50% dither falloff ring, the classic pixel-art
  way to soften light without blending.
* HUD: chamfered panels, 1 px neon border with accent rivets every 12 px,
  diamond-lattice fill.
* Curated clothes palette (plum / soft grey / denim + one maroon accent),
  arranged in a tidy cascade from the wardrobe. The coder keeps their own
  colours under the screen glow.

## Colour mood: dark Reference look + neon

The Reference, matched to ENDESGA 32, is about 70% INK/NAVY/DKSLATE (very dark
navy and blue-grey), then dark purple-brown, slate, teal and plum, with tiny
pink and white accents. Its median brightness is 46/255. The set reproduces
that with palette swaps only:

* `MOOD` remaps every drawn index once per frame: wood becomes teal/blue-grey,
  fabrics deep plum, plants and grass dark teal-green, the cat muted brown,
  whites soft grey. Ramp tones stay distinct, so textures survive.
* Lighting (`Lights.apply`), all hard-edged index swaps:
  * Before `beats.night`: a ceiling-light pool (`LIFT`) and a warm lamp.
  * After: a moonbeam (`LIFT`), a magenta monitor glow (`PGLOW`, doubled
    near the screens), a warm desk-lamp pool, a pink night-light pool, and a
    cyan underglow (`CGLOW`) that follows the car.
* Neon is drawn after lighting, so it stays full brightness:
  * a car-silhouette neon sign that flickers on in stepped frames
  * an LED strip along the baseboard
  * pink/cyan track kerbs and cyan centre dashes
  * string lights
  * code and battery monitors and the RGB keyboard
  * the cat's green eyes
  * the car itself
* HUD: ink panels with neon edges (hot-pink headline, plum captions) and
  cyan/hot-pink caption highlights.

## Encode settings

libx264 `-preset slow -tune animation -crf 14`, High profile, yuv420p,
`bt709` matrix/primaries/transfer, TV range, `+faststart`, 30 fps. Master:
yuv444p, High 4:4:4, CRF 10. The input is split **before** scaling so each
branch does RGB→YUV inside the single nearest-neighbour scale (an earlier
version scaled once and let ffmpeg auto-convert 420→444 bicubically, which put
0.35% non-uniform blocks into the master; now 0.000%). 8 px (and 6 px) blocks
are even, so 4:2:0 chroma never straddles two art pixels. No dithering. `paletteuse` is not
needed because frames are already palette indices.

## Verify checks (`pixelkit/verify.py`)

* grid: block size/phase found from edge energy folded modulo 2..16 px
* block uniformity: a block fails if its core (1 px trimmed) spans >24 in any
  channel. Hard limit ≤0.5 %
* held frames: consecutive frames identical when no native pixel (block mean)
  moves >28. Hard limit ≥40 % of pairs
* pre-encode colours from `--native-dir` ≤ `--palette-size` (32)
* output exactly 1080x1920
* straight edges: a run along one row/column boundary where the two sides
  differ by >24 and each side keeps the same colour (±10). A 1 px jog or a
  colour change ends it. Hard limit: longest run ≤ 20 native px
* flat regions: largest square with no neighbour step >10 inside. Hard
  limit ≤ 12x12 native px
* info: unique frames/s, hold lengths, % animated blocks, decoded palette estimate

Tolerances absorb codec noise. They were calibrated on the decoded Reference
(HEVC) and on our own x264 renders of flat blocks. All metrics are computed at
native resolution from block-core means. The edge and flat checks run on every
unique frame.

## Analysis and results (2026-11-06, 135x240 ×8 build)

| metric | Ours | Reference | Mine |
|---|---|---|---|
| source | h264 30 fps | HEVC 30 fps | h264 60 fps |
| grid / native res | 8 px / 135x240 | 8 px / 135x240 | 6 px / 180x320 |
| non-uniform blocks (≤0.5%) | **0.000%** | 0.025% | 0.933% FAIL |
| held pairs (≥40%) | **65.8%** | 27.1% FAIL | 0.0% FAIL |
| unique frames/s | 10.3 | 21.9 | 60.0 |
| hold lengths (frames×count) | 2×34 3×78 4×22 | 1×150 2×57 3×12 | 1×1080 |
| longest straight edge (≤20) | **17 px** | 63 px FAIL | 140 px FAIL |
| frames with a long edge | 0% | 100% | 100% |
| largest flat square (≤12) | **7x7** | 40x40 FAIL | 25x25 FAIL |
| median brightness (0-255) | 51 | 47 | 60 |
| decoded palette estimate | 24 | 263 | 297 |
| pre-encode colours (≤32) | **28** | n/a | n/a |
| verify | PASS (7/7) | FAIL | FAIL |

The yuv444p master gives identical results: 0.000%, 65.8%, 17 px and 9x9.
The Reference's flat squares are its large grey-teal floor. Its straight edges
are the room's wall lines. HEVC smoothing may hide fine floor texture that the
source had.

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
* At CRF 14 the art encodes to ~0.2 Mbps, well under 15–25 Mbps. That is
  expected for flat colour. If a platform needs a minimum bitrate, raise it with
  `crf` or add `-b:v`.
