"""ioniq_fake_gears: bright low-poly narrated short. Oddity (never mentioned): a snowman in sunglasses relaxing on a sun
lounger in the sunny infield, sipping a drink and not melting."""
import math, sys
import numpy as np
from PIL import Image, ImageDraw
from lowpoly import P, cat, box, cbox, cyl, sphere, tiles, Cam, sky, tex, font
import ymodels as Y
import fmodels as FM
import cars as C
import engine as E
from engine import ease, lerp, shake
from hero import hero

NAME = "ioniq"
V = E.Video(sys.modules[__name__]); ws = V.ws; DUR = V.dur
HOOK = "Hyundai made an electric car with a fake gearbox."
HOT = {"hyundai", "fake", "gearbox", "gearbox.", "ioniq", "fast", "e-shift", "eight-speed", "motors", "engine", "exhaust", "sounds",
       "miss", "shifts", "sixty", "three", "point", "five", "slower", "purpose", "genius", "gimmick"}
TOPS = [(ws(2, 0), ws(3, 0), "N e-Shift"), (ws(3, 0), ws(4, 0), "N ACTIVE SOUND+"), (ws(5, 0), ws(6, 0), "CAR AND DRIVER TEST")]
ONSCREEN = ["HYUNDAI", "N logo", "N e-SHIFT", "gear display 1-8", "MISSED SHIFT", "N ACTIVE SOUND+", "CAR AND DRIVER TEST",
            "0-60 MPH", "e-SHIFT ON 3.5 s", "FAKE (stamp)", "GENIUS", "GIMMICK"]
ODDITY = "a snowman in sunglasses relaxing on a sun lounger in the sunny infield, sipping a drink, not melting"
CRASH = [ws(1, 6), ws(6, 0)]
MUSIC_UNDER_DB = 4.0

GRASS = (100, 200, 90); ASPH = (88, 90, 100)

def _gauge(gear, missed=False):
    w, h = 320, 160
    im = Image.new("RGB", (w, h), (14, 18, 30)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 26), fill=(30, 40, 66)); d.text((10, 13), "N e-SHIFT", font=font(18), fill=(255, 255, 255), anchor="lm")
    d.polygon([(w - 40, 4), (w - 20, 4), (w - 34, 22)], fill=(230, 40, 50))
    for i in range(12):                                   # rpm bar
        c = (60, 200, 255) if i < 8 else (255, 200, 40) if i < 10 else (255, 60, 60)
        on = i < (3 + (gear * 7) % 9) if not missed else i < 11
        d.rectangle((14 + i * 25, 36, 34 + i * 25, 52), fill=c if on else (40, 46, 60))
    if missed:
        d.text((w / 2, 106), "MISSED", font=font(52), fill=(255, 70, 70), anchor="mm"); d.text((w / 2, 146), "SHIFT!", font=font(22), fill=(255, 200, 200), anchor="mm")
    else:
        d.text((w / 2, 108), str(gear), font=font(96), fill=(255, 255, 255), anchor="mm"); d.text((w - 40, 140), "/8", font=font(22), fill=(160, 170, 190), anchor="mm")
    return tex(im)
T_GEAR = [None] + [_gauge(g) for g in range(1, 9)]
T_MISSED = _gauge(3, True)
T_FAKE = Y.word("FAKE", 160, 64, (230, 30, 40), (250, 248, 240), 44, border=(230, 30, 40))
T_8SPD = Y.word("8-SPEED", 160, 48, (30, 30, 36), (250, 210, 40), 30)
T_060 = Y.word("0-60 MPH", 256, 64, (255, 255, 255), (20, 24, 34), 40)
T_35 = Y.word("e-SHIFT ON\n3.5 s", 256, 128, (255, 220, 40), (20, 24, 34), 44)
T_GENIUS = Y.word("GENIUS", 160, 64, (255, 255, 255), (40, 170, 70), 38)
T_GIMMICK = Y.word("GIMMICK", 160, 64, (255, 255, 255), (220, 40, 50), 36)
T_HYU_BANNER = C.T_HYUNDAI_SIGN

