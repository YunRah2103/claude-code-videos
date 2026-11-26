"""car_evolution — "How the car was made": ONE car on a glowing studio turntable gains one real invention per stage.
Benz 1886 -> hand crank -> 1912 Cadillac starter -> Ford Model T + assembly line -> 1959 Volvo three-point belt ->
1977 Oldsmobile microprocessor -> today's Tesla, code vs Boeing 737, $2,000 Acceleration Boost.
Oddity (never mentioned): a llama in sunglasses gliding past on a hoverboard in the background.
python car.py sheet out.png [t...] | still T out.png | check | meta out.json | video voice.wav music.wav out.mp4 [t0 t1]"""
import math, sys
import _lib  # noqa: F401
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw
from geo import (P, cat, quad, box, bbox, cb, lathe, cyl, superellipsoid, sphere, capsule, tube, tex, word_tex, rgb, Cam,
                 MATTE, PAINT, GLASS, CHROME, SATIN, RUBBER, GLOW, SCREEN, CLOTH, T_DISC)
from render3d import render
import engine3d as E
import props3d as PR
import cars3d as C
from yub import yub
import world as W
from world import ease, ease3, eout, ein, back, seg, lerp, mix, ACC

NAME = "car"; MAXDUR = 64.2
XF = 0.2                                     # cross-dissolve length at soft cuts (s)
def cam_e(u): return 0.4 * min(max(u, 0.0), 1.0) + 0.6 * ease3(u)      # camera never parks: no dead stop at cuts

class Video(E.Video):
    def _shot(s, i, t):
        S = s.m.SHOTS; t0 = S[i][0]; t1 = S[i + 1][0] if i + 1 < len(S) else s.dur
        return S[i][1]((t - t0) / (t1 - t0), t, t - t0)
    def _img(s, i, t):
        d = s._shot(i, t); mb = d.get("mb", 0)
        def one(dd): return render(dd["scene"], dd["cam"], dd.get("env") or s.m.ENV, glow=dd.get("glow", ()), sprites=dd.get("sprites", ()),
                                   shadow_center=dd.get("center")).astype(np.float32)
        if not mb: return one(d)
        acc = one(d)
        for k in range(1, mb + 1):                                  # motion blur: extra sub-frames inside the shutter
            acc += one(s._shot(i, t - k / (FPS * (mb + 1))))
        return acc / (mb + 1)
    def render_t(s, t):
        i, u, dt = s.shot_at(t)
        img = s._img(i, t)
        hard = getattr(s.m.SHOTS[i][1], "hard", False)
        if i > 0 and dt < XF and not hard:
            a = ease3(dt / XF); img = s._img(i - 1, t) * (1 - a) + img * a
        return np.clip(img + 0.5, 0, 255).astype(np.uint8)

FPS = E.FPS
V = Video(sys.modules[__name__]); ws = V.ws; DUR = V.dur
HOOK = "THE FIRST CAR HAD LESS THAN 1 HORSEPOWER"
ACCENT = (255, 190, 60)
HOT = {"1886", "benz", "0.75", "horse", "tiller", "10", "hand-cranked", "dangerously", "1912", "cadillac", "starter", "click", "done",
       "$850", "assembly", "12.5", "93", "15", "$260", "budget", "1959", "volvo", "three-point", "seatbelt", "free", "together", "1977",
       "oldsmobile", "microprocessor", "code", "millions", "737", "phone", "software", "2019", "tesla", "$2,000", "paywall", "upgrade"}
MUSIC_UNDER_DB = 4.0
ENV = W.env()
ODDITY = "a llama in sunglasses gliding across the background on a glowing hoverboard (hook, 1912, assembly line, 1977, finale)"
ONSCREEN = []

def D(scene, cam, acc=(90, 200, 255), glow=(), sprites=(), center=(0, 0, 0), mb=0, env=None, beams=True, t=0.0, dust=True):
    g = list(glow) + (W.beams(acc) if beams else [])
    sp = list(sprites) + (W.dust(t) if dust else [])
    return dict(scene=scene, cam=cam, env=env or W.env(acc), glow=g, sprites=sp, center=center, mb=mb)

def stage(t, st, v=0.0, tt=True):
    acc = ACC[min(st, 5)]
    s = W.floor(t, v, acc)
    if tt: s += W.turntable(acc)
    return s, acc

def drive(expr="smile", t=0.0, **kw):
    kw.setdefault("la", (55, 4, 40)); kw.setdefault("ra", (55, 4, 40))
    return W.seat_yub(yub(expr, sit=True, bob=kw.pop("bob", 0.008 * math.sin(t * 9)), **kw))

def orbit(a_deg, r, h, tgt=(0.1, 0.8, 0), fov=40, **kw):
    a = math.radians(a_deg)
    return Cam((tgt[0] + r * math.cos(a), h, tgt[2] + r * math.sin(a)), tgt, fov, **kw)

def llama_at(t, t0, x0=-8.0, v=1.3, z=-7.5):
    x = x0 + v * (t - t0)
    if abs(x) > 12: return [], []
    l, sp = W.llama(t, x, z, 1 if v > 0 else -1)
    return [l], [sp]

# ---------------------------------------------------------------- 0 hook
def sh_hook(u, t, dt):
    """Hook: the tiny Benz tricycle on the turntable, Yub squeezed on top (sweating). A huge hologram of today's car
    scans in behind on 'became this'."""
    s, acc = stage(t, 0)
    y = drive("cringe" if t < 2.6 else "grin", t, sweat=True, la=(40, -6, 95), ra=(40, -6, 95), head=(-10 + 14 * ease(seg(t, 1.0, 2.6)), 0, 4))
    m, g, sp = W.car(0, t, -t * 40, driver=y)
    s.append(m)
    ll, lsp = llama_at(t, 0, -9, 1.6, -8.5)
    e = cam_e(u)
    cam = orbit(mix(64, 40, e), mix(5.4, 4.6, e), mix(1.25, 1.45, e), (0.0, mix(1.3, 1.4, e), 0), 44, aperture=0.05)
    return D(s + ll, cam, acc, g, sp + lsp, t=t)

def sh_tease(u, t, dt):
    """Hook 'Here's how it became this.': flash-forward - today's red Tesla rises through a cyan scan ring on its own
    turntable, low dramatic angle, headlights flaring."""
    s, acc = stage(t, 5)
    k = ease3(0.3 + 0.7 * seg(dt, 0.0, 0.5)); hy = 1.6 * k
    h = W.modern().rot("y", -12)
    h.keep(h.t.mean(1)[:, 1] < hy)
    s.append(h)
    ring = lathe([(2.75, 0.0), (2.85, 0.0)], 48, (90, 210, 255), GLOW).glow(3.0 * (1 - 0.7 * k)).sc(1, 1, 0.5).rot("y", -12).mv(0, hy, 0)
    e = cam_e(u)
    cam = Cam(lerp((6.2, 2.0, 7.4), (5.4, 1.85, 6.9), e), (0.2, 1.1, 0), 42, aperture=0.02)
    return D(s, cam, acc, [ring], [((2.2, 0.66, sg * 0.66), (230, 240, 255), 0.08, 1.2 * k) for sg in (1, -1)], t=t)

# ---------------------------------------------------------------- 1886
def sh_badge(u, t, dt):
    """Macro: light sweeps across the BENZ plaque on the wooden seat box, then the camera pulls back over the wire wheel."""
    s, acc = stage(t, 0)
    m, g, sp = W.car(0, t, 0, driver=drive("smile", t)); s.append(m)
    e = cam_e(u); xs = -0.95 + 0.9 * seg(u, 0.05, 0.6)
    g = g + [PR.glow_quad(0.08, 0.5, (255, 230, 170), 1.6).mv(xs, 0.74, 0.44)]
    cam = Cam(lerp((-0.35, 0.95, 1.4), (-0.05, 1.05, 2.0), e), lerp((-0.5, 0.76, 0.4), (-0.35, 0.78, 0.25), e), 36, aperture=mix(0.3, 0.14, e))
    return D(s, cam, acc, g, sp, (0, 0, 0), t=t, mb=1)

def sh_patent(u, t, dt):
    """'patents': a parchment PATENT 1886 document slams down on its stand beside the car, stamp + dust."""
    s, acc = stage(t, 0)
    m, g, sp = W.car(0, t, 0, driver=drive("proud" if t > ws(1, 3) + 0.3 else "smile", t, ra=(75, 10, 85) if t > ws(1, 3) + 0.5 else (55, 4, 40))); s.append(m)
    k = back(seg(t, ws(1, 3) - 0.35, ws(1, 3) + 0.05), 1.2)
    doc = _patent().copy().rot("x", -15).mv(1.1, mix(4.0, 1.12, k), 1.2)
    stand = cat([capsule((1.1, 0.0, 1.0), (1.1, 0.7, 1.15), 0.02, 6, (180, 150, 80), CHROME), cb(1.1, 0.02, 1.0, 0.4, 0.04, 0.3, (40, 40, 44), b=0.01)])
    s += [doc, stand]
    hit = seg(t, ws(1, 3) + 0.05, ws(1, 3) + 0.6)
    if 0 < hit < 1: g = g + [PR.rings(hit * 0.8, 3, 0.2, 0.25, 1.5, (255, 220, 150), 1.4 * (1 - hit)).rot("x", -15).mv(1.1, 1.12, 1.25)]
    e = cam_e(u)
    cam = orbit(mix(70, 52, e), 5.3, 1.6, (0.4, 1.35, 0.5), 44, aperture=0.04)
    return D(s, cam, acc, g, sp, t=t)
@lru_cache(None)
def _patent(): return W.paper([("PATENT", 66), ("1886", 64), ("Benz", 40), ("Patent-Motorwagen", 32)], 0.75, 0.98, ("BENZ", (180, 30, 30)))

