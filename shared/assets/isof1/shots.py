"""Shot builders for the f1-downforce series (and any isometric F1 explainer). Each returns (small RGB array, Iso, info).
Arrays are 216x384 (upscale with hud.upscale); anchors come from Iso.p(...) * SC."""
import math
import numpy as np
from .engine import grade, ease, col
from . import car as CAR, scenes as S, race as R


def g_lab(a): return grade(a, (.92, 1.0, 1.08), (1.0, 1.0, 1.02), .4, .45)
def g_gold(a): return grade(a, (.95, .95, 1.05), (1.06, 1.0, .92), .38, .35)


def race(tau, k=1.7):
    """Broadcast follow-cam on the hero (blue) car in the 6-car race."""
    c, I, cars = R.view(tau, k=k)
    return g_gold(c.a), I, cars


def lab_car(t, cam=(74, 159), k=4.0, Z=0.0, hi=(), flap=0.0, squash=0.0, mode=None, posts=False, smoke='#e6f8ff', speed=34):
    """Dark-blue wind-tunnel lab, cyan turntable ring, car facing +X, optional smoke streamlines."""
    c, I = S.lab(t, cam, k)
    if mode: S.smoke(I, t, Z=Z if mode == 'under' else 0, mode=mode, when='far', speed=speed)
    if posts: S.lift_posts(I, Z)
    CAR.f1(I, 0, 0, '+x', t, Z=Z, hi=hi, flap=flap, squash=squash, spin=0 if mode is None else 6)
    if mode: S.smoke(I, t, Z=Z if mode == 'under' else 0, mode=mode, cl=smoke, speed=speed)
    return c, I


def downforce(t, t_hit, n=5):
    """Lab: red downforce arrows slam down onto the car at t_hit, the car squats, cyan ring glows."""
    lt = t - t_hit
    c, I = lab_car(t, squash=.7 * ease(lt / .2) if lt > 0 else 0, mode='over', speed=30)
    for i, (X, Y) in enumerate(((6, 3), (6, 10), (15, 6.5), (23, 3.5), (23, 9.5))[:n]):
        u = ease((lt + .3 - i * .05) / .3)
        S.arrow3d(I, X, Y, 6.5 + (1 - u) * 22 + (.6 * math.sin(t * 6 + i) if lt > .3 else 0), 7)
    if 0 < lt < 0.6:
        c.a[:] = np.roll(c.a, int(3 * math.sin(lt * 70) * (0.6 - lt)), 0)
        I.glow(15, 6.5, 0, 40, '#ffd84a', .25 * (1 - lt / .6), 14)
    return g_lab(c.a), I


def straight_car(t, speed=150, cam=(74, 159), k=4.0, flap=0.0, hi=(), squash=0.0):
    c, I = S.straight(t, speed=speed, cam=cam, k=k)
    CAR.f1(I, 0, 0, '+x', t, flap=flap, hi=hi, squash=squash, spin=22)
    return g_gold(c.a), I


def ceiling_split(t, speed=220):
    """Split frame: top half = the same straight flipped (car driving on the ceiling), bottom half = the road."""
    a, I = straight_car(t, speed, cam=(74, 255), k=3.4)
    b, _ = straight_car(t + .37, speed, cam=(74, 255), k=3.4)
    out = a.copy(); out[:192] = b[::-1][:192]
    out[188:196] = col('#0c0e16'); out[190:194] = col('#6ae6ff')
    return out, I


def drag(t, wake=True):
    """Lab with turbulent wake smoke behind the car (drag)."""
    c, I = lab_car(t, mode='wake' if wake else 'over', speed=40)
    return g_lab(c.a), I


def corner(lt, ghost=True, k=1.4):
    """Real circuit corner: the no-aero ghost runs wide into the gravel; the aero car turns in."""
    c, I, (pg, pa), dust = R.corner_view(lt, k=k, ghost=ghost)
    return g_gold(c.a), I, (pg, pa), dust


def speed_lines(a, t, n=40, speed=2.8, seed=3, colr=(235, 245, 255), alpha=0.75, dx=-2.0, dy=-1.0, ln=26):
    """Pixel speed streaks streaming the way the scenery moves (iso -X = up-left on screen). In place on a 216x384 array."""
    h, w = a.shape[:2]; c = np.array(colr, np.float32); norm = math.hypot(dx, dy); ux, uy = dx / norm, dy / norm
    for i in range(n):
        r1 = ((i * 73856093 + seed * 19349663) % 997) / 997; r2 = ((i * 83492791 + seed * 2654435761) % 991) / 991
        ph = (t * speed * (0.7 + 0.6 * r2) + r1) % 1
        x0 = (r1 * 1.7 + 0.3) * w - ux * ph * (w + h) * 0.9; y0 = (r2 * 1.2 - 0.1) * h - uy * ph * (w + h) * 0.9
        L = ln * (0.6 + 0.8 * r2)
        for j in range(int(L)):
            x, y = int(x0 + ux * j), int(y0 + uy * j)
            if 0 <= x < w - 1 and 0 <= y < h - 1:
                k = alpha * (1 - j / L)
                a[y:y + 2, x:x + 2] = a[y:y + 2, x:x + 2] * (1 - k) + c * k      # 2 px thick
    return a
