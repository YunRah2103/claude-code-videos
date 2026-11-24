"""ferrari-purrari: PS1-style low-poly short. 22 literal shots, one narrator, small word-by-word captions.
python render.py still T out.png | sheet out.png | meta out.json | thumb out.png | video voice.wav out.mp4 [t0 t1]"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from lowpoly import W, H, P, cat, box, cbox, cyl, sphere, quad, tiles, wall, Cam, sky, render, finish, font
import models as M
import fmodels as F

HERE = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(HERE, "words.json")))
FPS, OW, OH = 30, 1080, 1920
DUR = 28.0

def ws(line, i=0): return [o for o in WORDS if o["line"] == line][i]["s"]
def ease(u): return u * u * (3 - 2 * u)
def lerp(a, b, u): return tuple(x + (y - x) * u for x, y in zip(a, b))
def shake(t, amt, f=23.0): return (amt * math.sin(t * f * 6.1), amt * math.sin(t * f * 4.3 + 1), amt * math.sin(t * f * 5.2 + 2))

# ---------------------------------------------------------------- sets
SHOW_BG = sky((10, 10, 14), (26, 24, 30))
SHOW_FOG = (11, 30, (16, 14, 18))
SHOW_POINTS = [((x, 4.6, z), (255, 236, 214), 8.0) for x in (-3.5, 3.5) for z in (-1.5, 2.5)] + [((0, 3.5, 3.5), (255, 120, 90), 6.0)]

def oddcat(t, pos=(-5.6, 3.0, -5.8), s=0.6):
    """Comment bait: a tiny rainbow cat loafs on top of the showroom's corner pillar, trail and all. Never mentioned."""
    return F.flying_cat(t, 1.1).sc(s).rot("y", 200 + 8 * math.sin(t * 2)).mv(*pos)

def showroom(t, turntable=True, odd=True):
    s = [tiles(-12, -8, 12, 9, 0, 2.0, M.T_TILE_DARK),
         wall(-12, 0, 12, 6, -6.5, 3.0, -1, (34, 30, 32)),
         box(-2.2, 3.4, -6.48, 2.2, 4.3, -6.4, (255, 255, 255), texs={"f": F.T_FERRARI_SIGN}, e=1.0),
         box(-0.55, 4.45, -6.48, 0.55, 5.75, -6.4, (255, 255, 255), texs={"f": F.T_PLAQUE}),
         box(5.3, 0, -6.1, 5.9, 3.0, -5.5, (60, 56, 60)), box(-5.9, 0, -6.1, -5.3, 3.0, -5.5, (60, 56, 60)),
         box(-12, 0, -6.45, 12, 0.25, -6.3, (196, 14, 18))]
    if turntable: s.append(cyl(3.0, 3.0, 0.1, 20, (54, 54, 60)).rot("y", t * 20))
    s += [cbox(x, 5.6, z, 0.6, 0.1, 0.6, (255, 250, 230), e=1.0) for x in (-3.5, 3.5) for z in (-1.5, 2.5)]
    if odd: s.append(oddcat(t))
    return s

def office(t, odd=True):
    s = [tiles(-6, -4, 6, 6, 0, 2.0, M.T_TILE_DARK), wall(-6, 0, 6, 4, -2.5, 2.0, M.T_PANEL),
         box(-0.5, 1.6, -2.49, 0.5, 2.85, -2.45, (255, 255, 255), texs={"f": F.T_SHIELD}),
         box(1.4, 1.3, -2.49, 3.6, 2.9, -2.45, (255, 255, 255), texs={"f": M.T_WIN_COOL}, e=1.0)]
    if odd: s.append(oddcat(t, (-2.6, 2.95, -2.2), 0.3))
    return s

OFFICE_BG = sky((30, 30, 36), (54, 54, 60))
OFFICE_POINTS = [((0, 3.4, 1.0), (255, 236, 200), 6.0), ((2.5, 2.0, -1.5), (180, 200, 255), 4.0)]

def car_on_table(t, wrap=0.0, rot=None, **kw):
    a = rot if rot is not None else t * 20
    return F.f458(wrap, **kw).rot("y", a).mv(0, 0.1, 0)

