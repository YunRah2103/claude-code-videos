# shared/assets index

Reusable assets for the 3D pixel look (first used by `videos/speed-limit-deal-3d`) and their 2D pixel twins (`pix2d.py`). The 3D world renders in
Chromium (Three.js, Playwright) at 270x480, no antialiasing, and is upscaled 4x nearest to 1080x1920; text is drawn
sharp on top with `overlays.py`. Render: `node shared/assets/pix3d/render3d.mjs <scene.js> <out_dir> 60 0 <dur>`
(or `--times 0,1.3` for stills). An episode scene module exports `build(canvas) -> { frame(t) -> anchors }`.

| Asset | What it is | Path | Used by | Credit |
|---|---|---|---|---|
| Three.js r160 | Vendored ES module (pinned) | `vendor/three-0.160.0.module.min.js` | speed-limit-deal-3d | MIT, `vendor/THREE_LICENSE` |
| Palette | Limited colours matching the 2D garage and episode kit | `pix3d/palette.js` | speed-limit-deal-3d | - |
| Voxel helpers | Pixel map -> instanced voxel boxes, 3x5 voxel digits, <=32x32 nearest textures | `pix3d/voxel.js` | speed-limit-deal-3d | - |
| 3D garage | Brick room (32x32 brick tex), floor tiles, ceiling lamps + light cones, yellow ray fan, optional roller door, lights + fog | `pix3d/garage3d.js` | speed-limit-deal-3d | - |
| 3D scene setup | 270x480 renderer, orbit camera rig with shake / push-in, `project()` anchors for full-res overlays | `pix3d/stage.js` | speed-limit-deal-3d | - |
| Low-poly cars | Generic saloon and sports car (no logos), any colour; `poseCar` for drive, launch pitch, rev shake, flames, brake | `pix3d/cars.js` | speed-limit-deal-3d | - |
| Speedometer wall | Dial with lit segments, needle, red limit line, glowing voxel limit digits (no other numbers); force-field wall with hit ripple + shatter | `pix3d/speedo.js` | speed-limit-deal-3d | - |
| Handshake icon | Voxel handshake | `pix3d/props.js` `handshake()` | speed-limit-deal-3d | - |
| Key unlock | Voxel key + padlock with pop-open shackle | `pix3d/props.js` `key()`, `padlock()` | speed-limit-deal-3d | - |
| Renderer | Playwright frame renderer (PNG frames + anchors.json) | `pix3d/render3d.mjs`, `pix3d/page.html` | speed-limit-deal-3d | - |
| Stamp | Rubber stamp (e.g. SECRET DEAL) that slams in | `overlays.py` `stamp()` | speed-limit-deal-3d, speed-limit-deal-2d | - |
| Poll sticker | The 2D poll sticker (white card, YES / NO) at any scale | `overlays.py` `poll()` | speed-limit-deal-3d, speed-limit-deal-2d | - |
| Text chips, headline, captions, tag, credit | Sharp full-res text placed inside the TikTok safe zone (12-62 % height, left 85 % width) with a per-frame violation check | `overlays.py` | speed-limit-deal-3d, speed-limit-deal-2d | - |
| 2D gauge | Small pixel speedometer (70x66 grid, ~30 % of the width at 4x): lit segments, red limit line, needle, glowing limit digits only | `pix2d.py` `gauge()` | speed-limit-deal-2d (3D uses `pix3d/speedo.js` at r=9) | - |
| 2D props | Handshake, key, padlock (same pixel maps as `pix3d/props.js`), glowing force-field wall | `pix2d.py` | speed-limit-deal-2d | - |
| 2D palette | `palette.js` as RGB tuples | `pix2d.py` `PAL` | speed-limit-deal-2d | - |
| Motion score | Mean frame-to-frame grey diff at 108x192, 10 fps (cold-open check, target >= 12) | `../motion_score.py` | speed-limit-deal-2d, speed-limit-deal-3d | - |

Two versions of one episode: `videos/speed-limit-deal-3d/src/beats.py` holds the shared timings, text, poll, photo and
sound cues; each version's `render.py` only supplies the world (`shot(t)`) and screen anchors. Photo credit:
`videos/speed-limit-deal-*/assets/credits.json` (Wikimedia Commons, CC BY-SA 3.0).
