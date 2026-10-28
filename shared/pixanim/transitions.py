"""Screen-space transitions between two rendered shots (RGB images of equal size).

e runs 0 -> 1 across the transition. Character-driven transitions pair one of these with a presenter
overlay (see presenter.Presenter.draw_screen) whose path carries the eye from shot a into shot b.
"""
import math
from PIL import Image, ImageDraw
from .motion import io, ic, oc
from .fx import speed_lines

NAVY = (26, 26, 46)


def whip(a, b, e, dx=1, dy=0, lines=True):
    """Camera whip-pans: a leaves toward -direction... b arrives from (dx, dy) side, with motion streaks."""
    w, h = a.size
    out = Image.new('RGB', (w, h))
    ox, oy = int(-dx * w * e), int(-dy * h * e)
    out.paste(a, (ox, oy)); out.paste(b, (ox + dx * w, oy + dy * h))
    if lines:
        speed_lines(out, math.sin(math.pi * e), 7, horizontal=bool(dx), w=w, h=h)
    return out


def _zoom(img, z, cx, cy):
    w, h = img.size
    return img.transform((w, h), Image.AFFINE, (1 / z, 0, cx - cx / z, 0, 1 / z, cy - cy / z), resample=Image.NEAREST)


def iris(a, b, e, cx, cy, za=3.0, zb=1.6):
    """Zoom-through: a pushes in toward (cx, cy) while a circle of b opens from that point (b settles from zb)."""
    w, h = a.size
    za_ = 1 + (za - 1) * ic(e)
    out = _zoom(a, za_, cx, cy)
    R = (math.hypot(max(cx, w - cx), max(cy, h - cy)) + 40) * io(min(1.0, e * 1.15))
    if R > 2:
        bb = _zoom(b, 1 + (zb - 1) * (1 - oc(e)), cx, cy)
        m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).ellipse((cx - R, cy - R, cx + R, cy + R), fill=255)
        out.paste(bb, (0, 0), m)
        if e < 0.95:
            ImageDraw.Draw(out).ellipse((cx - R, cy - R, cx + R, cy + R), outline=NAVY, width=14)
    return out


def push(a, b, e, dx=-1):
    """a is shoved sideways off-screen (e.g. by the presenter) revealing b underneath, which drifts in slightly."""
    w, h = a.size
    k = io(e)
    out = Image.new('RGB', (w, h))
    out.paste(b, (int(-dx * w * 0.12 * (1 - k)), 0))
    ax = int(dx * w * k)
    edge = ax + w if dx < 0 else ax
    sh = Image.linear_gradient('L').rotate(90 if dx < 0 else -90).resize((60, h))
    out.paste((0, 0, 0), (edge if dx < 0 else edge - 60, 0, (edge + 60) if dx < 0 else edge, h), sh.point(lambda v: v * 0.6))
    out.paste(a, (ax, 0))
    return out


def cut(a, b, e, at=0.5):
    return a if e < at else b
