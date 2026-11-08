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
| Poll sticker | The 2D poll sticker (white card, any two options, e.g. HATCHBACK / SUV) at any scale; flood-save grows it with `scale` | `overlays.py` `poll()` | speed-limit-deal-3d, speed-limit-deal-2d, flood-save | - |
| Text chips, headline, captions, tag, credit | Sharp full-res text placed inside the TikTok safe zone (12-62 % height, left 85 % width) with a per-frame violation check | `overlays.py` | speed-limit-deal-3d, speed-limit-deal-2d, flood-save | - |
| LOWER / HIGHER pills | Clean label pill (dark plate, coloured rim, soft shadow; no offset copy), auto-clamped into the safe zone | `overlays.py` `pill()` | flood-save | - |
| Kinetic headline | Clean headline (single outline, soft shadow, one yellow word), each word pops in on its spoken time, fixed layout on one baseline | `overlays.py` `kinetic()`, `word_img()` | flood-save | - |
| 2D gauge | Small pixel speedometer (70x66 grid, ~30 % of the width at 4x): lit segments, red limit line, needle, glowing limit digits only | `pix2d.py` `gauge()` | speed-limit-deal-2d (3D uses `pix3d/speedo.js` at r=9) | - |
| 2D props | Handshake, key, padlock (same pixel maps as `pix3d/props.js`), glowing force-field wall | `pix2d.py` | speed-limit-deal-2d | - |
| 2D palette | `palette.js` as RGB tuples | `pix2d.py` `PAL` | speed-limit-deal-2d | - |
| Rain layer | Two-layer diagonal pixel rain + splash rings on water, any t (also negative, for loops) | `ambient.py` `rain()` | flood-save | - |
| Night-to-sunrise dissolve | `blend()` (eased linear mix, rain fades out with it) and dithered `dissolve()`; Bayer-dithered `glow()` and `vgrad()` skies | `ambient.py` | flood-save | - |
| Water-depth graphic | Neutral gauge post, rising rippling water line, low + high car outlines, current streaks, pixel '?'; `sweep=0..1` lifts and carries the SUV away | `ambient.py` `depth_graphic()` | flood-save | - |
| Mini main guy + umbrella | The main guy (characters/main-guy palette) as a small 9x23 outline-free figure for ambient scenes; red umbrella | `ambient.py` `mini_guy()`, `umbrella()` | flood-save | - |
| Generic cars | Side-view hatchback and SUV, no logos or badges, any colour | `ambient.py` `hatchback()`, `suv()` | flood-save | - |
| Motion score | Mean frame-to-frame grey diff at 108x192, 10 fps (cold-open check, target >= 12; calm ambient style >= 6) | `../motion_score.py` | speed-limit-deal-2d, speed-limit-deal-3d, flood-save | - |

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

Ambient pixel-moment look (`ambient.py`, first used by `videos/flood-save`): art at 216x384 upscaled 5x nearest, calm
teal-rain night and pink-orange sunrise palettes taken from the pixel-moments preview; text stays sharp via `overlays.py`.

## Dashboard explainer kit (`carbits.py`, `dashep.py`)

2D pixel props and wiring for the looping 'car stuff, explained' dashboard shorts, first used by the red-zone /
fuel-cap-light / windscreen-glass series. Sprites are small RGBA grids, scaled with `pixanim.grid.up` (nearest). All text
goes through `overlays.py`, so `render.py safecheck` checks the safe zone (pills register their boxes too).
Example wiring: `videos/red-zone/src/render.py`.

