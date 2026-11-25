"""jeep_wave: bright low-poly narrated short. Oddity (never mentioned): a cow lounging in a lawn chair under a beach
umbrella, reading a newspaper, beside the desert road."""
import math, sys
import numpy as np
from lowpoly import cat, box, cbox, cyl, sphere, tiles, wall, Cam, sky
import ymodels as Y
import cars as C
import engine as E
from engine import ease, lerp, shake
from hero import hero

NAME = "jeep"
V = E.Video(sys.modules[__name__]); ws = V.ws; DUR = V.dur
HOOK = "Jeep drivers have a secret rule."
HOT = {"jeep", "wave", "wave,", "waves", "tradition", "believed", "world", "war", "two", "willys", "unwritten", "rule", "back",
       "brands", "not", "much", "program", "popular", "name", "yes", "no"}
TOPS = [(ws(3, 0), ws(4, 0), "WWII · WILLYS MB"), (ws(4, 0), ws(4, 4), "NO OFFICIAL RULES"), (ws(6, 0), ws(7, 0), "JEEP WAVE OWNER PROGRAM")]
ONSCREEN = ["Jeep (logo wordmark)", "WWII · WILLYS MB", "NO OFFICIAL RULES", "RULES (blank sign)", "JEEP WAVE OWNER PROGRAM",
            "HELLO MY NAME IS JEEP WAVE", "YES", "NO"]
ODDITY = "a cow lounging in a lawn chair under a beach umbrella, reading a newspaper, beside the desert road"
CRASH = [ws(1, 6), ws(7, 0)]
MUSIC_UNDER_DB = 4.0

RED = (230, 56, 40); SAND = (238, 196, 128); SAND2 = (226, 178, 110)
T_RULES = Y.word("RULES:\n\n\n", 160, 128, (30, 30, 36), (252, 250, 240), 24, border=(200, 40, 40))
T_NAMETAG = Y.word("HELLO\nmy name is\nJEEP WAVE", 160, 112, (20, 20, 30), (255, 255, 255), 22, border=(220, 30, 40))
T_PROGRAM = Y.word("JEEP WAVE", 256, 72, (255, 255, 255), (20, 20, 24), 40)
T_WWII = Y.word("1941", 96, 48, (250, 250, 240), (84, 94, 52), 30)
import fmodels as FM

def wrap(x, t, v, L=80.0): return ((x - v * t + L / 2) % L) - L / 2

def desert(t, v=9.0, odd=True, cow_x=-6.0, road_z=0.0):
    s = [tiles(-44, -60, 44, 30, -0.01, 8.0, -1, SAND)]
    s += C.road(-44, 44, road_z - 2.4, road_z + 2.4)
    s += [box(wrap(x, t, v), 0.006, road_z - 0.07, wrap(x, t, v) + 1.8, 0.012, road_z + 0.07, (255, 214, 40)) for x in np.arange(-40, 40, 5.0)]
    for i, x in enumerate(np.arange(-40, 40, 7.0)):
        z = (-5.5 - (i * 37 % 9)) if i % 2 else (5.0 + (i * 23 % 7))
        s.append(C.cactus(1.2 + (i % 3) * 0.4).mv(wrap(x, t, v), 0, z))
    for x, z, w, h in ((-30, -45, 18, 9), (-6, -55, 26, 14), (20, -48, 16, 11), (38, -40, 12, 7)):
        s.append(C.mesa(w, h, 8).mv(x - 0.05 * v * t % 10, 0, z))
    for x, y, z in ((-20, 16, -50), (10, 20, -58), (30, 14, -46)):
        s.append(C.cloud(3.0).mv(x, y, z))
    if odd: s.append(C.lawn_chair_cow(t).rot("y", -30).mv(wrap(cow_x, t, v), 0, -4.6))
    return s

def drive_hero(expr="smile", t=0.0, **kw):
    kw.setdefault("la", (55, 4, 40)); kw.setdefault("ra", (55, 4, 40))
    return C.hero_seat(hero(expr, sit=True, bob=0.015 * math.sin(t * 17), **kw))

def yellow_jeep(t, expr="smile", **kw):
    return C.wrangler(C.JEEP_YELLOW, spin=-t * 900, driver=drive_hero(expr, t, **kw))

