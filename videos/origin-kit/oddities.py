"""Background oddities (never mentioned). Each draws at scale 1 around (x, fy); the engine passes a scaled D.
snowman, flamingo, sheep, llama: bmw-heated-seats; penguin, dino: platform-ladder; cat: supra-z4 (copied unchanged).
New here: giraffe, astronaut, ufo, cow_balloon, octopus, bear, pigeon."""
import math
from common import D, OL, spline, clamp, mix

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

def cat(d, x, y, t, push=0.0, col=(236, 150, 60), s=1.0):
    """Sitting ginger cat facing left; push 0..1 reaches its paw out to the left."""
    tail = math.sin(t * 3) * 14 * s
    tl = spline([(x + 30 * s, y - 10 * s), (x + 62 * s, y - 30 * s), (x + 66 * s + tail, y - 72 * s)], 5, closed=False)
    d.line(tl, OL, 14 * s); d.line(tl, col, 8 * s)
    d.ell(x + 10 * s, y - 34 * s, 36 * s, 34 * s, col, OL, 3.5)
    paw = 50 * push * s
    d.line([(x - 6 * s, y - 30 * s), (x - 20 * s - paw, y - 10 * s - 8 * push * s)], OL, 17 * s)
    d.line([(x - 6 * s, y - 30 * s), (x - 20 * s - paw, y - 10 * s - 8 * push * s)], col, 10 * s)
    hx, hy = x - 14 * s, y - 78 * s
    for sd in (-1, 1):
        d.poly([(hx + sd * 10 * s, hy - 16 * s), (hx + sd * 24 * s, hy - 36 * s), (hx + sd * 26 * s, hy - 8 * s)], col, OL, 3)
    d.ell(hx, hy, 28 * s, 24 * s, col, OL, 3.5)
    for sd in (-1, 1):
        if push > .5: d.line([(hx - 6 * s + sd * 11 * s - 5 * s, hy - 2 * s), (hx - 6 * s + sd * 11 * s + 5 * s, hy - 2 * s)], OL, 3)
        else: d.ell(hx - 6 * s + sd * 11 * s, hy - 2 * s, 4 * s, 6 * s, OL)
    d.ell(hx - 7 * s, hy + 8 * s, 4 * s, 3 * s, (230, 120, 130))
    for k in (-1, 1):
        d.line([(hx - 22 * s, hy + 6 * s), (hx - 42 * s, hy + 6 * s + k * 5 * s)], OL, 1.6)
    for i in range(3):
        d.line([(x - 4 * s + 14 * i * s, y - 52 * s), (x + 2 * s + 14 * i * s, y - 30 * s)], (196, 112, 40), 4 * s)

# ---------------------------------------------------------------- new oddities
def _eye(d, x, y, r, t, ph=0.0):
    if ((t + ph) % 3.2) < .12: d.line([(x - r, y), (x + r, y)], OL, 3)
    else: d.ell(x, y, r, r * 1.1, (255, 255, 255), OL, 2); d.ell(x + r * .25, y + r * .15, r * .5, r * .55, OL)

def giraffe(d, x, fy, t, s=1.0):
    """Giraffe outside the window, neck rising from below the sill, chewing and staring in."""
    YL, YD = (240, 196, 88), (168, 104, 44)
    lean = math.sin(t * .9) * 12
    neck = [(x - 10, fy + 20), (x - 4 + lean * .4, fy - 90), (x + lean, fy - 170)]
    d.line(neck, OL, 56); d.line(neck, YL, 46)
    for px, py in ((x - 14, fy - 20), (x + 6, fy - 70), (x - 4 + lean * .7, fy - 128)):
        d.poly(spline([(px - 11, py - 9), (px + 9, py - 11), (px + 13, py + 7), (px - 7, py + 11)], 3), YD)
    hx, hy = x + lean, fy - 200
    chew = math.sin(t * 9) * 3
    for sd in (-1, 1):
        d.line([(hx + sd * 16, hy - 30), (hx + sd * 20, hy - 62)], OL, 9); d.line([(hx + sd * 16, hy - 30), (hx + sd * 20, hy - 62)], YD, 6)
        d.ell(hx + sd * 20, hy - 64, 7, 7, (90, 58, 30), OL, 2)
        d.poly([(hx + sd * 30, hy - 26), (hx + sd * 60, hy - 36), (hx + sd * 34, hy - 14)], YL, OL, 3)
    d.ell(hx, hy - 6, 36, 38, YL, OL, 4)
    d.rect(hx - 26, hy + 8, hx + 26, hy + 56 + chew, (228, 182, 122), r=22, ol=OL, w=4)
    d.ell(hx - 10, hy + 36, 4, 3, OL); d.ell(hx + 10, hy + 36, 4, 3, OL)
    d.line([(hx + 12, hy + 52 + chew), (hx + 40, hy + 64 + chew)], (90, 170, 70), 4)          # a leaf sticking out
    for sd in (-1, 1): _eye(d, hx + sd * 15, hy - 10, 8, t)

