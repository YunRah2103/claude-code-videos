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

## Isometric F1 kit (`isof1/`)

Lit isometric pixel look from `videos/f1-aero` v3, moved here for the f1-downforce series. Worlds render at 216x384 and
are upscaled 5x nearest (`hud.upscale`); HUD and text are drawn sharp at 1080x1920 through `overlays.place`, so the
safe-zone check covers them. Wiring: `isof1/series.py` (kit + loop window + safecheck + cover CLI).

| Asset | What it is | Path | Used by | Credit |
|---|---|---|---|---|
| Iso engine | Lit iso boxes (top/left/right shading, edge highlights), soft shadows, dithered glow, floating dioramas, colour grade + bloom | `isof1/engine.py` | f1-downforce-1/2/3 | own work |
| F1 car model | Open-wheel car from oriented boxes at any heading, cylinder tyres with spinning rims, wing flap opening, highlight pulse, 6 team liveries (no logos) | `isof1/car.py` | f1-downforce-1/2/3 | own work |
| Track segment / circuit | Spline circuit (road ~3.4 car widths), kerbs, gravel, pit lane, billboards, tyre walls, grandstands, trees; 6-car race sim with braking and passing; corner test with a no-aero ghost | `isof1/race.py` | f1-downforce-1/2/3 | own work |
| Wind-tunnel lab | Dark-blue lab diorama, cyan turntable ring, spinning fan, smoke streamlines (over, under, front split, rear upwash, wake) | `isof1/scenes.py` `lab()`, `smoke()` | f1-downforce-1/2 | own work |
| Downforce arrows | Red 3D arrows that slam down onto the car (squat + screen shake) | `isof1/scenes.py` `arrow3d()`, `isof1/shots.py` `downforce()` | f1-downforce-1/2 | own work |
| Straight road | Golden-hour road diorama with scrolling kerbs, billboards, barriers | `isof1/scenes.py` `straight()`, `isof1/shots.py` `straight_car()` | f1-downforce-1/3 | own work |
| Ceiling split | Split frame: the road below, the same car driving across the ceiling above | `isof1/shots.py` `ceiling_split()` | f1-downforce-1/3 | own work |
| Speed streaks | Pixel speed lines streaming the way the scenery moves (cold-open motion) | `isof1/shots.py` `speed_lines()` | f1-downforce-1/2/3 | own work |
| Wing callouts / pills | Dark pill with a coloured edge (FRONT WING, REAR WING, GRIP, SLIDES OFF, STRAIGHT MODE: LOW DRAG, CORNER MODE: GRIP) | `isof1/hud.py` `pill()` | f1-downforce-1/2/3 | Inter font (SIL OFL) |
| Headline | White text, dark outline, one yellow highlighted word | `isof1/hud.py` `headline()` | f1-downforce-1/2/3 | Inter font (SIL OFL) |
| Grip meter | Vertical meter with a GRIP pill | `isof1/hud.py` `meter()` | f1-downforce-2 | own work |
| Drag arrow | Thick red arrow pointing back along the car with a DRAG pill | `isof1/hud.py` `drag_arrow()`, `isof1/shots.py` `drag()` | f1-downforce-2 | own work |
| Lap HUD | LAP 12/57 board with team-colour running order (top-left) + mini iso track map with live car dots (top-right) | `isof1/hud.py` `board()`, `track_map()` | f1-downforce-1/2/3 | own work |
| Poll sticker | Existing 2D poll sticker (YES / NO), reused | `overlays.py` `poll()` | f1-downforce-1/2/3 | - |
| Presenter placement | Main Guy (`pixanim/guy.py`) at 10x, feet on the bottom edge, lower-left, lip-synced to words.json | `isof1/hud.py` `presenter()` | f1-downforce-1/2/3 | characters/main-guy |
| Series runner | Kit wiring: progress bar, mixer, 60 fps H.264 + AAC, no running captions, loop crossfade into frame 0, safecheck / cover CLI | `isof1/series.py` | f1-downforce-1/2/3 | - |
| Snap sound | Short mechanical snap (wing flap closing) | `../audio/sfx.py` `snap()` | f1-downforce-3 | own work |

## Photo mini-documentary kit (`docstyle.py`)

Real-photo documentary look (no pixel engine), first used by `videos/brand-story-lamborghini`. Text goes through
`overlays.place`, so `overlays.violations()` checks the safe zone; `ds.STATS['max_up']` reports the largest photo upscale
(capped at 1.5x: `parallax` shrinks the card rather than upscale further, `kenburns` raises). Example wiring, CLI,
safe-zone `check` mode and loop-to-frame-0 ending: `videos/brand-story-lamborghini/src/render.py`.

| Asset | What it is | Path | Used by | Credit |
|---|---|---|---|---|
| Colour grade | One grade for every photo: contrast, muted colour, teal shadows, warm highlights | `docstyle.py` `graded()` | brand-story-lamborghini | - |
| Ken Burns | Eased pan-and-zoom of a photo crop, Lanczos, aspect kept (never stretched), upscale cap | `docstyle.py` `kenburns()` | brand-story-lamborghini | - |
| Parallax over blur | Sharp photo card (shadow, thin border) over a blurred, darkened, drifting copy of the same photo | `docstyle.py` `parallax()`, `background()`, `card()` | brand-story-lamborghini | - |
| Camera shake | Decaying jitter for cold opens and stamp hits | `docstyle.py` `shake()` | brand-story-lamborghini | - |
| Split screen | Two photo panels sliding in nose to nose (optional mirror) | `docstyle.py` `split()` | brand-story-lamborghini | - |
| Kinetic headline | One phrase at a time: white, dark outline, highlight words yellow, words pop in and kick when spoken | `docstyle.py` `headline()` | brand-story-lamborghini | - |
| Name chip | Plain silhouette icon + name on a dark pill (no likeness) | `docstyle.py` `name_chip()` | brand-story-lamborghini | - |
| Label pill | Small pill label; `flash=` blinks it (warning labels) | `docstyle.py` `pill()` | brand-story-lamborghini | - |
| Timeline + year counter | Rail with ticks, fill running to a marker (only the confirmed year labelled); big ticking year | `docstyle.py` `timeline()`, `year_counter()` | brand-story-lamborghini | - |
| Speech card | White quote bubble with tail; one line on a dark plate in yellow | `docstyle.py` `speech()` | brand-story-lamborghini | - |
| Segmented progress bar | Series bar across the top, one segment per chapter | `docstyle.py` `progress()` | brand-story-lamborghini | - |
| Film grain + vignette | Subtle grain (8 patterns, 30 Hz) and soft vignette, applied last | `docstyle.py` `finish()` | brand-story-lamborghini | - |
| Stamp, poll sticker, tag, credit line | Reused from `overlays.py` (`stamp`, `poll`, `tag`, `credit`) | `overlays.py` | brand-story-lamborghini, speed-limit-deal-2d/3d | - |

Photos for brand-story-lamborghini: `videos/brand-story-lamborghini/assets/credits.json` (Wikimedia Commons, CC BY / CC BY-SA 4.0).
