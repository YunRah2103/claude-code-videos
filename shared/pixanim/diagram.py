"""Diagram graphics that attach to world objects: labels with growing leader lines, tracking arrows, glow arcs."""
import math
from PIL import ImageDraw
from .fx import blit, big, popin, NAVY
from .motion import oc, prog, ob, ic


def label(cv, t, t0, text, anchor, at, body='#ffffff', ink='#1a1a2e', shade='#d6d9e2', s=6, t1=None, wob=True):
    """Leader line grows from the object (anchor) to the label position (at), then the badge pops in.
    anchor/at may be (x, y) tuples or callables of t, so the label tracks moving parts."""
    if t < t0 or (t1 is not None and t > t1 + 0.2): return
    out = 1.0 if t1 is None else 1 - ic(prog(t, t1, 0.2))
    ax, ay = anchor(t) if callable(anchor) else anchor
    bx, by = at(t) if callable(at) else at
    g = oc(prog(t, t0, 0.18)) * out
    d = ImageDraw.Draw(cv)
    ex, ey = ax + (bx - ax) * g, ay + (by - ay) * g
    d.line((ax, ay, ex, ey), fill=NAVY, width=14); d.line((ax, ay, ex, ey), fill=(240, 242, 248), width=6)
    pr = 14 + 4 * math.sin(t * 9)
    d.ellipse((ax - pr, ay - pr, ax + pr, ay + pr), fill=(240, 242, 248), outline=NAVY, width=5)
    k = popin(t, t0 + 0.14, 0.26) * out
    rot = 2.5 * math.sin(t * 3) if wob else 0
    blit(cv, big('badge', text, body, ink, shade, s=s), bx, by, k, k, rot, anchor='center')


def arrow_to(cv, t, t0, target, angle=90, dist=150, s=8, t1=None, col_img=None):
    """Pixel arrow that points at a (moving) target from `angle` (deg, 90 = from above) and bobs toward it."""
    if t < t0 or (t1 is not None and t > t1): return
    tx, ty = target(t) if callable(target) else target
    a = math.radians(angle)
    bob = 18 * math.sin((t - t0) * 9)
    k = popin(t, t0, 0.25)
    x, y = tx + math.cos(a) * (dist + bob) * -1, ty - math.sin(a) * (dist + bob)
    img = col_img or big('arrow', s=s)
    blit(cv, img, x, y, k, k, angle - 90, anchor='center')


def glow_arc(cv, t, t0, cx, cy, R, a0, a1, col=(60, 200, 90), k=1.0):
    """Coloured band on a gauge bezel showing a range (angles in maths degrees, CCW)."""
    if t < t0: return
    p = oc(prog(t, t0, 0.35)) * k
    if p <= 0.01: return
    d = ImageDraw.Draw(cv)
    s0, s1 = 360 - a0, 360 - a0 + (a0 - a1) * p
    d.arc((cx - R, cy - R, cx + R, cy + R), s0, s1, fill=NAVY, width=30)
    d.arc((cx - R + 6, cy - R + 6, cx + R - 6, cy + R - 6), s0, s1, fill=col, width=18)