def astronaut(d, x, fy, t, s=1.0):
    """Astronaut drifting past outside, waving slowly."""
    x += math.sin(t * .35) * 40; y = fy - 170 + math.sin(t * 1.1) * 14
    SU, SU2 = (244, 244, 246), (190, 194, 204)
    d.rect(x - 46, y - 20, x + 46, y + 64, (210, 212, 220), r=12, ol=OL, w=3)
    wave = math.sin(t * 3) * 18
    for sd in (-1, 1):
        d.line([(x + sd * 20, y + 60), (x + sd * 34, y + 96), (x + sd * 28, y + 106)], OL, 30)
        d.line([(x + sd * 20, y + 60), (x + sd * 34, y + 96), (x + sd * 28, y + 106)], SU, 22)
        d.ell(x + sd * 30, y + 110, 16, 10, SU2, OL, 3)
        ey = y + (26 if sd < 0 else -40 - wave)
        d.line([(x + sd * 34, y), (x + sd * 66, ey), (x + sd * 80, ey - 22)], OL, 26)
        d.line([(x + sd * 34, y), (x + sd * 66, ey), (x + sd * 80, ey - 22)], SU, 18)
        d.ell(x + sd * 82, ey - 24, 11, 11, SU2, OL, 3)
    d.rect(x - 38, y - 16, x + 38, y + 70, SU, r=18, ol=OL, w=3)
    d.rect(x - 18, y + 6, x + 18, y + 30, (90, 120, 200), r=4)
    d.ell(x - 8, y + 18, 3, 3, (240, 80, 70)); d.ell(x + 4, y + 18, 3, 3, (90, 220, 120))
    d.ell(x, y - 48, 40, 38, SU, OL, 3)
    d.ell(x + 4, y - 48, 28, 22, (40, 44, 62)); d.ell(x + 12, y - 56, 10, 6, (255, 220, 150, 170))

def _cow(d, x, y, t, s=1.0, legs_dangle=False):
    W_, B_ = (250, 250, 248), (30, 30, 34)
    sw = math.sin(t * 2.4) * 6 if legs_dangle else 0
    for lx in (-30, -12, 16, 32):
        d.line([(x + lx * s, y + 18 * s), (x + lx * s + sw * s * (1 if lx > 0 else -1), y + 52 * s)], OL, 11 * s)
        d.line([(x + lx * s, y + 18 * s), (x + lx * s + sw * s * (1 if lx > 0 else -1), y + 52 * s)], W_, 7 * s)
    d.ell(x, y, 50 * s, 30 * s, W_, OL, 3)
    d.ell(x - 14 * s, y - 8 * s, 14 * s, 10 * s, B_); d.ell(x + 22 * s, y + 6 * s, 12 * s, 9 * s, B_)
    hx, hy = x - 50 * s, y - 18 * s
    for sd in (-1, 1): d.ell(hx + sd * 20 * s, hy - 16 * s, 10 * s, 5 * s, W_, OL, 2)
    d.ell(hx, hy, 20 * s, 22 * s, W_, OL, 2)
    d.ell(hx - 4 * s, hy + 14 * s, 15 * s, 10 * s, (244, 170, 180), OL, 2)
    for sd in (-1, 1): d.ell(hx - 4 * s + sd * 6 * s, hy + 14 * s, 2.5 * s, 2.5 * s, OL)
    for sd in (-1, 1): d.ell(hx + sd * 8 * s, hy - 6 * s, 3.5 * s, 4 * s, OL)
    d.line([(x + 48 * s, y - 4 * s), (x + 64 * s, y + 16 * s + sw * s)], OL, 3)

