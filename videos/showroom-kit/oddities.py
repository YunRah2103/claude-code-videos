"""Background oddities (comment bait, never mentioned). Each ODD[name](img, t, tau) draws itself in the showroom layout of
engine.py; tau is the time since its scene started. Old ones come from bmw-heated-seats and platform-ladder."""
import math
from PIL import Image
from functools import lru_cache
from engine import D, K, OL, CEIL, CX, PLAT_Y, clamp, prog, spline, io, oc, npc, cast, mk, walkst

def paste_rot(img, layer, cx, cy, rot=0.0, flip=False):
    if flip: layer = layer.transpose(Image.FLIP_LEFT_RIGHT)
    if rot: layer = layer.rotate(rot, resample=Image.BICUBIC, expand=True)
    img.paste(layer, (int(cx * K - layer.width / 2), int(cy * K - layer.height / 2)), layer)

# 1 showroom: a snowman relaxing in a steaming hot tub, mug in hand, melting.   2 map room: a flamingo riding a robot vacuum.
# 3 payment office: two sheep stacked on top of a filing cabinet.   4 press conference: a llama with a press pass taking selfies.
# 5 showroom again: a mother duck driving a tiny ride-on car, three ducklings waddling after it.
def snowman(d, x, fy, t, s=1.0):
    melt = clamp(t / 14)                                   # sinks a little and the puddle grows
    d.ell(x, fy - 2, (52 + 30 * melt) * s, (9 + 3 * melt) * s, (196, 226, 246, 200))
    sink = 10 * melt * s
    W_, SH = (250, 252, 255), (206, 220, 236)
    for r_, cy in ((50, fy - 46 + sink), (38, fy - 120 + sink), (28, fy - 176 + sink)):
        d.ell(x, cy, r_ * s, r_ * s, W_, OL, 3); d.ell(x + 8 * s, cy + 6 * s, r_ * .6 * s, r_ * .6 * s, SH)
        d.ell(x - 6 * s, cy - 6 * s, r_ * .55 * s, r_ * .55 * s, W_)
    wave = math.sin(t * 2.4) * 10
    for side, ang in ((-1, 0), (1, wave)):
        sx_, sy_ = x + side * 34 * s, fy - 128 + sink
        ex, ey = sx_ + side * 50 * s, sy_ - 26 * s - (ang if side > 0 else 0) * s
        d.line([(sx_, sy_), (ex, ey)], (110, 72, 40), 5); d.line([(ex - side * 14 * s, ey + 2), (ex + side * 4 * s, ey - 14 * s)], (110, 72, 40), 4)
    hy = fy - 176 + sink
    d.rect(x - 34 * s, hy - 13 * s, x + 34 * s, hy - 3 * s, (28, 105, 190), r=4)                # blue scarf
    d.poly([(x + 12 * s, hy - 6 * s), (x + 26 * s, hy - 6 * s), (x + 30 * s, hy + 34 * s), (x + 16 * s, hy + 34 * s)], (28, 105, 190), OL, 2)
    d.rect(x - 34 * s, hy - 34 * s, x + 34 * s, hy - 28 * s, (20, 20, 24))                     # top hat
    d.rect(x - 22 * s, hy - 74 * s, x + 22 * s, hy - 30 * s, (20, 20, 24))
    d.rect(x - 22 * s, hy - 40 * s, x + 22 * s, hy - 34 * s, (190, 30, 40))
    blink = (t % 3.7) < .12
    for side in (-1, 1):
        if blink: d.line([(x + side * 10 * s - 4, hy - 8 * s), (x + side * 10 * s + 4, hy - 8 * s)], OL, 2)
        else: d.ell(x + side * 10 * s, hy - 8 * s, 3.5 * s, 3.5 * s, OL)
    d.poly([(x - 2 * s, hy - 2 * s), (x - 2 * s, hy + 6 * s), (x - 30 * s, hy + 3 * s)], (246, 130, 30), OL, 2)   # carrot
    for i in range(3): d.ell(x, fy - 112 + sink + i * 16 * s, 3 * s, 3 * s, OL)
    mx, my = x + 70 * s, fy - 150 + sink - math.sin(t * 2.4) * 8 * s      # mug on the waving arm
    d.rect(mx - 10 * s, my - 14 * s, mx + 10 * s, my + 8 * s, (190, 30, 40), r=3, ol=OL, w=2)
    tub_top = fy - 92 * s                                                   # hot tub in front of him
    d.ell(x, tub_top, 82 * s, 16 * s, (90, 200, 230), OL, 3)
    for i in range(3):                                                      # bubbles
        bx_ = x - 50 * s + ((t * 40 + i * 37) % 100) * s
        d.ell(bx_, tub_top - 2, 5 * s, 3 * s, (230, 250, 255))
    d.poly([(x - 82 * s, tub_top), (x + 82 * s, tub_top), (x + 76 * s, fy), (x - 76 * s, fy)], (150, 98, 56), OL, 3)
    for k_ in range(-3, 4):
        d.line([(x + k_ * 22 * s, tub_top + 8), (x + k_ * 20 * s, fy - 4)], (112, 72, 40), 2)
    for k_ in (.3, .7):
        d.line([(x - 80 * s, tub_top + k_ * 92 * s), (x + 80 * s, tub_top + k_ * 92 * s)], (70, 70, 76), 4)
    for i in range(4):                                                      # steam
        ph = (t * .6 + i * .25) % 1
        sx0 = x - 50 * s + i * 34 * s
        pts = [(sx0 + 8 * math.sin(ph * 6 + k * 1.3 + i), tub_top - 20 - k * 16 - ph * 50) for k in range(5)]
        d.line(pts, (255, 255, 255, int(170 * (1 - ph))), 5)

def flamingo(d, x, fy, t, s=1.0):
    P1, P2 = (246, 140, 170), (226, 104, 140)
    bob = math.sin(t * 1.6) * 3 * s
    d.line([(x, fy), (x + 2 * s, fy - 66 * s), (x, fy - 120 * s)], (226, 104, 140), 4)              # standing leg
    d.line([(x + 1 * s, fy - 96 * s), (x + 24 * s, fy - 84 * s), (x + 4 * s, fy - 70 * s)], (226, 104, 140), 4)   # tucked leg
    d.ell(x + 4 * s, fy, 12 * s, 3 * s, (226, 104, 140))
    bx, by = x + 2 * s, fy - 140 * s + bob
    d.ell(bx, by, 52 * s, 30 * s, P1, OL, 3)
    d.poly([(bx + 30 * s, by - 6 * s), (bx + 66 * s, by - 2 * s), (bx + 34 * s, by + 14 * s)], P2, OL, 2)   # tail
    d.arc(bx - 4 * s, by - 2 * s, 30 * s, 16 * s, 200, 340, P2, 3)                                         # wing line
    tuck = max(0.0, math.sin(t * .9 - 2)) ** 4                                                              # dips its head now and then
    nk = [(bx - 40 * s, by - 6 * s), (bx - 58 * s, by - 50 * s), (bx - 30 * s, by - 90 * s + 30 * tuck * s),
          (bx - 44 * s, by - 116 * s + 44 * tuck * s)]
    nk = spline(nk, 6, closed=False)
    d.line(nk, OL, 15 * s); d.line(nk, P1, 10 * s)
    hx, hy = nk[-1]
    d.ell(hx, hy, 13 * s, 11 * s, P1, OL, 2)
    d.poly([(hx - 10 * s, hy - 2 * s), (hx - 32 * s, hy + 10 * s), (hx - 26 * s, hy + 18 * s), (hx - 8 * s, hy + 6 * s)], (250, 240, 236), OL, 2)
    d.poly([(hx - 26 * s, hy + 12 * s), (hx - 32 * s, hy + 10 * s), (hx - 26 * s, hy + 18 * s)], (20, 20, 24))
    if (t % 3.1) > .12: d.ell(hx + 3 * s, hy - 3 * s, 2.6 * s, 2.6 * s, OL)