def red_jeep(t, wave=0.0, kind="beard"):
    a = 150 + 18 * math.sin(t * 16) if wave else 0
    d = C.driver(kind, ra=(0, a, 20)) if wave else C.driver(kind, ra=(45, 4, 30), la=(45, 4, 30))
    return C.wrangler(RED, spin=-t * 900, driver=C.seat(d))

# ---------------------------------------------------------------- shots
def sh_hook(u, t, dt):
    """Low front 3/4: Yub cruises in a yellow Wrangler through the desert, smug little smile."""
    car = yellow_jeep(t, "smug", head=(-15, 0, 0))
    e = ease(u)
    return dict(scene=desert(t) + [car], cam=Cam(lerp((2.9, 1.5, -2.9), (2.4, 1.6, -2.5), e), (-0.5, 1.55, -0.45), 56, roll=-3))

def sh_secret(u, t, dt):
    """Close-up in the Jeep: 'secret rule?' — he raises an eyebrow and glances around."""
    look = "l" if u < 0.5 else "r"
    car = yellow_jeep(t, "confused", look=look, head=(12 * math.sin(t * 5), 0, 6))
    return dict(scene=desert(t) + [car], cam=Cam((1.2, 1.95, -1.25), (-0.62, 1.9, -0.42), 50))

def sh_pass(u, t, dt):
    """Wide: a red Wrangler comes the other way in the next lane."""
    xr = 18 - 26 * ease(u)
    red = red_jeep(t).rot("y", 180).mv(xr, 0, 1.3)
    car = yellow_jeep(t, "smile").mv(0, 0, -1.3)
    return dict(scene=desert(t) + [car, red], cam=Cam((-6.5, 2.6, -5.0), (3.0, 0.9, 0.5), 50))

def sh_wave(u, t, dt):
    """The red Jeep's bearded driver gives the wave, right at us."""
    red = red_jeep(t, wave=1).rot("y", 180).mv(1.2 - 1.6 * u, 0, 0)
    marks = C.wave_marks(t).rot("y", -90).mv(0.6 - 1.6 * u, 2.25, 0.95)
    return dict(scene=desert(t, odd=False) + [red, marks], cam=Cam((-2.4 - 1.6 * u, 1.75, -1.6), (0.4 - 1.6 * u, 1.55, 0.4), 44))

def sh_panic(u, t, dt):
    """JOKE: Yub panics — sweat, hands off the wheel, flailing, head whipping."""
    f = math.sin(t * 22)
    car = yellow_jeep(t, "panic", sweat=True, la=(20, 60 + 40 * f, 50), ra=(20, 60 - 40 * f, 50), head=(20 * f, 0, 8 * f))
    sx, sy, _ = shake(t, 0.03)
    return dict(scene=desert(t) + [car], cam=Cam((1.3 + sx, 1.8 + sy, -1.5), (-0.6, 1.5, -0.42), 48))

def sh_tradition(u, t, dt):
    """Overlook: six Wranglers in a row, every driver waving in sync."""
    cols = [(255, 196, 20), (230, 56, 40), (40, 150, 230), (60, 190, 90), (250, 120, 30), (180, 80, 200)]
    s = desert(0.0, 0.0, odd=False)
    kinds = ["beard", "cap", "granny", "beard", "cap", "granny"]
    for i, c in enumerate(cols):
        a = 150 + 20 * math.sin(t * 14 + i * 0.7)
        d = C.driver(kinds[i], ra=(0, a, 20))
        s.append(C.wrangler(c, driver=C.seat(d)).rot("y", -80).mv(-7.5 + 3.0 * i, 0, -2.0))
    x = -4 + 7 * ease(u)
    return dict(scene=s, cam=Cam((x, 2.4, 6.0), (x + 0.5, 1.2, -2.0), 50))

def sh_ww2(u, t, dt):
    """'World War Two': a 1941 Willys MB with a soldier at the wheel on a dirt track, white star on the hood."""
    d = C.driver("soldier", ra=(45, 4, 30), la=(45, 4, 30))
    w = C.willys(spin=-t * 800, driver=C.seat(d, -0.68, 0.7, -0.32, 0.6))
    s = desert(t, 7.0, odd=False) + [w]
    e = ease(u)
    return dict(scene=s, cam=Cam(lerp((4.6, 1.2, 3.0), (3.4, 1.5, 2.2), e), (0, 0.95, 0), 50), bg=sky((90, 160, 235), (236, 220, 190)))

