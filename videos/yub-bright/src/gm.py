"""gm_carplay: bright low-poly narrated short. Oddity (never mentioned): an astronaut in a full spacesuit lounging on a
striped deck chair under a beach umbrella on the dealership forecourt, sipping a drink."""
import math, sys
import numpy as np
from PIL import Image, ImageDraw
from lowpoly import P, cat, box, cbox, cyl, sphere, tiles, Cam, sky, tex, font
import ymodels as Y
import fmodels as FM
import models as M
import cars as C
import engine as E
from engine import ease, lerp, shake
from hero import hero, bbox, cb, clean

NAME = "gm"
V = E.Video(sys.modules[__name__]); ws = V.ws; DUR = V.dur
HOOK = "GM wants your car to forget your iPhone."
HOT = {"gm", "iphone", "phone", "nothing", "2023", "carplay", "android", "auto", "evs", "future", "2028", "better", "experience",
       "no", "thanks", "nine", "ten", "forty-six", "percent", "must-have", "half", "how", "about", "yes"}
TOPS = [(ws(2, 0), ws(3, 0), "2023 · GM ELECTRIC CARS"), (ws(3, 0), ws(4, 0), "FUTURE GM CARS · ~2028"), (ws(6, 0), ws(7, 0), "CARS.COM DATA")]
ONSCREEN = ["gm logo", "CHEVROLET + bowtie", "CarPlay", "Android Auto", "2023", "2028", "BETTER EXPERIENCE", "NO THANKS",
            "NEARLY 9 IN 10", "46% MUST-HAVE", "NO", "YES"]
ODDITY = "an astronaut in a full spacesuit lounging on a striped deck chair under a beach umbrella on the dealership forecourt"
CRASH = [ws(1, 4), ws(7, 9)]
MUSIC_UNDER_DB = 4.0

# ---------------------------------------------------------------- textures
def _app(kind, n=128, x=False):
    im = Image.new("RGB", (n, n), (245, 246, 250)); d = ImageDraw.Draw(im)
    if kind == "carplay":
        for y in range(n): d.line((0, y, n, y), fill=(int(40 + 60 * y / n), int(200 - 60 * y / n), int(120 + 100 * y / n)))
        d.rounded_rectangle((18, 18, n - 18, n - 18), 22, outline=(255, 255, 255), width=7)
        d.polygon([(52, 42), (52, 86), (88, 64)], fill=(255, 255, 255))
    else:
        d.rectangle((0, 0, n, n), fill=(250, 250, 252))
        d.polygon([(64, 18), (110, 104), (88, 104), (64, 58), (40, 104), (18, 104)], fill=(60, 170, 80))
        d.polygon([(64, 58), (88, 104), (40, 104)], fill=(66, 133, 244))
    if x: d.line((10, 10, n - 10, n - 10), fill=(230, 30, 40), width=14); d.line((n - 10, 10, 10, n - 10), fill=(230, 30, 40), width=14)
    return tex(im)
T_CP, T_AA, T_CPX, T_AAX = _app("carplay"), _app("android"), _app("carplay", x=True), _app("android", x=True)

def _screen(kind, w=320, h=180):
    im = Image.new("RGB", (w, h), (18, 24, 36)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 22), fill=(30, 40, 60)); d.text((8, 11), "12:00", font=font(14), fill=(220, 226, 236), anchor="lm")
    if kind == "home":
        for i, (lab, c) in enumerate((("Maps", (60, 170, 90)), ("Music", (230, 80, 90)), ("Phone", (60, 140, 230)), ("Climate", (240, 170, 40)))):
            x = 22 + i * 74; d.rounded_rectangle((x, 50, x + 60, 110), 12, fill=c); d.text((x + 30, 128), lab, font=font(14), fill=(230, 236, 244), anchor="mm")
    elif kind == "wait":
        d.text((w / 2, 80), "Phone connected?", font=font(24), fill=(240, 244, 250), anchor="mm")
        d.text((w / 2, 125), "...", font=font(40), fill=(150, 160, 180), anchor="mm")
    elif kind == "nothanks":
        d.ellipse((w / 2 - 34, 34, w / 2 + 34, 102), fill=(60, 140, 230)); d.line((w / 2 - 14, 60, w / 2 - 6, 60), fill=(255, 255, 255), width=5)
        d.line((w / 2 + 6, 60, w / 2 + 14, 60), fill=(255, 255, 255), width=5); d.line((w / 2 - 12, 82, w / 2 + 12, 82), fill=(255, 255, 255), width=4)
        d.text((w / 2, 140), "No thanks.", font=font(36), fill=(255, 255, 255), anchor="mm")
    elif kind == "forget":
        d.rounded_rectangle((w / 2 - 70, 40, w / 2 - 20, 140), 10, fill=(40, 44, 54), outline=(200, 206, 220), width=4)
        d.text((w / 2 + 50, 92), "?", font=font(110), fill=(255, 90, 90), anchor="mm")
    elif kind == "no":
        d.text((w / 2, 100), "NO", font=font(100), fill=(255, 70, 70), anchor="mm")
    return tex(im)