| Asset | What it is | Path | Used by | Credit |
|---|---|---|---|---|
| RPM gauge with red zone | Rev counter (same dial as `pixanim/dash.py`), needle, pulsing red glow over the red section; `rpm_deg(frac)` | `carbits.py` `rpm_gauge()` | red-zone | own work |
| Engine warning light | Amber engine lamp (on / off) for the dashboard ENG slot or as a prop | `carbits.py` `warn_lamp()` | fuel-cap-light | own work |
| Fuel cap | Car rear quarter (window, trim, crease, wheel arch), filler flap open, cap that turns (`CAP_XY` = cap centre) | `carbits.py` `fuel_cap()` | fuel-cap-light | own work |
| Three-layer glass cutaway | Laminated glass side view: glass / plastic / glass, a crack that runs through the top glass and stops at the plastic | `carbits.py` `glass_layers()` | windscreen-glass | own work |
| Windscreen | Windscreen front view with stone chip and a star crack that spreads | `carbits.py` `windscreen()` | windscreen-glass | own work |
| Fuel-cut icon, drive tick | Fuel pump with red slash; green tick box | `carbits.py` `fuel_cut()`, `tick()` | red-zone, fuel-cap-light | own work |
| Callout pill | Pixel badge with a growing leader line (`pixanim/diagram.label`), box recorded for the safe-zone check | `carbits.py` `pill()` | red-zone, fuel-cap-light, windscreen-glass, oil-dipstick, cold-battery, hot-radiator | own work |
| Poll sticker | Reused `overlays.poll()` (YES / NO), kept inside the safe zone | `overlays.py` `poll()` | red-zone, fuel-cap-light, windscreen-glass, oil-dipstick, cold-battery, hot-radiator | - |
| Episode wiring | `wire()` (kit + safe-zone captions with mute windows + corner tag, -16 LUFS), `sequence()` (whips between shots), `camera()` (push-in + slow drift, nearest), loop back to frame 0, `cli()` (still / safecheck / safestill / cover / video) | `dashep.py` | red-zone, fuel-cap-light, windscreen-glass | - |
| Warning beep, glass crack | Synthesised sound effects | `../audio/sfx.py` `beep()`, `glass_crack()` | red-zone, windscreen-glass | own work |
| Word timings | faster-whisper word timings mapped onto the exact script (`est=1` marks interpolated words) | `../align_fw.py` | red-zone, fuel-cap-light, windscreen-glass | - |

## Under-the-bonnet kit (`garagebits.py`)

Pixel props for the oil-dipstick / cold-battery / hot-radiator episodes, same conventions as `carbits.py` (small RGBA
grids, scale with `pixanim.grid.up`, nearest). Wiring is `dashep.py`; callout pills and the poll sticker are the ones above.
Example: `videos/oil-dipstick/src/render.py`.

| Asset | What it is | Path | Used by | Credit |
|---|---|---|---|---|
| Dipstick | Yellow loop handle, rod, blade with MIN (green) / MAX (red) notches, oil film at any level (overfill past MAX), mark glow; `DIP_MIN`, `DIP_MAX` rows for anchors | `garagebits.py` `dipstick()` | oil-dipstick | own work |
| Snowflake overlay | Pixel snowflake icon, falling screen-space snow (seamless for any t), frosted corners | `garagebits.py` `snowflake()`, `snow()`, `frost()` | cold-battery, hot-radiator (icon) | own work |
| Battery cutaway | 12 V lead-acid battery cut open: six cells, plates, electrolyte, drifting ions (pass integrated time to slow them), frost tint, charge bar | `garagebits.py` `battery_cutaway()` | cold-battery | own work |
| Pressure gauge | Round gauge, green / amber / red arc, needle 0..1, red-zone glow | `garagebits.py` `pressure_gauge()` | hot-radiator | own work |
| Radiator + cap | Radiator front view with filler neck and a cap that turns (`CAP_XY`), heat tint | `garagebits.py` `radiator()` | hot-radiator | own work |
| Coolant spray, steam | Looping droplet fan under gravity (`t1` stops it); blocky rising steam column | `garagebits.py` `spray()`, `steam()` | hot-radiator | own work |
| Ring gear | Flywheel ring gear / pinion at any angle (starter scene, with `pixanim/autos.motor()`) | `garagebits.py` `gear()` | cold-battery | own work |
| Whirr, hiss | Slow struggling starter whirr; steam / pressure hiss | `../audio/sfx.py` `whirr()`, `hiss()` | cold-battery, hot-radiator | own work |

## Explainer series kit (`seriesbits.py`)

