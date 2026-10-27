# Main Guy (explainer character model)

Reusable front-view pixel sprite for the TikTok explainer videos. Approved base design.

| Part | Spec |
|---|---|
| Skin | Brown `#c08862` (shade `#a06b4b`) |
| Hair | Dark messy, two cowlick strands `#231a1c` |
| Glasses | Silver square frames `#a9b0bb` |
| Top | Plain white t-shirt `#f7f7fa` |
| Bottoms | Baggy black jeans `#2b2d33` |
| Shoes | White sneakers `#f4f4f6` |
| Outline | Navy `#1a1a2e`, auto-generated |

- Grid: 36x60 px. `main-guy_1x.png` is native, `main-guy_16x.png` is nearest-neighbour upscaled. Both have a transparent background.
- Always scale with nearest-neighbour (`image-rendering: pixelated`) so pixels stay crisp.
- Regenerate or make outfit/expression variants by editing the palette `P` and rects in `make_sprite.py`, then run `python3 make_sprite.py <outdir>` (needs Pillow).
