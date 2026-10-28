"""The main-guy presenter sprite (48x60 grid): short dark hair, round silver glasses, white tee, dark jeans, white sneakers.

Same design as characters/main-guy, rebuilt as a rig:
  arms  - preset name (ARMS) or ('aim', angle_deg) for the right arm; angle 0 = outward, 90 = down, -90 = up
  legs  - 'stand', 'run1', 'run2', 'fly', 'tuck', 'sit'
  expr  - 'smile', 'talk', 'grin', 'shock', 'wow', 'think', 'smirk', 'sad', 'happy' (eyes closed)
  gaze  - (gx, gy), each -1..1: pupils follow whatever the presenter is looking at
Arms stay attached at the shoulders; everything is drawn on the pixel grid, then scaled with nearest neighbour.
"""
import math
from functools import lru_cache
from .grid import Grid, hexc

GP = {
 'hair': '#231a1c', 'hairhi': '#4f3d42', 'skin': '#c08862', 'skinsh': '#a06b4b', 'blush': '#d4917a',
 'mouth': '#6e2f33', 'inner': '#3a1418', 'eye': '#12121c', 'white': '#ffffff', 'frame': '#a9b0bb', 'framehi': '#d3d8e0',
 'framesh': '#7b8491', 'tee': '#f7f7fa', 'teesh': '#d6d9e2', 'jeans': '#2b2d33', 'jeansh': '#1f2025',
 'jeanhi': '#454852', 'waist': '#16171b', 'shoe': '#f4f4f6', 'shoesh': '#cfd2da', 'sole': '#b9bcc6',
}
OX = 6            # side padding so arms can reach outward
W, H = 36 + 2 * OX, 60
SHOULDER_R = (26 + OX, 31)
FEET = (W / 2, H)  # sprite anchor: bottom centre

_D = ((0, 6), (0, 11))
ARMS = {
 'down': (_D, _D), 'down2': (((1, 6), (1, 11)), ((1, 6), (1, 11))),
 'talkR': (_D, ((2, 6), (6, 2))), 'talkL': (((2, 6), (6, 2)), _D), 'talkB': (((2, 6), (5, 3)), ((2, 6), (5, 3))),
 'point': (_D, ((5, -1), (11, -2))), 'pointup': (_D, ((5, -3), (9, -8))),
 'up1': (((3, -5), (5, -12)), ((3, -5), (5, -12))), 'up2': (((4, -5), (7, -11)), ((4, -5), (7, -11))),
 'shrug': (((4, 4), (7, -1)), ((4, 4), (7, -1))), 'shock': (((4, -1), (5, -7)), ((4, -1), (5, -7))),
 'hips': (((4, 4), (1, 8)), ((4, 4), (1, 8))), 'thumb': (_D, ((4, 6), (7, 0))), 'catch': (_D, ((3, 6), (8, 6))),
 'wave1': (_D, ((5, -2), (6, -10))), 'wave2': (_D, ((4, -3), (9, -9))),
 'flail1': (((5, -2), (9, -6)), ((5, 2), (10, 4))), 'flail2': (((5, 2), (10, 4)), ((5, -2), (9, -6))),
 'present': (((2, 6), (4, 9)), ((4, 3), (10, 1))), 'think': (((2, 6), (4, 10)), ((1, 4), (-3, -6))),
 'push': (((3, 2), (-6, 1)), ((5, 1), (11, 1))), 'hold': (((4, -3), (8, -9)), ((4, -3), (8, -9))),
 'fly': (((4, 1), (9, 3)), ((4, 1), (9, 3))), 'cheer1': (((4, -5), (7, -12)), ((4, -5), (7, -12))),
 'cheer2': (((5, -4), (10, -10)), ((5, -4), (10, -10))), 'brace': (((4, 1), (8, 5)), ((4, 1), (8, 5))),
}
THUMB = {'thumb'}

LEGS = {  # per leg: (x shift, lift) for the lower leg and shoe
 'stand': ((0, 0), (0, 0)), 'run1': ((-2, 3), (1, 0)), 'run2': ((-1, 0), (2, 3)),
 'fly': ((-2, 2), (-2, 1)), 'tuck': ((-1, 4), (1, 4)), 'sit': ((-2, 3), (2, 3)),
}


def aim_arm(angle_deg):
    """Right arm reaching along angle (sprite space, 0 = outward, 90 = down)."""
    a = math.radians(angle_deg)
    return ((round(5.5 * math.cos(a) + 0.8), round(5.5 * math.sin(a) + 0.8)), (round(11 * math.cos(a)), round(11 * math.sin(a))))


def hand_offset(angle_deg, s, facing=1):
    """World offset of the right hand from the feet anchor for an aimed arm at pixel size s."""
    a = math.radians(angle_deg)
    x = SHOULDER_R[0] - FEET[0] + 11 * math.cos(a) + 1
    y = SHOULDER_R[1] - FEET[1] + 11 * math.sin(a) + 1
    return x * s * facing, y * s