def sheep(d, x, fy, t, s=1.0, cabinet=True):
    if cabinet: _cabinet(d, x, fy, s)
    top = fy - 150 * s if cabinet else fy
    _sheep(d, x, top, t, s)

def _cabinet(d, x, fy, s):
    d.rect(x - 58 * s, fy - 150 * s, x + 58 * s, fy, (128, 136, 146), ol=OL, w=3)
    for i in range(3):
        y = fy - 146 * s + i * 49 * s
        d.rect(x - 50 * s, y + 4, x + 50 * s, y + 44 * s, (150, 158, 168), ol=(90, 96, 104), w=2)
        d.rect(x - 14 * s, y + 18 * s, x + 14 * s, y + 24 * s, (60, 64, 70), r=3)

def _sheep(d, x, top, t, s):
    for side in (-1, 1):
        for k_ in (0, 1):
            lx = x + side * (18 + k_ * 20) * s
            d.line([(lx, top - 4), (lx, top - 34 * s)], (36, 34, 38), 7)
    wool = (244, 242, 232)
    for dx, dy, r_ in ((-30, -58, 26), (0, -66, 30), (30, -58, 26), (-18, -42, 26), (18, -42, 26), (0, -80, 22), (44, -70, 18)):
        d.ell(x + dx * s, top + dy * s, r_ * s, r_ * s, wool, OL, 2)
    for dx, dy, r_ in ((-30, -58, 24), (0, -66, 28), (30, -58, 24), (-18, -42, 24), (18, -42, 24), (0, -80, 20), (44, -70, 16)):
        d.ell(x + dx * s, top + dy * s, r_ * s, r_ * s, wool)
    chew = math.sin(t * 8) * 2 * s
    hx, hy = x - 52 * s, top - 74 * s + math.sin(t * 1.2) * 2
    for side in (-1, 1):
        d.ell(hx + side * 22 * s, hy - 12 * s, 12 * s, 6 * s, (40, 38, 44), OL, 2)
    d.ell(hx, hy, 19 * s, 26 * s, (40, 38, 44), OL, 2)
    d.ell(hx, hy + 18 * s + chew, 10 * s, 6 * s, (60, 56, 62))
    d.ell(hx, hy - 24 * s, 16 * s, 10 * s, wool)
    for side in (-1, 1):
        if (t % 3.3) < .12: d.line([(hx + side * 8 * s - 3, hy - 4 * s), (hx + side * 8 * s + 3, hy - 4 * s)], (255, 255, 255), 2)
        else: d.ell(hx + side * 8 * s, hy - 4 * s, 3.5 * s, 3.5 * s, (255, 255, 255))

def llama(d, x, fy, t, s=1.0):
    C1, C2 = (236, 222, 196), (206, 188, 156)
    for lx in (-30, -14, 26, 40):
        d.line([(x + lx * s, fy - 66 * s), (x + lx * s, fy)], C2, 9); d.ell(x + lx * s, fy, 6 * s, 3 * s, (60, 50, 40))
    d.ell(x + 4 * s, fy - 90 * s, 60 * s, 38 * s, C1, OL, 3)
    sway = math.sin(t * 1.3) * 4 * s
    nk = [(x - 36 * s, fy - 104 * s), (x - 40 * s + sway, fy - 200 * s)]
    d.line(nk, OL, 30 * s); d.line(nk, C1, 24 * s)
    hx, hy = x - 46 * s + sway, fy - 214 * s
    for side in (-1, 1):
        d.poly([(hx + side * 8 * s, hy - 16 * s), (hx + side * 16 * s, hy - 44 * s), (hx + side * 20 * s, hy - 14 * s)], C1, OL, 2)
    d.ell(hx + 4 * s, hy, 20 * s, 18 * s, C1, OL, 2)
    chew = math.sin(t * 7) * 2 * s
    d.rect(hx - 26 * s, hy - 2 * s, hx + 4 * s, hy + 18 * s + chew, C1, r=8 * s, ol=OL, w=2)
    d.ell(hx - 20 * s, hy + 4 * s, 2.5 * s, 2 * s, OL)
    px, py = hx - 70 * s, hy - 70 * s + math.sin(t * 2) * 4                 # selfie stick held in the mouth
    d.line([(hx - 24 * s, hy + 10 * s), (px, py)], (40, 40, 46), 4)
    d.rect(px - 12 * s, py - 20 * s, px + 12 * s, py + 20 * s, (20, 20, 24), r=4, ol=(200, 200, 210), w=2)
    if (t % 1.6) < .1: d.ell(px, py, 30 * s, 30 * s, (255, 255, 255, 200))
    if (t % 3.5) > .12: d.ell(hx + 2 * s, hy - 6 * s, 4 * s, 4.5 * s, OL)
    # press pass on a lanyard
    d.line([(x - 52 * s + sway, fy - 168 * s), (x - 40 * s, fy - 128 * s), (x - 26 * s + sway, fy - 168 * s)], (28, 105, 190), 3)
    d.rect(x - 52 * s, fy - 130 * s, x - 26 * s, fy - 106 * s, (250, 250, 250), r=3, ol=OL, w=2)
    d.rect(x - 50 * s, fy - 128 * s, x - 28 * s, fy - 122 * s, (190, 30, 40))

def ducks(d, t, tau, x0=800, fy0=990):
    x0 = x0 + 18 * tau
    for i, (dx, s) in enumerate(((0, 1.5), (-64, .75), (-108, .75), (-152, .75))):
        x, fy = x0 + dx * (1 + 0 * i), fy0
        hop = abs(math.sin(tau * 7 + i)) * 4 * s if i else 0.0
        if i == 0:                                                         # tiny red ride-on car under the mother duck
            d.rect(x - 44, fy - 34, x + 44, fy - 10, (210, 36, 44), r=10, ol=OL, w=3)
            d.rect(x - 20, fy - 50, x + 14, fy - 34, (170, 210, 240), r=4, ol=OL, w=2)
            for wx in (x - 26, x + 28): d.ell(wx, fy - 8, 10, 10, (24, 24, 28), OL, 2)
            d.line([(x + 26, fy - 36), (x + 34, fy - 56)], OL, 4); d.ell(x + 34, fy - 58, 9, 4, OL)
            fy -= 30
        waddle = math.sin(tau * 7 + i) * 6
        Y = (250, 214, 64) if i else (246, 246, 240)
        d.ell(x, fy - 2, 18 * s, 4 * s, (0, 0, 0, 60))
        d.ell(x, fy - 26 * s - hop, 28 * s, 20 * s, Y, OL, 2)
        d.poly([(x - 22 * s, fy - 34 * s - hop), (x - 38 * s, fy - 44 * s - hop), (x - 26 * s, fy - 22 * s - hop)], Y, OL, 2)
        hx, hy = x + 20 * s, fy - 52 * s - hop
        d.ell(hx, hy, 14 * s, 13 * s, Y, OL, 2)
        d.poly([(hx + 10 * s, hy - 2 * s), (hx + 26 * s, hy + 2 * s), (hx + 10 * s, hy + 6 * s)], (246, 150, 30), OL, 1.5)
        d.ell(hx + 4 * s, hy - 3 * s, 2.5 * s, 2.5 * s, OL)
        for side in ((-1, 1) if i else ()):
            fx = x + side * 6 * s + (waddle if side > 0 else -waddle) * s * .5
            d.line([(x + side * 6 * s, fy - 10 * s - hop), (fx, fy - 2)], (246, 150, 30), 3 * s)

