"""Renders 'Electric cars are silent. So why the fake sound?': pedestrian-warning sound rules (US 18.6 mph, EU 12 mph).

Template: videos/ac-idle shot structure on shared/episode.py (captions, progress bar, mixer). Looping format: no outro
card; the last shot replays the cold open's glide-in, so the last frame flows into frame 0. Voiceover: out/ev-fake-sound/
voiceover.wav (clip 3 of out/voiceover/full_voiceover.wav, see ../../fuel-gauge-arrow/src/voiceover.py).
Numbers exactly as scripted: US below 18.6 mph, EU below 12 mph; no dates for when the rules started.
Shots:
  1 crossing 0.00  cold open: a silent EV glides toward a crossing, flat sound meter; a pedestrian steps out, '!', the hum starts
  2 law      3.70  'THE LAW SAYS SO' stamp slams down with a camera punch; the real EV photo pops in
  3 zone     5.35  speedometer arc: US zone to 18.6 mph, EU zone to 12 mph; the pedestrian hears it and steps back; poll sticker
  4 slots   11.70  slot-machine sound picker spins engine / spaceship / music
  5 loop    14.15  replays the cold-open glide-in, so the last frame matches frame 0
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, headline, sticker, street, ROAD_Y
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, ob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline
from pixanim.autos import ev, ptext

WORDS = kit.load_words(HERE)
DUR = 14.8
END_T = 14.15
def ws(i): return WORDS[i]['s']
HOOK = ((('Electric cars are', None),), (('SILENT.', '#ffd23f'),), (('So why the fake sound?', None),))
CYAN = (90, 200, 255)


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def walker(step=0, back=False):
    """Generic pedestrian silhouette (14x30): no face or logo; step 0..3 walk cycle, `back` = leaning away."""
    img = Image.new('RGBA', (14, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    body, dark, skin = (88, 132, 196), (52, 82, 130), (214, 170, 130)
    lean = -1 if back else 0
    d.ellipse((4 + lean, 0, 9 + lean, 5), fill=skin); d.rectangle((4 + lean, 0, 9 + lean, 1), fill=(60, 44, 36))
    d.rectangle((3 + lean, 6, 10 + lean, 16), fill=body); d.rectangle((3 + lean, 6, 4 + lean, 16), fill=dark)
    sw = [(-2, 2), (0, 0), (2, -2), (0, 0)][step]
    d.line([(4 + lean, 8), (2 + lean + sw[0], 15)], fill=body, width=2); d.line([(9 + lean, 8), (11 + lean + sw[1], 15)], fill=body, width=2)
    d.rectangle((4, 17, 9, 19), fill=(40, 42, 54))
    d.line([(5, 19), (5 + sw[0], 28)], fill=(40, 42, 54), width=2); d.line([(8, 19), (8 + sw[1], 28)], fill=(40, 42, 54), width=2)
    d.rectangle((3 + sw[0], 28, 6 + sw[0], 29), fill=(20, 20, 26)); d.rectangle((7 + sw[1], 28, 10 + sw[1], 29), fill=(20, 20, 26))
    return outline(img)


@lru_cache(None)
def meter(level=0, ph=0):
    """Sound meter (60x22): a dark screen with a speaker icon and a waveform, flat at level 0, louder up to level 4."""
    img = Image.new('RGBA', (60, 22), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 59, 21), 4, fill=(20, 21, 28), outline=(150, 156, 170))
    d.rectangle((4, 8, 6, 13), fill=(226, 230, 238)); d.polygon([(7, 8), (11, 4), (11, 17), (7, 13)], fill=(226, 230, 238))
    if level == 0:
        d.line([(15, 4), (24, 17)], fill=(255, 90, 90), width=1); d.line([(15, 17), (24, 4)], fill=(255, 90, 90), width=1)
    col = CYAN if level else (90, 94, 104)
    pts = [(27 + x, 11 - level * 1.6 * math.sin((x + ph) * 0.9) * (0.6 + 0.4 * math.sin(x * 0.4))) for x in range(30)]
    d.line(pts, fill=col)
    return outline(img)


@lru_cache(None)
def speedo(needle=0.0, us=0.0, eu=0.0):
    """Speedometer arc (110x66), 0-30 mph over 180 deg; green US zone to 18.6 (us 0..1), yellow EU zone to 12 (eu 0..1)."""
    img = Image.new('RGBA', (110, 66), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cx, cy, R = 55, 58, 50
    d.pieslice((cx - R - 4, cy - R - 4, cx + R + 4, cy + R + 4), 180, 360, fill=(26, 26, 46))
    d.pieslice((cx - R, cy - R, cx + R, cy + R), 180, 360, fill=(20, 21, 28))
    ang = lambda v: 180 + 180 * v / 30
    if us > 0: d.arc((cx - R + 2, cy - R + 2, cx + R - 2, cy + R - 2), 180, ang(18.6 * us), fill=(60, 200, 90), width=6)
    if eu > 0: d.arc((cx - R + 9, cy - R + 9, cx + R - 9, cy + R - 9), 180, ang(12 * eu), fill=(255, 210, 63), width=5)
    for v in range(0, 31, 5):
        a = math.radians(ang(v)); r0 = R - (8 if v % 10 == 0 else 5)
        d.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + (R - 1) * math.cos(a), cy + (R - 1) * math.sin(a))], fill=(226, 230, 238))
        if v % 10 == 0:
            n = ptext(str(v), (200, 204, 214)); r1 = R - 16
            img.alpha_composite(n, (round(cx + r1 * math.cos(a) - n.width / 2), round(cy + r1 * math.sin(a) - 4)))
    a = math.radians(ang(needle))
    d.line([(cx, cy), (cx + (R - 6) * math.cos(a), cy + (R - 6) * math.sin(a))], fill=(255, 96, 40), width=2)
    d.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=(176, 182, 192))
    m = ptext('MPH', (150, 156, 170)); img.alpha_composite(m, (cx - m.width // 2, cy - 18))
    return outline(img)


@lru_cache(None)
def icon(kind):
    """Slot icons (18x18): 'engine' block with pistons, 'ship' flying saucer, 'music' double note."""
    img = Image.new('RGBA', (18, 18), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if kind == 'engine':
        d.rectangle((2, 6, 15, 15), fill=(150, 156, 170)); d.rectangle((2, 6, 15, 7), fill=(200, 204, 214))
        for x in (4, 8, 12): d.rectangle((x, 2, x + 1, 6), fill=(214, 48, 58))
        d.rectangle((0, 9, 2, 12), fill=(110, 116, 128)); d.rectangle((15, 9, 17, 12), fill=(110, 116, 128))
    elif kind == 'ship':
        d.ellipse((5, 2, 12, 9), fill=(126, 200, 240)); d.ellipse((0, 7, 17, 13), fill=(176, 182, 192))
        for x in (3, 8, 13): d.point((x, 10), fill=(255, 210, 63))
        d.line([(6, 13), (4, 16)], fill=(90, 220, 120)); d.line([(11, 13), (13, 16)], fill=(90, 220, 120))
    else:
        d.rectangle((6, 2, 15, 3), fill=(255, 120, 200)); d.rectangle((6, 2, 7, 13), fill=(255, 120, 200)); d.rectangle((14, 2, 15, 11), fill=(255, 120, 200))
        d.ellipse((2, 11, 7, 15), fill=(255, 120, 200)); d.ellipse((10, 9, 15, 13), fill=(255, 120, 200))
    return outline(img)


def waves(fg, t, t0, x, y, n=3, col=CYAN, flip=False):
    """Sound waves: arcs pulsing out of (x, y) every 0.3 s after t0."""
    if t < t0: return
    d = ImageDraw.Draw(fg)
    for k in range(n):
        u = ((t - t0) / 0.9 + k / n) % 1
        r = 40 + 220 * u; a = int(255 * (1 - u))
        box = (x - r, y - r, x + r, y + r)
        d.arc(box, 140 if flip else -40, 220 if flip else 40, fill=col + (a,), width=12)


# ================================================================== shot 1: the silent glide and the hum
EVS = 5
STOP = 1.35                                            # brakes for the pedestrian
PED_T, BANG, HUM = 0.55, 1.05, 1.45
def ev_x1(t): return lerp(-560, 330, oc(prog(t, -1.2, STOP + 1.2)))
def ped_x1(t): return lerp(1180, 800, oc(prog(t, PED_T, 0.7)))
CAM1 = Camera(W, H, [(-2.0, (520, 1000, 1.04)), (0.0, (540, 1000, 1.1)), (STOP, (560, 1000, 1.16), 'oc'), (3.8, (560, 1000, 1.2), 'io')],
              kicks=[(BANG, 0.12, 800, 1000), (HUM, 0.08, 420, 1050)], shakes=[(BANG, 0.25, 10)])


def shot_cross(t):
    img = street(t, 120 * t if t < STOP else 120 * STOP); fg = layer(); d = ImageDraw.Draw(fg)
    for k in range(6): d.rectangle((640 + k * 70, ROAD_Y - 64, 680 + k * 70, ROAD_Y + 10), fill=(226, 230, 238, 200))   # crossing
    x = ev_x1(t)
    blit(fg, up(ev('air', int(t * 400) % 360 if t < STOP else 0, lights=True), EVS), x, ROAD_Y + 6)
    if t < STOP:
        fx.speed_lines(fg, 0.5 * (1 - prog(t, -1.2, STOP + 1.2)), int(t * 12) % 5, col=(170, 200, 230))
    waves(fg, t, HUM, x + 270, ROAD_Y - 90)
    blit(fg, up(walker(int(t * 8) % 4 if PED_T < t < PED_T + 0.7 else 1), 9), ped_x1(t), ROAD_Y + 10, flip=True)
    if t >= BANG:
        k = popin(t, BANG, 0.2)
        blit(fg, fx.big('glyph', '!', '#e0303a', s=18), ped_x1(t), ROAD_Y - 330, k, k, 8 * math.sin(t * 9), anchor='center')
        fx.burst(fg, t, BANG, ped_x1(t), ROAD_Y - 360, RED, n=12, seed=11)
    lv = 0 if t < HUM else min(4, 1 + int((t - HUM) * 8))
    km = 1 + (0.15 * math.exp(-(t - HUM) * 8) if t >= HUM else 0)
    blit(fg, up(meter(lv, int(t * 12) % 30), 9), 540, 860, km, km, -2 + math.sin(t * 2), anchor='center')
    if t >= HUM: fx.ring(fg, t, HUM, 540, 860, CYAN, r1=360)
    return CAM1.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 2: the law says so
T2 = 3.70
LAW = ws(15)                                           # 'law'
P2 = Presenter([
    (T2, dict(path=Track([(T2, (1300, 400)), (T2 + 0.35, (880, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='talk', face=-1, ground=None)),
    (T2 + 0.35, dict(ground=GROUND, squash=True, arms='point', point=(540, 700), look=(540, 700), expr='talk')),
    (LAW, dict(arms='shock', expr='wow', squash=True, point=None, look=None, look_camera=True)),
], words=WORDS, base_size=6)
CAM2 = Camera(W, H, [(T2, (540, 940, 1.06)), (5.4, (540, 940, 1.14), 'io')], kicks=[(LAW, 0.25, 540, 1150), (T2 + 0.35, 0.06, 880, 1100)],
              shakes=[(LAW, 0.4, 20)])


def shot_law(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    P2.draw(fg, t)
    if t >= LAW:
        fx.stamp_at(fg, t, LAW, 'THE LAW SAYS SO', 540, 1170, rot=-8, s=9, col='#e0303a')
        fx.burst(fg, t, LAW, 520, 1120, RED, n=18, seed=21); fx.ring(fg, t, LAW, 520, 1120, GLOW, r1=600)
        fx.dust(fg, t, LAW, 520, 1200, n=14, seed=22)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the sound zone
T3 = 5.35
US, EU = ws(28), ws(35)                                # '18.6', '12.'
POLL = 9.6
def needle3(t):
    if t < US: return 18.6 * io(clamp((t - T3 - 0.2) / (US - T3 - 0.2)))
    if t < EU - 0.4: return 18.6 + 0.3 * math.sin(t * 9)
    return lerp(18.6, 12, io(clamp((t - EU + 0.4) / 0.4))) + 0.3 * math.sin(t * 9)
P3 = Presenter([
    (T3, dict(path=Track([(T3, (1300, 300)), (T3 + 0.4, (950, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='grin', face=-1, ground=None)),
    (T3 + 0.4, dict(ground=GROUND, squash=True, arms='point', point=(540, 760), look=(540, 760), expr='talk')),
    (US, dict(squash=True, expr='wow')),
    (EU, dict(squash=True, expr='grin')),
], words=WORDS, base_size=6)
CAM3 = Camera(W, H, [(T3, (540, 900, 1.02)), (US, (540, 880, 1.08), 'io'), (11.7, (540, 900, 1.1), 'io')],
              kicks=[(US, 0.16, 540, 800), (EU, 0.16, 540, 850), (ws(26), 0.08, 220, 1100)], shakes=[(US, 0.2, 8)])
BACK = ws(26) + 0.2                                    # 'pedestrians': he hears it and steps back


def shot_zone(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    us = oc(clamp((t - US) / 0.5)) if t >= US else 0
    eu = oc(clamp((t - EU) / 0.5)) if t >= EU else 0
    blit(fg, up(speedo(round(needle3(t) * 4) / 4, round(us * 12) / 12, round(eu * 12) / 12), 8), 540, 990)
    if t >= US:
        fx.ring(fg, t, US, 540, 760, GRN, r1=520); fx.sparkles(fg, t, 540, 760, 860, 300, n=8, seed=31)
        k = popin(t, US + 0.1)
        blit(fg, fx.big('badge', 'US: BELOW 18.6 MPH', '#7fe3a0', '#1a1a2e', '#3c9e5a', s=6), 450, 1090, k, k, -2 + 1.5 * math.sin(t * 4), anchor='center')
    if t >= EU:
        fx.ring(fg, t, EU, 540, 800, GLOW, r1=480)
        k = popin(t, EU + 0.1)
        blit(fg, fx.big('badge', 'EU: BELOW 12 MPH', '#ffd23f', '#1a1a2e', '#e8b923', s=6), 450, 1200, k, k, 2 - 1.5 * math.sin(t * 4), anchor='center')
    bx = 190 if t < BACK else lerp(190, 110, oc(prog(t, BACK, 0.3)))   # pedestrian at the kerb hears the hum and steps back
    blit(fg, up(walker(int(t * 8) % 4 if BACK < t < BACK + 0.3 else 1, t >= BACK), 6), bx, GROUND + 20)
    waves(fg, t, T3 + 0.1, 300, GROUND - 120, n=2, flip=True)
    if t >= BACK:
        k = popin(t, BACK, 0.2) * popout(t, BACK + 1.2)
        blit(fg, fx.big('glyph', '!', '#ffd23f', s=10), bx, GROUND - 230, k, k, anchor='center')
    P3.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM3, t)


# ================================================================== shot 4: pick your sound
T4 = 11.70
PULL = T4 + 0.35
STOPS = [12.55, 12.95, 13.35]                         # reels land around 'pick' ... 'what would it be'
KINDS = ('engine', 'ship', 'music')
P4 = Presenter([
    (T4, dict(path=Track([(T4, (1300, 400)), (T4 + 0.3, (900, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='grin', face=-1, ground=None)),
    (T4 + 0.3, dict(ground=GROUND, squash=True, arms=('aim', 60), expr='grin')),
    (PULL, dict(arms=('aim', -30), expr='wow', squash=True)),
    (STOPS[-1] + 0.1, dict(arms='shrug', expr='think', look_camera=True, squash=True)),
], words=WORDS, base_size=6)
CAM4 = Camera(W, H, [(T4, (540, 900, 1.06)), (STOPS[-1], (540, 900, 1.14), 'io'), (END_T, (540, 900, 1.16))],
              kicks=[(PULL, 0.1, 540, 800)] + [(s, 0.08, 300 + 240 * i, 800) for i, s in enumerate(STOPS)])


def shot_slots(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer(); d = ImageDraw.Draw(fg)
    x0, y0, x1, y1 = 120, 560, 840, 1080                # cabinet
    d.rounded_rectangle((x0 - 20, y0 - 120, x1 + 20, y1 + 60), 40, fill=(26, 26, 46))
    d.rounded_rectangle((x0 - 10, y0 - 110, x1 + 10, y1 + 50), 34, fill=(214, 48, 58))
    for i in range(14):                                 # chase lights
        on = (i + int(t * 10)) % 3 == 0
        d.ellipse((x0 + 10 + i * 50, y0 - 95, x0 + 30 + i * 50, y0 - 75), fill=(255, 217, 59) if on else (120, 40, 46))
    rh = y1 - 40 - y0
    for i in range(3):
        rx = x0 + 20 + i * 235
        reel = Image.new('RGBA', (215, rh), (0, 0, 0, 0)); ImageDraw.Draw(reel).rounded_rectangle((0, 0, 214, rh - 1), 20, fill=(250, 250, 246))
        spin = PULL <= t < STOPS[i]
        off = (t - PULL) * 9 if spin else 0.0
        settle = 0 if spin or t < STOPS[i] else 30 * math.exp(-(t - STOPS[i]) * 10) * math.cos((t - STOPS[i]) * 30)
        for j in (-1, 0, 1, 2):
            kind = KINDS[(i - j + int(off)) % 3]
            ic_ = up(icon(kind), 10)
            if spin: ic_ = ic_.resize((ic_.width, int(ic_.height * 1.4)), Image.NEAREST)
            yy = rh / 2 + j * 240 + (off % 1) * 240 * (1 if spin else 0) + settle
            reel.alpha_composite(ic_, (107 - ic_.width // 2, int(yy - ic_.height / 2))) if -ic_.height < yy - ic_.height / 2 < rh else None
        rm = Image.new('L', reel.size, 0); ImageDraw.Draw(rm).rounded_rectangle((0, 0, 214, rh - 1), 20, fill=255)
        fg.paste(reel, (rx, y0), rm)
        if t >= STOPS[i]:
            fx.ring(fg, t, STOPS[i], rx + 107, y0 + rh / 2, GLOW, r1=200)
    lever = 0 if t < PULL else max(0, 1 - (t - PULL) * 3)
    d.rectangle((x1 + 30, y0 + 40, x1 + 50, y0 + 300), fill=(150, 156, 170))
    d.ellipse((x1 + 15, y0 - 20 + 220 * lever, x1 + 65, y0 + 30 + 220 * lever), fill=(255, 90, 90))
    fl = fg
    if t >= STOPS[-1]:
        fx.confetti(fl, t, STOPS[-1], 480, 500, n=30, seed=41)
        kq = popin(t, STOPS[-1] + 0.1) * (1 + 0.08 * math.sin(t * 7))
        blit(fl, fx.big('glyph', '?', '#ffd23f', s=16), 480, 420, kq, kq, 8 * math.sin(t * 4), anchor='center')
    P4.draw(fl, t)
    GAR.reflect(img, fl)
    return finish(img, fl, CAM4, t)


def shot_loop(t): return shot_cross(t - DUR)


def overlay(cv, t):
    headline(cv, t, 2.6, HOOK, y=470, sz=100)
    if t >= END_T and t - DUR > -0.45: headline(cv, max(-0.35, t - DUR), 2.6, HOOK, y=470, sz=100)
    kit.photo_hq(cv, t, T2 + 0.12, T3 - 0.1, 'ev', 540, 640, 760, rot=-4, label='A REAL EV')
    sticker(cv, t, POLL, T4 + 1.5, ('What would YOU pick?',), 330, opts=(('ENGINE', (214, 48, 58)), ('SPACESHIP', (60, 140, 220)), ('MUSIC', (200, 80, 170))), w=940)


SHOTS = [(-3.0, shot_cross), (T2, shot_law), (T3, shot_zone), (T4, shot_slots), (END_T, shot_loop)]
TRANS = {1: (T2, T2 + 0.2, 'whip', dict(dx=1)), 2: (T3, T3 + 0.2, 'push', None), 3: (T4, T4 + 0.2, 'whip', dict(dx=0, dy=1)),
         4: (END_T, END_T + 0.2, 'whip', dict(dx=-1))}
KEYCOL = {'silent.': YEL, 'silent': YEL, 'fake': RED, 'law': RED, '18.6': GRN, 'pedestrians': YEL, 'europe,': YEL, 'europe': YEL, '12': YEL, 'pick': YEL}
CUES = [(0.0, 'whoosh', 0.35), (PED_T, 'thump', 0.25), (BANG, 'pop', 0.8), (BANG + 0.02, 'screech', 0.6), (HUM, 'hum', 0.9),
        (HUM + 1.0, 'hum', 0.6), (T2 + 0.12, 'pop', 0.7), (T2 + 0.35, 'thump', 0.4), (LAW, 'stamp', 1.0), (LAW + 0.02, 'boom', 0.6),
        (US, 'ding', 0.8), (US + 0.1, 'pop', 0.5), (BACK, 'hum', 0.5), (BACK + 0.05, 'pop', 0.4), (POLL, 'pop', 0.7),
        (EU, 'ding', 0.8), (EU + 0.1, 'pop', 0.5), (T4 + 0.3, 'thump', 0.4), (PULL, 'creak', 0.5)] + [
        (PULL + 0.08 * k, 'click', 0.3) for k in range(int((STOPS[-1] - PULL) / 0.08))] + [
        (s, 'ding', 0.6) for s in STOPS] + [(STOPS[-1] + 0.05, 'confetti', 0.6), (STOPS[-1] + 0.1, 'sparkle', 0.6)]

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='blue', gauge=False, loud=True, crisp=True,
          end=False, flash=False, tag='corner')

if __name__ == '__main__':
    kit.main()
