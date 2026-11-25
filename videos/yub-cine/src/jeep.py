"""jeep_wave: cinematic low-poly short. Golden-hour desert canyon road.
Oddity (never mentioned): a cow lounging in a lawn chair under a beach umbrella beside the road, reading a newspaper."""
import math, sys
import _lib  # noqa: F401  (lib/cine3d + characters/yub-3d on sys.path)
from functools import lru_cache
import numpy as np
from geo import (P, cat, quad, box, cbox, bbox, cb, lathe, cyl, superellipsoid, sphere, capsule, tiles, panel, word_tex, font, rgb, tex, Cam,
                 MATTE, PAINT, GLASS, CHROME, SATIN, RUBBER, GLOW, SCREEN, SKIN as M_SKIN, CLOTH, T_DISC)
from render3d import Env
import cars3d as C
import props3d as PR
import engine3d as E
from engine3d import ease, lerp, shake
from yub import yub
import facedraw as FD

NAME = "jeep"
V = E.Video(sys.modules[__name__]); ws = V.ws; DUR = V.dur
HOOK = "Jeep drivers have a secret rule."
ACCENT = (255, 190, 0)
HOT = {"jeep", "waves", "wave", "wave,", "tradition", "believed", "world", "war", "two", "soldiers", "willys", "official", "rules",
       "unwritten", "back", "brand", "nothing", "program", "popular", "name", "yes", "no"}
TOPS = [(ws(3, 0), ws(4, 0), "WWII · Willys MB"), (ws(4, 0), ws(4, 5), "No official rules"), (ws(6, 0), ws(7, 0), "Jeep Wave owner program")]
ONSCREEN = ["Jeep wordmark", "WWII · Willys MB", "white star", "No official rules", "RULES (blank pages)", "Jeep Wave owner program", "JEEP WAVE emblem",
            "HELLO my name is JEEP WAVE", "YES", "NO"]
ODDITY = "a cow lounging in a lawn chair under a beach umbrella beside the desert road, reading a newspaper"
CRASH = [ws(1, 6), ws(7, 0)]
MUSIC_UNDER_DB = 3.5

GOLD = dict(sky_top=(50, 90, 200), sky_hor=(255, 175, 130), ground=(120, 90, 90), sun_dir=(0.45, 0.4, -0.8), sun=(255, 210, 170), sun_i=1.9,
            amb_i=1.0, fog=(40, 160), fog_col=(235, 170, 150), exposure=0.88, stars=0.0, bloom=0.6, sun_disc=True, sat=1.08, shadow_size=16)
def env(**kw):
    d = dict(GOLD); d.update(kw); return Env(**d)
ENV = env()
SAND = (226, 176, 128); ROCK = (196, 98, 66)

# ---------------------------------------------------------------- people
@lru_cache(None)
def _npc_face(kind):
    skins = dict(beard=(232, 186, 150), cap=(150, 100, 70), granny=(236, 196, 170), soldier=(226, 180, 140))
    FD.SKIN = skins[kind]; FD.HAIR = dict(beard=(120, 70, 30), cap=(20, 20, 20), granny=(220, 220, 226), soldier=(80, 56, 30))[kind]
    t = tex(FD._face("smile" if kind != "soldier" else "grin")); FD.SKIN = (190, 128, 90); FD.HAIR = (30, 24, 28)
    return t, skins[kind]

