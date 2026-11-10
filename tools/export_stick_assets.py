"""Export the reusable stick-explainer assets as PNGs (transparent sprites + backgrounds).

    python tools/export_stick_assets.py            # writes assets/stick-explainer/

Everything is generated from code (videos/stick-duel, videos/brake-explainer, videos/new-car-trap), so the PNGs are
references/previews for other tools; videos should keep importing the code so animation, pixel snapping and FX match.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'stick-explainer'


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def crop(img, pad=6):
    box = img.getbbox()
    return img.crop((max(0, box[0] - pad), max(0, box[1] - pad), box[2] + pad, box[3] + pad)) if box else img


def sheet(sprites, bg=(0, 0, 0, 0)):
    w = sum(s.width for s in sprites) + 8 * (len(sprites) + 1); h = max(s.height for s in sprites) + 16
    out = Image.new('RGBA', (w, h), bg); x = 8
    for s in sprites:
        out.alpha_composite(s, (x, h - 8 - s.height)); x += s.width + 8
    return out


def main():
    brake = load('brake', 'videos/brake-explainer/src/render.py')
    duel, pix = brake.duel, brake.pix
    OUT.mkdir(parents=True, exist_ok=True)
    big, _ = duel.build_bg()
    Image.fromarray(big.astype(np.uint8)).save(OUT / 'bg_mountain_meadow_1280x720.png')
    road, _ = brake.build_road()
    Image.fromarray(road.astype(np.uint8)).save(OUT / 'bg_mountain_road_1280x720.png')
    pix.car('blue', 0).save(OUT / 'car_blue_52x24.png')
    brake.CAR_IMG[0].save(OUT / 'car_blue_x6.png')

    poses = ['stand', 'crouch', 'windup', 'slash', 'dash', 'punch', 'flykick', 'tuck', 'land', 'guardup', 'knock']
    for cloak, name in (('green', 'fighter_green_katana'), ('red', 'fighter_red_axe')):
        sprites = []
        for p in poses:
            lay = Image.new('RGBA', (brake.W, brake.H), (0, 0, 0, 0))
            duel.draw_fighter(ImageDraw.Draw(lay), [(0, 640, 0, p, 1)], 0.0, cloak, 1.0, 600)
            sprites.append(crop(duel.pixelate(lay, duel.CPX)))
        sheet(sprites).save(OUT / f'{name}_poses.png')
    sprites = [crop(brake.host_layer(0.0, [(0, 640, 0, p, 1)])) for p in ('idle', 'talk1', 'talk2', 'point', 'kneeup', 'shrug')]
    sheet(sprites).save(OUT / 'presenter_shirt_glasses_poses.png')

    pal = duel.FX_PAL.astype(np.uint8)
    sw = Image.new('RGB', (len(pal) * 24, 24))
    for i, c in enumerate(pal): sw.paste(tuple(int(v) for v in c), (i * 24, 0, i * 24 + 24, 24))
    sw.save(OUT / 'fx_palette.png')
    lay = Image.new('RGBA', (360, 200), (0, 0, 0, 0))
    lay.alpha_composite(brake.diagram_lowres(brake.wt(6, 'heat') + 1.5).crop((200, 50, 380, 150)).resize((360, 200), Image.Resampling.NEAREST))
    lay.save(OUT / 'diagram_rotor_hot_preview.png')
    for f in sorted(OUT.glob('*.png')): print(f.relative_to(ROOT), Image.open(f).size)


if __name__ == '__main__':
    sys.exit(main())