Pixel props for the tyres-black / seatbelt-pretensioner / catalytic-theft 'car stuff, explained' series (same wiring as the
dashboard kit: `dashep.py`, text through `overlays.py`, recurring dashboard with the A/C button in the ask shot). Sprites are
small RGBA grids, scaled with `pixanim.grid.up` (nearest). Example wiring: `videos/tyres-black/src/render.py`.

| Asset | What it is | Path | Used by | Credit |
|---|---|---|---|---|
| Tyre | Side-on tyre: tread blocks + 5-spoke rim turning; `light` = pale unfilled rubber, `wear` flattens the tread | `seriesbits.py` `tyre()` | tyres-black | own work |
| Tyre cutaway | Cut-open tread rubber that fills with jiggling carbon-black particles (and darkens) | `seriesbits.py` `rubber_block()` | tyres-black | own work |
| Sun-protection shield | Pixel sun with turning rays; blue shield whose tick draws on | `seriesbits.py` `sun()`, `shield()` | tyres-black | own work |
| Wear bar | Horizontal tread-life bar (any colour) | `seriesbits.py` `wear_bar()` | tyres-black | own work |
| Seatbelt buckle | Buckle + pretensioner tube cut open: the charge flashes, gas drives the piston, the buckle is pulled down | `seriesbits.py` `buckle()` | seatbelt-pretensioner | own work |
| Car seat, belt motor | Seat side view (`RETRACTOR` belt exit); electric belt motor with a spinning gear | `seriesbits.py` `seat()`, `motor()` | seatbelt-pretensioner | own work |
| Exhaust + catalytic converter | Exhaust line: pipe, converter cut open (honeycomb glows with `glow`), silencer; `EXH_CAT` anchor; crop `(62, 4, 122, 36)` for the converter alone | `seriesbits.py` `exhaust()` | catalytic-theft | own work |
| Precious-metal tiles | Ingot tiles for platinum / palladium / rhodium with a sweeping shine | `seriesbits.py` `metal_tile()` | catalytic-theft | own work |
| Thief silhouette | Flat dark crouching figure with a saw (no features); scenes blur it | `seriesbits.py` `thief()` | catalytic-theft | own work |
| Callout pills | Reused `carbits.pill()` (CARBON BLACK, SUN PROTECTION, WEARS FASTER, CHARGE, MOTOR, SNUG, PRETENSIONER, BEFORE IMPACT, CLEANS THE FUMES, PLATINUM, PALLADIUM, RHODIUM) | `carbits.py` `pill()` | all three | own work |
| Poll sticker | Reused `overlays.poll()` (YES / NO) | `overlays.py` `poll()` | all three | - |
| Soft metal clink | Synthesised low metal clink | `../audio/sfx.py` `clink()` | catalytic-theft | own work |
| Voiceover script | One Gemini TTS request per episode (Fenrir), resumable, 0.95x / 1.0x tempo, pause cap if still over 15 s | `videos/tyres-black/src/make_voiceover.py` | all three | - |

## Ten-episode dashboard series (abs-pumping ... warm-up-myth)

One shared render (`shared/series10/engine.py`), called once per episode from `videos/<ep>/src/render.py`. Sprites are
pixel grids scaled nearest with `pixanim.grid.up`. Voiceover: `shared/series10/make_voiceover.py` (Gemini TTS, Fenrir).

