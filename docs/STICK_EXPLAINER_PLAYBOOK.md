# Stick-fighter explainer playbook

How `videos/brake-explainer` was made, written so another agent can produce a new topic in one pass.
Format: 1280x720, 30 fps, pixel art, about 60–70 s. Example output: a stick fight on a road, a car brakes,
a wheel-to-rotor match cut, then a narrated disc-brake and ABS explanation with a corner presenter.

## 1. What already exists (reuse, don't rebuild)

| Need | Where | Notes |
|---|---|---|
| Fighters, poses, motion curve, flips, smears | `videos/stick-duel/src/render.py` | `draw_fighter(d, keys, t, cloak, z, gy)`; cloaks: `green` (coat + katana), `red` (cape + axe), `shirt` (presenter: white shirt, no weapon) |
| Keyframes | same | `(t, x, yoff, pose, facing[, rot])`; screen x, `yoff` < 0 = airborne, `rot` in degrees (−360 = backflip) |
| Poses | `duel.P` | add new ones with `duel.P.update({...})` (hip-relative, facing right, last value = weapon angle) |
| Pixel snapping | `duel.pixelate(layer, duel.CPX)` | characters on the same 10.67 px grid as the background |
| Pixel FX | `duel.pixel_fx(layer, 8)`, `duel.pixel_glow(gl, 8)` | palette `duel.FX_PAL`, dark 1-cell outlines, dithered stepped glow |
| FX shapes | `duel.slash / streak / fire_arc / particles / bolt / spikes / shock / dust / puff` | draw onto the FX layer; glow goes on the `gl` layer |
| Hit feel | `duel.BIG`, `duel.hitstop`, `duel.speedlines`, impact frames + colour split + camera punch in `duel.frame` | add a hit time to `HITS`/`BIG`, ground slams to `SLAMS` |
| Intensity FX | `duel.weapon_smear`, `duel.sparks`, `duel.debris`, `duel.aura` | smears trace the real weapon path; aura shows on `windup`/`raise` poses |
| Whole duel shot | `duel.frame(t, bg, dark, tail)` | override `duel.CZ/CX/CY` for a steady camera |
| Backgrounds | `duel.build_bg()` (meadow), `brake.build_road()` (road) | both on the 120x68 art grid |
| Car sprite, pixel font, icons | `videos/new-car-trap/src/pix.py` | `pix.car`, `pix.label`, `pix.FONT` (add missing glyphs as in `brake/render.py`), `pix.check/xmark` |
| Sound effects, music | `new-car-trap/src/sfx.py`, `duel.music/clang/crackle/zap` | |
| Presenter | `brake.host_layer(t, keys)` | plain stickman, white shirt, glasses, 6 px grid, two flat tones + rim |
| TTS | `videos/brake-explainer/src/tts.py` | Gemini TTS, voice Fenrir, one clip per line |
| Word timings | `videos/brake-explainer/src/align.py` | PocketSphinx forced alignment → `words.json` |
| PNG previews | `assets/stick-explainer/` (`python tools/export_stick_assets.py`) | backgrounds, car, pose sheets, FX palette |

Start a new topic by copying `videos/brake-explainer/src/` to `videos/<topic>/src/` and changing `script.json`,
the diagram functions and the road/scene props. The duel is imported by file path, so nothing else needs copying.

## 2. Pipeline (commands)

```bash
python tools/video.py doctor                     # once; if pocketsphinx is missing: bash tools/setup.sh
cd videos/<topic>/src
# 1. write script.json: a list of short lines (one sentence or two), about 2.6 words/s
python3 tts.py ../../../out/<topic>/vo           # Gemini Fenrir; free tier = 3 requests/min, script backs off
../../../.venv/bin/python align.py ../../../out/<topic>/vo   # must print a word count for every line
python render.py still ../../../out/<topic>/st 10 20 30 40   # inspect stills first
python ../../../tools/video.py run --log ../../../out/<topic>/test.log -- python render.py video ../../../out/<topic>/test.mp4 END START
python ../../../tools/video.py run --log ../../../out/<topic>/render.log -- python render.py video ../../../out/<topic>/<topic>.mp4
```

The full 66 s render takes about 3 minutes. Never commit MP4s, WAVs or frames (`out/` holds them).

## 3. Timing model (no hand-typed times)

- `START[i]` is computed from the real clip lengths plus gaps; `GAP` adds room for transitions.
- `OFF` shifts everything after the opening fight (the brake video plays the whole duel first).
- `wt(line, 'word')` gives the absolute time a word starts. Anchor every label, pop, gesture, sound and
  camera move to `wt()` so a regenerated voice just works.
- `DUR` must be a literal number (the preview tool parses it); there is an assert that the voice fits.