def track(t, v=0.0, odd=True, sx=0.0):
    off = lambda x, L=80: ((x - v * t + L / 2) % L) - L / 2
    s = [tiles(-46, -60, 46, 40, -0.01, 8.0, -1, GRASS), tiles(-46, -4.0, 46, 4.0, 0.0, 4.0, -1, ASPH)]
    for k, x in enumerate(np.arange(-40, 40, 1.6)):
        col = (230, 40, 50) if k % 2 else (250, 250, 250)
        s += [box(off(x), 0.0, -4.4, off(x) + 1.6, 0.05, -4.0, col), box(off(x), 0.0, 4.0, off(x) + 1.6, 0.05, 4.4, col)]
    s += [box(off(x), 0.004, -0.06, off(x) + 2.0, 0.01, 0.06, (250, 250, 250)) for x in np.arange(-40, 40, 6.0)]
    # grandstand with crowd and Hyundai banners
    gs = [box(-30, 0, -16 - i * 1.2, 30, 0.8 + i * 0.8, -15 - i * 1.2, (200, 206, 220)) for i in range(4)]
    rng = np.random.default_rng(3)
    for i in range(4):
        for x in np.arange(-28, 28, 1.1):
            c = tuple(int(v) for v in rng.choice([(230, 60, 60), (60, 120, 230), (250, 200, 40), (60, 190, 90), (240, 240, 240), (200, 90, 200)]))
            gs.append(cbox(x + rng.uniform(-0.2, 0.2), 1.0 + i * 0.8 + 0.25 * math.sin(t * 6 + x), -15.6 - i * 1.2, 0.4, 0.5, 0.3, c))
    for x in (-20, -6, 8, 22):
        gs.append(box(x - 3, 0.2, -14.0, x + 3, 1.7, -13.9, (255, 255, 255), texs={"f": T_HYU_BANNER}))
    s += [cat(gs).mv(off(0, 160) * 0.0 + sx, 0, 0)]
    for x in (-34, -26, 26, 34): s.append(C.tree(4.0).mv(x, 0, -10))
    for x, y, z in ((-20, 16, -50), (10, 20, -58), (30, 14, -46)): s.append(C.cloud(3.0).mv(x, y, z))
    if odd: s.append(C.snowman_lounger(t).rot("y", -150).mv(off(-7.0) if v else -7.0, 0, 7.0))
    return s

def car_at(t, x=0.0, z=0.0, v=0.0, yaw=0.0):
    return C.ioniq5n(spin=-t * (1200 if v else 0)).rot("y", yaw).mv(x, 0, z)

def cockpit(gear_tid, t, expr="smile", ra=(55, 4, 40), la=(55, 4, 40), head=(0, 0, 0), jolt=0.0, **kw):
    """Inside the Ioniq 5 N: dash, wide screen with the e-Shift gear display, wheel with paddles; Yub in the driver seat."""
    hw = 0.95
    dash = [box(0.55, 0.75, -hw, 1.25, 1.18, hw, (30, 32, 40)), box(0.62, 1.18, -0.85, 0.66, 1.42, 0.05, (255, 255, 255), texs={"l": gear_tid}, e=1.0),
            box(0.66, 1.16, -0.88, 0.72, 1.44, 0.08, (20, 22, 28)), box(-1.5, 0.2, -hw, 1.3, 0.4, hw, (40, 42, 52)),
            box(-1.4, 0.4, -hw - 0.05, 1.3, 1.2, -hw, (60, 120, 190))]
    seat = [box(-0.9, 0.55, -0.7, -0.35, 0.75, -0.15, (30, 30, 36)), box(-0.95, 0.75, -0.7, -0.8, 1.55, -0.15, (30, 30, 36)),
            box(-0.97, 1.2, -0.66, -0.94, 1.5, -0.19, (226, 34, 46))]
    sw = cat([C.steering(0.19), cbox(0.0, 0.0, -0.17, 0.08, 0.06, 0.02, (226, 34, 46)), cbox(0.0, 0.0, 0.17, 0.08, 0.06, 0.02, (226, 34, 46))]).rot("z", 70).mv(0.22, 1.16, -0.42)
    h = C.hero_seat(hero(expr, sit=True, la=la, ra=ra, head=head, lean=-14 * jolt, **kw))
    return [*dash, *seat, sw, h]

