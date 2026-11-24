"""tesla_acceleration_boost: PS1 low-poly narrated short.
Oddity (never mentioned): an astronaut lounging on a deck chair under a beach umbrella beside the drag strip."""
import math, sys
from lowpoly import cat, box, cbox, cyl, sphere, tiles, wall, Cam, sky
import models as M
import fmodels as F
import ymodels as Y
import engine as E
from engine import ease, lerp, shake

NAME = "tesla"
V = E.Video(sys.modules[__name__]); ws = V.ws; DUR = V.dur
HOT = {"tesla", "faster", "$2,000", "december", "2019", "acceleration", "boost", "over-the-air", "half", "second", "free", "paid", "yes", "no"}
ONSCREEN = ["TESLA", "$2,000", "DEC", "NOV", "2019", "ACCELERATION BOOST", "UPGRADE", "DUAL MOTOR", "DOWNLOADING", "0-60 MPH", "3.9 s",
            "PEAK POWER +5%", "FREE", "$2,000", "YES", "NO"]
ODDITY = "an astronaut in a full white suit sipping a pink drink on a deck chair under a beach umbrella beside the drag strip"

WHITE = Y.TES_WHITE
T_PRICE = Y.tag("$2,000", 128, 64)
T_DEC = Y._calendar("DEC", "2019")
T_NOV = Y._calendar("NOV", "2019")
T_UPG = [Y.screen(["ACCELERATION", "BOOST", "UPGRADE  $2,000"], 192, 108, accent=(90, 200, 255), logo="tesla"),
         Y.screen(["ACCELERATION", "BOOST", "PURCHASED"], 192, 108, accent=(90, 230, 120), logo="tesla")]
T_DL = [Y.screen(["SOFTWARE UPDATE", "DOWNLOADING"], 192, 108, bar=b, logo="tesla") for b in (0.1, 0.35, 0.6, 0.85, 1.0)]
T_FIVE = [Y.screen(["PEAK POWER", "+%d%%" % k], 192, 108, accent=(90, 230, 120), logo="tesla") for k in range(6)]
T_PAID = Y.screen(["UPDATE", "$2,000"], 192, 108, accent=(255, 80, 70), logo="tesla")
T_FREE = Y.tag("FREE", 96, 56, (90, 220, 120))
T_W39 = Y._watchface("3.9 s")
T_060 = Y.word("0-60 MPH", 128, 32, (255, 255, 255), (20, 20, 24), 20)
T_DUALTAG = Y.word("DUAL\nMOTOR", 96, 64, (255, 255, 255), (20, 20, 24), 22)
T_PLATE = Y._plate("BOOST")
STRIP_POINTS = [((0, 5, 4), (255, 200, 170), 12.0), ((6, 3, -4), (255, 140, 90), 8.0)]
SHOW_POINTS = [((x, 4.6, z), (240, 244, 255), 8.0) for x in (-3.5, 3.5) for z in (-1.5, 2.5)]

# ---------------------------------------------------------------- sets
def xmas_tree(lit=0):
    """Drag-strip starting lights."""
    s = [box(-0.08, 0, -0.08, 0.08, 2.4, 0.08, (40, 40, 44)), box(-0.3, 1.2, -0.06, 0.3, 2.4, 0.06, (24, 24, 26))]
    for i, c in enumerate([(250, 200, 40)] * 3 + [(60, 240, 80)]):
        on = i < lit
        s.append(sphere(0.07, 6, 3, c if on else (50, 50, 50), e=1.0 if on else 0.0).mv(0, 2.2 - 0.27 * i, 0.08))
    return cat(s)

def strip(t, odd=True, lit=4, scroll=0.0):
    s = [tiles(-30, -4, 60, 4, 0, 3.0, -1, (56, 56, 62)),
         tiles(-30, -14, 60, -4, 0, 3.0, -1, (90, 80, 60)), tiles(-30, 4, 60, 14, 0, 3.0, -1, (90, 80, 60))]
    s += [box(x - scroll % 6, 0.005, -0.05, x + 3 - scroll % 6, 0.012, 0.05, (240, 240, 230)) for x in range(-30, 60, 6)]
    s.append(box(-30, 0, -4.1, 60, 0.8, -4.0, (200, 200, 204)))          # far barrier only (the near one would block the camera)
    s += [box(-2.3, 0.005, -4, -2.15, 0.012, 4, (240, 240, 240))]                       # start line
    s.append(xmas_tree(lit).mv(-2.2, 0, 0))
    s.append(cat([box(-2.5, 0, -0.1, 2.5, 4.0, 0.1, (40, 40, 44)), box(-2.2, 3.0, 0.11, 2.2, 3.9, 0.15, (255, 255, 255), texs={"f": Y.T_TES_SIGN}, e=1.0)]).mv(4.0, 0, -9.0))
    if odd: s.append(Y.astronaut_chair(t).rot("y", -150).mv(2.2, 0, -6.2))
    return s