def npc(kind="beard", wave=0.0, t=0.0):
    """Seated driver (upper body), faces +z. kinds: beard, cap, granny, soldier. wave: 0..1 arm up."""
    fid, sk = _npc_face(kind)
    top = dict(beard=(200, 50, 50), cap=(40, 150, 90), granny=(150, 90, 200), soldier=(104, 112, 64))[kind]
    head = superellipsoid(0.13, 0.15, 0.13, 0.8, 0.75, 24, 16, sk, M_SKIN)
    c = head.t.mean(1); fr = c[:, 2] > 0.06
    head.k[fr] = fid; head.c[fr] = 1.0
    head.uv[fr] = np.stack([np.clip(0.5 + head.t[..., 0] / 0.22, 0.01, 0.99), np.clip(0.5 - head.t[..., 1] / 0.25, 0.01, 0.99)], -1)[fr]
    head.mv(0, 1.62, 0)
    parts = [superellipsoid(0.19, 0.27, 0.12, 0.5, 0.6, 16, 10, top, CLOTH).mv(0, 1.17, 0), head]
    if kind == "beard": parts.append(superellipsoid(0.12, 0.07, 0.07, 0.8, 0.8, 14, 8, (120, 70, 30), MATTE).mv(0, 1.52, 0.08))
    if kind in ("beard", "granny"): parts.append(superellipsoid(0.14, 0.08, 0.14, 0.8, 0.8, 14, 8, dict(beard=(120, 70, 30), granny=(220, 220, 226))[kind], MATTE).mv(0, 1.74, -0.01))
    if kind == "cap": parts += [superellipsoid(0.145, 0.08, 0.145, 0.7, 0.8, 16, 8, (220, 60, 40), MATTE).mv(0, 1.74, 0), cb(0, 1.7, 0.16, 0.2, 0.02, 0.12, (220, 60, 40), b=0.008)]
    if kind == "soldier": parts.append(superellipsoid(0.17, 0.1, 0.17, 0.8, 0.9, 18, 10, (84, 94, 52), SATIN).mv(0, 1.76, 0))
    a = wave * (150 + 20 * math.sin(t * 16))
    for sg in (-1, 1):
        if sg == 1 and wave > 0:
            el = np.float32([0.22, 1.36, 0]) + np.float32([math.sin(math.radians(a)) * 0.28, -math.cos(math.radians(a)) * 0.28, 0])
            hand = el + np.float32([math.sin(math.radians(a - 20)) * 0.26, -math.cos(math.radians(a - 20)) * 0.26, 0])
            parts += [capsule((0.22, 1.36, 0), el, 0.05, 8, top, CLOTH), capsule(el, hand, 0.042, 8, sk, M_SKIN),
                      superellipsoid(0.045, 0.06, 0.02, 0.7, 0.7, 10, 6, sk, M_SKIN).mv(*(hand + (hand - el) * 0.25))]
        else:
            parts += [capsule((sg * 0.22, 1.36, 0), (sg * 0.24, 1.1, 0.25), 0.05, 8, top, CLOTH), capsule((sg * 0.24, 1.1, 0.25), (sg * 0.12, 1.12, 0.5), 0.042, 8, sk, M_SKIN)]
    return cat(parts)

def seat_npc(p, x=-0.62, y=0.75, z=-0.42): return p.rot("y", 90).mv(x, y - 0.95, z)
def seat_yub(h, x=-0.62, y=0.75, z=-0.42): return h.rot("y", 90).mv(x, y - 0.5, z)

# ---------------------------------------------------------------- sets
def cactus(h=1.8):
    g = (60, 150, 70)
    return cat([capsule((0, 0, 0), (0, h, 0), 0.16, 10, g, SATIN), capsule((0, h * 0.5, 0), (0.35, h * 0.5, 0), 0.1, 8, g, SATIN),
                capsule((0.35, h * 0.5, 0), (0.35, h * 0.8, 0), 0.1, 8, g, SATIN), capsule((0, h * 0.4, 0), (-0.3, h * 0.42, 0), 0.09, 8, g, SATIN),
                capsule((-0.3, h * 0.42, 0), (-0.3, h * 0.65, 0), 0.09, 8, g, SATIN)])

def mesa(w, h, d, col=ROCK):
    return cat([superellipsoid(w / 2, h * 0.38, d / 2, 0.25, 0.35, 16, 8, col, MATTE).mv(0, h * 0.38, 0),
                superellipsoid(w * 0.36, h * 0.2, d * 0.38, 0.25, 0.35, 16, 8, tuple(int(c * 0.9) for c in col), MATTE).mv(0, h * 0.85, 0),
                superellipsoid(w / 2 * 1.01, h * 0.03, d / 2 * 1.01, 0.2, 0.35, 16, 4, (250, 170, 110), MATTE).mv(0, h * 0.45, 0)])

