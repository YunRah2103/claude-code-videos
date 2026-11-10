# Stickman cast (pixel art)

Code: `videos/stick-duel/src/render.py` (`draw_fighter`), presenter: `videos/brake-explainer/src/render.py` (`host_layer`).
Pose sheets: `assets/stick-explainer/` (regenerate with `python tools/export_stick_assets.py`).

| Character | `cloak` | Look | Weapon |
|---|---|---|---|
| Green fighter | `green` | black stickman, long green coat, scarf trail | curved katana with gold guard |
| Red fighter | `red` | black stickman, long red cape | long-haft battle axe with red edge |
| Presenter | `shirt` | same plain stickman, white shirt, glasses (two light-blue lenses), light rim | none; gestures `idle talk1 talk2 point kneeup shrug` |

Rules: keep the black ink body (`duel.INK`), snap to the pixel grid, and give dark characters a light rim on dark backgrounds.