def sh_three(u, t, dt):
    """'Three wheels': top 3/4, a glowing ring snaps around each wheel in turn."""
    s, acc = stage(t, 0)
    m, g, sp = W.car(0, t, -t * 30, driver=drive("smile", t)); s.append(m)
    for i, (x, y, z, R) in enumerate(((-0.55, 0.46, 0.66, 0.46), (-0.55, 0.46, -0.66, 0.46), (0.98, 0.3, 0.0, 0.3))):
        k = back(seg(t, ws(2, 0) + 0.12 * i, ws(2, 0) + 0.12 * i + 0.3))
        if k > 0:
            ring = lathe([(R + 0.05, -0.01), (R + 0.09, 0.0), (R + 0.05, 0.01)], 40, (255, 200, 90), GLOW).glow(2.6).sc(k).rot("x", 90).mv(x, y, z + (0.03 if z >= 0 else -0.03))
            g = g + [ring]
    e = cam_e(u)
    cam = orbit(mix(40, 28, e), 4.9, 3.1, (0.2, 0.95, 0), 44)
    return D(s, cam, acc, g, sp, t=t)

def sh_engine(u, t, dt):
    """Macro on the single-cylinder engine: brass rings, flywheel blur-spinning, heat glow pulsing with each stroke."""
    s, acc = stage(t, 0)
    m, g, sp = W.car(0, t, -t * 200, driver=drive("smile", t)); s.append(m)
    beat = 0.5 + 0.5 * math.sin(t * 22)
    g = g + [PR.glow_quad(0.5, 0.3, (255, 120, 40), 0.5 + 0.9 * beat).rot("y", 90).mv(-1.25, 0.72, 0.1),
             PR.rings(t, 3, 0.12, 0.12, 0.7, (255, 150, 60), 1.0).rot("y", -90).mv(-1.4, 0.72, 0.1)]
    e = cam_e(u)
    cam = Cam(lerp((-1.9, 1.15, 1.25), (-1.7, 1.0, 0.95), e), (-1.05, 0.66, 0.05), 38, aperture=0.32)
    return D(s, cam, acc, g, sp + [((-1.2, 0.72, 0.22), (255, 160, 80), 0.05, 0.8 * beat)], (-1, 0, 0), mb=1, t=t)

def sh_horse(u, t, dt):
    """'0.75 horsepower': a glowing hologram horse scans in beside the car - only the front three quarters of it.
    JOKE: on 'horse' the back-less horse slowly tips onto its missing rear. Yub stares."""
    s, acc = stage(t, 0)
    look = t > ws(2, 7)
    m, g, sp = W.car(0, t, 0, driver=drive("confused" if look else "smile", t, head=(-50 if look else 0, 0, 0), look="r" if look else "c")); s.append(m)
    k = ease3(seg(t, ws(2, 5) - 0.1, ws(2, 5) + 0.6))
    cut = -0.62 + 0.0                                                   # front 3/4 of the 1.85 m horse
    tip = ein(seg(t, ws(2, 11) - 0.2, ws(2, 12) + 0.5)) * 24
    h = W.horse((255, 196, 90), 0.34, cut).rot("z", tip, (cut, 0.06, 0)).sc(0.85)
    if k < 1: h.keep(h.t.mean(1)[:, 0] > 1.0 - 2.0 * k)
    h.sc(0.88).mv(1.55, 0, -1.3)
    edge = PR.glow_quad(0.6, 1.35, (255, 240, 200), 1.4 * k).rot("y", 90).mv(cut, 1.15, 0).rot("z", tip, (cut, 0.06, 0)).sc(0.85 * 0.88).mv(1.55, 0, -1.3)
    lab = W.neon("0.75 HP", 1.3, 0.42, (255, 200, 80), 2.6).mv(1.55, 2.2, -1.3)
    s.append(lab.sc(1) if k > 0.3 else None)
    e = cam_e(u)
    cam = Cam(lerp((1.5, 1.8, 7.6), (1.2, 1.75, 7.0), e), (0.6, 1.35, -0.4), 44, aperture=0.03)
    return D([q for q in s if q is not None], cam, acc, g + [h, edge], sp, (0, 0, 1), t=t)

# ---------------------------------------------------------------- tiller, 10 mph, tip-over
def sh_tiller(u, t, dt):
    """Macro: Yub's hands on the tiller, steering left-right like a boat; the floor grid streams past."""
    s, acc = stage(t, 0, v=4.5, tt=False)
    sw = 14 * math.sin(t * 3.2)
    m, g, sp = W.car(0, t, -t * 560, driver=drive("smile", t, la=(60, -2 + sw * 0.3, 30), ra=(60, -2 - sw * 0.3, 30), head=(sw * 0.6, 0, 0))); s.append(m)
    e = cam_e(u)
    cam = Cam(lerp((1.75, 1.75, 1.85), (1.5, 1.7, 1.55), e), (-0.2, 1.35, 0.0), 40, aperture=0.1)
    return D(s, cam, acc, g, sp + [PR_line for PR_line in []], (0, 0, 0), t=t)

def speedo(v, acc):
    ring = []
    for i in range(13):
        a = math.radians(210 - i * 20)
        ring.append(capsule((0.5 * math.cos(a), 0.5 * math.sin(a), 0), (0.58 * math.cos(a), 0.58 * math.sin(a), 0), 0.012, 4, acc))
    an = math.radians(210 - 240 * v / 12)
    needle = capsule((0, 0, 0.01), (0.46 * math.cos(an), 0.46 * math.sin(an), 0.01), 0.018, 6, (255, 80, 60))
    return cat(ring).glow(2.2), needle.glow(3.0)

def sh_speed(u, t, dt):
    """'Top speed? About 10 miles an hour': tracking shot alongside, hologram speedometer needle climbs to 10, speed lines."""
    s, acc = stage(t, 0, v=4.5, tt=False)
    m, g, sp = W.car(0, t, -t * 560, driver=drive("grin" if t > ws(3, 9) else "smile", t, head=(-20, 0, 0))); s.append(m)
    v = 10 * eout(seg(t, ws(3, 6), ws(3, 10)))
    r, n = speedo(v, (255, 200, 90))
    pos = (0.9, 1.68, 0.9)
    lab = W.neon(f"{int(round(v))} MPH", 0.9, 0.3, (255, 200, 90), 2.4, frame=False).mv(pos[0], pos[1] - 0.22, pos[2] + 0.02)
    g = g + [r.mv(*pos), n.mv(*pos), PR.speed_lines(t, 10, 2.4, (1.6, 0.8), (200, 230, 255), 0.6).mv(-2.2, 1.0, 0.6)]
    s.append(lab)
    e = cam_e(u)
    cam = Cam(lerp((1.6, 1.5, 4.8), (0.9, 1.6, 5.0), e), (0.4, 1.5, 0.2), 44, aperture=0.03)
    return D(s, cam, acc, g, sp, (0, 0, 0), t=t)

def sh_tip(u, t, dt):
    """JOKE 'Still too fast for me.': the tricycle swerves and slowly rolls onto its side, Yub panicking, dust puff."""
    s, acc = stage(t, 0, v=4.5 * (1 - ease(seg(t, ws(3, 13), ws(3, 17) + 0.3))), tt=False)
    k = ease3(seg(t, ws(3, 13) - 0.1, ws(3, 16)))
    y = drive("panic", t, sweat=True, la=(20, 70 + 30 * math.sin(t * 20), 40), ra=(20, 70 - 30 * math.sin(t * 20), 40), head=(10 * math.sin(t * 18), 0, 0))
    m, g, sp = W.car(0, t, -t * 400, driver=y)
    m.rot("y", -14 * ease(seg(t, ws(3, 12), ws(3, 14)))).rot("x", 80 * k, (0, 0, 0.66))
    s.append(m)
    hit = seg(t, ws(3, 16), ws(3, 16) + 0.6)
    if 0 < hit < 1:
        g = g + [PR.glow_quad(2.4, 0.8, (200, 200, 230), 0.35 * (1 - hit)).rot("x", -90).mv(0, 0.05, 1.3)]
        sp = sp + [((-0.4 + 0.3 * i, 0.15 + hit * 0.4, 1.4 + 0.1 * i), (220, 220, 240), 0.12 + 0.2 * hit, 0.6 * (1 - hit)) for i in range(4)]
    e = cam_e(u)
    cam = Cam(lerp((3.2, 1.9, 5.0), (2.9, 1.8, 4.7), e), (0.0, 0.95, 0.5), 46, aperture=0.03)
    return D(s, cam, acc, g, sp, (0, 0, 0), mb=1, t=t)

# ---------------------------------------------------------------- hand crank
def sh_upgrade1(u, t, dt):
    """'early cars had to be hand-cranked': a red scan plane sweeps the tricycle into a four-wheel brass-era car with a
    bonnet, radiator and a starting crank."""
    s, acc = stage(t, 1)
    y = drive("shock", t)
    a, _, _ = W.car(0, t, 0, driver=None); b, g, sp = W.car(1, t, 0, driver=None, crank_on=0)
    xs = mix(1.6, -1.5, ease3(seg(t, ws(4, 0) - 0.05, ws(4, 6))))
    s += [W.wipe(a, b, xs), y]
    sg, ssp = W.scan_fx(xs, acc, 1.9, 1.7, 1.0 if -1.45 < xs < 1.55 else 0, t)
    e = cam_e(u)
    cam = orbit(mix(25, 40, e), 5.2, 1.8, (0.2, 1.25, 0), 44)
    return D(s, cam, acc, g + sg, sp + ssp, t=t)