def _line(a, b):
    (x0, y0), (x1, y1) = a, b
    pts = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if (x0, y0) == (x1, y1): break
        e2 = 2 * err
        if e2 >= dy: err += dy; x0 += sx
        if e2 <= dx: err += dx; y0 += sy
    return pts


def _arm(g, sh, pose, side):
    (ex, ey), (hx, hy) = pose
    sgn = -1 if side == 'L' else 1
    e = (sh[0] + sgn * ex, sh[1] + ey)
    h = (sh[0] + sgn * hx, sh[1] + hy)
    pts = _line(sh, e) + _line(e, h)[1:]
    for i, (x, y) in enumerate(pts):
        g.rect(x - 1, y - 1, x + 1, y + 1, GP['tee'] if i < 3 else GP['skin'])
    if len(pts) > 3:
        x, y = pts[3]; g.rect(x - 1, y - 1, x + 1, y + 1, GP['teesh'])
        for x, y in pts[4:]:
            g.rect(x - 1, y - 1, x + 1, y + 1, GP['skin'])
    x, y = h
    if side == 'L': g.rect(x - 2, y - 1, x + 1, y + 2, GP['skin'])
    else: g.rect(x - 1, y - 1, x + 2, y + 2, GP['skin'])
    return h


def _arms_spec(arms):
    if isinstance(arms, tuple) and arms and arms[0] == 'aim':
        return (_D, aim_arm(arms[1])), False
    if isinstance(arms, tuple) and arms and arms[0] == 'aim2':      # left arm down at hip, right aimed
        return (((4, 4), (1, 8)), aim_arm(arms[1])), False
    return ARMS[arms], arms in THUMB


@lru_cache(None)
def _body(arms, legs):
    g = Grid(W, H)
    def r(x0, y0, x1, y1, c): g.rect(x0 + OX, y0, x1 + OX, y1, GP[c] if c else None)
    def p(x, y, c): g.px(x + OX, y, GP[c] if c else None)
    # head and hair
    r(14, 0, 14, 1, 'hair'); r(18, 0, 18, 1, 'hair')
    r(8, 2, 27, 12, 'hair')
    r(12, 3, 17, 4, 'hairhi'); r(20, 3, 24, 3, 'hairhi')
    r(9, 13, 9, 14, 'hair'); r(26, 13, 26, 14, 'hair')
    r(9, 9, 26, 25, 'skin')
    r(9, 9, 26, 10, 'hair'); r(13, 9, 18, 11, 'skin')
    r(10, 11, 12, 11, 'hair'); r(20, 10, 25, 11, 'hair')
    r(9, 11, 9, 12, 'hair'); r(26, 11, 26, 12, 'hair')
    r(8, 13, 8, 14, 'hair'); r(27, 13, 27, 14, 'hair')
    p(9, 25, None); p(26, 25, None); p(9, 24, 'skin'); p(26, 24, 'skin')
    r(7, 14, 8, 19, 'skin'); r(27, 14, 28, 19, 'skin')
    r(9, 14, 9, 20, 'skinsh'); r(26, 14, 26, 20, 'skinsh')
    r(11, 12, 15, 12, 'hair'); r(20, 12, 24, 12, 'hair')
    for (x0, x1) in ((10, 16), (19, 25)):
        r(x0, 13, x1, 19, 'frame'); r(x0 + 1, 14, x1 - 1, 18, 'skin')
        r(x0, 13, x1, 13, 'framehi'); r(x0, 19, x1, 19, 'framesh')
    r(17, 14, 18, 14, 'frame'); r(9, 14, 9, 15, 'frame'); r(26, 14, 26, 15, 'frame')
    r(17, 20, 18, 21, 'skinsh')
    r(11, 21, 12, 21, 'blush'); r(23, 21, 24, 21, 'blush')
    # torso
    r(15, 26, 20, 29, 'skinsh')
    r(9, 28, 26, 31, 'tee')
    r(11, 28, 24, 43, 'tee')
    r(15, 28, 20, 29, 'skinsh'); r(16, 30, 19, 30, 'skinsh')
    r(14, 28, 14, 29, 'teesh'); r(21, 28, 21, 29, 'teesh'); p(15, 30, 'teesh'); p(20, 30, 'teesh')
    r(14, 31, 21, 31, 'teesh')
    r(11, 40, 14, 40, 'teesh'); r(22, 38, 24, 38, 'teesh')
    r(11, 34, 11, 43, 'teesh'); r(24, 34, 24, 43, 'teesh')
    # jeans: hips and thighs fixed, lower legs and sneakers posed
    r(10, 44, 25, 47, 'jeans'); r(10, 44, 25, 44, 'waist')
    r(9, 48, 16, 49, 'jeans'); r(19, 48, 26, 49, 'jeans')
    r(12, 46, 13, 46, 'jeanhi'); r(22, 46, 23, 46, 'jeanhi')
    p(11, 45, 'waist'); p(24, 45, 'waist')
    for (x0, x1, xs), (dx, lift) in zip(((9, 16, 8), (19, 26, 19)), LEGS[legs]):
        y1 = 54 - lift
        r(x0 + dx, 50, x1 + dx, y1, 'jeans'); r(x0 + dx - (1 if xs == 8 else 0), y1, x1 + dx + (1 if xs == 19 else 0), y1, 'jeans')
        r(x0 + dx + 1, 50, x0 + dx + 1, y1 - 1, 'jeansh'); r(x0 + dx + 4, 50, x0 + dx + 4, y1 - 2, 'jeanhi')
        r(x0 + dx, y1 - 1, x1 + dx, y1 - 1, 'jeansh')
        sx0, sx1, sy = xs + dx, xs + 8 + dx, 55 - lift
        r(sx0, sy, sx1, sy + 2, 'shoe'); r(sx0, sy + 2, sx1, sy + 2, 'shoesh'); r(sx0, sy + 3, sx1, sy + 3, 'sole')
        r(sx0 + 1, sy, sx0 + 3, sy, 'shoesh')
    (L, R), thumb = _arms_spec(arms)
    _arm(g, (9 + OX, 31), L, 'L')
    hx, hy = _arm(g, SHOULDER_R, R, 'R')
    if thumb:
        g.rect(hx, hy - 4, hx + 1, hy - 2, GP['skin'])
    return g


