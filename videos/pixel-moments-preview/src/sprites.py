"""Original hand-drawn sprites + procedural limbs for the pixel-moments preview."""
import math

# ---- dad, front view, holding umbrella in his right hand (viewer's left) ----
# H hair h hair-hi S skin s skin-shade G glasses L lens e eye B beard o mouth
# F fur collar f fur shade J jacket j jacket shade K jacket hi T shirt t shirt shade
# U belt P jeans p jeans shade X shoes x shoe hi
DAD_FRONT = [
    "........HHHHH.........",
    "......HHhhhHHHH.......",
    ".....HHhhHHHHHHH......",
    ".....HhHHHHHHHHHH.....",
    ".....HHHHHHHHHHHH.....",
    ".....HHSSSSSSSHHH.....",
    ".....HSSSSSSSSSSH.....",
    "....sGGGGGSGGGGGs.....",
    "....sGLeLGsGLeLGs.....",
    "....sSGGGSSSGGGSs.....",
    ".....SSSSSsSSSSSs.....",
    ".....SSSSSssSSSSs.....",
    ".....BSSSSSSSSSBs.....",
    "......BBSoooSBBs......",
    "......BBBBBBBBBB......",
    ".......sBBBBBBs.......",
    "........sSSSs.........",
    "....FFFFFsSsFFFF......",
    "..FFFFFFfTTtfFFFFF....",
    ".JFFFFFfTTTTtfFFFFFj..",
    "JJJFFFfTTTTTTtfFFFJjj.",
    "JJJJJJjTTTTTTtjJJJJjj.",
    "JKJJJJjTTTTTTtjJJJJjjj",
    "JKJJJJjTTTTTTtjJJJKjjj",
    "JKJJJJjTTTTTTtjJJJKjjj",
    "JKJJJJjTTTTTTtjJJJJjjj",
    "JKJJJJjTTTTTTtjJJJJjjj",
    "SSSsJJjTTTTTTtjJJJJjjj",
    "SSSsJJjTTTTTTtjJJJJjjj",
    "sSSsJJjTTTTTttjJJJJjjj",
    "JKJjJJjTTTTTttjJJJJjjj",
    ".JJjJJjTTTTTttjJJjJjjj",
    ".JJjJJjUUUUUUUjJJjJjj.",
    ".JJjJJjPPPPPPpjJJjjjj.",
    "..JjJJjPPPPPPpjJJJjjj.",
    "..JJJJjPPPPPPpjJJJjj..",
    "..jjjjjPPPpPPpjjjjjj..",
    ".......PPPp.PPpp......",
    ".......PPPp.PPpp......",
    ".......PPPp.PPpp......",
    ".......PPPp.PPpp......",
    ".......PPPp.PPpp......",
    ".......PPPp.PPpp......",
    ".......PPPp.PPpp......",
    ".......pPPp.PPpp......",
    ".......pPPp.PPpp......",
    "......XxXXX.XXxXX.....",
    ".....XXXXXX.XXXXXX....",
]
DAD_HAND = (1, 27)   # umbrella grip, sprite coords
DAD_HEAD_ROWS = 17   # rows that bob with breathing (head+collar)

# ---- side-view heads (facing right) ----
DAD_HEAD_SIDE = [
    "....HHHHH....",
    "..HHHhhHHHH..",
    ".HHhhHHHHHHH.",
    ".HHHHHHHHHSSS",
    ".HHHHHHSSSSSS",
    ".HHHHHGGGGGGS",
    ".HHHkkSSGLeLS",
    "..HHkkSSSGGGS",
    "..HSSSSSSSSSs",
    "..SSSSSSSSSSS",
    "..BSSSSSSSSs.",
    "..BBBBBBBBoo.",
    "...BBBBBBBB..",
    "....BBBBBs...",
    "....sSSs.....",
]
KID_HEAD_SIDE = [   # yellow raincoat hood
    "..yyyyy..",
    ".yyYyyyyy",
    "yyYyyHHyy",
    "yYyyHHSSy",
    "yYyyHSSSS",
    "yYyyHSSeS",
    "yyYySSSSS",
    ".yyyySSsk",
    "..yyyysS.",
]
KID_HEAD_BEACH = [  # messy hair, no hood
    "..HhHHH..",
    ".HhhHHHHH",
    "HHhHHHHHH",
    "HHHHHHSSH",
    "HHHHSSSSS",
    "HHHkSSSeS",
    ".HHSSSSSS",
    "..SSSSSsk",
    "...ssSS..",
]

# torsos, side view (facing right). Rows top->bottom, x0 = back edge.
DAD_TORSO_SIDE = [
    "..FFFFff..",
    ".FFFFFfJJ.",
    "jJJJJJJJTT",
    "jJJJJJJJTT",
    "jJJJJJJKTT",
    "jJJJJJJKTt",
    "jJJJJJJJTt",
    "jJJJJJJJTt",
    "jJJJJJJJtt",
    "jjJJJJJJtt",
    "jjJJJJJJJt",
    "jjJJJJJJJJ",
    "jjjJJJJJJJ",
    ".jjjjjjjj.",
]
DAD_SHIRT_TORSO = [  # beach: open linen shirt over tee
    "..TTTTtt..",
    ".TTTTTtRR.",
    "tTTTTTTRRS",
    "tTTTTTTRRS",
    "tTTTTTTRRR",
    "tTTTTTTTRR",
    "tTTTTTTTRR",
    "tTTTTTTTRR",
    "ttTTTTTTRR",
    "ttTTTTTTTR",
    "ttTTTTTTTT",
    "tPPPPPPPPP",
    "pPPPPPPPPP",
    "pPPPPPPPPP",
]
KID_TORSO_SIDE = [
    ".yyyyy.",
    "yyyyyYY",
    "yyyyyyY",
    "YyyyyyY",
    "YyyyyyY",
    "YyyyyyY",
    "YYyyyyY",
    "YYYYYYY",
]
KID_TORSO_BEACH = [
    ".TTTTT.",
    "TTTTTTT",
    "TTWTTTT",
    "tTTWTTT",
    "tTTTWTT",
    "tTTTTTT",
    "PPPPPPP",
    "pPPPPPP",
]