def _cranker(t, ang, expr="angry", spin=0.0, **kw):
    """Standing Yub at the front, bent over the crank handle."""
    hx = 1.22 + 0.24; hy = 0.56 + 0.17 * math.cos(math.radians(ang)); hz = 0.17 * math.sin(math.radians(ang))
    reach = 70 + 25 * (0.73 - hy) / 0.34
    y = yub(expr, lean=24, ra=(reach, 8, 20), la=(reach - 10, 14, 30), head=(0, 18, 0), **kw)
    return y.rot("y", -90 + spin).mv(1.98, 0, hz * 0.4)

def sh_cranking(u, t, dt):
    """Yub at the front, heaving the crank round and round (sweat)."""
    s, acc = stage(t, 1)
    ang = -((t - ws(4, 6)) * 520)
    m, g, sp = W.car(1, t, 0, driver=None, crank_on=ang); s += [m, _cranker(t, ang, "angry", sweat=True)]
    e = cam_e(u)
    cam = orbit(mix(84, 74, e), 4.4, 1.6, (1.35, 1.1, 0), 42, aperture=0.05)
    return D(s, cam, acc, g, sp, (1, 0, 0), t=t)

def sh_kick(u, t, dt):
    """JOKE 'Dangerously.': the crank kicks back and spins Yub around like a top, dizzy stars."""
    s, acc = stage(t, 1)
    k = eout(seg(t, ws(4, 7), ws(4, 7) + 0.9))
    ang = -150 + 900 * k
    spin = 720 * k
    stars = [((1.98 + 0.25 * math.cos(t * 9 + i * 2.1), 2.05, 0.25 * math.sin(t * 9 + i * 2.1)), (255, 230, 90), 0.04, 1.4) for i in range(3)] if k > 0.5 else []
    m, g, sp = W.car(1, t, 0, driver=None, crank_on=ang)
    yb = yub("panic" if k < 0.7 else "confused", la=(30, 80, 20), ra=(30, 80, 20), head=(0, -10, 12 * math.sin(t * 6)), sweat=True)
    yb.rot("y", -90 + spin).rot("z", 10 * math.sin(t * 7) * k, (0, 0, 0)).mv(2.0 + 0.3 * k, 0, 0)
    s += [m, yb]
    cam = orbit(76, 4.6, 1.6, (1.5, 1.15, 0), 44, aperture=0.04)
    return D(s, cam, acc, g, sp + stars, (1, 0, 0), mb=2, t=t)

# ---------------------------------------------------------------- 1912 starter
def sh_flyoff(u, t, dt):
    """'So in 1912': the hand crank pops off the nose and tumbles away into the dark, red light flaring."""
    s, acc = stage(t, 1)
    m, g, sp = W.car(1, t, 0, driver=drive("smug", t)); s.append(m)
    k = seg(t, ws(5, 0), ws(5, 0) + 1.0)
    cr = W.crank(k * 1400).rot("z", 360 * k * 1.3).mv(1.22 + 3.2 * k, 0.56 + 2.6 * k - 3.2 * k * k, 0.8 * k)
    s.append(cr)
    ll, lsp = llama_at(t, ws(5, 0), -6.5, 1.5, -7.0)
    e = cam_e(u)
    cam = orbit(mix(10, 25, e), 4.4, 1.3, (0.8, 0.9, 0), 44, aperture=0.03)
    return D(s + ll, cam, acc, g, sp + lsp, (0.5, 0, 0), mb=1, t=t)

def sh_crest(u, t, dt):
    """Macro: light sweep across the Cadillac crest on the brass radiator."""
    s, acc = stage(t, 1)
    m, g, sp = W.car(1, t, 0, driver=drive("smug", t)); s.append(m)
    zs = mix(-0.4, 0.4, ease3(u))
    g = g + [PR.glow_quad(0.06, 0.45, (255, 220, 180), 1.4).rot("y", 90).mv(1.23, 0.88, zs)]
    e = cam_e(u)
    cam = Cam(lerp((2.05, 0.95, 0.55), (1.95, 0.92, -0.35), e), (1.2, 0.88, 0.0), 34, aperture=0.4)
    return D(s, cam, acc, g, sp + [((1.23, 0.88, zs), (255, 230, 190), 0.05, 1.2)], (1, 0, 0), t=t)

def sh_starter(u, t, dt):
    """Macro mechanism: Kettering's electric starter motor slides in beside the engine, bolts lock, blue arcs crackle."""
    s, acc = stage(t, 1)
    m, g, sp = W.car(1, t, 0, driver=drive("smile", t)); s.append(m)
    k = back(seg(t, ws(5, 6), ws(5, 9) + 0.1), 0.8)
    st = W.starter(0.4 + 1.2 * seg(t, ws(5, 9), ws(5, 9) + 0.3)).mv(0.45, 0.6, 0.36 + 1.4 * (1 - k))
    s.append(st)
    if k >= 0.99:
        r = np.random.default_rng(int(t * 12))
        arcs = [tube([(0.5 + 0.08 * j, 0.6 + r.uniform(-0.09, 0.09), 0.36 + r.uniform(0.07, 0.11)) for j in range(4)], 0.006, 4, (120, 220, 255)).glow(4.0) for _ in range(2)]
        g = g + arcs
        sp = sp + [((0.6, 0.6, 0.45), (120, 210, 255), 0.09, 1.3)]
    e = cam_e(u)
    cam = Cam(lerp((0.3, 0.86, 1.45), (0.36, 0.8, 1.22), e), (0.62, 0.62, 0.36), 40, aperture=0.28)
    return D(s, cam, acc, g, sp, (0.5, 0, 0), t=t)

def sh_click(u, t, dt):
    """'Click. Done.': Yub presses the starter button, headlamps flare, engine rings pulse; 'Done.' smug thumbs-up."""
    s, acc = stage(t, 1)
    pressed = t > ws(5, 10)
    done = t > ws(5, 11) - 0.05
    if done: y = drive("smug", t, ra=(75, 10, 85), la=(55, 4, 40), head=(-25, 0, 0))
    else: y = drive("smile", t, ra=(62, 2, 20 if pressed else 30))
    m, g, sp = W.car(1, t, -max(0, t - ws(5, 10)) * 120, driver=y, starter_k=1.0)
    s.append(m)
    p = seg(t, ws(5, 10), ws(5, 10) + 0.8)
    btn = cyl(0.03, 0.03, 0.02, 12, (255, 60, 60), MATTE, e=1.5 + 2 * (p > 0)).rot("z", 90).mv(0.25, 1.06, 0.12)
    s.append(btn)
    if p > 0:
        g = g + [PR.rings(p * 1.4, 3, 0.1, 0.2, 1.2, (90, 200, 255), 1.6 * (1 - p)).rot("y", -90).mv(-1.4, 0.72, 0.1)]
        g = g + [C._glow_disc(1.23, 0.88, 0, 0.4, (255, 230, 180), 1.2 * (1 - p))]
    e = cam_e(u)
    cam = orbit(mix(48, 36, e), 2.9, 1.65, (0.0, 1.2, 0), 42, aperture=0.08)
    return D(s, cam, acc, g, sp, t=t)

# ---------------------------------------------------------------- Model T
def sh_modelT(u, t, dt):
    """'Then Ford's Model T launched at $850': blue scan sweeps the car into a black Model T (fenders, windscreen,
    steering wheel, wooden wheels, Ford oval); a $850 price hologram pops up."""
    s, acc = stage(t, 2)
    a, _, _ = W.car(1, t, 0, driver=None, starter_k=1.0); b, g, sp = W.car(2, t, 0, driver=None, lamps=0.8)
    xs = mix(1.6, -1.5, ease3(seg(t, ws(6, 0), ws(6, 5))))
    y = drive("grin", t)
    s += [W.wipe(a, b, xs), y]
    sg, ssp = W.scan_fx(xs, acc, 1.9, 1.7, 1.0 if -1.45 < xs < 1.55 else 0, t)
    k = back(seg(t, ws(6, 6) - 0.1, ws(6, 6) + 0.3))
    if k > 0: s.append(W.neon("$850", 0.9, 0.42, (90, 160, 255), 2.8).sc(k).mv(0.3, 2.1, 0))
    e = cam_e(u)
    cam = orbit(mix(50, 28, e), 5.4, 1.8, (0.2, 1.4, 0), 44, aperture=0.03)
    return D(s, cam, acc, g + sg, sp + ssp, t=t)

@lru_cache(None)
def _tproxy():
    """Cheap Model T for crowds."""
    k = BLACK = (20, 20, 24)
    wt = C._rim(12, (186, 128, 64), (26, 26, 28), style="solid")
    s = [bbox(-0.9, 0.52, -0.42, -0.12, 0.9, 0.42, BLACK, b=0.03, m=PAINT), bbox(0.3, 0.52, -0.3, 1.1, 0.98, 0.3, BLACK, b=0.06, m=PAINT),
         bbox(1.1, 0.46, -0.34, 1.2, 1.04, 0.34, (214, 168, 74), b=0.03, m=CHROME), bbox(-0.94, 0.9, -0.42, -0.82, 1.38, 0.42, (46, 30, 26), b=0.04),
         quad((0.3, 1.1, 0.39), (0.3, 1.1, -0.39), (0.245, 1.59, -0.39), (0.245, 1.59, 0.39), (150, 200, 255), e=0.07, m=GLOW),
         bbox(-0.12, 0.42, -0.74, 0.68, 0.46, 0.74, (30, 30, 34), b=0.012)]
    for x, R in ((-0.55, 0.47), (1.05, 0.38)):
        for sg in (-1, 1):
            s.append(cyl(R, R, 0.1, 18, (255, 255, 255), RUBBER, captex=wt).rot("x", 90 * sg).mv(x, R, sg * 0.6))
            s.append(bbox(x - R - 0.05, R * 2 + 0.0, sg * 0.54 - 0.1, x + R + 0.05, R * 2 + 0.05, sg * 0.54 + 0.1, BLACK, b=0.02, m=PAINT))
    return cat(s)

