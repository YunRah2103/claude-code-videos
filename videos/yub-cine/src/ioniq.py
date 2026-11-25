"""ioniq_fake_gears: cinematic low-poly short. Night race track, floodlights, glowing breakdown of N e-Shift.
Oddity (never mentioned): a giant inflatable rubber duck floating in the infield pond."""
import math, sys
import numpy as np
from geo import (P, cat, quad, box, cbox, bbox, cb, lathe, cyl, superellipsoid, sphere, capsule, tiles, panel, word_tex, font, rgb, Cam,
                 MATTE, PAINT, GLASS, CHROME, SATIN, RUBBER, GLOW, SCREEN, T_DISC)
from render3d import Env
import cars3d as C
import props3d as PR
import engine3d as E
from engine3d import ease, lerp, shake
from yub import yub

NAME = "ioniq"
V = E.Video(sys.modules[__name__]); ws = V.ws; DUR = V.dur
HOOK = "Hyundai made an electric car with a fake gearbox."
ACCENT = (226, 30, 44)
HOT = {"fake", "gearbox", "fast", "e-shift", "eight-speed", "dual-clutch", "torque", "split", "shift", "engine", "exhaust", "sounds",
       "miss", "shifts", "gears", "sixty", "three", "point", "five", "slower", "purpose", "genius", "gimmick"}
TOPS = [(ws(3, 0), ws(3, 8), "N e-Shift: a fake 8-speed"), (ws(3, 8), ws(4, 0), "Torque cut at every 'shift'"), (ws(4, 0), ws(5, 0), "N Active Sound+"),
        (ws(6, 0), ws(7, 0), "Car and Driver test")]
ONSCREEN = ["HYUNDAI / N logos", "N e-Shift: a fake 8-speed", "Torque cut at every 'shift'", "gear numbers 1-8", "N Active Sound+", "MISSED SHIFT",
            "Car and Driver test", "0-60 MPH", "e-SHIFT ON 3.5 s", "GENIUS", "GIMMICK"]
ODDITY = "a giant inflatable rubber duck floating in the infield pond, lit by a floodlight"
CRASH = [ws(1, 0), ws(7, 0)]
MUSIC_UNDER_DB = 3.5

NIGHT = dict(sky_top=(8, 12, 46), sky_hor=(96, 56, 140), ground=(30, 30, 50), sun_dir=(0.45, 0.35, -0.6), sun=(150, 170, 255), sun_i=0.9,
             amb_i=0.75, fog=(30, 120), fog_col=(60, 44, 100), exposure=1.25, stars=1.0, bloom=0.9, sun_disc=False, sat=1.18, shadow_size=16)
FLOODS = [PR.floodlight(-9, -9, 10, (0.5, -1, 0.6), beam_e=0.06), PR.floodlight(9, -9, 10, (-0.5, -1, 0.6), beam_e=0.06), PR.floodlight(0, 14, 10, (0, -1, -0.7), beam_e=0.06)]
def env(points=(), **kw):
    p = [f[3] for f in FLOODS] + list(points)
    d = dict(NIGHT); d.update(kw)
    return Env(points=p, **d)
ENV = env()

T_NLOGO = C.T_N
T_BANNER = word_tex("HYUNDAI  N", 512, 96, (255, 255, 255), (0, 40, 110), 62)
T_TIMER = [word_tex(s, 512, 200, c, (6, 8, 16), z) for s, c, z in (("0-60 MPH", (255, 255, 255), 56), ("e-SHIFT ON\n3.5 s", (255, 220, 60), 46))]
def _cluster(gear=None, missed=False, on=True):
    def dr(d, w, h):
        d.rectangle((0, 0, w, 36), fill=(26, 34, 60)); d.text((16, 18), "N e-SHIFT  " + ("ON" if on else "OFF"), font=font(24), fill=(255, 255, 255), anchor="lm")
        d.polygon([(w - 50, 6), (w - 20, 6), (w - 42, 30)], fill=(226, 30, 44))
        for i in range(14):
            c = (60, 200, 255) if i < 9 else (255, 200, 40) if i < 12 else (255, 60, 60)
            lit = i < (14 if missed else 4 + 2 * ((gear or 1) % 5))
            d.rectangle((20 + i * 34, 50, 46 + i * 34, 72), fill=c if lit else (34, 40, 58))
        if missed:
            d.text((w / 2, 150), "MISSED", font=font(84), fill=(255, 70, 70), anchor="mm"); d.text((w / 2, 220), "SHIFT!", font=font(36), fill=(255, 190, 190), anchor="mm")
        else:
            d.text((w / 2, 160), str(gear) if gear else "D", font=font(150), fill=(255, 255, 255), anchor="mm"); d.text((w - 60, 220), "/ 8", font=font(30), fill=(150, 160, 190), anchor="mm")
    return PR.screen_tex(dr)