# ---------------------------------------------------------------- shots: fn(u, t, dt) -> dict
def sh_hook(u, t, dt):
    """Dark showroom; spotlight snaps on; low hero dolly across the 458's nose."""
    on = min(1, dt / 0.25)
    e = ease(u)
    pts = [((2.8, 3.2, 1.5), (255, 236, 214), 7.5 * on), ((-1, 4.5, 2), (255, 220, 200), 7.0 * on), ((3.5, 0.6, 2.5), (255, 90, 60), 4.0)]
    return dict(scene=showroom(t) + [car_on_table(t, rot=-25)], cam=Cam(lerp((5.6, 0.45, 4.6), (4.4, 0.5, 3.0), e), (0.6, 0.6, 0.0), 48,
                roll=-5 + 4 * e), points=pts, amb=0.18 + 0.12 * on)

def sh_refuse(u, t, dt):
    """Salesman at his desk shakes his head and pulls the key away; the 458 waits behind him."""
    shake_h = 22 * math.sin(t * 16) * (1 - u * 0.3)
    sm = F.salesman(head=(shake_h, 0), ra=(70 - 20 * ease(u), 25, 30), la=(20, 6, 10)).mv(0, 0, -0.9)
    key = F.key_fob().mv(0.42 - 0.2 * ease(u), 1.1, -0.45)
    s = showroom(t, turntable=False) + [F.desk().mv(0, 0, 0), sm, key, F.f458().rot("y", 30).mv(-1.2, 0, -4.0)]
    return dict(scene=s, cam=Cam((0.6 + 0.2 * u, 1.35, 2.6 - 0.4 * u), (0.1, 1.25, -0.6), 52), points=SHOW_POINTS, amb=0.32)

def sh_cash(u, t, dt):
    bc = F.briefcase(ease(min(1, u * 2.2))).mv(0, 0.78, 0.0)
    s = showroom(t, turntable=False) + [F.desk(), bc]
    return dict(scene=s, cam=Cam((0.0, 1.55 - 0.2 * u, 1.1 - 0.35 * ease(u)), (0, 0.85, -0.05), 50),
                points=SHOW_POINTS + [((0.0, 1.8, 0.6), (180, 255, 180), 2.0)], amb=0.34)

def sh_pushback(u, t, dt):
    """A suited hand shoves the open case of cash back across the desk; it skids at the camera."""
    k = ease(min(1, u * 1.6))
    bc = F.briefcase(1.0).mv(0, 0.78, -0.2 + 0.55 * k)
    arm = cat([box(-0.06, -0.06, -0.6, 0.06, 0.06, 0.0, (22, 22, 26)), box(-0.05, -0.05, 0.0, 0.05, 0.05, 0.1, (220, 180, 150))]).mv(0.05, 0.92, -0.42 + 0.55 * k)
    sm = F.salesman(ra=(60, 0, 0)).mv(0.3, 0, -1.2)
    sx, sy, _ = shake(t, 0.02 if 0.55 < u < 0.75 else 0, 11)
    s = showroom(t, turntable=False) + [F.desk(), bc, arm, sm]
    return dict(scene=s, cam=Cam((0.5 + sx, 1.25 + sy, 1.55), (0, 0.9, -0.1), 56), points=SHOW_POINTS, amb=0.34)

def sh_pick(u, t, dt):
    """A queue of buyers; a spotlight sweeps along them and the salesman points at one."""
    s = showroom(t, turntable=False)
    pick = 2
    for i, fc in enumerate(F.F_BUYERS):
        x = -2.1 + i * 1.4
        s.append(M.person(skin=(200, 160, 120), top=[(150, 40, 40), (40, 90, 60), (60, 60, 140), (200, 150, 40)][i], face=fc,
                          ra=(150, 10, 0) if (i == pick and u > 0.6) else (10, 5, 10)).mv(x, 0, 0.8))
    sx = -2.1 + 1.4 * min(pick, u * 4.2) if u < 0.6 else -2.1 + 1.4 * pick
    s.append(F.salesman(ra=(85, -20, 0), head=(-30, 0)).rot("y", 120).mv(3.4, 0, 2.4))
    s.append(cyl(0.6, 0.6, 0.01, 12, (255, 240, 190), e=1.0).mv(sx, 0.01, 0.8))
    pts = [((sx, 4.0, 1.6), (255, 240, 200), 5.0), ((0, 4.0, 4.0), (120, 130, 160), 8.0)]
    return dict(scene=s, cam=Cam((0.0, 2.2, 7.6 - 0.6 * u), (0.0, 1.2, 0.8), 56), points=pts, amb=0.2)