| Asset | What it is | Path | Used by | Credit |
|---|---|---|---|---|
| Callout pills | Pixel pill with leader line, safe-zone registered | `carbits.py` `pill()` | all ten | own work |
| Presenter placement | `SPOT`: open (200,1600) size 6, mid (185,1640) size 6, ask (300,1600) size 9 | `explainbits.py` `SPOT`, `series10/engine.py` `presenter()` | all ten | own work |
| RPM gauge | Rev counter with red zone (ask shot, every episode) + full dashboard with AC button | `carbits.py` `rpm_gauge()`, `../pixanim/dash.py` | all ten; dashboard: abs-pumping, stop-start, flashing-check-engine | own work |
| Car and wheel parts | Side-view car, top-down car with steered wheels, tyre, wheel hub with nuts | `../pixanim/car.py` `car()`, `explainbits.py` `car_top()`, `wheel_hub()`, `seriesbits.py` `tyre()` | abs-pumping, brake-squeal, wheel-nut-order, hill-wheels, ev-one-gear, warm-up-myth | own work |
| Brake disc and pad | Face-on disc + caliper (clamp pulse); pad cutaway with steel wear tab | `explainbits.py` `disc_caliper()`, `pad_section()`, `PAD_TAB()` | abs-pumping, brake-squeal | own work |
| Brake pedal | Pedal + shoe pressed by `press` | `explainbits.py` `pedal()` | abs-pumping | own work |
| Star-pattern diagram | Numbered nuts joined in star order (and the wrong round-the-circle route) | `explainbits.py` `star_lines()`, `circle_lines()` | wheel-nut-order | own work |
| Headlight cutaway | Headlight front view yellowing with `haze`; lens cutaway with eroding UV coat | `explainbits.py` `headlight()`, `lens_layers()` | headlight-yellow | own work |
| Coolant bottle | Expansion tank with MIN/MAX, coolant colour, sludge; coolant hose that blocks | `explainbits.py` `coolant_bottle()`, `hose()` | coolant-mixing | own work |
| Warning-light icon | Engine warning lamp (amber / flashing) | `carbits.py` `warn_lamp()` | flashing-check-engine | own work |
| Stop-start bits | Traffic light, stop-start 'A' icon | `explainbits.py` `traffic_light()`, `ss_icon()` | stop-start | own work |
| EV drive | Motor pinion + reduction gear; torque-vs-rpm chart | `explainbits.py` `gear_pair()`, `torque_graph()` | ev-one-gear | own work |
| Thermometer | Fills to `k` | `explainbits.py` `thermo()` | warm-up-myth | own work |
| Poll sticker | YES / NO or two-option sticker, position varies per episode | `overlays.py` `poll()` | all ten | own work |
| Opening moves | push-in, whip-pan, pull-back, wipe, zoom-out, tilt, slow-motion, cut-in, drop-in, glitch-in | `../series10/engine.py` `opening()` | one per episode | own work |
| ABS pulse, metal scrape | Synthesised sound effects | `../audio/sfx.py` `pulse()`, `scrape()` | abs-pumping, brake-squeal | own work |

## Six-episode series (limp-mode, timing-belt, speedometer-high, blind-spot, airbag-light, premium-fuel)

Shared render: `../series10/engine.py` `build()` (called once per episode from `videos/<ep>/src/render.py`); scripts in
`../series6/scripts.py`; voiceover: `SERIES=series6 python shared/series10/make_voiceover.py` (Gemini TTS, Fenrir).

| Asset | What it is | Path | Used by | Credit |
|---|---|---|---|---|
| Callout pills | Badge + leader line, recorded for the safe-zone check | `carbits.py` `pill()` | all six | own work |
| RPM gauge | Chrome dial with red zone and needle (recurring ask-shot gauge) | `carbits.py` `rpm_gauge()` | all six (limp-mode key beat) | own work |
| Speedometer dial | SPEED dial: dashed amber tolerance band, green true-speed tick, red shown needle (no numbers) | `series6bits.py` `speedo()` | speedometer-high | own work |
| Power meter | Segmented POWER bar meter that drops and blinks when power is cut | `series6bits.py` `power_meter()` | limp-mode | own work |
| Timing belt + pulleys | Toothed belt over two cam pulleys and the crank pulley; teeth move; `snap` breaks it | `series6bits.py` `belt_drive()` | timing-belt | own work |
| Valve / piston gap | One-cylinder cutaway, valve down / piston up, contact flash | `series6bits.py` `valve_piston()` | timing-belt | own work |
| Blind-spot cone | Top-down road: mirror-view cones (blue), blind-spot cone (red), car hidden in it, head-check sight cone, mirror warning lamp | `series6bits.py` `blind_road(look=, warn=)` | blind-spot | own work |
| Airbag warning icon | Generic seated-passenger + bag symbol lamp; SRS control unit with sensor / connector wires | `series6bits.py` `airbag_icon()`, `bulb()`, `airbag_module()` | airbag-light | own work |
| Fuel gauge comparison | E..F fuel gauge; REGULAR vs PREMIUM gauges with equal power bars | `series6bits.py` `fuel_gauge()`, `fuel_compare()` | premium-fuel | own work |
| Poll sticker | Two-option sticker, position / tilt varies per episode | `overlays.py` `poll()` | all six | own work |
| Sound effects | power-down whine, metal clack, soft alert chime, needle tick (alias of click) | `../audio/sfx.py` `power_down()`, `clack()`, `alert()`, `tick` | limp-mode, timing-belt, blind-spot, airbag-light, speedometer-high | own work |