def cow_chair(t):
    hide = (250, 250, 248)
    body = superellipsoid(0.55, 0.32, 0.3, 0.8, 0.8, 18, 10, hide, SATIN).rot("z", 35).mv(0, 0.8, 0)
    spots = [sphere(0.12, 10, 6, (24, 24, 26)).sc(1, 0.6, 0.3).mv(-0.1 + 0.25 * i, 0.85 + 0.1 * (i % 2), 0.27) for i in range(3)]
    head = cat([superellipsoid(0.17, 0.2, 0.15, 0.8, 0.8, 14, 8, hide, SATIN).mv(-0.45, 1.3, 0), superellipsoid(0.12, 0.08, 0.13, 0.8, 0.8, 12, 6, (240, 170, 170), SATIN).mv(-0.5, 1.18, 0.08),
                *[capsule((-0.45, 1.46, s * 0.1), (-0.48, 1.56, s * 0.17), 0.025, 6, (240, 230, 200)) for s in (1, -1)],
                *[sphere(0.022, 6, 4, (16, 16, 18)).mv(-0.42, 1.34, s * 0.07 + 0.12) for s in (1, -1)]])
    legs = [capsule((0.35, 0.55, s * 0.15), (0.75, 0.45, s * 0.15), 0.07, 8, hide) for s in (1, -1)] + [capsule((0.75, 0.45, s * 0.15), (0.8, 0.05, s * 0.15), 0.06, 8, hide) for s in (1, -1)]
    paper = cat([box(0.18, 0.95, -0.25, 0.2, 1.35, 0.25, (240, 238, 228))]).rot("z", -12 + 4 * math.sin(t * 2), (0.19, 1.0, 0))
    chair = cat([bbox(-0.5, 0.35, -0.38, 0.6, 0.42, 0.38, (40, 140, 230), b=0.02), bbox(-0.62, 0.35, -0.38, -0.52, 1.2, 0.38, (40, 140, 230), b=0.02).rot("z", -22, (-0.57, 0.38, 0)),
                 *[capsule((x, 0, z), (x, 0.37, z), 0.02, 6, (210, 210, 216), CHROME) for x in (-0.45, 0.5) for z in (-0.35, 0.35)]])
    umb = cat([cyl(0.03, 0.03, 2.3, 6, (230, 230, 230))] + [P([(0, 2.4, 0), (1.3 * math.cos(a0), 2.05, 1.3 * math.sin(a0)), (1.3 * math.cos(a1), 2.05, 1.3 * math.sin(a1))],
               (240, 60, 80) if i % 2 else (255, 240, 120), m=SATIN) for i, (a0, a1) in enumerate((2 * math.pi * k / 10, 2 * math.pi * (k + 1) / 10) for k in range(10))]).mv(-1.0, 0, 0)
    return cat([chair, body, *spots, head, *legs, paper, umb])

def wrap(x, t, v, L=90.0): return ((x - v * t + L / 2) % L) - L / 2

def desert(t, v=0.0, odd=True, cow_x=-6.0):
    s = [tiles(-60, -80, 60, 40, -0.01, 12.0, -1, SAND, m=MATTE), tiles(-60, -2.6, 60, 2.6, 0.0, 6.0, -1, (64, 62, 70), m=SATIN)]
    s += [box(wrap(x, t, v), 0.006, -0.08, wrap(x, t, v) + 2.2, 0.012, 0.08, (255, 200, 40), m=PAINT) for x in np.arange(-44, 44, 5.0)]
    s += [box(-60, 0.006, z - 0.06, 60, 0.012, z + 0.06, (240, 240, 240)) for z in (-2.35, 2.35)]
    r = np.random.default_rng(4)
    for i, x in enumerate(np.arange(-44, 44, 6.5)):
        z = (-5.5 - r.uniform(0, 8)) if i % 2 else (5.0 + r.uniform(0, 7))
        s.append(cactus(1.4 + r.uniform(0, 1)).mv(wrap(x, t, v), 0, z))
    for x, z, w, h in ((-34, -52, 22, 12), (-8, -64, 30, 18), (22, -55, 20, 14), (44, -46, 14, 9), (-50, 30, 18, 10), (30, 40, 24, 12)):
        s.append(mesa(w, h, 10).mv(x - (0.03 * v * t) % 20, 0, z))
    if odd: s.append(cow_chair(t).rot("y", -35).mv(wrap(cow_x, t, v), 0, -4.8))
    return s

def drive_yub(expr="smile", t=0.0, **kw):
    kw.setdefault("la", (55, 4, 40)); kw.setdefault("ra", (55, 4, 40))
    return seat_yub(yub(expr, sit=True, bob=0.012 * math.sin(t * 17), **kw))

def yjeep(t, expr="smile", v=1, **kw): return C.wrangler(C.JEEP_YELLOW, spin=-t * 700 * v, driver=drive_yub(expr, t, **kw))
def rjeep(t, wave=0.0, kind="beard", col=C.JEEP_RED, v=1): return C.wrangler(col, spin=-t * 700 * v, driver=seat_npc(npc(kind, wave, t)))

def arc(p0, p1, t, h=0.8, col=(255, 220, 120), n=26, prog=1.0, e=2.6):
    p0, p1 = np.float32(p0), np.float32(p1); out = []
    m = int(n * prog)
    for i in range(m):
        a, b = i / n, (i + 1) / n
        A = p0 + (p1 - p0) * a + np.float32([0, h * 4 * a * (1 - a), 0]); B = p0 + (p1 - p0) * b + np.float32([0, h * 4 * b * (1 - b), 0])
        out.append(capsule(A, B, 0.025, 6, col).glow(e * (0.5 + 0.5 * math.sin(i * 0.6 - t * 12))))
    return cat(out) if out else None