def sh_rare(u, t, dt):
    """Behind a velvet rope, the silk cover lifts off a yellow special 458."""
    lift = ease(min(1, u * 1.5))
    car = F.f458(body=(250, 196, 20)).rot("y", -20).mv(0, 0.1, -1.5)
    s = showroom(t) + [car, F.cover_sheet(lift).rot("y", -20).mv(0, 0.1, -1.5), F.velvet_rope(x0=-2.4, x1=2.4).mv(0, 0, 1.6)]
    return dict(scene=s, cam=Cam((1.0 - 0.6 * u, 1.3, 5.6 - 0.6 * u), (0, 0.8, -1.4), 50), points=SHOW_POINTS, amb=0.3)

def sh_contract(u, t, dt):
    k = min(6, int(u * 8))
    paper = box(-0.21, 0.78, -0.27, 0.21, 0.785, 0.27, (255, 255, 255), texs={"t": F.T_CONTRACT[k]}).rot("y", 8)
    sx = -0.15 + 0.13 * min(1, u * 1.33)
    pen = cat([cyl(0.012, 0.012, 0.24, 6, (20, 20, 24)), cyl(0.012, 0.0, 0.03, 6, (220, 200, 120)).rot("x", 180)]).rot("x", 35).rot("z", -25)
    pen = pen.mv(sx + 0.01 * math.sin(t * 40), 0.81, 0.2 + 0.006 * math.sin(t * 33))
    return dict(scene=office(t) + [F.desk(), paper, pen], cam=Cam((0.05, 1.5 - 0.1 * u, 0.62 - 0.12 * u), (0, 0.78, 0.0), 52),
                bg=OFFICE_BG, points=OFFICE_POINTS, amb=0.42)

def sh_nosale(u, t, dt):
    """FOR SALE sign on the windscreen; a big red NO slams onto it."""
    hit = 0.3
    drop = 1.0 - min(1, u / hit)
    car = F.f458(sale=True, no=drop if u > 0.05 else None)
    sx, sy, _ = shake(t, 0.04 if hit < u < hit + 0.15 else 0, 13)
    return dict(scene=showroom(t, turntable=False) + [car], cam=Cam((2.6 + sx, 1.5 + sy, 0.5), (0.2, 0.98, 0.0), 40),
                points=SHOW_POINTS + [((2.0, 2.0, 0.5), (255, 240, 220), 3.0)], amb=0.36)

def sh_year(u, t, dt):
    k = int(u * 24)
    s = [wall(-3, 0, 3, 4, 0, 1.0, M.T_PANEL),
         box(-0.32, 1.1, 0.0, 0.32, 1.9, 0.03, (255, 255, 255), texs={"f": M.T_CAL[(k + 1) % 12]}),
         cbox(0, 1.93, 0.03, 0.06, 0.06, 0.03, (40, 40, 40)), tiles(-3, 0, 3, 3, 0, 1.0, M.T_TILE)]
    f = (u * 24) % 1
    page = box(-0.32, -0.8, 0, 0.32, 0, 0.004, (255, 255, 255), texs={"f": M.T_CAL[k % 12], "b": M.T_CAL[k % 12]})
    s.append(page.rot("x", -f * 120).rot("z", f * 60).mv(f * 0.6, 1.9 + f * 0.5, 0.04 + f * 1.0))
    s.append(F.f458().rot("y", 90).sc(0.12).mv(0.75, 1.62, 0.05))      # toy 458 on the shelf
    s.append(box(0.5, 1.6, 0.0, 1.0, 1.62, 0.25, (60, 50, 40)))
    return dict(scene=s, cam=Cam((0.2, 1.5, 2.0 - 0.35 * u), (0.05, 1.5, 0), 46), bg=OFFICE_BG, fog=None, points=OFFICE_POINTS, amb=0.45)

