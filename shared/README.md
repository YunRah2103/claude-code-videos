# shared/

Reusable pieces for the pixel-art explainer episodes. Each episode in `videos/*/src` imports from here.
Nothing in `shared/` depends on a specific episode.

| Package | Use it for | Start here |
|---|---|---|
| `backdrops/garage.py` | Monochrome garage set: light cone, dust, LED pulse, floor reflection, rim light, vignette | `backdrops/README.md` |
| `pixanim/` | Film-style animation: presenter rig and timeline, flight paths, shot camera, transitions, effects, diagram labels, dashboard, engine cutaway, car, street, props | `pixanim/README.md` |

## Importing from an episode

An episode lives at `videos/<name>/src/render.py`, so `shared/` is three levels up:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'shared'))
from backdrops.garage import Garage
from pixanim.presenter import Presenter, reach
from pixanim.motion import Track, Orbit, springs
from pixanim.camera import Camera
```

## Reference episode

`videos/ac-idle/src/render.py` (V2) uses every package here. Read it for worked examples of shots,
character beats, transitions and the caption/audio code that stays unchanged.

## Checks

From a fresh clone, all modules import and render frames at 1080×1920. The smoke test is the
snippet in `pixanim/README.md`; run it after changing any shared module.