## Cozy top-down room kit (`cozyroom.py`)

Oblique top-down room look from `videos/cozy-sim-room` (180x320 native, 6x nearest, smooth full-res light over the pixels), 48-colour master palette
(`PAL`, one char per colour; quantise frames onto `PAL_ARR` with a Bayer dither). Sprites are hand-authored pixel maps
returned as float RGBA for `ambient.paste`; `S(rows, outline=, sub=)` builds any map with a 1px outline and recolours.

| Asset | What it is | Path | Used by | Credit |
|---|---|---|---|---|
| Palette | 48 hand-picked colours: teal-blue darks, purple + blue neon, warm window, reds, skin, greens, greys, mint, pink | `cozyroom.py` `PAL`, `PAL_ARR` | cozy-sim-room | own work |
| Cat | Curled orange tabby from above; `cat(breath=0..1, flick=-1/0/1, mood=sleep|awake|yawn)` (awake/yawn maps are 1 row taller: paste 1px higher) | `cozyroom.py` `cat()` | cozy-sim-room | own work |
| Mug | White mug with a heart, coffee inside (pair with a steam loop) | `cozyroom.py` `mug()` | cozy-sim-room | own work |
| Console shelf | Wall shelf front with eight generic retro consoles (no logos); returns (sprite, LED row y) | `cozyroom.py` `console_shelf()`, `console(kind)` | cozy-sim-room | own work |
| Monitor | Bezel + stand for any w x h screen (draw content at [2:2+h, 2:2+w]) | `cozyroom.py` `monitor()` | cozy-sim-room | own work |
| Gaming chair | Chair seen from above/behind: backrest, side trims, five-star base | `cozyroom.py` `CHAIR`, `chair()` | cozy-sim-room | own work |
| Plush creature | Original round mint dumpling with a sprout, dot eyes and blush | `cozyroom.py` `plush()` | cozy-sim-room | own work |
| Car posters | 14x30 wall posters, no text or badges: `sunset`, `track` (top-down race car), `blue` (blueprint) | `cozyroom.py` `poster(kind)` | cozy-sim-room | own work |
| Room props | 46 small pixel maps: model cars, controller, snack, trainers, clothes, helmet, cone, tyre, toolbox, books, boxes, pizza, lamp, plant, bin, bowls, yarn, skateboard ... | `cozyroom.py` `PROPS`, `prop(name)` | cozy-sim-room | own work |

## 3D pixel car kit (`3d-car/`)

Pixel-art look from a real 3D model, first used by `videos/rear-engine-3d`. Three.js (vendored r160, Chromium via Playwright)
renders ID / light / depth tiles at 270x480 (no colour in WebGL); `pixpost.py` reduces them to a 135x240 grid (front-most
sample wins), maps every pixel to one fixed 32-colour palette as flat posterised tones (dither only at band edges and on
the x-ray shell), adds 1-px navy outlines (depth jumps + part boundaries), then scales 8x nearest. Frames are stepped
deterministically with `pix3d/render3d.mjs` at 30 fps and held x2 in the 60 fps video (pixel-animation cadence). Text goes on top through `overlays.py` (safe zone checked).