def sh_wrapping(u, t, dt):
    """The cat livery rolls on from the nose backwards; the roll travels along the side."""
    w = 0.05 + 0.6 * u
    car = F.f458(wrap=w)
    rx = 2.3 - 4.6 * w
    roll = cyl(0.07, 0.07, 1.0, 8, (230, 230, 236), captex=F.T_WRAP_ROLL).mv(0, 0, 0).mv(rx, 0.2, 1.02)
    gl = F.salesman(top=(40, 40, 44), legs=(40, 40, 44), shirt=None, ra=(70, 10, 30), la=(70, 10, 30), face=M.face_tex(skin=(200, 160, 130), hair=(60, 40, 30), mouth="flat")).rot("y", 180).mv(rx + 0.1, 0, 1.6)
    s = showroom(t, turntable=False) + [car, roll, gl]
    return dict(scene=s, cam=Cam((rx + 2.2, 2.4, 6.0), (rx - 0.6, 0.6, 0.0), 50), points=SHOW_POINTS, amb=0.34)

def sh_458(u, t, dt):
    car = F.f458(wrap=0.7 + 0.3 * ease(u)).rot("y", 30)
    a = math.radians(10 + 45 * ease(u))
    eye = (4.6 * math.cos(a), 0.5 + 0.4 * u, 4.6 * math.sin(a))
    return dict(scene=showroom(t, turntable=False) + [car], cam=Cam(eye, (0.8, 0.55, 0.3), 46), points=SHOW_POINTS, amb=0.32)

def sh_nyan(u, t, dt):
    """A grey cartoon cat paddles through space with a rainbow trail."""
    c = F.flying_cat(t, 3.5).rot("z", 8 * math.sin(t * 6)).mv(0, 0.15 * math.sin(t * 7), 0)
    return dict(scene=[c], cam=Cam((-0.6 + 0.6 * u, 0.4, 2.2 - 0.3 * u), (-0.3, 0.35, 0), 50), bg=F.STAR_BG, fog=None,
                points=[((0.5, 1.5, 1.5), (255, 255, 255), 4.0)], amb=0.55)

def road(t, speed=10.0):
    s = [tiles(-30, -6, 30, 6, 0, 3.0, -1, (36, 36, 40))]
    off = (t * speed) % 4.0
    s += [box(x - off, 0.005, -0.06, x - off + 2.0, 0.01, 0.06, (230, 230, 200)) for x in np.arange(-28, 30, 4.0)]
    s += [cat([cyl(0.06, 0.05, 4.5, 6, (40, 40, 44)), cbox(0.4, 4.5, 0, 0.9, 0.1, 0.2, (60, 60, 64)),
               cbox(0.75, 4.4, 0, 0.3, 0.05, 0.2, (255, 220, 160), e=1.0)]).mv(x - (t * speed) % 12, 0, -4.5) for x in np.arange(-24, 30, 12)]
    return s

def sh_purrari(u, t, dt):
    """The Purrari cruises a night road, rainbow streaming behind, plate reads PURRARI."""
    car = F.f458(wrap=1.0, spin=-t * 900, plate=True).rot("y", 0).mv(0, 0, 1.2)
    tr = F.trail(7.0, t * 12, 0.3, 0.6, 1.2).mv(-2.3, 0, 0)
    s = road(t) + [car, tr, oddcat(t, (6.0, 0.0, -3.5), 0.5)]
    a = math.radians(20 + 40 * ease(u))
    eye = (6.4 * math.cos(a), 0.8 + 0.5 * u, 1.2 + 6.4 * math.sin(a))
    return dict(scene=s, cam=Cam(eye, (-0.4, 0.6, 1.2), 48), bg=F.STAR_BG, fog=(14, 40, (20, 16, 50)),
                points=[((0, 5, 4), (200, 200, 255), 9.0), ((3.6, 1.0, 2.0), (255, 200, 240), 4.5), ((-2, 1.5, 3), (120, 220, 255), 4.0)], amb=0.5)

def sh_hq(u, t, dt):
    """Ferrari's office: the shield on the wall, the camera pushes in."""
    s = office(t) + [F.desk(), F.salesman(face=F.F_EXEC, hair=(150, 150, 150), la=(70, 40, 100), ra=(70, 40, 100)).mv(0, 0, -1.4)]
    return dict(scene=s, cam=Cam((0.0, 1.7, 3.6 - 1.2 * ease(u)), (0, 1.9, -2.4), 50), bg=OFFICE_BG, points=OFFICE_POINTS, amb=0.42)

