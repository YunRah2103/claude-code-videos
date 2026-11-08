"""Overlay cards for the cinematic kit: framed photo card (or illustrated fallback), poll sticker, pills, tags.
All return 1x RGBA images with soft drop shadows; cached.

    photo_card(path, w=320, h=240)        # white mat frame, rounded, soft shadow; path=None -> illustrated retractor card
    poll_img(w=760, tap=0..1)             # 'Did you know that?' YES / NO with gradient buttons and tap ripple
    pill_img(text, fill, sz=60, icon=None)  # rounded label; icon='check' draws a tick before the text
"""
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from stickman.vec import Layer, hexc, SS
from stickman import car as C
from .paint import gfill

FONT = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
NAVY = (26, 26, 46, 255)


def font(sz):
    try: return ImageFont.truetype(FONT, sz)
    except OSError: return ImageFont.load_default(size=sz)


def _shadow(img, r=14, off=(0, 12), a=150):
    pad = r * 3
    out = Image.new('RGBA', (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new('RGBA', img.size, (8, 12, 24, a)); sh.putalpha(img.getchannel('A').point(lambda v: v * a // 255))
    out.alpha_composite(sh, (pad + off[0], pad + off[1]))
    out = out.filter(ImageFilter.GaussianBlur(r))
    out.alpha_composite(img, (pad, pad))
    return out


@lru_cache(4)
def photo_card(path=None, w=320, h=240):
    m = 14
    L = Layer(w + 2 * m, h + 2 * m + 8); P = L.pen()
    P.rrect((2, 2, w + 2 * m - 2, h + 2 * m + 6), 14, (250, 248, 242, 255), ow=3, oc=NAVY)
    card = L.done()
    if path:
        ph = ImageOps.fit(Image.open(path).convert('RGB'), (w, h), Image.LANCZOS)
    else:                                   # illustrated fallback: retractor close-up
        Q = Layer(w, h); R = Q.pen(w / 2 - C.RETRACTOR[0] * 30, h / 2 - C.RETRACTOR[1] * 30 - 10, 30)
        gfill(Q.pen(), [(0, 0), (w, 0), (w, h), (0, h)], (40, 60, 80, 255), (20, 28, 44, 255), (0, 0), (0, h))
        C.draw_retractor(R, 0.4, 1.0, 0.0)
        ph = Q.done().convert('RGB')
    mask = Image.new('L', (w * 2, h * 2), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, w * 2 - 1, h * 2 - 1), 16, fill=255)
    card.paste(ph, (m, m), mask.resize((w, h), Image.LANCZOS))
    return _shadow(card)


@lru_cache(64)
def poll_img(w=760, tap=0.0, q='Did you know that?', a='YES', b='NO'):
    h = 380
    L = Layer(w, h); P = L.pen()
    box = [(6, 6), (w - 6, 6), (w - 6, h - 6), (6, h - 6)]
    P.rrect((6, 6, w - 6, h - 6), 40, (255, 255, 255, 255), ow=4, oc=NAVY)
    P.text((w / 2, 82), q, font(64 * SS), NAVY, 'mm')
    bw = (w - 90) / 2
    for i, (lab, c0, c1) in enumerate(((a, hexc('#ffd54a'), hexc('#ff9b2e')), (b, hexc('#f4f6f9'), hexc('#d5dbe4')))):
        x0 = 36 + i * (bw + 18)
        on = i == 0 and tap > 0.3
        if on: c0, c1 = hexc('#6ee59a'), hexc('#25b864')
        dy = 6 * min(1, tap / 0.15) * (1 - min(1, max(0, tap - 0.15) / 0.3)) if i == 0 and tap > 0 else 0
        P.rrect((x0, 160 + 10, x0 + bw, 330 + 10), 34, (20, 24, 40, 70), ow=0)
        btn = (x0, 160 + dy, x0 + bw, 330 + dy)
        P.rrect(btn, 34, c0, ow=4, oc=NAVY)
        gfill(P, [(x0 + 6, 166 + dy), (x0 + bw - 6, 166 + dy), (x0 + bw - 6, 324 + dy), (x0 + 6, 324 + dy)], c0[:3] + (0,), c1[:3] + (255,), (0, 170 + dy), (0, 330 + dy))
        P.rrect((x0 + 24, 172 + dy, x0 + bw - 24, 196 + dy), 12, (255, 255, 255, 110), ow=0)
        P.text((x0 + bw / 2, 247 + dy), lab, font(76 * SS), NAVY, 'mm')
        if i == 0 and 0 < tap < 1:
            P.arc((x0 + bw / 2, 245), 40 + 220 * tap, 0, 360, 8 * (1 - tap), (255, 255, 255, int(230 * (1 - tap))))
    return _shadow(L.done(), 18, (0, 16), 140)


@lru_cache(64)
def pill_img(txt, fill, sz=60, fg=(26, 26, 46), icon=None):
    f = font(sz * SS); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    tw = d0.textlength(txt, font=f) / SS
    ic = sz * 0.9 if icon else 0
    w, h = int(tw + 70 + ic), int(sz * 1.6)
    L = Layer(w, h); P = L.pen()
    P.rrect((3, 3, w - 3, h - 3), h / 2, fill, ow=4, oc=NAVY)
    gfill(P, [(8, 6), (w - 8, 6), (w - 8, h * 0.5), (8, h * 0.5)], (255, 255, 255, 90), (255, 255, 255, 0), (0, 6), (0, h * 0.5))
    if icon == 'check':
        cx, cy = 34 + ic * 0.35, h / 2
        P.line([(cx - sz * 0.26, cy), (cx - sz * 0.06, cy + sz * 0.2), (cx + sz * 0.3, cy - sz * 0.24)], sz * 0.16, fg + (255,))
    P.text((w / 2 + ic / 2, h / 2 + 1), txt, f, fg, 'mm')
    return _shadow(L.done(), 10, (0, 8), 130)