S_HOME, S_WAIT, S_NOTHX, S_NO, S_FORGET = _screen("home"), _screen("wait"), _screen("nothanks"), _screen("no"), _screen("forget")
T_CHEVY = Y.word("CHEVROLET", 320, 64, (30, 30, 36), (250, 250, 252), 40)
T_2023 = Y.word("2023", 160, 80, (255, 255, 255), (230, 40, 50), 56)
T_2028 = Y.word("~2028", 160, 80, (255, 255, 255), (40, 110, 220), 52)
T_BETTER = Y.word("\"A BETTER\nEXPERIENCE\"", 256, 128, (20, 30, 60), (250, 250, 252), 34, border=(40, 110, 220))
T_9IN10 = Y.word("NEARLY\n9 IN 10", 192, 128, (255, 255, 255), (40, 110, 220), 36)
T_46 = Y.word("46%\nMUST-HAVE", 224, 128, (255, 255, 255), (230, 40, 50), 34)
T_EV = Y.word("EV", 64, 40, (255, 255, 255), (40, 170, 90), 28)
T_PHONE_HOME = tex(Image.new("RGB", (40, 80), (60, 140, 230)))
T_YES, T_NO = FM.T_YES_BTN, FM.T_NO_BTN

ASPH = (150, 154, 162); RED = C.EQ_RED

def phone(t=0.0, lit=True):
    p = cat([bbox(-0.045, 0, -0.01, 0.045, 0.19, 0.01, (24, 24, 28), b=0.012),
             box(-0.038, 0.012, 0.0101, 0.038, 0.178, 0.0111, (255, 255, 255), texs={"f": T_CP}, e=1.0 if lit else 0.2)])
    return p

def dealer(t, odd=True):
    s = [tiles(-40, -40, 40, 30, -0.01, 8.0, -1, (110, 200, 100)), tiles(-24, -14, 24, 12, 0.0, 4.0, -1, ASPH)]
    s += [box(x, 0.004, -6, x + 0.1, 0.012, 6, (250, 250, 250)) for x in np.arange(-12, 13, 3.0)]
    bld = [box(-14, 0, -24, 14, 7, -14, (246, 248, 252)), box(-12, 0.3, -14.05, 12, 5.2, -14.0, (150, 205, 240)),
           box(-14, 7, -24, 14, 7.4, -14, (40, 110, 220)), box(-4.5, 7.4, -14.6, 4.5, 8.6, -14.4, (255, 255, 255), texs={"f": T_CHEVY}),
           cbox(5.6, 8.0, -14.5, 1.6, 0.8, 0.2, (255, 255, 255), texs={"f": C.T_BOWTIE})]
    s += bld
    pylon = cat([box(-0.25, 0, -0.25, 0.25, 3.2, 0.25, (200, 204, 214)), box(-1.3, 3.2, -0.15, 1.3, 5.8, 0.15, (255, 255, 255), texs={"f": C.T_GM, "b": C.T_GM})])
    s.append(pylon.mv(-5.5, 0, -9))
    for x in (-18, 16, 20): s.append(C.palm(4.2).mv(x, 0, -8))
    for x, y, z in ((-20, 18, -50), (10, 22, -58), (30, 16, -46)): s.append(C.cloud(3.0).mv(x, y, z))
    for i, x in enumerate((-6, -2, 2, 6)):
        s.append(cat([cyl(0.04, 0.04, 4.0, 5, (220, 220, 220)), box(0.0, 3.2, -0.01, 1.0, 3.9, 0.01, [(230, 40, 50), (40, 110, 220), (250, 200, 40), (60, 190, 90)][i])]).mv(x, 0, -13))
    if odd: s.append(Y.astronaut_chair(t).rot("y", 200).sc(1.2).mv(9.5, 0, -6.5))
    return s