# ---------------------------------------------------------------- shots
def sh_hook(u, t, dt):
    """Golden hour: Yub (LTN cap) cruises a yellow Wrangler down a desert road, low tracking front 3/4, sun flaring."""
    e = ease(u)
    return dict(scene=desert(t, 9) + [yjeep(t, "smug", head=(-15, 0, 0))], cam=Cam(lerp((2.6, 1.55, -2.9), (2.2, 1.65, -2.5), e), (-0.6, 1.65, -0.5), 52, roll=-3, aperture=0.1),
                sprites=[((2.12, 0.9, s * 0.55), (255, 240, 220), 0.06, 0.6) for s in (1, -1)], center=(0, 0, 0))

def sh_secret(u, t, dt):
    """Macro: Yub's face in the Jeep - eyebrow up, eyes darting: 'secret rule?'"""
    look = "l" if u < 0.5 else "r"
    return dict(scene=desert(t, 9) + [yjeep(t, "confused", look=look, head=(12 * math.sin(t * 5), 0, 6))], cam=Cam((1.15, 1.92, -1.2), (-0.62, 1.9, -0.42), 44, aperture=0.25), center=(0, 1, 0))

def sh_pass(u, t, dt):
    """Wide: a red Wrangler approaches in the other lane, sun behind it."""
    xr = 16 - 24 * ease(u)
    s = desert(t, 9) + [yjeep(t).mv(0, 0, -1.3), rjeep(t).rot("y", 180).mv(xr, 0, 1.3)]
    return dict(scene=s, cam=Cam((-6.5, 2.4, -5.2), (3.0, 1.0, 0.5), 46, aperture=0.04), center=(2, 0, 0))

def sh_wavemacro(u, t, dt):
    """Slow-mo macro: the red Jeep driver's hand lifts into the wave, warm light trails behind the fingers."""
    j = rjeep(t * 0.3, wave=min(1, u * 2.5)).rot("y", 180).mv(0.6 - 0.6 * u, 0, 0)
    hand = np.float32([0.6 - 0.6 * u + 0.62, 1.55 + 0.25 * min(1, u * 2.5), 0.42 + 0.35])
    return dict(scene=desert(t * 0.3, 9, odd=False) + [j], cam=Cam((-1.2 - 0.6 * u, 1.8, 2.6), (0.9 - 0.6 * u, 1.7, 0.6), 38, aperture=0.35, focus=2.4),
                sprites=[(tuple(hand), (255, 220, 150), 0.08, 0.8)], center=(0, 1, 0))

def sh_panic(u, t, dt):
    """JOKE: Yub panics - sweat, hands off the wheel, flailing, head whipping."""
    f = math.sin(t * 22)
    sx, sy, _ = shake(t, 0.03)
    j = yjeep(t, "panic", sweat=True, la=(20, 60 + 40 * f, 50), ra=(20, 60 - 40 * f, 50), head=(20 * f, 0, 8 * f))
    return dict(scene=desert(t, 9) + [j], cam=Cam((1.4 + sx, 1.85 + sy, -1.6), (-0.6, 1.62, -0.42), 46, aperture=0.15), center=(0, 1, 0))

def sh_convoy(u, t, dt):
    """'a tradition between Jeep drivers': drone orbit over five Wranglers in a row on the canyon road, every driver waving."""
    cols = [C.JEEP_YELLOW, C.JEEP_RED, C.JEEP_BLUE, (60, 180, 90), (250, 120, 30)]; kinds = ["cap", "beard", "granny", "cap", "beard"]
    s = desert(t, 0)
    for i, (c, k) in enumerate(zip(cols, kinds)):
        s.append(C.wrangler(c, spin=0, driver=seat_npc(npc(k, 1.0, t + i * 0.3))).rot("y", 180 if i % 2 else 0).mv(-10 + 5 * i, 0, 1.3 if i % 2 else -1.3))
    a = math.radians(-60 + 50 * u)
    return dict(scene=s, cam=Cam((9 * math.sin(a), 6.5, 9 * math.cos(a)), (0, 1.0, 0), 48, aperture=0.03), center=(0, 0, 0))

