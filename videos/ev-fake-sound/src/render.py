"""Renders 'Electric cars are silent. So why the fake sound?': pedestrian-warning sound rules (US 18.6 mph, EU 12 mph).

Template: videos/ac-idle shot structure on shared/episode.py (captions, progress bar, mixer). Looping format: no outro
card; the last shot replays the cold open's glide-in, so the last frame flows into frame 0. Voiceover: out/ev-fake-sound/
voiceover.wav (clip 3 of out/voiceover/full_voiceover.wav, see ../../fuel-gauge-arrow/src/voiceover.py).
Numbers exactly as scripted: US below 18.6 mph, EU below 12 mph; no dates for when the rules started.
Shots (v2: ~1.5 s beats, detailed worlds, choreographed presenter):
  1 crossing 0.00  cold open: a silent EV glides toward a crossing, flat sound meter; a pedestrian steps out, '!', the hum starts;
                   he pops up beside the meter, puzzled
  2 law      3.70  a rule book slams down, 'THE LAW SAYS SO' stamp, camera punch; the real EV photo pops in
  3 street   5.35  'In the US...': the EV creeps up humming, the pedestrian at the kerb hears it and steps back; he points
  4 zone     8.20  chrome speedometer: US zone to 18.6 mph, then EU zone to 12 mph; poll sticker from 9.6 s
  5 slots   11.70  he yanks the lever of a slot-machine sound picker: engine / spaceship / music
  6 loop    14.15  replays the cold-open glide-in, so the last frame matches frame 0
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
from pixanim.presenter import Presenter, reach
from pixanim import fx, diagram as dg
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
    img = Image.new('RGBA', (112, 66), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cx, cy, R = 56, 59, 50
    for r_, col in ((R + 5, (26, 26, 46)), (R + 4, (132, 138, 150)), (R + 3, (176, 182, 194)), (R + 1, (96, 100, 112))):   # chrome bezel
        d.pieslice((cx - r_, cy - r_, cx + r_, cy + r_), 180, 360, fill=col)
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


@lru_cache(None)
def rulebook(open_=0):
    """Thick rule book (40x30): navy cover, gold 'LAW' lettering and corners, page block; open_ 1 = slightly opened."""
    img = Image.new('RGBA', (40, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((2, 20, 39, 29), fill=(240, 236, 222)); [d.line((3, y, 38, y), fill=(206, 200, 184)) for y in (22, 24, 26, 28)]
    d.rectangle((0, 14 - 3 * open_, 37, 21), fill=(34, 44, 86)); d.rectangle((0, 14 - 3 * open_, 37, 15 - 3 * open_), fill=(70, 84, 140))
    d.rectangle((0, 0 if not open_ else 2, 36, 18), fill=(40, 52, 100)); d.rectangle((1, 1, 35, 2), fill=(76, 92, 150))
    for x, y in ((2, 2), (32, 2), (2, 14), (32, 14)): d.rectangle((x, y, x + 2, y + 2), fill=(255, 210, 63))
    t = ptext('LAW', (255, 210, 63)); img.alpha_composite(t, (18 - t.width // 2, 6))
    return outline(img)


# ================================================================== shot 1: the silent glide and the hum
EVS = 6
STOP = 1.35                                            # brakes for the pedestrian
PED_T, BANG, HUM = 0.55, 1.05, 1.45
def ev_x1(t): return lerp(-600, 300, oc(prog(t, -1.2, STOP + 1.2)))
def ped_x1(t): return lerp(1180, 820, oc(prog(t, PED_T, 0.7)))
P1 = Presenter([
    (-5, dict(path=Track([(2.0, (1150, 1500)), (2.3, (880, 760), 'oc')], smooth=True), size=5, legs='auto', arms='fly', expr='think',
              face=-1, hover=8, visible=False)),
    (2.0, dict(visible=True)),
    (2.3, dict(arms='shrug', look_camera=True, squash=True)),
], words=WORDS, base_size=5)
CAM1 = Camera(W, H, [(-2.0, (420, 1000, 1.2)), (0.0, (460, 1000, 1.24)), (STOP, (580, 1000, 1.24), 'oc'), (3.8, (600, 980, 1.3), 'io')],
              kicks=[(BANG, 0.14, 820, 1000), (HUM, 0.1, 420, 1050)], shakes=[(BANG, 0.3, 12)])


def shot_cross(t):
    img = street(t, 160 * t if t < STOP else 160 * STOP); fg = layer(); d = ImageDraw.Draw(fg)
    for k in range(6): d.rectangle((660 + k * 70, ROAD_Y - 64, 700 + k * 70, ROAD_Y + 10), fill=(226, 230, 238, 200))   # crossing
    x = ev_x1(t)
    d.polygon([(x + 300, ROAD_Y - 80), (x + 760, ROAD_Y - 150), (x + 760, ROAD_Y + 30), (x + 300, ROAD_Y - 40)], fill=(255, 244, 200, 40))
    blit(fg, up(ev('air', int(t * 400) % 360 if t < STOP else 0, lights=True), EVS), x, ROAD_Y + 6)
    if t < STOP:
        fx.speed_lines(fg, 0.5 * (1 - prog(t, -1.2, STOP + 1.2)), int(t * 12) % 5, col=(170, 200, 230))
        for k in range(4):                              # silent: just a shimmer trail, no exhaust
            fx.sparkles(fg, t + k * 0.1, x - 320 - 60 * k, ROAD_Y - 90, 80, 60, n=2, seed=70 + k, s=5)
    waves(fg, t, HUM, x + 320, ROAD_Y - 100)
    blit(fg, up(walker(int(t * 8) % 4 if PED_T < t < PED_T + 0.7 else 1, t >= BANG), 10), ped_x1(t), ROAD_Y + 10, flip=True)
    if t >= BANG:
        k = popin(t, BANG, 0.2)
        blit(fg, fx.big('glyph', '!', '#e0303a', s=18), ped_x1(t), ROAD_Y - 360, k, k, 8 * math.sin(t * 9), anchor='center')
        fx.burst(fg, t, BANG, ped_x1(t), ROAD_Y - 390, RED, n=12, seed=11)
    lv = 0 if t < HUM else min(4, 1 + int((t - HUM) * 8))
    km = 1 + (0.18 * math.exp(-(t - HUM) * 8) if t >= HUM else 0)
    blit(fg, up(meter(lv, int(t * 12) % 30), 9), 560, 870, km, km, -2 + math.sin(t * 2), anchor='center')
    if t >= HUM: fx.ring(fg, t, HUM, 560, 870, CYAN, r1=380); fx.burst(fg, t, HUM, 560, 870, CYAN, n=10, seed=15)
    P1.draw(fg, t)
    return CAM1.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 2: the law says so
T2 = 3.70
LAW = ws(15)                                           # 'law'
BOOK = (540, 1170)
def book_y(t): return BOOK[1] if t >= LAW else lerp(-300, BOOK[1], ic(prog(t, LAW - 0.3, 0.3)))
P2 = Presenter([
    (T2, dict(path=Track([(T2, (1300, 400)), (T2 + 0.35, (900, GROUND), 'oc')], smooth=True), size=6, legs='auto', arms='fly', expr='talk',
              face=-1, ground=None, trail=True)),
    (T2 + 0.35, dict(ground=GROUND, squash=True, arms='point', point=(540, 640), look=(540, 640), expr='talk')),
    (LAW, dict(path=Track([(LAW, (900, GROUND)), (LAW + 0.2, (920, GROUND - 160), 'oc'), (LAW + 0.4, (920, GROUND), 'ic')]), arms='shock',
               expr='wow', squash=True, point=None, look=None, look_camera=True)),
], words=WORDS, base_size=6)
CAM2 = Camera(W, H, [(T2, (540, 940, 1.12)), (LAW - 0.1, (540, 1000, 1.2), 'io'), (5.4, (540, 960, 1.16), 'io')],
              kicks=[(LAW, 0.18, *BOOK), (T2 + 0.35, 0.06, 900, 1100)], shakes=[(LAW, 0.45, 24)])


def shot_law(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    if t >= LAW: fx.rays(fg, t, LAW, *BOOK, (255, 210, 63, 34), hold=True, r=700)
    if t >= LAW - 0.3:
        sq = 1 + (0.25 * math.exp(-(t - LAW) * 12) * math.cos((t - LAW) * 30) if t >= LAW else 0)
        blit(fg, up(rulebook(int(t >= LAW + 0.1)), 12), BOOK[0], book_y(t) + 120, 1 / sq ** 0.5, sq, 0)
    if t >= LAW:
        fx.dust(fg, t, LAW, BOOK[0] - 200, BOOK[1] + 120, n=12, seed=22, dirx=-1); fx.dust(fg, t, LAW, BOOK[0] + 200, BOOK[1] + 120, n=12, seed=23, dirx=1)
        fx.burst(fg, t, LAW, *BOOK, RED, n=18, seed=21); fx.ring(fg, t, LAW, *BOOK, GLOW, r1=620)
        fx.stamp_at(fg, t, LAW + 0.12, 'THE LAW SAYS SO', 540, 1000, rot=-8, s=7, col='#e0303a')
    P2.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM2, t)


# ================================================================== shot 3: the pedestrian hears it
T3 = 5.35
BACK = ws(26) + 0.1                                    # 'pedestrians': he hears it and steps back
def ev_x3(t): return lerp(-500, 330, oc(prog(t, T3 - 0.2, BACK - T3 + 0.2)))
P3 = Presenter([
    (T3, dict(path=Track([(T3, (-200, 500)), (T3 + 0.4, (170, 760), 'oc')], smooth=True), size=5, legs='auto', arms='fly', expr='grin',
              face=1, hover=10, trail=True)),
    (T3 + 0.4, dict(arms='point', point=lambda t: (ev_x3(t) + 100, ROAD_Y - 120), look=lambda t: (ev_x3(t) + 100, ROAD_Y - 120), expr='talk')),
    (BACK, dict(arms='point', point=(840, ROAD_Y - 200), look=(840, ROAD_Y - 200), expr='wow', squash=True)),
], words=WORDS, base_size=5)
CAM3 = Camera(W, H, [(T3, (540, 1000, 1.16)), (BACK, (660, 1020, 1.28), 'io'), (8.3, (640, 1000, 1.24), 'io')],
              follow=[(T3, BACK, lambda t: (ev_x3(t) + 250, 1000), 0.35)],
              kicks=[(ws(20), 0.1, 540, 900), (BACK, 0.14, 840, 1000)])


def shot_street(t):
    img = street(t, 400 + 60 * (t - T3)); fg = layer(); d = ImageDraw.Draw(fg)
    for k in range(6): d.rectangle((660 + k * 70, ROAD_Y - 64, 700 + k * 70, ROAD_Y + 10), fill=(226, 230, 238, 200))
    x = ev_x3(t)
    blit(fg, up(ev('air', int(t * 200) % 360 if t < BACK else 0, lights=True), EVS), x, ROAD_Y + 6)
    waves(fg, t, T3 + 0.1, x + 320, ROAD_Y - 100, n=4)
    px = 880 if t < BACK else lerp(880, 1000, oc(prog(t, BACK, 0.3)))
    blit(fg, up(walker(int(t * 8) % 4 if BACK < t < BACK + 0.3 else 1, t >= BACK), 10), px, ROAD_Y + 10 - 70 * (t < BACK), flip=True)
    if t >= BACK:
        k = popin(t, BACK, 0.2) * popout(t, BACK + 1.6)
        blit(fg, fx.big('glyph', '!', '#ffd23f', s=14), px, ROAD_Y - 400, k, k, 6 * math.sin(t * 9), anchor='center')
        fx.ring(fg, t, BACK, px, ROAD_Y - 200, CYAN, r1=320)
        dg.label(fg, t, BACK + 0.15, 'HEARD IT', (px, ROAD_Y - 250), (px - 120, ROAD_Y - 560), '#7fd4ff', '#1a1a2e', '#3c8ab8', s=7)
    kb = popin(t, ws(20) - 0.05)                       # 'US' tag
    if kb > 0: blit(fg, fx.big('badge', 'US', '#ffffff', '#1a1a2e', '#d6d9e2', s=11), 540, 560, kb, kb, -4 + 2 * math.sin(t * 4), anchor='center')
    P3.draw(fg, t)
    return CAM3.apply(Image.alpha_composite(img, fg).convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 4: the sound zone
T4 = 8.20
US, EU = ws(28), ws(35)                                # '18.6', '12.'
POLL = 9.6
SPC = (540, 1000)                                      # speedometer bottom centre
def needle4(t):
    if t < US: return 18.6 * io(clamp((t - T4) / (US - T4 + 0.05)))
    if t < EU - 0.4: return 18.6 + 0.3 * math.sin(t * 9)
    return lerp(18.6, 12, io(clamp((t - EU + 0.4) / 0.4))) + 0.3 * math.sin(t * 9)
def tip4(t):
    a = math.radians(180 + 180 * needle4(t) / 30)
    return SPC[0] + 44 * 8 * math.cos(a), SPC[1] - 7 * 8 + 44 * 8 * math.sin(a)
P4 = Presenter([
    (T4, dict(path=Track([(T4, (1300, 300)), (T4 + 0.35, (990, GROUND + 60), 'oc')], smooth=True), size=6, legs='auto', arms='fly', expr='grin',
              face=-1, ground=None, trail=True)),
    (T4 + 0.35, dict(ground=GROUND + 60, squash=True, arms='point', point=tip4, look=tip4, expr='talk')),
    (US, dict(squash=True, expr='wow')),
    (EU, dict(squash=True, expr='grin')),
], words=WORDS, base_size=6)
CAM4 = Camera(W, H, [(T4, (540, 860, 1.14)), (US, (540, 840, 1.06), 'io'), (EU - 0.4, (540, 880, 1.04), 'io'), (EU, (540, 900, 1.08), 'io'), (11.7, (540, 900, 1.06), 'io')],
              kicks=[(US, 0.16, 540, 760), (EU, 0.16, 460, 860)], shakes=[(US, 0.2, 8)])


def shot_zone(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    us = oc(clamp((t - US) / 0.5)) if t >= US else 0
    eu = oc(clamp((t - EU) / 0.5)) if t >= EU else 0
    if t >= US: fx.rays(fg, t, US, 540, 760, (90, 220, 120, 26) if t < EU else (255, 210, 63, 26), hold=True, r=700)
    blit(fg, up(speedo(round(needle4(t) * 4) / 4, round(us * 12) / 12, round(eu * 12) / 12), 8), *SPC)
    fx.glint(fg, t, T4 + 0.3, 540, 760, r=380, life=0.6)
    if t >= US:
        fx.ring(fg, t, US, 540, 760, GRN, r1=520); fx.sparkles(fg, t, 540, 760, 860, 300, n=8, seed=31)
        k = popin(t, US + 0.1)
        blit(fg, fx.big('badge', 'US: BELOW 18.6 MPH', '#7fe3a0', '#1a1a2e', '#3c9e5a', s=6), 440, 1090, k, k, -2 + 1.5 * math.sin(t * 4), anchor='center')
    if t >= EU:
        fx.ring(fg, t, EU, 540, 800, GLOW, r1=480); fx.burst(fg, t, EU, 470, 820, GLOW, n=12, seed=32)
        k = popin(t, EU + 0.1)
        blit(fg, fx.big('badge', 'EU: BELOW 12 MPH', '#ffd23f', '#1a1a2e', '#e8b923', s=6), 440, 1200, k, k, 2 - 1.5 * math.sin(t * 4), anchor='center')
    P4.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM4, t)


# ================================================================== shot 5: pick your sound
T5 = 11.70
PULL = T5 + 0.45
STOPS = [12.55, 12.95, 13.35]                         # reels land around 'pick' ... 'what would it be'
KINDS = ('engine', 'ship', 'music')
X0, Y0, X1, Y1 = 100, 660, 820, 1150                  # cabinet
def knob(t):
    lever = 0 if t < PULL else max(0, 1 - (t - PULL) * 2.5)
    if T5 + 0.3 <= t < PULL: lever = -0.1 * prog(t, T5 + 0.3, PULL - T5 - 0.3)
    return X1 + 40, Y0 + 5 + 220 * max(0, lever)
P5 = Presenter([
    (T5, dict(path=Track([(T5, (1300, 300)), (T5 + 0.3, reach((X1 + 40, Y0 + 5), 150, 6, -1).at(0), 'oc')], smooth=True), size=6, legs='auto',
              arms='fly', expr='grin', face=-1, hover=6, trail=True)),
    (T5 + 0.3, dict(path=reach(knob, 150, 6, -1), arms=('aim', 150), expr='smirk', legs='fly')),
    (PULL, dict(expr='wow', squash=True)),
    (PULL + 0.45, dict(path=Track([(PULL + 0.45, reach((X1 + 40, Y0 + 225), 150, 6, -1).at(0)), (PULL + 0.75, (950, GROUND), 'oc')]),
                       arms='point', point=(460, 820), look=(460, 820), legs='auto', ground=GROUND, squash=True)),
    (STOPS[-1] + 0.1, dict(arms='shrug', point=None, look=None, expr='think', look_camera=True, squash=True)),
], words=WORDS, base_size=6)
CAM5 = Camera(W, H, [(T5, (560, 860, 1.12)), (PULL, (600, 840, 1.16), 'io'), (STOPS[-1], (520, 860, 1.12), 'io'), (END_T, (520, 860, 1.14))],
              kicks=[(PULL, 0.12, X1 + 40, Y0 + 200)] + [(s, 0.08, X0 + 127 + 235 * i, 800) for i, s in enumerate(STOPS)])


def shot_slots(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer(); d = ImageDraw.Draw(fg)
    fx.rays(fg, t, T5, 460, 820, (255, 210, 63, 22), hold=True, r=800)
    d.rounded_rectangle((X0 - 20, Y0 - 160, X1 + 20, Y1 + 60), 40, fill=(26, 26, 46))
    d.rounded_rectangle((X0 - 10, Y0 - 150, X1 + 10, Y1 + 50), 34, fill=(214, 48, 58))
    d.rounded_rectangle((X0 + 10, Y0 - 140, X1 - 10, Y0 - 70), 16, fill=(26, 26, 46))
    mq = up(ptext('PICK A SOUND', (255, 217, 59) if int(t * 4) % 2 else (255, 255, 255)), 5)
    fg.alpha_composite(mq, (int((X0 + X1) / 2 - mq.width / 2), Y0 - 128))
    for i in range(14):                                 # chase lights
        on = (i + int(t * 10)) % 3 == 0
        d.ellipse((X0 + 10 + i * 50, Y0 - 60, X0 + 30 + i * 50, Y0 - 40), fill=(255, 217, 59) if on else (120, 40, 46))
    rh = Y1 - 40 - Y0
    for i in range(3):
        rx = X0 + 20 + i * 235
        reel = Image.new('RGBA', (215, rh), (0, 0, 0, 0)); ImageDraw.Draw(reel).rounded_rectangle((0, 0, 214, rh - 1), 20, fill=(250, 250, 246))
        spin = PULL <= t < STOPS[i]
        off = (t - PULL) * 9 if spin else 0.0
        settle = 0 if spin or t < STOPS[i] else 30 * math.exp(-(t - STOPS[i]) * 10) * math.cos((t - STOPS[i]) * 30)
        for j in (-1, 0, 1, 2):
            ic_ = up(icon(KINDS[(i - j + int(off)) % 3]), 10)
            if spin: ic_ = ic_.resize((ic_.width, int(ic_.height * 1.4)), Image.NEAREST)
            yy = rh / 2 + j * 240 + (off % 1) * 240 * (1 if spin else 0) + settle
            if -ic_.height < yy - ic_.height / 2 < rh: reel.alpha_composite(ic_, (107 - ic_.width // 2, int(yy - ic_.height / 2)))
        ImageDraw.Draw(reel).rectangle((0, 0, 214, 30), fill=(0, 0, 0, 60)); ImageDraw.Draw(reel).rectangle((0, rh - 30, 214, rh), fill=(0, 0, 0, 60))
        rm = Image.new('L', reel.size, 0); ImageDraw.Draw(rm).rounded_rectangle((0, 0, 214, rh - 1), 20, fill=255)
        fg.paste(reel, (rx, Y0), rm)
        if t >= STOPS[i]:
            fx.ring(fg, t, STOPS[i], rx + 107, Y0 + rh / 2, GLOW, r1=200); fx.burst(fg, t, STOPS[i], rx + 107, Y0 + rh / 2, GLOW, n=8, r0=80, r1=200, seed=40 + i)
    kx, ky = knob(t)
    d.rectangle((X1 + 30, Y0 + 20, X1 + 50, Y0 + 300), fill=(150, 156, 170)); d.rectangle((X1 + 30, Y0 + 20, X1 + 34, Y0 + 300), fill=(200, 204, 214))
    d.line([(X1 + 40, Y0 + 300), (kx, ky)], fill=(176, 182, 194), width=14)
    d.ellipse((kx - 30, ky - 30, kx + 30, ky + 30), fill=(255, 90, 90), outline=(26, 26, 46), width=6)
    if t >= STOPS[-1]:
        fx.confetti(fg, t, STOPS[-1], 460, 500, n=40, seed=41)
        kq = popin(t, STOPS[-1] + 0.1) * (1 + 0.08 * math.sin(t * 7))
        blit(fg, fx.big('glyph', '?', '#ffd23f', s=16), 460, 400, kq, kq, 8 * math.sin(t * 4), anchor='center')
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


def shot_loop(t): return shot_cross(t - DUR)


def overlay(cv, t):
    headline(cv, t, 2.6, HOOK, y=470, sz=100)
    if t >= END_T and t - DUR > -0.45: headline(cv, max(-0.35, t - DUR), 2.6, HOOK, y=470, sz=100)
    kit.photo_hq(cv, t, T2 + 0.12, T3 - 0.1, 'ev', 540, 560, 600, rot=-4, label='A REAL EV, CHARGING')
    sticker(cv, t, POLL, T5 + 0.85, ('What would YOU pick?',), 330, opts=(('ENGINE', (214, 48, 58)), ('SPACESHIP', (60, 140, 220)), ('MUSIC', (200, 80, 170))), w=940)


SHOTS = [(-3.0, shot_cross), (T2, shot_law), (T3, shot_street), (T4, shot_zone), (T5, shot_slots), (END_T, shot_loop)]
TRANS = {1: (T2, T2 + 0.2, 'whip', dict(dx=1)), 2: (T3, T3 + 0.2, 'push', None), 3: (T4, T4 + 0.22, 'iris', (540, 900)),
         4: (T5, T5 + 0.2, 'whip', dict(dx=0, dy=1)), 5: (END_T, END_T + 0.2, 'whip', dict(dx=-1))}
KEYCOL = {'silent': YEL, 'fake': RED, 'law': RED, '18.6': GRN, 'pedestrians': YEL, 'europe': YEL, '12': YEL, 'pick': YEL}
CUES = [(0.0, 'whoosh', 0.35), (PED_T, 'thump', 0.25), (BANG, 'pop', 0.8), (BANG + 0.02, 'screech', 0.6), (HUM, 'hum', 0.9),
        (HUM + 1.0, 'hum', 0.6), (2.0, 'whoosh', 0.4), (2.3, 'pop', 0.4), (T2 + 0.12, 'pop', 0.7), (T2 + 0.35, 'thump', 0.4),
        (LAW - 0.3, 'whoosh', 0.6), (LAW, 'stamp', 1.0), (LAW + 0.02, 'boom', 0.7), (LAW + 0.12, 'stamp', 0.6),
        (T3, 'hum', 0.7), (T3 + 1.1, 'hum', 0.7), (ws(20) - 0.05, 'pop', 0.6), (BACK, 'pop', 0.6), (BACK + 0.05, 'screech', 0.25),
        (T4, 'whoosh', 0.5), (T4 + 0.35, 'thump', 0.4)] + [(T4 + 0.1 + 0.07 * k, 'click', 0.25) for k in range(int((US - T4 - 0.1) / 0.07))] + [
        (US, 'ding', 0.8), (US + 0.1, 'pop', 0.5), (POLL, 'pop', 0.7), (EU, 'ding', 0.8), (EU + 0.1, 'pop', 0.5),
        (T5 + 0.3, 'click', 0.5), (PULL, 'creak', 0.6), (PULL + 0.02, 'cha_ching', 0.4)] + [
        (PULL + 0.08 * k, 'click', 0.3) for k in range(int((STOPS[-1] - PULL) / 0.08))] + [
        (s, 'ding', 0.6) for s in STOPS] + [(STOPS[-1] + 0.05, 'confetti', 0.6), (STOPS[-1] + 0.1, 'sparkle', 0.6)]

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='blue', gauge=False, loud=True, crisp=True,
          end=False, flash=False, tag='corner')

if __name__ == '__main__':
    kit.main()
