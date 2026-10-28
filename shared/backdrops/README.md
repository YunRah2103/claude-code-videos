# Shared backdrops

Reusable pixel backdrops for the explainer episodes. Scenes draw onto a transparent
foreground layer; the backdrop supplies the set, lighting and finishing passes.

## garage.py: monochrome workshop

Charcoal concrete panels, brick wainscot, silver skirting, pegboard with tool
silhouettes, metal shelving, stacked tyres, faint workbench, overhead pendant light.

| Call | What it does |
|---|---|
| `Garage(W, H, GROUND, S, light_x=540)` | Set up for the canvas, ground line and sprite scale |
| `frame(t)` | Backdrop RGB for time `t`: baked light cone, LED strip pulse, dust in the beam |
| `reflect(img, fg)` | Glossy floor reflection of the foreground below `GROUND` |
| `rim(fg)` | Top-edge highlights on sprites under the light; returns a new RGBA layer |
| `vignette(img)` | Heavy dark edges; call after the camera, before captions |

Import from an episode `src/render.py`:

```python
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'shared'))
from backdrops.garage import Garage
GAR = Garage(W, H, GROUND, S)

def compose(fg, t):
    img = GAR.frame(t); GAR.reflect(img, fg); fg = GAR.rim(fg); img.paste(fg, (0, 0), fg)
    return img
```

On a dark set, draw contact shadows and sunbursts with translucent RGBA fills
(see `videos/ac-idle/src/render.py`). Episode reference: `videos/ac-idle`.