def sh_willys(u, t, dt):
    """Two Willys pass each other; the soldiers wave."""
    a = 150 + 18 * math.sin(t * 15)
    w1 = C.willys(spin=-t * 800, driver=C.seat(C.driver("soldier", ra=(0, a, 20)), -0.68, 0.7, -0.32, 0.6)).mv(0, 0, -1.3)
    w2 = C.willys(spin=-t * 800, driver=C.seat(C.driver("soldier", ra=(0, a, 20)), -0.68, 0.7, -0.32, 0.6)).rot("y", 180).mv(6 - 9 * u, 0, 1.3)
    return dict(scene=desert(t, 7.0, odd=False) + [w1, w2], cam=Cam((-5.5, 2.2, -4.5), (2.0, 1.0, 0.3), 48), bg=sky((90, 160, 235), (236, 220, 190)))

def sh_rules(u, t, dt):
    """JOKE: 'The unwritten rule' — Yub, parked, reads a roadside RULES sign. It's blank. He squints."""
    sign = Y.sign_board(T_RULES, 1.6, 1.3, 1.5).mv(0.0, 0, -3.2)
    turn = ease(min(1, max(0, (u - 0.35) / 0.25)))
    h = hero("confused" if u < 0.6 else "deadpan", look="c", head=(0, -6, 6 * turn), ra=(0, 15, 140)).rot("y", 210 - 170 * turn).mv(1.0, 0, -1.5)
    car = C.wrangler(C.JEEP_YELLOW).rot("y", 90).mv(-2.6, 0, -2.2)
    return dict(scene=desert(0, 0, odd=False) + [sign, h, car], cam=Cam((2.9 - 0.3 * u, 1.7, 1.0), (0.5, 1.75, -2.3), 50))

def sh_waveback(u, t, dt):
    """'A Jeep driver waves, you wave back': red driver waves (left), Yub waves back proudly (right)."""
    a = 150 + 18 * math.sin(t * 16)
    red = red_jeep(t, wave=1).rot("y", 180).mv(1.0 - 5 * u, 0, 2.2)
    hy = 1 if t > ws(4, 7) else 0
    car = yellow_jeep(t, "grin" if hy else "smile", la=(0, a, 20) if hy else (55, 4, 40), wave="l" if hy else None, blush=bool(hy)).mv(0, 0, -1.3)
    return dict(scene=desert(t) + [car, red], cam=Cam((2.0, 2.15, -3.5), (-0.6, 1.9, -1.4), 54))

def sh_tesla(u, t, dt):
    """JOKE: Yub waves enthusiastically at a white Tesla Model 3. The Tesla driver stares straight ahead."""
    a = 150 + 22 * math.sin(t * 18)
    car = yellow_jeep(t, "grin", la=(0, a, 20), wave="l", head=(-30, 0, 0)).mv(0, 0, -1.3)
    tes = Y.model3().rot("y", 180).mv(1.5 - 7 * u, 0, 2.4)
    return dict(scene=desert(t, cow_x=8.0) + [car, tes], cam=Cam((2.0, 2.15, -3.5), (-0.7, 1.85, -1.2), 54))

def sh_nothing(u, t, dt):
    """'Not so much': close-up — the wave slowly dies, deadpan stare, a tumbleweed rolls past."""
    k = ease(min(1, u * 1.4))
    a = 150 - 110 * k
    car = yellow_jeep(t, "deadpan" if k > 0.4 else "smile", la=(0, a, 20 + 40 * k), wave="l", head=(-10 * (1 - k), 0, 0))
    weed = sphere(0.35, 6, 4, (170, 130, 70)).rot("z", -t * 400).mv(3.0 - 6 * u, 0.35, 1.2)
    return dict(scene=desert(t) + [car, weed], cam=Cam((1.4, 1.7, -1.6), (-0.6, 1.55, -0.42), 46))

