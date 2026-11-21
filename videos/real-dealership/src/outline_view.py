"""Overlay a traced outline on its photo (with a 5% grid) to correct points. Usage: python outline_view.py EPDIR NAME OUT.png [x0 x1]"""
import os, sys, importlib.util
from PIL import Image, ImageDraw, ImageFont
ep, name, out = os.path.abspath(sys.argv[1]), sys.argv[2], sys.argv[3]
spec = importlib.util.spec_from_file_location('c', os.path.join(ep, 'cutouts.py')); C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
src, poly, _ = C.CUTS[name]
x0, x1 = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (0, 100)
im = Image.open(os.path.join(ep, 'assets', src)).convert('RGB'); W, H = im.size
im = im.crop((int(W * x0 / 100), 0, int(W * x1 / 100), H)); sc = 1000 / im.width
im = im.resize((1000, int(H * sc))); d = ImageDraw.Draw(im); F = ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf', 13)
P = lambda x, y: ((x - x0) / 100 * W * sc, y / 100 * H * sc)
for i in range(1, 40):
    v = i * 2.5
    if x0 < v < x1:
        d.line([P(v, 0), P(v, 100)], fill=(0, 255, 255) if i % 2 else (255, 0, 255)); d.text((P(v, 0)[0] + 2, 2), f'{v:g}', fill=(255, 255, 0), font=F, stroke_width=2, stroke_fill=0)
    d.line([P(x0, v), P(x1, v)], fill=(0, 255, 255) if i % 2 else (255, 0, 255)); d.text((2, P(0, v)[1] + 1), f'{v:g}', fill=(255, 255, 0), font=F, stroke_width=2, stroke_fill=0)
pts = [P(*p) for p in poly]
d.line(pts + [pts[0]], fill=(255, 30, 30), width=2)
for i, p in enumerate(pts): d.ellipse((p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3), fill=(255, 255, 0)); d.text((p[0] + 4, p[1] - 14), str(i), fill=(255, 255, 255), font=F, stroke_width=2, stroke_fill=0)
im.save(out)