def sh_notfunny(u, t, dt):
    """Stone-faced executive; a tiny rainbow-cat toy on the desk gets flicked off."""
    ex = F.salesman(face=F.F_EXEC, hair=(150, 150, 150), la=(70, 40, 100), ra=(70, 40, 100)).mv(0, 0, -1.0)
    k = max(0, (u - 0.45) / 0.55)
    toy = F.rcat(t * (1 - k)).sc(0.4).rot("z", -400 * k).mv(0.3 + 1.2 * k, 0.78 + 0.6 * math.sin(math.pi * min(1, k)) - 0.8 * max(0, k - 0.6), -0.1)
    s = office(t) + [F.desk(), ex, toy]
    return dict(scene=s, cam=Cam((0.4, 1.45, 0.9), (0.1, 1.45, -1.0), 50), bg=OFFICE_BG, points=OFFICE_POINTS, amb=0.42)

def sh_envelope(u, t, dt):
    """A sealed envelope flies across a hallway onto the doormat."""
    k = ease(min(1, u * 1.3))
    env = box(-0.2, 0, -0.13, 0.2, 0.01, 0.13, (255, 255, 255), texs={"t": F.T_ENVELOPE}).rot("y", 200 * (1 - k)).rot("x", 70 * (1 - k))
    env = env.sc(1.3).mv(0.0, 0.05 + 0.9 * (1 - k) ** 2, -1.3 + 1.4 * k)
    s = [tiles(-5, -3, 5, 4, 0, 1.0, M.T_WOOD), wall(-5, 0, 5, 3, -1.5, 1.0, M.T_PANEL),
         box(-0.6, 0.0, -0.3, 0.6, 0.02, 0.5, (90, 60, 40)), box(-0.6, 0, -1.48, 0.6, 2.2, -1.42, (120, 30, 30)),
         box(-0.2, 0.9, -1.42, 0.2, 0.96, -1.38, (200, 170, 60)), env]
    return dict(scene=s, cam=Cam((0.9, 1.1, 1.4), (0.0, 0.45, -0.5), 52), bg=OFFICE_BG, points=OFFICE_POINTS, amb=0.45)

def sh_letter(u, t, dt):
    """The envelope's letter unfolds on the mat: CEASE AND DESIST. The Purrari waits outside the door."""
    o = ease(min(1, u * 2.0))
    let = box(-0.21, 0, -0.28 * o, 0.21, 0.005, 0.28, (255, 255, 255), texs={"t": F.T_LETTER})
    s = [tiles(-5, -3, 5, 4, 0, 1.0, M.T_WOOD), box(-0.6, 0.0, -0.4, 0.6, 0.02, 0.5, (90, 60, 40)), let.mv(0, 0.03, 0)]
    car = F.f458(wrap=1.0).rot("y", 20).mv(0.2, 0, -4.5)
    return dict(scene=s + [car], cam=Cam((0.0, 1.05 - 0.2 * u, 0.62), (0, 0.0, -0.08), 50),
                bg=OFFICE_BG, points=OFFICE_POINTS + [((0, 1.5, 0.5), (255, 240, 220), 3.0)], amb=0.45)

def sh_blacklist(u, t, dt):
    """A clipboard titled BLACKLIST: not one name on it."""
    clip = cat([box(-0.24, 0, -0.32, 0.24, 0.02, 0.32, (110, 76, 44)),
                box(-0.2, 0.02, -0.28, 0.2, 0.025, 0.28, (255, 255, 255), texs={"t": F.T_BLACKLIST}),
                box(-0.1, 0.02, -0.33, 0.1, 0.05, -0.27, (190, 190, 196))]).rot("x", 60).mv(0, 1.2, 0)
    s = office(t) + [F.desk(), clip]
    return dict(scene=s, cam=Cam((0.1 * math.sin(u * 3), 1.4, 1.2 - 0.35 * ease(u)), (0, 1.2, 0), 46, roll=4 * math.sin(u * 4)),
                bg=OFFICE_BG, points=OFFICE_POINTS, amb=0.45)

