"""Flat-vector poll sticker: 'Did you know that?' with YES / NO buttons (TikTok-style), thick outline + soft shadow.

    img = poll_img(w=760, tap=0..1, font_path=...)   # RGBA 1x; tap > 0 fills YES with a ripple + tick
"""
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from .vec import INK, hexc, Layer

FONT = '/usr/share/fonts/opentype/inter/Inter-Black.otf'


def _f(sz, path=FONT):
    try: return ImageFont.truetype(path, sz)
    except OSError: return ImageFont.load_default(size=sz)


@lru_cache(64)
def poll_img(w=760, tap=0.0, q='Did you know that?', a='YES', b='NO'):
    tap = round(tap, 2); h = 400
    L = Layer(w + 40, h + 50); P = L.pen(); d = L.d
    sh = Image.new('L', ((w + 40) * 2, (h + 50) * 2), 0)
    ImageDraw.Draw(sh).rounded_rectangle((36, 52, w * 2 + 36, h * 2 + 40), 72, fill=110)
    L.img.paste((20, 22, 30, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(16)))
    P.rrect((14, 10, w + 14, h + 10), 36, (255, 255, 255, 255), ow=7)
    P.rrect((14, 10, w + 14, 30), 0, (255, 255, 255, 255), ow=0)
    P.text((w / 2 + 14, 92), q, _f(66 * 2), INK, anchor='mm')
    bw = (w - 90) / 2
    for i, (lab, col) in enumerate(((a, hexc('#ffc928')), (b, hexc('#e9ebee')))):
        x0 = 44 + i * (bw + 30)
        on = i == 0 and tap > 0
        fill = hexc('#3ccf6e') if on and tap > 0.3 else col
        P.rrect((x0, 168 + 8, x0 + bw, 338 + 8), 30, INK, ow=0)
        dy = 6 * min(1, tap / 0.15) * (1 - min(1, max(0, tap - 0.15) / 0.3)) if i == 0 else 0
        P.rrect((x0, 168 + dy, x0 + bw, 338 + dy), 30, fill, ow=6)
        P.text((x0 + bw / 2, 253 + dy), lab + (' ✓' if on and tap > 0.3 else ''), _f(78 * 2), INK, anchor='mm')
        if on and tap < 1:
            r = 40 + 260 * tap
            P.arc((x0 + bw / 2, 253), r, 0, 360, 8 * (1 - tap), (255, 255, 255, int(220 * (1 - tap))))
    return L.done()