T_GEAR = [None] + [_cluster(g) for g in range(1, 9)]; T_MISSED = _cluster(missed=True); T_OFF = _cluster(None, on=False)
T_GENIUS = None; T_GIMMICK = None

# ---------------------------------------------------------------- sets
def track(t, v=0.0, odd=True):
    off = lambda x, L=96: ((x - v * t + L / 2) % L) - L / 2
    s = [tiles(-50, -60, 50, 40, -0.01, 10.0, -1, (24, 50, 30)), tiles(-50, -5, 50, 5, 0.0, 5.0, -1, (44, 44, 52), m=SATIN)]
    for k, x in enumerate(np.arange(-48, 48, 1.6)):
        col = (220, 30, 40) if k % 2 else (240, 240, 244)
        s += [box(off(x), 0.0, -5.5, off(x) + 1.6, 0.06, -5.0, col, m=PAINT), box(off(x), 0.0, 5.0, off(x) + 1.6, 0.06, 5.5, col, m=PAINT)]
    s += [box(off(x), 0.004, -0.07, off(x) + 2.5, 0.01, 0.07, (240, 240, 244)) for x in np.arange(-48, 48, 6.0)]
    rng = np.random.default_rng(3)
    gs = [box(-36, 0, -20 - i * 1.3, 36, 0.9 + i * 0.9, -19 - i * 1.3, (60, 64, 90)) for i in range(5)]
    for i in range(5):
        for x in np.arange(-34, 34, 1.3):
            c = tuple(int(q) for q in rng.choice([(230, 60, 60), (60, 140, 255), (255, 210, 40), (80, 220, 120), (240, 240, 250), (220, 90, 220)]))
            gs.append(cbox(x + rng.uniform(-0.2, 0.2), 1.15 + i * 0.9, -19.6 - i * 1.3, 0.5, 0.6, 0.35, c))
    gs += [box(x - 4, 0.3, -18.0, x + 4, 1.8, -17.9, (255, 255, 255), texs={"f": T_BANNER}, e=1.2) for x in (-22, -6, 10, 26)]
    s.append(cat(gs).mv(off(0, 192) * 0 , 0, 0))
    for x in (-40, -30, 30, 40): s.append(cat([cyl(0.15, 0.12, 2.5, 8, (90, 60, 40)), superellipsoid(1.4, 2.2, 1.4, 1, 1, 10, 8, (30, 90, 50)).mv(0, 3.4, 0)]).mv(x, 0, -14))
    s += [f[0] for f in FLOODS]
    if odd:
        pond = superellipsoid(6, 0.02, 3.5, 1, 1, 24, 4, (20, 60, 120), GLASS).mv(off(14) if v else 14, 0.01, 12)
        s += [pond, PR.duck(1.6).rot("y", -140 + 10 * math.sin(t)).mv(off(14) if v else 14, 0.05 + 0.05 * math.sin(t * 2), 12)]
    return s

def tglow(): return [f[1] for f in FLOODS]
def tsprites(): return [f[2] for f in FLOODS]

def car(t, x=0.0, z=0.0, yaw=0.0, v=0.0, lights=1.0):
    return C.ioniq5n(spin=-t * (1500 if v else 0), lights=lights).rot("y", yaw).mv(x, 0, z)

def headbeams(x, z, yaw=0.0, e=0.22):
    out = []
    for s in (1, -1):
        a = math.radians(yaw); px = x + 2.4 * math.cos(a) - s * 0.68 * math.sin(a); pz = z - 2.4 * math.sin(a) - s * 0.68 * math.cos(a)
        out.append(PR.beam((px, 0.64, pz), (math.cos(a), -0.08, -math.sin(a)), 14, 2.2, (200, 225, 255), e))
    return out

