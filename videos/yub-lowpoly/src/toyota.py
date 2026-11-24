"""toyota_key_fob: PS1 low-poly narrated short. Oddity (never mentioned): a penguin pushing a shopping cart past in the background."""
import math, sys
from lowpoly import cat, box, cbox, cyl, sphere, tiles, wall, Cam, sky
import models as M
import fmodels as F
import ymodels as Y
import engine as E
from engine import ease, lerp, shake

NAME = "toyota"
V = E.Video(sys.modules[__name__]); ws = V.ws; DUR = V.dur
HOT = {"toyota", "own", "subscription", "eight", "eighty", "radio", "paid", "backlash", "intentional", "reviewing", "key", "rent", "button", "yes", "no"}
ONSCREEN = ["TOYOTA", "LOCK", "OPEN", "TRUNK", "START", "2018", "2019", "2020", "2021", "REMOTE START", "SUBSCRIPTION REQUIRED",
            "$8 / MONTH", "$80 / YEAR", "CHECKING PAYMENT", "NOT PAID", "MY KEY MY CAR", "NO FOB FEES", "NOT INTENTIONAL", "UNDER REVIEW",
            "25¢ PER START", "YES", "NO"]
ODDITY = "a penguin pushing a shopping cart (with a crate of fish) along the sidewalk behind the driveway"