def ufo(d, x, fy, t, s=1.0):
    """Flying saucer beaming a calm cow up and down outside the window."""
    hx, hy = x + math.sin(t * .8) * 18, fy - 240 + math.sin(t * 1.7) * 6
    lift = (math.sin(t * .9) * .5 + .5)
    d.poly([(hx - 30, hy + 8), (hx + 30, hy + 8), (hx + 70, fy), (hx - 70, fy)], (190, 255, 170, 90))
    _cow(d, hx + 4, fy - 30 - 110 * lift, t, .62, legs_dangle=True)
    d.ell(hx, hy - 14, 34, 28, (170, 230, 255), OL, 3)
    d.ell(hx + 8, hy - 22, 9, 6, (255, 255, 255, 200))
    d.ell(hx, hy + 4, 86, 22, (150, 156, 170), OL, 4)
    d.ell(hx, hy - 2, 70, 12, (196, 200, 210))
    for i in range(5):
        on = int(t * 6 + i) % 2
        d.ell(hx - 56 + i * 28, hy + 8, 6, 5, (255, 220, 60) if on else (120, 110, 60))

def cow_balloon(d, x, fy, t, s=1.0):
    """A cow floating past under a bunch of party balloons."""
    y = fy - 120 + math.sin(t * .9) * 22
    cx = x + math.sin(t * .5) * 20
    cols = [(240, 60, 70), (60, 170, 240), (250, 210, 60), (120, 210, 110), (200, 110, 220)]
    for i, (bx, by) in enumerate(((-38, -150), (0, -172), (36, -150), (-16, -122), (20, -118))):
        px, py = cx + bx + math.sin(t * 1.3 + i) * 4, y + by
        d.line([(cx + 4, y - 26), (px, py + 26)], (60, 60, 70), 2)
        d.ell(px, py, 22, 27, cols[i], OL, 3); d.ell(px - 7, py - 9, 5, 7, (255, 255, 255, 170))
    _cow(d, cx, y, t, .9, legs_dangle=True)

def octopus(d, x, fy, t, s=1.0):
    """Purple octopus stuck to the outside of the glass, squeegeeing it clean."""
    P, P2 = (170, 90, 210), (130, 60, 170)
    cy = fy - 160
    for i in range(8):
        a = math.pi * (0.1 + 0.8 * i / 7)
        wig = math.sin(t * 2.6 + i) * 10
        pts = [(x + math.cos(a) * 30, cy + 30), (x + math.cos(a) * 70 + wig, cy + 60 + math.sin(a) * 30),
               (x + math.cos(a) * 96 - wig, cy + 100 + math.sin(a) * 20)]
        pts = spline(pts, 5, closed=False)
        d.line(pts, OL, 22); d.line(pts, P, 15)
    for sd in (-1, 1):                                                   # two arms with squeegees
        sx_ = x + sd * (70 + 26 * math.sin(t * 3.4 + (0 if sd < 0 else 1.6)))
        sy_ = cy - 40 + 30 * math.cos(t * 3.4 + (0 if sd < 0 else 1.6))
        arm = spline([(x + sd * 30, cy), (x + sd * 60, cy - 10), (sx_, sy_)], 5, closed=False)
        d.line(arm, OL, 20); d.line(arm, P, 13)
        d.line([(sx_, sy_), (sx_ + sd * 6, sy_ - 30)], (60, 60, 70), 5)
        d.rect(sx_ + sd * 6 - 26, sy_ - 40, sx_ + sd * 6 + 26, sy_ - 30, (40, 140, 240), r=3, ol=OL, w=2)
        for k in range(3):                                               # suds trail
            d.ell(sx_ - sd * (20 + k * 16), sy_ - 20 + k * 6, 9 - k * 2, 8 - k * 2, (255, 255, 255, 200))
    d.ell(x, cy - 20, 62, 66, P, OL, 4)
    d.ell(x - 18, cy - 46, 14, 10, (210, 150, 240))
    for sd in (-1, 1): _eye(d, x + sd * 22, cy - 6, 12, t, .7)
    d.arc(x, cy + 18, 12, 8, 20, 160, OL, 3)