def SCREEN_CAM(): return Cam((-0.9, 1.75, 0.55), (0.62, 1.3, -0.4), 44)     # over Yub's shoulder onto the gear display
def FACE_CAM(): return Cam((1.15, 1.7, 0.35), (-0.62, 1.55, -0.42), 52)       # from the passenger side of the dash

# ---------------------------------------------------------------- shots
def sh_hook(u, t, dt):
    """Yub leans on a Performance Blue Ioniq 5 N on the start straight, smug; banners and crowd behind."""
    car = car_at(t, 0, 0, yaw=-25)
    h = hero("smug", la=(10, 20, 100), ra=(10, 20, 100), head=(10, 0, 4)).rot("y", -20).mv(1.3, 0, 1.55)
    e = ease(u)
    return dict(scene=track(t) + [car, h], cam=Cam(lerp((4.6, 1.3, 5.6), (4.0, 1.4, 4.9), e), (0.4, 1.15, 0.2), 52))

def _gearbox(stamp=0.0):
    g = [box(-0.5, 0, -0.35, 0.5, 0.6, 0.35, (170, 176, 190)), box(-0.5, 0.6, -0.36, 0.5, 0.75, 0.36, (140, 146, 160)),
         box(-0.3, 0.75, -0.04, 0.3, 0.9, 0.04, (255, 255, 255), texs={"f": T_8SPD})]
    g += [cyl(0.14, 0.14, 0.04, 10, (210, 214, 224), capcol=(120, 124, 140)).rot("x", 90).mv(x, 0.32, 0.37) for x in (-0.25, 0.05, 0.3)]
    g.append(cyl(0.025, 0.025, 0.5, 6, (40, 40, 44)).mv(0, 0.75, 0)); g.append(sphere(0.07, 8, 5, (24, 24, 28)).mv(0, 1.27, 0))
    if stamp > 0: g.append(box(-0.5, 0, -0.01, 0.5, 0.4, 0.01, (255, 255, 255), texs={"f": T_FAKE}).rot("z", 12).sc(0.6 + 0.4 * stamp).mv(0, 0.3, 0.42))
    return cat(g)

def sh_fakebox(u, t, dt):
    """'fake gearbox': a shiny 8-speed gearbox on a plinth; a big FAKE stamp slams onto it. Yub, shocked."""
    k = ease(min(1, max(0, (u - 0.35) / 0.15)))
    gb = _gearbox(k).mv(0, 0.8, 0)
    plinth = box(-0.7, 0, -0.5, 0.7, 0.8, 0.5, (250, 250, 250))
    h = hero("shock" if k > 0.5 else "smile", la=(30, 30, 80), ra=(30, 30, 80)).rot("y", -30).mv(1.4, 0, 0.6)
    sx, sy, _ = shake(t, 0.03 if 0.35 < u < 0.5 else 0)
    return dict(scene=track(0, odd=False) + [gb, plinth, h], cam=Cam((0.8 + sx, 1.7 + sy, 4.4), (0.5, 1.25, 0.0), 50))

def sh_fast(u, t, dt):
    """'a fast EV': the Ioniq 5 N blasts down the straight past the camera."""
    x = -3 + 8 * ease(u)
    car = car_at(t, x, -1.5, v=1)
    return dict(scene=track(t) + [car], cam=Cam((3.0, 0.8, 2.6), (x, 0.8, -1.5), 52, roll=-4))

def sh_whoosh(u, t, dt):
    """JOKE: Yub trackside; the car zooms past and spins him round, glasses askew."""
    x = -14 + 30 * u
    spin = 360 * ease(min(1, max(0, (u - 0.3) / 0.5)))
    h = hero("shock", sweat=True, la=(0, 40, 20), ra=(0, 40, 20)).rot("y", spin).mv(0, 0, 5.0)
    car = car_at(t, x, 1.5, v=1)
    return dict(scene=track(t) + [h, car], cam=Cam((2.6, 1.6, 9.2), (0, 1.2, 4.0), 48))