def sh_ww2(u, t, dt):
    """'World War Two': a dusty convoy of olive Willys MBs with white stars, soldiers at the wheel, light shafts through the haze."""
    s = desert(t, 6, odd=False)
    for i in range(3):
        s.append(C.willys(spin=-t * 600, driver=seat_npc(npc("soldier", 0, t), -0.68, 0.72, -0.32)).mv(-4.5 * i, 0, -1.2))
    e = ease(u)
    sun_beams = [PR.beam((x, 14, -30), (0.1, -0.7, 1), 34, 6, (255, 200, 150), 0.05) for x in (-8, 0, 8)]
    return dict(scene=s, cam=Cam(lerp((5.6, 1.1, 3.2), (4.6, 1.3, 2.6), e), (-2.5, 1.0, -1.2), 46, aperture=0.05),
                env=env(sky_hor=(255, 190, 120), fog=(10, 70), fog_col=(230, 170, 110), sat=1.05), glow=sun_beams, center=(-3, 0, -1))

def sh_willys(u, t, dt):
    """'the original Willys Jeeps': macro over the white star on the olive hood, then two soldiers exchange a wave as their Willys pass."""
    w1 = C.willys(spin=-t * 600, driver=seat_npc(npc("soldier", 1.0, t), -0.68, 0.72, -0.32)).mv(0, 0, -1.2)
    w2 = C.willys(spin=-t * 600, driver=seat_npc(npc("soldier", 1.0, t + 0.4), -0.68, 0.72, -0.32)).rot("y", 180).mv(5 - 8 * u, 0, 1.2)
    e = ease(u)
    return dict(scene=desert(t, 6, odd=False) + [w1, w2], cam=Cam(lerp((3.4, 2.1, 0.9), (-3.5, 2.4, -4.5), e), lerp((1.1, 1.0, -1.2), (1.0, 1.2, 0.2), e), 44, aperture=0.1),
                env=env(sky_hor=(255, 190, 120), fog=(10, 70), fog_col=(230, 170, 110), sat=1.05), center=(0, 0, 0))

T_RULES = word_tex("RULES", 256, 96, (40, 40, 50), (250, 246, 232), 60)
def book(open_=1.0, flip=0.0):
    cover = (150, 30, 30)
    a = 80 * open_
    left = cat([bbox(-0.6, 0, -0.42, 0, 0.04, 0.42, cover, b=0.01, m=SATIN), box(-0.57, 0.04, -0.39, -0.02, 0.06, 0.39, (250, 246, 232), e=0.25)]).rot("z", a, (0, 0, 0))
    right = cat([bbox(0, 0, -0.42, 0.6, 0.04, 0.42, cover, b=0.01, m=SATIN), box(0.02, 0.04, -0.39, 0.57, 0.06, 0.39, (250, 246, 232), e=0.25),
                 box(0.08, 0.061, -0.3, 0.52, 0.062, -0.12, (255, 255, 255), texs={"t": T_RULES})]).rot("z", -a, (0, 0, 0))
    page = box(0.02, 0.06, -0.38, 0.56, 0.065, 0.38, (252, 250, 240), e=0.3).rot("z", -a + (2 * a) * flip, (0, 0, 0))
    return cat([left, right, page])

def sh_rules(u, t, dt):
    """'There are no official rules.': a glowing rulebook floats open beside the Jeep - Yub flips the pages: all blank."""
    flip = (u * 3) % 1
    b = book(1.0, flip).rot("x", -60).mv(0.45, 1.85, 0.4)
    h = yub("confused" if u < 0.6 else "deadpan", look="c", la=(40, 30, 70), ra=(60, 20, 60), head=(0, 10, 0)).rot("y", 20).mv(-0.4, 0, 0.9)
    return dict(scene=desert(t, 0, odd=False) + [C.wrangler(C.JEEP_YELLOW).rot("y", 70).mv(-1.5, 0, -2.5), b, h], cam=Cam((0.5, 1.75, 4.0), (0.1, 1.5, 0.4), 46, aperture=0.18),
                glow=[PR.glow_quad(1.6, 1.2, (255, 230, 180), 0.7).rot("x", -60).mv(0.2, 2.0, 0.42)], sprites=[((0.2, 1.95, 0.45), (255, 230, 170), 0.25, 0.5)], center=(0, 1, 0))

def _pass_scene(t, u, wave_back=0.0, tesla=False):
    j = yjeep(t, "grin" if wave_back > 0.5 else "smile", la=(0, 150 + 18 * math.sin(t * 16), 20) if wave_back > 0 else (55, 4, 40), wave="l" if wave_back > 0 else None,
              blush=wave_back > 0.5).mv(0, 0, -1.3)
    if tesla: other = C.model3().rot("y", 180).mv(2.0 - 7 * u, 0, 1.4)
    else: other = rjeep(t, wave=1.0).rot("y", 180).mv(1.2 - 4 * u, 0, 1.3)
    return j, other