| Asset | What it is | Path | Used by | Credit |
|---|---|---|---|---|
| Coupe builder | Original rear-engine sports coupe (no brand/badge/plate): 150-section lofted body with wheel-arch cut-outs, near-upright side glass with B-pillar, windscreen + rear glass groups, layered round headlights with a light ring, side lamps, intakes, red light bar on a black tail panel, tapered duck-tail, louvres, aero mirrors, door cuts + handle, finned engine intake ahead of the rear wheel, sill, big twin exhausts, low-profile 5-split-spoke wheels with red calipers (wider rears); x-ray internals (flat engine behind the rear axle, gearbox, axles); `pose()` spin/squat/steer/hot tyres; anchors `engine`, `rear_axle`, `front_axle`, `rear_tyre(_l)`, `front_tyre`, `headlight`, `tail`, `roof` | `3d-car/coupe.js` | rear-engine-3d | own work |
| Coupe glTF | Static export of the coupe + internals (standard materials), 1.9 MB; regenerate with `node shared/assets/3d-car/export_gltf.mjs <out.gltf>` | `3d-car/coupe.gltf`, `3d-car/export_gltf.mjs`, `3d-car/gltf_scene.js` | rear-engine-3d | own work; GLTFExporter (three.js, MIT) |
| Toon ID materials | One shader for every part: info pass (id, light, cool rim) and 16-bit depth pass; `env` = painted-metal reflection (sky above the horizon, crisp dark horizon band, ground below), `glare` = dark glass with diagonal glare streaks; warm key + cool rim follow the camera; sand floor (light pool, joints, contact shadow), slatted roller-door backdrop with lamps; `stdMat()` stand-ins | `3d-car/toon.js` | rear-engine-3d | - |
| Stage | 4-tile renderer, orbit rig with vertical + horizontal lens shift (`shift`, `shiftX`: car low in the 9:16 frame, clear of the presenter), `project()` anchors in 1080x1920 px | `3d-car/stage.js` | rear-engine-3d | - |
| Car turntable | 10 fixed review views (3/4s, side, front, rear, top, headlight and wheel close-ups), no text: `node shared/assets/pix3d/render3d.mjs shared/assets/3d-car/turntable.js <dir> 1 --times 0,1,2,3,4,5,6,7,8,9` then `pixpost.post()` | `3d-car/turntable.js` | rear-engine-3d (model review) | - |
| Palette + post-process | `RAMPS` per material id (cream/tan body, navy, sand, teal glass, orange glow, ...), `post(png, xray)`, `up()` | `3d-car/pixpost.py` | rear-engine-3d | - |
| Signature presenter on the pixel grid | The main guy sprite rig (`pixanim/presenter`, characters/main-guy) drawn at size 2 on a 270x480 layer, halved nearest and composited into the 135x240 art, so 1 sprite pixel = 1 scene pixel (8x8 on screen); points at the projected `_pt` anchor, shrugs for the poll | `videos/rear-engine-3d/src/render.py` `GUY`, `shot()` | rear-engine-3d | characters/main-guy |
| Pinned pills | Pill in the safe zone with a leader line + dot to a moving 3D anchor; `icon_pill_img` with a chip glyph (ELECTRONICS) | `overlays.py` `pin(..., grid=8)` (leader drawn as hard pixels on the art grid), `icon_pill_img()`, `chip_icon()` | rear-engine-3d | Inter font (SIL OFL) |
| Three.js addons | GLTFExporter, TextureUtils, RoundedBoxGeometry (r160, same build as the vendored core) | `vendor/jsm/` | rear-engine-3d | MIT, `vendor/THREE_LICENSE` |

## Stickman flat-vector kit (`stickman/`)

Flat vector shapes, thick dark outlines, soft greys + warm tones with yellow/red highlights, no pixelation. Pure PIL,
drawn on a 2x supersampled layer and box-filtered (anti-aliased); physics via pymunk. Composed for 1080x1920 from the
start. Example: `videos/seatbelt-stickman` (style test against the pixel `seatbelt-pretensioner`). No earlier stickman /
"warehouse shootout" code existed in the repo, so this kit was built from scratch.