def showroom(t, snow=False):
    s = [tiles(-12, -8, 12, 9, 0, 2.0, M.T_TILE_DARK), wall(-12, 0, 12, 6, -6.5, 3.0, -1, (210, 212, 218)),
         box(-2.6, 3.6, -6.48, 2.6, 4.5, -6.4, (255, 255, 255), texs={"f": Y.T_TES_SIGN}, e=1.0),
         cyl(3.0, 3.0, 0.1, 20, (40, 40, 44)).rot("y", t * 20)]
    s += [box(x - 1.3, 0.4, -6.47, x + 1.3, 3.2, -6.42, (255, 255, 255), texs={"f": M.T_WIN_COOL}, e=0.5) for x in (-6.5, 6.5)]
    s += [cbox(x, 5.6, z, 0.6, 0.1, 0.6, (255, 250, 240), e=1.0) for x in (-3.5, 3.5) for z in (-1.5, 2.5)]
    if snow:
        s += [cbox(-6.5 + ((i * 0.37) % 2.4) - 1.2, 3.1 - ((t * 0.8 + i * 0.29) % 2.7), -6.38, 0.06, 0.06, 0.01, (255, 255, 255), e=1.0) for i in range(24)]
    return s

def dash(tid):
    """Model 3 interior: low flat dash with the wood strip and the big landscape centre screen."""
    return cat([box(-1.3, 0.6, -0.7, 1.3, 0.92, -0.1, (24, 24, 26)), box(-1.3, 0.8, -0.1, 1.3, 0.86, -0.06, (120, 84, 52)),
                box(-0.36, 0.95, -0.28, 0.36, 1.36, -0.24, (255, 255, 255), texs={"f": tid}, e=1.0),
                box(-0.04, 0.9, -0.3, 0.04, 0.96, -0.26, (30, 30, 34)),
                cyl(0.19, 0.19, 0.05, 12, (24, 24, 26), capcol=(30, 30, 30)).rot("x", 70).mv(-0.62, 1.0, 0.05),
                box(-1.4, 0.6, -0.9, 1.4, 2.0, -0.85, (30, 34, 44))])

# ---------------------------------------------------------------- shots
def sh_launch(u, t, dt):
    """Dusk drag strip: lights go green, the white Model 3 launches; camera low at the side."""
    lit = min(4, int(u * 7))
    go = max(0, (u - 0.5) / 0.5)
    x = 0.4 + 7.0 * go ** 2
    car = Y.model3(WHITE, spin=-t * 1400 * go, plate=T_PLATE).mv(x, 0, 1.6)
    sx, sy, _ = shake(t, 0.03 * go, 13)
    return dict(scene=strip(t, lit=lit) + [car], cam=Cam((8.0 + sx, 1.1 + sy, 5.4), (0.6 + 5.0 * go, 0.7, 0.6), 46),
                bg=Y.DUSK_BG, fog=(18, 45, (180, 110, 100)), points=STRIP_POINTS + [((-2.2, 2.0, 0.5), (60, 255, 90) if lit == 4 else (255, 200, 60), 3.0)], amb=0.45)

def sh_price(u, t, dt):
    """A big $2,000 price tag drops onto the hood of the turntable Model 3."""
    k = ease(min(1, u * 2.0))
    tg = cat([box(-0.5, -0.25, -0.01, 0.5, 0.25, 0.01, (255, 255, 255), texs={"f": T_PRICE, "b": T_PRICE})]).rot("x", -70 * k).mv(1.3, 0.95 + 1.6 * (1 - k), 0.0)
    car = Y.model3(WHITE).rot("y", 25 + t * 12)
    sx, sy, _ = shake(t, 0.03 if 0.48 < u < 0.6 else 0, 12)
    return dict(scene=showroom(t) + [car, tg.rot("y", 25 + t * 12)], cam=Cam((5.6 + sx, 2.8 + sy, 6.4), (0.4, 0.8, 0.0), 46), points=SHOW_POINTS, amb=0.4)