## 4. Scene recipe used for the brake video

1. **Hook fight (0 → OFF + 2.3 s):** `duel.frame(t, road, dark, tail)` with a steady camera.
2. **Event (car):** constant-deceleration motion, `car_front(t)`, skid marks, tyre smoke (`duel.puff`), nose dip,
   brake-light glow, bystander reaction keys (`G2`, `R2`).
3. **Question line:** slow push-in towards the object you will explain (`road_cam`).
4. **Match-cut transition:** zoom the road shot into the wheel (exponential zoom to 10x) while the diagram
   is held with its rotor at the same screen spot and size, then cross-dissolve for 0.4 s and ease out to the
   overview. The reverse does the same back to the road.
5. **Diagram:** a low-res canvas (640x180, 4x scale) with two panels (system on the left, ABS comparison
   on the right) and a camera (`diagram_cam`) that pans between them. Parts animate from state functions:
   `press(t)`, `clamp_amt(t)`, `heat(t)`, `rotor_angle(t)`.
6. **Presenter:** `host_keys()` builds gestures from the words: `point` on each part name, `kneeup`
   then stomp on "press", alternating `talk1/talk2` beats, `shrug`; it slides in and out with the transitions.
7. **Outro:** keyword cards popping on their words, then the fighters clash again; fade out over 0.5 s.

## 5. Pixel-art rules (what made it look right)

- Everything sits on a coarse grid: background 10.67 px, fighters `duel.CPX`, FX 8 px, presenter 6 px,
  diagram 4 px per art pixel.
- Diagram camera zooms are whole multiples (1.0, 1.25, 1.5, so 4, 5 or 6 screen px per art pixel), and pans
  snap to art pixels (`zoom(..., snap=)`), which stops pixels shimmering.
- Use a limited palette with hard bands (`FX_PAL`), dark outlines around parts and FX, light-to-shadow
  checker dithering (`duel.BAYER`) and heat spread in dithered steps rather than smooth gradients.
- Dark characters on the dark diagram need a 1-cell light rim; snap presenter cells to two flat tones (ink
  or shirt white) so they don't turn into grey mush.
- Draw text after `pixel_fx`, otherwise the 8 px FX grid chops the font.

## 6. Animation rules

- Moves use `duel.move_curve`: a small wind-up, then acceleration, then settle. Knockbacks use a hard
  start that slows (`'knock'` destination pose).
- Ground movement steps with planted feet (stride tied to distance), and very fast dashes become short leaps.
  `tests/test_stick_duel_motion.py` guards both.
- Keep pose keys at least 0.12 s apart so they blend; use `rot` for flips and tumbles.

## 7. Gotchas met along the way

- Effects keyed to the old end time leaked into the extension; give each effect an explicit end time.
- PIL `rectangle` raises an error when x1 < x0; guard tiny animated arrows (`if x1 - x0 < 6: return`).
- Before the full render, scan every frame's logic quickly (`diagram_lowres(t)` and `caption(t)` for all t).
- The TTS free tier allows 3 requests/min; `tts.py` skips lines that already exist, so rerunning only fills gaps.
- PocketSphinx lives in `.venv`; spell out acronyms in `align.py`'s `NUM` map (for example ABS → "a b s").
- `pix.FONT` lacks J, Q, Z, apostrophe and colon; `brake/render.py` adds them.

## 8. Verification checklist (do all before sending)

1. `align.py` reports a word count for every line.
2. Stills: hook, event, both transitions, every diagram beat, outro.
3. A short test clip across each transition (motion and dissolve).
4. A frame-logic scan for exceptions.
5. Full render: `ffprobe` shows h264 + aac and the expected duration; a 0.5 fps contact sheet;
   `volumedetect` mean about −16 dB with no long silences.
6. `python3 -m unittest tests.test_stick_duel_motion` passes.

## 9. Handoff: current state

- Done: `videos/stick-duel` (12.1 s duel) and `videos/brake-explainer` (66.1 s explainer). Both share the fight
  upgrades: swing smears, impact frames, camera punch, colour split, sparks, slam debris and wind-up aura.
- Renders are not committed. Regenerate them with the commands in section 2. The voice clips live in
  `out/brake/vo/`; if they are missing, rerun `tts.py` and `align.py` (Gemini free tier: 3 requests/min).
- Open points: slam debris has not been checked at full size; the aura shows on every `windup`, so drop
  `'windup'` from `duel.aura` if it feels too frequent.
- Next topic: copy `videos/brake-explainer/src/` to `videos/<topic>/src/`, rewrite `script.json`, replace the
  diagram functions (`diagram_lowres`, `abs_panel`, the state functions, `POINTS`, `diagram_cam`) and the
  road event (car), then run the section 8 checklist.
