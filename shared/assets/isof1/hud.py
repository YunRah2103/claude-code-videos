"""Full-res (1080x1920) HUD for the isometric F1 look, matching videos/f1-aero v3:
lap board (top-left), mini track map (top-right), callout pills, the big headline (white, dark outline, one yellow
highlighted word), grip meter, drag arrow, and the Main Guy presenter standing in the lower-left (lip-synced).
Every text element goes through overlays.place(), so the TikTok safe-zone check (overlays.violations) sees it.
World -> screen: iso canvases are 216x384, upscaled x5 (SC); use scr(I.p(X, Y, Z)) for anchors.
"""
import math
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw
from episode import font
from assets import overlays as ov
from pixanim.guy import guy
from pixanim.fx import popin, popout
from . import race as R
from .engine import col, SC

YEL, CYAN, RED, GRN, WHITE, GREY = (255, 216, 74), (106, 230, 255), (255, 90, 72), (74, 222, 128), (255, 255, 255), (200, 204, 216)
INK = (12, 14, 22)
CHIP = {'blue': '#2a5ad8', 'red': '#d8302a', 'orange': '#ff8a1a', 'green': '#1e8a5a', 'pink': '#f05aa8', 'silver': '#b8c0cc'}


def scr(p): return (p[0] * SC, p[1] * SC)


def upscale(a):
    """216x384 float canvas -> 1080x1920 RGB PIL image, nearest neighbour (crisp pixel blocks)."""
    a = np.clip(a, 0, 255).astype(np.uint8)
    return Image.fromarray(np.repeat(np.repeat(a, SC, 0), SC, 1))


