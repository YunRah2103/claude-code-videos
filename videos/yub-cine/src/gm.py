"""gm_carplay: cinematic low-poly short. Blue-hour Chevrolet dealership, neon GM sign, glowing breakdown.
Oddity (never mentioned): an astronaut in a full spacesuit lounging on a deck chair under a beach umbrella on the forecourt."""
import math, sys
import numpy as np
from PIL import Image, ImageDraw
from geo import (P, cat, quad, box, cbox, bbox, cb, lathe, cyl, superellipsoid, sphere, capsule, tiles, panel, word_tex, font, rgb, tex, Cam,
                 MATTE, PAINT, GLASS, CHROME, SATIN, RUBBER, GLOW, SCREEN, T_DISC)
from render3d import Env
import cars3d as C
import props3d as PR
import engine3d as E
from engine3d import ease, lerp, shake
from yub import yub

NAME = "gm"
V = E.Video(sys.modules[__name__]); ws = V.ws; DUR = V.dur
HOOK = "GM wants your car to forget your iPhone."
ACCENT = (40, 130, 255)
HOT = {"nothing", "2023", "carplay", "android", "auto", "evs", "ceo", "gas", "2028", "better", "no", "thanks", "nine", "ten", "forty-six",
       "percent", "must-have", "half", "how", "about", "yes"}
TOPS = [(ws(2, 0), ws(3, 0), "2023: most new GM EVs"), (ws(3, 0), ws(4, 0), "Next: gas cars, ~2028"), (ws(6, 0), ws(7, 0), "Cars.com data")]
ONSCREEN = ["gm logo", "CHEVROLET + bowtie", "CarPlay icon", "Android Auto icon", "2023", "2028", "No thanks.", "9 in 10", "46%", "NO", "YES"]
ODDITY = "an astronaut in a full spacesuit lounging on a deck chair under a beach umbrella on the dealership forecourt"
CRASH = [ws(1, 0), ws(7, 9)]
MUSIC_UNDER_DB = 3.5

DUSK = dict(sky_top=(18, 34, 110), sky_hor=(255, 130, 120), ground=(40, 40, 60), sun_dir=(-0.75, 0.12, -0.55), sun=(255, 150, 110), sun_i=1.6,
            amb_i=0.85, fog=(35, 140), fog_col=(150, 90, 130), exposure=1.15, stars=0.25, bloom=0.85, sun_disc=True, sat=1.18, shadow_size=18)
LOT_LIGHTS = [((-6, 5.5, -4), (200, 220, 255), 2.2, 6), ((6, 5.5, -4), (200, 220, 255), 2.2, 6), ((0, 3, -11), (120, 180, 255), 3.0, 6)]
def env(points=(), **kw):
    d = dict(DUSK); d.update(kw); return Env(points=list(LOT_LIGHTS) + list(points), **d)
ENV = env()

# ---------------------------------------------------------------- textures
def _app(kind, n=128, x=False):
    im = Image.new("RGB", (n * 2, n * 2), (245, 246, 250)); d = ImageDraw.Draw(im); N = n * 2
    if kind == "carplay":
        for y in range(N): d.line((0, y, N, y), fill=(int(40 + 60 * y / N), int(205 - 70 * y / N), int(120 + 110 * y / N)))
        d.rounded_rectangle((36, 36, N - 36, N - 36), 44, outline=(255, 255, 255), width=14); d.polygon([(104, 84), (104, 172), (176, 128)], fill=(255, 255, 255))
    else:
        d.polygon([(128, 36), (220, 208), (176, 208), (128, 116), (80, 208), (36, 208)], fill=(60, 170, 80)); d.polygon([(128, 116), (176, 208), (80, 208)], fill=(66, 133, 244))
    if x: d.line((20, 20, N - 20, N - 20), fill=(230, 30, 40), width=28); d.line((N - 20, 20, 20, N - 20), fill=(230, 30, 40), width=28)
    return tex(im.resize((n, n), Image.LANCZOS))