def sh_unwritten(u, t, dt):
    """'if a fellow Jeep driver waves': two Jeeps pass in slow motion; a glowing arc leaps from the other driver's hand towards Yub."""
    ts = t * 0.35
    j, o = _pass_scene(ts, u)
    x0 = 1.2 - 4 * u
    p0 = (x0 - 0.62 + 0.3, 2.05, 1.3 + 0.42 - 0.2); p1 = (-0.62 + 0.1, 1.95, -1.3 - 0.42 + 0.3)
    a_ = arc(p0, p1, t, 0.9, prog=min(1, u * 1.4))
    return dict(scene=desert(ts, 9) + [j, o] + ([a_] if a_ is not None else []), cam=Cam((6.5, 3.6, -1.0), (-0.3, 1.5, 0.0), 44, aperture=0.04), center=(0, 0, 0))

def sh_waveback(u, t, dt):
    """'you wave back.': Yub waves back proudly; the arc completes and bursts into sparks."""
    ts = t * 0.5
    j, o = _pass_scene(ts, 0.9 + 0.1 * u, wave_back=1.0)
    sp = [sphere(0.03, 6, 4, (255, 220, 120)).glow(4).mv(-0.5 + 0.6 * math.cos(i * 1.3 + t * 3), 2.2 + 0.4 * math.sin(i * 2.1 + t * 4), -1.6 + 0.3 * math.sin(i)) for i in range(10)]
    return dict(scene=desert(ts, 9) + [j, o] + sp, cam=Cam((1.5, 1.9, -2.9), (-0.6, 1.95, -1.6), 54, aperture=0.15), center=(0, 1, 0))

def sh_tesla(u, t, dt):
    """'Wave at a different brand?': Yub waves eagerly at a passing white Tesla Model 3."""
    j, o = _pass_scene(t, u, wave_back=1.0, tesla=True)
    return dict(scene=desert(t, 9, cow_x=8) + [j, o], cam=Cam((1.5, 1.9, -2.9), (-0.6, 1.85, -0.9), 54, aperture=0.08), center=(0, 1, 0))

def sh_nothing(u, t, dt):
    """JOKE 'Nothing.': the Tesla glides off; crickets; tumbleweed; Yub's wave slowly sinks, deadpan to camera."""
    k = ease(min(1, u * 1.4))
    j = yjeep(t, "deadpan" if k > 0.3 else "grin", la=(0, 150 - 110 * k, 20 + 40 * k), wave="l", head=(-25 * k, 0, 0))
    weed = superellipsoid(0.35, 0.33, 0.35, 1, 1, 10, 8, (180, 130, 70), MATTE).rot("z", -t * 500).mv(3.0 - 6 * u, 0.35, 1.4)
    return dict(scene=desert(t, 9) + [j, weed, C.model3().rot("y", 180).mv(-6 - 5 * u, 0, 1.4)], cam=Cam((1.3, 1.85, -1.55), (-0.62, 1.7, -0.42), 46, aperture=0.2), center=(0, 1, 0))

def emblem(t, k):
    ring = cat([capsule((0.75 * math.cos(a), 0.75 * math.sin(a), 0), (0.75 * math.cos(a + 0.21), 0.75 * math.sin(a + 0.21), 0), 0.03, 6, (255, 200, 60)).glow(2.5)
                for a in np.linspace(0, 2 * math.pi, 30, endpoint=False)])
    hand = cat([superellipsoid(0.16, 0.2, 0.05, 0.7, 0.7, 12, 8, (255, 210, 90)).mv(0, -0.05, 0)] +
               [capsule((-0.11 + 0.075 * i, 0.12, 0), (-0.13 + 0.09 * i, 0.32 + 0.03 * (i in (1, 2)), 0), 0.03, 6, (255, 210, 90)) for i in range(4)] +
               [capsule((0.15, 0.0, 0), (0.28, 0.12, 0), 0.03, 6, (255, 210, 90))]).glow(1.6).rot("z", 12 * math.sin(t * 6))
    sign = PR.neon_sign("JEEP WAVE", 1.6, 0.36, (255, 200, 60), 2.8, frame=False).mv(0, -1.05, 0)
    return cat([ring, hand, sign]).sc(0.4 + 0.6 * k)