def cockpit(screen, t, expr="smile", la=(55, 4, 40), ra=(55, 4, 40), held=None, head=(0, 0, 0), **kw):
    """Inside the Equinox EV (cutaway): dash with a big centre screen facing the cabin, wheel with bowtie, Yub at the wheel."""
    hw = 0.95
    dash = [box(0.55, 0.75, -hw, 1.25, 1.15, hw, (236, 236, 240)), box(0.5, 1.12, -0.3, 0.56, 1.42, 0.35, (255, 255, 255), texs={"l": screen}, e=1.0),
            box(0.56, 1.1, -0.32, 0.62, 1.44, 0.37, (24, 24, 28)), box(-1.5, 0.2, -hw, 1.3, 0.4, hw, (60, 62, 70)),
            box(-1.4, 0.4, -hw - 0.05, 1.3, 1.15, -hw, RED), cbox(0.5, 0.98, 0.05, 0.03, 0.03, 0.06, (30, 30, 30))]
    seat = [box(-0.9, 0.55, -0.7, -0.35, 0.75, -0.15, (50, 50, 56)), box(-0.95, 0.75, -0.7, -0.8, 1.55, -0.15, (50, 50, 56))]
    sw = cat([C.steering(0.19), box(-0.04, 0.03, -0.06, 0.04, 0.05, 0.06, (255, 255, 255), texs={"t": C.T_BOWTIE})]).rot("z", 70).mv(0.22, 1.16, -0.42)
    h = C.hero_seat(hero(expr, sit=True, la=la, ra=ra, head=head, held=held, **kw))
    return [*dash, *seat, sw, h]

def SCREEN_CAM(): return Cam((-0.65, 1.62, 0.5), (0.53, 1.27, 0.03), 44)
def FACE_CAM(): return Cam((1.15, 1.68, 0.45), (-0.62, 1.52, -0.42), 54)

# ---------------------------------------------------------------- shots
def sh_hook(u, t, dt):
    """Yub at a GM dealership next to a red Chevrolet Equinox EV, proudly holding up his iPhone."""
    car = C.equinox().rot("y", -30).mv(-1.0, 0, -1.2)
    h = hero("proud", ra=(150, 15, 30), held=phone(t), head=(10, 0, 0)).rot("y", -15).mv(1.1, 0, 1.0)
    e = ease(u)
    return dict(scene=dealer(t) + [car, h], cam=Cam(lerp((2.8, 1.5, 5.6), (2.4, 1.6, 4.9), e), (0.2, 1.6, -0.6), 54))

def sh_forget(u, t, dt):
    """'forget your iPhone': the car's screen shows a phone with a big question mark; the bowtie wheel looks on."""
    sc = cockpit(S_FORGET, t, "confused", look="r")
    return dict(scene=sc, cam=SCREEN_CAM())

def sh_plug(u, t, dt):
    """'Plug in your phone': Yub plugs the cable in, hopeful smile."""
    k = ease(min(1, u * 1.5))
    sc = cockpit(S_WAIT, t, "smile", ra=(70 - 10 * k, 30, 60), held=phone(t), la=(55, 4, 40))
    cable = box(0.45 - 0.2 * (1 - k), 0.96, 0.03, 0.5, 0.99, 0.07, (240, 240, 240))
    return dict(scene=sc + [cable], cam=FACE_CAM())

def sh_nothing(u, t, dt):
    """JOKE 'nothing.': the screen stays on its own home page. Crickets. Yub stares, deadpan."""
    sc = cockpit(S_HOME, t, "deadpan", held=phone(t), ra=(70, 30, 60))
    return dict(scene=sc, cam=FACE_CAM() if u > 0.35 else SCREEN_CAM())

def _wall(tids, x0=0.0, k=1.0):
    return [box(x0 - 1.7 + 1.2 * i, 1.0, -0.05, x0 - 0.7 + 1.2 * i, 2.0, 0.05, (255, 255, 255), texs={"f": tid}) for i, tid in enumerate(tids)]