| Asset | What it is | Path | Used by | Credit |
|---|---|---|---|---|
| Vector pen | 2x supersampled layer, world->px pen with squash/stretch (`kx`, `ky`), outlined polys, capsule limbs, arcs, pills, translucent blending, soft contact shadows | `stickman/vec.py` | seatbelt-stickman | - |
| Stickman rig | FK skeleton (`Pose`, `presenter_joints`, `point_angle`) for an original presenter: round cream head, dot eyes, brows, talking mouth, signature red cap, thick charcoal limbs | `stickman/rig.py` `draw_presenter()` | seatbelt-stickman | original |
| Crash dummy + marker | Stick crash-test dummy (sand limbs, joint discs) with yellow/black crash-test markers on head and chest; `marker()` on its own | `stickman/rig.py` `draw_dummy()`, `marker()` | seatbelt-stickman | - |
| Vector hatchback | Original 3-door sports hatchback, side view, no badge; `mode='glass'` (cabin seen through tint) or `'cut'` (door + glass removed), `crumple=0..1` front crush, spinning wheels; seat, steering wheel, belt (with slack bow + glow), retractor with charge cartridge / motor | `stickman/car.py` | seatbelt-stickman | original |
| Crash ragdoll | pymunk seated dummy in the car frame: frontal pulse, lap + shoulder belt as slide joints; `crash(pretensioner=True/False)` -> 1 ms joint frames, `sample()` | `stickman/physics.py` | seatbelt-stickman | pymunk (MIT) |
| Crash hall + barrier | Muted grey test hall strip (windows, light shafts, roller doors, hazard edges, track dashes; seamless scroll via `view()`), vignette, barrier with chevrons + honeycomb crush face | `stickman/stage.py` | seatbelt-stickman | look after the user's reference clip |
| FX | Impact starburst + ring, smoke puffs, debris, speed lines, spark pop | `stickman/fx.py` | seatbelt-stickman | - |
| Poll sticker | Flat 'Did you know that? YES / NO' card with tap ripple | `stickman/poll.py` `poll_img()` | seatbelt-stickman | - |

## Cinematic illustrated kit (`cinematic/`)

Layered 2.5D dusk look in pure PIL + numpy (no Blender in the cloud box): depth layers with parallax and per-layer
depth-of-field, gradient shading, glows, then a filmic finish (grade, bloom, vignette, grain). Builds on `stickman/`
(vector pen, car geometry + cutaway, crash ragdoll, FX). Example: `videos/seatbelt-cinematic`.

| Asset | What it is | Path | Used by | Credit |
|---|---|---|---|---|
| Main guy, illustrated rig | `characters/main-guy` redrawn smooth: dark messy hair + 2 cowlicks, brown skin, silver square glasses, white tee, black shorts, white/black trainers; jointed arms/legs, poses neutral / point / surprised / thumbs / ask / hips, `blend_pose`, `aim`, mouth from voice loudness, brows, blink, look, turn, step | `cinematic/guy.py` | seatbelt-cinematic | original character |
| Glossy hatchback | Lit version of the stickman hatchback: body gradient, teal sky reflection, speculars, rim light, wheel motion blur, headlight beam + glow, tail glow, retractor glow; glass / cutaway / crumple | `cinematic/car.py` | seatbelt-cinematic | original design |
| Dusk proving ground + camera | Sky (gradient, sun glow, stars, clouds), far hills/city, floodlight towers + grandstand, track with kerbs/dashes/light pools, blurred foreground cones; `Cam` (scroll, zoom, focus, shake) with parallax depths 0.04-1.7 | `cinematic/scene.py` | seatbelt-cinematic | - |
| Post pipeline | Teal/navy shadows + warm highlights grade, soft bloom, vignette, deterministic fine grain | `cinematic/post.py` `finish()` | seatbelt-cinematic | - |
| Paint helpers | Linear-gradient polygon fill, radial glow sprites, edge-safe composite, cheap big blur | `cinematic/paint.py` | seatbelt-cinematic | - |
| Photo card, poll, pills | Framed photo card (illustrated retractor fallback), gradient YES / NO poll with tap ripple, glossy pills with optional tick | `cinematic/cards.py` | seatbelt-cinematic | - |

## Inkfight kit (`inkfight/`)