CAR_COL = (176, 24, 30)                    # Supersonic-red style RAV4
T_DASH_LOCK = Y.screen(["REMOTE START", "SUBSCRIPTION", "REQUIRED"], accent=(255, 70, 60), logo="toyota")
T_DASH_CHECK = [Y.screen(["CHECKING", "PAYMENT..."], bar=b, logo="toyota") for b in (0.15, 0.45, 0.8, 1.0)]
T_DASH_NOT = Y.screen(["PAYMENT", "NOT PAID"], accent=(255, 70, 60), logo="toyota")
T_DASH_OFF = Y.screen([" "], bg=(6, 8, 10))
T_TAG_M = Y.tag("$8 / MONTH", 128, 56)
T_TAG_Y = Y.tag("$80 / YEAR", 128, 56)
T_YEARS = [Y.word(str(y), 96, 48, (20, 20, 20), (250, 230, 60), 30) for y in (2018, 2019, 2020, 2021, 2022)]
T_PROTEST = [Y.word(s, 128, 72, (20, 20, 20), (244, 244, 236)) for s in ("MY KEY\nMY CAR", "NO FOB\nFEES", "MY KEY\nMY CAR", "NO FOB\nFEES", "?!")]
T_STATEMENT = Y.word("TOYOTA\nSTATEMENT:\nNOT\nINTENTIONAL", 96, 128, (20, 20, 20), (250, 250, 246), 15)
T_REVIEW = Y.word("UNDER\nREVIEW", 128, 128, (190, 20, 30), (250, 250, 246), 26, border=(190, 20, 30))
T_METER = Y.word("25¢ PER\nSTART", 64, 40, (255, 120, 60), (16, 20, 24), 11)
T_PLATE = Y._plate("MY KEY")
T_CAL = [Y._calendar(m, "$8") for m in ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")]
STREET_POINTS = [((-3.5, 4.2, -4.0), (255, 200, 140), 9.0), ((4.5, 4.2, -4.0), (255, 200, 140), 9.0), ((0.5, 2.6, 3.0), (200, 210, 255), 7.0),
                 ((-2.0, 2.2, -3.2), (255, 230, 200), 4.5)]

# ---------------------------------------------------------------- sets
def streetlamp(x, z):
    return cat([cyl(0.06, 0.05, 4.2, 6, (50, 50, 56)), cbox(0.35, 4.2, 0, 0.8, 0.1, 0.22, (60, 60, 66)),
                cbox(0.6, 4.12, 0, 0.3, 0.05, 0.18, (255, 220, 150), e=1.0)]).mv(x, 0, z)

def house(x, z, col, w=4.0, lit=(1, 0, 1)):
    s = [box(x - w / 2, 0, z - 3, x + w / 2, 3.0, z, col), box(x - w / 2 - 0.2, 3.0, z - 3.2, x + w / 2 + 0.2, 3.25, z + 0.2, (60, 40, 36))]
    for i, on in enumerate(lit):
        wx = x - w / 2 + 0.7 + i * (w - 1.4) / max(1, len(lit) - 1)
        s.append(box(wx - 0.35, 1.2, z, wx + 0.35, 2.1, z + 0.03, (255, 255, 255), texs={"f": M.T_WIN if on else M.T_WIN_COOL}, e=1.0 if on else 0.2))
    return cat(s)

def penguin_walk(t, z=-4.6):
    x = -2.6 + 0.8 * (t % 10.5)            # crosses frame in the hook, mid-video and the question
    return Y.penguin(t).sc(1.3).mv(x, 0.12, z)

def street(t, odd=True):
    s = [tiles(-14, -3.4, 14, 5, 0, 2.0, M.T_TILE),                                   # driveway / concrete
         tiles(-14, -4.0, 14, -3.4, 0.12, 2.0, -1, (120, 120, 116)),                   # kerb
         box(-14, 0, -4.0, 14, 0.12, -3.95, (150, 150, 146)),
         tiles(-14, -5.2, 14, -4.0, 0.12, 2.0, -1, (110, 110, 108)),                   # sidewalk
         tiles(-14, -12, 14, -5.2, 0.0, 2.0, -1, (40, 40, 46)),                        # road
         *[box(x, 0.005, -8.7, x + 1.6, 0.012, -8.5, (220, 200, 120)) for x in range(-13, 14, 4)],
         house(-6, -13, (150, 140, 120)), house(0, -13, (120, 130, 150), lit=(0, 1, 1)), house(6, -13, (150, 120, 110), lit=(1, 1, 0)),
         streetlamp(-4.0, -4.8), streetlamp(4.0, -4.8),
         box(-14, 0, -4.9, -9, 0.9, -4.8, (60, 90, 50)), box(9, 0, -4.9, 14, 0.9, -4.8, (60, 90, 50))]
    if odd: s.append(penguin_walk(t))
    return s

def lot(t):
    """Toyota dealer lot at night: a row of RAV4s with yellow year placards, the red TOYOTA pylon."""
    s = [tiles(-14, -10, 14, 6, 0, 2.0, -1, (54, 54, 60))]
    s += [box(x - 0.04, 0.005, -3.0, x + 0.04, 0.012, 3.0, (220, 220, 210)) for x in (-6.6, -3.3, 0, 3.3, 6.6)]
    pylon = cat([box(-0.2, 0, -0.2, 0.2, 4.6, 0.2, (60, 60, 66)), box(-1.4, 4.6, -0.12, 1.4, 5.6, 0.12, (255, 255, 255), texs={"f": Y.T_TOY_SIGN, "b": Y.T_TOY_SIGN}, e=1.0)])
    s.append(pylon.mv(2.0, 0, -7.0))
    s += [cat([cyl(0.04, 0.04, 2.5, 5, (200, 200, 200))] + [box(0.0, 2.5 - 0.6 * i, -0.01, 0.5, 2.0 - 0.6 * i, 0.01, F.RAINBOW[i * 2]) for i in range(3)]).mv(x, 0, -4.5) for x in (-8, 8)]
    return s

LOT_POINTS = [((-4, 5, 2), (255, 240, 220), 10.0), ((4, 5, 2), (255, 240, 220), 10.0), ((2, 5, -6), (255, 80, 80), 6.0)]

# ---------------------------------------------------------------- shots: fn(u, t, dt) -> dict
def sh_press(u, t, dt):
    """Close-up: a thumb presses START on the Toyota fob, the button lights blue... (the car behind stays dark)."""
    p = min(1, max(0, (u - 0.25) / 0.15)) if u < 0.7 else max(0, 1 - (u - 0.7) / 0.1)
    fob = Y.fob_toyota(press=p, lit=p > 0.5).rot("x", -12)
    h = cat([fob, Y.hand(), Y.thumb(press=p).mv(-0.06, -0.01, 0.0)]).sc(1.0).rot("y", -15).mv(-0.35, 1.3, 3.6)
    car = Y.rav4(CAR_COL, plate=T_PLATE).rot("y", -100).mv(0.4, 0, -1.2)
    sx, sy, _ = shake(t, 0.006 if 0.3 < u < 0.5 else 0, 9)
    return dict(scene=street(t) + [car, h], cam=Cam((-0.25 + sx, 1.55 + sy, 4.7 - 0.2 * ease(u)), (0.2, 0.9, -1.0), 50),
                bg=Y.NIGHT_BG, fog=(10, 26, (14, 14, 30)), points=STREET_POINTS + [((-0.3, 1.5, 3.9), (120, 200, 255), 0.1 + 1.5 * p)], amb=0.28)

def sh_dark(u, t, dt):
    """Low push-in on the red RAV4 in the driveway: lights stay off, the Toyota badge catches the streetlight."""
    car = Y.rav4(CAR_COL, plate=T_PLATE).rot("y", -100).mv(0.4, 0, -1.2)
    e = ease(u)
    return dict(scene=street(t) + [car], cam=Cam(lerp((1.4, 0.55, 4.8), (0.9, 0.75, 2.6), e), (0.2, 0.75, -1.0), 48, roll=-3 + 3 * e),
                bg=Y.NIGHT_BG, fog=(10, 26, (14, 14, 30)), points=STREET_POINTS, amb=0.26)

def sh_years(u, t, dt):
    """A row of 2018-and-newer RAV4s on the lot, each with a year placard; camera tracks past."""
    s = lot(t)
    cols = [(176, 24, 30), (200, 200, 204), (40, 60, 110), (30, 30, 34), (90, 110, 90)]
    for i in range(5):
        x = -6.6 + 3.3 * i
        s.append(Y.rav4(cols[i]).rot("y", -90).mv(x, 0, 0))
        s.append(box(-0.3, 0, -0.02, 0.3, 0.3, 0.02, (255, 255, 255), texs={"f": T_YEARS[i]}).rot("x", -25).mv(x, 1.55, 1.05))
    x = -5.5 + 9.0 * ease(u)
    return dict(scene=s, cam=Cam((x, 2.7, 9.5), (x + 0.8, 0.9, 0.0), 50), bg=Y.NIGHT_BG, fog=(14, 34, (16, 14, 26)), points=LOT_POINTS, amb=0.32)

def sh_fobwave(u, t, dt):
    """Remote start from the key fob: the fob in hand, rings of radio leave it towards the RAV4."""
    fob = cat([Y.fob_toyota(press=1, lit=True), Y.hand(), Y.thumb(press=1).mv(-0.06, -0.01, 0)]).rot("y", -20).sc(1.0).mv(-0.9, 1.15, 1.6)
    w = Y.waves(t, 4, 0.1, 0.35, r0=0.04).rot("y", -55).mv(-0.65, 1.3, 1.5)
    car = Y.rav4(CAR_COL, plate=T_PLATE).rot("y", -60).mv(1.6, 0, -1.6)
    return dict(scene=street(t) + [car, fob, w], cam=Cam((-1.6 + 0.3 * u, 1.55, 3.4), (0.3, 1.0, -0.6), 52),
                bg=Y.NIGHT_BG, fog=(10, 26, (14, 14, 30)), points=STREET_POINTS + [((-0.8, 1.6, 1.8), (100, 200, 255), 3.0)], amb=0.3)

def dashboard(tid):
    return cat([box(-1.2, 0.6, -0.6, 1.2, 0.95, 0.0, (30, 30, 34)), box(-0.35, 0.95, -0.35, 0.35, 1.35, -0.3, (255, 255, 255), texs={"f": tid}, e=1.0),
                cyl(0.2, 0.2, 0.05, 12, (24, 24, 26), capcol=(24, 24, 26)).rot("x", 70).mv(-0.6, 1.0, -0.15),
                box(-0.75, 0.95, -0.5, -0.45, 1.25, -0.45, (14, 16, 20)), box(-1.3, 0.6, -0.8, 1.3, 1.9, -0.75, (20, 24, 34))])

def sh_locked(u, t, dt):
    """Inside the car: the screen says REMOTE START / SUBSCRIPTION REQUIRED; a padlock drops onto the dash."""
    k = ease(min(1, u * 2.2))
    lock = Y.padlock().sc(0.7).mv(0.5, 0.98 + 0.7 * (1 - k), -0.2)
    sx, sy, _ = shake(t, 0.01 if 0.42 < u < 0.55 else 0, 12)
    return dict(scene=[dashboard(T_DASH_LOCK), lock], cam=Cam((0.15 + sx, 1.35 + sy, 1.75 - 0.25 * u), (0.05, 1.12, -0.3), 46), bg=Y.NIGHT_BG, fog=None,
                points=[((0, 1.15, 0.0), (255, 90, 80), 1.6), ((0.6, 1.6, 0.4), (255, 240, 220), 1.5)], amb=0.22)

def sh_month(u, t, dt):
    """A yellow $8 / MONTH price tag swings off the key fob; coins drop past it."""
    sw = 18 * math.sin(t * 5) * (1 - 0.5 * u)
    fob = Y.fob_toyota().sc(2.2).mv(0, 1.55, 0)
    tagp = cat([box(-0.004, -0.2, -0.004, 0.004, 0.0, 0.004, (230, 230, 230)),
                box(-0.32, -0.5, -0.005, 0.32, -0.2, 0.005, (255, 255, 255), texs={"f": T_TAG_M, "b": T_TAG_M})]).rot("z", sw).mv(0, 1.25, 0.02)
    coins = [Y.coin().rot("x", 90 + 200 * t + i * 40).mv(-0.6 + 0.4 * i, 2.4 - ((t * 2.4 + i * 0.37) % 2.6), 0.3) for i in range(4)]
    return dict(scene=[wall(-3, 0, 3, 4, -0.6, 1.0, M.T_PANEL), fob, tagp, *coins], cam=Cam((0.0, 1.3, 1.9 - 0.25 * u), (0, 1.2, 0), 48),
                bg=E.DEF_BG, fog=None, points=[((0.6, 2.0, 1.2), (255, 240, 220), 4.0)], amb=0.5)

def sh_year(u, t, dt):
    """Twelve calendar pages of $8 fly off; the tag flips to $80 / YEAR."""
    k = min(11, int(u * 16))
    s = [wall(-3, 0, 3, 4, -0.6, 1.0, M.T_PANEL)]
    for i in range(k, 12):
        s.append(box(-0.32, 1.1, -0.5 + 0.002 * (12 - i), 0.32, 1.9, -0.49 + 0.002 * (12 - i), (255, 255, 255), texs={"f": T_CAL[i]}))
    f = (u * 16) % 1
    if k < 11:
        s.append(box(-0.32, -0.8, 0, 0.32, 0, 0.004, (255, 255, 255), texs={"f": T_CAL[k], "b": T_CAL[k]}).rot("x", -f * 120).rot("z", f * 60).mv(f * 0.8, 1.9 + f * 0.5, -0.46 + f))
    fl = min(1, max(0, (u - 0.45) / 0.25))
    tg = box(-0.32, -0.15, -0.005, 0.32, 0.15, 0.005, (255, 255, 255), texs={"f": T_TAG_Y if fl > 0.5 else T_TAG_M, "b": T_TAG_Y}).rot("y", 180 * fl if fl < 0.5 else 180 * fl - 180)
    s.append(tg.mv(0.05, 0.82, 0.4))
    return dict(scene=s, cam=Cam((0.2, 1.35, 2.2), (0.15, 1.3, -0.4), 46), bg=E.DEF_BG, fog=None, points=[((0.6, 2.0, 1.2), (255, 240, 220), 4.0)], amb=0.5)

def sh_radio(u, t, dt):
    """Wide: the owner on the porch steps holds out the fob; radio rings cross the driveway to the car."""
    owner = Y.guy(top=(70, 90, 140), ra=(80, 10, 0), held=Y.fob_toyota().sc(0.8)).rot("y", 150).mv(-3.0, 0, 3.0)
    w = Y.waves(t * 1.4, 5, 0.6, 2.2).rot("y", 60).mv(-2.6, 1.3, 2.3)
    car = Y.rav4(CAR_COL, plate=T_PLATE).rot("y", -100).mv(0.6, 0, -1.2)
    a = math.radians(70 + 25 * ease(u))
    return dict(scene=street(t) + [owner, w, car], cam=Cam((1.0 + 7.5 * math.cos(a), 3.4, 1.0 + 7.5 * math.sin(a)), (-0.6, 0.9, 0.4), 50),
                bg=Y.NIGHT_BG, fog=(12, 30, (14, 14, 30)), points=STREET_POINTS, amb=0.3)

def sh_check(u, t, dt):
    """Inside the car: the screen runs CHECKING PAYMENT... then flashes NOT PAID."""
    i = min(3, int(u * 5))
    tid = T_DASH_NOT if u > 0.72 and int(t * 6) % 2 == 0 else (T_DASH_NOT if u > 0.72 else T_DASH_CHECK[i])
    dash = dashboard(tid)
    sx, sy, _ = shake(t, 0.008 if 0.72 < u < 0.82 else 0, 11)
    return dict(scene=[dash], cam=Cam((0.1 + sx, 1.32 + sy, 0.75 - 0.15 * u), (0, 1.15, -0.3), 52), bg=Y.NIGHT_BG, fog=None,
                points=[((0, 1.15, 0.0), (120, 170, 255) if u < 0.72 else (255, 60, 50), 1.6)], amb=0.18)

def hq(t):
    return [tiles(-10, -6, 10, 6, 0, 2.0, M.T_TILE), wall(-10, 0, 10, 6, -3.0, 2.0, -1, (196, 198, 204)),
            box(-2.4, 3.6, -2.98, 2.4, 5.2, -2.9, (255, 255, 255), texs={"f": Y.T_TOY_SIGN}, e=0.8),
            *[box(x - 0.8, 0.0, -2.96, x + 0.8, 3.0, -2.92, (255, 255, 255), texs={"f": M.T_WIN_COOL}, e=0.3) for x in (-5.5, 5.5)]]
HQ_POINTS = [((0, 4.5, 2.0), (255, 240, 220), 9.0), ((-4, 3, 3), (200, 210, 255), 7.0)]

def sh_backlash(u, t, dt):
    """A crowd outside Toyota HQ waving MY KEY MY CAR / NO FOB FEES signs."""
    s = hq(t)
    for i in range(5):
        x = -2.6 + 1.3 * i; z = 0.8 + 0.4 * (i % 2)
        bob = 0.12 * abs(math.sin(t * 7 + i))
        s.append(M.person(skin=[(220, 180, 150), (150, 100, 70), (200, 160, 120), (120, 80, 56), (230, 190, 160)][i],
                          top=[(150, 40, 40), (40, 90, 60), (60, 60, 140), (200, 150, 40), (90, 60, 120)][i], face=Y.F_ANGRY[i],
                          ra=(160, 0, 0), la=(150, 0, 0)).rot("y", 180).mv(x, bob, z))
        s.append(Y.sign_board(T_PROTEST[i], 0.9, 0.55, 0.9).rot("y", 180).rot("z", 8 * math.sin(t * 6 + i)).mv(x, 1.3 + bob, z - 0.05))
    return dict(scene=s, cam=Cam((0.6 * math.sin(u * 2), 1.4, 6.5 - 1.0 * ease(u)), (0, 1.9, 0), 54), bg=sky((30, 30, 40), (60, 60, 70)),
                fog=(14, 30, (30, 30, 40)), points=HQ_POINTS, amb=0.42)

def sh_statement(u, t, dt):
    """A Toyota spokesperson at a podium holds up the statement: NOT INTENTIONAL."""
    sp = Y.guy(top=(26, 26, 30), skin=(214, 176, 146), hair=(60, 60, 60), ra=(110, 0, 20), la=(40, 0, 60)).mv(0, 0, -1.4)
    podium = cat([box(-0.45, 0, -0.3, 0.45, 1.1, 0.3, (40, 40, 46)), box(-0.3, 0.6, 0.301, 0.3, 0.9, 0.31, (255, 255, 255), texs={"f": Y.T_TOY_BADGE})]).mv(0, 0, -0.6)
    lift = ease(min(1, u * 2))
    doc = box(-0.24, 0, -0.005, 0.24, 0.64, 0.005, (255, 255, 255), texs={"f": T_STATEMENT}).mv(0.3, 1.2 + 0.45 * lift, -1.0)
    mics = [cyl(0.012, 0.012, 0.3, 4, (20, 20, 20)).rot("x", 30).mv(x, 1.1, -0.35) for x in (-0.1, 0.1)]
    flash = ((0, 2, 2), (255, 255, 255), 0.1 + 5.0 * (1 if int(t * 7) % 3 == 0 else 0))
    return dict(scene=hq(t) + [sp, podium, doc, *mics], cam=Cam((0.4, 1.55, 2.6 - 0.8 * ease(u)), (0.15, 1.5, -1.0), 50),
                bg=sky((30, 30, 40), (60, 60, 70)), fog=(14, 30, (30, 30, 40)), points=HQ_POINTS + [flash], amb=0.42)

def sh_review(u, t, dt):
    """A magnifying glass sweeps over the key fob lying on an UNDER REVIEW clipboard."""
    board = cat([box(-0.3, 0, -0.38, 0.3, 0.02, 0.38, (110, 76, 44)), Y.paper(T_REVIEW, 0.5, 0.62).mv(0, 0.021, 0.02),
                 box(-0.12, 0.02, -0.4, 0.12, 0.05, -0.33, (190, 190, 196))])
    fob = Y.fob_toyota().rot("x", -90).mv(0.08, 0.06, 0.12)
    mg = Y.magnifier().sc(0.6).rot("x", -70).mv(0.12 + 0.12 * math.sin(u * 3.5), 0.25, 0.14 + 0.06 * math.cos(u * 3))
    return dict(scene=[tiles(-2, -2, 2, 2, 0, 1.0, M.T_WOOD), board, fob, mg], cam=Cam((0.0, 1.05 - 0.15 * u, 0.62), (0, 0.0, -0.02), 52),
                bg=E.DEF_BG, fog=None, points=[((0.4, 1.2, 0.6), (255, 240, 220), 3.0)], amb=0.5)

def sh_own(u, t, dt):
    """You own the key: the fob on a velvet cushion under a spotlight, slowly turning."""
    cush = cat([cbox(0, 0.9, 0, 0.6, 0.12, 0.6, (150, 20, 40)), cyl(0.2, 0.15, 0.9, 8, (200, 170, 60))])
    fob = Y.fob_toyota().rot("x", -60).rot("y", 30 * math.sin(t * 1.5)).sc(1.4).mv(0, 1.1, 0)
    return dict(scene=[tiles(-4, -4, 4, 4, 0, 2.0, M.T_TILE_DARK), cush, fob], cam=Cam((0.0, 1.5, 1.4 - 0.3 * u), (0, 1.05, 0), 46),
                bg=E.DEF_BG, fog=(4, 10, (12, 10, 14)), points=[((0, 2.6, 0.2), (255, 236, 200), 3.5)], amb=0.25)

def sh_rent(u, t, dt):
    """You rent the button: a coin-op meter now stands on top of the fob's START button; a coin goes in."""
    fob = Y.fob_toyota(press=0.0).rot("x", -90).sc(2.0).mv(0, 0.04, 0)
    m = Y.meter(T_METER).sc(0.32).mv(0.0, 0.08, 0.19)
    k = min(1, u * 1.8)
    c = Y.coin().sc(0.35).rot("x", 90).mv(0, 0.5 - 0.06 * k, 0.4 - 0.12 * k)
    return dict(scene=[tiles(-2, -2, 2, 2, 0, 1.0, M.T_WOOD), fob, m, c if k < 1 else None], cam=Cam((0.35, 0.6, 0.95 - 0.15 * u), (0, 0.25, 0.1), 46),
                bg=E.DEF_BG, fog=None, points=[((0.4, 1.0, 0.8), (255, 240, 220), 3.0)], amb=0.5)

def sh_question(u, t, dt):
    """Back in the driveway: the fob dangles in the foreground, the dark RAV4 behind; penguin passes again."""
    fob = Y.fob_toyota().rot("y", -20).rot("z", 10 * math.sin(t * 3)).sc(1.1)
    car = Y.rav4(CAR_COL, plate=T_PLATE).rot("y", -100).mv(0.4, 0, -1.2)
    a = math.radians(95 - 25 * ease(u))
    eye = (0.4 + 6.0 * math.cos(a), 1.6, 6.0 * math.sin(a) - 0.6)
    fob = fob.mv(eye[0] + 0.85 * (0.3 - eye[0]) / 6.0 - 0.25, 1.35, eye[2] + 0.85 * (-0.4 - eye[2]) / 6.0)
    return dict(scene=street(t) + [car], cam=Cam(eye, (0.3, 1.0, -0.4), 50), bg=Y.NIGHT_BG, fog=(10, 26, (14, 14, 30)), points=STREET_POINTS, amb=0.28)

def sh_yesno(u, t, dt):
    yes = F.button(F.T_YES_BTN, press=max(0, math.sin(t * 6))).rot("y", 180).mv(-0.7, 0, 2.4)
    no = F.button(F.T_NO_BTN, press=max(0, math.sin(t * 6 + 3))).rot("y", 180).mv(0.7, 0, 2.4)
    car = Y.rav4(CAR_COL, plate=T_PLATE).rot("y", -100).mv(0.4, 0, -1.2)
    e = ease(u)
    return dict(scene=street(t) + [car, yes, no], cam=Cam(lerp((0.0, 2.6, 5.4), (0.6, 1.6, 4.6), e), (0, 0.6, 1.2), 50),
                bg=Y.NIGHT_BG, fog=(10, 26, (14, 14, 30)), points=STREET_POINTS + [((0, 1.5, 3.2), (255, 255, 255), 3.0)], amb=0.32)

SHOTS = [
    (0.0, sh_press, "thumb presses START on a Toyota fob, button lights, nothing happens (penguin with cart behind)"),
    (ws(0, 7), sh_dark, "the red RAV4 stays dark in the driveway"),
    (ws(1, 0), sh_years, "row of RAV4s with 2018-2022 placards on a Toyota lot"),
    (ws(1, 4), sh_fobwave, "fob in hand sends radio rings to the car"),
    (ws(1, 10), sh_locked, "car screen: REMOTE START SUBSCRIPTION REQUIRED, padlock drops on the dash"),
    (ws(2, 0), sh_month, "$8 / MONTH tag swings off the fob, coins fall"),
    (ws(2, 9), sh_year, "12 calendar pages fly, tag flips to $80 / YEAR"),
    (ws(3, 0), sh_radio, "owner on the porch, radio rings cross the driveway"),
    (ws(3, 6), sh_check, "car screen: CHECKING PAYMENT... NOT PAID"),
    (ws(4, 0), sh_backlash, "angry crowd with signs outside Toyota HQ"),
    (ws(4, 3), sh_statement, "spokesperson at podium: NOT INTENTIONAL"),
    (ws(4, 8), sh_review, "magnifying glass over fob on UNDER REVIEW clipboard"),
    (ws(5, 0), sh_own, "fob on a velvet cushion (you own the key)"),
    (ws(5, 4), sh_rent, "coin meter on the START button (you rent the button)"),
    (ws(6, 0), sh_question, "fob dangles in front of the dark RAV4"),
    (ws(6, 10), sh_yesno, "YES / NO buttons in front of the RAV4"),
]
SFX = [(0.85, "pop", 0.6), (1.4, "buzzer", 0.5), (ws(1, 0), "whoosh", 0.5), (ws(1, 4), "sparkle", 0.4), (ws(1, 10) + 0.25, "thump", 0.8),
       (ws(2, 0), "coin", 0.8), (ws(2, 0) + 0.4, "coin", 0.6), (ws(2, 9), "whoosh", 0.4), (ws(3, 0), "sparkle", 0.3),
       (ws(3, 6) + 1.4, "buzzer", 0.6), (ws(4, 0), "poof", 0.6), (ws(4, 3), "pop", 0.5), (ws(4, 8), "whoosh", 0.4),
       (ws(5, 0), "ding", 0.6), (ws(5, 4) + 0.45, "coin", 0.9), (ws(6, 10), "pop", 0.6)]

if __name__ == "__main__": E.main(V)