# 1 VW: a penguin standing quietly behind the Touareg.   2 Porsche: a small car parked upside down on the ceiling.
# 3 Bentley: someone in an inflatable dinosaur costume, sipping tea.   4 Lamborghini: an astronaut drifting past the wall.
# 5 VW again: a giraffe's head poking down through a ceiling tile, chewing.
def penguin(d, x, fy, t, s=1.0):
    sw = math.sin(t * 1.7) * 2
    flap = max(0.0, math.sin(t * 2.3)) ** 8 * 26           # an occasional little flipper flap
    for side in (-1, 1):
        d.ell(x + side * 13 * s, fy - 4 * s, 13 * s, 6 * s, (250, 170, 40), OL, 2)
        d.poly([(x + sw + side * 30 * s, fy - 96 * s), (x + sw + side * (46 * s + (flap if side > 0 else 0)), fy - 40 * s - (flap if side > 0 else 0)),
                (x + sw + side * 34 * s, fy - 34 * s)], (24, 26, 34), OL, 3)
    d.ell(x + sw, fy - 62 * s, 36 * s, 60 * s, (24, 26, 34), OL, 3)
    d.ell(x + sw + 3 * s, fy - 54 * s, 24 * s, 46 * s, (246, 246, 244))
    hx, hy = x + sw + 5 * s * math.sin(t * .8), fy - 124 * s
    d.ell(hx, hy, 27 * s, 25 * s, (24, 26, 34), OL, 3)
    blink = (t % 3.3) < .12
    for side in (-1, 1):
        ex = hx + side * 9 * s
        if blink: d.line([(ex - 5 * s, hy - 2 * s), (ex + 5 * s, hy - 2 * s)], (255, 255, 255), 2)
        else:
            d.ell(ex, hy - 3 * s, 6 * s, 6.5 * s, (255, 255, 255)); d.ell(ex + 1.5 * s, hy - 2 * s, 3 * s, 3.5 * s, OL)
    d.poly([(hx - 8 * s, hy + 6 * s), (hx + 8 * s, hy + 6 * s), (hx, hy + 20 * s)], (250, 170, 40), OL, 2)

def dino(d, x, fy, t, s=1.0):
    """Person in an inflatable T-rex costume, holding a teacup; sways, takes a sip now and then."""
    G, G2, BL = (112, 190, 92), (80, 150, 66), (226, 236, 172)
    sw = math.sin(t * 2.0) * 5 * s
    sip = max(0.0, math.sin(t * 1.3 - 1)) ** 6
    d.poly(spline([(x - 30 * s, fy - 120 * s), (x - 150 * s, fy - 30 * s), (x - 120 * s, fy - 24 * s), (x - 20 * s, fy - 76 * s)], 5), G, OL, 3)
    for side in (-1, 1):
        d.rect(x + side * 28 * s - 15 * s, fy - 96 * s, x + side * 28 * s + 15 * s, fy - 14 * s, G2, r=10 * s, ol=OL, w=3)
        d.ell(x + side * 28 * s + 6 * s, fy - 12 * s, 22 * s, 11 * s, (40, 40, 46), OL, 2)   # human trainers
    d.ell(x + sw * .5, fy - 178 * s, 74 * s, 104 * s, G, OL, 4)
    d.ell(x + sw * .5 + 14 * s, fy - 166 * s, 44 * s, 76 * s, BL)
    d.ell(x + sw * .5 + 22 * s, fy - 232 * s, 24 * s, 16 * s, (36, 36, 42))                # face window (mesh)
    for i in range(-2, 3):
        d.line([(x + sw * .5 + 22 * s + i * 8 * s, fy - 246 * s), (x + sw * .5 + 22 * s + i * 8 * s, fy - 218 * s)], (60, 60, 66), 1.5)
    hx, hy = x + sw + 30 * s, fy - 312 * s
    d.ell(hx, hy, 54 * s, 42 * s, G, OL, 4)
    d.rect(hx + 10 * s, hy - 20 * s, hx + 84 * s, hy + 26 * s, G, r=20 * s, ol=OL, w=4)
    for i in range(5):
        tx = hx + 22 * s + i * 13 * s
        d.poly([(tx, hy + 24 * s), (tx + 10 * s, hy + 24 * s), (tx + 5 * s, hy + 34 * s)], (255, 255, 255), OL, 1.5)
    d.ell(hx + 6 * s, hy - 14 * s, 10 * s, 10 * s, (255, 255, 255), OL, 2); d.ell(hx + 9 * s, hy - 13 * s, 4.5 * s, 4.5 * s, OL)
    d.ell(hx + 74 * s, hy - 10 * s, 4 * s, 3 * s, OL)
    # tiny arm with a teacup, lifted toward the face window for a sip
    sx, sy = x + sw * .5 + 56 * s, fy - 214 * s
    hx2, hy2 = sx + 30 * s - 12 * s * sip, sy + 14 * s - 30 * s * sip
    d.line([(sx, sy), (hx2, hy2)], OL, 15 * s); d.line([(sx, sy), (hx2, hy2)], G, 10 * s)
    d.ell(hx2 + 6 * s, hy2 + 8 * s, 18 * s, 4 * s, (250, 250, 250), OL, 2)                  # saucer
    d.rect(hx2 - 6 * s, hy2 - 10 * s, hx2 + 16 * s, hy2 + 6 * s, (250, 250, 250), r=4 * s, ol=OL, w=2)
    d.arc(hx2 + 18 * s, hy2 - 2 * s, 6 * s, 6 * s, 270, 90, OL, 2)

@lru_cache(None)
def astronaut_layer():
    S = 240
    lay = Image.new('RGBA', (S * K, S * K), (0, 0, 0, 0)); d = D(lay, ox=-S / 2, oy=-S / 2)
    SU, SU2 = (244, 244, 246), (196, 198, 206)
    d.rect(-46, -20, 46, 64, (210, 212, 220), r=12, ol=OL, w=3)                                 # backpack
    for side in (-1, 1):
        d.line([(side * 20, 60), (side * 34, 96), (side * 28, 104)], OL, 30); d.line([(side * 20, 60), (side * 34, 96), (side * 28, 104)], SU, 22)
        d.ell(side * 30, 108, 16, 10, SU2, OL, 3)
        d.line([(side * 34, 0), (side * 66, 26 if side < 0 else -26), (side * 80, 4 if side < 0 else -40)], OL, 26)
        d.line([(side * 34, 0), (side * 66, 26 if side < 0 else -26), (side * 80, 4 if side < 0 else -40)], SU, 18)
        d.ell(side * 82, 4 if side < 0 else -42, 11, 11, SU2, OL, 3)
    d.rect(-38, -16, 38, 70, SU, r=18, ol=OL, w=3)
    d.rect(-18, 6, 18, 30, (90, 120, 200), r=4)                                                  # chest panel
    d.ell(-8, 18, 3, 3, (240, 80, 70)); d.ell(4, 18, 3, 3, (90, 220, 120))
    d.ell(0, -48, 40, 38, SU, OL, 3)
    d.ell(4, -48, 28, 22, (40, 44, 62)); d.ell(12, -56, 10, 6, (255, 220, 150, 170))            # visor + glint
    return lay

def astronaut(img, t, tau):
    x = 930 - 38 * tau
    y = 400 + 22 * math.sin(tau * 1.1)
    paste_rot(img, astronaut_layer(), x, y, rot=-14 * tau + 20)

def giraffe(img, t):
    d = D(img)
    hx0 = 840
    d.ell(hx0, CEIL - 2, 62, 14, (20, 18, 16))                                                    # broken tile
    for dx in (-60, -30, 24, 52):
        d.poly([(hx0 + dx, CEIL - 4), (hx0 + dx + 14, CEIL + 10), (hx0 + dx + 22, CEIL - 4)], (236, 236, 232), OL, 2)
    lean = math.sin(t * .9) * 10
    YL, YD = (238, 196, 92), (164, 104, 44)
    neck = [(hx0 - 2, CEIL), (hx0 + lean * .5, CEIL + 70), (hx0 + lean, CEIL + 130)]
    d.line(neck, OL, 52); d.line(neck, YL, 44)
    for i, (px, py) in enumerate(((hx0 - 8, CEIL + 30), (hx0 + 10, CEIL + 64), (hx0 - 6 + lean * .8, CEIL + 104))):
        d.poly(spline([(px - 10, py - 8), (px + 8, py - 10), (px + 12, py + 6), (px - 6, py + 10)], 3), YD)
    hx, hy = hx0 + lean, CEIL + 170
    chew = math.sin(t * 9) * 3
    for side in (-1, 1):
        d.line([(hx + side * 16, hy - 34), (hx + side * 20, hy - 62)], OL, 9); d.line([(hx + side * 16, hy - 34), (hx + side * 20, hy - 62)], YD, 6)
        d.ell(hx + side * 20, hy - 64, 7, 7, (90, 58, 30), OL, 2)
        d.poly([(hx + side * 30, hy - 30), (hx + side * 58, hy - 40), (hx + side * 34, hy - 18)], YL, OL, 3)
    d.ell(hx, hy - 10, 34, 36, YL, OL, 4)
    d.rect(hx - 24, hy + 4, hx + 24, hy + 50 + chew, (226, 180, 120), r=20, ol=OL, w=4)          # muzzle
    d.ell(hx - 9, hy + 32, 4, 3, OL); d.ell(hx + 9, hy + 32, 4, 3, OL)
    blink = (t % 2.9) < .14
    for side in (-1, 1):
        ex = hx + side * 15
        if blink: d.line([(ex - 7, hy - 12), (ex + 7, hy - 12)], OL, 3)
        else:
            d.ell(ex, hy - 12, 8, 9, (255, 255, 255), OL, 2); d.ell(ex, hy - 10, 4, 5, OL)
            d.line([(ex - 9, hy - 22), (ex + 9, hy - 24)], OL, 2)