# ------------------------------------------------------------------ headline + pills
@lru_cache(None)
def headline_img(lines, sz=104):
    """lines: tuple of lines, each a tuple of (text, highlighted?) runs. White text, dark outline, yellow highlight."""
    f = font(sz); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1))); st = max(8, sz // 10)
    widths = [sum(d0.textlength(tx, font=f) for tx, _ in ln) for ln in lines]
    w, h = int(max(widths) + 4 * st), int(len(lines) * sz * 1.08 + 3 * st)
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        x = (w - widths[i]) / 2; y = st + i * sz * 1.08
        for tx, hi in ln:
            d.text((x + 4, y + 6), tx, font=f, fill=(0, 0, 0, 120), stroke_width=st, stroke_fill=(0, 0, 0, 120))
            d.text((x, y), tx, font=f, fill=YEL if hi else WHITE, stroke_width=st, stroke_fill=(10, 10, 18))
            x += d0.textlength(tx, font=f)
    return img


def headline(cv, t, t0, t1, lines, y=330, sz=104, maxw=720):
    """Pops in at t0 (already settled if t0 < 0), wobbles gently, pops out at t1."""
    if not (t0 <= t < t1 + 0.2): return
    img = headline_img(lines, sz)
    u = max(0.0, t - t0)
    k = (1 + 0.12 * math.exp(-u * 9) * math.cos(u * 22)) * popin(t, t0, 0.18) * popout(t, t1, 0.2)
    k *= min(1, maxw / img.width)
    ov.place(cv, img, ov.SAFE_CX, y, k, -1.5 + 1.2 * math.sin(t * 3), 'headline')


@lru_cache(None)
def pill_img(txt, colr=YEL, sz=46):
    f = font(sz); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1))); tw = d0.textlength(txt, font=f)
    w, h = int(tw + 64), int(sz * 1.6)
    img = Image.new('RGBA', (w + 8, h + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((6, 8, w + 6, h + 8), h // 2, fill=(0, 0, 0, 110))
    d.rounded_rectangle((0, 0, w, h), h // 2, fill=INK + (225,), outline=colr, width=6)
    d.text((w / 2, h / 2 + 2), txt, font=f, fill=colr, anchor='mm')
    return img


def pill(cv, t, t0, t1, txt, x, y, colr=YEL, sz=46, rot=0.0):
    """Callout pill, e.g. REAR WING / GRIP / STRAIGHT MODE: LOW DRAG. Clamped into the text safe zone."""
    if not (t0 <= t < t1 + 0.2): return
    img = pill_img(txt, colr, sz)
    x, y = ov.clamp_to_safe(x, y, img.width * 1.15 + 20, img.height * 1.15 + 20)   # room for the pop-in overshoot
    ov.place(cv, img, x, y, popin(t, t0, 0.22) * popout(t, t1, 0.16), rot + 0.8 * math.sin(t * 3 + x), 'pill ' + txt)


# ------------------------------------------------------------------ race HUD: lap board + mini track map
def board(cv, tau, alpha=1.0, lap='LAP 12/57', x=44, y=560):
    """Lap counter + running order (team colour chips, no logos)."""
    if alpha <= 0.01: return
    order = R.standings(tau); A = int(225 * alpha); TA = int(255 * alpha)
    img = Image.new('RGBA', (290, 64 + 50 * len(order)), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, img.width - 1, img.height - 1), 24, fill=INK + (A,))
    fs = font(34); d.text((24, 32), lap, font=fs, fill=YEL + (TA,), anchor='lm')
    for i, (code, liv) in enumerate(order):
        yy = 86 + i * 50
        d.text((24, yy), str(i + 1), font=fs, fill=GREY + (TA,), anchor='lm')
        d.rounded_rectangle((62, yy - 17, 74, yy + 17), 4, fill=tuple(int(v) for v in col(CHIP[liv])) + (TA,))
        d.text((90, yy), code, font=fs, fill=(YEL if code == 'BLU' else WHITE) + (TA,), anchor='lm')
    ov.place(cv, img, x + img.width / 2, y + img.height / 2, 1.0, 0, 'board')


_MAP = {}


def track_map(cv, tau, alpha=1.0, cx=938, cy=300, size=190):
    """Mini iso map of the whole circuit (top-right) with live car dots; no text."""
    if alpha <= 0.01: return
    if size not in _MAP:
        P = R.PTS; mn, mx = P.min(0), P.max(0); k = size / (mx - mn).max()
        iso = lambda X, Y: (((X - mn[0]) - (Y - mn[1])) * k * .7, ((X - mn[0]) + (Y - mn[1])) * k * .35)
        pts = [iso(X, Y) for X, Y in P[::4]] + [iso(*P[0])]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        ox, oy = -min(xs) + 30, -min(ys) + 30
        _MAP[size] = (iso, [(x + ox, y + oy) for x, y in pts], (ox, oy), (int(max(xs) - min(xs) + 60), int(max(ys) - min(ys) + 60)))
    iso, pts, (ox, oy), (w, h) = _MAP[size]
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 24, fill=INK + (int(215 * alpha),))
    d.line(pts, fill=(255, 255, 255, int(255 * alpha)), width=9, joint='curve')
    for c in R.cars_at(tau):
        x, y = iso(c['X'], c['Y']); x += ox; y += oy; r = 14 if c['i'] == 0 else 9
        d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(int(v) for v in col(CHIP[R.TEAMS[c['i']][1]])) + (int(255 * alpha),),
                  outline=(255, 255, 255, int(255 * alpha)), width=3)
    cv.paste(img, (int(cx - w / 2), int(cy - h / 2)), img)


# ------------------------------------------------------------------ meters and arrows
def meter(cv, frac, label='GRIP', colr=GRN, x=830, y0=640, y1=1040, w=84):
    frac = min(1.0, max(0.0, frac))
    ov_ = Image.new('RGBA', cv.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov_)
    d.rounded_rectangle((x - w / 2 - 14, y0 - 14, x + w / 2 + 14, y1 + 14), 30, fill=INK + (215,))
    hh = (y1 - y0) * frac
    if hh > 4: d.rounded_rectangle((x - w / 2, y1 - hh, x + w / 2, y1), 18, fill=colr)
    cv.paste(ov_, (0, 0), ov_)
    pill(cv, 1, 0, 9, label, x, y1 + 80, colr, 40)


def drag_arrow(cv, a, b, label='DRAG', colr=RED, k=1.0):
    """Thick arrow from a to b (screen px), label above its middle."""
    if k <= 0.01: return
    xa, ya = a; xb, yb = a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k
    d = ImageDraw.Draw(cv); ang = math.atan2(yb - ya, xb - xa)
    d.line((xa, ya, xb, yb), fill=(10, 10, 18), width=40); d.line((xa, ya, xb, yb), fill=colr, width=26)
    tip = [(xb + 46 * math.cos(ang), yb + 46 * math.sin(ang)), (xb + 60 * math.cos(ang + 2.3), yb + 60 * math.sin(ang + 2.3)),
           (xb + 60 * math.cos(ang - 2.3), yb + 60 * math.sin(ang - 2.3))]
    d.polygon(tip, fill=colr, outline=(10, 10, 18), width=5)
    if label: pill(cv, 1, 0, 9, label, (xa + xb) / 2, (ya + yb) / 2 - 90, colr, 50)


# ------------------------------------------------------------------ presenter (lower-left, 10x pixel sprite)
_G = {}


def presenter(cv, t, words, arms='talkR', expr=None, x=-40, slide_t=None, gaze=(1, 0)):
    """Main Guy, 480x600 px, feet on the bottom edge, lower-left. Mouth flaps while a word is being spoken."""
    talking = any(w['s'] <= t < w['e'] for w in words)
    e = expr or (('talk' if int(t * 11) % 2 == 0 else 'smile') if talking else ('happy' if (t % 3.1) < .12 else 'smile'))
    if expr == 'shock' and talking: e = 'wow' if int(t * 11) % 2 == 0 else 'shock'
    key = (e, arms if isinstance(arms, str) else tuple(arms), gaze)
    if key not in _G:
        g = guy(e, arms, 'stand', gaze)
        _G[key] = g.resize((g.width * 10, g.height * 10), Image.NEAREST)
    g = _G[key]
    bob = 10 if (not talking and (t * 1.6) % 1 < .5) else 0
    if slide_t is not None: x += int(-520 * (1 - min(1, max(0, (t - slide_t) / 0.35)) ** 0.5))
    sh = Image.new('RGBA', (360, 70), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((0, 0, 359, 69), fill=(0, 0, 0, 110))
    cv.paste(sh, (x + 70, 1920 - 80), sh)
    cv.paste(g, (x, 1920 - g.height + 28 + bob), g)