def sh_dec(u, t, dt):
    """DEC 2019 calendar on the showroom wall; snow falls past the window behind it."""
    cal = box(-0.4, -0.5, 0, 0.4, 0.5, 0.02, (255, 255, 255), texs={"f": T_DEC}).mv(-4.8, 2.0, -6.3)
    return dict(scene=showroom(t, snow=True) + [cal], cam=Cam((-4.5, 2.0, -4.0 - 0.4 * u), (-4.8, 2.0, -6.3), 46), points=SHOW_POINTS + [((-4.8, 2.5, -5.0), (255, 255, 255), 3.0)], amb=0.45)

def sh_screen(u, t, dt):
    """The centre screen offers ACCELERATION BOOST; a finger taps UPGRADE and it flips to PURCHASED."""
    tap = min(1, max(0, (u - 0.45) / 0.1))
    tid = T_UPG[1] if u > 0.55 else T_UPG[0]
    finger = cat([cbox(0, 0, 0, 0.05, 0.05, 0.2, (206, 164, 128)), cbox(0, -0.04, -0.2, 0.14, 0.12, 0.25, (206, 164, 128)), cbox(0, -0.06, -0.45, 0.16, 0.16, 0.3, (40, 50, 80))])
    finger = finger.mv(0.18, 1.05, 0.25 - 0.45 * math.sin(math.pi * tap) - 0.0 * u)
    return dict(scene=[dash(tid), finger], cam=Cam((0.05, 1.25, 1.4 - 0.1 * u), (0, 1.05, -0.26), 46), bg=E.DEF_BG, fog=None,
                points=[((0, 1.15, 0.2), (120, 190, 255), 1.6)], amb=0.25)

def sh_dual(u, t, dt):
    """X-ray: the Model 3 Dual Motor's two motors glow, front axle and rear axle; DUAL MOTOR badge on the boot."""
    car = Y.model3(WHITE, dual=True, xray=0.6 + 0.4 * math.sin(t * 8)).rot("y", 200 + 50 * ease(u))
    return dict(scene=showroom(t) + [car], cam=Cam((0.0, 2.8, 6.6 - 0.6 * u), (0, 0.5, 0), 46), points=SHOW_POINTS, amb=0.32)

def sh_ota(u, t, dt):
    """Over the air: rings of signal come down from the sky onto the parked car; its screen fills a download bar."""
    car = Y.model3(WHITE).rot("y", -30)
    rings = Y.waves(t, 4, 0.35, 0.9, (90, 200, 255), r0=0.2).rot("x", 90).mv(-0.2, 2.6 + 0.4 * math.sin(t), 0.0)
    tower = cat([cyl(0.15, 0.06, 8.0, 5, (130, 130, 136)), sphere(0.2, 6, 3, (255, 60, 60), e=1.0).mv(0, 8.1, 0)]).mv(-6, 0, -10)
    return dict(scene=strip(t, odd=False) + [car, rings, tower], cam=Cam((3.4, 4.6 + 0.4 * u, 6.0), (0, 1.3, 0), 52),
                bg=Y.DUSK_BG, fog=(18, 45, (180, 110, 100)), points=STRIP_POINTS + [((0, 2.5, 0), (90, 200, 255), 3.5)], amb=0.45)

def sh_download(u, t, dt):
    return dict(scene=[dash(T_DL[min(4, int(u * 5))])], cam=Cam((0.0, 1.25, 1.4), (0, 1.05, -0.26), 46), bg=E.DEF_BG, fog=None,
                points=[((0, 1.15, 0.2), (120, 190, 255), 1.6)], amb=0.25)

def sh_race(u, t, dt):
    """Two Model 3s side by side from the start line: the boosted one pulls clear by a nose."""
    a = 9.0 * ease(u) ** 1.6
    c1 = Y.model3(WHITE, spin=-t * 1400).mv(-1.0 + a * 1.1, 0, 1.3)
    c2 = Y.model3((150, 154, 160), spin=-t * 1300).mv(-1.0 + a, 0, -1.3)
    sx, sy, _ = shake(t, 0.02, 13)
    return dict(scene=strip(t, scroll=0) + [c1, c2], cam=Cam((7.5 + a + sx, 1.3 + sy, 5.5), (a, 0.6, 0), 46),
                bg=Y.DUSK_BG, fog=(18, 45, (180, 110, 100)), points=[((a, 5, 4), (255, 200, 170), 12.0)], amb=0.5)