# ================================================================ new oddities for the car-twin series
GX, GFY = 465, 1012                         # floor gap between the two characters (behind them)
def _eyes(d, x, y, s, look=0, blink=False, r=5):
    for side in (-1, 1):
        ex = x + side * 2.2 * r * s
        if blink: d.line([(ex - r * s, y), (ex + r * s, y)], OL, max(1.5, 2 * s))
        else: d.ell(ex, y, r * s, r * 1.1 * s, (255, 255, 255), OL, max(1, 1.5 * s)); d.ell(ex + look * r * .4 * s, y + .5 * s, r * .5 * s, r * .55 * s, OL)

def odd_shark(img, t, tau):
    """A shark fin cruising back and forth through the glossy floor."""
    d = D(img)
    x = GX + 70 * math.sin(tau * .9); v = math.cos(tau * .9); fy = GFY
    for i in range(3):                                                          # ripples
        r = ((tau * 40 + i * 30) % 90)
        d.ell(x - v * r * .6, fy, 30 + r, 7 + r * .16, None, (200, 220, 240, int(160 * (1 - r / 90))), 2)
    sgn = 1 if v >= 0 else -1
    pts = [(x - sgn * 40, fy), (x + sgn * 26, fy), (x + sgn * 8, fy - 46), (x - sgn * 10, fy - 92), (x - sgn * 16, fy - 50)]
    d.poly(spline(pts, 5), (88, 104, 124), OL, 3)
    d.poly(spline([(x - sgn * 22, fy - 4), (x + sgn * 14, fy - 4), (x - sgn * 4, fy - 40)], 4), (126, 142, 162))
    d.ell(x, fy + 2, 46, 8, (40, 60, 90, 120))

def odd_mime(img, t, tau):
    """A mime stuck in an invisible box, palms flat on the glass."""
    s = .34; x, fy = GX, GFY
    ph = tau * 2.2
    lp = (-80 + 18 * math.sin(ph), -150 + 60 * math.sin(ph * .7)); rp = (-80 + 18 * math.cos(ph), -40 + 60 * math.cos(ph * .7))
    st = mk(lp, rp, look=0, brows='worried', smile=-1); st['blink'] = (tau % 3) < .12
    npc(img, x, fy, s, MIME, st)
    d = D(img)
    hy = fy - 905 * s; top = fy - 800 * s
    for k in range(6):                                                          # striped shirt
        y = top + 14 * s + k * 52 * s
        d.rect(x - 100 * s, y, x + 100 * s, y + 22 * s, (246, 246, 246))
    d.chord(x - 6, hy - 22, 26, 13, 180, 360, (16, 16, 20)); d.ell(x + 16, hy - 34, 5, 5, (16, 16, 20))   # beret
    a = int(70 + 50 * math.sin(tau * 3))
    for gx_ in (x - 62, x + 62):                                                # the invisible glass catching the light
        d.line([(gx_, fy - 300), (gx_, fy - 40)], (220, 236, 255, a), 2)
    d.line([(x - 62, fy - 300), (x + 62, fy - 300)], (220, 236, 255, a), 2)

def odd_ufo(img, t, tau):
    """A small flying saucer beaming a traffic cone up off the end of the platform."""
    d = D(img)
    ux, uy = 808 + 14 * math.sin(tau * 1.3), 360 + 6 * math.sin(tau * 2.1)
    lift = clamp((tau - .6) / 6)
    d.poly([(ux - 22, uy + 10), (ux + 22, uy + 10), (ux + 70, PLAT_Y + 10), (ux - 70, PLAT_Y + 10)], (180, 255, 170, 70))
    cy = PLAT_Y - 10 - (PLAT_Y - uy - 50) * io(lift); rot = tau * 2
    w = 22 * abs(math.cos(rot)) + 8
    d.poly([(ux - w, cy), (ux + w, cy), (ux + 5, cy - 50), (ux - 5, cy - 50)], (250, 120, 30), OL, 2)
    d.rect(ux - w * .7, cy - 30, ux + w * .7, cy - 22, (250, 250, 250))
    d.rect(ux - 30, cy, ux + 30, cy + 7, (230, 100, 24), r=2, ol=OL, w=2)
    d.ell(ux, uy - 14, 30, 22, (170, 220, 250, 230), OL, 3)
    d.ell(ux, uy, 76, 18, (170, 176, 188), OL, 3); d.ell(ux, uy - 4, 60, 9, (210, 214, 224))
    for i in range(6):
        on = int(tau * 6 + i) % 2
        d.ell(ux - 55 + i * 22, uy + 6, 5, 4, (255, 230, 80) if on else (120, 110, 60))

def odd_pigeon(img, t, tau):
    """A pigeon in a hard hat pacing with a clipboard, inspecting the place."""
    d = D(img); s = 1.5
    x = GX + 46 * math.sin(tau * .7); dirn = 1 if math.cos(tau * .7) >= 0 else -1; fy = GFY
    step = math.sin(tau * 9); bob = abs(step) * 4
    for side in (-1, 1):
        d.line([(x + side * 8 * s, fy - 30 * s), (x + side * 8 * s + side * step * 6, fy)], (230, 120, 110), 3)
    d.ell(x, fy - 2, 26 * s, 4 * s, (0, 0, 0, 60))
    d.ell(x, fy - 46 * s - bob, 34 * s, 26 * s, (130, 138, 156), OL, 2)
    d.poly([(x - dirn * 28 * s, fy - 50 * s - bob), (x - dirn * 54 * s, fy - 40 * s - bob), (x - dirn * 30 * s, fy - 30 * s - bob)], (96, 102, 118), OL, 2)
    d.ell(x + dirn * 4 * s, fy - 50 * s - bob, 18 * s, 13 * s, (110, 116, 134))                                 # wing
    hx, hy = x + dirn * 26 * s + dirn * 6 * max(0, step), fy - 80 * s - bob
    d.ell(hx - dirn * 6 * s, hy + 12 * s, 14 * s, 12 * s, (112, 170, 150))                                          # neck sheen
    d.ell(hx, hy, 15 * s, 13 * s, (140, 146, 164), OL, 2)
    d.poly([(hx + dirn * 12 * s, hy), (hx + dirn * 26 * s, hy + 4 * s), (hx + dirn * 12 * s, hy + 6 * s)], (60, 56, 50))
    d.ell(hx + dirn * 5 * s, hy - 3 * s, 3 * s, 3 * s, (240, 140, 40)); d.ell(hx + dirn * 5.6 * s, hy - 3 * s, 1.4 * s, 1.4 * s, OL)
    d.chord(hx, hy - 8 * s, 17 * s, 13 * s, 180, 360, (250, 206, 30)); d.rect(hx - 20 * s, hy - 9 * s, hx + 20 * s, hy - 6 * s, (230, 180, 20))
    cx_ = x + dirn * 14 * s                                                                                         # clipboard under the wing
    d.rect(cx_ - 12 * s, fy - 66 * s - bob, cx_ + 12 * s, fy - 36 * s - bob, (196, 150, 96), r=2, ol=OL, w=2)
    d.rect(cx_ - 9 * s, fy - 62 * s - bob, cx_ + 9 * s, fy - 40 * s - bob, (250, 250, 248))