def sh_program(u, t, dt):
    """'Jeep even named an owner program Jeep Wave': a big Jeep sign and a JEEP WAVE banner; Yub looks up, impressed."""
    sign = cat([box(-0.15, 0, -0.15, 0.15, 3.2, 0.15, (60, 60, 66)), box(-2.0, 3.2, -0.1, 2.0, 4.7, 0.1, (255, 255, 255), texs={"f": C.T_JEEP_WORD_SIGN})]).mv(-1.0, 0, -6)
    ban = box(-1.8, 0, -0.05, 1.8, 0.75, 0.05, (255, 255, 255), texs={"f": T_PROGRAM}).mv(-1.0, 2.2, -5.85)
    hand = cat([cbox(0, 0.4, 0, 0.5, 0.6, 0.15, (255, 200, 40)), *[cbox(-0.18 + 0.12 * i, 0.85, 0, 0.09, 0.35, 0.12, (255, 200, 40)) for i in range(4)],
                cbox(0.32, 0.5, 0, 0.12, 0.3, 0.12, (255, 200, 40)).rot("z", -40, (0.25, 0.4, 0))]).rot("z", 15 * math.sin(t * 6), (0, 0.1, 0)).mv(1.8, 3.1, -5.9)
    h = hero("shock" if u < 0.4 else "grin", look="u", head=(0, -15, 0)).rot("y", 150).mv(1.6, 0, -1.4)
    cars_ = [C.wrangler(c).rot("y", 60).mv(x, 0, -9) for c, x in (((40, 150, 230), -5.5), ((60, 190, 90), 3.5))]
    return dict(scene=desert(0, 0, odd=False) + [sign, ban, hand, h] + cars_, cam=Cam((0.9, 0.9 + 0.3 * u, 2.6), (-0.4, 2.95, -5.5), 54))

def _giant_hand(t, tag=0.0):
    h = cat([cbox(0, 1.5, 0, 1.6, 2.0, 0.5, (255, 200, 40)), *[cbox(-0.6 + 0.4 * i, 3.1, 0, 0.32, 1.4, 0.4, (255, 200, 40)) for i in range(4)],
             cbox(1.05, 1.8, 0, 0.4, 1.0, 0.4, (255, 200, 40)).rot("z", -40, (0.8, 1.4, 0)), cbox(0, 0.25, 0, 1.0, 0.5, 0.6, (120, 120, 130))])
    s = [h.rot("z", 6 * math.sin(t * 4), (0, 0.5, 0))]
    if tag > 0:
        s.append(box(-0.55, -0.4, 0.26, 0.55, 0.4, 0.28, (255, 255, 255), texs={"f": T_NAMETAG}).sc(0.5 + 0.5 * tag).mv(0, 1.5, 0))
    return cat(s)

def sh_popular(u, t, dt):
    """'A wave so popular': a giant yellow waving-hand monument in the desert, crowds of Jeeps around it."""
    s = desert(0, 0, odd=False) + [_giant_hand(t).mv(0, 0, -6)]
    for i, (c, a) in enumerate((((230, 56, 40), 40), ((40, 150, 230), -40), ((60, 190, 90), 120), ((180, 80, 200), -120))):
        r = 5.0; s.append(C.wrangler(c).rot("y", a).mv(r * math.sin(math.radians(a)), 0, -6 + r * math.cos(math.radians(a)) * 0.6))
    e = ease(u)
    return dict(scene=s, cam=Cam(lerp((-3.0, 1.0, 5.0), (2.0, 1.6, 4.0), e), (0, 2.6, -6), 56))

def sh_name(u, t, dt):
    """'...the company put a name on it': Yub slaps a HELLO MY NAME IS: JEEP WAVE tag on the giant hand. Proud."""
    k = ease(min(1, u * 3))
    hm = _giant_hand(t, tag=k).mv(0, 0, -2.0)
    h = hero("proud", la=(70 * k, 10, 10), ra=(0, 8, 10)).rot("y", -25).mv(1.5, 0, -0.9)
    sx, sy, _ = shake(t, 0.03 if 0.3 < u < 0.4 else 0)
    return dict(scene=desert(0, 0, odd=False) + [hm, h], cam=Cam((2.6 + sx, 1.7 + sy, 4.4), (0.2, 1.7, -1.6), 50))