def sh_vip(u, t, dt):
    """Special edition on its plinth: the rope opens for one buyer, the next is held back."""
    car = F.f458(body=(250, 196, 20)).rot("y", -20 + t * 15).mv(0, 0.1, -1.6)
    gate = min(1, u * 2)
    r = F.velvet_rope(x0=-2.0, x1=2.0).rot("y", 70 * gate, (2.0, 0, 0)).mv(0, 0, 1.2)
    b1 = M.person(skin=(200, 160, 120), top=(60, 60, 140), face=F.F_BUYERS[2], step=10 * math.sin(t * 8)).rot("y", 180).mv(0.6, 0, 2.0 - 1.4 * u)
    b2 = M.person(skin=(150, 100, 70), top=(150, 40, 40), face=F.F_BUYERS[1], la=(80, 0, 0), ra=(80, 0, 0)).rot("y", 180).mv(-1.0, 0, 2.6)
    guard = F.salesman(ra=(90, -40, 0), head=(-40, 0)).rot("y", 140).mv(-2.4, 0, 1.6)
    s = showroom(t) + [car, r, b1, b2, guard]
    return dict(scene=s, cam=Cam((1.4 + 0.5 * u, 1.9, 6.2 - 0.6 * u), (0, 0.9, 0.2), 52), points=SHOW_POINTS, amb=0.3)

def sh_money(u, t, dt):
    """It's your money: a fan of bills in a buyer's hand."""
    fan = cat([box(-0.03, 0, -0.005, 0.03, 0.15, 0.005, (255, 255, 255), texs={"f": F.T_BILL}).rot("z", -30 + 15 * i, (0, 0, 0)).mv(0, 0, 0.002 * i)
               for i in range(5)])
    hand = cbox(0, -0.03, 0, 0.09, 0.08, 0.04, (200, 160, 120))
    sl = cbox(0, -0.18, 0, 0.1, 0.24, 0.07, (60, 60, 140))
    g = cat([fan, hand, sl]).sc(2.0).rot("z", 8 * math.sin(t * 3)).mv(0, 1.2, 0)
    return dict(scene=showroom(t, turntable=False) + [g], cam=Cam((0.0, 1.35, 1.3 - 0.25 * u), (0, 1.35, 0), 50), points=SHOW_POINTS, amb=0.38)

def sh_theircar(u, t, dt):
    """It's their car: the yellow key fob dangles, then the salesman's hand closes and pulls it away."""
    k = ease(max(0, (u - 0.35) / 0.65))
    fob = F.key_fob().rot("z", 12 * math.sin(t * 5)).sc(2.0).mv(0.6 * k, 1.25, -0.2)
    car = F.f458().rot("y", 160).mv(0.0, 0, -3.5)
    return dict(scene=showroom(t, turntable=False) + [fob, car], cam=Cam((0.0, 1.3, 1.0), (0.1, 1.15, -1.0), 50), points=SHOW_POINTS, amb=0.36)

def sh_question(u, t, dt):
    """Red 458 and the Purrari side by side; slow orbit."""
    a = F.f458().rot("y", 70).mv(-1.6, 0, 0)
    b = F.f458(wrap=1.0).rot("y", 110).mv(1.6, 0, 0)
    ang = math.radians(80 - 30 * ease(u))
    eye = (7.5 * math.cos(ang), 1.6, 7.5 * math.sin(ang))
    return dict(scene=showroom(t, turntable=False) + [a, b], cam=Cam(eye, (0, 0.8, 0), 48), points=SHOW_POINTS, amb=0.32)

def sh_yesno(u, t, dt):
    """YES / NO floor buttons in front of the hero 458; ends on the opening framing so the short loops."""
    yes = F.button(F.T_YES_BTN, press=max(0, math.sin(t * 6))).rot("y", 180).mv(-0.7, 0, 3.6)
    no = F.button(F.T_NO_BTN, press=max(0, math.sin(t * 6 + 3))).rot("y", 180).mv(0.7, 0, 3.6)
    e = ease(u)
    pts = [((2.8, 3.2, 1.5), (255, 236, 214), 7.5), ((-1, 4.5, 2), (255, 220, 200), 7.0), ((3.5, 0.6, 2.5), (255, 90, 60), 4.0)]
    eye = lerp((0.0, 2.0, 6.6), (5.6, 0.45, 4.6), e)
    tgt = lerp((0, 0.4, 3.2), (0.6, 0.6, 0.0), e)
    return dict(scene=showroom(t) + [car_on_table(t, rot=-25), yes, no], cam=Cam(eye, tgt, 46 + 4 * (1 - e)), points=pts, amb=0.3)

