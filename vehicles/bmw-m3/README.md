# BMW M3 (E90 sedan) — reusable vehicle sprite

Side-view pixel sprite traced from an E90 M3 profile photo. Faces **left**.

| Detail | Pixel feature |
|---|---|
| Silhouette | Long hood, raked windscreen, short trunk with lip spoiler |
| Glass | Black trim, B-pillar, quarter window with Hofmeister kink |
| Body | Shoulder crease, fender gill, mirror, door handles, side skirt |
| Lights | Headlight with angel eye, wraparound L tail light |
| Wheels | Mesh multi-spoke rims, red calipers, 2-frame spin (`phase` 0/1) |
| Rear | Diffuser with quad exhaust pipes |

- Grid: 96x35 px, transparent background, navy `#1a1a2e` auto-outline.
- Colours: `blue` (default), `silver`, `black`, `red`, `green`, `broken` (rusty, for repair gags).
- Always scale with nearest-neighbour. Scale 6 (576x210) fits beside the main guy in 1080x1920.

## Use

```python
import sys; sys.path.insert(0, 'vehicles/bmw-m3')
import bmw_m3
img = bmw_m3.sprite('blue', phase=0)   # PIL RGBA, 96x35
```

`videos/bmw-3-series/src/pix.py` imports it as `pix.m3(color, phase)`.
Regenerate the PNGs: `python bmw_m3.py vehicles/bmw-m3`.
For other models, copy this folder, keep `Grid`/`sprite()` and change the
greenhouse lines, `top(x)` profile, `WHEELS` and palette.
