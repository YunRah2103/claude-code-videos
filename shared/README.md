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

## Not shared yet (still in `videos/ac-idle/src/render.py`)

- Caption chunking and highlighting, title and end-card text, progress bar, and the `build_audio` mixer.
  Copy these from the reference episode when you need them. They depend on that episode's `WORDS` timing.

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