def conveyor(t, v, L=24):
    s = [bbox(-L / 2, 0.0, -1.1, L / 2, 0.22, 1.1, (40, 42, 50), b=0.04, m=SATIN)]
    off = (v * t) % 0.6
    s += [box(x, 0.221, -1.05, x + 0.05, 0.226, 1.05, (255, 170, 60), e=0.6) for x in np.arange(-L / 2 + off, L / 2, 0.6)]
    return cat(s)

def sh_line(u, t, dt):
    """'The moving assembly line': factory dark, the car multiplies down a moving conveyor - every copy has its own
    waving Yub (JOKE) - under a hologram clock: 12.5 HOURS spins down to 93 MIN."""
    acc = ACC[2]; v = 0.9
    s = W.floor(t, 0, acc) + [conveyor(t, v)]
    mult = ease3(seg(t, ws(7, 0), ws(7, 3)))
    cars_ = []
    for i in range(-3, 4):
        x = i * 3.0 * mult + v * (t - ws(7, 0))
        if i == 0:
            m, g0, sp0 = W.car(2, t, 0, driver=drive("grin", t, ra=(0, 150 + 18 * math.sin(t * 14), 30), wave="r"), lamps=0.6)
            cars_.append(m.mv(x, 0.22, 0))
        elif abs(x) < 11:
            p = _tproxy().copy().mv(x, 0.22, 0)
            yb = W.seat_yub(yub("grin", sit=True, ra=(0, 150 + 18 * math.sin(t * 14 + i), 30), wave="r", la=(55, 4, 40))).mv(x, 0.22, 0)
            cars_ += [p, yb]
    s += cars_
    # gantry arches with lamps
    for x in (-6, 0, 6):
        s += [cb(x, 2.4, -1.6, 0.16, 4.8, 0.16, (50, 52, 60), b=0.03), cb(x, 2.4, 1.6, 0.16, 4.8, 0.16, (50, 52, 60), b=0.03), cb(x, 4.8, 0, 0.18, 0.18, 3.4, (50, 52, 60), b=0.03)]
    glow = [PR.beam((x, 4.7, 0), (0, -1, 0), 4.6, 1.3, (255, 200, 140), 0.12) for x in (-6, 0, 6)]
    # clock hologram
    hrs = t < ws(7, 10) + 0.05
    clk = W.neon("12.5 HOURS" if hrs else "93 MIN", 1.9, 0.5, (255, 190, 80) if hrs else (90, 240, 160), 2.8).mv(0.6 * mult, 3.6, -0.6)
    ang = -((t - ws(7, 0)) * (60 if t < ws(7, 8) else 1400))
    face = cat([lathe([(0.55, 0), (0.6, 0)], 40, (255, 200, 120), GLOW).glow(2.0).rot("x", 90),
                capsule((0, 0, 0.02), (0.42 * math.sin(math.radians(ang)), 0.42 * math.cos(math.radians(ang)), 0.02), 0.025, 6, (255, 255, 255)).glow(3),
                capsule((0, 0, 0.02), (0.28 * math.sin(math.radians(ang / 12)), 0.28 * math.cos(math.radians(ang / 12)), 0.02), 0.03, 6, (255, 255, 255)).glow(3)]).mv(0.6 * mult, 2.55, -0.6)
    s.append(clk)
    ll, lsp = llama_at(t, ws(7, 0), 7, -1.4, -6.0)
    e = cam_e(u)
    cam = Cam(lerp((3.2, 2.1, 6.6), (5.0, 2.4, 6.8), e), lerp((0.4, 1.6, 0), (1.2, 1.9, -0.3), e), 50, aperture=0.02)
    return D(s + ll, cam, acc, glow + [face], lsp + [((x, 4.6, 0), (255, 210, 160), 0.2, 1.0) for x in (-6, 0, 6)], (0, 0, 0), beams=False, t=t,
             env=W.env(acc, fog=(10, 40)))

def sh_crowd(u, t, dt):
    """'Over 15 million were built': crane up and away over a sea of black Model Ts, the hero car glowing in the middle."""
    acc = ACC[2]
    s = W.floor(t, 0, acc)
    m, g, sp = W.car(2, t, 0, driver=drive("proud", t), lamps=1.0)
    s.append(m)
    r = np.random.default_rng(7)
    for i in range(-4, 5):
        for j in range(-4, 3):
            if i == 0 and j == 0: continue
            s.append(_tproxy().copy().rot("y", r.uniform(-4, 4)).mv(i * 3.0 + r.uniform(-0.2, 0.2), 0, j * 2.0))
    g = g + [PR.beam((0, 9, 0), (0, -1, 0), 9, 1.8, (120, 170, 255), 0.18)]
    k = back(seg(t, ws(8, 1) - 0.1, ws(8, 1) + 0.3))
    if k > 0: s.append(W.neon("15,000,000+", 2.3, 0.5, (90, 160, 255), 2.6).sc(k).rot("x", -30).mv(0, 2.15, 0.3))
    e = cam_e(u)
    cam = Cam(lerp((2.6, 2.2, 5.0), (5.0, 7.5, 9.5), e), lerp((0, 1.5, 0), (0, 1.2, -1.5), e), 48)
    return D(s, cam, acc, g, sp, (0, 0, 0), beams=False, t=t, env=W.env(acc, fog=(8, 34), shadow_size=14))

def tag(text, col, w=1.3):
    return W.neon(text, w, 0.5, col, 2.8)

def sh_price(u, t, dt):
    """'the price fell to $260': $850 tag gets slashed with a red bar and a green $260 tag drops into place; coins."""
    s, acc = stage(t, 2)
    m, g, sp = W.car(2, t, 0, driver=drive("shock" if t < ws(8, 10) else "grin", t), lamps=0.6); s.append(m)
    k1 = seg(t, ws(8, 7), ws(8, 9))
    old = tag("$850", (90, 160, 255)).mv(0.3, 2.05 - 1.2 * ein(seg(t, ws(8, 10), ws(8, 10) + 0.5)), 0)
    if t < ws(8, 10) + 0.5: s.append(old)
    if k1 > 0: s.append(cb(0.3, 2.05, 0.09, 1.4 * ease(k1), 0.08, 0.02, (255, 40, 40), b=0.01, e=3.0).rot("z", 12, (0.3, 2.05, 0)))
    k2 = back(seg(t, ws(8, 10) - 0.05, ws(8, 10) + 0.35))
    if k2 > 0: s.append(tag("$260", (80, 255, 140)).sc(k2).mv(0.3, 2.05, 0.05))
    e = cam_e(u)
    cam = orbit(mix(58, 50, e), 5.3, 1.9, (0.2, 1.55, 0), 44, aperture=0.03)
    return D(s, cam, acc, g, sp, t=t)

@lru_cache(None)
def _wallet():
    br = (120, 70, 40)
    return (bbox(-0.12, -0.01, -0.08, 0.0, 0.01, 0.08, br, b=0.005, m=SATIN), bbox(0.0, -0.01, -0.08, 0.12, 0.01, 0.08, br, b=0.005, m=SATIN))

def moth(t):
    body = capsule((0, 0, -0.03), (0, 0, 0.03), 0.012, 6, (120, 110, 100))
    f = 50 * math.sin(t * 40)
    w1 = quad((0, 0, 0), (0.07, 0, -0.02), (0.07, 0, 0.03), (0, 0, 0.02), (180, 170, 150), m=CLOTH).rot("z", f)
    w2 = quad((0, 0, 0.02), (-0.07, 0, 0.03), (-0.07, 0, -0.02), (0, 0, 0), (180, 170, 150), m=CLOTH).rot("z", -f)
    return cat([body, w1, w2])

def sh_wallet(u, t, dt):
    """JOKE 'Finally, a car in my budget.': Yub, standing by the Model T, opens his wallet - a single moth flutters out."""
    s, acc = stage(t, 2)
    m, g, sp = W.car(2, t, 0, driver=None, lamps=0.6); s.append(m)
    op = ease3(seg(t, ws(8, 13), ws(8, 15)))
    expr = "grin" if t < ws(8, 15) + 0.1 else "deadpan"
    a, b = _wallet(); wl = cat([a.copy().rot("z", -80 * op, (0, 0, 0)), b.copy().rot("z", 80 * op, (0, 0, 0))]).sc(2.4).rot("x", -55).rot("y", 20)
    yb = yub(expr, ra=(55, 6, 80), la=(55, -6, 80), head=(0, 15 if t < ws(8, 15) else -12, 0), look="c" if t < ws(8, 15) else "u")
    hand = (0.0, 1.15, 0.38)
    s += [yb.rot("y", -30).mv(0.8, 0, 1.7)]
    wl_pos = (0.8 + 0.38 * math.sin(math.radians(-30)), 1.1, 1.7 + 0.38 * math.cos(math.radians(-30)))
    s.append(wl.mv(*wl_pos))
    fm = seg(t, ws(8, 15), ws(8, 15) + 1.4)
    if fm > 0:
        mp = (wl_pos[0] + 0.22 * math.sin(fm * 9) + 0.25 * fm, wl_pos[1] + 0.05 + 0.75 * eout(fm), wl_pos[2] + 0.25 * fm + 0.08 * math.cos(fm * 7))
        s.append(moth(t).sc(3.2).mv(*mp)); sp = sp + [(mp, (255, 240, 200), 0.06, 0.5)]
    e = cam_e(u)
    cam = Cam(lerp((1.8, 1.7, 5.0), (1.5, 1.7, 4.4), e), (0.6, 1.5, 1.5), 42, aperture=0.08)
    return D(s, cam, acc, g, sp, (0.5, 0, 1), t=t)