def odd_disco(img, t, tau):
    """A disco ball drops from the ceiling and one customer dances alone under it."""
    d = D(img)
    bx, by = 130, CEIL + 80 + 30 * oc(clamp(tau / .8))
    d.line([(bx, CEIL), (bx, by - 34)], (150, 150, 160), 2)
    d.ell(bx, by, 34, 34, (190, 196, 210), OL, 2)
    for i in range(-3, 4):
        for j in range(-3, 4):
            if i * i + j * j <= 10:
                c = 150 + int(90 * ((i + j + int(tau * 8)) % 3 == 0))
                d.rect(bx + i * 9 - 4, by + j * 9 - 4, bx + i * 9 + 4, by + j * 9 + 4, (c, c, min(255, c + 20)))
    for k in range(10):                                                       # light specks sweeping the wall
        a = tau * 1.4 + k * .63
        sx, sy = bx + 240 + 360 * ((k * .37 + tau * .05) % 1), 300 + 230 * math.sin(a)
        d.ell(sx, sy, 6, 6, (255, 255, 255, 150))
    ph = tau * 4
    up = (70, -290) if math.sin(ph) > 0 else (235, 70)
    st = mk((40, -230) if math.sin(ph) > 0 else 'hip', up, look=0, brows='up', smile=1); st['dy'] = -abs(math.sin(ph * 2)) * 14
    npc(img, GX + 10 * math.sin(ph / 2), GFY, .30, NPC2['dancer'], st)

def odd_goat(img, t, tau, x=520, fy=470):
    """A goat on the car roof, chewing a sales brochure."""
    if tau < .7: return
    d = D(img); s = 1.0
    drop = (1 - oc(clamp((tau - .7) / .35))) * 120
    fy -= drop
    chew = math.sin(tau * 10) * 2
    for lx in (-30, -18, 22, 34):
        d.line([(x + lx, fy - 40), (x + lx, fy)], (210, 206, 196), 7); d.ell(x + lx, fy, 5, 3, (60, 50, 40))
    d.ell(x, fy - 54, 48, 26, (238, 236, 228), OL, 3)
    d.ell(x + 10, fy - 50, 16, 12, (196, 190, 176))
    hx, hy = x - 50, fy - 84
    d.poly([(x - 30, fy - 70), (hx + 6, hy + 4), (hx + 14, hy + 22), (x - 26, fy - 50)], (238, 236, 228), OL, 3)
    d.ell(hx, hy, 18, 15, (238, 236, 228), OL, 3)
    d.poly([(hx - 6, hy - 10), (hx - 12, hy - 34), (hx + 2, hy - 14)], (150, 140, 120), OL, 2)
    d.poly([(hx + 6, hy - 10), (hx + 12, hy - 34), (hx + 14, hy - 10)], (150, 140, 120), OL, 2)
    d.ell(hx - 4, hy - 3, 3, 3, OL)
    d.poly([(hx - 10, hy + 12), (hx - 6, hy + 30), (hx + 2, hy + 14)], (200, 196, 186))           # beard
    d.rect(hx - 34, hy + 4 + chew, hx - 10, hy + 22 + chew, (250, 250, 250), r=2, ol=OL, w=2)   # brochure in its mouth
    d.rect(hx - 31, hy + 8 + chew, hx - 14, hy + 12 + chew, (220, 40, 50))

def odd_scuba(img, t, tau):
    """A customer in full scuba gear (mask, snorkel, flippers) reading a magazine in the waiting area."""
    s = .30; x, fy = GX, GFY
    st = mk((-96, 40), (-96, 40), look=0, brows='flat'); st['blink'] = (tau % 3.7) < .12
    npc(img, x, fy, s, NPC2['scuba'], st)
    d = D(img)
    hy = fy - 905 * s
    for side in (-1, 1):                                                        # flippers
        d.poly([(x + side * 12, fy - 6), (x + side * 46, fy + 4), (x + side * 52, fy - 4), (x + side * 26, fy - 14)], (250, 206, 30), OL, 2)
    d.rect(x - 26, hy - 10, x + 26, hy + 6, (60, 170, 220, 200), r=6, ol=(250, 206, 30), w=3)  # mask
    d.line([(x + 22, hy + 14), (x + 30, hy - 6), (x + 30, hy - 40)], (250, 120, 30), 4)          # snorkel
    d.rect(x - 34, fy - 280 * s * 2.6 - 6, x + 34, fy - 280 * s * 2.6 + 34, (230, 60, 90), r=3, ol=OL, w=2)
    d.rect(x - 28, fy - 280 * s * 2.6, x + 28, fy - 280 * s * 2.6 + 10, (250, 250, 250))
    flip = (tau % 4) < .3
    if flip: d.line([(x, fy - 280 * s * 2.6 - 6), (x + 20, fy - 280 * s * 2.6 - 16)], (250, 250, 250), 3)

def odd_plant(img, t, tau):
    """A potted plant tiptoeing out of the showroom on tiny legs."""
    d = D(img)
    x, fy = GX + 90 - 26 * tau, GFY
    st = math.sin(tau * 12)
    for side in (-1, 1):
        d.line([(x + side * 12, fy - 26), (x + side * 12 + side * st * 6, fy - 2)], OL, 4)
        d.ell(x + side * 12 + side * st * 6 + 4, fy - 1, 7, 3, OL)
    d.poly([(x - 30, fy - 90), (x + 30, fy - 90), (x + 22, fy - 26), (x - 22, fy - 26)], (196, 98, 60), OL, 3)
    d.rect(x - 34, fy - 98, x + 34, fy - 86, (176, 84, 50), r=3, ol=OL, w=2)
    sway = math.sin(tau * 6) * 4
    for a, ln in ((-60, 90), (-30, 120), (0, 130), (30, 116), (60, 86), (-80, 60), (80, 60)):
        r = math.radians(a - 90); ex, ey = x + math.cos(r) * ln * .8 + sway, fy - 96 + math.sin(r) * ln
        d.poly(spline([(x, fy - 96), (ex - 12, (fy - 96 + ey) / 2), (ex, ey), (ex + 12, (fy - 96 + ey) / 2)], 4), (60, 160, 70), (30, 90, 40), 2)
    _eyes(d, x, fy - 66, 1.0, look=-1, blink=(tau % 2.6) < .12)

def odd_balloon(img, t, tau):
    """A hot-air balloon drifting through the showroom, a cat looking over the basket."""
    d = D(img)
    x, y = 930 - 52 * tau, 300 + 10 * math.sin(tau * 1.2)
    cols = [(236, 60, 60), (250, 200, 40), (60, 140, 230), (250, 250, 250)]
    for i in range(6):
        u0, u1 = -1 + i / 3, -1 + (i + 1) / 3
        pts = [(x + 70 * math.sin(math.pi / 2 * v) * (1 - .15 * abs(math.sin(a))), y - 70 + 66 * math.cos(a))
               for v in (u0, u1) for a in ((0, .6, 1.2, 1.8, 2.4, 2.9) if v == u0 else (2.9, 2.4, 1.8, 1.2, .6, 0))]
        d.poly(pts, cols[i % 4])
    d.ell(x, y - 70, 70, 74, None, OL, 3)
    for side in (-1, 1): d.line([(x + side * 30, y), (x + side * 18, y + 40)], (120, 90, 60), 2)
    fl = 10 + 6 * abs(math.sin(tau * 13))
    d.poly([(x - 6, y + 38), (x + 6, y + 38), (x, y + 38 - fl)], (255, 170, 40))
    d.rect(x - 22, y + 40, x + 22, y + 70, (170, 120, 70), r=4, ol=OL, w=2)
    cx_ = x + 6 * math.sin(tau)
    d.ell(cx_, y + 36, 13, 11, (90, 90, 96), OL, 2)
    for side in (-1, 1): d.poly([(cx_ + side * 12, y + 30), (cx_ + side * 8, y + 18), (cx_ + side * 3, y + 28)], (90, 90, 96), OL, 2)
    d.ell(cx_ - 4, y + 34, 2, 2.5, (250, 220, 60)); d.ell(cx_ + 4, y + 34, 2, 2.5, (250, 220, 60))

