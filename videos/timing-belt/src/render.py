"""timing-belt: 'A snapped timing belt' (car stuff, explained; series6 via series10 engine, opening: zoom-out).
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <vo.wav> <out.mp4> [t0 t1]"""
import math, os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared', 'series10'))
import engine as S
from engine import W, H, G, kit, cb, X, fx, up, D, prog, oc, io, lerp
from assets import series6bits as B

WORDS = kit.load_words(HERE); ST = S.sentences(WORDS)
def sw(n): return WORDS[ST[n]]['s']
HOOK = ((('A', None), ('SNAPPED', '#e8343f')), (('timing belt', None),))
KEYCOL = {'snapped': kit.RED, 'timing': kit.YEL, 'belt': kit.YEL, 'wreck': kit.RED, 'valves': kit.YEL, 'pistons': kit.YEL,
          'collide': kit.RED, 'interference': kit.RED, 'manual': kit.YEL, 'replace': kit.YEL}
SNAP = 0.55
HIT = sw(1) + 1.2                                             # valve meets piston


def layer(img, spr, s, x, y, anchor='bottom'):
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0)); fx.blit(fg, up(spr, s), x, y, anchor=anchor); img.alpha_composite(G.rim(fg))


def shot_open(t):
    img = S.stage(t); sn = prog(t, SNAP, 0.25)
    layer(img, B.belt_drive(t, sn), 7, 620, 1760)
    if SNAP <= t < SNAP + 0.4: fx.ring(img, t, SNAP, 450, 1300, (232, 52, 63), life=0.4, r1=220)
    cb.pill(img, t, 0.3, 99, 'TIMING BELT', (452, 1100), (600, 700), '#ffd23f', '#1a1a2e', '#c9a21c')
    return img


def shot_cut(t):
    img = S.stage(t)
    gap = 1 - io(prog(t, HIT - 0.7, 0.7)) if t < HIT + 0.6 else 0.25 * (1 + math.sin((t - HIT) * 8))
    hit = max(0.0, 1 - abs(t - HIT) * 4) if t < HIT + 0.3 else (1.0 if gap < 0.1 else 0.0)
    layer(img, B.valve_piston(gap, hit), 6, 640, 1720)
    layer(img, B.belt_drive(t, 1.0), 3, 860, 960)
    cb.pill(img, t, sw(1) + 0.3, 99, 'VALVE', (640, 1310), (420, 560), '#ffffff', '#1a1a2e', '#d6d9e2')
    cb.pill(img, t, sw(1) + 0.7, 99, 'PISTON', (720, 1520), (420, 760), '#ffffff', '#1a1a2e', '#d6d9e2')
    return img


def shot_key(t):
    img = S.stage(t); g = 0.5 + 0.5 * math.sin(t * 5)               # belt intact: valve and piston never quite meet
    layer(img, B.belt_drive(t), 4, 520, 1640)
    layer(img, B.valve_piston(0.15 + 0.5 * g), 5, 850, 1720)
    cb.pill(img, t, sw(2) + 0.2, sw(3) - 0.1, 'INTERFERENCE', (850, 1440), (480, 560), '#e8343f', '#ffffff', '#a01c26')
    cb.pill(img, t, sw(3), 99, 'CHECK YOUR MANUAL', (520, 1260), (480, 560), '#ffd23f', '#1a1a2e', '#c9a21c')
    return img


CUES = [(SNAP, 'clack', 1.0), (SNAP + 0.05, 'snap', 0.6), (sw(1) + 0.3, 'pop', 0.5), (HIT, 'clack', 1.0), (HIT + 0.02, 'thump', 0.6),
        (sw(2) + 0.2, 'buzzer', 0.4), (sw(3), 'click', 0.7)]
S.build(HERE, WORDS, HOOK, KEYCOL, 'zoom-out', (560, 1200), (420, 1250), (shot_open, shot_cut, shot_key), 2,
        ('Know when yours is due?', (('YES', S.ov.GRN), ('NO', S.ov.RED)), 480, 820, 3), CUES, cut_point=(640, 1300),
        key_point=(850, 1440), lufs=-15.6, ask_prop=lambda t: (B.belt_drive(t), 4))

if __name__ == '__main__':
    D.cli()