# ---------------------------------------------------------------- 1959 Volvo seatbelt
def sh_upgrade3(u, t, dt):
    """'1959': mint scan sweeps the Model T into a two-tone 1950s car with chrome bumpers, whitewalls, Volvo badge."""
    s, acc = stage(t, 3)
    a, _, _ = W.car(2, t, 0, driver=None, lamps=0.6); b, g, sp = W.car(3, t, 0, driver=None, lamps=0.8)
    xs = mix(1.6, -1.5, ease3(seg(t, ws(9, 0), ws(9, 1))))
    s += [W.wipe(a, b, xs), drive("smile", t)]
    sg, ssp = W.scan_fx(xs, acc, 1.9, 1.7, 1.0 if -1.45 < xs < 1.55 else 0, t)
    e = cam_e(u)
    cam = orbit(mix(-30, -10, e), 5.2, 1.8, (0.2, 1.25, 0), 44)
    return D(s, cam, acc, g + sg, sp + ssp, t=t)

def sh_volvo(u, t, dt):
    """Macro on the Volvo badge on the chrome grille, light sweep."""
    s, acc = stage(t, 3)
    m, g, sp = W.car(3, t, 0, driver=drive("smile", t), lamps=0.9); s.append(m)
    zs = mix(-0.4, 0.4, ease3(u))
    g = g + [PR.glow_quad(0.06, 0.45, (200, 255, 230), 1.3).rot("y", 90).mv(1.23, 0.9, zs)]
    e = cam_e(u)
    cam = Cam(lerp((2.0, 1.0, -0.6), (1.95, 0.95, 0.4), e), (1.2, 0.88, 0.0), 34, aperture=0.4)
    return D(s, cam, acc, g, sp, (1, 0, 0), t=t)

def belt(prog, slump=0.0):
    """Three-point belt across seated Yub: shoulder strap (pillar top -> buckle) + lap strap (hip anchor -> buckle)."""
    A = np.float32([-0.9, 1.62, 0.44]); B = np.float32([-0.36, 1.1, -0.2]); Cp = np.float32([-0.62, 1.05, 0.44])
    sh = [A, np.float32([-0.56, 1.56, 0.18]), np.float32([-0.355, 1.38, 0.07]), np.float32([-0.345, 1.22, -0.08]), B]
    lp = [Cp, np.float32([-0.42, 1.14, 0.22]), np.float32([-0.38, 1.15, 0.0]), B]
    def strap(pts, p):
        out = []; n = len(pts) - 1
        for i in range(n):
            a, b = pts[i], pts[i + 1]; f = min(max(p * n - i, 0), 1)
            if f <= 0: break
            out.append(capsule(a, a + (b - a) * f, 0.026, 6, (120, 140, 180), CLOTH).glow(0.25))
        return out
    parts = strap(sh, prog) + strap(lp, prog)
    parts.append(cb(B[0], B[1], B[2], 0.06, 0.04, 0.09, (220, 224, 232), b=0.01, m=CHROME))
    return cat(parts) if parts else None, (A, B, Cp)

def sh_belt(u, t, dt):
    """Macro: three anchor points glow 1-2-3, Bohlin's belt draws across Yub and CLICKS into the buckle."""
    s, acc = stage(t, 3)
    m, g, sp = W.car(3, t, 0, driver=drive("smile" if t < ws(9, 8) else "grin", t, la=(40, 10, 60)), lamps=0.9); s.append(m)
    prog = ease3(seg(t, ws(9, 6) - 0.2, ws(9, 8) - 0.02))
    b, pts = belt(prog); s.append(b)
    for i, p in enumerate(pts):
        k = back(seg(t, ws(9, 5) + 0.15 * i, ws(9, 5) + 0.15 * i + 0.3))
        if k > 0: sp = sp + [(tuple(p), (90, 255, 200), 0.05 * k, 1.6)]
    c = seg(t, ws(9, 8), ws(9, 8) + 0.6)
    if 0 < c < 1: g = g + [PR.rings(c * 0.6, 3, 0.05, 0.08, 1.0, (120, 255, 210), 2.0 * (1 - c)).rot("y", 70).mv(*pts[1])]
    e = cam_e(u)
    cam = Cam(lerp((1.15, 2.05, 1.15), (0.95, 1.95, 0.9), e), (-0.45, 1.3, 0.05), 46, aperture=0.12)
    return D(s, cam, acc, g, sp, (0, 0, 0), t=t)

@lru_cache(None)
def _free(): return W.paper([("PATENT", 66), ("3-POINT", 52), ("SEATBELT", 48), ("1959", 44)], 0.75, 0.98, ("FREE", (30, 150, 60)))

def sh_free(u, t, dt):
    """'Volvo gives the patent away, free': the belt patent floats up out of the car, a green FREE stamp lands on it,
    and it multiplies into copies flying off to every direction."""
    s, acc = stage(t, 3)
    b, _ = belt(1.0)
    m, g, sp = W.car(3, t, 0, driver=drive("proud", t), lamps=0.9); s += [m, b]
    k = ease3(seg(t, ws(9, 9), ws(9, 13)))
    doc = _free().copy().mv(0.3, 1.2 + 1.2 * k, 0.9)
    s.append(doc)
    fly = seg(t, ws(9, 15) - 0.2, ws(9, 15) + 0.8)
    for i in range(5):
        if fly <= 0: break
        a = i * 1.26
        s.append(_free().copy().sc(0.6).rot("y", 40 * i).mv(0.3 + 3.5 * fly * math.cos(a), 2.4 + 1.0 * fly, 0.9 + 3.0 * fly * math.sin(a)))
    e = cam_e(u)
    cam = orbit(mix(70, 58, e), 4.4, 1.9, (0.2, 1.5, 0.3), 46, aperture=0.03)
    return D(s, cam, acc, g, sp, t=t)

def sh_together(u, t, dt):
    """JOKE 'Finally, something holding me together.': Yub goes floppy with relief - he sags, wobbles like jelly,
    and the glowing belt keeps him upright."""
    s, acc = stage(t, 3)
    w = math.sin((t - ws(10, 0)) * 9) * math.exp(-(t - ws(10, 0)) * 1.2)
    y = drive("proud", t, la=(10, 30, 10), ra=(10, 30, 10), head=(0, 18 * w, 14 * w), lean=12 * w - 6)
    m, g, sp = W.car(3, t, 0, driver=y, lamps=0.9)
    b, pts = belt(1.0); b.glow(0.5 + 0.4 * math.sin(t * 6)); b.c[:] = rgb((90, 255, 200))
    s += [m, b]
    e = cam_e(u)
    cam = Cam(lerp((1.1, 2.1, 1.3), (0.9, 2.0, 1.05), e), (-0.45, 1.45, 0.0), 42, aperture=0.12)
    return D(s, cam, acc, g, sp + [((-0.5, 1.5, 0.3), (120, 255, 210), 0.3, 0.4)], (0, 0, 0), t=t)

# ---------------------------------------------------------------- 1977 microprocessor
def sh_upgrade4(u, t, dt):
    """'1977': orange scan sweeps the car into a bronze 1970s car with an Oldsmobile badge and a dash pod."""
    s, acc = stage(t, 4)
    a, _, _ = W.car(3, t, 0, driver=None, lamps=0.8); b, g, sp = W.car(4, t, 0, driver=None, lamps=0.9)
    xs = mix(1.6, -1.5, ease3(seg(t, ws(11, 0), ws(11, 2))))
    bl, _ = belt(1.0)
    s += [W.wipe(a, b, xs), drive("smile", t), bl]
    sg, ssp = W.scan_fx(xs, acc, 1.9, 1.7, 1.0 if -1.45 < xs < 1.55 else 0, t)
    ll, lsp = llama_at(t, ws(11, 0), -7.5, 1.5, -7.0)
    e = cam_e(u)
    cam = orbit(mix(20, 45, e), 5.2, 1.9, (0.2, 1.25, 0), 44)
    return D(s + ll, cam, acc, g + sg, sp + ssp + lsp, t=t)

def chip(t, k=1.0):
    body = cb(0, 0, 0, 0.14, 0.02, 0.14, (20, 20, 24), b=0.006, m=SATIN)
    pins = [cb(sg * 0.08, -0.005, z, 0.03, 0.006, 0.012, (230, 190, 90), b=0.002, m=CHROME) for sg in (-1, 1) for z in np.linspace(-0.055, 0.055, 6)]
    die = cb(0, 0.011, 0, 0.07, 0.002, 0.07, (255, 150, 50), b=0.001, e=1.2 + 2.0 * k)
    return cat([body, die] + pins)

def sh_chip(u, t, dt):
    """Macro mechanism: the microprocessor on the dash; golden traces light up and race away from it, light rays bloom."""
    s, acc = stage(t, 4)
    m, g, sp = W.car(4, t, 0, driver=drive("shock", t, look="c"), lamps=0.9); s.append(m)
    k = ease3(seg(t, ws(11, 9), ws(11, 10) + 0.3))
    s.append(chip(t, k).mv(0.16, 1.13, -0.18))
    for i in range(6):
        a = i * 1.047
        pts = [(0.16, 1.125, -0.18), (0.16 + 0.12 * math.cos(a), 1.125, -0.18 + 0.12 * math.sin(a)), (0.16 + 0.12 * math.cos(a) + 0.1, 1.125, -0.18 + 0.2 * math.sin(a))]
        g = g + [PR.flow(pts, t, (255, 170, 60), 0.006, 2.5, 2.0 * (0.3 + k), 8)]
    g = g + [PR.beam((0.16, 1.14, -0.18), (0, 1, 0.1), 0.8, 0.35, (255, 170, 80), 0.25 * k)]
    e = cam_e(u)
    cam = Cam(lerp((0.62, 1.48, -0.6), (0.5, 1.4, -0.45), e), (0.16, 1.13, -0.18), 36, aperture=0.5, focus=0.6)
    return D(s, cam, acc, g, sp + [((0.16, 1.14, -0.18), (255, 170, 80), 0.06, 1.2 * k)], (0, 1, 0), t=t)