def odd_cow(img, t, tau):
    """A cow jogging on a treadmill."""
    d = D(img); x, fy = GX, GFY
    d.rect(x - 96, fy - 22, x + 90, fy - 4, (40, 42, 48), r=6, ol=OL, w=2)
    belt = (tau * 160) % 24
    for k in range(9): d.line([(x - 90 + ((k * 24 - belt) % 180), fy - 20), (x - 90 + ((k * 24 - belt) % 180), fy - 6)], (80, 84, 92), 2)
    d.line([(x - 90, fy - 20), (x - 112, fy - 130)], (60, 62, 70), 6); d.rect(x - 134, fy - 150, x - 92, fy - 124, (60, 62, 70), r=4)
    d.rect(x - 130, fy - 146, x - 96, fy - 130, (60, 220, 120))
    ph = tau * 11; bob = abs(math.sin(ph)) * 4
    for i, lx in enumerate((-46, -30, 36, 52)):
        sw = math.sin(ph + (0 if i % 2 else math.pi)) * 12
        d.line([(x + lx, fy - 70 - bob), (x + lx + sw, fy - 24)], (240, 240, 236), 9); d.ell(x + lx + sw, fy - 24, 6, 4, (50, 44, 40))
    d.rect(x - 64, fy - 118 - bob, x + 70, fy - 62 - bob, (244, 244, 240), r=26, ol=OL, w=3)
    for sx, sy, r in ((-30, -100, 14), (20, -86, 18), (52, -104, 10)): d.ell(x + sx, fy + sy - bob, r, r * .8, (30, 30, 34))
    hx, hy = x - 82, fy - 124 - bob
    d.ell(hx, hy, 24, 22, (244, 244, 240), OL, 3); d.rect(hx - 30, hy + 4, hx + 4, hy + 26, (240, 180, 180), r=10, ol=OL, w=2)
    for side in (-1, 1): d.poly([(hx + side * 12, hy - 18), (hx + side * 20, hy - 36), (hx + side * 22, hy - 16)], (236, 220, 180), OL, 2)
    d.ell(hx - 6, hy - 4, 3, 3.5, OL)
    d.line([(x + 70, fy - 100 - bob), (x + 92, fy - 70 - bob + 8 * math.sin(ph))], (240, 240, 236), 4)
    d.rect(hx - 6, hy - 26, hx + 10, hy - 20, (60, 160, 240), r=2)                                           # sweatband

def odd_knight(img, t, tau):
    """A knight in full armour mopping the floor."""
    s = .30; ph = tau * 2.4; sw = math.sin(ph) * 40
    x, fy = GX, GFY
    st = mk((60 + sw * .4, 230), (-30 + sw * .4, 250), look=-1, brows='flat')
    npc(img, x, fy, s, NPC2['knight'], st)
    d = D(img); hy = fy - 905 * s
    d.rect(x - 24, hy - 30, x + 24, hy + 26, (180, 186, 196), r=12, ol=OL, w=3)                           # helmet over the head
    d.rect(x - 18, hy - 6, x + 18, hy, (30, 32, 40))
    d.poly([(x - 4, hy - 30), (x + 4, hy - 30), (x + 10, hy - 52), (x - 6, hy - 44)], (220, 40, 50))          # plume
    mx = x - 30 + sw
    d.line([(x - 12, fy - 160), (mx, fy - 10)], (150, 110, 70), 4)
    d.ell(mx, fy - 6, 22, 8, (236, 236, 226), OL, 2)
    d.ell(mx + 10, fy - 2, 40, 6, (150, 200, 240, 90))
    d.rect(x + 40, fy - 30, x + 76, fy, (240, 200, 40), r=4, ol=OL, w=2)                                # bucket

def odd_snailrace(img, t, tau):
    """A snail and a tortoise racing across the floor; the snail is winning."""
    d = D(img); fy = GFY
    fx = GX - 86
    d.line([(fx, fy), (fx, fy - 70)], (60, 60, 66), 3)
    for i in range(4):
        for j in range(3): d.rect(fx + i * 8, fy - 70 + j * 8, fx + i * 8 + 8, fy - 62 + j * 8, (0, 0, 0) if (i + j) % 2 else (255, 255, 255))
    sx = GX + 100 - 9 * tau; tx = GX + 150 - 7 * tau
    d.ell(tx, fy - 24, 40, 24, (110, 150, 80), OL, 3)
    for i in range(3): d.poly([(tx - 24 + i * 18, fy - 34), (tx - 14 + i * 18, fy - 44), (tx - 4 + i * 18, fy - 34)], (80, 120, 60))
    st = math.sin(tau * 3) * 3
    for lx in (-26, 22): d.ell(tx + lx + st, fy - 4, 9, 6, (150, 180, 110), OL, 2)
    d.ell(tx - 46, fy - 22, 14, 11, (150, 180, 110), OL, 2); d.ell(tx - 50, fy - 25, 2, 2, OL)
    d.poly(spline([(sx - 30, fy), (sx + 26, fy), (sx + 30, fy - 8), (sx - 26, fy - 8)], 3), (200, 200, 150), OL, 2)
    d.ell(sx + 6, fy - 26, 22, 22, (196, 130, 70), OL, 3); d.arc(sx + 6, fy - 26, 12, 12, 0, 300, (130, 80, 40), 3)
    for ax in (-26, -20): d.line([(sx + ax + 4, fy - 6), (sx + ax - 4, fy - 34)], (200, 200, 150), 3); d.ell(sx + ax - 4, fy - 36, 3, 3, OL)
    d.rect(sx - 8, fy - 48, sx + 20, fy - 40, (40, 120, 230), r=2)                                          # racing number band
    d.text(sx + 6, fy - 64, '1', 14, (250, 250, 250), stroke=2, sc=OL)

def odd_statue(img, t, tau):
    """A marble bust on a plinth whose eyes, then whole head, slowly turn to follow the buyer."""
    d = D(img); x, fy = GX, GFY
    d.rect(x - 40, fy - 150, x + 40, fy, (226, 222, 214), ol=OL, w=3); d.rect(x - 50, fy - 160, x + 50, fy - 146, (236, 232, 224), ol=OL, w=3)
    d.rect(x - 50, fy - 10, x + 50, fy, (210, 206, 198), ol=OL, w=2)
    turn = io(clamp((tau - 2.5) / .6)) * -1
    d.poly(spline([(x - 54, fy - 160), (x - 40, fy - 210), (x + 40, fy - 210), (x + 54, fy - 160)], 4), (238, 236, 230), OL, 3)
    hx, hy = x + 8 * turn, fy - 250
    d.rect(x - 12, fy - 222, x + 12, fy - 200, (230, 228, 222))
    d.ell(hx, hy, 30, 36, (240, 238, 232), OL, 3)
    for i in range(6): d.ell(hx - 24 + i * 9, hy - 34 + abs(i - 2.5) * 3, 8, 7, (230, 228, 220), OL, 1.5)    # curls
    look = -1 if tau > 1.2 else 0
    for side in (-1, 1):
        ex = hx + side * 11 + turn * 5
        d.ell(ex, hy - 2, 6, 5, (250, 250, 248), OL, 1.5); d.ell(ex + look * 2.5, hy - 1, 2.2, 2.2, (150, 150, 150))
    d.line([(hx + turn * 8, hy + 2), (hx + turn * 10 - 3, hy + 12)], (200, 196, 190), 2)
    d.line([(hx - 8 + turn * 6, hy + 20), (hx + 8 + turn * 6, hy + 20)], (180, 176, 170), 2)