def sh_brands(u, t, dt):
    """'Should every car brand have a wave?': Yub at the roadside waving hopefully at a Tesla, a Toyota, a Hyundai, a Chevy."""
    a = 150 + 20 * math.sin(t * 15)
    h = hero("grin", ra=(0, a, 20), wave="r", head=(-30, 0, 0)).rot("y", 35).mv(3.4, 0, -3.8)
    lst = [Y.model3(), Y.rav4((40, 120, 220)), C.ioniq5n(), C.equinox()]
    cars_ = [c.mv(-30 + 30 * u + i * 6.5, 0, -1.2) for i, c in enumerate(lst)]
    return dict(scene=desert(t, 0.0, cow_x=-9.0) + [h] + cars_, cam=Cam((6.8, 1.7, -5.6), (0.5, 1.2, -1.6), 52))

def sh_question(u, t, dt):
    """'Yes, or no?': Yub between a green YES sign and a red NO sign, shrugging."""
    up = t > ws(8, 7)
    h = hero("smug" if up else "smile", la=(25, 55, 80), ra=(25, 55, 80), head=(0, 0, 8 * math.sin(t * 4)))
    yes = Y.sign_board(FM.T_YES_BTN, 0.75, 0.75, 1.0).mv(-0.95, 0, -0.3); no = Y.sign_board(FM.T_NO_BTN, 0.75, 0.75, 1.0).mv(0.95, 0, -0.3)
    car = C.wrangler(C.JEEP_YELLOW).rot("y", 70).mv(-2.6, 0, -3.5)
    return dict(scene=desert(0, 0, cow_x=-5.0) + [h, yes, no, car], cam=Cam((0.0, 1.5, 4.3 - 0.3 * u), (0, 1.25, 0), 50))

SHOTS = [
    (0.0, sh_hook, "Yub cruises in a yellow Wrangler (cow in lawn chair behind)"),
    (1.3, sh_secret, "close-up: Yub raises an eyebrow, looks around"),
    (ws(1, 0), sh_pass, "red Wrangler approaches in the other lane"),
    (ws(1, 5) - 0.05, sh_wave, "red Jeep's driver waves at camera"),
    (ws(1, 6) + 0.45, sh_panic, "JOKE: Yub panics, sweat, hands flailing"),
    (ws(2, 3), sh_tradition, "six Wranglers in a row, all drivers waving"),
    (ws(3, 0), sh_ww2, "1941 Willys MB with soldier driver, star on hood"),
    (ws(3, 9) - 0.1, sh_willys, "two Willys pass, soldiers wave"),
    (ws(4, 0), sh_rules, "JOKE: blank RULES sign, Yub squints"),
    (ws(4, 3) - 0.1, sh_waveback, "red driver waves, Yub waves back proudly"),
    (ws(5, 0), sh_tesla, "JOKE: Yub waves at a Tesla, driver ignores him"),
    (ws(5, 2) - 0.1, sh_nothing, "wave dies, deadpan, tumbleweed"),
    (ws(6, 0), sh_program, "Jeep sign + JEEP WAVE banner, Yub impressed"),
    (ws(7, 0), sh_popular, "giant waving-hand monument circled by Jeeps"),
    (ws(7, 6) - 0.1, sh_name, "JOKE: Yub slaps a HELLO MY NAME IS JEEP WAVE tag on it"),
    (ws(8, 0), sh_brands, "Yub waves at a Tesla, Toyota, Hyundai and Chevy"),
    (ws(8, 7) - 0.15, sh_question, "Yub with YES / NO paddles, shrugging"),
]
SFX = [(ws(1, 6), "honk", 0.5), (ws(1, 6) + 0.5, "boing", 0.7), (ws(1, 6) + 0.6, "screech", 0.4), (ws(2, 3), "whoosh", 0.4),
       (ws(3, 0), "vroom", 0.35), (ws(4, 0) + 0.6, "crickets", 0.9), (ws(4, 7), "sparkle", 0.4), (ws(5, 0) + 0.2, "whoosh", 0.4),
       (ws(5, 2), "crickets", 1.0), (ws(6, 0), "ding", 0.5), (ws(7, 0), "confetti", 0.5), (ws(7, 6) + 0.25, "stamp", 0.8),
       (ws(7, 10) + 0.25, "rimshot", 0.7), (ws(8, 0), "honk", 0.35), (ws(8, 7), "pop", 0.5), (ws(8, 9), "pop", 0.5)]

if __name__ == "__main__": E.main(V)