def sh_2023(u, t, dt):
    """'In 2023, GM began dropping CarPlay and Android Auto': a big 2023 sign; the two app tiles get red X'd and drop."""
    k = u > 0.45
    drop = max(0, (u - 0.6) * 3)
    board = [box(-2.3, 0, -0.3, 2.3, 2.6, -0.2, (250, 250, 252)), box(-0.8, 2.6, -0.26, 0.8, 3.4, -0.24, (255, 255, 255), texs={"f": T_2023})]
    apps = [box(-1.6, 1.0 - drop, -0.19, -0.2, 2.4 - drop, -0.18, (255, 255, 255), texs={"f": T_CPX if k else T_CP}).rot("z", 20 * drop, (-0.9, 1.0, 0)),
            box(0.2, 1.0 - drop * 0.8, -0.19, 1.6, 2.4 - drop * 0.8, -0.18, (255, 255, 255), texs={"f": T_AAX if k else T_AA}).rot("z", -15 * drop, (0.9, 1.0, 0))]
    return dict(scene=dealer(t, odd=False) + board + apps, cam=Cam((0.0, 2.3, 6.2), (0, 2.55, 0), 50))

def sh_evs(u, t, dt):
    """'from new EVs': a row of Chevrolet EVs on the lot, each with a green EV tag."""
    s = dealer(t, odd=True)
    for i, c in enumerate(((210, 30, 40), (40, 110, 220), (240, 240, 244), (60, 190, 90))):
        x = -6 + 4 * i
        s.append(C.equinox(c).rot("y", -90).mv(x, 0, -3))
        s.append(box(-0.3, 0, -0.02, 0.3, 0.36, 0.02, (255, 255, 255), texs={"f": T_EV}).mv(x, 1.9, -0.4))
    e = ease(u)
    return dict(scene=s, cam=Cam(lerp((9.0, 2.2, 3.4), (8.0, 2.0, 2.6), e), (-1.5, 1.0, -3), 50))

def sh_2028(u, t, dt):
    """'Future GM cars follow, around 2028': a covered car with a ~2028 sign, a charger and a fuel pump either side."""
    k = ease(min(1, max(0, (u - 0.2) / 0.5)))
    cover = cat([bbox(-2.4, 0.1, -1.0, 2.4, 1.6 - 0.4 * k, 1.0, (230, 232, 240), b=0.4)]).mv(0, 0, 0)
    car = C.equinox((40, 40, 50)).sc(1.0, 1.0, 1.0)
    sign = Y.sign_board(T_2028, 1.4, 0.7, 2.0).mv(0, 0, -2.0)
    pump = cat([box(-0.35, 0, -0.25, 0.35, 1.6, 0.25, (230, 50, 50)), box(-0.25, 1.0, 0.25, 0.25, 1.4, 0.26, (250, 250, 250)), cyl(0.04, 0.04, 0.6, 5, (30, 30, 30)).rot("z", 70).mv(0.35, 1.0, 0)]).mv(3.4, 0, 0.4)
    chg = cat([box(-0.3, 0, -0.2, 0.3, 1.5, 0.2, (40, 170, 90)), box(-0.2, 1.0, 0.2, 0.2, 1.3, 0.21, (220, 255, 230))]).mv(-3.4, 0, 0.4)
    obj = [car, sign, pump, chg] if k > 0.9 else [cover, sign, pump, chg]
    return dict(scene=dealer(t, odd=False) + obj, cam=Cam((0.0, 2.2, 7.4 - u), (0, 1.3, 0), 50))

def sh_better(u, t, dt):
    """'GM calls it a better experience': a GM spokesperson presents a 'BETTER EXPERIENCE' board; Yub, unconvinced."""
    rep = FM.salesman(ra=(60, 30, 40)).rot("y", 20).mv(-1.2, 0, 0) if hasattr(FM, "salesman") else None
    brd = Y.sign_board(T_BETTER, 1.6, 0.8, 1.4).mv(-0.3, 0, -1.2)
    spark = [sphere(0.05, 4, 3, (255, 230, 80), e=1.0).mv(-0.3 + 0.9 * math.cos(t * 3 + i), 2.6 + 0.4 * math.sin(t * 4 + i * 2), -1.1) for i in range(5)]
    h = hero("smug" if u < 0.5 else "deadpan", la=(30, 60, 100), ra=(30, 60, 100), head=(-20, 0, 0)).rot("y", -25).mv(1.3, 0, 0.6)
    s = dealer(t) + [brd, h] + spark + ([clean(rep)] if rep is not None else [])
    return dict(scene=s, cam=Cam((0.8, 1.7, 6.0), (0.0, 1.5, -0.4), 52))