def sh_watch(u, t, dt):
    """A stopwatch stops at 3.9 s; the needle snaps back half a second."""
    ang = 360 * 3.9 / 10 * min(1, u * 1.6)
    sw = Y.stopwatch(T_W39, ang).sc(1.2).mv(0, 1.4, 0)
    lab = box(-0.4, 0.55, -0.01, 0.4, 0.75, 0.01, (255, 255, 255), texs={"f": T_060})
    return dict(scene=showroom(t)[:2] + [sw, lab], cam=Cam((0, 1.2, 1.6 - 0.2 * u), (0, 1.15, 0), 50), points=[((0.5, 2, 1.5), (255, 240, 220), 4.0)], amb=0.5, fog=None)

def sh_nov(u, t, dt):
    """A month earlier: the calendar page flips back from DEC to NOV 2019."""
    f = min(1, u * 1.6)
    back = box(-0.4, -0.5, 0, 0.4, 0.5, 0.02, (255, 255, 255), texs={"f": T_NOV}).mv(0, 2.0, -6.3)
    page = box(-0.4, -1.0, 0, 0.4, 0, 0.005, (255, 255, 255), texs={"f": T_DEC, "b": T_DEC}).rot("x", 160 * (1 - f) if f < 1 else 0).mv(0, 2.5, -6.27) if f < 1 else None
    if f >= 1: back = back
    page2 = box(-0.4, -1.0, 0, 0.4, 0, 0.005, (255, 255, 255), texs={"f": T_NOV, "b": T_NOV}).rot("x", -170 * (1 - f)).mv(0, 2.5, -6.27)
    return dict(scene=showroom(t)[:3] + [back, page2], cam=Cam((0.0, 2.0, -4.7), (0, 2.0, -6.4), 46), points=SHOW_POINTS, amb=0.5)

def sh_every(u, t, dt):
    """Every Model 3: a row of them in the lot, each lights up in turn."""
    s = strip(t, odd=False)
    cols = [WHITE, (30, 30, 34), (180, 20, 30), (40, 70, 140), (150, 154, 160)]
    for i in range(5):
        on = u * 6 > i
        s.append(Y.model3(cols[i], glow=on).rot("y", 90).mv(-4.0 + 2.2 * i, 0, -1.5))
        if on: s.append(Y.waves(t, 2, 0.3, 0.6, (90, 200, 255), 0.1).rot("x", 90).mv(-4.0 + 2.2 * i, 1.8, -1.5))
    return dict(scene=s, cam=Cam((-1.0 + 2.0 * u, 3.6, 9.0), (0.4, 0.6, -1.5), 50), bg=Y.DUSK_BG, fog=(18, 45, (180, 110, 100)), points=STRIP_POINTS, amb=0.45)

def sh_five(u, t, dt):
    return dict(scene=[dash(T_FIVE[min(5, int(u * 9))])], cam=Cam((0.1, 1.25, 1.35 - 0.1 * u), (0, 1.05, -0.26), 46), bg=E.DEF_BG, fog=None,
                points=[((0, 1.15, 0.2), (120, 255, 160), 1.6)], amb=0.25)

def sh_gift(u, t, dt):
    """For free: a gift box on the roof pops open, a FREE tag springs out."""
    o = ease(min(1, u * 2.0))
    car = Y.model3(WHITE, giftbox=o).rot("y", -25)
    tg = box(-0.3, -0.18, -0.01, 0.3, 0.18, 0.01, (255, 255, 255), texs={"f": T_FREE, "b": T_FREE}).rot("y", -25 + 20 * math.sin(t * 4)).mv(-0.35, 1.45 + 0.9 * o, 0.15)
    return dict(scene=showroom(t) + [car, tg], cam=Cam((3.0, 2.6, 4.0 - 0.5 * u), (-0.3, 1.3, 0), 48), points=SHOW_POINTS + [((-0.3, 2.4, 0.5), (255, 240, 120), 3.0 * o + 0.1)], amb=0.4)

def sh_paid(u, t, dt):
    """Paid update second: a hand feeds a wad of cash into the Model 3's charge port (rear, driver's side); the port screen reads $2,000."""
    car = Y.model3(WHITE)
    k = ease(min(1, u * 1.5))
    cash = box(-0.09, -0.04, -0.2, 0.09, 0.04, 0.2, (255, 255, 255), texs={"t": Y.T_CASH, "d": Y.T_CASH, "b": Y.T_CASH}).mv(-2.0, 0.76, -1.15 - 0.45 * (1 - k))
    hnd = cat([cbox(0, 0, 0, 0.16, 0.08, 0.12, (206, 164, 128)), cbox(0.0, -0.02, -0.28, 0.16, 0.14, 0.4, (40, 50, 80))]).mv(-2.0, 0.8, -1.35 - 0.45 * (1 - k))
    port = box(-2.12, 0.68, -0.935, -1.88, 0.88, -0.925, (255, 255, 255), texs={"b": T_PAID}, e=1.0)
    return dict(scene=showroom(t)[:2] + [car, cash, hnd, port], cam=Cam((-2.9, 1.25, -3.0), (-2.0, 0.8, -0.93), 44),
                points=SHOW_POINTS + [((-2.5, 1.5, -2.2), (255, 240, 220), 3.0)], amb=0.42)

