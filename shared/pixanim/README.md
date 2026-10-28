# pixanim: shared animation system for the pixel explainers

Reusable building blocks for directing an episode as a miniature film. Episode reference:
`videos/ac-idle/src/render.py` (V2).

Import from an episode `src/render.py`:

```python
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'shared'))
from pixanim.presenter import Presenter, reach
```

| Module | What it gives you |
|---|---|
| `motion.py` | Easing (incl. anticipation `back`, overshoot `ob`, `elastic`), `spring`/`springs` for needles, `jelly`/`wob` squash, `Track` keyframes (Catmull-Rom flight paths with `smooth=True`), `Orbit` (with `depth()` for passing behind objects), `Seq` to chain motions |
| `camera.py` | `Camera(keys, kicks, shakes, follow)`: centre/zoom shot framing, punch-in kicks, shake, follow targets; `to_screen`/`to_world` |
| `guy.py` | The main-guy sprite as a rig: expressions (`smile talk grin shock wow think smirk sad happy blink`), eye `gaze`, arm presets or `('aim', deg)`, legs (`stand run1 run2 fly tuck sit`) |
| `presenter.py` | `Presenter(beats)`: timeline of beats (path, size, arms/point, look, legs, expr, ground, z, visible, squash). Auto talking on voiceover, blinking, facing, gaze tracking, lean into motion, hover bob, motion ghosts and speed lines, contact shadows, landing wobbles. `reach(target, angle, s, facing)` puts his hand on a moving target (buttons, needles, sheets) |
| `fx.py` | `blit`, pop-ins, stamps with jelly, sparkles, confetti, dust, smoke `puff`, `poof`, light-shaft `rays`, shock `ring`, impact `burst`, glass `glint`, vent `flakes`, `speed_lines` |
| `transitions.py` | `whip` (any direction), `iris` zoom-through, `push` reveal, `cut`; pair them with a screen-space presenter overlay for character-driven transitions |
| `diagram.py` | `label` (leader line grows from a part, then the badge pops, can track moving parts), `arrow_to`, `glow_arc` for gauge ranges |
| `dash.py` | Car interior close-up (5 px grid): rev counter + speedometer with procedural needles, warning lamps, LCD, A/C button with press + LED, knobs, vents; `needle_tip()` for interactions |
| `engine.py` | Animated engine cutaway (5 px grid): pistons, con-rods, crank, spark flashes, serpentine belt with moving ribs, pulleys, A/C compressor clutch, frosting line, rev inset; `crank_angle()` integrates speed profiles; `comp_mask()` for occlusion |
| `car.py` | Detailed side-view car: palettes, rolling wheels (`wheel_deg`), headlights/brake lights, opening bonnet; grid anchors for roof, bay, exhaust, headlight |
| `street.py` | Night street with 5 parallax layers (stars, skyline, lit buildings + sign, lamps with light pools, road, foreground railing) |
| `props.py` | ECU robot, dust-sheet teaser object with lift reveal |
| `sprites.py`, `grid.py` | Small shared props (tags, stamps, badges, ticks, sparkles) and the pixel grid/font/outline helpers |

Conventions
- Each world keeps one pixel scale (dashboard and engine 5 px, garage 8-9 px, street 3 px); presenter size follows the world.
- Scenes draw onto a transparent RGBA foreground layer; worlds supply the background; the shot camera frames the composite.
- Occlusion: draw the presenter with `layer='back'` before foreground parts (or paste the part back through a mask), `'front'` after.
- Keep the voiceover and sound cues as the timing spine: put visual beats on the word times that already have cues.