def sh_yourphone(u, t, dt):
    """'Your phone?': Yub holds his iPhone up to the big screen, hopeful."""
    sc = cockpit(S_WAIT, t, "smile", ra=(95, 20, 30), held=phone(t), head=(0, 6, 0))
    return dict(scene=sc, cam=FACE_CAM())

def sh_nothanks(u, t, dt):
    """JOKE 'No thanks.': the screen shows a snooty butler face: 'No thanks.' The phone gets shoved back. Yub cringes."""
    k = ease(min(1, u * 2.5))
    sc = cockpit(S_NOTHX, t, "cringe" if u > 0.3 else "shock", ra=(95 - 50 * k, 20 + 20 * k, 30), held=phone(t), head=(0, -8 * k, 0))
    return dict(scene=sc, cam=SCREEN_CAM() if u < 0.55 else FACE_CAM())

FACES = {}
def shopper(i, t, phone_up=True):
    from models import face_tex
    key = i % 5
    if key not in FACES:
        skins = [(230, 186, 150), (150, 100, 70), (200, 160, 120), (120, 80, 56), (236, 196, 170)]
        hairs = [(60, 40, 24), (20, 20, 20), (200, 190, 160), (120, 70, 30), (30, 26, 22)]
        FACES[key] = (face_tex(skin=skins[key], hair=hairs[key], mouth="smile"), skins[key], hairs[key])
    fid, sk, hr = FACES[key]
    tops = [(230, 60, 60), (60, 120, 230), (250, 200, 40), (60, 190, 90), (200, 90, 200), (240, 140, 40)]
    ra = (150 + 10 * math.sin(t * 8 + i), 10, 20) if phone_up else (0, 8, 10)
    return M.person(skin=sk, top=tops[i % 6], hair=hr, face=fid, ra=ra, held=phone(t) if phone_up else None)

def sh_9in10(u, t, dt):
    """'nearly nine in ten shoppers value it': ten shoppers in a row; nine hold glowing phones up; one shrugs."""
    s = dealer(t, odd=False)
    n_up = min(9, int(u * 14))
    for i in range(10):
        s.append(shopper(i, t, phone_up=(i < n_up and i != 6)).mv(-3.6 + 0.8 * i, 0, 0))
    s.append(box(-0.8, 0, -0.02, 0.8, 1.1, 0.02, (255, 255, 255), texs={"f": T_9IN10}).mv(0, 2.4, -1.5))
    return dict(scene=s, cam=Cam((0.0, 2.0, 7.2), (0, 1.6, 0), 50))

def sh_46(u, t, dt):
    """'forty-six percent call it a must-have': a 3D bar grows to 46% next to a 100% outline bar."""
    k = ease(min(1, u * 1.6))
    bar = box(-0.6, 0, -0.4, 0.6, 3.0 * 0.46 * k, 0.4, (230, 40, 50)).mv(-0.3, 0, 0)
    full = [box(x - 0.3, 0, z, x - 0.24, 3.0, z + 0.06, (40, 40, 48)) for x in (-0.66, 0.6) for z in (-0.46, 0.4)] + [box(-0.96, 2.97, -0.46, 0.36, 3.03, 0.46, (40, 40, 48))]
    lab = box(-0.7, 0, -0.02, 0.7, 0.8, 0.02, (255, 255, 255), texs={"f": T_46}).mv(0.95, 1.5, 0)
    h = hero("shock", la=(30, 30, 80), ra=(80, 40, 40)).rot("y", 30).mv(-1.5, 0, 0.8)
    return dict(scene=dealer(t, odd=False) + [bar, *full, lab, h], cam=Cam((0.0, 2.0, 7.6), (0, 1.6, 0), 50))

