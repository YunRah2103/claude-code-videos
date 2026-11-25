"""Render Yub's reference sheets into characters/yub-3d/previews/:
turnaround.png (front, 3/4, side, back), expressions.png (all 11 faces), poses.png (common poses).
Run from the repo root:  python characters/yub-3d/make_previews.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(1, os.path.join(HERE, "..", "..", "lib", "cine3d"))
from PIL import Image, ImageDraw, ImageFont
from geo import Cam, tiles, cat
from render3d import render, Env
from yub import yub, EXPR_NAMES

OUT = os.path.join(HERE, "previews"); os.makedirs(OUT, exist_ok=True)
STUDIO = Env(sky_top=(150, 175, 215), sky_hor=(236, 236, 242), ground=(150, 150, 160), sun_dir=(-0.45, 0.75, 0.6), sun=(255, 246, 236), sun_i=1.9,
             amb_i=1.0, fog=None, exposure=0.95, bloom=0.3, sun_disc=False, sat=1.05, shadow_size=6, shadow_center=(0, 0, 0))
FLOOR = tiles(-6, -6, 6, 6, 0, 2.0, -1, (200, 200, 208))
FONT = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", 30)

def shot(scene, cam, w=405, h=720):
    return Image.fromarray(render(scene, cam, STUDIO)).resize((w, h), Image.LANCZOS)

def sheet(ims, labels, path, cols):
    w, h = ims[0].size; rows = (len(ims) + cols - 1) // cols
    s = Image.new("RGB", (cols * w, rows * (h + 44)), (250, 250, 252)); d = ImageDraw.Draw(s)
    for i, (im, lab) in enumerate(zip(ims, labels)):
        x, y = (i % cols) * w, (i // cols) * (h + 44)
        s.paste(im, (x, y)); d.text((x + w / 2, y + h + 22), lab, font=FONT, fill=(30, 30, 40), anchor="mm")
    s.save(path); print("wrote", path)

if __name__ == "__main__":
    body = yub("smile")
    turn = []
    for lab, ang in (("front", 0), ("three-quarter", 35), ("side", 90), ("back", 180)):
        turn.append(shot([FLOOR, body.copy().rot("y", ang)], Cam((0, 1.05, 3.6), (0, 0.95, 0), 40)))
    sheet(turn, ["front", "three-quarter", "side", "back"], os.path.join(OUT, "turnaround.png"), 4)

    ex = [shot([FLOOR, yub(e, sweat=(e == "panic"), blush=(e in ("grin", "proud")))], Cam((0, 1.66, 0.95), (0, 1.66, 0), 34), 324, 432) for e in EXPR_NAMES]
    sheet(ex, EXPR_NAMES, os.path.join(OUT, "expressions.png"), 6)

    poses = [("idle", dict()), ("wave", dict(ra=(0, 150, 30), wave="r", expr="grin")), ("point", dict(ra=(80, 10, 0), expr="smile")),
             ("shrug", dict(la=(25, 55, 80), ra=(25, 55, 80), expr="confused")), ("facepalm", dict(la=(135, 10, 150), expr="cringe", head=(0, 12, 0))),
             ("thumbs up / smug", dict(ra=(75, 10, 85), expr="smug", head=(-12, 0, 6))), ("sitting (driving)", dict(sit=True, la=(55, 4, 40), ra=(55, 4, 40))),
             ("arms on hips", dict(la=(10, 20, 100), ra=(10, 20, 100), expr="smug"))]
    ims = []
    for lab, kw in poses:
        e = kw.pop("expr", "smile"); p = yub(e, **kw)
        if kw.get("sit"): p = cat([p.mv(0, 0.25, 0)])
        ims.append(shot([FLOOR, p.rot("y", 20)], Cam((0, 1.05, 3.6), (0, 0.95, 0), 40)))
    sheet(ims, [p[0] for p in poses], os.path.join(OUT, "poses.png"), 4)