def sh_question(u, t, dt):
    """Stopwatch on a stack of cash in front of the Model 3 on the strip; astronaut lounging behind."""
    sw = Y.stopwatch(T_W39, 140).rot("x", -20).sc(0.6).mv(0.0, 0.62, 2.8)
    cash = Y.cash_stack(7).sc(1.4).mv(0.0, 0, 2.8)
    car = Y.model3(WHITE, plate=T_PLATE).rot("y", -60).mv(0.6, 0, 0)
    a = math.radians(80 - 20 * ease(u))
    eye = (5.2 * math.cos(a), 1.3, 2.8 + 3.4 * math.sin(a))
    return dict(scene=strip(t) + [car, cash, sw], cam=Cam(eye, (0.3, 0.8, 0.6), 50), bg=Y.DUSK_BG, fog=(18, 45, (180, 110, 100)), points=STRIP_POINTS, amb=0.48)

def sh_yesno(u, t, dt):
    yes = F.button(F.T_YES_BTN, press=max(0, math.sin(t * 6))).rot("y", 180).mv(-0.7, 0, 3.4)
    no = F.button(F.T_NO_BTN, press=max(0, math.sin(t * 6 + 3))).rot("y", 180).mv(0.7, 0, 3.4)
    car = Y.model3(WHITE, plate=T_PLATE).rot("y", -60).mv(0.6, 0, 0)
    e = ease(u)
    return dict(scene=strip(t) + [car, yes, no], cam=Cam(lerp((0.0, 2.6, 6.6), (0.8, 1.6, 6.0), e), (0.2, 0.6, 1.8), 50),
                bg=Y.DUSK_BG, fog=(18, 45, (180, 110, 100)), points=STRIP_POINTS + [((0, 1.5, 4.0), (255, 255, 255), 3.0)], amb=0.5)

SHOTS = [
    (0.0, sh_launch, "drag-strip lights go green, white Model 3 launches (astronaut on a deck chair behind)"),
    (ws(0, 6), sh_price, "$2,000 tag drops onto the hood"),
    (ws(1, 0), sh_dec, "DEC 2019 calendar, snow outside"),
    (ws(1, 3), sh_screen, "centre screen: ACCELERATION BOOST, tap UPGRADE"),
    (ws(1, 9), sh_dual, "x-ray Model 3: two glowing motors, DUAL MOTOR badge"),
    (ws(2, 0), sh_ota, "over-the-air rings come down onto the car"),
    (ws(2, 4), sh_download, "screen: SOFTWARE UPDATE DOWNLOADING bar"),
    (ws(2, 5), sh_race, "two Model 3s race, the boosted one pulls ahead"),
    (ws(2, 11), sh_watch, "stopwatch stops at 3.9 s, label 0-60 MPH"),
    (ws(3, 0), sh_nov, "calendar flips back to NOV 2019"),
    (ws(3, 3), sh_every, "row of Model 3s lighting up one by one"),
    (ws(3, 9), sh_five, "screen: PEAK POWER +5%"),
    (ws(3, 13), sh_gift, "gift box on the roof pops open: FREE"),
    (ws(4, 3), sh_paid, "cash fed into the charge port, screen $2,000"),
    (ws(5, 0), sh_question, "stopwatch on a stack of cash before the Model 3"),
    (ws(5, 8), sh_yesno, "YES / NO buttons"),
]
SFX = [(0.9, "ding", 0.3), (1.2, "vroom", 0.9), (ws(0, 6) + 0.5, "cha_ching", 0.6), (ws(1, 0), "whoosh", 0.4), (ws(1, 3) + 0.85, "pop", 0.6),
       (ws(1, 9), "sparkle", 0.4), (ws(2, 0), "sparkle", 0.4), (ws(2, 5), "vroom", 0.7), (ws(2, 11) + 0.6, "ding", 0.5),
       (ws(3, 0), "whoosh", 0.4), (ws(3, 3), "sparkle", 0.3), (ws(3, 13), "confetti", 0.6), (ws(4, 3) + 0.4, "cha_ching", 0.6),
       (ws(5, 8), "pop", 0.6)]

if __name__ == "__main__": E.main(V)