def sh_eshift(u, t, dt):
    """Cockpit: the dash screen reads N e-SHIFT and the gear number climbs 1..8 as Yub flicks the paddle."""
    g = 1 + min(7, int(u * 8))
    flick = 1 if (u * 8) % 1 < 0.25 else 0
    jolt = max(0, 1 - ((u * 8) % 1) / 0.25)
    sc = cockpit(T_GEAR[g], t, "grin", ra=(55 + 8 * flick, 4, 40), jolt=jolt * 0.6)
    cam = SCREEN_CAM() if u < 0.55 else FACE_CAM()
    return dict(scene=sc + track(t, 6, odd=False), cam=cam)

def sh_motors(u, t, dt):
    """'by controlling the motors': X-ray Ioniq; front and rear motors glow; their torque dips at every 'shift'."""
    car = C.ioniq5n((140, 180, 220))
    pulse = 0.4 + 0.6 * ((u * 6) % 1)
    motors = [cat([cyl(0.32, 0.32, 0.7, 12, (255, 200, 40), e=pulse, capcol=(200, 140, 20)).rot("x", 90).mv(x, 2.5, 0.35),
                   box(x - 0.03, 1.7, -0.03, x + 0.03, 2.2, 0.03, (255, 220, 120), e=0.8)]) for x in (1.5, -1.45)]
    bars = [box(-0.55 + 0.24 * i, 3.1, -0.05, -0.37 + 0.24 * i, 3.1 + 0.9 * (((i + u * 6) % 3) / 3 + 0.2), 0.05, (60, 200, 255), e=1.0) for i in range(5)]
    return dict(scene=track(0, odd=False) + [car, *motors, *bars], cam=Cam((4.4, 2.6, 6.2), (0, 2.0, 0), 50))

def sh_speakers(u, t, dt):
    """'fake engine and exhaust sounds': the tailpipes are loudspeakers, sound rings blasting out the back."""
    car = car_at(t, 0, 0, yaw=0)
    spk = [cat([cyl(0.12, 0.12, 0.12, 10, (30, 30, 34), capcol=(60, 60, 66)).rot("z", 90).mv(-2.32, 0.38, z),
                cyl(0.07, 0.07, 0.02, 10, (180, 180, 190)).rot("z", 90).mv(-2.45, 0.38, z)]) for z in (-0.5, 0.5)]
    rings = [Y.waves(t, 3, 0.16, 0.7, (255, 220, 60), r0=0.05).rot("y", -90).mv(-2.6, 0.4, z) for z in (-0.5, 0.5)]
    return dict(scene=track(t, odd=False) + [car, *spk, *rings], cam=Cam((-5.0, 1.0, 2.6), (-1.6, 0.6, 0.0), 48))

def sh_vroom(u, t, dt):
    """Yub in the seat, eyes shut, air-drumming to the fake engine sound."""
    f = math.sin(t * 20)
    sc = cockpit(T_GEAR[4], t, "grin", ra=(70 + 25 * f, 20, 60), la=(70 - 25 * f, 20, 60), head=(0, 10 * f, 0), blush=True)
    return dict(scene=sc + track(t, 6, odd=False), cam=FACE_CAM())

def sh_miss(u, t, dt):
    """JOKE: Yub yanks the paddle — the screen says MISSED SHIFT, the car lurches, his head snaps forward, panic."""
    missed = u > 0.2
    jolt = 0 if u < 0.2 else max(0, math.sin((u - 0.2) * 14) * math.exp(-(u - 0.2) * 3))
    sc = cockpit(T_MISSED if missed else T_GEAR[3], t, "panic" if missed else "smile", sweat=missed, jolt=jolt,
                 ra=(80, 30, 70) if missed else (55, 4, 40), la=(80, 30, 70) if missed else (55, 4, 40))
    sx, sy, _ = shake(t, 0.02 * jolt)
    c = SCREEN_CAM() if u < 0.5 else FACE_CAM(); c.eye = c.eye + np.float32([sx, sy, 0])
    return dict(scene=sc + track(t, 3 * (1 - u), odd=False), cam=c)

def _timing(tid, pole_lights=0):
    tw = [box(-0.15, 0, -0.15, 0.15, 3.0, 0.15, (60, 62, 70)), box(-1.6, 3.0, -0.08, 1.6, 4.6, 0.08, (255, 255, 255), texs={"f": tid}, e=0.6)]
    return cat(tw)