def cockpit(screen, t, expr="smile", la=(55, 4, 40), ra=(55, 4, 40), head=(0, 0, 0), jolt=0.0, lean=0.0, **kw):
    hw = 0.95
    dash = [bbox(0.55, 0.75, -hw, 1.3, 1.16, hw, (30, 32, 40), b=0.06), box(0.6, 1.16, -0.92, 0.64, 1.44, 0.12, (255, 255, 255), texs={"l": screen}, e=1.6, m=SCREEN),
            bbox(0.63, 1.14, -0.95, 0.7, 1.46, 0.15, (16, 16, 20), b=0.02), bbox(-1.5, 0.2, -hw, 1.3, 0.42, hw, (36, 38, 48), b=0.03),
            bbox(-1.4, 0.4, -hw - 0.06, 1.3, 1.18, -hw, C.N_BLUE, b=0.03, m=SATIN), bbox(-0.3, 0.42, -0.12, 0.7, 0.78, 0.12, (26, 26, 32), b=0.04),
            cb(1.32, 1.4, 0, 0.04, 0.5, 1.9, (60, 70, 110), b=0.01, m=GLASS)]
    seat = [bbox(-0.9, 0.55, -0.7, -0.35, 0.75, -0.15, (30, 30, 36), b=0.05), bbox(-0.98, 0.75, -0.7, -0.8, 1.58, -0.15, (30, 30, 36), b=0.05),
            cb(-0.9, 1.3, -0.425, 0.03, 0.4, 0.4, (226, 30, 44), b=0.01, m=PAINT)]
    sw = cat([lathe([(0.17, -0.015), (0.19, 0.0), (0.17, 0.015)], 24, (24, 24, 28), RUBBER), cb(0, 0.0, 0, 0.3, 0.03, 0.05, (24, 24, 28), b=0.01),
              cb(0, 0.025, 0.12, 0.05, 0.03, 0.04, (60, 200, 90), b=0.008, e=1.5), cb(0, 0.025, -0.12, 0.05, 0.03, 0.04, (226, 30, 44), b=0.008, e=1.5),
              cb(0.02, -0.05, 0.2, 0.08, 0.03, 0.1, (190, 194, 204), b=0.01, m=CHROME), cb(0.02, -0.05, -0.2, 0.08, 0.03, 0.1, (190, 194, 204), b=0.01, m=CHROME)]).rot("z", 70).mv(0.22, 1.16, -0.425)
    h = C_hero(yub(expr, sit=True, la=la, ra=ra, head=head, lean=lean - 14 * jolt, **kw))
    return [*dash, *seat, sw, h]

def C_hero(h, x=-0.62, y=0.75, z=-0.425): return h.rot("y", 90).mv(x, y - 0.5, z)
CAB_LIGHT = [((0.4, 1.4, -0.3), (120, 180, 255), 0.9, 0.9), ((-0.2, 1.9, 0.4), (255, 230, 210), 0.6, 2.0)]
def SCREEN_CAM(): return Cam((-1.05, 1.78, 0.55), (0.62, 1.3, -0.4), 42, aperture=0.18, focus=1.85)
def FACE_CAM(): return Cam((1.12, 1.66, 0.3), (-0.62, 1.58, -0.42), 46, aperture=0.12)

# ---------------------------------------------------------------- shots
def sh_hook(u, t, dt):
    """Night pit lane: the Performance Blue Ioniq 5 N under floodlights; Yub (LTN cap) leans on it, smug."""
    e = ease(u)
    h = yub("smug", la=(10, 20, 100), ra=(10, 20, 100), head=(12, 0, 4), lean=-6).rot("y", -25).mv(0.05, 0, 1.45)
    return dict(scene=track(t) + [car(t, 0, 0, -25), h], cam=Cam(lerp((4.8, 0.9, 6.0), (4.0, 1.15, 5.0), e), (0.3, 1.15, 0.6), 46, aperture=0.08),
                glow=tglow() + headbeams(0, 0, -25), sprites=tsprites(), center=(0, 0, 0))

def _gearbox(t, stamp):
    gears = [PR.gear(0.32, 18).rot("y", t * 120).rot("x", 90).mv(-0.35, 1.25, 0), PR.gear(0.22, 12, col=(214, 170, 70)).rot("y", -t * 175 + 7).rot("x", 90).mv(0.17, 1.25, 0),
             PR.gear(0.26, 14).rot("y", t * 150).rot("x", 90).mv(-0.3, 0.72, 0.05), PR.gear(0.18, 10, col=(214, 170, 70)).rot("y", -t * 210).rot("x", 90).mv(0.15, 0.78, 0.05),
             capsule((-0.35, 1.25, -0.2), (-0.35, 1.25, 0.25), 0.04, 10, (120, 124, 134), CHROME), capsule((0.17, 1.25, -0.2), (0.17, 1.25, 0.25), 0.03, 10, (120, 124, 134), CHROME)]
    case = cat([bbox(-0.8, 0.35, -0.35, 0.65, 0.42, 0.3, (60, 64, 76), b=0.02)])
    s = [cat(gears), case]
    if stamp > 0:
        s.append(PR.neon_sign("FAKE", 1.1, 0.42, (255, 50, 60), 2.6).rot("z", 10).sc(0.6 + 0.4 * stamp).mv(-0.05, 1.0, 0.45))
    return s