def circuits(t, k):
    """Glowing circuit traces running over the 1977 car's body."""
    out = []
    for sg in (-1, 1):
        for j, y in enumerate((0.62, 0.72, 0.84)):
            pts = [(-0.88, y, sg * 0.43), (-0.5, y, sg * 0.43), (-0.4, y + 0.06, sg * 0.43), (0.3, y + 0.06, sg * 0.31), (1.1, y + 0.02 * j, sg * 0.31)]
            n = max(2, int(len(pts) * k + 0.5))
            out.append(PR.flow(pts[:n], t + j * 0.3, (120, 230, 255), 0.008, 2.0, 2.2, 14))
    out.append(PR.flow([(0.32, 0.99, -0.2), (0.7, 0.99, -0.05), (1.08, 0.99, -0.05)], t, (120, 230, 255), 0.008, 2.0, 2.2, 10))
    out.append(PR.flow([(0.32, 0.99, 0.2), (0.7, 0.99, 0.05), (1.08, 0.99, 0.05)], t + 0.5, (120, 230, 255), 0.008, 2.0, 2.2, 10))
    return out

def sh_code(u, t, dt):
    """'Then the code kept coming': circuits flood the whole car, code panels rise and orbit it, Yub's face lit cyan."""
    s, acc = stage(t, 4)
    k = ease3(seg(t, ws(12, 0), ws(12, 4)))
    m, g, sp = W.car(4, t, 0, driver=drive("shock", t, head=(20 * math.sin(t * 2), -10, 0), look="u"), lamps=0.9)
    bl, _ = belt(1.0)
    s += [m, bl, chip(t).mv(0.16, 1.13, -0.18)]
    g = g + circuits(t, k)
    for i in range(8):
        a = i * 0.785 + t * 0.6
        g.append(W.code_panel(i, 0.5, 0.65, (120, 255, 200), 0.9 * k).rot("y", -math.degrees(a) + 90).mv(0.1 + 2.0 * math.cos(a), 0.9 + 0.25 * i % 1.5 + 1.2 * k, 2.0 * math.sin(a)))
    e = cam_e(u)
    cam = orbit(mix(35, 60, e), 3.9, 2.1, (0.1, 1.1, 0), 46, aperture=0.03)
    return D(s, cam, (90, 230, 255), g, sp, t=t, env=W.env((90, 230, 255)))

# ---------------------------------------------------------------- today: code vs 737
def stack(n, col, w=0.9, d=0.6, hgt=0.14):
    out = []
    for i in range(n):
        out.append(cb(0, hgt * (i + 0.5), 0, w, hgt * 0.8, d, (18, 26, 40), b=0.02, m=SATIN))
        out.append(box(-w / 2 - 0.002, hgt * (i + 0.15), d / 2 + 0.002, w / 2 + 0.002, hgt * (i + 0.85), d / 2 + 0.004, col, texs={"f": W.T_CODE[i % 4]}, e=1.0))
    return cat(out) if out else None

def sh_today(u, t, dt):
    """'Today': cyan scan sweeps the 1977 car into a red Tesla; Yub hops beside it; a tower of glowing code slabs rises
    floor by floor, the camera tilting up with it."""
    s, acc = stage(t, 5)
    a, _, _ = W.car(4, t, 0, driver=None, lamps=0.9)
    b = W.modern()
    xs = mix(2.6, -2.6, ease3(seg(t, ws(13, 0) - 0.1, ws(13, 3))))
    s.append(W.wipe(a, b, xs))
    sg, ssp = W.scan_fx(xs, acc, 1.9, 2.2, 1.0 if -2.55 < xs < 2.55 else 0, t)
    n = int(32 * ease3(seg(t, ws(13, 4), ws(13, 11) + 0.2)))
    st = stack(n, (120, 255, 220))
    if st is not None: s.append(st.mv(-1.0, 0, -2.2))
    yb = yub("shock" if t < ws(13, 9) else "grin", look="u", head=(-20, -20 * ease(seg(t, ws(13, 4), ws(13, 11))), 0)).rot("y", 20).mv(0.6, 0, 1.6)
    s.append(yb)
    if t > ws(13, 7): s.append(W.neon("100s OF MILLIONS", 2.4, 0.32, (120, 255, 220), 2.6).mv(-1.0, 4.9, -2.0))
    e = 0.25 * u + 0.75 * ease3(seg(t, ws(13, 3), ws(13, 11) + 0.6))
    cam = Cam(lerp((3.6, 1.5, 6.6), (3.8, 2.2, 8.2), e), lerp((0.0, 0.9, 0), (-0.6, 2.8, -1.5), e), 50, aperture=0.02)
    return D(s, cam, acc, g if False else sg, ssp, (0, 0, 0), t=t, env=W.env(acc, shadow_size=12))

@lru_cache(None)
def _plane():
    wh = (238, 240, 246); bl = (30, 60, 140)
    fus = cat([capsule((-2.6, 0, 0), (2.4, 0, 0), 0.36, 18, wh, PAINT), superellipsoid(0.36, 0.36, 0.36, 1, 1, 16, 10, wh, PAINT).sc(1.3, 1, 1).mv(2.4, 0, 0)])
    stripe = box(-2.4, -0.05, 0.355, 2.2, 0.05, 0.37, bl, m=PAINT)
    txt = box(-1.2, 0.1, 0.36, 0.8, 0.28, 0.37, (255, 255, 255), texs={"f": word_tex("BOEING 737", 384, 64, (30, 50, 120), (238, 240, 246), 40)})
    wings = [P([(0.4, -0.1, 0), (-0.6, -0.1, 0), (-1.0, -0.16, sg * 2.8)], wh, m=PAINT) for sg in (-1, 1)] + \
            [P([(0.4, -0.1, 0), (-1.0, -0.16, sg * 2.8), (-0.7, -0.16, sg * 2.8)], wh, m=PAINT) for sg in (-1, 1)]
    wings = [w for w in wings]
    eng = [cyl(0.2, 0.18, 0.6, 16, (200, 204, 214), CHROME).rot("z", -90).mv(-0.1, -0.35, sg * 1.2) for sg in (-1, 1)]
    tail = [P([(-2.2, 0.2, 0), (-2.9, 0.2, 0), (-3.0, 1.3, 0)], bl, m=PAINT), P([(-2.2, 0.2, 0), (-3.0, 1.3, 0), (-2.75, 1.3, 0)], bl, m=PAINT),
            P([(-2.3, 0.05, 0), (-2.9, 0.05, 0), (-3.0, 0.05, 1.1)], wh, m=PAINT), P([(-2.3, 0.05, 0), (-3.0, 0.05, -1.1), (-2.9, 0.05, 0)], wh, m=PAINT)]
    win = [sphere(0.035, 6, 4, (20, 24, 34), GLASS).sc(1, 1.2, 0.4).mv(x, 0.12, 0.35) for x in np.arange(-1.8, 1.8, 0.24)]
    return cat([fus, stripe, txt, *wings, *eng, *tail, *win]).mv(0, 0.8, 0)

def sh_737(u, t, dt):
    """'A Boeing 737? About 15 million': a Boeing 737 model glides in beside the stage with its own code stack - tiny next
    to the car's tower."""
    s, acc = stage(t, 5)
    s += [W.modern().mv(0, 0, 0), stack(32, (120, 255, 220)).mv(-0.5, 0, -2.2), W.neon("100s OF MILLIONS", 2.4, 0.32, (120, 255, 220), 2.6).mv(-0.5, 4.85, -2.0)]
    k = ease3(seg(t, ws(13, 12) - 0.3, ws(13, 14) + 0.3))
    s.append(_plane().copy().rot("y", -20).mv(mix(12, 3.0, k), mix(3.0, 0.0, k), -5.0))
    n = int(3 * ease3(seg(t, ws(13, 15), ws(13, 16) + 0.3)))
    stb = stack(max(n, 0), (255, 200, 90))
    if stb is not None: s.append(stb.mv(2.2, 0, -1.4))
    if t > ws(13, 16): s.append(W.neon("~15 MILLION", 1.9, 0.3, (255, 200, 90), 2.6).mv(2.2, 0.95, -1.3))
    yb = yub("smug", ra=(80, 10, 0), head=(-30, 0, 0)).rot("y", 40).mv(0.4, 0, 1.8)
    s.append(yb)
    e = cam_e(u)
    cam = Cam(lerp((2.6, 2.7, 10.2), (2.2, 2.6, 10.6), e), (1.3, 2.3, -1.6), 52, aperture=0.01)
    return D(s, cam, acc, (), (), (1, 0, -1), t=t, env=W.env(acc, shadow_size=16))

def phone_tex(state):
    def drw(d, w, h):
        if state == "fail":
            d.text((w / 2, h * 0.4), "PAIRING", font=W._f(40), fill=(255, 255, 255), anchor="mm"); d.text((w / 2, h * 0.62), "FAILED", font=W._f(46), fill=(255, 70, 70), anchor="mm")
        else:
            d.text((w / 2, h * 0.38), "PAIRING", font=W._f(40), fill=(255, 255, 255), anchor="mm")
            for i in range(8):
                a = i * 0.785; d.ellipse((w / 2 + 40 * math.cos(a) - 7, h * 0.62 + 40 * math.sin(a) - 7, w / 2 + 40 * math.cos(a) + 7, h * 0.62 + 40 * math.sin(a) + 7), fill=(90 + 20 * i, 200, 255))
    return PR.screen_tex(drw, 200, 380, (14, 18, 30))
T_PH1 = phone_tex("wait"); T_PH2 = phone_tex("fail")