def bear(d, x, fy, t, s=1.0):
    """Brown bear in a tiny party hat riding a unicycle back and forth outside."""
    B, B2 = (150, 96, 56), (110, 68, 38)
    x += math.sin(t * .7) * 46; wob = math.sin(t * 4.1) * 6
    wy = fy - 40
    ang = t * 6 * (1 if math.cos(t * .7) > 0 else -1)
    d.ell(x, wy, 38, 38, (40, 40, 46), OL, 4); d.ell(x, wy, 22, 22, (200, 204, 212), OL, 2)
    for k in range(4):
        a = ang + k * math.pi / 4
        d.line([(x - math.cos(a) * 22, wy - math.sin(a) * 22), (x + math.cos(a) * 22, wy + math.sin(a) * 22)], (90, 92, 100), 2)
    d.line([(x, wy), (x + wob * .3, wy - 90)], (90, 92, 100), 6)
    for sd in (-1, 1):                                                   # legs pedalling
        ph = ang + (0 if sd < 0 else math.pi)
        fx, fy2 = x + math.cos(ph) * 18, wy + math.sin(ph) * 18
        d.line([(x + sd * 14 + wob * .3, wy - 90), (fx + sd * 6, fy2 - 20), (fx, fy2)], OL, 22)
        d.line([(x + sd * 14 + wob * .3, wy - 90), (fx + sd * 6, fy2 - 20), (fx, fy2)], B, 15)
    bx, by = x + wob * .5, wy - 140
    d.ell(bx, by, 46, 56, B, OL, 4); d.ell(bx, by + 10, 28, 34, (206, 160, 112))
    for sd in (-1, 1):                                                   # arms out for balance
        arm = [(bx + sd * 36, by - 24), (bx + sd * 76, by - 40 + sd * wob), (bx + sd * 98, by - 30 + sd * wob)]
        d.line(arm, OL, 22); d.line(arm, B, 15)
    hx, hy = bx, by - 74
    for sd in (-1, 1): d.ell(hx + sd * 28, hy - 26, 13, 13, B, OL, 3)
    d.ell(hx, hy, 40, 36, B, OL, 4)
    d.ell(hx, hy + 14, 18, 13, (206, 160, 112)); d.ell(hx, hy + 8, 7, 5, OL)
    for sd in (-1, 1): _eye(d, hx + sd * 15, hy - 8, 6, t, .3)
    d.poly([(hx - 16, hy - 32), (hx + 14, hy - 34), (hx - 4, hy - 78)], (250, 80, 140), OL, 3)
    d.ell(hx - 4, hy - 80, 6, 6, (255, 230, 80), OL, 2)

def pigeon(d, x, fy, t, s=1.0):
    """Pigeon in a tiny necktie on the sill, reading a newspaper and turning the page."""
    G, G2 = (150, 156, 176), (110, 116, 138)
    bob = abs(math.sin(t * 2.2)) * 4
    for sd in (-1, 1): d.line([(x + sd * 10, fy - 30), (x + sd * 12, fy)], (226, 120, 120), 4)
    d.ell(x + 6, fy - 54 - bob * .3, 40, 34, G, OL, 3)
    d.poly([(x + 36, fy - 60), (x + 74, fy - 40), (x + 34, fy - 36)], G2, OL, 3)
    hx, hy = x - 20, fy - 104 - bob
    d.ell(hx + 6, hy + 26, 24, 20, (120, 170, 150))                      # iridescent neck
    d.ell(hx, hy, 24, 22, G, OL, 3)
    d.poly([(hx - 20, hy + 2), (hx - 38, hy + 8), (hx - 20, hy + 12)], (70, 64, 60), OL, 2)
    _eye(d, hx - 6, hy - 4, 6, t, 1.1)
    d.poly([(hx + 2, hy + 30), (hx + 12, hy + 30), (hx + 10, hy + 66), (hx + 7, hy + 72), (hx + 4, hy + 66)], (210, 30, 40), OL, 2)
    flip = (t % 4.0) / 4.0                                               # newspaper with a page turn
    px, py = x - 64, fy - 74
    d.rect(px - 46, py - 40, px + 6, py + 34, (240, 238, 228), ol=OL, w=2)
    d.rect(px - 40, py - 32, px, py - 22, (40, 40, 44))
    for k in range(5): d.line([(px - 40, py - 12 + k * 8), (px - 2, py - 12 + k * 8)], (150, 150, 150), 2)
    if flip > .85:
        k = (flip - .85) / .15
        d.poly([(px + 6, py - 40), (px + 6 - 52 * k, py - 40), (px + 6 - 52 * k, py + 34), (px + 6, py + 34)], (255, 252, 240), OL, 2)