def sh_fakebox(u, t, dt):
    """Macro: an eight-speed gearbox's gears spinning, chrome glinting; a neon FAKE stamp slams on; Yub pops in, shocked."""
    k = ease(min(1, max(0, (u - 0.3) / 0.12)))
    h = yub("shock", la=(30, 30, 90), ra=(30, 30, 90)).rot("y", -35).mv(1.25, 0, 0.6)
    sx, sy, _ = shake(t, 0.025 if 0.3 < u < 0.45 else 0)
    return dict(scene=_gearbox(t, k) + [h, tiles(-4, -4, 4, 4, 0, 2, -1, (30, 32, 44), m=SATIN)],
                cam=Cam((0.2 + sx, 1.3 + sy, 3.6 - 0.3 * u), (-0.05, 1.0, 0), 44, aperture=0.2),
                env=env(points=[((0, 2.2, 1.2), (255, 230, 200), 2.2, 2.5), ((-1.5, 1.2, 0.5), (90, 140, 255), 1.6, 2.0)], fog=None), sprites=[], center=(0, 0.8, 0))

def sh_fast(u, t, dt):
    """'a seriously fast EV': low tracking shot at wheel height, the car blasting along the straight, pixel lights blazing, speed streaks."""
    x = -2 + 3 * u
    c = car(t, x, -1.5, 0, v=1)
    return dict(scene=track(t, 34) + [c], cam=Cam((x + 4.2, 0.55, 2.2), (x, 0.65, -1.5), 50, roll=-5, aperture=0.1),
                glow=tglow() + headbeams(x, -1.5) + [PR.speed_lines(t).mv(x, 0, -1.5)], sprites=tsprites(), center=(x, 0, -1.5))

def sh_gforce(u, t, dt):
    """Yub pinned to the seat, cheeks flapping, cap brim lifting: pure joy."""
    f = math.sin(t * 30) * 0.5
    sc = cockpit(T_GEAR[3], t, "grin", lean=-10, head=(f * 6, -8, 0), blush=True)
    return dict(scene=sc + track(t, 30, odd=False), cam=FACE_CAM(), env=env(points=CAB_LIGHT), glow=tglow(), sprites=tsprites(), center=(0, 1, 0))

def sh_button(u, t, dt):
    """'N e-Shift': macro of the wheel; Yub's thumb presses the glowing N button; the cluster lights up N e-SHIFT ON."""
    on = u > 0.45
    sc = cockpit(T_GEAR[1] if on else T_OFF, t, "smile", ra=(62, 6, 52))
    return dict(scene=sc + track(t, 4, odd=False), cam=Cam((-0.55, 1.62, 0.25), (0.42, 1.3, -0.3), 38, aperture=0.3, focus=1.2),
                env=env(points=CAB_LIGHT + ([((0.5, 1.3, -0.4), (60, 220, 120), 1.4, 0.5)] if on else [])), glow=[], sprites=[], center=(0, 1, 0))

def chassis(t, gear_n, cut=0.0):
    """Cutaway Ioniq 5 N skateboard: battery pack (glowing cells), front + rear motors, half-shafts, wheels; energy flows."""
    batt = [bbox(-1.35, 0.25, -0.75, 1.15, 0.42, 0.75, (30, 36, 60), b=0.04, m=SATIN)]
    batt += [cbox(-1.2 + 0.24 * i, 0.43, -0.6 + 0.3 * j, 0.2, 0.02, 0.24, (60, 160, 255), e=1.2 * (1 - cut)) for i in range(10) for j in range(5)]
    mot = []
    for x in (1.5, -1.5):
        mot += [cyl(0.2, 0.2, 0.46, 24, (200, 120, 60), CHROME).rot("x", 90).mv(x, 0.38, 0.23),
                cyl(0.21, 0.21, 0.04, 24, (255, 170, 60), MATTE, e=1.8 * (1 - cut)).rot("x", 90).mv(x, 0.38, 0.25),
                capsule((x, 0.38, -0.82), (x, 0.38, 0.82), 0.035, 10, (170, 174, 184), CHROME)]
    wheels = C._wheels((1.5, -1.5), 0.86, 0.36, 0.27, C.T_RIM_N, -t * 900, C.N_RED)
    fl = [PR.flow([(0.2, 0.45, 0), (1.3, 0.45, 0), (1.5, 0.4, 0.0)], t, e=2.4 * (1 - cut)), PR.flow([(-0.2, 0.45, 0), (-1.3, 0.45, 0), (-1.5, 0.4, 0)], t, e=2.4 * (1 - cut))]
    fl += [PR.flow([(x, 0.38, 0), (x, 0.38, s * 0.8)], t * 1.5, (255, 190, 70), 0.025, e=2.2 * (1 - cut)) for x in (1.5, -1.5) for s in (1, -1)]
    num = PR.neon_sign(str(gear_n), 0.5, 0.5, (255, 255, 255), 2.4, frame=False).mv(0, 1.55, 0) if gear_n else None
    return [*batt, *mot, *wheels, *fl] + ([num] if num is not None else [])