def sh_phone(u, t, dt):
    """JOKE 'And I still can't pair my phone.': Yub jabs at his phone by the Tesla: PAIRING... spinner, then FAILED."""
    s, acc = stage(t, 5)
    s.append(W.modern())
    fail = t > ws(14, 4)
    ph = cat([cb(0, 0, 0, 0.09, 0.17, 0.012, (20, 20, 24), b=0.006, m=SATIN),
              quad((-0.04, -0.08, 0.007), (0.04, -0.08, 0.007), (0.04, 0.08, 0.007), (-0.04, 0.08, 0.007), (255, 255, 255), T_PH2 if fail else T_PH1, 1.4, m=SCREEN)]).sc(2.2)
    ph.rot("x", -10).rot("z", 0 if not fail else 6 * math.sin(t * 30))
    yb = yub("angry" if fail else "confused", la=(58, -14, 80), ra=(52, -12, 90), head=(0, 12, 0), sweat=fail)
    s.append(yb.rot("y", -25).mv(1.2, 0, 1.9))
    pp = (1.2 - 0.5 * math.sin(math.radians(25)), 1.1, 1.9 + 0.5 * math.cos(math.radians(25)))
    s.append(ph.rot("y", -25).mv(*pp))
    sp = [(pp, (255, 80, 80) if fail else (120, 200, 255), 0.12, 0.8)]
    e = cam_e(u)
    cam = Cam(lerp((0.2, 1.95, 4.7), (0.3, 1.9, 4.2), e), (1.0, 1.45, 1.9), 40, aperture=0.1)
    return D(s, cam, acc, (), sp, (1, 0, 2), t=t)

def ui_tex(kind):
    def drw(d, w, h):
        d.rounded_rectangle((6, 6, w - 6, h - 6), 24, outline=(120, 230, 255), width=6)
        if kind == "update":
            d.text((w / 2, h * 0.3), "SOFTWARE UPDATE", font=W._f(48), fill=(255, 255, 255), anchor="mm")
            d.rounded_rectangle((60, h * 0.55, w - 60, h * 0.7), 12, outline=(120, 230, 255), width=4)
        else:
            d.text((w / 2, h * 0.22), "ACCELERATION", font=W._f(52), fill=(255, 255, 255), anchor="mm")
            d.text((w / 2, h * 0.4), "BOOST", font=W._f(52), fill=(255, 255, 255), anchor="mm")
            d.text((w / 2, h * 0.6), "$2,000", font=W._f(64), fill=(255, 210, 80), anchor="mm")
            d.rounded_rectangle((w / 2 - 110, h * 0.72, w / 2 + 110, h * 0.9), 20, fill=(220, 30, 40)); d.text((w / 2, h * 0.81), "BUY", font=W._f(48), fill=(255, 255, 255), anchor="mm")
    return PR.screen_tex(drw, 512, 360 if kind == "update" else 440, (0, 0, 0))
T_UPD = ui_tex("update"); T_BUY = ui_tex("buy")

def holo(tid, w, h, e=1.4, col=(255, 255, 255)):
    return quad((-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0), col, tid, e, m=GLOW)

def sh_software(u, t, dt):
    """'Now even features are software': a SOFTWARE UPDATE hologram unfolds over the Tesla, progress bar filling,
    data streams pouring into the car."""
    s, acc = stage(t, 5)
    s.append(W.modern())
    k = back(seg(t, ws(15, 0), ws(15, 0) + 0.45))
    p = seg(t, ws(15, 1), ws(15, 4) + 0.6)
    g = [holo(T_UPD, 2.2 * k, 1.55 * k, 1.3).mv(0, 2.6, 0.2)] if k > 0 else []
    if p > 0: g.append(cb(-0.85 + 0.85 * p, 2.6 - 0.15 * 1.55 + 0.0, 0.22, 1.7 * p, 0.12, 0.01, (120, 230, 255), b=0.005).glow(2.5).mat(GLOW))
    for i in range(5):
        x = -1.6 + 0.8 * i
        g.append(PR.flow([(x, 2.0, 0.2), (x * 0.6, 1.4, 0.0)], t + i * 0.2, (120, 230, 255), 0.012, 3.0, 2.0, 8))
    e = cam_e(u)
    cam = orbit(mix(60, 45, e), 6.6, 2.2, (0.0, 1.5, 0), 46)
    return D(s, cam, acc, g, (), t=t)

def sh_boost(u, t, dt):
    """'In 2019, Tesla sold an Acceleration Boost for $2,000': a glowing ACCELERATION BOOST $2,000 [BUY] panel; Yub
    taps BUY on '$2,000' and the car's motors flare, energy surging under the body."""
    s, acc = stage(t, 5, v=0.0)
    car_ = W.modern()
    bought = t > ws(15, 13)
    lunge = 0.25 * math.sin(math.pi * seg(t, ws(15, 13) + 0.1, ws(15, 13) + 0.7))
    s.append(car_.mv(lunge, 0, 0))
    k = back(seg(t, ws(15, 5) - 0.1, ws(15, 5) + 0.4))
    g = [holo(T_BUY, 1.4 * k, 1.2 * k, 1.4).rot("y", 30).mv(0.5, 1.75, 2.4)] if k > 0 else []
    tap = seg(t, ws(15, 13) - 0.35, ws(15, 13))
    yb = yub("grin" if not bought else "shock", ra=(70 + 20 * tap, 8, 30 - 20 * tap), head=(-20, 0, 0)).rot("y", -75).mv(1.75, 0, 2.75)
    s.append(yb)
    if bought:
        q = seg(t, ws(15, 13), ws(15, 13) + 0.9)
        g += [PR.flow([(-1.4, 0.25, z), (0, 0.22, z), (1.4, 0.25, z)], t, (255, 60, 70), 0.03, 4, 3.0, 16) for z in (-0.5, 0.5)]
        g += [PR.rings(q * 1.5, 3, 0.2, 0.3, 1.5, (255, 80, 90), 2.0 * (1 - q)).rot("y", 90).mv(-2.4, 0.7, 0)]
    e = cam_e(u)
    cam = Cam(lerp((3.6, 1.7, 7.4), (3.2, 1.7, 6.8), e), (0.5, 1.4, 1.4), 46, aperture=0.03)
    return D(s, cam, acc, g, [((0.5, 1.5, 2.4), (255, 210, 80), 0.18, 0.6 * k)], t=t, mb=1 if bought else 0)

def paywall(t, k):
    bars = []
    for i in range(9):
        z = -1.6 + 0.4 * i
        bars.append(capsule((0, 0, z), (0, 2.2 * k, z), 0.02, 6, (255, 210, 80)))
    for j in range(5):
        y = 0.3 + 0.45 * j
        if y < 2.2 * k: bars.append(capsule((0, y, -1.6), (0, y, 1.6), 0.02, 6, (255, 210, 80)))
    return cat(bars).glow(2.2 + 0.6 * math.sin(t * 8))

def sh_paywall(u, t, dt):
    """JOKE 'My horsepower has a paywall.': a glowing golden lattice slams up in front of the Tesla's nose with a big $
    lock; the car nudges into it and bounces back. Yub deadpan to camera."""
    s, acc = stage(t, 5)
    k = back(seg(t, ws(15, 14) - 0.2, ws(15, 14) + 0.2), 1.0)
    bump = 0.18 * math.sin(math.pi * seg(t, ws(15, 16), ws(15, 16) + 0.5))
    s.append(W.modern().mv(bump, 0, 0))
    g = [paywall(t, k).mv(2.75, 0, 0)] if k > 0 else []
    if k > 0.5: s.append(W.neon("$", 0.5, 0.6, (255, 210, 80), 3.0).rot("y", 90).mv(2.78, 1.3, 0))
    yb = yub("deadpan", la=(10, 20, 100), ra=(10, 20, 100), head=(-25, 0, 0)).rot("y", 40).mv(3.0, 0, 1.8)
    s.append(yb)
    e = cam_e(u)
    cam = Cam(lerp((7.2, 1.8, 5.8), (6.8, 1.7, 5.2), e), (2.5, 1.2, 0.5), 46, aperture=0.03)
    return D(s, cam, (255, 210, 80), g, [((2.78, 1.3, 0.1), (255, 210, 80), 0.3, 0.7 * k)], t=t, env=W.env((255, 190, 80)))

# ---------------------------------------------------------------- question
LINEUP = [(0, "1886"), (1, "1912"), (2, "MODEL T"), (3, "1959"), (4, "1977"), (5, "TODAY")]
TIER = [(-0.85, 2.3, -1.2), (0.85, 2.3, -1.2), (-0.85, 1.15, -0.6), (0.85, 1.15, -0.6), (-0.85, 0.0, 0.0), (0.85, 0.0, 0.0)]
def sh_question(u, t, dt):
    """'Which of these was the biggest upgrade?': all six versions of the car on a three-tier glowing display shelf
    (oldest at the top, today at the bottom), year signs under each; Yub in front, shrugging; slow push-in."""
    s = W.floor(t, 0, (120, 200, 255)); g = []
    for y0, z0 in ((1.15, -0.6), (2.3, -1.2)):
        s.append(bbox(-1.75, 0, z0 - 0.55, 1.75, y0, z0 + 0.55, (26, 28, 40), b=0.03, m=SATIN))
    for (st, lab), (x, y, z) in zip(LINEUP, TIER):
        acc = ACC[st]
        k = back(seg(t, ws(16, 0) - 0.1 + 0.1 * st, ws(16, 0) + 0.25 + 0.1 * st))
        if st < 5:
            m, gg, _ = W.car(st, t, 0, driver=None, lamps=0.7, starter_k=1.0 if st == 1 else 0)
            m = m.sc(0.5 * max(k, 0.01)).rot("y", 28).mv(x, y, z)
        else: m = W.modern().sc(0.3 * max(k, 0.01)).rot("y", 28).mv(x, y, z)
        s.append(m)
        g.append(lathe([(0.72, 0.0), (0.76, 0.0)], 40, acc, GLOW).glow(2.2).mv(x, y + 0.005, z))
        s.append(W.neon(lab, 0.62 if len(lab) < 6 else 0.86, 0.2, acc, 2.6).mv(x, y + 0.13, z + 0.58))
    yb = yub("smile" if u < 0.35 else "confused", la=(25, 55, 80), ra=(25, 55, 80), head=(10 * math.sin(t * 2.5), 0, 8 * math.sin(t * 3)))
    s.append(yb.rot("y", -8).mv(0.0, 0, 1.3))
    ll, lsp = llama_at(t, ws(16, 0), 6, -1.4, -6.5)
    e = cam_e(u)
    cam = Cam(lerp((1.2, 2.2, 8.2), (0.9, 2.05, 7.3), e), (0.0, 1.85, -0.4), 48, aperture=0.015)
    return D(s + ll, cam, (120, 200, 255), g, lsp, (0, 1, -0.5), t=t, env=W.env((120, 200, 255), shadow_size=10, amb_i=1.0))