def sh_program(u, t, dt):
    """'an official owner program, called Jeep Wave': at a canyon overlook a holographic JEEP WAVE emblem rises out of the yellow Jeep's grille."""
    k = ease(min(1, u * 1.6))
    j = C.wrangler(C.JEEP_YELLOW).rot("y", -90).mv(0, 0, -1)
    em = emblem(t, k).mv(0, 1.3 + 1.0 * k, 1.4)
    h = yub("shock" if u < 0.4 else "grin", look="u", head=(0, -15, 0)).rot("y", 200).mv(1.6, 0, 3.3)
    return dict(scene=desert(t, 0, odd=False) + [j, em, h], cam=Cam((2.6, 1.3, 7.0), (0.2, 1.3, 0.8), 46, aperture=0.08),
                sprites=[((0, 1.3 + 1.0 * k, 1.45), (255, 210, 120), 0.6, 0.9 * k)], center=(0, 0, 0))

def giant_hand(t, tag=0.0):
    y = (255, 196, 30)
    h = [superellipsoid(0.9, 1.1, 0.32, 0.6, 0.7, 18, 12, y, SATIN).mv(0, 2.2, 0)]
    h += [capsule((-0.62 + 0.42 * i, 3.1, 0), (-0.7 + 0.47 * i, 4.4 + 0.25 * (i in (1, 2)), 0), 0.19, 10, y, SATIN) for i in range(4)]
    h += [capsule((0.85, 2.0, 0), (1.45, 2.9, 0), 0.2, 10, y, SATIN), bbox(-1.1, 0, -0.7, 1.1, 0.9, 0.7, (120, 110, 120), b=0.08)]
    s = [cat(h).rot("z", 5 * math.sin(t * 3), (0, 0.9, 0))]
    if tag > 0:
        s.append(cat([bbox(-0.62, -0.42, 0.33, 0.62, 0.42, 0.36, (255, 255, 255), b=0.03), box(-0.58, -0.38, 0.361, 0.58, 0.38, 0.365, (255, 255, 255), texs={"f": T_TAG})]).sc(0.4 + 0.6 * tag).mv(0, 2.2, 0))
    return cat(s)
T_TAG = word_tex("HELLO\nmy name is\nJEEP WAVE", 256, 176, (24, 24, 30), (255, 255, 255), 40, border=(220, 30, 40))

def sh_popular(u, t, dt):
    """'A wave so popular': a giant yellow waving-hand monument at sunset, Jeeps parked round it, light rays."""
    s = desert(t, 0, odd=False) + [giant_hand(t).mv(0, 0, -6)]
    for i, (c, a) in enumerate(((C.JEEP_RED, 40), (C.JEEP_BLUE, -40), ((60, 180, 90), 130), ((250, 120, 30), -130))):
        s.append(C.wrangler(c).rot("y", a).mv(5 * math.sin(math.radians(a)), 0, -6 + 4 * math.cos(math.radians(a))))
    e = ease(u)
    return dict(scene=s, cam=Cam(lerp((-4.0, 1.0, 6.0), (2.0, 1.8, 5.0), e), (0, 3.0, -6), 48, aperture=0.04),
                glow=[PR.beam((x, 16, -40), (0, -0.4, 1), 40, 7, (255, 200, 150), 0.045) for x in (-10, 6)], center=(0, 0, -6))

def sh_name(u, t, dt):
    """JOKE 'the company put a name on it.': Yub slaps a HELLO my name is JEEP WAVE sticker onto the giant hand. Proud."""
    k = ease(min(1, u * 3))
    h = yub("proud", la=(75 * k, 10, 10), ra=(0, 8, 10)).rot("y", -25).mv(1.5, 0, -0.3)
    sx, sy, _ = shake(t, 0.03 if 0.3 < u < 0.4 else 0)
    return dict(scene=desert(t, 0, odd=False) + [giant_hand(t, k).mv(0, 0, -1.4), h], cam=Cam((2.4 + sx, 2.0 + sy, 4.8), (0.4, 2.1, -1.0), 48, aperture=0.08), center=(0, 0, 0))

def sh_brands(u, t, dt):
    """'Should every car brand have a wave?': Yub at the roadside waves hopefully at a Tesla, a Hyundai and a Chevrolet passing by."""
    a = 150 + 20 * math.sin(t * 15)
    h = yub("grin", ra=(0, a, 20), wave="r", head=(-30, 0, 0)).rot("y", 35).mv(3.4, 0, -3.8)
    lst = [C.model3(), C.ioniq5n(lights=0.6), C.blazer_ev(lights=0.6)]
    cars_ = [c.mv(-24 + 26 * u + i * 7, 0, -1.2) for i, c in enumerate(lst)]
    return dict(scene=desert(t, 0, cow_x=-10) + [h] + cars_, cam=Cam((7.4, 1.7, -6.2), (0.5, 1.3, -1.8), 48, aperture=0.05), center=(2, 0, -2))