Flat-colour, silhouette-led stickman fight animation drawn on a Chromium canvas (Playwright), 1080x1920 at 60 fps,
deterministic per-frame (`frame(i)`), rendered in 4 parallel pages. Scene = classic script defining
`window.SCENE = {init(data), frame(i, fps), events}`. Render:
`node shared/assets/inkfight/render.mjs <scene.js> <data.json> <out_dir> 60 0 <dur> 4` (or `--times a,b`); writes PNG frames,
`boxes.json` (every text box per frame, for the safe-zone check) and `events.json` (impact / sfx cue times).
Example: `videos/seatbelt-fight`.

| Asset | What it is | Path | Used by | Credit |
|---|---|---|---|---|
| Frame renderer | Playwright canvas renderer, parallel pages, PNG frames + text boxes + events | `inkfight/render.mjs` | seatbelt-fight | own work |
| Keyframe tracks | Hand-keyed pose tracks with per-key easing (`io`, snap-out `o`, anticipation `i`, overshoot `back`, hold `h`); hit-stops = repeated keys | `inkfight/kit.js` `K.track`, `K.ease` | seatbelt-fight | own work |
| Main guy, stickman rig | The main guy as a stickman: messy dark hair, grey square glasses, brown skin, white tee, black shorts, white/black trainers; FK pose (lean, head, arms, legs, squash/stretch), profile-to-camera `turn`, whole-body `rot` (flips) and `sx` 1..-1..1 (spins), mouth from voice loudness, blink, brows, thumbs-up, warm rim light | `inkfight/kit.js` `K.drawGuy`, `K.drawGuyHead`, `K.joints` | seatbelt-fight | characters/main-guy identity, own drawing |
| Rival stickman | Vermilion faceless stickman with fluttering headband, cyan rim light; `pal`/`band`/`cap`/`thumb` options make a neutral driver | `inkfight/kit.js` `K.drawRival` | seatbelt-fight | own work |
| Smear + impact FX | Limb smear ribbons, starburst + rings, sparks, dust puffs, speed lines, ground crack, shockwave, ground shadow | `inkfight/kit.js` `K.smear`, `K.crack`, `K.shockwave`, `K.burst`, `K.sparks`, `K.dust`, `K.speedLines`, `K.shadow` | seatbelt-fight | own work |
| Camera | Shot list with hard cuts, eased moves, decaying impact shake; `K.apply` | `inkfight/kit.js` `K.camera` | seatbelt-fight | own work |
| Dusk city street | Parallax dusk sky + blurred skyline with lit windows, streetlights, blank neon sign shapes (no text/logos), bokeh, wet road with light reflections, lane dashes | `inkfight/kit.js` `K.buildStreet`, `K.drawStreet` | seatbelt-fight | own work |
| Generic car | Unbadged side-view hatch (blank plate), any colour, crumple, pitch, spinning wheels, glass tint, x-ray door-off cutaway with an occupant callback | `inkfight/kit.js` `K.drawCar` | seatbelt-fight | own work |
| Seatbelt diagram parts | Seat, crash dummy, retractor spool, pyro cartridge (with firing puff), electric motor, arrows, airbag | `inkfight/kit.js` `K.seatShape`, `K.dummy`, `K.spool`, `K.cartridge`, `K.motor`, `K.arrow`, `K.airbag` | seatbelt-fight | own work |
| Post finish | Bloom, warm/cool split grade, vignette, animated grain | `inkfight/kit.js` `K.makePost` | seatbelt-fight | own work |
| Text + poll | Safe-zone text with plates / strokes / per-word colours, logged boxes; YES / NO poll card | `inkfight/kit.js` `K.text`, `K.poll` | seatbelt-fight | own work |
| Fight sfx | Punch, guarded block, record scratch, airbag pop (synthesised) | `../audio/sfx.py` `punch()`, `block()`, `scratch()`, `airbag_pop()` | seatbelt-fight | own work |
| VO placement | Places one TTS take on a timeline in segments, shortens long gaps, maps real word timings, per-frame loudness for the mouth | `videos/seatbelt-fight/src/build_vo.py` | seatbelt-fight | own work |