for _f, _h in ((sh_tip, True), (sh_kick, True), (sh_wallet, False), (sh_together, False), (sh_phone, False), (sh_paywall, True)):
    _f.hard = _h

SHOTS = [
    (0.0, sh_hook, "hook: tiny Benz tricycle, Yub squeezed on top; hologram of today's car scans in on 'became this' (llama glides past)"),
    (ws(0, 8) - 0.15, sh_tease, "flash-forward: today's red Tesla rises through a scan ring (\'became this\')"),
    (ws(1, 0) - 0.1, sh_badge, "1886: macro light sweep across the BENZ plaque, pull back"),
    (ws(1, 3) - 0.6, sh_patent, "PATENT 1886 document slams onto its stand"),
    (ws(2, 0) - 0.05, sh_three, "three wheels each get a glowing ring"),
    (ws(2, 2) - 0.05, sh_engine, "macro: single-cylinder engine, flywheel spinning, heat pulses"),
    (ws(2, 5) - 0.2, sh_horse, "0.75 HP: front three quarters of a hologram horse; JOKE it tips onto its missing rear"),
    (ws(3, 0) - 0.1, sh_tiller, "macro: Yub steers with the tiller, floor streams past"),
    (ws(3, 6) - 0.1, sh_speed, "tracking: speedometer hologram climbs to 10 MPH"),
    (ws(3, 12) + 0.05, sh_tip, "JOKE: too fast - the tricycle tips over, Yub panics"),
    (ws(4, 0) - 0.1, sh_upgrade1, "scan upgrade: four wheels, bonnet, radiator, hand crank"),
    (ws(4, 5), sh_cranking, "Yub heaves the crank"),
    (ws(4, 7) - 0.05, sh_kick, "JOKE: crank kicks back, spins Yub like a top, dizzy stars"),
    (ws(5, 0) - 0.1, sh_flyoff, "1912: the crank pops off and tumbles away"),
    (ws(5, 3) - 0.1, sh_crest, "macro: Cadillac crest light sweep"),
    (ws(5, 6) - 0.15, sh_starter, "macro: Kettering's electric starter slides in, blue arcs"),
    (ws(5, 10) - 0.25, sh_click, "Click: button, lamps flare, engine pulses; Done: smug thumbs-up"),
    (ws(6, 0) - 0.1, sh_modelT, "scan upgrade to the black Ford Model T, $850 hologram"),
    (ws(7, 0) - 0.1, sh_line, "assembly line: the car multiplies, every copy has a waving Yub; clock 12.5 HOURS -> 93 MIN"),
    (ws(8, 0) - 0.1, sh_crowd, "crane up over a sea of Model Ts, 15,000,000+"),
    (ws(8, 6) - 0.1, sh_price, "$850 slashed, $260 drops in"),
    (ws(8, 11) - 0.1, sh_wallet, "JOKE: Yub opens his wallet, a moth flies out"),
    (ws(9, 0) - 0.1, sh_upgrade3, "1959: scan upgrade to a two-tone 50s car"),
    (ws(9, 1) - 0.05, sh_volvo, "macro: Volvo badge light sweep"),
    (ws(9, 5) - 0.25, sh_belt, "three anchor points glow, belt draws across, CLICK"),
    (ws(9, 9) - 0.05, sh_free, "patent floats up, FREE stamp, copies fly everywhere"),
    (ws(10, 0) - 0.1, sh_together, "JOKE: Yub goes floppy, the belt holds him together"),
    (ws(11, 0) - 0.1, sh_upgrade4, "1977: scan upgrade to the bronze Oldsmobile"),
    (ws(11, 4) - 0.1, sh_chip, "macro: the microprocessor lights up, golden traces"),
    (ws(12, 0) - 0.1, sh_code, "circuits flood the car, code panels orbit"),
    (ws(13, 0) - 0.15, sh_today, "scan into a red Tesla, code tower rises: 100s OF MILLIONS"),
    (ws(13, 12) - 0.15, sh_737, "Boeing 737 glides in with a tiny ~15 MILLION stack"),
    (ws(14, 0) - 0.1, sh_phone, "JOKE: PAIRING... FAILED"),
    (ws(15, 0) - 0.1, sh_software, "SOFTWARE UPDATE hologram"),
    (ws(15, 5) - 0.2, sh_boost, "ACCELERATION BOOST $2,000 BUY, car surges"),
    (ws(15, 14) - 0.25, sh_paywall, "JOKE: a $ paywall lattice blocks the car"),
    (ws(16, 0) - 0.1, sh_question, "all six versions in a row, Yub shrugs"),
]

TOPS = [(ws(1, 0), ws(2, 0), "1886 · Benz Patent-Motorwagen"), (ws(2, 5), ws(3, 0), "0.75 horsepower"), (ws(3, 6), ws(3, 13), "About 10 mph"),
        (ws(5, 2), ws(6, 0), "1912 · Cadillac electric starter"), (ws(6, 0), ws(7, 0), "1908 · Ford Model T · $850"),
        (ws(7, 0), ws(8, 0), "Assembly line: 12.5 h → 93 min"), (ws(8, 0), ws(8, 11), "15 million+ built · $850 → $260"),
        (ws(9, 0), ws(11, 0), "1959 · Volvo three-point seatbelt"), (ws(11, 0), ws(12, 0), "1977 · Oldsmobile Toronado"),
        (ws(13, 0), ws(14, 0), "Lines of code: car vs Boeing 737"), (ws(15, 5), ws(16, 0), "2019 · Tesla Acceleration Boost $2,000")]

SFX = [(ws(0, 8), "sparkle", 0.6), (ws(1, 0), "whoosh", 0.4), (ws(1, 3) + 0.05, "stamp", 0.9), (ws(2, 0), "pop", 0.4), (ws(2, 0) + 0.12, "pop", 0.4),
       (ws(2, 0) + 0.24, "pop", 0.4), (ws(2, 2), "sputter", 0.6), (ws(2, 5), "sparkle", 0.5), (ws(2, 12), "fall", 0.6), (ws(3, 6), "vroom", 0.3),
       (ws(3, 14), "screech", 0.6), (ws(3, 16), "crash", 0.7), (ws(4, 0), "whoosh", 0.5), (ws(4, 5), "grind", 0.5), (ws(4, 7), "boing", 0.8),
       (ws(4, 7) + 0.3, "whoosh", 0.5), (ws(5, 0), "pop", 0.7), (ws(5, 3), "sparkle", 0.5), (ws(5, 9), "click", 1.0), (ws(5, 9) + 0.05, "buzzer", 0.25),
       (ws(5, 10), "click", 1.4), (ws(5, 10) + 0.1, "vroom", 0.6), (ws(5, 11), "ding", 0.5), (ws(6, 0), "whoosh", 0.5), (ws(6, 6), "cha_ching", 0.6),
       (ws(7, 0), "whoosh", 0.4), (ws(7, 10), "ding", 0.6), (ws(8, 1), "confetti", 0.5), (ws(8, 7), "slide_down", 0.5), (ws(8, 10), "coin", 0.8),
       (ws(8, 15) + 0.1, "crickets", 0.8), (ws(9, 0), "whoosh", 0.5), (ws(9, 8), "click", 1.6), (ws(9, 8) + 0.02, "ding", 0.4),
       (ws(9, 15), "stamp", 0.7), (ws(10, 0), "boing", 0.6), (ws(11, 0), "whoosh", 0.5), (ws(11, 10), "sparkle", 0.7), (ws(12, 0), "boom", 0.4),
       (ws(13, 0), "whoosh", 0.5), (ws(13, 12), "vroom", 0.4), (ws(14, 4), "buzzer", 0.6), (ws(15, 0), "sparkle", 0.5), (ws(15, 13), "cha_ching", 0.7),
       (ws(15, 13) + 0.1, "vroom", 0.6), (ws(15, 14), "thump", 0.8), (ws(15, 16) + 0.1, "boing", 0.5), (ws(16, 0), "pop", 0.4), (ws(16, 6), "ding", 0.4)]
CRASH = [ws(1, 0), ws(5, 2), ws(6, 0), ws(9, 0), ws(11, 0), ws(13, 0), ws(16, 0)]

ONSCREEN = [HOOK] + [x[2] for x in TOPS] + ["BENZ plaque", "PATENT 1886 Benz Patent-Motorwagen", "0.75 HP", "MPH speedometer", "Cadillac crest",
            "$850", "12.5 HOURS", "93 MIN", "15,000,000+", "$260", "Volvo badge", "PATENT 3-POINT SEATBELT 1959 FREE", "OLDSMOBILE badge",
            "100s OF MILLIONS", "BOEING 737", "~15 MILLION", "PAIRING FAILED", "SOFTWARE UPDATE", "ACCELERATION BOOST $2,000 BUY", "$",
            "1886 / 1912 / MODEL T / 1959 / 1977 / TODAY", "Ford oval", "Tesla T"]

if __name__ == "__main__": E.main(V)