def sh_cutaway(u, t, dt):
    """'fakes an eight-speed dual-clutch gearbox': X-ray of the drivetrain, the body ghosted away; the floating gear number climbs 1..8."""
    g = 1 + min(7, int(u * 8)); ph = (u * 8) % 1
    cut = 1.0 if ph < 0.12 else 0.0
    e_ = ease(u)
    return dict(scene=chassis(t, g, cut) + [tiles(-6, -6, 6, 6, 0, 2, -1, (14, 16, 30), m=SATIN)],
                cam=Cam(lerp((4.6, 2.9, 4.2), (3.4, 2.2, 3.6), e_), (0, 0.6, 0), 42, aperture=0.08),
                env=env(points=[((0, 2.5, 0), (120, 170, 255), 1.4, 3.5)], fog=None, stars=0.6), glow=[], sprites=[], center=(0, 0.3, 0))

def sh_motor(u, t, dt):
    """'controlling the motors' torque': macro on the rear motor; copper windings glow, torque arrows spin round the shaft."""
    ph = (u * 3) % 1; cut = ph < 0.15
    sc = chassis(t, None, 1.0 if cut else 0.0)
    arrows = [capsule((-1.5 + 0.05, 0.38 + 0.36 * math.cos(a), 0.36 * math.sin(a)), (-1.5 + 0.05, 0.38 + 0.36 * math.cos(a + 0.5), 0.36 * math.sin(a + 0.5)), 0.022, 6, (255, 200, 60)).glow(0 if cut else 2.6)
              for a in np.linspace(0, 2 * math.pi, 6, endpoint=False) + t * 5]
    return dict(scene=sc + arrows + [tiles(-6, -6, 6, 6, 0, 2, -1, (14, 16, 30), m=SATIN)], cam=Cam((-0.4, 0.9, 1.3), (-1.5, 0.4, 0.2), 40, aperture=0.35, focus=1.5),
                env=env(points=[((-1.2, 1.2, 0.8), (255, 190, 120), 1.6, 1.6)], fog=None, stars=0.6), glow=[], sprites=[], center=(-1.5, 0.3, 0))

SHIFT_X = [0.0, 0.12, 0.25, 0.37, 0.5, 0.62, 0.75, 0.87, 1.0]
def _torque(n=160):
    v = []
    for i in range(n):
        x = i / (n - 1); seg = min(7, int(x * 8)); f = x * 8 - seg
        y = 0.85 - 0.06 * seg + (0.08 * math.sin(f * math.pi))
        if f < 0.08: y *= 0.25 + 9 * f                   # the cut at each 'shift'
        v.append(max(0.05, y))
    return v
TORQUE = _torque()
def sh_graph(u, t, dt):
    """'cutting power for a split second at each shift': a glowing torque trace draws itself; it dives at every shift, sparks fly."""
    rev = 0.2 + 0.8 * ease(u)
    g, head = PR.line_graph(TORQUE, 1.8, 1.1, rev, r=0.018)
    gp = PR.grid_panel(1.8, 1.25)
    ticks = [cb(1.8 * x, -0.05, 0, 0.015, 0.08, 0.015, (255, 255, 255), b=0.004, e=1.0) for x in SHIFT_X[1:-1]]
    dot = sphere(0.05, 12, 8, (255, 255, 255)).glow(4).mv(*head)
    sc = [g, gp, dot, *ticks]
    return dict(scene=sc, cam=Cam((0.9 + 0.25 * (head[0] / 1.8 - 0.5), 0.62, 3.3), (0.9, 0.6, 0), 46, aperture=0.04),
                env=env(fog=None, stars=0.4, points=[((head[0], 1.0, 0.8), (90, 200, 255), 1.2, 1.2)]), glow=[], sprites=[(head, (120, 220, 255), 0.06, 2.0)], center=(1.6, 0.8, 0))

