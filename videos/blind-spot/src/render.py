"""blind-spot: 'Something's in your BLIND SPOT' (car stuff, explained; series6 via series10 engine, opening: slow-motion).
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <vo.wav> <out.mp4> [t0 t1]"""
import math, os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared', 'series10'))
import engine as S
from engine import W, H, G, kit, cb, X, fx, up, D, prog, oc, io, lerp
from assets import series6bits as B

WORDS = kit.load_words(HERE); ST = S.sentences(WORDS)
def sw(n): return WORDS[ST[n]]['s']
HOOK = ((('Something\'s in your', None),), (('BLIND SPOT', '#e8343f'),))
KEYCOL = {'blind': kit.RED, 'spot': kit.RED, 'mirrors': kit.YEL, 'whole': kit.YEL, 'head': kit.YEL, 'check': kit.YEL,
          'gap': kit.RED, 'warnings': kit.YEL}
RX, RY, RS = 560, 1900, 6                                  # road sprite: bottom-centre anchor and scale
def g(x, y): return RX - 70 * RS + x * RS, RY - 200 * RS + y * RS   # road grid -> frame
MIRROR, OTHER, DRIVER = g(54, 84), g(108, 132), g(28, 88)


def road(img, t, k, other=True):
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0)); fx.blit(fg, up(B.blind_road(k, t, other), RS), RX, RY); img.alpha_composite(G.rim(fg))


def shot_open(t):
    img = S.stage(t); road(img, t, 0.55 + 0.3 * math.sin(t * 4) ** 2)
    cb.pill(img, t, 0.3, 99, 'BLIND SPOT', OTHER, (600, 680), '#e8343f', '#ffffff', '#a01c26')
    return img


def shot_cut(t):
    img = S.stage(t); road(img, t, 0.15)
    cb.pill(img, t, sw(1) + 0.3, 99, 'MIRROR VIEW', g(66, 170), (470, 600), '#50aaff', '#1a1a2e', '#2f78c0')
    if int(t * 2) % 2 == 0: cb.pill(img, t, sw(1) + 1.0, 99, '?', OTHER, (800, 860), '#ffffff', '#1a1a2e', '#d6d9e2')
    return img


def shot_key(t):
    img = S.stage(t); road(img, t, oc(prog(t, sw(2), 0.6)))
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(B.head_check(io(prog(t, sw(2) + 0.3, 0.5)) - io(prog(t, sw(3) - 0.3, 0.4)) * 0.6), 5), *DRIVER, anchor='center')
    if t >= sw(3) and int(t * 4) % 2 == 0:                          # amber blind-spot warning in the mirror
        d = ImageDraw.Draw(fg); x, y = MIRROR
        d.polygon([(x - 26, y + 22), (x + 26, y + 22), (x, y - 24)], fill=(255, 150, 30, 255), outline=(26, 26, 46, 255))
        d.rectangle((x - 3, y - 8, x + 3, y + 8), fill=(26, 26, 46, 255))
    img.alpha_composite(fg)
    cb.pill(img, t, sw(2) + 0.2, sw(3) - 0.1, 'HEAD CHECK', DRIVER, (470, 600), '#46d26e', '#1a1a2e', '#2f9a4e')
    cb.pill(img, t, sw(3), 99, 'BLIND SPOT WARNING', MIRROR, (480, 600), '#ffd23f', '#1a1a2e', '#c9a21c')
    return img


CUES = [(0.25, 'alert', 0.5), (sw(1) + 0.3, 'pop', 0.6), (sw(2) + 0.3, 'whoosh', 0.5), (sw(2) + 0.35, 'pop', 0.5),
        (sw(3), 'alert', 0.9), (sw(3) + 0.5, 'beep', 0.4)]
S.build(HERE, WORDS, HOOK, KEYCOL, 'slow-motion', (620, 1300), OTHER, (shot_open, shot_cut, shot_key), 2,
        ('Do you check every time?', (('ALWAYS', S.ov.GRN), ('NOT ALWAYS', S.ov.RED)), 470, 700, -2), CUES,
        cut_point=g(66, 170), key_point=DRIVER, ask_prop=lambda t: (B.blind_road(0.5 + 0.5 * math.sin(t * 3) ** 2, t), 2))

if __name__ == '__main__':
    D.cli()