def _face(g, expr, gaze):
    def r(x0, y0, x1, y1, c): g.rect(x0 + OX, y0, x1 + OX, y1, GP[c] if c else None)
    def p(x, y, c): g.px(x + OX, y, GP[c] if c else None)
    gx, gy = gaze
    for ex in (11, 20):                              # lens interiors: x ex..ex+4, y 14..18
        if expr == 'happy':
            p(ex, 16, 'eye'); r(ex + 1, 15, ex + 2, 15, 'eye'); p(ex + 3, 16, 'eye')
            continue
        if expr == 'blink':
            r(ex, 16, ex + 3, 16, 'eye'); continue
        tall = expr in ('shock', 'wow')
        y0 = 14 + max(0, gy) if tall else 15 + gy
        r(ex, y0, ex + 3, y0 + (2 if tall else 1), 'white')
        px = ex + 1 + gx
        py = y0 + (1 if tall else 0)
        r(px, py, px + 1, py + 1, 'eye'); p(px, py, 'white')
    r(14, 22, 21, 24, 'skin')
    if expr in ('smile', 'blink'):
        p(14, 22, 'mouth'); p(21, 22, 'mouth'); r(15, 23, 20, 23, 'mouth')
    elif expr == 'talk':
        r(14, 22, 21, 22, 'mouth'); r(15, 23, 20, 23, 'inner'); r(16, 24, 19, 24, 'mouth')
    elif expr in ('grin', 'happy'):
        p(14, 22, 'mouth'); p(21, 22, 'mouth'); r(15, 22, 20, 22, 'white'); r(15, 23, 20, 23, 'inner'); r(16, 24, 19, 24, 'mouth')
    elif expr == 'shock':
        r(16, 22, 19, 22, 'mouth'); r(16, 24, 19, 24, 'mouth'); p(15, 23, 'mouth'); p(20, 23, 'mouth'); r(16, 23, 19, 23, 'inner')
    elif expr == 'wow':
        r(17, 22, 18, 22, 'mouth'); p(16, 23, 'mouth'); p(19, 23, 'mouth'); r(17, 23, 18, 23, 'inner'); r(17, 24, 18, 24, 'mouth')
    elif expr == 'think':
        r(17, 23, 20, 23, 'mouth'); p(21, 22, 'mouth')
        r(20, 12, 24, 12, 'skin'); r(20, 11, 24, 11, 'hair')            # one brow raised
    elif expr == 'smirk':
        r(15, 23, 20, 23, 'mouth'); p(21, 22, 'mouth')
    elif expr in ('sad', 'sadtalk'):
        r(15, 22, 20, 22, 'mouth'); p(14, 23, 'mouth'); p(21, 23, 'mouth')
        if expr == 'sadtalk': r(15, 23, 20, 23, 'inner')


@lru_cache(4096)
def guy(expr='smile', arms='down', legs='stand', gaze=(1, 0)):
    """RGBA 48x60 sprite. Cached per pose, so animate by switching between cached frames."""
    g = _body(arms, legs)
    g2 = Grid(W, H); g2.g = [row[:] for row in g.g]
    _face(g2, expr, gaze)
    return g2.image()