def _v8(e=1.0):
    col = (255, 150, 50)
    blk = [cb(0, 0.3, 0, 0.9, 0.35, 0.5, col, b=0.04)] + [cb(0, 0.6, s * 0.22, 0.9, 0.3, 0.18, col, b=0.04).rot("x", s * 30, (0, 0.45, s * 0.1)) for s in (1, -1)]
    blk += [cyl(0.07, 0.07, 0.08, 12, col).mv(-0.3 + 0.2 * i, 0.78, s * 0.33) for i in range(4) for s in (1, -1)]
    blk += [cb(0, 0.8, 0, 0.7, 0.12, 0.18, col, b=0.03)]
    return cat(blk).mat(GLOW).glow(0.55 * e)

def sh_sound(u, t, dt):
    """'plays fake engine and exhaust sounds': rear 3/4 of the car; hidden speakers pump glowing sound rings; a holographic V8 flickers above."""
    c = car(t, 0, 0, 160)
    holo = _v8(0.6 + 0.4 * math.sin(t * 25)).sc(1.4).mv(0, 2.1 + 0.05 * math.sin(t * 3), 0)
    rngs = [PR.rings(t, 4, 0.15, 0.25, 1.4, (255, 190, 60), 1.8).rot("y", -110).mv(-2.1 * math.cos(math.radians(160)), 0.6, 2.1 * math.sin(math.radians(160)) + s * 0.6) for s in (1, -1)]
    return dict(scene=track(t) + [c], cam=Cam((-5.6, 1.6, -3.0), (0.2, 1.3, 0.2), 46, aperture=0.08),
                glow=tglow() + [holo] + rngs, sprites=tsprites(), center=(0, 0, 0))

def sh_miss(u, t, dt):
    """JOKE 'you can even miss shifts': Yub yanks the paddle - the cluster flashes MISSED SHIFT, the car lurches, his head snaps forward."""
    missed = u > 0.25
    jolt = 0 if u < 0.25 else max(0, math.sin((u - 0.25) * 16) * math.exp(-(u - 0.25) * 4))
    sc = cockpit(T_MISSED if missed else T_GEAR[3], t, "panic" if missed else "smile", sweat=missed, jolt=jolt,
                 ra=(85, 35, 75) if missed else (55, 4, 40), la=(85, 35, 75) if missed else (55, 4, 40))
    c = SCREEN_CAM() if u < 0.55 else FACE_CAM(); sx, sy, _ = shake(t, 0.025 * jolt); c.eye = c.eye + np.float32([sx, sy, 0])
    return dict(scene=sc + track(t, 6 * (1 - u), odd=False), cam=c, env=env(points=CAB_LIGHT + ([((0.6, 1.3, -0.4), (255, 60, 60), 1.6, 0.8)] if missed else [])),
                glow=tglow(), sprites=tsprites(), center=(0, 1, 0))

def sh_nogears(u, t, dt):
    """JOKE 'In a car with no gears.': Yub holds up a single tiny cog between finger and thumb and stares at it, deadpan."""
    cog = PR.gear(0.07, 10, col=(214, 170, 70)).rot("x", 90).rot("z", t * 40)
    sc = cockpit(T_GEAR[3], t, "deadpan", look="r", ra=(70, 25, 70), held=cog, head=(-25, 10, 0))
    return dict(scene=sc + track(t, 2, odd=False), cam=FACE_CAM(), env=env(points=CAB_LIGHT), glow=tglow(), sprites=tsprites(), center=(0, 1, 0))

def _tree(u):
    lit = int(u * 4.5)
    out = [cb(0, 0.9, 0, 0.14, 1.8, 0.14, (40, 40, 46), b=0.02)]
    sp = []
    for i in range(3):
        on = i < lit
        out.append(sphere(0.08, 12, 8, (255, 190, 30) if on else (50, 46, 30)).glow(3 if on else 0).mv(0, 1.1 + 0.25 * i, 0.08))
    out.append(sphere(0.08, 12, 8, (60, 240, 90) if u > 0.85 else (30, 50, 34)).glow(3 if u > 0.85 else 0).mv(0, 1.85, 0.08))
    return cat(out)

def _board(tid):
    return cat([cyl(0.12, 0.12, 3.5, 10, (60, 62, 70)).mv(-1.4, 0, 0), cyl(0.12, 0.12, 3.5, 10, (60, 62, 70)).mv(1.4, 0, 0),
                bbox(-1.8, 3.4, -0.12, 1.8, 4.9, 0.08, (14, 16, 24), b=0.04), box(-1.7, 3.5, 0.081, 1.7, 4.8, 0.09, (255, 255, 255), texs={"f": tid}, e=2.0, m=SCREEN)])