def sh_test(u, t, dt):
    """'Car and Driver': drag strip, timing tower reading 0-60 MPH, the Ioniq lined up at the lights."""
    tree = cat([box(-0.08, 0, -0.08, 0.08, 1.8, 0.08, (40, 40, 44))] +
               [sphere(0.09, 6, 4, (255, 200, 40) if i < int(u * 4) else (60, 60, 60), e=1.0 if i < int(u * 4) else 0).mv(0, 1.0 + 0.22 * i, 0.1) for i in range(3)] +
               [sphere(0.09, 6, 4, (60, 230, 90) if u > 0.85 else (60, 60, 60), e=1.0 if u > 0.85 else 0).mv(0, 1.66, 0.1)])
    car = car_at(t, -1.0, -1.5)
    return dict(scene=track(t, odd=True) + [car, _timing(T_060).mv(-5.4, 0, -7.0), tree.mv(1.8, 0, 0.0)], cam=Cam((5.4, 1.5, 4.6), (-0.8, 1.6, -2.0), 52))

def sh_time(u, t, dt):
    """'sixty took three point five seconds': the car launches; the board flips to e-SHIFT ON 3.5 s."""
    x = -1.0 + 16 * ease(u) ** 2
    car = car_at(t, x, -1.5, v=1)
    board = _timing(T_35 if u > 0.45 else T_060).mv(-1.8, 0, -7.0)
    return dict(scene=track(t) + [car, board], cam=Cam((5.0, 1.7, 6.4), (0.4, 2.2, -2.6), 54))

def sh_slower(u, t, dt):
    """JOKE 'Slower.': deadpan close-up; a snail wearing an N sticker crawls across the dash."""
    snail = cat([sphere(0.07, 8, 5, (200, 120, 60)).mv(0, 0.07, 0), box(-0.1, 0, -0.03, 0.1, 0.04, 0.03, (150, 200, 120)),
                 box(0.08, 0.04, -0.012, 0.1, 0.1, 0.012, (150, 200, 120)), box(-0.02, 0.06, 0.068, 0.04, 0.1, 0.071, (255, 255, 255), texs={"f": C.T_N})])
    snail = snail.rot("y", 90).mv(0.85, 1.19, 0.25 - 0.4 * u)
    sc = cockpit(T_GEAR[8], t, "deadpan", look="r")
    return dict(scene=sc + [snail] + track(t, 2, odd=False), cam=Cam((1.15, 1.6, 0.35), (-0.2, 1.4, -0.2), 54))

def sh_fastcar(u, t, dt):
    """'Hyundai built a fast car': hero shot, car at full speed through the corner, sparkles."""
    car = car_at(t, 0, 0, v=1, yaw=-15 + 10 * u)
    return dict(scene=track(t, 14) + [car], cam=Cam((5.0, 1.1, 5.6), (0, 0.8, 0), 48, roll=5))

def sh_chute(u, t, dt):
    """'then added a way to make it slower': a drag parachute pops out of the hatch and yanks the car back."""
    k = ease(min(1, u * 2))
    ch = cat([P([(0, 0, 0), (math.cos(a) * 1.2 * k, math.sin(a) * 1.2 * k, -2.0 * k), (math.cos(b) * 1.2 * k, math.sin(b) * 1.2 * k, -2.0 * k)],
                (230, 40, 50) if i % 2 else (250, 250, 250)) for i, (a, b) in enumerate((2 * math.pi * j / 10, 2 * math.pi * (j + 1) / 10) for j in range(10))] +
             [sphere(1.2 * k + 0.01, 10, 4, (250, 250, 250)).sc(1, 1, 0.4).mv(0, 0, -2.0 * k)]).rot("y", -90).mv(-2.4, 1.1, 0)
    car = car_at(t, 0, 0, v=1)
    return dict(scene=track(t, 8 * (1 - 0.7 * k)) + [car, ch], cam=Cam((-9.5, 2.6, 3.8), (-3.6, 1.2, 0), 52))

