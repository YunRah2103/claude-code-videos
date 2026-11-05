"""Renders 'car stuff, explained': why thieves steal catalytic converters (loops).

Shots (timed to words.json, faster-whisper on out/catalytic-theft/voiceover.wav):
  1 street  0.00  night street, car under a lamp; a blurred pixel silhouette is already sawing at the exhaust on frame 0,
                  sparks flying, a stopwatch whirring; headline 'THIEVES target this in MINUTES'
  2 exhaust ~3.4  exhaust cutaway: dirty fumes in, the converter glows, clean air out -> CLEANS THE FUMES
  3 metals  ~6.3  the converter cracks open; PLATINUM, PALLADIUM, RHODIUM tiles fly out and glint on their words
  4 target  ~11.0 back on the street: a red reticle locks onto the converter under the car ('a target')
  5 ask     ~12.7 dashboard (A/C on): presenter asks, poll 'Do you know where yours is? YES / NO'; loops to shot 1
    python render.py still <dir> t... | safecheck | safestill <dir> t... | cover <png> | video <vo.wav> <out.mp4> [t0 t1]
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared', 'assets'))
import episode as kit
from episode import W, H, RED, YEL, WHITE
from backdrops.garage import Garage
from pixanim.motion import prog, lerp, io, oc, ob
from pixanim.presenter import Presenter, Fn
from pixanim.dash import Dashboard
from pixanim.street import Street
from pixanim.car import car, EXHAUST
from pixanim.props import stopwatch
from pixanim.grid import up
from pixanim import fx
from assets import overlays as ov, carbits as cb, seriesbits as sb
import dashep as D

WORDS = kit.load_words(HERE)
def ws(i): return WORDS[i]['s']

DUR = 14.22
END_T = 13.82                                                      # last word ends 13.74
T2 = ws(8) - 0.15                                                  # "It's the part of your exhaust that cleans the fumes"
EXH, CLEAN = ws(13), ws(15)
T3 = ws(18) - 0.15                                                 # 'Inside are precious metals like platinum, palladium and rhodium'
INSIDE, PREC = ws(18), ws(20)
MET = (ws(23), ws(24), ws(26))                                     # platinum, palladium, rhodium
T4 = ws(27) - 0.15                                                 # "That's why it's a target"
TGT = ws(31)
T5 = ws(32) - 0.15                                                 # 'Do you know where yours is?'
G = Garage(W, H, 1520, 9)
DASH = Dashboard(outside=Garage(W, H, 1180, 9).base())
ST = Street()
HOOK = ((('THIEVES target this', None),), (('in', None), ('MINUTES', '#e8343f')))
KEYCOL = {'thieves': RED, 'minutes.': RED, 'exhaust': YEL, 'cleans': YEL, 'fumes.': YEL, 'precious': YEL, 'platinum,': YEL,
          'palladium': YEL, 'rhodium.': YEL, 'target.': RED, 'yours': YEL}


# ------------------------------------------------------------------ the street: car parked under a lamp
CS, CX, CB = 9, 640, 1190                                          # car scale, centre x, bottom y
CAR_TOP = CB - 50 * CS
EX = (CX - 45 * CS + EXHAUST[0] * CS, CAR_TOP + EXHAUST[1] * CS)   # exhaust tip on screen
CAT = (EX[0] + 230, EX[1] + 30)                                    # converter under the car floor


def street(t, glow=0.0):
    img = ST.frame(t, 380 + 30 * math.sin(t * 0.7)).convert('RGBA')
    d = ImageDraw.Draw(img)
    if glow > 0:                                                    # x-ray: the converter glowing through the car floor
        d.rounded_rectangle((CAT[0] - 90, CAT[1] - 26, CAT[0] + 90, CAT[1] + 26), 16, fill=(255, 150, 60, int(200 * glow)))
    fx.blit(img, up(car('blue'), CS), CX, CB)
    if glow > 0:
        fx.blit(img, up(sb.exhaust(t, 1.0).crop((60, 4, 124, 36)), 3), CAT[0], CAT[1], anchor='center')
    return img


def thief_layer(t):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); x = EX[0] - 10
    ImageDraw.Draw(lay).ellipse((x - 220, CB - 330, x + 220, CB + 40), fill=(255, 236, 190, 70))   # lamp light behind him
    fx.blit(lay, up(sb.thief(t), 8), x, CB + 20)
    return lay.filter(ImageFilter.GaussianBlur(7))                  # silhouette stays a blur: no person to recognise


# ------------------------------------------------------------------ shot 1: the theft
def shot_street(t):
    img = street(t); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(fg)
    fl = 0.7 + 0.3 * math.sin(t * 23) * math.sin(t * 7)            # torch beam from the thief to the pipe
    d.polygon([(EX[0] - 90, EX[1] + 30), (EX[0] + 260, EX[1] - 90), (EX[0] + 260, EX[1] + 140)], fill=(255, 246, 200, int(70 * fl)))
    img.alpha_composite(fg); img.alpha_composite(thief_layer(t))
    sp = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for k in range(4):                                              # saw sparks, a fresh shower every 0.18 s
        t0 = math.floor(t / 0.18) * 0.18 - k * 0.18
        fx.burst(sp, t, t0, EX[0] + 40, EX[1] + 10, (255, 190, 70), n=8, life=0.4, r0=20, r1=260, seed=70 + int(t0 * 50) % 9, s=7)
    img.alpha_composite(sp)
    fx.blit(img, up(stopwatch((t * 1.5) % 1), 7), 860, 760, anchor='center')
    fx.ring(img, t % 0.5, 0, 860, 760, (255, 90, 90), life=0.4, r1=220)
    z = lerp(1.7, 1.1, oc(prog(t, -0.2, 1.1))); sh = 12 + 22 * math.exp(-max(0, t) * 2)
    return D.camera(img.convert('RGB'), t, z, EX[0] + 80, EX[1] - 120, sh)


# ------------------------------------------------------------------ shot 2: what it does
XS, XC = 5, (540, 780)
CATX = XC[0] - 95 * XS + sb.EXH_CAT[0] * XS


def card(fg, box):
    ImageDraw.Draw(fg).rounded_rectangle(box, 36, fill=(18, 20, 28, 235), outline=(90, 96, 112, 255), width=8)


P2 = Presenter([(-9, dict(path=Fn(lambda t: (170, 1720)), size=7, legs='stand', arms='point', point=XC, expr='smile', ground=1720, look=XC)),
                (CLEAN, dict(arms='cheer', expr='grin', squash=True))], words=WORDS)


def shot_exhaust(t):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(fg)
    card(fg, (40, 480, 1040, 1060))
    glow = oc(prog(t, CLEAN - 0.3, 0.5))
    for j in range(7):                                              # fumes travelling down the pipe
        u = ((t - T2) * 0.6 + j / 7) % 1; x = lerp(70, 1020, u); y = XC[1] - 70 + 12 * math.sin(t * 6 + j)
        clean = x > CATX and glow > 0.5
        r = 30 + 10 * math.sin(j + t * 4)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(236, 244, 255, 150) if clean else (70, 66, 64, 210))
    fx.blit(fg, up(sb.exhaust(t, glow), XS), XC[0], XC[1], anchor='center')
    if t >= EXH: fx.ring(fg, t, EXH, XC[0], XC[1], (255, 210, 63), life=0.4, r1=520)
    if glow > 0:
        fx.sparkles(fg, t, 930, XC[1] - 100, 220, 160, n=5, seed=31)
        fx.ring(fg, t, CLEAN, CATX, XC[1], (255, 150, 60), life=0.45, r1=300)
    img.alpha_composite(G.rim(fg)); P2.draw(img, t)
    cb.pill(img, t, CLEAN + 0.05, T3 - 0.1, 'CLEANS THE FUMES', (CATX, XC[1] - 70), (520, 580), '#5adc78', '#1a1a2e', '#2f9a4c', s=6)
    z = lerp(1.2, 1.05, oc(prog(t, T2, 0.6))) + (0.05 * math.exp(-(t - CLEAN) * 6) if t >= CLEAN else 0)
    return D.camera(img.convert('RGB'), t, z, 540, 820, 4 + (16 * math.exp(-(t - CLEAN) * 5) if t >= CLEAN else 0))


# ------------------------------------------------------------------ shot 3: the precious metals inside
CATB = (800, 470)                                                  # the converter, cracked open, top right
TILES = (('platinum', 'PLATINUM'), ('palladium', 'PALLADIUM'), ('rhodium', 'RHODIUM'))
ROW = lambda i: (290, 650 + 150 * i)


def shot_metals(t):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    card(fg, (40, 340, 1040, 1060))
    jit = 8 * math.sin(t * 40) * math.exp(-max(0, t - INSIDE) * 3) if t >= INSIDE else 0
    fx.blit(fg, up(sb.exhaust(t, 1.0).crop((62, 4, 122, 36)), 6), CATB[0] + jit, CATB[1], anchor='center')
    if t >= INSIDE: fx.ring(fg, t, INSIDE, *CATB, (255, 150, 60), life=0.4, r1=260)
    if t >= PREC: fx.flakes(fg, t, PREC, CATB[0], CATB[1], n=10, seed=61, spread=420, life=1.6, rise=300)
    for i, (kind, _) in enumerate(TILES):
        if t < MET[i] - 0.3: continue
        u = oc(prog(t, MET[i] - 0.3, 0.32)); x, y = lerp(CATB[0], ROW(i)[0], u), lerp(CATB[1], ROW(i)[1], u)
        fx.blit(fg, up(sb.metal_tile(kind, t, MET[i]), 6), x, y + 4 * math.sin(t * 5 + i), rot=lerp(40, 0, u), anchor='center')
        if t >= MET[i]:
            fx.glint(fg, t, MET[i], *ROW(i), r=120)
            fx.sparkles(fg, t, *ROW(i), 260, 140, n=3, seed=40 + i)
    img.alpha_composite(G.rim(fg))
    for i, (_, lab) in enumerate(TILES):
        cb.pill(img, t, MET[i] + 0.05, T4 - 0.1, lab, (ROW(i)[0] + 100, ROW(i)[1]), (680, ROW(i)[1]), '#ffd23f', '#1a1a2e', '#e8b923', s=6)
    hit = max([m for m in MET if t >= m] or [-9])
    z = lerp(1.18, 1.04, oc(prog(t, T3, 0.5))) + 0.04 * math.exp(-(t - hit) * 6)
    return D.camera(img.convert('RGB'), t, z, 540, 800, 4 + 14 * math.exp(-(t - hit) * 5))


# ------------------------------------------------------------------ shot 4: a target
def shot_target(t):
    img = street(t, glow=0.6 + 0.4 * math.sin(t * 8)); d = ImageDraw.Draw(img)
    k = oc(prog(t, T4, TGT - T4 + 0.1)); r = lerp(420, 140, k); a = t * 90
    for rr, w in ((r, 14), (r * 0.6, 8)):
        d.arc((CAT[0] - rr, CAT[1] - rr, CAT[0] + rr, CAT[1] + rr), a, a + 300, fill=(232, 52, 63), width=w)
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):             # corner brackets closing in
        x, y = CAT[0] + sx * (r + 30), CAT[1] + sy * (r + 30)
        d.line((x, y, x - sx * 60, y), fill=(232, 52, 63), width=14); d.line((x, y, x, y - sy * 60), fill=(232, 52, 63), width=14)
    d.line((CAT[0] - r - 80, CAT[1], CAT[0] - r + 40, CAT[1]), fill=(232, 52, 63), width=8)
    d.line((CAT[0] + r - 40, CAT[1], CAT[0] + r + 80, CAT[1]), fill=(232, 52, 63), width=8)
    if t >= TGT:
        fx.ring(img, t, TGT, *CAT, (255, 90, 90), life=0.45, r1=420); fx.burst(img, t, TGT, *CAT, (255, 90, 90), n=12, r0=100, r1=380)
    z = lerp(1.15, 1.45, io(prog(t, T4, T5 - T4))); sh = 4 + (20 * math.exp(-(t - TGT) * 6) if t >= TGT else 0)
    return D.camera(img.convert('RGB'), t, z, CAT[0], CAT[1] - 150, sh)


# ------------------------------------------------------------------ shot 5: the question, on the dashboard
P5 = Presenter([(-9, dict(path=Fn(lambda t: (250, 1700)), size=9, legs='stand', arms='shrug', expr='smile', ground=1700, look_camera=True,
                          squash=True)),
                (ws(36), dict(arms=('aim', -12), expr='grin', squash=True))], words=WORDS)


def shot_ask(t):
    img = DASH.frame(t, rpm_deg=cb.rpm_deg(0.12 + 0.015 * math.sin(t * 9)), ac_on=True).copy()
    fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.blit(fg, up(sb.exhaust(t, 0.5 + 0.5 * math.sin(t * 4)).crop((62, 4, 122, 36)), 4), 820, 1640 + 10 * math.sin(t * 3), anchor='center')
    fx.sparkles(fg, t, 820, 1640, 300, 240, n=4, seed=41)
    img.alpha_composite(fg); P5.draw(img, t)
    return D.camera(img.convert('RGB'), t, lerp(1.15, 1.04, oc(prog(t, T5, 0.6))), 540, 1200, 5)


SCENE = D.sequence([(-9, shot_street), (T2, shot_exhaust), (T3, shot_metals), (T4, shot_target), (T5, shot_ask)])


def overlay(cv, t):
    ov.headline(cv, t, T2 - 0.2, HOOK, y=440)
    if t >= END_T: ov.headline(cv, max(-0.35, t - DUR), T2 - 0.2, HOOK, y=440)
    ov.poll(cv, t, T5 + 0.1, END_T - 0.1, 'Do you know where yours is?', ov.SAFE_CX, 640, 0.9)


CUES = ([(0.0, 'creak', 0.5), (0.05, 'whoosh', 0.5)] + [(k * 0.18, 'snap', 0.25) for k in range(int(T2 / 0.18))] +
        [(ws(7), 'ding', 0.5), (EXH, 'pop', 0.5), (CLEAN - 0.3, 'hum', 0.4), (CLEAN + 0.05, 'pop', 0.7), (CLEAN, 'sparkle', 0.5),
         (INSIDE, 'clink', 0.6), (PREC, 'sparkle', 0.6)] +
        [(m - 0.3, 'whoosh', 0.4) for m in MET] + [(m, 'clink', 0.8) for m in MET] + [(m + 0.05, 'pop', 0.5) for m in MET] +
        [(T4 + 0.1, 'beep', 0.5), (TGT, 'stamp', 0.7), (T5 + 0.1, 'pop', 0.8), (END_T, 'whoosh', 0.6)])

D.wire(HERE, WORDS, DUR, END_T, SCENE, [T2, T3, T4, T5], CUES, KEYCOL, overlay, cap=(T2, 1100, ((T5, 99),)))

if __name__ == '__main__':
    D.cli()