def sh_test(u, t, dt):
    """'Car and Driver tested it': drag strip, timing board reads 0-60 MPH, the start tree counts down, the car staged with lights on."""
    c = car(t, -0.5, -1.5, 0)
    return dict(scene=track(t) + [c, _board(T_TIMER[0]).rot("y", 35).mv(-2.4, 0, -7.5), _tree(u).mv(2.6, 0, 0.2)], cam=Cam((6.4, 1.6, 5.0), (0.2, 1.6, -2.5), 48, aperture=0.06),
                glow=tglow() + headbeams(-0.5, -1.5), sprites=tsprites(), center=(0, 0, -1.5))

def sh_launch(u, t, dt):
    """'zero to sixty took 3.5 seconds': the launch - tyres bite, the car rockets away; the board flips to e-SHIFT ON 3.5 s."""
    x = -0.5 + 18 * ease(u) ** 2
    c = car(t, x, -1.5, 0, v=1)
    b = _board(T_TIMER[1] if u > 0.42 else T_TIMER[0]).rot("y", 30).mv(0.1, 0, -7.5)
    return dict(scene=track(t, 0) + [c, b], cam=Cam((6.0, 1.5, 6.0), (1.0, 2.2, -2.5), 50, aperture=0.05),
                glow=tglow() + headbeams(x, -1.5) + [PR.speed_lines(t, 8).mv(x, 0, -1.5)], sprites=tsprites(), center=(x, 0, -1.5))

def sh_snail(u, t, dt):
    """JOKE 'Slower.': macro, shallow focus - a snail wearing an N sticker crawls across the bonnet; Yub deadpan behind it, out of focus."""
    sn = PR.snail(C.T_N).sc(1.4).rot("y", 90).mv(1.9, 0.93, 0.25 - 0.3 * u)
    c = car(t, 0, 0, 0)
    h = yub("deadpan", la=(0, 8, 10), ra=(0, 8, 10)).rot("y", -90).mv(3.3, 0, 0.1)
    return dict(scene=track(t, odd=False) + [c, sn, h], cam=Cam((2.4, 1.12, 0.9), (1.9, 1.0, 0.15), 34, aperture=0.6, focus=0.85),
                glow=tglow(), sprites=tsprites(), center=(2, 0.8, 0))

def sh_corner(u, t, dt):
    """'Hyundai built a fast car': hero shot sliding through a corner, tail lights streaking."""
    yaw = -20 + 25 * u
    c = car(t, 0, 0, yaw, v=1)
    return dict(scene=track(t, 20) + [c], cam=Cam((4.2, 1.0, 4.6), (0, 0.8, 0), 44, roll=6, aperture=0.08),
                glow=tglow() + headbeams(0, 0, yaw), sprites=tsprites(), center=(0, 0, 0))

def sh_chute(u, t, dt):
    """'then added a way to make it slower': a red-and-white drag parachute blooms out of the hatch and yanks the car back."""
    k = ease(min(1, u * 1.8))
    c = car(t, 0, 0, 0, v=1)
    ch = PR.chute(k * 0.72).mv(-2.4, 1.0, 0)
    sx, sy, _ = shake(t, 0.02 * k)
    return dict(scene=track(t, 14 * (1 - 0.8 * k)) + [c, ch], cam=Cam((-11 + sx, 3.0 + sy, 8.5), (-2.2, 1.0, 0), 44, aperture=0.04),
                glow=tglow(), sprites=tsprites(), center=(-2, 0, 0))

def sh_purpose(u, t, dt):
    """'On purpose.': Yub, smug, slow thumbs-up under a floodlight; the parachute draped over the car behind him."""
    h = yub("smug", ra=(75, 10, 85), head=(-12, 0, 6)).rot("y", -15).mv(0.8, 0, 2.0)
    ch = PR.chute(0.6).rot("z", -70, (0, 0, 0)).mv(-2.2, 1.6, 0)
    return dict(scene=track(t) + [car(t, -0.8, 0, -30), h, ch], cam=Cam((1.5, 1.6, 4.9), (0.5, 1.45, 1.6), 42, aperture=0.2),
                glow=tglow() + [PR.beam((0.8, 6, 2.0), (0, -1, 0), 6, 1.6, (255, 236, 200), 0.18)], sprites=tsprites(), center=(0, 0, 1))

