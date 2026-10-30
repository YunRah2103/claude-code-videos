# shared/

Reusable pieces for the pixel-art explainer episodes. Nothing here depends on one episode.

## Start here (for the next agent)

1. Check this folder first. Reuse what exists instead of writing new code.
2. Use the reference episode `videos/ac-idle/src/render.py` as the template: copy its import block and shot structure.
3. Don't re-read large files in full. Read this README and the package README you need, then the relevant functions.
4. Keep the existing voiceover, `words.json` and the sound-cue timeline. Align only if the script changes.
5. Test with a few stills (`tools/video.py preview --times ...`), then one short clip, then the full render.

## What is here

| Path | What it gives you | Read |
|---|---|---|
| `backdrops/garage.py` | Monochrome garage set: light cone, dust, LED pulse, floor reflection, rim light, vignette | `backdrops/README.md` |
| `pixanim/` | Presenter rig + timeline, flight paths, shot camera, transitions, effects, diagram labels, dashboard, engine cutaway, car, street, props | `pixanim/README.md` |
| `audio/sfx.py` | Synthesised sound effects (pop, whoosh, stamp, ding, click, confetti, vroom, etc.) and `render(cues, duration)` | docstrings in the file |

| `episode.py` | Episode kit lifted from ac-idle/jaguar: captions (one highlighted keyword), hook `title`, framed real `photo` cards, progress bar, NEXT EPISODE `teaser`, photo-credit line, `build_audio` mixer, `still`/`video` CLI. No corner gauge. Example: `videos/tractors-vs-ferraris/src/render.py` | module docstring |
| `align.py` | `align(script, mp3, out_json, say=, extra=)`: pocketsphinx forced alignment -> `words.json` (numbers spoken as words, extra phones for names) | docstring |
| `vo.py` | `tighten(src_mp3, words, out_mp3, target=17.2)`: shortens long pauses and applies a gentle atempo for short-form pacing; re-align the result. `episode.setup(..., gauge=True, loud=True)` adds the corner rev counter and -14 LUFS loudness | docstring |
| `split_vo.py` | Split one long voiceover into per-episode clips at long silences (`silencedetect`, default -35 dB / 1.5 s); fails unless the count matches | docstring |
| `pixanim/autos.py` | Sprites: supercar wedges, endurance racer, muscle coupe, EV saloons, V12/V8, motor, battery, chargers, plug/socket, light tree, year calendar, trophy, flag | docstring |
| `photos.py` | Fetch Wikimedia Commons photos + `credits.json` (file, source, licence, author) into `videos/<ep>/assets/` (jpgs are git-ignored) | docstring |

`episode.setup(..., crisp=True)` keeps the handheld sway nearest-neighbour; `photo(..., hq=True)` called from the overlay shows the whole photo uncropped, Lanczos-scaled. `vo.pace()` adds silence for very short reads.

Older episodes still carry their own copies of the caption/progress/mixer code; new ones use `episode.py`.

## Importing from an episode

An episode lives at `videos/<name>/src/render.py`, so `shared/` is three levels up:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'shared'))
from backdrops.garage import Garage
from pixanim.presenter import Presenter, reach
from pixanim.motion import Track, Orbit, springs
from pixanim.camera import Camera
from audio import sfx
```

## Checks

From a fresh clone, all modules should import and render frames at 1080×1920. After changing any shared module, run the smoke test in `pixanim/README.md`.