SHOTS = [
    (0.0, sh_hook, "dark showroom, spotlight snaps on the red 458 (tiny rainbow cat on the corner pillar)"),
    (ws(0, 2), sh_refuse, "salesman shakes head, pulls the key away"),
    (ws(0, 7), sh_cash, "briefcase of cash opens"),
    (ws(0, 9), sh_pushback, "case of cash shoved back across the desk"),
    (ws(1, 0), sh_pick, "spotlight picks one buyer from the queue"),
    (ws(1, 5), sh_rare, "silk cover off a yellow special 458 behind a rope"),
    (ws(2, 0), sh_contract, "contract signed: NO RESALE - FIRST YEAR"),
    (ws(2, 5), sh_nosale, "FOR SALE sign stamped NO"),
    (ws(2, 9), sh_year, "a year of calendar pages fly off"),
    (ws(3, 0), sh_wrapping, "cat livery rolled onto the 458"),
    (ws(3, 4), sh_458, "wrapped 458 orbit"),
    (ws(3, 8), sh_nyan, "rainbow-trail cat in space"),
    (ws(4, 0), sh_purrari, "the Purrari on a night road, plate PURRARI"),
    (ws(5, 0), sh_hq, "Ferrari shield on the office wall"),
    (ws(5, 3), sh_notfunny, "stern exec flicks a cat toy off the desk"),
    (ws(6, 0), sh_envelope, "sealed envelope flies onto the doormat"),
    (ws(6, 7), sh_letter, "CEASE AND DESIST letter, Purrari behind"),
    (ws(7, 0), sh_blacklist, "empty BLACKLIST clipboard"),
    (ws(8, 0), sh_vip, "velvet rope opens for one buyer"),
    (ws(9, 0), sh_money, "your money"),
    (ws(9, 3), sh_theircar, "their car: key pulled away"),
    (ws(10, 0), sh_question, "red 458 and Purrari side by side"),
    (ws(10, 9), sh_yesno, "YES / NO buttons, back to the opening framing"),
]

def shot_at(t):
    i = max(k for k, s in enumerate(SHOTS) if s[0] <= t)
    t0 = SHOTS[i][0]; t1 = SHOTS[i + 1][0] if i + 1 < len(SHOTS) else DUR
    return i, (t - t0) / (t1 - t0), t - t0

def frame_lowres(t):
    i, u, dt = shot_at(t)
    d = SHOTS[i][1](u, t, dt)
    if i and dt < 0.18: d["cam"].fov *= 1 + 0.22 * (1 - dt / 0.18) ** 2      # zoom punch on every cut
    return render(d["scene"], d["cam"], d.get("bg", SHOW_BG), fog=d.get("fog", SHOW_FOG), amb=d.get("amb", 0.34), dif=0.6,
                  light=d.get("light", (-0.4, 0.8, 0.45)), points=d.get("points", SHOW_POINTS))

# ---------------------------------------------------------------- captions (small, one word at a time)
CAP_FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 66)
CAP_Y = int(0.58 * OH)
HOT = {"refuse", "money.", "contract:", "reselling", "Purrari.", "funny.", "cease-and-desist.", "blacklists", "money.", "car.", "Yes,", "no?"}

def caption_at(t):
    for k, o in enumerate(WORDS):
        nxt = WORDS[k + 1]["s"] if k + 1 < len(WORDS) else DUR
        if o["s"] <= t < min(nxt, o["e"] + 0.35): return k, o["w"]
    return None, None