def sh_question(u, t, dt):
    """'Fake gears: genius, or gimmick?': Yub between a green GENIUS neon and a red GIMMICK neon, looking from one to the other."""
    global T_GENIUS
    look = "l" if t < ws(8, 3) else "r"
    h = yub("confused" if t < ws(8, 3) else "smug", look=look, la=(25, 55, 80), ra=(25, 55, 80), head=(0, 0, 8 * math.sin(t * 4)))
    g1 = PR.neon_sign("GENIUS", 1.0, 0.36, (60, 230, 110), 2.8).mv(-0.95, 1.55, 0.1)
    g2 = PR.neon_sign("GIMMICK", 1.0, 0.36, (255, 50, 60), 2.8).mv(0.95, 1.55, 0.1)
    return dict(scene=track(t) + [h, g1, g2, car(t, -0.5, -4.2, -25)], cam=Cam((0, 1.45, 5.8 - 0.3 * u), (0, 1.3, 0), 46, aperture=0.12),
                glow=tglow(), sprites=tsprites(), env=env(points=[((-0.95, 1.6, 0.6), (60, 230, 110), 1.2, 1.2), ((0.95, 1.6, 0.6), (255, 50, 60), 1.2, 1.2)]), center=(0, 0, 0))

SHOTS = [
    (0.0, sh_hook, "night pit lane, floodlights; Yub leans on the Ioniq 5 N, smug (rubber duck in the infield pond)"),
    (ws(0, 4), sh_fakebox, "macro: 8-speed gears spinning, neon FAKE stamp slams on, Yub shocked"),
    (ws(1, 0), sh_fast, "low tracking shot: the car blasting down the straight, speed streaks"),
    (ws(1, 6), sh_gforce, "Yub pinned in his seat, grinning"),
    (ws(2, 0), sh_button, "macro: thumb presses the N button; cluster lights N e-SHIFT ON"),
    (ws(3, 0), sh_cutaway, "x-ray drivetrain: battery, two motors, energy flowing; gear number climbs 1..8"),
    (ws(3, 7), sh_motor, "macro: rear motor glowing, torque arrows spin, power cuts out"),
    (ws(3, 11), sh_graph, "glowing torque trace dives at every shift"),
    (ws(4, 0), sh_sound, "rear 3/4: hidden speakers pump sound rings, holographic V8 above"),
    (ws(5, 0), sh_miss, "JOKE: MISSED SHIFT, car lurches, Yub's head snaps forward"),
    (ws(5, 8), sh_nogears, "JOKE: Yub holds up one tiny cog, deadpan"),
    (ws(6, 0), sh_test, "drag strip, timing board 0-60 MPH, start tree"),
    (ws(6, 9), sh_launch, "launch, board flips to e-SHIFT ON 3.5 s"),
    (ws(6, 17) - 0.05, sh_snail, "JOKE: snail with an N sticker crawls across the bonnet, macro"),
    (ws(7, 0), sh_corner, "hero shot through a corner"),
    (ws(7, 5), sh_chute, "drag parachute blooms and yanks the car back"),
    (ws(7, 13) - 0.05, sh_purpose, "Yub smug thumbs-up under a floodlight"),
    (ws(8, 0), sh_question, "Yub between GENIUS and GIMMICK neons"),
]
SFX = [(ws(0, 4) + 0.35 * (ws(1, 0) - ws(0, 4)), "stamp", 0.8), (ws(1, 0), "vroom", 0.7), (ws(1, 6), "whoosh", 0.5),
       (ws(2, 0) + 0.45 * (ws(3, 0) - ws(2, 0)), "click", 0.9), (ws(2, 0) + 0.47 * (ws(3, 0) - ws(2, 0)), "ding", 0.5),
       *[(ws(3, 0) + k * (ws(3, 7) - ws(3, 0)) / 8, "click", 0.6) for k in range(1, 8)], (ws(3, 11), "whoosh", 0.4),
       (ws(4, 0), "vroom", 0.8), (ws(4, 4), "vroom", 0.6), (ws(5, 0) + 0.25 * (ws(5, 8) - ws(5, 0)), "grind", 0.9),
       (ws(5, 0) + 0.32 * (ws(5, 8) - ws(5, 0)), "sputter", 0.7), (ws(5, 8), "crickets", 0.8), (ws(6, 9), "vroom", 0.9),
       (ws(6, 9) + 0.9, "ding", 0.5), (ws(6, 17), "boing", 0.4), (ws(7, 5) + 0.1, "poof", 0.9), (ws(7, 13), "rimshot", 0.8),
       (ws(8, 2), "pop", 0.5), (ws(8, 4), "pop", 0.5)]

if __name__ == "__main__": E.main(V)