def odd_octopus(img, t, tau):
    """An octopus polishing the end of the platform with four cloths."""
    d = D(img); x, fy = 66, PLAT_Y + 26
    P1, P2 = (190, 90, 190), (150, 60, 160)
    for i in range(6):
        a = math.radians(200 + i * 28); ln = 70
        wob = math.sin(tau * 6 + i) * 14
        pts = [(x, fy - 40), (x + math.cos(a) * ln * .5 + wob * .3, fy - 40 - math.sin(a) * ln * .3),
               (x + math.cos(a) * ln + wob, fy - 6 + abs(math.sin(a)) * 10)]
        pts = spline(pts, 5, closed=False)
        d.line(pts, OL, 14); d.line(pts, P1, 10)
        if i % 2 == 0:
            ex, ey = pts[-1]
            d.rect(ex - 12, ey - 7, ex + 12, ey + 7, [(250, 210, 60), (90, 200, 240), (250, 120, 120)][i // 2], r=4, ol=OL, w=2)
    d.ell(x, fy - 66, 36, 40, P1, OL, 3); d.ell(x - 10, fy - 80, 10, 12, (220, 140, 220))
    _eyes(d, x, fy - 56, 1.0, look=1, blink=(tau % 3.1) < .12)
    d.arc(x, fy - 44, 8, 5, 20, 160, P2, 3)

def odd_bear(img, t, tau):
    """A bear in a fluffy bathrobe and slippers, reading the newspaper."""
    s = .30; x, fy = GX, GFY
    st = mk((-96, 40), (-96, 40), look=0, brows='flat'); st['blink'] = (tau % 3.4) < .12
    npc(img, x, fy, s, NPC2['bear'], st)
    d = D(img); hy = fy - 905 * s
    for side in (-1, 1): d.ell(x + side * 20, hy - 22, 9, 9, (110, 70, 40), OL, 2); d.ell(x + side * 20, hy - 22, 4, 4, (190, 140, 110))
    d.ell(x, hy + 10, 12, 9, (190, 150, 110), OL, 2); d.ell(x, hy + 6, 5, 4, OL)
    py = fy - 280 * s * 2.6 + 6
    turn = math.sin(tau * .7) * 2
    d.rect(x - 40, py - 22, x + 40, py + 36, (240, 238, 228), r=2, ol=OL, w=2)
    for k in range(5): d.line([(x - 34, py - 12 + k * 9), (x + 34 - (k % 2) * 20, py - 12 + k * 9)], (150, 150, 150), 2)
    d.text(x, py - 16 + turn, 'NEWS', 11, (30, 30, 30))
    for side in (-1, 1): d.ell(x + side * 16, fy - 6, 18, 8, (250, 180, 200), OL, 2)

def odd_vending(img, t, tau):
    """A vending machine that dispenses a live chicken, which walks off."""
    d = D(img); x, fy = GX, GFY
    d.rect(x - 64, fy - 250, x + 64, fy, (196, 30, 40), r=8, ol=OL, w=3)
    d.rect(x - 52, fy - 236, x + 22, fy - 90, (190, 220, 236), r=4, ol=OL, w=2)
    for r in range(4):
        for c in range(3):
            d.rect(x - 46 + c * 22, fy - 228 + r * 34, x - 32 + c * 22, fy - 206 + r * 34, [(250, 200, 40), (90, 200, 120), (250, 250, 250)][(r + c) % 3], r=2)
    d.rect(x + 30, fy - 230, x + 56, fy - 160, (30, 30, 34), r=3)
    for k in range(3): d.ell(x + 43, fy - 214 + k * 18, 5, 5, (220, 220, 220) if int(tau * 4 + k) % 3 else (60, 230, 120))
    d.rect(x - 52, fy - 70, x + 52, fy - 30, (20, 20, 24), r=4)
    ck = clamp((tau - 1.5) / 4)
    if tau > 1.5:
        cxp = x + 4 - 30 * ck * 4 if ck < .25 else x - 30 - 60 * (ck - .25)
        cyp = fy - 34 if ck < .2 else fy + 2
        _chicken(d, cxp, cyp, tau)

def _chicken(d, x, fy, tau):
    st = math.sin(tau * 10)
    for side in (-1, 1): d.line([(x + side * 6, fy - 16), (x + side * 6 + side * st * 4, fy)], (240, 160, 40), 3)
    d.ell(x, fy - 28, 22, 16, (252, 252, 250), OL, 2)
    d.ell(x - 18, fy - 46, 11, 11, (252, 252, 250), OL, 2)
    d.poly([(x - 22, fy - 58), (x - 18, fy - 66), (x - 14, fy - 58)], (230, 40, 40))
    d.poly([(x - 28, fy - 46), (x - 38, fy - 43), (x - 28, fy - 40)], (250, 180, 40)); d.ell(x - 21, fy - 48, 2, 2, OL)
    d.poly([(x + 18, fy - 34), (x + 30, fy - 46), (x + 22, fy - 26)], (240, 240, 236), OL, 2)

def odd_banana(img, t, tau):
    """Someone in a full banana costume, sipping a coffee."""
    d = D(img); x, fy = GX, GFY
    sw = math.sin(tau * 1.4) * 4
    for side in (-1, 1): d.line([(x + side * 14, fy - 60), (x + side * 16, fy)], (40, 40, 60), 9); d.ell(x + side * 18, fy - 2, 13, 6, (240, 240, 240), OL, 2)
    body = spline([(x - 50 + sw, fy - 290), (x - 70, fy - 180), (x - 46, fy - 70), (x, fy - 50), (x + 44, fy - 72),
                   (x + 40, fy - 180), (x + 4 + sw, fy - 292)], 6)
    d.poly(body, (252, 222, 60), OL, 3)
    d.line(spline([(x - 30 + sw, fy - 270), (x - 40, fy - 170), (x - 20, fy - 90)], 5, closed=False), (230, 180, 30), 4)
    d.poly([(x - 30 + sw, fy - 288), (x - 14 + sw, fy - 314), (x - 2 + sw, fy - 290)], (110, 80, 40), OL, 2)
    fx, fyc = x - 6 + sw * .5, fy - 210
    d.ell(fx, fyc, 22, 26, (226, 170, 130), OL, 2)
    _eyes(d, fx, fyc - 4, .9, look=-1, blink=(tau % 3.3) < .12)
    sip = max(0.0, math.sin(tau * 1.1 - 1)) ** 6
    hx, hy = x + 40, fy - 150 - 50 * sip
    d.line([(x + 30, fy - 140), (hx, hy)], (252, 222, 60), 10)
    d.rect(hx - 9, hy - 22, hx + 9, hy, (250, 250, 248), r=3, ol=OL, w=2); d.rect(hx - 9, hy - 14, hx + 9, hy - 8, (150, 96, 56))

def odd_horse(img, t, tau):
    """A horse in reading glasses at a desk, typing furiously with its hooves."""
    d = D(img); x, fy = GX, GFY
    d.rect(x - 90, fy - 100, x + 90, fy - 88, (150, 110, 74), ol=OL, w=2)
    for lx in (-80, 72): d.rect(x + lx, fy - 88, x + lx + 8, fy, (110, 80, 52))
    ty = math.sin(tau * 18)
    B, B2 = (150, 96, 56), (120, 74, 40)
    d.poly([(x - 30, fy - 100), (x - 40, fy - 190), (x + 36, fy - 190), (x + 30, fy - 100)], B, OL, 3)
    hx, hy = x - 8, fy - 236
    d.poly([(x - 20, fy - 180), (hx - 14, hy + 10), (hx + 16, hy + 6), (x + 22, fy - 186)], B, OL, 3)
    d.poly(spline([(hx - 26, hy - 34), (hx + 20, hy - 30), (hx + 18, hy + 30), (hx - 10, hy + 60), (hx - 34, hy + 50)], 4), B, OL, 3)
    d.ell(hx - 24, hy + 50, 16, 12, B2)
    d.ell(hx - 30, hy + 50, 3, 3, OL)
    for side in (-1, 1): d.poly([(hx + side * 10 - 4, hy - 30), (hx + side * 10, hy - 54), (hx + side * 10 + 6, hy - 30)], B, OL, 2)
    d.poly([(hx - 8, hy - 36), (hx + 20, hy - 30), (hx + 22, hy + 10), (hx + 10, hy - 20)], (50, 30, 20))
    d.ell(hx - 12, hy - 4, 10, 8, None, (40, 40, 44), 2); d.ell(hx + 8, hy - 4, 10, 8, None, (40, 40, 44), 2)
    d.ell(hx - 12, hy - 4, 3, 3, OL); d.ell(hx + 8, hy - 4, 3, 3, OL)
    d.rect(x - 50, fy - 112, x + 30, fy - 100, (60, 62, 70), r=2)                                             # laptop
    d.poly([(x - 46, fy - 112), (x + 26, fy - 112), (x + 34, fy - 170), (x - 38, fy - 170)], (80, 84, 94), OL, 2)
    d.poly([(x - 40, fy - 116), (x + 22, fy - 116), (x + 28, fy - 164), (x - 34, fy - 164)], (120, 200, 250))
    for side, ph in ((-1, 0), (1, math.pi)):
        up = max(0, math.sin(tau * 18 + ph)) * 12
        d.line([(x + side * 30, fy - 160), (x + side * 22, fy - 116 - up)], B, 12); d.rect(x + side * 22 - 8, fy - 118 - up, x + side * 22 + 8, fy - 108 - up, (40, 30, 24), r=2)

def odd_cactus(img, t, tau):
    """A cactus in sunglasses cruising across the floor on a skateboard."""
    d = D(img); x, fy = GX + 110 - 34 * tau, GFY
    d.rect(x - 40, fy - 16, x + 40, fy - 8, (220, 70, 40), r=4, ol=OL, w=2)
    for wx in (x - 26, x + 26): d.ell(wx, fy - 4, 6, 6, (250, 250, 250), OL, 2)
    d.poly([(x - 22, fy - 16), (x + 22, fy - 16), (x + 26, fy - 56), (x - 26, fy - 56)], (196, 98, 60), OL, 2)
    G = (80, 170, 80)
    d.rect(x - 18, fy - 160, x + 18, fy - 52, G, r=18, ol=OL, w=3)
    d.line([(x - 18, fy - 100), (x - 40, fy - 100), (x - 40, fy - 136)], OL, 18); d.line([(x - 18, fy - 100), (x - 40, fy - 100), (x - 40, fy - 136)], G, 12)
    d.line([(x + 18, fy - 86), (x + 38, fy - 86), (x + 38, fy - 112)], OL, 18); d.line([(x + 18, fy - 86), (x + 38, fy - 86), (x + 38, fy - 112)], G, 12)
    for k in range(5): d.line([(x - 10 + k * 5, fy - 150 + k * 18), (x - 6 + k * 5, fy - 146 + k * 18)], (230, 250, 210), 2)
    d.rect(x - 20, fy - 140, x + 20, fy - 128, (16, 16, 20), r=4); d.ell(x - 10, fy - 134, 9, 7, (16, 16, 20)); d.ell(x + 10, fy - 134, 9, 7, (16, 16, 20))
    d.arc(x, fy - 118, 7, 5, 20, 160, OL, 2)
    d.ell(x + 2, fy - 168, 8, 6, (250, 110, 160))

def odd_fishwalk(img, t, tau):
    """A customer walking a goldfish bowl on wheels on a leash."""
    x = GX + 120 - 40 * tau; fy = GFY
    st = walkst(tau, 8, lp='rest', rp=(60, 210), look=-1)
    npc(img, x, fy, .30, NPC2['walker2'], st)
    d = D(img)
    bx = x - 80
    d.line([(x - 18, fy - 190), (bx + 10, fy - 70)], (220, 40, 60), 2)
    d.rect(bx - 30, fy - 24, bx + 30, fy - 14, (90, 90, 100), r=3); 
    for wx in (bx - 20, bx + 20): d.ell(wx, fy - 8, 7, 7, (30, 30, 34), OL, 2)
    d.ell(bx, fy - 58, 36, 36, (190, 230, 250, 170), OL, 2); d.rect(bx - 24, fy - 98, bx + 24, fy - 90, (190, 230, 250, 200))
    d.ell(bx, fy - 50, 30, 18, (90, 170, 230, 160))
    fx = bx + 10 * math.sin(tau * 2)
    d.ell(fx, fy - 54, 12, 8, (250, 140, 30), OL, 2); d.poly([(fx + 10, fy - 54), (fx + 20, fy - 62), (fx + 20, fy - 46)], (250, 140, 30), OL, 2)
    d.ell(fx - 5, fy - 56, 1.8, 1.8, OL)

def odd_ghost(img, t, tau):
    """A bedsheet ghost peeking out from behind the end of the platform, then hiding again."""
    d = D(img)
    k = clamp(math.sin(tau * .8) * 1.6)
    x, y = 905 - 50 * k, 640 + 8 * math.sin(tau * 2)
    hem = [(x - 46 + i * 15, y + 70 + (8 if i % 2 else 0) + 4 * math.sin(tau * 5 + i)) for i in range(7)]
    d.poly(spline([(x - 46, y + 70), (x - 48, y - 10), (x, y - 60), (x + 48, y - 10), (x + 48, y + 70)], 5, closed=False) + hem[::-1],
           (248, 248, 252, 230), OL, 3)
    d.ell(x - 14, y - 12, 8, 11, (20, 20, 26)); d.ell(x + 12, y - 12, 8, 11, (20, 20, 26))
    d.ell(x - 1, y + 12, 7, 9, (20, 20, 26))

MIME = cast('f6f4f0', '1a1a1e', '16161a', pants='16161a', shirt='f6f6f6')
NPC2 = dict(dancer=cast('a86a48', '1a1a1a', 'd040a0', pants='202030', shirt='f4e04a'),
            scuba=cast('e0b090', '2a1d16', '15161c', pants='15161c', shirt='15161c'),
            knight=cast('e0b090', '603018', 'a8aeb8', pants='8a909c', shoe='70767f', shirt='c8ccd4'),
            bear=cast('8a5a34', '6a4224', 'f2a8c4', pants='f2a8c4', shirt='f2a8c4', shoe='f2a8c4'),
            walker2=cast('f2d0b0', 'b04a2a', '2f8a6a', pants='2a2a30', style='messy'))

def _wrap(fn, **kw):
    return lambda img, t, tau: fn(D(img), kw.get('x', GX), kw.get('fy', GFY), tau, kw.get('s', 1.0))
def _flamingo_vac(img, t, tau):
    d = D(img); x = GX + 60 * math.sin(tau * .6)
    d.ell(x, GFY - 8, 46, 14, (40, 42, 48), OL, 3); d.ell(x, GFY - 14, 40, 10, (70, 74, 82)); d.ell(x + 14, GFY - 16, 4, 3, (80, 230, 120))
    flamingo(d, x, GFY - 20, tau, .9)
def _ducks(img, t, tau): ducks(D(img), t, tau, x0=GX + 40, fy0=GFY)
def _sheep(img, t, tau): sheep(D(img), GX, GFY, tau, .8)

ODD = dict(shark=odd_shark, mime=odd_mime, ufo=odd_ufo, pigeon=odd_pigeon, disco=odd_disco, goat=odd_goat, scuba=odd_scuba,
           plant=odd_plant, balloon=odd_balloon, cow=odd_cow, knight=odd_knight, snailrace=odd_snailrace, statue=odd_statue,
           octopus=odd_octopus, bear=odd_bear, vending=odd_vending, banana=odd_banana, horse=odd_horse, cactus=odd_cactus,
           fishwalk=odd_fishwalk, ghost=odd_ghost,
           snowman=_wrap(snowman, s=.85), flamingo=_flamingo_vac, sheep=_sheep, llama=_wrap(llama, s=.95),
           ducks=_ducks, penguin=_wrap(penguin, s=1.1), dino=_wrap(dino, s=.75),
           giraffe=lambda img, t, tau: giraffe(img, tau), astronaut=lambda img, t, tau: astronaut(img, t, tau))