def sh_purpose(u, t, dt):
    """'On purpose.': Yub gives a smug thumbs-up next to the car with the parachute draped over it."""
    h = hero("smug", ra=(70, 10, 80), la=(0, 8, 10), head=(-10, 0, 6)).rot("y", -15).mv(0.8, 0, 2.0)
    car = car_at(t, -0.8, 0, yaw=-30)
    return dict(scene=track(t) + [car, h], cam=Cam((1.6, 1.7, 5.3), (0.4, 1.45, 1.4), 48))

def sh_question(u, t, dt):
    """'Fake gears: genius, or gimmick?': Yub between a GENIUS sign and a GIMMICK sign, the Ioniq behind."""
    up = t > ws(7, 3)
    h = hero("confused" if not up else "smug", look="l" if t < ws(7, 3) else "r", la=(25, 55, 80), ra=(25, 55, 80), head=(0, 0, 8 * math.sin(t * 4)))
    g1 = Y.sign_board(T_GENIUS, 0.9, 0.4, 1.1).mv(-0.85, 0, -0.3); g2 = Y.sign_board(T_GIMMICK, 0.9, 0.4, 1.1).mv(0.85, 0, -0.3)
    car = car_at(t, -0.5, -4.0, yaw=-25)
    return dict(scene=track(t) + [h, g1, g2, car], cam=Cam((0.0, 1.5, 5.6 - 0.3 * u), (0, 1.25, 0), 50))

SHOTS = [
    (0.0, sh_hook, "Yub leans on a blue Ioniq 5 N, smug (snowman on lounger in the infield)"),
    (ws(0, 5), sh_fakebox, "FAKE stamp slams onto a shiny 8-speed gearbox, Yub shocked"),
    (ws(1, 0), sh_fast, "Ioniq 5 N blasts down the straight"),
    (ws(1, 5), sh_whoosh, "JOKE: car zooms past and spins Yub round"),
    (ws(2, 0), sh_eshift, "cockpit: N e-SHIFT gear display climbs 1..8 with paddle flicks"),
    (ws(2, 7), sh_motors, "x-ray car, motors glow, torque bars dip per shift"),
    (ws(3, 0), sh_speakers, "tailpipes are loudspeakers blasting sound rings"),
    (ws(3, 4), sh_vroom, "Yub air-drums to the fake engine sound"),
    (ws(4, 0), sh_miss, "JOKE: MISSED SHIFT, the car lurches, Yub panics"),
    (ws(5, 0), sh_test, "drag strip, timing tower 0-60 MPH, lights counting down"),
    (ws(5, 7), sh_time, "car launches, board flips to e-SHIFT ON 3.5 s"),
    (ws(5, 13) - 0.05, sh_slower, "JOKE: deadpan Yub, a snail with an N sticker crawls across the dash"),
    (ws(6, 0), sh_fastcar, "hero shot: Ioniq 5 N at full speed"),
    (ws(6, 5), sh_chute, "a drag parachute pops out and yanks the car back"),
    (ws(6, 13) - 0.05, sh_purpose, "Yub smug thumbs-up"),
    (ws(7, 0), sh_question, "Yub between GENIUS and GIMMICK signs"),
]
SFX = [(ws(0, 5) + 0.4, "stamp", 0.8), (ws(1, 0), "vroom", 0.6), (ws(1, 5) + 0.3, "whoosh", 0.8), (ws(1, 5) + 0.5, "boing", 0.5),
       *[(ws(2, 0) + k * (ws(2, 7) - ws(2, 0)) / 8, "click", 0.7) for k in range(8)], (ws(3, 0), "vroom", 0.7), (ws(3, 4), "vroom", 0.5),
       (ws(4, 0) + 0.25, "grind", 0.8), (ws(4, 0) + 0.6, "sputter", 0.7), (ws(5, 7), "vroom", 0.7), (ws(5, 10), "ding", 0.5),
       (ws(5, 13), "crickets", 0.9), (ws(6, 5) + 0.1, "poof", 0.8), (ws(6, 13), "rimshot", 0.7), (ws(7, 2), "pop", 0.5), (ws(7, 4), "pop", 0.5)]

if __name__ == "__main__": E.main(V)
