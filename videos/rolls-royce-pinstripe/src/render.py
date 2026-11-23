"""rolls-royce-pinstripe: PS1-style low-poly short. 24 literal shots, one narrator, word-by-word captions.
python render.py still T out.png | sheet out.png | meta out.json | thumb out.png | video voice.wav out.mp4 [t0 t1]"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
from lowpoly import W, H, P, cat, box, cbox, cyl, sphere, quad, tiles, wall, Cam, sky, render, finish, font, tex
import models as M

HERE = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(HERE, "words.json")))
FPS, OW, OH = 30, 1080, 1920
DUR = 34.4

def ws(line, i=0):
    return [o for o in WORDS if o["line"] == line][i]["s"]

def ease(u): return u * u * (3 - 2 * u)
def lerp(a, b, u): return tuple(x + (y - x) * u for x, y in zip(a, b))
def shake(t, amt, f=23.0):
    return (amt * math.sin(t * f * 6.1), amt * math.sin(t * f * 4.3 + 1), amt * math.sin(t * f * 5.2 + 2))

# ---------------------------------------------------------------- characters + textures
F_PAINTER = M.face_tex(skin=(214, 172, 142), hair=(120, 116, 112), mouth="flat", brows=(90, 86, 80))
F_PAINTER_FOCUS = M.face_tex(skin=(214, 172, 142), hair=(120, 116, 112), mouth="open", brows=(90, 86, 80), eyes_wide=True)
F_AVATAR = M.face_tex(skin=(176, 118, 76), hair=(20, 16, 14), glasses=True, mouth="smile")
F_AVATAR_TALK = M.face_tex(skin=(176, 118, 76), hair=(20, 16, 14), glasses=True, mouth="open")
F_CROWD = [M.face_tex(skin=s, hair=h, mouth="open", eyes_wide=True)
           for s, h in (((230, 190, 160), (90, 60, 30)), ((150, 100, 70), (20, 20, 20)), ((200, 160, 120), (200, 190, 160)),
                        ((120, 80, 56), (30, 26, 22)), ((240, 205, 180), (160, 70, 30)))]

def painter(**kw):
    a = dict(skin=(214, 172, 142), top=(34, 40, 52), legs=(44, 46, 54), face=F_PAINTER, hair=(120, 116, 112),
             apron=(200, 196, 186), held=M.brush())
    a.update(kw); return M.person(**a)

def avatar(talk=False, **kw):
    a = dict(skin=(176, 118, 76), top=(30, 44, 96), legs=(30, 34, 50), face=F_AVATAR_TALK if talk else F_AVATAR,
             hair=(20, 16, 14), spiky=True, shirt=(245, 245, 245))
    a.update(kw); return M.person(**a)

def _ruler():
    im = Image.new("RGB", (128, 16), (220, 200, 120)); d = ImageDraw.Draw(im)
    for x in range(2, 128, 4): d.line((x, 0, x, 4 if x % 20 else 8), fill=(40, 30, 20))
    return im
T_RULER = tex(_ruler())

# ---------------------------------------------------------------- sets
def workshop(t, odd=None, lights=True, props=True):
    s = [tiles(-12, -8, 12, 8, 0, 2.0, M.T_TILE),
         wall(-12, 0, 12, 5, -7.5, 2.5, M.T_PANEL),
         wall(-8, 0, 8, 5, -11.5, 2.5, M.T_PANEL, axis="x"),
         wall(-8, 0, 8, 5, 11.5, 2.5, M.T_PANEL, axis="x")]
    if lights:
        s += [cbox(x, 4.6, z, 3.0, 0.08, 0.35, (255, 255, 250), e=1.0) for x in (-6, 0, 6) for z in (-3, 2)]
    s.append(box(-11.4, 1.2, 2.0, -11.3, 3.0, 5.0, (255, 255, 255), texs={"r": M.T_WIN_COOL}))
    if props:     # shelves of paint tins and a yellow floor line
        for x in (-9.5, -6.5, 6.5, 9.5):
            s.append(box(x - 1.2, 0, -7.45, x + 1.2, 2.4, -7.38, (70, 74, 82)))
            for yy in (0.5, 1.3, 2.1):
                s.append(box(x - 1.15, yy, -7.4, x + 1.15, yy + 0.05, -6.95, (150, 150, 156)))
                for j in range(5):
                    c = [(200, 40, 40), (222, 176, 60), (40, 60, 140), (230, 230, 230), (30, 120, 70)][(j + int(x) + int(yy * 3)) % 5]
                    s.append(cyl(0.14, 0.14, 0.3, 6, c).mv(x - 0.9 + j * 0.45, yy + 0.05, -7.15))
        s.append(box(-12, 0.005, 3.2, 12, 0.01, 3.35, (230, 200, 40)))
    if odd is not None:   # comment bait: a squirrel in a hi-vis vest drives a forklift across the workshop
        x, z = odd
        s.append(cat([M.forklift(), M.squirrel(math.sin(t * 9), vest=True).sc(2.4).mv(-0.18, 0.98, 0).rot("y", -90)]).rot("y", 180).mv(x, 0, z))
    return s

WS_BG = sky((236, 238, 242), (205, 208, 214))
WS_FOG = (10, 30, (226, 228, 232))
NIGHT_BG = sky((10, 14, 40), (44, 40, 80))
SHOW_BG = sky((14, 14, 18), (30, 30, 36))

def showroom(t):
    s = [tiles(-12, -8, 12, 8, 0, 2.0, M.T_TILE_DARK),
         wall(-12, 0, 12, 6, -7, 3.0, -1, (36, 36, 42)),
         cyl(3.6, 3.6, 0.12, 20, (60, 60, 66)).rot("y", t * 25),
         box(-1.2, 2.4, -6.98, 1.2, 5.4, -6.9, (255, 255, 255), texs={"f": M.T_BADGE}),
         ]
    s += [cbox(x, 5.5, z, 0.6, 0.1, 0.6, (255, 250, 230), e=1.0) for x in (-3, 3) for z in (-2, 2)]
    return s

def pub(t):
    s = [tiles(-10, -4, 10, 10, 0, 2.0, M.T_COBBLE),
         wall(-6, 0, 6, 6, -2.0, 1.5, M.T_BRICK),
         box(-6.2, 6.0, -3.8, 6.2, 6.3, -1.8, (40, 30, 30)),
         P([(-6.2, 6.3, -1.8), (6.2, 6.3, -1.8), (6.2, 8.0, -3.0)], (60, 40, 34)),
         P([(-6.2, 6.3, -1.8), (6.2, 8.0, -3.0), (-6.2, 8.0, -3.0)], (60, 40, 34)),
         box(-0.7, 0, -2.0, 0.7, 2.3, -1.9, (40, 70, 50)),
         box(1.7, 0.1, -1.95, 3.0, 0.3, -1.2, (255, 255, 255), texs={"t": M.T_WOOD_DARK, "f": M.T_WOOD_DARK})]
    for x in (-3.5, 3.5):
        s.append(box(x - 1.2, 1.0, -1.98, x + 1.2, 2.5, -1.9, (255, 255, 255), texs={"f": M.T_WIN}, e=1.0))
    for x in (-3.5, 3.5):
        s.append(box(x - 0.9, 3.4, -1.98, x + 0.9, 4.8, -1.9, (255, 255, 255), texs={"f": M.T_WIN}, e=1.0))
    # bracket + swinging sign
    s.append(box(1.0, 3.9, -2.0, 2.9, 3.98, -1.9, (20, 20, 20)).rot("y", -60, (1.0, 0, -1.95)))
    sw = 6 * math.sin(t * 2.4)
    sign = box(-0.55, -1.4, -0.04, 0.55, 0, 0.04, (90, 60, 30), texs={"f": M.T_PUBSIGN, "b": M.T_PUBSIGN})
    s.append(sign.rot("x", sw).rot("y", 30).mv(1.75, 3.85, -0.65))
    # street lamp
    s += [cyl(0.06, 0.05, 4.2, 6, (30, 30, 34)).mv(-4.8, 0, 1.5), cbox(-4.8, 4.3, 1.5, 0.35, 0.4, 0.35, (255, 220, 140), e=1.0)]
    # comment bait 2: a cow standing on the pub roof
    s.append(M.cow().rot("y", 200 + 10 * math.sin(t)).mv(-2.6, 6.9, -2.7))
    return s

NIGHT_FOG = (12, 40, (30, 30, 60))

# ---------------------------------------------------------------- shots: (start time, fn(u, t, dt) -> dict)
def sh_line_dolly(u, t, dt):
    x = 2.4 - 2.4 * ease(u)
    return dict(scene=workshop(t) + [M.phantom()], cam=Cam((x, 1.08, 1.75), (x - 1.6, 0.97, 1.0), 52))

def sh_front(u, t, dt):
    a = math.radians(28 + 34 * u); r = 4.6 - 0.9 * u
    eye = (2.6 + r * math.cos(a), 0.55 + 0.25 * u, r * math.sin(a))
    return dict(scene=workshop(t) + [M.phantom()], cam=Cam(eye, (2.9, 0.95, 0.1), 50))

def sh_one_man(u, t, dt):
    p = painter(ra=(70 + 10 * math.sin(t * 3), 10, 50), la=(0, 8, 10)).rot("y", 20).mv(0.6, 0, 1.9)
    eye = (1.4 + 0.6 * u, 2.05, 6.2 - 1.4 * ease(u))
    return dict(scene=workshop(t, odd=(1.2 - 3.0 * u, -3.4)) + [M.phantom(), p], cam=Cam(eye, (0.4, 1.2, 0.8), 50))

def sh_name(u, t, dt):
    p = painter(head=(8, -4), ra=(20, 8, 60), la=(0, 6, 10)).mv(0, 0, 2.3)
    eye = (0.55 - 0.5 * u, 1.64, 3.75 - 0.25 * u)
    return dict(scene=workshop(t, odd=(0.5 - 0.6 * u, -2.4)) + [M.phantom().rot("y", 25).mv(-3, 0, -1.5), p], cam=Cam(eye, (0.0, 1.6, 2.3), 44))

def sh_calendar(u, t, dt):
    k = int(u * 26)
    s = [wall(-3, 0, 3, 4, 0, 1.0, M.T_PANEL),
         box(-0.32, 1.1, 0.0, 0.32, 1.9, 0.03, (255, 255, 255), texs={"f": M.T_CAL[(k + 1) % 12]}),
         cbox(0, 1.93, 0.03, 0.06, 0.06, 0.03, (40, 40, 40))]
    f = (u * 26) % 1     # the page being torn off flies toward the camera and spins away
    page = box(-0.32, -0.8, 0, 0.32, 0, 0.004, (255, 255, 255), texs={"f": M.T_CAL[k % 12], "b": M.T_CAL[k % 12]})
    s.append(page.rot("x", -f * 120).rot("z", f * 60).mv(f * 0.6, 1.9 + f * 0.5, 0.04 + f * 1.0))
    s.append(painter(ra=(40, 10, 30)).rot("y", 150).mv(1.1, -0.2, 1.3))
    eye = (0.25, 1.5, 2.1 - 0.35 * u)
    return dict(scene=s + [tiles(-3, 0, 3, 3, 0, 1.0, M.T_TILE)], cam=Cam(eye, (0, 1.45, 0), 46), bg=WS_BG)

def sh_machine(u, t, dt):
    s = workshop(t, props=True) + [M.robot_arm(droop=1.0, light=(255, 30, 20) if (t * 4) % 1 < 0.5 else (60, 10, 10)).mv(-8.5, 0, -6.2),
                                  cbox(-7.5, 0.1, -5.6, 0.6, 0.2, 0.4, (90, 90, 96)),
                                  cyl(0.02, 0.02, 2.2, 4, (20, 20, 20)).rot("z", 80).mv(-6.6, 0.03, -5.8)]
    eye = (-5.0 - 0.8 * u, 1.6, -2.6); return dict(scene=s, cam=Cam(eye, (-8.4, 1.0, -6.4), 48))

def sh_sticker(u, t, dt):
    bench = box(-1.2, 0, -0.6, 1.2, 0.9, 0.6, (255, 255, 255), texs={"t": M.T_WOOD, "f": M.T_WOOD})
    bin_ = cyl(0.28, 0.32, 0.65, 10, (60, 70, 80)).mv(1.7, 0, 0.3)
    hole = cyl(0.27, 0.27, 0.01, 10, (10, 10, 12)).mv(1.7, 0.65, 0.3)
    v = min(1, u / 0.75); x = -0.3 + 2.0 * v; y = 1.0 + 0.6 * math.sin(math.pi * v) - (0.9 * max(0, v - 0.85) / 0.15 if v > 0.85 else 0)
    roll = cyl(0.12, 0.12, 0.06, 12, M.GOLD, capcol=(80, 60, 30)).rot("x", 90).rot("z", -u * 720).mv(x, y, 0.3)
    tail_ = quad((x, y - 0.1, 0.33), (x - 0.5, 0.92, 0.33), (x - 0.5, 0.92, 0.35), (x, y - 0.1, 0.35), M.GOLD)
    s = workshop(t, props=True, lights=False) + [bench, bin_, hole, roll, tail_]
    return dict(scene=s, cam=Cam((0.7 + 0.3 * u, 1.55, 3.5), (0.7, 1.05, 0.3), 50))

def sh_ruler(u, t, dt):
    bench = box(-1.6, 0, -0.6, 1.6, 0.9, 0.6, (255, 255, 255), texs={"t": M.T_WOOD, "f": M.T_WOOD})
    ruler = box(-0.6, 0.9, -0.05, 0.6, 0.915, 0.07, (255, 255, 255), texs={"t": T_RULER}).rot("y", 12, (0, 0, 0))
    web = [quad((-0.6, 0.915, 0.0), (-0.2, 0.915, 0.03), (-0.2, 1.25, -0.2), (-0.6, 1.3, -0.25), (210, 210, 220)).mv(0, 0, 0),
           ]
    webs = [cyl(0.003, 0.003, 0.55, 3, (235, 235, 240), e=1.0).rot("z", a).mv(-0.55, 0.915, 0.02) for a in (-20, -45, -70)]
    dust = [cbox(x, 0.92, z, 0.03, 0.01, 0.03, (150, 140, 120)) for x, z in np.random.default_rng(2).uniform(-0.6, 0.6, (20, 2))]
    spider = cat([sphere(0.02, 6, 4, (20, 20, 20)).mv(-0.2, 1.2, -0.05)])
    s = workshop(t, props=True, lights=False) + [bench, ruler, *webs, *dust, spider]
    return dict(scene=s, cam=Cam((0.9 - 0.6 * u, 1.35, 1.1), (-0.1, 0.92, 0.0), 46))

def sh_brush(u, t, dt):
    b = M.brush(5).mv(0, 0, 0.3).rot("x", -72).rot("y", 60 + 160 * u).mv(0, 1.1, 0)
    spot = cyl(1.0, 1.0, 0.02, 14, (60, 60, 70)).mv(0, 0.4, 0)
    return dict(scene=[b, spot], cam=Cam((0.0, 1.45, 2.7 - 0.4 * u), (0, 1.15, -0.2), 50), bg=SHOW_BG)

def sh_squirrel(u, t, dt):
    sq = M.squirrel(math.sin(t * 10)).sc(2.2).rot("y", -30 + 60 * math.sin(u * 3)).mv(0, 0.9, 0)
    bench = box(-1.2, 0, -0.6, 1.2, 0.9, 0.6, (255, 255, 255), texs={"t": M.T_WOOD, "f": M.T_WOOD})
    b = M.brush(3).rot("y", 80).mv(0.6, 0.94, 0.2)
    s = workshop(t, props=True) + [bench, sq, b]
    return dict(scene=s, cam=Cam((0.4 - 0.3 * u, 1.55, 1.9), (0.1, 1.35, 0), 48))

def sh_width(u, t, dt):
    jaw = 0.12 - 0.09 * ease(min(1, u * 1.6))
    cal = cat([box(-0.01, 0.985 + jaw, 1.03, 0.4, 0.985 + jaw + 0.015, 1.05, (200, 204, 210)),
               box(-0.01, 0.985 - jaw - 0.015, 1.03, 0.4, 0.985 - jaw, 1.05, (200, 204, 210)),
               box(0.38, 0.985 - jaw - 0.015, 1.03, 0.42, 1.4, 1.05, (200, 204, 210)),
               box(0.39, 1.1, 1.05, 0.41, 1.4, 1.06, (255, 255, 255), texs={"f": T_RULER})]).mv(0.2, 0, 0)
    eye = (0.3 - 0.1 * u, 1.05, 1.62); return dict(scene=workshop(t, props=True) + [M.phantom(), cal], cam=Cam(eye, (0.35, 0.985, 1.0), 40))

def _tip(frac): return 2.55 + (-2.7 - 2.55) * frac

def sh_track(u, t, dt):
    frac = 0.08 + 0.47 * u; x = _tip(frac)
    p = painter(ra=(80, 0, 15), la=(30, 10, 40), step=8 * math.sin(t * 6)).rot("y", 180).mv(x - 0.3, 0.0, 1.85)
    return dict(scene=workshop(t) + [M.phantom(line=frac), p], cam=Cam((x + 1.4, 1.25, 3.4), (x - 0.2, 1.0, 1.0), 50))

def sh_wide(u, t, dt):
    frac = 0.55 + 0.45 * ease(u); x = _tip(frac)
    p = painter(ra=(80, 0, 15), la=(30, 10, 40), step=8 * math.sin(t * 6)).rot("y", 180).mv(x - 0.3, 0.0, 1.85)
    return dict(scene=workshop(t) + [M.phantom(line=frac), p], cam=Cam((1.5 - 2.0 * u, 4.2, 7.5), (0, 0.8, 0.6), 50))

def sh_wobble(u, t, dt):
    sx, sy, _ = shake(t, 0.012, 7)
    x = 0.3 - 0.25 * u
    hand = cat([box(-0.04, -0.1, -0.035, 0.04, 0.0, 0.035, (214, 172, 142)), M.brush(1).mv(0, -0.08, 0.0),
                box(-0.04, 0.0, -0.04, 0.04, 0.25, 0.04, (34, 40, 52))]).rot("y", 180).mv(0, 0.08, 0.13)
    hand = hand.mv(sx, 0.985 + sy, 1.012)
    x = _tip(0.45)
    eye = (x - 0.25, 1.1, 1.85)
    return dict(scene=workshop(t) + [M.phantom(line=0.45, line_wobble=0.9), hand.mv(x - 0.05 * u, 0, 0)],
                cam=Cam(eye, (x + 0.35, 0.98, 1.0), 40, roll=3 * math.sin(t * 20)))

def sh_crowd(u, t, dt):
    s = workshop(t, props=True)
    for i, f in enumerate(F_CROWD):
        x = -2.4 + i * 1.2
        turn = max(0, min(1, u * 3 - i * 0.25))
        s.append(M.person(skin=(200, 160, 120), top=[(150, 40, 40), (40, 90, 60), (60, 60, 140), (200, 150, 40), (90, 90, 90)][i],
                          face=f, head=(-50 + 50 * turn, 0), la=(10, 5, 10), ra=(10, 5, 10)).mv(x, 0, 0.3 * (i % 2)))
    return dict(scene=s, cam=Cam((-2.6 + 4.0 * u, 1.6, 3.4), (-1.2 + 3.0 * u, 1.55, 0), 50))

def sh_clock(u, t, dt):
    mins = 3 * 360 * ease(u)
    warm = u
    s = [wall(-4, 0, 4, 4, 0, 1.0, M.T_PANEL), M.clock(mins, 300 + mins / 12).mv(0, 2.2, 0.02),
         box(1.1, 1.2, 0.0, 2.4, 2.8, 0.03, (255, 255, 255), texs={"f": M.T_WIN_COOL if u < 0.5 else M.T_WIN}, e=1.0)]
    p = painter(ra=(80, 0, 20)).rot("y", 180).mv(-1.4, 0, 1.0)
    bg = WS_BG
    return dict(scene=s + [p], cam=Cam((0.3, 2.0, 2.6 - 0.6 * u), (0.1, 2.1, 0), 50), bg=bg,
                amb=0.45 + 0.1 * math.sin(u * math.pi), light=(-0.4 + 0.8 * warm, 0.8, 0.45))

def splat(n=9, r=0.06, x=0.0, seed=1):
    g = np.random.default_rng(seed); out = []
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        r0, r1 = r * g.uniform(0.6, 1.3), r * g.uniform(0.6, 1.3)
        out.append(P([(x, 0.985, 1.016), (x + r0 * math.cos(a0), 0.985 + r0 * math.sin(a0), 1.016),
                       (x + r1 * math.cos(a1), 0.985 + r1 * math.sin(a1), 1.016)], M.GOLD, e=0.35))
    return cat(out)

def sh_slip(u, t, dt):
    k = min(1, u * 3)
    sx, sy, _ = shake(t, 0.03 * (1 - u), 9)
    hand = cat([box(-0.04, -0.1, -0.035, 0.04, 0.0, 0.035, (214, 172, 142)), M.brush(1).mv(0, -0.08, 0.0),
                box(-0.04, 0.0, -0.04, 0.04, 0.25, 0.04, (34, 40, 52))]).rot("y", 180).mv(0, 0.08, 0.13)
    x = _tip(0.45)
    hand = hand.rot("z", 40 * k, (0, 0.2, 0)).mv(x - 0.02 - 0.15 * k, 0.985 + 0.1 * k, 1.012)
    s = workshop(t) + [M.phantom(line=0.45), hand]
    if u > 0.2: s.append(splat(r=0.07 * min(1, (u - 0.2) * 4), x=x - 0.04))
    return dict(scene=s, cam=Cam((x - 0.3 + sx, 1.1 + sy, 1.8), (x + 0.3, 0.98, 1.0), 40))

def sh_eraser(u, t, dt):
    x = _tip(0.45) - 0.04
    e = M.eraser().sc(0.35).rot("x", 90).mv(x + 0.04 * math.sin(t * 22), 1.05, 1.06)
    crumbs = [cbox(x + 0.05 * i, 0.9 - 0.04 * ((t * 3 + i * 0.3) % 1) * 8, 1.15, 0.02, 0.02, 0.02, (240, 140, 160)) for i in range(4)]
    s = workshop(t) + [M.phantom(line=0.45), splat(r=0.07, x=x), e, *crumbs]
    return dict(scene=s, cam=Cam((x + 0.45, 1.2, 2.0), (x - 0.05, 1.0, 1.0), 42))

def sh_twist(u, t, dt):
    a = math.radians(-60 + 200 * ease(u)); r = 2.0 - 0.7 * u
    p = painter(head=(0, 0), ra=(20, 10, 20)).mv(0, 0, 0)
    eye = (r * math.sin(a), 1.65, r * math.cos(a))
    return dict(scene=workshop(t, props=True) + [p], cam=Cam(eye, (0, 1.6, 0), 60 - 20 * u, roll=12 * math.sin(u * math.pi)))

def sh_pub(u, t, dt):
    eye = (2.2, 0.6 + 3.8 * ease(u), 6.0 - 1.2 * u)
    return dict(scene=pub(t), cam=Cam(eye, (0.6, 3.0 + 1.0 * u, -1.6), 56), bg=NIGHT_BG, fog=NIGHT_FOG,
                amb=0.32, light=(0.3, 0.6, 0.7))

def sh_ladder(u, t, dt):
    yng = painter(face=F_PAINTER_FOCUS, hair=(60, 40, 24), held=M.brush(1.2), ra=(95 + 10 * math.sin(t * 8), 10, 20), la=(80, 0, 40),
                  apron=(170, 160, 140)).rot("y", 145).mv(2.0, 1.2, 0.6)
    lad = M.ladder(3.0).rot("x", -12).mv(2.2, 0, 0.75)
    a = math.radians(20 + 30 * u)
    eye = (1.9 + 3.0 * math.sin(a), 2.7, 0.0 + 3.0 * math.cos(a) + 0.6)
    return dict(scene=pub(t) + [lad, yng], cam=Cam(eye, (1.75, 3.1, -0.4), 52), bg=NIGHT_BG, fog=NIGHT_FOG,
                amb=0.34, light=(0.3, 0.6, 0.7))

def sh_robot(u, t, dt):
    hit = 0.55
    s = [tiles(-6, -4, 6, 6, 0, 2.0, M.T_TILE_DARK), wall(-6, 0, 6, 4, -2.5, 2.0, M.T_PANEL),
         box(-0.6, 2.0, -2.49, 0.6, 3.4, -2.45, (255, 255, 255), texs={"f": M.T_BADGE}),
         box(-1.2, 0, -0.5, 1.2, 0.78, 0.5, (255, 255, 255), texs={"t": M.T_WOOD_DARK, "f": M.T_WOOD_DARK, "r": M.T_WOOD_DARK}),
         M.robot(ra=(40, 5, 50), la=(40, 5, 50), head=10 * math.sin(t * 2)).mv(0, 0, -1.2),
         box(-0.2, 0.78, 0.0, 0.2, 0.785, 0.45, (255, 255, 255), texs={"t": M.T_PAPER_STAMP if u > hit else M.T_PAPER})]
    sy = 0.79 + (0.6 * (1 - u / hit) if u < hit else 0.02 + 0.5 * min(1, (u - hit) * 4))
    s.append(M.stamp().mv(0.0, sy, 0.22))
    sx, syy, _ = shake(t, 0.03 if hit < u < hit + 0.12 else 0, 13)
    eye = lerp((0.0, 2.0, 3.0), (0.2, 1.6, 1.0), ease(u))
    return dict(scene=s, cam=Cam((eye[0] + sx, eye[1] + syy, eye[2]), lerp((0, 1.3, -0.8), (0, 0.8, 0.2), ease(u)), 52), bg=WS_BG)

def sh_hired(u, t, dt):
    p = painter(ra=(150, 10, 10), la=(0, 8, 10), held=M.brush(1.5)).rot("y", 20).mv(0.2, 0, 1.9)
    sign = box(-0.55, 2.0, -7.4, 0.55, 3.4, -7.32, (255, 255, 255), texs={"f": M.T_PUBSIGN})
    a = math.radians(15 + 25 * u); r = 7.6 - 1.2 * u
    eye = (r * math.sin(a), 1.4 + 0.5 * u, r * math.cos(a))
    return dict(scene=workshop(t) + [M.phantom(), p, sign], cam=Cam(eye, (0.0, 1.3, 0.0), 50))

def sh_question(u, t, dt):
    talk = int(t * 8) % 2 == 0
    av = avatar(talk=talk, ra=(15, 125 + 18 * math.sin(t * 9), 40), la=(10, 8, 10)).rot("y", -10).mv(1.2, 0, 2.2)
    car = M.phantom().rot("y", 18 + 10 * u).mv(-0.6, 0.12, -0.6)
    eye = (1.35 + 0.1 * u, 1.65, 4.4 - 0.6 * ease(u))
    return dict(scene=showroom(t) + [car, av], cam=Cam(eye, (0.8, 1.45, 1.6), 52), bg=SHOW_BG, amb=0.62, fog=(14, 30, (14, 14, 18)))

def sh_yesno(u, t, dt):
    car = M.phantom().rot("y", 18 + 10 * (u + 1)).mv(-0.6, 0.12, -0.6)
    av = avatar(talk=False, ra=(50, 45, 70), la=(50, 45, 70)).rot("y", 35).mv(1.9, 0, 2.8)
    a = math.radians(75 - 25 * u)
    eye = (-0.6 + 7.6 * math.cos(a), 1.6, -0.6 + 7.6 * math.sin(a))
    return dict(scene=showroom(t) + [car, av], cam=Cam(eye, (-0.2, 0.9, 0), 46), bg=SHOW_BG, amb=0.62, fog=(14, 30, (14, 14, 18)))

SHOTS = [
    (0.0, sh_line_dolly, "coachline dolly"),
    (ws(0, 4), sh_front, "grille, RR badge, Spirit of Ecstasy"),
    (ws(0, 7), sh_one_man, "the painter with his brush; squirrel forklift behind"),
    (ws(1, 0), sh_name, "painter portrait"),
    (ws(1, 5), sh_calendar, "calendar pages flying off"),
    (ws(2, 0), sh_machine, "robot arm switched off"),
    (ws(2, 2), sh_sticker, "sticker roll binned"),
    (ws(2, 4), sh_ruler, "ruler covered in cobwebs"),
    (ws(3, 0), sh_brush, "the brush"),
    (ws(3, 3), sh_squirrel, "squirrel"),
    (ws(4, 0), sh_width, "calipers on the line"),
    (ws(5, 0), sh_track, "brush tracking along the side"),
    (ws(5, 8), sh_wide, "whole side, one go"),
    (ws(6, 0), sh_wobble, "shaking hand, wobbly line"),
    (ws(6, 2), sh_crowd, "everyone turns and stares"),
    (ws(7, 0), sh_clock, "clock spins three hours"),
    (ws(8, 0), sh_slip, "slip and splat"),
    (ws(8, 4), sh_eraser, "eraser does nothing"),
    (ws(9, 0), sh_twist, "spin on the painter"),
    (ws(9, 3), sh_pub, "pub at night, cow on the roof"),
    (ws(9, 6), sh_ladder, "painting the pub sign"),
    (ws(10, 0), sh_robot, "robot not hired"),
    (ws(11, 0), sh_hired, "pub sign painter hired"),
    (ws(12, 0), sh_question, "avatar asks"),
    (ws(12, 10), sh_yesno, "yes or no"),
]

def shot_at(t):
    i = max(k for k, s in enumerate(SHOTS) if s[0] <= t)
    t0 = SHOTS[i][0]; t1 = SHOTS[i + 1][0] if i + 1 < len(SHOTS) else DUR
    return i, (t - t0) / (t1 - t0), t - t0

def frame_lowres(t):
    i, u, dt = shot_at(t)
    d = SHOTS[i][1](u, t, dt)
    return render(d["scene"], d["cam"], d.get("bg", WS_BG), fog=d.get("fog", WS_FOG if "bg" not in d else None),
                  amb=d.get("amb", 0.45), light=d.get("light", (-0.4, 0.8, 0.45)))

# ---------------------------------------------------------------- captions (one word at a time)
CAP_FONT = font(70)
CAP_Y = int(0.55 * OH)
def caption_at(t):
    for k, o in enumerate(WORDS):
        nxt = WORDS[k + 1]["s"] if k + 1 < len(WORDS) else DUR
        end = min(nxt, o["e"] + 0.35)
        if o["s"] <= t < end: return k, o["w"]
    return None, None

def draw_caption(im, word):
    d = ImageDraw.Draw(im)
    d.text((OW // 2, CAP_Y), word, font=CAP_FONT, fill=(255, 241, 118), anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0))
    return d.textbbox((OW // 2, CAP_Y), word, font=CAP_FONT, anchor="mm", stroke_width=5)

def frame(n):
    t = n / FPS
    im = Image.fromarray(finish(frame_lowres(t)))
    _, w = caption_at(t)
    if w: draw_caption(im, w)
    return np.asarray(im)

def meta(path):
    caps = []
    capH = CAP_FONT.getbbox("H")[3] - CAP_FONT.getbbox("H")[1]
    for k, o in enumerate(WORDS):
        im = Image.new("RGB", (OW, OH)); x0, y0, x1, y1 = draw_caption(im, o["w"])
        caps.append(dict(text=o["w"], t=o["s"], x0=x0, y0=y0, x1=x1, y1=y1, cap_height=capH))
    onscreen = ["ROLLS ROYCE", "THE SQUIRREL & BRUSH", "APPLICATION", "NOT HIRED"] + M.MONTHS
    json.dump(dict(size=[OW, OH], fps=FPS, duration=DUR, captions=caps, onscreen=onscreen,
                   shots=[dict(t=round(s[0], 2), what=s[2]) for s in SHOTS]), open(path, "w"), indent=1)

def thumb(path):
    t = ws(5, 8) + 0.4
    im = Image.fromarray(finish(render(workshop(t) + [M.phantom(line=0.8), painter(ra=(80, 0, 15), la=(30, 10, 40)).rot("y", 180).mv(_tip(0.8) - 0.3, 0, 1.85)],
                                       Cam((0.6, 1.5, 5.6), (-1.4, 1.05, 0.8), 52), WS_BG, fog=WS_FOG)))
    d = ImageDraw.Draw(im); f = font(118)
    for i, line in enumerate(["ONE MAN.", "ONE BRUSH.", "NO STICKER."]):
        d.text((OW // 2, 260 + i * 150), line, font=f, fill=(255, 241, 118) if i < 2 else (255, 255, 255), anchor="mm", stroke_width=9, stroke_fill=(0, 0, 0))
    im.save(path)

def sheet(path, times=None):
    times = times or [s[0] + 0.3 for s in SHOTS]
    th = [Image.fromarray(frame(int(t * FPS))).resize((216, 384)) for t in times]
    cols = 7; rows = (len(th) + cols - 1) // cols
    sh = Image.new("RGB", (cols * 216, rows * 384))
    for i, im in enumerate(th): sh.paste(im, ((i % cols) * 216, (i // cols) * 384))
    sh.save(path)

def video(voice, out, t0=0.0, t1=DUR):
    from multiprocessing import Pool
    from mix import build_mix
    mixwav = out + ".mix.wav"; build_mix(voice, mixwav, SHOTS, DUR)
    n0, n1 = int(t0 * FPS), int(t1 * FPS)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
           "-ss", str(t0), "-t", str(t1 - t0), "-i", mixwav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-af", "alimiter=limit=0.7:level=false,loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for k, fr in enumerate(pool.imap(frame, range(n0, n1), chunksize=4)):
            ff.stdin.write(fr.tobytes())
            if k % 150 == 0: print("frame", n0 + k, flush=True)
    ff.stdin.close(); ff.wait(); os.remove(mixwav)
    if ff.returncode: sys.exit("ffmpeg failed")
    tmp = out + ".ln.mp4"     # second loudness pass on the finished audio: the first lands about 1 LU low
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", tmp], check=True); os.replace(tmp, out)
    print("ok", out)

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "still": Image.fromarray(frame(int(float(sys.argv[2]) * FPS))).save(sys.argv[3])
    elif cmd == "sheet": sheet(sys.argv[2])
    elif cmd == "meta": meta(sys.argv[2])
    elif cmd == "thumb": thumb(sys.argv[2])
    elif cmd == "video": video(sys.argv[2], sys.argv[3], *[float(x) for x in sys.argv[4:6]])