def draw_caption(im, word, pop=0.0):
    d = ImageDraw.Draw(im)
    col = (255, 70, 60) if word in HOT else (255, 255, 255)
    y = CAP_Y - int(10 * pop)
    d.text((OW // 2, y), word, font=CAP_FONT, fill=col, anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0))
    return d.textbbox((OW // 2, y), word, font=CAP_FONT, anchor="mm", stroke_width=5)

def frame(n):
    t = n / FPS
    im = Image.fromarray(finish(frame_lowres(t), seed=n % 7))
    k, w = caption_at(t)
    if w: draw_caption(im, w, max(0, 1 - (t - WORDS[k]["s"]) / 0.08))
    return np.asarray(im)

def meta(path):
    caps = []; capH = CAP_FONT.getbbox("H")[3] - CAP_FONT.getbbox("H")[1]
    for o in WORDS:
        x0, y0, x1, y1 = draw_caption(Image.new("RGB", (OW, OH)), o["w"])
        caps.append(dict(text=o["w"], t=o["s"], x0=x0, y0=y0 - 10, x1=x1, y1=y1, cap_height=capH))
    onscreen = ["FERRARI", "SF", "SALES CONTRACT", "NO RESALE - FIRST YEAR", "FOR SALE", "NO", "PURRARI", "CEASE AND DESIST", "BLACKLIST", "YES"] + M.MONTHS
    json.dump(dict(size=[OW, OH], fps=FPS, duration=DUR, captions=caps, onscreen=onscreen,
                   shots=[dict(t=round(s[0], 2), what=s[2]) for s in SHOTS]), open(path, "w"), indent=1)

def thumb(path):
    t = 13.5
    red = F.f458().rot("y", 200).mv(-1.2, 0, -2.6)
    car = F.f458(wrap=1.0, plate=True).rot("y", -28).mv(0.4, 0, 0.6)
    pts = [((3.0, 3.0, 3.0), (255, 240, 230), 8.0), ((-1, 4.0, 2.5), (255, 220, 200), 7.0), ((3.5, 1.0, 3.0), (255, 120, 230), 5.0),
           ((-2.5, 2.0, -1.0), (255, 120, 90), 5.0)]
    im = Image.fromarray(finish(render(showroom(t, turntable=False) + [red, car, F.trail(4.5, 0, 0.3, 0.5, 0).rot("y", -28).mv(-1.5, 0, 1.6)],
                                       Cam((4.8, 1.3, 6.2), (0.0, 0.7, 0.6), 46), SHOW_BG, fog=SHOW_FOG, points=pts, amb=0.5, dif=0.7)))
    d = ImageDraw.Draw(im)
    for i, (line, c, sz) in enumerate([("FERRARI", (255, 255, 255), 140), ("vs", (255, 220, 60), 90), ("THE PURRARI", (255, 60, 50), 124)]):
        d.text((OW // 2, [200, 330, 450][i]), line, font=font(sz), fill=c, anchor="mm", stroke_width=10, stroke_fill=(0, 0, 0))
    im.save(path)

def sheet(path, times=None):
    times = times or [s[0] + 0.35 for s in SHOTS]
    th = [Image.fromarray(frame(int(t * FPS))).resize((216, 384)) for t in times]
    cols = 8; rows = (len(th) + cols - 1) // cols
    sh = Image.new("RGB", (cols * 216, rows * 384))
    for i, im in enumerate(th): sh.paste(im, ((i % cols) * 216, (i // cols) * 384))
    sh.save(path)

def video(voice, out, t0=0.0, t1=DUR):
    from multiprocessing import Pool
    from mix import build_mix
    mixwav = out + ".mix.wav"; build_mix(voice, mixwav, SHOTS, DUR, t0)
    n0, n1 = int(t0 * FPS), int(t1 * FPS)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
           "-i", mixwav, "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p",
           "-af", "alimiter=limit=0.7:level=false,loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", "-t", str(t1 - t0), out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for k, fr in enumerate(pool.imap(frame, range(n0, n1), chunksize=4)):
            ff.stdin.write(fr.tobytes())
            if k % 150 == 0: print("frame", n0 + k, flush=True)
    ff.stdin.close(); ff.wait(); os.remove(mixwav)
    if ff.returncode: sys.exit("ffmpeg failed")
    tmp = out + ".ln.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-t", f"{t1 - t0 - 0.05:.2f}", "-c:v", "copy", "-af",
                    f"loudnorm=I=-12.8:TP=-1.5:LRA=11,afade=t=out:st={t1 - t0 - 0.3:.2f}:d=0.25,alimiter=limit=0.89:level=false", "-ar", "48000",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", tmp], check=True); os.replace(tmp, out)
    print("ok", out)

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "still": Image.fromarray(frame(int(float(sys.argv[2]) * FPS))).save(sys.argv[3])
    elif cmd == "sheet": sheet(sys.argv[2])
    elif cmd == "meta": meta(sys.argv[2])
    elif cmd == "thumb": thumb(sys.argv[2])
    elif cmd == "video": video(sys.argv[2], sys.argv[3], *[float(x) for x in sys.argv[4:6]])