T_CP, T_AA, T_CPX, T_AAX = _app("carplay"), _app("android"), _app("carplay", x=True), _app("android", x=True)
def _scr(kind):
    def dr(d, w, h):
        d.rectangle((0, 0, w, 30), fill=(24, 34, 56)); d.text((14, 15), "12:00", font=font(20, "bold"), fill=(220, 226, 236), anchor="lm")
        if kind == "home":
            for i, (lab, c) in enumerate((("Maps", (60, 170, 90)), ("Music", (230, 80, 90)), ("Phone", (60, 140, 230)), ("Climate", (240, 170, 40)))):
                x = 30 + i * 120; d.rounded_rectangle((x, 70, x + 92, 162), 18, fill=c); d.text((x + 46, 190), lab, font=font(20, "bold"), fill=(230, 236, 244), anchor="mm")
        elif kind == "wait":
            d.text((w / 2, 110), "Searching for phone...", font=font(34, "bold"), fill=(240, 244, 250), anchor="mm"); d.text((w / 2, 175), "...", font=font(60), fill=(140, 150, 175), anchor="mm")
        elif kind == "nothanks":
            d.ellipse((w / 2 - 52, 40, w / 2 + 52, 144), fill=(60, 140, 230)); d.line((w / 2 - 24, 82, w / 2 - 8, 82), fill=(255, 255, 255), width=8)
            d.line((w / 2 + 8, 82, w / 2 + 24, 82), fill=(255, 255, 255), width=8); d.line((w / 2 - 18, 116, w / 2 + 18, 116), fill=(255, 255, 255), width=6)
            d.text((w / 2, 200), "No thanks.", font=font(52), fill=(255, 255, 255), anchor="mm")
        elif kind == "integrated":
            d.rectangle((20, 50, w * 0.62, h - 20), fill=(40, 70, 60)); d.line((40, h - 40, 140, 150, 220, 170, 290, 80), fill=(80, 200, 255), width=8)
            d.rounded_rectangle((w * 0.66, 50, w - 20, 130), 12, fill=(40, 50, 80)); d.rounded_rectangle((w * 0.66, 145, w - 20, h - 20), 12, fill=(60, 40, 70))
    return PR.screen_tex(dr)