def sh_crowd(u, t, dt):
    """'Nearly half of shoppers say they must have it': a crowd outside the GM dealership waving their phones."""
    s = dealer(t)
    for i in range(14):
        p = shopper(i, t, phone_up=i % 2 == 0)
        s.append(p.mv(-5 + (i % 7) * 1.5 + 0.3 * (i // 7), 0.05 * abs(math.sin(t * 7 + i)), -3.0 - 1.4 * (i // 7)))
    return dict(scene=s, cam=Cam((2.0, 2.6, 5.5), (-0.5, 1.6, -4), 50))

def sh_howaboutno(u, t, dt):
    """JOKE 'GM says: how about no.': under the gm sign a giant red NO button gets slammed; Yub facepalms."""
    press = max(0, math.sin(min(1, max(0, (u - 0.45) / 0.25)) * math.pi))
    btn = FM.button(T_NO, press=press).rot("y", 180).sc(2.0).mv(-0.8, 0, -1.5)
    h = hero("cringe", la=(130, 10, 150) if u > 0.5 else (0, 8, 10), head=(0, 10 * (u > 0.5), 0)).rot("y", -20).mv(0.6, 0, 0.2)
    sx, sy, _ = shake(t, 0.04 if 0.45 < u < 0.6 else 0)
    return dict(scene=dealer(t, odd=False) + [btn, h], cam=Cam((0.4 + sx, 2.1 + sy, 4.4), (-0.4, 1.1, -1.5), 54))

def sh_question(u, t, dt):
    """'Would you buy a car without CarPlay? Yes, or no?': Yub next to the Equinox EV, phone in hand, YES / NO signs."""
    up = t > ws(8, 7)
    h = hero("smug" if up else "confused", look="c", la=(25, 55, 80), ra=(25, 55, 80), held=phone(t), head=(0, 0, 8 * math.sin(t * 4)))
    y = Y.sign_board(T_YES, 0.75, 0.75, 1.0).mv(-0.95, 0, -0.3); n = Y.sign_board(T_NO, 0.75, 0.75, 1.0).mv(0.95, 0, -0.3)
    car = C.equinox().rot("y", -30).mv(-0.5, 0, -4.0)
    return dict(scene=dealer(t) + [h, y, n, car], cam=Cam((0.0, 1.5, 4.6 - 0.3 * u), (0, 1.3, 0), 50))

SHOTS = [
    (0.0, sh_hook, "Yub at a GM dealership with a red Equinox EV, holding up his iPhone (astronaut on deck chair)"),
    (ws(0, 4) - 0.05, sh_forget, "car screen shows ? (forget your iPhone)"),
    (ws(1, 0), sh_plug, "Yub plugs his phone in, hopeful"),
    (ws(1, 4) - 0.1, sh_nothing, "JOKE: nothing happens, crickets, deadpan"),
    (ws(2, 0), sh_2023, "2023 board, CarPlay and Android Auto tiles X'd out and dropped"),
    (ws(2, 9) - 0.1, sh_evs, "row of Chevrolet EVs with EV tags"),
    (ws(3, 0), sh_2028, "covered future car revealed, ~2028 sign, charger and fuel pump"),
    (ws(4, 0), sh_better, "'A BETTER EXPERIENCE' board, Yub unconvinced"),
    (ws(5, 0), sh_yourphone, "Yub holds his phone up to the screen"),
    (ws(5, 2) - 0.1, sh_nothanks, "JOKE: screen butler says No thanks, phone shoved back"),
    (ws(6, 0), sh_9in10, "ten shoppers, nine hold phones up: NEARLY 9 IN 10"),
    (ws(6, 9) - 0.1, sh_46, "bar grows to 46% MUST-HAVE"),
    (ws(7, 0), sh_crowd, "crowd outside the dealership waving phones"),
    (ws(7, 9) - 0.1, sh_howaboutno, "JOKE: giant NO button slammed, Yub facepalms"),
    (ws(8, 0), sh_question, "Yub with phone between YES and NO signs"),
]
SFX = [(ws(0, 4), "pop", 0.4), (ws(1, 0) + 0.3, "click", 0.9), (ws(1, 4), "crickets", 1.0), (ws(2, 0) + 0.1, "stamp", 0.6),
       (ws(2, 5), "buzzer", 0.5), (ws(2, 9), "whoosh", 0.4), (ws(3, 0) + 0.4, "poof", 0.6), (ws(4, 0), "sparkle", 0.5),
       (ws(5, 2), "ding", 0.6), (ws(5, 2) + 0.4, "boing", 0.6), (ws(6, 0) + 0.3, "pop", 0.4), (ws(6, 9), "slide_down", 0.3),
       (ws(7, 0), "confetti", 0.4), (ws(7, 9) + 0.6, "buzzer", 0.8), (ws(7, 12) + 0.2, "rimshot", 0.7), (ws(8, 7), "pop", 0.5), (ws(8, 9), "pop", 0.5)]

if __name__ == "__main__": E.main(V)