def sh_question(u, t, dt):
    """'Yes, or no?': Yub between a green YES neon and a red NO neon, the yellow Jeep behind, sun setting."""
    up = t > ws(8, 7)
    h = yub("smug" if up else "smile", la=(25, 55, 80), ra=(25, 55, 80), head=(0, 0, 8 * math.sin(t * 4)))
    y = PR.neon_sign("YES", 0.8, 0.4, (60, 230, 110), 2.8).mv(-0.95, 1.55, 0.1); n = PR.neon_sign("NO", 0.8, 0.4, (255, 50, 60), 2.8).mv(0.95, 1.55, 0.1)
    return dict(scene=desert(t, 0, cow_x=-4) + [h, y, n, C.wrangler(C.JEEP_YELLOW).rot("y", 70).mv(-2.6, 0, -3.6)], cam=Cam((0, 1.45, 5.8 - 0.3 * u), (0, 1.3, 0), 46, aperture=0.12),
                env=env(points=[((-0.95, 1.6, 0.6), (60, 230, 110), 1.0, 1.2), ((0.95, 1.6, 0.6), (255, 50, 60), 1.0, 1.2)]), center=(0, 0, 0))

SHOTS = [
    (0.0, sh_hook, "golden hour: Yub cruises a yellow Wrangler (cow in a lawn chair by the road)"),
    (ws(0, 4) - 0.05, sh_secret, "macro: eyebrow up, eyes darting"),
    (ws(1, 0), sh_pass, "red Wrangler approaches"),
    (ws(1, 5) - 0.05, sh_wavemacro, "slow-mo macro of the other driver's wave"),
    (ws(1, 8) + 0.05, sh_panic, "JOKE: Yub panics"),
    (ws(2, 4), sh_convoy, "drone orbit: five Wranglers, everyone waving"),
    (ws(3, 0), sh_ww2, "WWII: dusty convoy of Willys MBs, light shafts"),
    (ws(3, 10), sh_willys, "macro over the white star, soldiers exchange a wave"),
    (ws(4, 0), sh_rules, "glowing rulebook: all pages blank"),
    (ws(4, 5), sh_unwritten, "slow-mo pass: glowing arc from the other driver's hand to Yub"),
    (ws(4, 16), sh_waveback, "Yub waves back, arc bursts into sparks"),
    (ws(5, 0), sh_tesla, "Yub waves at a Tesla Model 3"),
    (ws(5, 5) - 0.05, sh_nothing, "JOKE: nothing; tumbleweed; wave sinks, deadpan"),
    (ws(6, 0), sh_program, "holographic JEEP WAVE emblem rises from the grille"),
    (ws(7, 0), sh_popular, "giant waving-hand monument at sunset"),
    (ws(7, 5) - 0.05, sh_name, "JOKE: Yub slaps a HELLO my name is JEEP WAVE sticker on it"),
    (ws(8, 0), sh_brands, "Yub waves at a Tesla, a Hyundai and a Chevrolet"),
    (ws(8, 7) - 0.1, sh_question, "Yub between YES and NO neons"),
]
SFX = [(ws(1, 5), "whoosh", 0.4), (ws(1, 8) + 0.1, "honk", 0.5), (ws(1, 8) + 0.4, "boing", 0.7), (ws(2, 4), "whoosh", 0.4),
       (ws(3, 0), "vroom", 0.4), (ws(4, 0) + 0.4, "slide_down", 0.3), (ws(4, 2), "crickets", 0.7), (ws(4, 5) + 0.3, "sparkle", 0.6),
       (ws(4, 16), "ding", 0.6), (ws(4, 16) + 0.1, "sparkle", 0.6), (ws(5, 0) + 0.2, "whoosh", 0.4), (ws(5, 5), "crickets", 1.0),
       (ws(6, 0) + 0.3, "sparkle", 0.6), (ws(7, 0), "confetti", 0.5), (ws(7, 5) + 0.3, "stamp", 0.8), (ws(7, 10) + 0.2, "rimshot", 0.8),
       (ws(8, 0), "honk", 0.35), (ws(8, 7), "pop", 0.5), (ws(8, 9), "pop", 0.5)]

if __name__ == "__main__": E.main(V)