S_HOME, S_WAIT, S_NOTHX, S_INTEG = _scr("home"), _scr("wait"), _scr("nothanks"), _scr("integrated")
def _phone_tex(kind):
    def dr(d, w, h):
        if kind == "carplay":
            for y in range(h): d.line((0, y, w, y), fill=(20 + y // 12, 30 + y // 10, 70 + y // 6))
            d.rounded_rectangle((w / 2 - 70, h / 2 - 70, w / 2 + 70, h / 2 + 70), 34, fill=(60, 180, 140)); d.polygon([(w / 2 - 22, h / 2 - 34), (w / 2 - 22, h / 2 + 34), (w / 2 + 34, h / 2)], fill=(255, 255, 255))
            d.text((w / 2, h / 2 + 120), "CarPlay", font=font(34, "bold"), fill=(255, 255, 255), anchor="mm")
        else:
            d.text((w / 2, h / 2), "Connecting...", font=font(30, "bold"), fill=(220, 226, 240), anchor="mm")
    return PR.screen_tex(dr, 256, 512, (10, 12, 24))
T_PH_CP, T_PH_WAIT = _phone_tex("carplay"), _phone_tex("wait")
T_CHEVY = word_tex("CHEVROLET", 512, 96, (255, 255, 255), (10, 12, 20), 70)
T_9 = word_tex("9 / 10", 256, 112, (255, 255, 255), (10, 30, 70), 80)
T_GMCHIP = C.T_GM

def phone(t=0.0, scr=None):
    s = T_PH_CP if scr is None else scr
    return cat([bbox(-0.038, 0, -0.008, 0.038, 0.16, 0.008, (30, 30, 36), b=0.008, m=PAINT),
                box(-0.034, 0.006, 0.0081, 0.034, 0.154, 0.0085, (255, 255, 255), texs={"f": s}, e=1.6, m=SCREEN),
                cb(-0.02, 0.13, -0.0095, 0.03, 0.03, 0.004, (60, 60, 66), b=0.004, m=GLASS)])

# ---------------------------------------------------------------- sets
def astronaut(t):
    suit = (236, 236, 240)
    body = cat([superellipsoid(0.2, 0.26, 0.15, 0.7, 0.7, 16, 10, suit, SATIN).rot("z", 55).mv(-0.05, 0.55, 0),
                sphere(0.17, 18, 12, suit, SATIN).mv(-0.3, 0.86, 0), superellipsoid(0.04, 0.1, 0.12, 0.6, 0.8, 12, 8, (230, 170, 40), CHROME).mv(-0.17, 0.86, 0),
                capsule((0.12, 0.42, 0.1), (0.5, 0.35, 0.1), 0.07, 10, suit, SATIN), capsule((0.12, 0.42, -0.1), (0.5, 0.35, -0.1), 0.07, 10, suit, SATIN),
                capsule((0.5, 0.35, 0.1), (0.55, 0.05, 0.1), 0.065, 10, suit, SATIN), capsule((0.5, 0.35, -0.1), (0.55, 0.05, -0.1), 0.065, 10, suit, SATIN),
                capsule((-0.12, 0.62, 0.18), (0.08, 0.62 + 0.04 * math.sin(t * 2), 0.3), 0.055, 10, suit, SATIN),
                cyl(0.035, 0.045, 0.12, 10, (255, 120, 170), PAINT).mv(0.1, 0.62 + 0.04 * math.sin(t * 2), 0.32)])
    chair = cat([bbox(-0.5, 0.25, -0.3, 0.6, 0.3, 0.3, (240, 120, 40), b=0.02).rot("z", 8), bbox(-0.55, 0.3, -0.3, -0.45, 1.0, 0.3, (250, 250, 250), b=0.02).rot("z", 35, (-0.5, 0.3, 0))])
    umb = cat([cyl(0.025, 0.025, 2.0, 6, (230, 230, 230))] + [P([(0, 2.1, 0), (1.1 * math.cos(a0), 1.75, 1.1 * math.sin(a0)), (1.1 * math.cos(a1), 1.75, 1.1 * math.sin(a1))],
               (240, 60, 70) if i % 2 else (255, 240, 220), m=SATIN) for i, (a0, a1) in enumerate((2 * math.pi * k / 10, 2 * math.pi * (k + 1) / 10) for k in range(10))]).mv(-0.9, 0, 0)
    return cat([chair, body, umb])

def dealer(t, odd=True):
    s = [tiles(-40, -40, 40, 30, -0.01, 10.0, -1, (40, 70, 50)), tiles(-24, -14, 24, 12, 0.0, 6.0, -1, (70, 72, 84), m=SATIN)]
    s += [box(x, 0.004, -7, x + 0.1, 0.012, 7, (230, 230, 240)) for x in np.arange(-12, 13, 3.0)]
    s += [bbox(-18, 0, -34, 18, 5, -24, (236, 240, 248), b=0.2), box(-16, 0.3, -24.02, 16, 3.6, -23.98, (180, 220, 255), e=1.1, m=GLASS),
          bbox(-18, 5, -34, 18, 5.4, -23.8, (30, 110, 230), b=0.1, e=0.5), box(-4, 3.75, -23.77, 4, 4.75, -23.72, (255, 255, 255), texs={"f": T_CHEVY}, e=1.6),
          box(4.4, 3.8, -23.77, 6.2, 4.7, -23.72, (255, 255, 255), texs={"f": C.T_BOWTIE}, e=1.2)]
    pylon = cat([cyl(0.2, 0.2, 1.6, 10, (200, 204, 214), CHROME), bbox(-1.1, 1.6, -0.16, 1.1, 3.8, 0.16, (240, 240, 244), b=0.08),
                 box(-1.0, 1.7, 0.161, 1.0, 3.7, 0.17, (255, 255, 255), texs={"f": C.T_GM}, e=1.4)])
    s.append(pylon.mv(-6.5, 0, -10))
    for x in (-19, 17, 21): s.append(cat([cyl(0.14, 0.1, 4.2, 8, (150, 110, 80))] + [P([(0, 4.3, 0), (1.5 * math.cos(a), 3.7, 1.5 * math.sin(a)), (1.1 * math.cos(a + 0.35), 4.0, 1.1 * math.sin(a + 0.35))], (40, 140, 70), m=SATIN) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)]).mv(x, 0, -9))
    s += [cat([cyl(0.04, 0.04, 4.0, 6, (220, 220, 220), CHROME), box(0, 3.2, -0.01, 1.0, 3.9, 0.01, c, m=SATIN)]).mv(x, 0, -12.5) for x, c in ((-3, (230, 40, 50)), (0, (40, 110, 230)), (3, (250, 200, 40)))]
    if odd: s.append(astronaut(t).rot("y", 200).sc(1.15).mv(10, 0, -5.5))
    return s
GL = [PR.beam((-6, 5.6, -4), (0.1, -1, 0.1), 6.5, 2.4, (200, 220, 255), 0.07), PR.beam((6, 5.6, -4), (-0.1, -1, 0.1), 6.5, 2.4, (200, 220, 255), 0.07)]
POLES = [cat([cyl(0.08, 0.06, 5.6, 8, (60, 62, 70)), cb(0, 5.65, 0, 0.6, 0.12, 0.3, (40, 40, 46), b=0.03), cb(0, 5.58, 0, 0.5, 0.03, 0.24, (240, 245, 255), b=0.01, e=4)]).mv(x, 0, -4) for x in (-6, 6)]
SPR = [((x, 5.58, -4), (220, 235, 255), 0.4, 1.2) for x in (-6, 6)]
def dglow(): return list(GL)
def blazer(t=0.0, x=0.0, z=0.0, yaw=0.0, col=C.CHEVY_RED, lights=1.0): return C.blazer_ev(col, -t * 0, lights).rot("y", yaw).mv(x, 0, z)

def cockpit(screen, t, expr="smile", la=(55, 4, 40), ra=(55, 4, 40), held=None, head=(0, 0, 0), **kw):
    hw = 0.95
    dash = [bbox(0.55, 0.75, -hw, 1.3, 1.12, hw, (236, 236, 240), b=0.06, m=SATIN), bbox(0.6, 1.0, -0.95, 1.0, 1.14, 0.95, (24, 24, 28), b=0.03),
            box(0.5, 1.1, -0.36, 0.55, 1.5, 0.42, (255, 255, 255), texs={"l": screen}, e=1.6, m=SCREEN), bbox(0.54, 1.08, -0.38, 0.6, 1.52, 0.44, (14, 14, 16), b=0.015),
            bbox(-1.5, 0.2, -hw, 1.3, 0.42, hw, (40, 40, 48), b=0.03), bbox(-1.4, 0.4, -hw - 0.06, 1.3, 1.16, -hw, C.CHEVY_RED, b=0.03, m=PAINT),
            bbox(-0.3, 0.42, -0.12, 0.6, 0.76, 0.12, (30, 30, 36), b=0.04), cb(0.45, 0.8, 0.0, 0.04, 0.03, 0.05, (10, 10, 12), b=0.008),
            cb(1.3, 1.4, 0, 0.04, 0.5, 1.9, (60, 70, 110), b=0.01, m=GLASS)]
    seat = [bbox(-0.9, 0.55, -0.7, -0.35, 0.75, -0.15, (40, 40, 46), b=0.05), bbox(-0.98, 0.75, -0.7, -0.8, 1.58, -0.15, (40, 40, 46), b=0.05)]
    sw = cat([lathe([(0.17, -0.015), (0.19, 0.0), (0.17, 0.015)], 24, (24, 24, 28), RUBBER), cb(0, 0, 0, 0.3, 0.03, 0.05, (24, 24, 28), b=0.01),
              box(-0.04, 0.025, -0.06, 0.04, 0.03, 0.06, (255, 255, 255), texs={"t": C.T_BOWTIE})]).rot("z", 70).mv(0.22, 1.16, -0.425)
    h = yub(expr, sit=True, la=la, ra=ra, head=head, held=held, **kw).rot("y", 90).mv(-0.62, 0.25, -0.425)
    return [*dash, *seat, sw, h]
CAB = [((0.3, 1.35, 0.0), (140, 190, 255), 1.0, 0.9), ((-0.3, 1.9, 0.4), (255, 220, 200), 0.6, 2.0)]
def SCREEN_CAM(f=None): return Cam((-0.62, 1.48, 0.62), (0.52, 1.12, 0.03), 44, aperture=0.2, focus=f)
def FACE_CAM(): return Cam((1.1, 1.64, 0.35), (-0.62, 1.56, -0.42), 46, aperture=0.12)
def outside(t, v=0.0): return dealer(t, odd=False) + POLES

# ---------------------------------------------------------------- shots
def sh_hook(u, t, dt):
    """Blue hour at a Chevrolet dealership; red Blazer EV glowing; Yub (LTN cap) holds his iPhone up proudly."""
    h = yub("proud", ra=(150, 15, 30), held=phone(t), head=(10, 0, 0)).rot("y", -15).mv(1.1, 0, 1.2)
    e = ease(u)
    return dict(scene=dealer(t) + POLES + [blazer(t, -1.0, -1.0, -30), h], cam=Cam(lerp((2.8, 1.2, 6.2), (2.3, 1.45, 5.3), e), (0.0, 1.6, -0.5), 48, aperture=0.06),
                glow=dglow(), sprites=SPR + [((1.35, 2.7, 1.25), (120, 200, 255), 0.06, 1.2)], center=(0, 0, 0))

def sh_iphone(u, t, dt):
    """Macro: the iPhone's CarPlay screen glowing in his hand; the car's dash out of focus behind."""
    ph = phone(t).sc(2.0).rot("y", -20).mv(-0.1, 1.2, 0.3)
    sc = cockpit(S_HOME, t, "smile")
    return dict(scene=sc + [ph], cam=Cam((0.35, 1.45, 0.95), (-0.08, 1.37, 0.3), 36, aperture=0.6, focus=0.75), env=env(points=CAB), glow=[], sprites=[], center=(0, 1, 0))

def sh_plug(u, t, dt):
    """'Plug your phone into a new GM EV': macro on the console - the cable clicks into the port, light races along the cord."""
    k = ease(min(1, u * 1.6))
    sc = cockpit(S_WAIT, t, "smile", ra=(70, 30, 60), held=phone(t, T_PH_WAIT))
    port = cat([cb(0.5, 0.8, 0.0, 0.03, 0.05, 0.09, (10, 10, 12), b=0.008), lathe([(0.035, 0), (0.04, 0.004), (0.035, 0.008)], 16, (90, 200, 255), MATTE, e=2.5 * k).rot("z", -90).mv(0.485, 0.8, 0.0)])
    plug = cb(0.5 - 0.06 - 0.12 * (1 - k), 0.8, 0.0, 0.07, 0.035, 0.05, (230, 230, 236), b=0.01, m=SATIN)
    cable = PR.flow([(0.44 - 0.12 * (1 - k), 0.8, 0.0), (0.1, 0.82, 0.12), (-0.15, 1.0, 0.05)], t, (90, 200, 255), 0.014, 2.0, 2.2 * k + 0.4)
    return dict(scene=sc + [port, plug, cable], cam=Cam((0.12, 0.98, 0.42), (0.47, 0.8, 0.0), 38, aperture=0.5, focus=0.55),
                env=env(points=CAB + [((0.45, 0.95, 0.15), (140, 200, 255), 1.4, 0.6)]), glow=[], sprites=[((0.485, 0.8, 0.0), (120, 210, 255), 0.03, 1.5 * k)], center=(0, 1, 0))

def sh_nothing(u, t, dt):
    """JOKE 'and... nothing.': the screen stays on its own home page; crickets; Yub stares, deadpan."""
    sc = cockpit(S_HOME, t, "deadpan" if u > 0.4 else "smile", ra=(70, 30, 60), held=phone(t, T_PH_WAIT))
    return dict(scene=sc, cam=SCREEN_CAM() if u < 0.45 else FACE_CAM(), env=env(points=CAB), glow=[], sprites=[], center=(0, 1, 0))

def holo_text(txt, h=1.0, col=(80, 190, 255), e=2.2):
    w = h * max(1.6, 0.62 * len(txt))
    return PR.glow_quad(w, h, col, e, word_tex(txt, int(256 * w / h), 256, (255, 255, 255), (0, 0, 0), 190))

def sh_2023(u, t, dt):
    """'Starting in 2023': a holographic 2023 hangs over a row of new Chevrolet EVs on the lot."""
    s = outside(t)
    for i, c in enumerate(((170, 18, 28), (30, 90, 200), (236, 238, 242), (40, 40, 46))):
        s.append(blazer(t, -5 + 3.3 * i, -3, -90, c))
    e = ease(u)
    return dict(scene=s, cam=Cam(lerp((7.5, 2.6, 6.0), (5.0, 2.2, 5.5), e), (-0.5, 1.6, -3), 46, aperture=0.05),
                glow=dglow() + [holo_text("2023", 1.1).mv(2.6, 2.6, -2.5)], sprites=SPR, center=(0, 0, -3))

def _tile(tid, s=0.7): return box(-s / 2, -s / 2, -0.02, s / 2, s / 2, 0.02, (255, 255, 255), texs={"f": tid, "b": tid}, e=1.3, m=SCREEN)
def sh_apps(u, t, dt):
    """'stopped offering CarPlay and Android Auto': glowing CarPlay and Android Auto tiles hover over the Blazer EV, get X'd, and shatter."""
    k = u > 0.45; br = max(0, (u - 0.6) * 2.5)
    tiles_ = []
    for j, (a, ax) in enumerate(((T_CP, T_CPX), (T_AA, T_AAX))):
        x0 = -0.7 + 1.4 * j
        if br <= 0: tiles_.append(_tile(ax if k else a).rot("y", 10 * math.sin(t * 2 + j)).mv(x0, 2.6 + 0.05 * math.sin(t * 3 + j), 0))
        else:
            for q in range(9):
                qx, qy = (q % 3 - 1) * 0.24, (q // 3 - 1) * 0.24
                piece = box(-0.11, -0.11, -0.02, 0.11, 0.11, 0.02, (255, 255, 255), texs={"f": ax}, e=1.2 * (1 - br), m=SCREEN)
                piece.uv[:] = piece.uv * (1 / 3) + np.float32([(q % 3) / 3, 1 - (q // 3 + 1) / 3])
                tiles_.append(piece.rot("z", 200 * br * (q - 4) / 4).mv(x0 + qx * (1 + br * 2), 2.6 + qy - br * br * 2.2, br * (q - 4) * 0.1))
    return dict(scene=outside(t) + [blazer(t, 0, 0, -20)] + tiles_, cam=Cam((2.2, 2.2, 5.6), (0.0, 2.0, 0), 46, aperture=0.08),
                glow=dglow(), sprites=SPR, env=env(points=[((0, 2.6, 1.0), (90, 200, 160), 1.2, 2.0)]), center=(0, 0, 0))

def gas_pump(e=1.0):
    return cat([bbox(-0.35, 0, -0.25, 0.35, 1.7, 0.25, (220, 40, 40), b=0.05, m=PAINT), box(-0.25, 1.05, 0.251, 0.25, 1.45, 0.26, (200, 230, 255), e=1.2 * e, m=SCREEN),
                capsule((0.35, 1.2, 0), (0.55, 0.7, 0.1), 0.03, 8, (30, 30, 30)), cb(0.55, 0.62, 0.1, 0.08, 0.16, 0.06, (40, 40, 44), b=0.01)])

def sh_gas(u, t, dt):
    """'gas cars should lose them too': a gas pump beside a dark-grey Chevy; the CarPlay tile above flickers and fades out."""
    fl = max(0.0, 1 - u * 1.3) * (0.6 + 0.4 * (math.sin(t * 40) > 0))
    tile = box(-0.35, -0.35, -0.02, 0.35, 0.35, 0.02, (255, 255, 255), texs={"f": T_CP}, e=1.3 * fl, m=SCREEN).mv(0.0, 2.5, 0)
    s = outside(t) + [blazer(t, 0, 0, -25, (70, 72, 80)), gas_pump().rot("y", -20).mv(1.9, 0, 1.4), tile]
    return dict(scene=s, cam=Cam((3.0, 1.9, 6.2), (0.6, 1.6, 0), 46, aperture=0.06), glow=dglow(), sprites=SPR, center=(0, 0, 0))

def sh_chip(u, t, dt):
    """'with a new computer platform around 2028': macro of a glowing circuit board; traces light up and race into a central chip; holo 2028."""
    pcb = bbox(-1.2, -0.04, -0.8, 1.2, 0.0, 0.8, (14, 50, 36), b=0.01, m=SATIN)
    chip = cat([bbox(-0.28, 0.0, -0.28, 0.28, 0.08, 0.28, (24, 24, 28), b=0.02, m=SATIN), box(-0.2, 0.081, -0.2, 0.2, 0.082, 0.2, (255, 255, 255), texs={"t": C.T_GM}, e=0.6)])
    traces = []
    for i in range(10):
        a = 2 * math.pi * i / 10; r0, r1 = 0.32, 1.1
        traces.append(PR.flow([(r1 * math.cos(a), 0.01, r1 * math.sin(a) * 0.7), (r0 * 1.6 * math.cos(a), 0.01, r1 * 0.5 * math.sin(a) * 0.7), (r0 * math.cos(a), 0.01, r0 * math.sin(a))],
                              t + i * 0.13, (80, 220, 255) if i % 2 else (255, 190, 70), 0.012, 2.6, 2.2, 14))
    e = ease(u)
    return dict(scene=[pcb, chip] + traces, cam=Cam(lerp((1.6, 1.4, 1.8), (0.9, 1.0, 1.2), e), (0, 0.05, 0), 44, aperture=0.35, focus=1.6 - 0.4 * e),
                glow=[holo_text("2028", 0.32).rot("x", -25).mv(0, 0.32, 0.55)], env=env(fog=None, stars=0.0, points=[((0, 0.8, 0), (90, 200, 255), 1.4, 1.0)]),
                sprites=[((0, 0.1, 0), (120, 220, 255), 0.25, 1.0)], center=(0, 0, 0))

def sh_better(u, t, dt):
    """'a better, more integrated experience': the big Chevy screen shows maps and apps, sparkles; Yub side-eyes it, unconvinced."""
    sp = [sphere(0.012, 6, 4, (255, 240, 180)).glow(4).mv(0.45, 1.15 + 0.35 * ((t * 0.7 + i * 0.13) % 1), -0.3 + 0.08 * i) for i in range(9)]
    sc = cockpit(S_INTEG, t, "smug" if u < 0.5 else "deadpan", look="r", head=(25, 0, 0))
    return dict(scene=sc + sp, cam=Cam((-0.35, 1.75, 0.95), (0.35, 1.28, -0.2), 48, aperture=0.12), env=env(points=CAB), glow=[], sprites=[], center=(0, 1, 0))

def sh_yourphone(u, t, dt):
    """'Your phone?': Yub holds the phone up to the screen, hopeful, eyebrows up."""
    sc = cockpit(S_WAIT, t, "smile", ra=(98, 20, 30), held=phone(t), head=(0, 6, 0))
    return dict(scene=sc, cam=SCREEN_CAM(), env=env(points=CAB), glow=[], sprites=[], center=(0, 1, 0))

def sh_nothanks(u, t, dt):
    """JOKE 'No thanks.': the screen's snooty butler face says No thanks; the phone recoils; Yub cringes."""
    k = ease(min(1, u * 2.5))
    sc = cockpit(S_NOTHX, t, "cringe" if u > 0.35 else "shock", ra=(98 - 50 * k, 20 + 25 * k, 30), held=phone(t), head=(0, -8 * k, 0))
    return dict(scene=sc, cam=SCREEN_CAM() if u < 0.55 else FACE_CAM(), env=env(points=CAB + [((0.4, 1.3, 0.0), (60, 140, 230), 1.0, 1.0)]), glow=[], sprites=[], center=(0, 1, 0))

FACES = {}
def shopper(i, t, up=True):
    from yub import face as _f
    skins = [(232, 190, 150), (150, 100, 70), (205, 160, 120), (118, 78, 54), (236, 196, 170)]
    tops = [(230, 60, 60), (60, 120, 230), (250, 200, 40), (60, 190, 90), (200, 90, 200), (240, 140, 40), (40, 200, 200)]
    sk = skins[i % 5]; top = tops[i % 7]
    body = cat([capsule((0.08, 0.1, 0), (0.08, 0.86, 0), 0.07, 10, (40, 44, 60)), capsule((-0.08, 0.1, 0), (-0.08, 0.86, 0), 0.07, 10, (40, 44, 60)),
                superellipsoid(0.18, 0.28, 0.11, 0.5, 0.6, 16, 12, top, MATTE).mv(0, 1.15, 0), sphere(0.13, 16, 12, sk, MATTE).mv(0, 1.58, 0),
                superellipsoid(0.14, 0.07, 0.14, 0.8, 0.8, 14, 8, [(40, 30, 24), (20, 20, 20), (200, 180, 140), (110, 70, 30)][i % 4], MATTE).mv(0, 1.68, -0.01),
                *[sphere(0.018, 6, 4, (20, 20, 24)).mv(sx, 1.6, 0.12) for sx in (-0.045, 0.045)],
                capsule((-0.2, 1.36, 0), (-0.24, 0.92, 0.02), 0.045, 8, sk)])
    arm = capsule((0.2, 1.36, 0), (0.28, 1.86, 0.05), 0.045, 8, sk) if up else capsule((0.2, 1.36, 0), (0.24, 0.92, 0.02), 0.045, 8, sk)
    parts = [body, arm]
    if up: parts.append(phone(t).sc(1.3).mv(0.28, 1.86, 0.06))
    return cat(parts)

def sh_9in10(u, t, dt):
    """'nearly nine in ten shoppers value smartphone integration': ten shoppers; nine raise glowing phones one by one; a holo 9 / 10."""
    n_up = min(9, int(u * 12))
    s = outside(t) + [shopper(i, t, i < n_up + (i > 6) and i != 6).mv(-3.6 + 0.8 * i, 0, 0) for i in range(10)]
    s.append(PR.neon_sign("9 in 10", 1.5, 0.5, (80, 190, 255), 2.6).mv(0, 2.45, 0.6))
    return dict(scene=s, cam=Cam((0.0, 2.0, 7.4), (0, 1.6, 0), 46, aperture=0.05), glow=dglow(),
                sprites=SPR, center=(0, 0, 0))

def sh_46(u, t, dt):
    """'forty-six percent call it a must-have': a glowing pie; the 46% wedge lifts out, red and bright; Yub points at it, shocked."""
    k = ease(min(1, u * 1.8))
    segs = []
    n = 60
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        hot = i < int(n * 0.46)
        r = 1.0; h = 0.18 + (0.25 * k if hot else 0)
        off = np.float32([math.cos(math.pi * 0.46), 0, math.sin(math.pi * 0.46)]) * (0.15 * k if hot else 0)
        col = (255, 60, 70) if hot else (60, 80, 130)
        tri = P([(0, h, 0), (r * math.cos(a0), h, r * math.sin(a0)), (r * math.cos(a1), h, r * math.sin(a1)),
                 (r * math.cos(a0), 0, r * math.sin(a0)), (r * math.cos(a1), 0, r * math.sin(a1)), (r * math.cos(a1), h, r * math.sin(a1)),
                 (r * math.cos(a0), 0, r * math.sin(a0)), (r * math.cos(a1), h, r * math.sin(a1)), (r * math.cos(a0), h, r * math.sin(a0))], col, m=PAINT, e=(0.6 * k if hot else 0.05))
        segs.append(tri.mv(*off))
    pie = cat(segs).mv(0, 0.6, 0)
    h = yub("shock", ra=(80, 40, 30), la=(30, 30, 80)).rot("y", 40).mv(-1.6, 0, 0.6)
    return dict(scene=outside(t) + [pie, bbox(-1.1, 0, -1.1, 1.1, 0.6, 1.1, (30, 30, 40), b=0.05), h], cam=Cam((0.6, 2.4, 4.2), (-0.2, 1.0, 0), 46, aperture=0.08),
                glow=dglow() + [holo_text("46%", 0.55, (255, 90, 100)).mv(0.2, 1.55, 0.2)], sprites=SPR, env=env(points=[((0, 1.6, 0.8), (255, 80, 90), 1.4, 1.5)]), center=(0, 0, 0))

def sh_crowd(u, t, dt):
    """'Nearly half of shoppers say they must have it': a crowd outside the dealership, phones up, bouncing."""
    s = outside(t) + [shopper(i, t, i % 2 == 0).mv(-5 + (i % 7) * 1.5 + 0.3 * (i // 7), 0.05 * abs(math.sin(t * 7 + i)), -3.0 - 1.4 * (i // 7)) for i in range(14)]
    return dict(scene=s, cam=Cam((2.4, 2.4, 5.0), (-0.8, 1.7, -4), 46, aperture=0.06), glow=dglow(), sprites=SPR, center=(0, 0, -3))

def sh_no(u, t, dt):
    """JOKE 'GM says: how about no.': a giant red NO button under the GM sign gets slammed; red light floods the lot; Yub facepalms."""
    press = max(0.0, math.sin(min(1, max(0, (u - 0.4) / 0.25)) * math.pi))
    btn = cat([cyl(0.7, 0.75, 0.35, 32, (40, 40, 46), SATIN), cyl(0.55, 0.55, 0.22 - 0.15 * press, 32, (230, 30, 40), PAINT, e=0.4 + 1.2 * press).mv(0, 0.35, 0),
               box(-0.34, 0.575 - 0.15 * press, -0.18, 0.34, 0.58 - 0.15 * press, 0.18, (255, 255, 255), texs={"t": word_tex("NO", 128, 64, (255, 255, 255), (230, 30, 40), 50)}, e=1.2)]).mv(-0.6, 0, -1.2)
    h = yub("cringe", la=(135, 10, 150) if u > 0.5 else (0, 8, 10), head=(0, 12 if u > 0.5 else 0, 0)).rot("y", -20).mv(0.9, 0, 0.6)
    sx, sy, _ = shake(t, 0.04 if 0.4 < u < 0.6 else 0)
    return dict(scene=outside(t) + [btn, h], cam=Cam((0.3 + sx, 2.2 + sy, 4.6), (-0.4, 0.55, -1.4), 48, aperture=0.08), glow=dglow(),
                sprites=SPR + ([((-0.6, 0.7, -1.2), (255, 40, 50), 0.6, 2.0 * press)] if press > 0.05 else []),
                env=env(points=[((-0.6, 1.5, -1.0), (255, 40, 50), 3.0 * press, 3.0)]), center=(0, 0, 0))

def sh_question(u, t, dt):
    """'Would you buy a car without CarPlay? Yes, or no?': Yub with his phone between green YES and red NO neons, the Blazer EV behind."""
    up = t > ws(8, 7)
    h = yub("smug" if up else "confused", la=(25, 55, 80), ra=(25, 55, 80), held=phone(t), head=(0, 0, 8 * math.sin(t * 4)))
    y = PR.neon_sign("YES", 0.8, 0.4, (60, 230, 110), 2.8).mv(-0.95, 1.55, 0.1); n = PR.neon_sign("NO", 0.8, 0.4, (255, 50, 60), 2.8).mv(0.95, 1.55, 0.1)
    return dict(scene=dealer(t) + POLES + [h, y, n, blazer(t, -0.5, -4.2, -30)], cam=Cam((0, 1.45, 5.8 - 0.3 * u), (0, 1.3, 0), 46, aperture=0.12),
                glow=dglow(), sprites=SPR, env=env(points=[((-0.95, 1.6, 0.6), (60, 230, 110), 1.2, 1.2), ((0.95, 1.6, 0.6), (255, 50, 60), 1.2, 1.2)]), center=(0, 0, 0))

SHOTS = [
    (0.0, sh_hook, "blue-hour Chevrolet dealership, Yub holds his iPhone up by a red Blazer EV (astronaut on a deck chair)"),
    (ws(0, 5), sh_iphone, "macro: the iPhone's glowing CarPlay screen, dash blurred behind"),
    (ws(1, 0), sh_plug, "macro: cable clicks into the console port, light races along it"),
    (ws(1, 8), sh_nothing, "JOKE: nothing happens; crickets; deadpan"),
    (ws(2, 0), sh_2023, "holographic 2023 over a row of Chevrolet EVs"),
    (ws(2, 5), sh_apps, "CarPlay + Android Auto tiles X'd and shattered over the Blazer EV"),
    (ws(3, 0), sh_gas, "gas pump + grey Chevy; CarPlay tile flickers out"),
    (ws(3, 9), sh_chip, "macro: glowing circuit board, traces racing into a GM chip, holo 2028"),
    (ws(4, 0), sh_better, "big Chevy screen with maps, sparkles; Yub side-eyes it"),
    (ws(5, 0), sh_yourphone, "Yub holds his phone up to the screen"),
    (ws(5, 2) - 0.05, sh_nothanks, "JOKE: butler screen 'No thanks.', phone recoils, cringe"),
    (ws(6, 0), sh_9in10, "ten shoppers, nine raise glowing phones; holo 9 / 10"),
    (ws(6, 10), sh_46, "glowing pie chart: the 46% wedge lifts out"),
    (ws(7, 0), sh_crowd, "crowd outside the dealership waving phones"),
    (ws(7, 9) - 0.05, sh_no, "JOKE: giant NO button slammed, red flood, facepalm"),
    (ws(8, 0), sh_question, "Yub with phone between YES and NO neons"),
]
SFX = [(ws(0, 5), "sparkle", 0.4), (ws(1, 0) + 0.35, "click", 0.9), (ws(1, 0) + 0.4, "whoosh", 0.3), (ws(1, 8), "crickets", 1.0),
       (ws(2, 0), "whoosh", 0.4), (ws(2, 5) + 0.45 * (ws(3, 0) - ws(2, 5)), "buzzer", 0.5), (ws(2, 5) + 0.6 * (ws(3, 0) - ws(2, 5)), "crash", 0.6),
       (ws(3, 0) + 0.3, "slide_down", 0.4), (ws(3, 9), "sparkle", 0.5), (ws(4, 0), "sparkle", 0.4), (ws(5, 2), "ding", 0.6),
       (ws(5, 2) + 0.4, "boing", 0.6), (ws(6, 0) + 0.3, "pop", 0.4), (ws(6, 10), "whoosh", 0.4), (ws(7, 0), "confetti", 0.4),
       (ws(7, 9) + 0.6, "buzzer", 0.9), (ws(7, 12) + 0.2, "rimshot", 0.8), (ws(8, 7), "pop", 0.5), (ws(8, 9), "pop", 0.5)]

if __name__ == "__main__": E.main(V)