# ---- procedural side-view person ----
SPEC = {
    'dad': dict(hip=21, thigh=9, shin=9, th=3, upper=9, fore=8, ath=2, torso=DAD_TORSO_SIDE,
                head=DAD_HEAD_SIDE, neck=(5, 13), head_dx=-1, foot=4),
    'kid': dict(hip=12, thigh=5, shin=5, th=2, upper=5, fore=4, ath=2, torso=KID_TORSO_SIDE,
                head=KID_HEAD_SIDE, neck=(3, 8), head_dx=-1, foot=3),
}


def _pt(x, y, ang, ln):  # angle from straight down, + = forward (right)
    return x + math.sin(ang) * ln, y + math.cos(ang) * ln


def seg(c, x0, y0, x1, y1, th, col, hi=None):
    n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
    for i in range(n + 1):
        t = i / n; x = x0 + (x1 - x0) * t; y = y0 + (y1 - y0) * t
        c.rect(round(x - th / 2), round(y - th / 2), th, th, col)
        if hi is not None: c.px(round(x + th / 2 - 1), round(y - th / 2), hi)


def person(c, x, feet, pal, kind='dad', phase=0.0, gait='walk', flip=False, hold=None, spec=None):
    """Draw side-view character. x = hip x, feet = ground y. Returns front-hand position.
    hold: (hx, hy) world point the *front* hand reaches to (hand-holding)."""
    sp = dict(SPEC[kind]); sp.update(spec or {})
    w = phase * 2 * math.pi
    run = gait == 'run'; stand = gait == 'stand'
    A = 0 if stand else (.75 if run else .42)
    Bk = 1.4 if run else .9
    bob = 0 if stand else (-(abs(math.cos(w)) > .55) * (2 if run else 1))
    lean = .18 if run else 0
    hipy = feet - sp['hip'] + bob
    s = -1 if flip else 1
    P = lambda col: pal[col] if isinstance(col, str) and len(col) == 1 else col

    def leg(off, near):
        th = A * math.sin(w + off)
        sh = th - Bk * max(0, math.cos(w + off)) * (A > 0)
        kx, ky = _pt(x, hipy, s * th, sp['thigh'])
        fx, fy = _pt(kx, ky, s * sh, sp['shin'])
        fy = min(fy, feet - 1)
        g = lambda k, d: pal.get(k + ('' if near else '2'), pal[d if near else d.lower()])
        sc = pal['X'] if near else pal['x']
        seg(c, x, hipy, kx, ky, sp['th'], g('thigh', 'P'))
        seg(c, kx, ky, fx, fy, sp['th'] - (sp['th'] > 2), g('shin', 'P'))
        c.rect(round(fx - 1 if s > 0 else fx - sp['foot'] + 2), round(fy), sp['foot'], 2 if kind == 'dad' else 1, sc)

    tor = sp['torso']; tw, thh = len(tor[0]), len(tor)
    shx = x + s * lean * 6; shy = hipy - thh + 3

    def arm(off, near, target=None):
        a = -A * .9 * math.sin(w + off); fa = a + (1.3 if run else .25)
        ex, ey = _pt(shx, shy + 1, s * a, sp['upper'])
        if target:
            hx, hy = target
            d = math.hypot(hx - shx, hy - shy); L = sp['upper'] + sp['fore']
            if d < L:  # bend elbow outward/back
                mx, my = (shx + hx) / 2, (shy + hy) / 2
                k = math.sqrt(max(0, (L / 2) ** 2 - (d / 2) ** 2))
                ex, ey = mx - s * k * .3, my + k * .9
            else:
                ex, ey = shx + (hx - shx) * sp['upper'] / L, shy + (hy - shy) * sp['upper'] / L
        else:
            hx, hy = _pt(ex, ey, s * fa, sp['fore'])
        g = lambda k: pal.get(k + ('' if near else '2'), pal['J' if near else 'j'])
        seg(c, shx, shy + 1, ex, ey, sp['ath'] + 1, g('upper'))
        seg(c, ex, ey, hx, hy, sp['ath'], g('fore'))
        c.rect(round(hx - 1), round(hy - 1), 2, 2, pal['S'] if near else pal['s'])
        return hx, hy

    arm(math.pi, False, hold if (hold and kind == 'kid') else None)
    leg(math.pi, False)
    # torso
    x0 = round(shx - tw / 2) if s > 0 else round(shx - tw / 2)
    y0 = round(shy - 1)
    c.spr(x0, y0, tor, pal, flip=flip)
    leg(0, True)
    hd = sp['head']; nx, ny = sp['neck']
    hx0 = round(shx + s * sp['head_dx'] - (nx if s > 0 else len(hd[0]) - nx))
    hy0 = round(shy - ny + 1)
    c.spr(hx0, hy0, hd, pal, flip=flip)
    return arm(0, True, hold if (hold and kind == 'dad') else None)
