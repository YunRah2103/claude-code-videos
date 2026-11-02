"""Renders 'How old are your tyres?': read the DOT date code (last four digits = week + year).

Template: videos/ac-idle shot structure on shared/episode.py (captions, progress bar, mixer). Looping format: no outro
card; the last shot replays the cold open's roll-in, so the last frame flows into frame 0. Voiceover: out/tyre-birthday/
voiceover.wav (clip 2 of out/voiceover/full_voiceover.wav, see ../../fuel-gauge-arrow/src/voiceover.py).
The age warning stays hedged ('tyres age, even if you barely drive'); no replacement age is stated anywhere.
Shots:
  1 cake     0.00  cold open: a tyre rolls in wearing a birthday cake with a lit candle; hairline cracks; he lands, shocked
  2 dot      2.55  sidewall close-up: DOT lights up, then the last four digits; real DOT photo; comment sticker
  3 code     7.55  '1822' splits into 18 = week and 22 = year; a calendar flips to week 18 of 2022
  4 age     10.45  the tyre sits on the drive, cracks creep, a clock spins, 'even if you barely drive'
  5 torch   11.80  he checks a tyre with a torch; share sticker
  6 loop    13.25  replays the cold-open roll-in, so the last frame matches frame 0
"""
import math, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
import episode as kit
from episode import W, H, S, GROUND, GAR, GLOW, RED, YEL, GRN, WHITE, layer, finish, draw_car, headline, sticker, title
from pixanim.motion import Track, prog, lerp, clamp, oc, ic, io, ob
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim import fx
from pixanim.fx import blit, popin, popout
from pixanim.grid import up, outline
from pixanim.autos import ptext

WORDS = kit.load_words(HERE)
DUR = 13.9
END_T = 13.25
def ws(i): return WORDS[i]['s']
HOOK = ((('How', None), ('OLD', '#ff5a5a'), ('are', None)), (('your tyres?', None),))
WIDE = False
RUB, RUB2, RUB_HI, RIMC = (30, 31, 37), (46, 48, 56), (70, 73, 84), (190, 196, 206)
CRACKS = [[(0.80, 0.05), (0.86, 0.12), (0.83, 0.2), (0.88, 0.27)], [(0.62, 1.9), (0.7, 2.0), (0.66, 2.1), (0.74, 2.22)],
          [(0.78, 3.3), (0.84, 3.38), (0.8, 3.5)], [(0.66, 4.3), (0.74, 4.4), (0.7, 4.52), (0.78, 4.6)],
          [(0.8, 5.4), (0.86, 5.5), (0.82, 5.6)], [(0.64, 1.0), (0.72, 1.1), (0.7, 1.2)]]


# ------------------------------------------------------------------ episode sprites
@lru_cache(None)
def tyre(rot=0, crack=0.0):
    """Side-on tyre (64x64): tread blocks, sidewall, five-spoke rim at angle `rot` (deg, step 10); hairline cracks 0..1."""
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(img); c = 31.5
    d.ellipse((0, 0, 63, 63), fill=RUB)
    for k in range(24):                                  # tread blocks turn with the wheel
        a = math.radians(rot + k * 15)
        x, y = c + 30 * math.cos(a), c + 30 * math.sin(a)
        d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=RUB2)
    d.ellipse((5, 5, 58, 58), fill=RUB2); d.arc((6, 6, 57, 57), 200, 290, fill=RUB_HI)
    d.ellipse((15, 15, 48, 48), fill=RIMC); d.ellipse((18, 18, 45, 45), fill=(140, 146, 158))
    for k in range(5):
        a = math.radians(rot + k * 72)
        d.line([(c, c), (c + 12 * math.cos(a), c + 12 * math.sin(a))], fill=RIMC, width=3)
    d.ellipse((28, 28, 35, 35), fill=(226, 230, 238))
    n = crack * len(CRACKS)
    for i, cr in enumerate(CRACKS):
        if i >= n: break
        part = min(1, n - i); pts = cr[:max(2, round(len(cr) * part))]
        d.line([(c + r * 31 * math.cos(a + math.radians(rot)), c + r * 31 * math.sin(a + math.radians(rot))) for r, a in pts], fill=(222, 226, 236), width=1)
    return outline(img)


@lru_cache(None)
def cake(ph=0):
    """Birthday cake (30x28) with one lit candle; flame flickers with phase 0..2."""
    img = Image.new('RGBA', (30, 28), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 25, 29, 27), fill=(226, 230, 238))
    d.rectangle((3, 14, 26, 25), fill=(244, 160, 190)); d.rectangle((3, 19, 26, 20), fill=(250, 240, 230))
    d.rectangle((3, 12, 26, 15), fill=(255, 248, 240))
    for x in (5, 10, 16, 22): d.rectangle((x, 15, x + 1, 16 + (x % 3)), fill=(255, 248, 240))
    for x in (6, 13, 20, 24): d.point((x, 22), fill=(255, 90, 90)); d.point((x + 2, 17), fill=(90, 180, 255))
    d.rectangle((14, 4, 15, 11), fill=(120, 200, 255)); d.point((14, 6), fill=WHITE); d.point((15, 9), fill=WHITE)
    fl = [(14, 0, 15, 3), (13, 0, 15, 3), (14, 0, 16, 3)][ph]
    d.ellipse(fl, fill=(255, 210, 63)); d.point((14 + (ph == 2), 2), fill=(255, 120, 40))
    return outline(img)


@lru_cache(None)
def sidewall(dot=0, num=0):
    """Sidewall close-up (160x52): a band of the tyre wall with raised lettering 'DOT 4B JX 1822'; dot/num highlight 0..2."""
    img = Image.new('RGBA', (160, 52), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.ellipse((-80, 8, 239, 327), fill=RUB); d.ellipse((-70, 16, 229, 317), fill=RUB2)
    d.arc((-70, 16, 229, 317), 220, 320, fill=RUB_HI)
    for k in range(13): d.rectangle((6 + k * 12, 10 + abs(k - 6) * 1.0, 10 + k * 12, 13 + abs(k - 6) * 1.0), fill=(40, 41, 48))
    def word(txt, x, y, hi):
        col = (255, 217, 59) if hi else (176, 180, 192)
        g = ptext(txt, col); g = g.resize((g.width * 2, g.height * 2), Image.NEAREST)
        if hi == 2:
            d.rounded_rectangle((x - 3, y - 3, x + g.width + 1, y + g.height + 1), 3, outline=(255, 217, 59))
        img.alpha_composite(g, (x, y))
        return x + g.width + 6
    x = word('DOT', 16, 24, dot)
    x = word('4B', x, 24, 0); x = word('JX', x, 24, 0) if WIDE else x
    word('1822', x + 2, 24, num)
    return img


@lru_cache(None)
def calendar(week, year):
    """Desk calendar page (44x46): red binder header 'WEEK', big week number, year underneath."""
    img = Image.new('RGBA', (44, 46), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 4, 43, 45), fill=(250, 250, 246)); d.rectangle((0, 4, 43, 13), fill=(214, 48, 58))
    for x in (9, 33): d.rectangle((x, 0, x + 1, 7), fill=(120, 124, 134))
    hw = ptext('WEEK', (255, 255, 255)); img.alpha_composite(hw, (22 - hw.width // 2, 5))
    n = ptext(str(week), (26, 26, 46)); n = n.resize((n.width * 2, n.height * 2), Image.NEAREST)
    img.alpha_composite(n, (22 - n.width // 2, 16))
    y = ptext(str(year), (214, 48, 58)); img.alpha_composite(y, (22 - y.width // 2, 35))
    return outline(img)


@lru_cache(None)
def clock(step=0):
    """Wall clock (24x24): minute hand at step*30 deg, hour hand at step*2.5 deg."""
    img = Image.new('RGBA', (24, 24), (0, 0, 0, 0)); d = ImageDraw.Draw(img); c = 11.5
    d.ellipse((0, 0, 23, 23), fill=(214, 48, 58)); d.ellipse((2, 2, 21, 21), fill=(250, 250, 246))
    for k in range(12):
        a = math.radians(k * 30); d.point((c + 8 * math.cos(a), c + 8 * math.sin(a)), fill=(26, 26, 46))
    for ang, ln, col in ((step * 30 - 90, 8, (26, 26, 46)), (step * 2.5 - 90, 5, (214, 48, 58))):
        a = math.radians(ang); d.line([(c, c), (c + ln * math.cos(a), c + ln * math.sin(a))], fill=col, width=1)
    return outline(img)


# ================================================================== shot 1: the birthday tyre rolls in
TS = 7                                                 # tyre scale (576 px)
LAND = 0.45
def tyre_x1(t): return lerp(1500, 540, oc(prog(t, -0.9, LAND + 0.9)))
def rot1(t): return round(-(tyre_x1(t) - 540) / (32 * TS) * 57.3 / 10) * 10
CR1 = ws(5)                                            # 'Bet': cracks start
P1 = Presenter([
    (-5, dict(path=Track([(1.1, (-200, 500)), (1.45, (170, GROUND), 'oc')]), size=6, legs='auto', arms='fly', expr='wow', face=1,
              ground=None, visible=False)),
    (1.1, dict(visible=True)),
    (1.45, dict(ground=GROUND, squash=True, arms='shock', expr='shock', look=(540, 800))),
    (2.0, dict(arms='point', point=(540, 900), expr='talk')),
], words=WORDS, base_size=6)
CAM1 = Camera(W, H, [(-2.0, (560, 960, 1.04)), (0.0, (560, 960, 1.08)), (LAND, (540, 960, 1.12), 'oc'), (2.6, (540, 980, 1.2), 'io')],
              kicks=[(LAND, 0.1, 540, 900), (CR1, 0.12, 540, 960), (1.45, 0.06, 170, 1100)], shakes=[(LAND, 0.25, 10), (CR1, 0.3, 8)])


def shot_cake(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    x = tyre_x1(t); bounce = 0 if t < LAND else 40 * abs(math.sin((t - LAND) * 9)) * math.exp(-(t - LAND) * 5)
    cr = clamp((t - CR1) / 0.9) if t >= CR1 else 0
    fx.contact_shadow(fg, x, GROUND, 520)
    blit(fg, up(tyre(rot1(t), round(cr * 12) / 12), TS), x, GROUND - bounce)
    cy = GROUND - 64 * TS + 14 - bounce * 1.4
    blit(fg, up(cake(int(t * 10) % 3), 9), x + 4 * math.sin(t * 6), cy, 1, 1, 6 * math.sin(t * 5) * (1 if t < LAND + 0.6 else 0.3))
    fx.sparkles(fg, t, x, cy - 260, 200, 120, n=4, seed=3)
    if t < LAND:
        fx.speed_lines(fg, 0.7 * (1 - prog(t, -0.9, LAND + 0.9)), int(t * 12) % 5, col=(200, 204, 220))
        for k in range(3): fx.puff(fg, t, -0.3 + k * 0.2, x + 300, GROUND - 20, seed=10 + k, drift=(260, -40))
    else:
        fx.dust(fg, t, LAND, x, GROUND, n=10, seed=11)
    if t >= CR1:
        fx.ring(fg, t, CR1, x, GROUND - 290, RED, r1=420); fx.burst(fg, t, CR1, x + 200, GROUND - 400, RED, n=10, seed=12)
    P1.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM1, t)


# ================================================================== shot 2: the sidewall code
T2 = 2.55
DOT_T, NUM_T = ws(12), ws(17)                          # 'DOT', 'last'
PH0, PH1 = DOT_T + 0.3, NUM_T - 0.05                  # photo on screen
CM0 = NUM_T + 0.7                                      # comment sticker
CAM2 = Camera(W, H, [(T2, (540, 900, 1.0)), (DOT_T, (500, 900, 1.06), 'io'), (NUM_T, (580, 900, 1.06), 'io'), (7.6, (560, 900, 1.04), 'io')],
              kicks=[(T2 + 0.05, 0.08, 540, 600), (DOT_T, 0.16, 270, 650), (NUM_T, 0.16, 774, 650)])


def shot_dot(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    dot = 2 if t >= DOT_T and int(t * 6) % 2 == 0 else int(t >= DOT_T)
    num = 2 if t >= NUM_T and int(t * 6) % 2 == 0 else int(t >= NUM_T)
    sw = up(sidewall(dot, num), 6)
    blit(fg, sw, 540, 780 + 6 * math.sin(t * 2))
    if t >= DOT_T:
        fx.ring(fg, t, DOT_T, 270, 650, GLOW, r1=300); fx.burst(fg, t, DOT_T, 270, 650, GLOW, n=10, seed=21)
    if t >= NUM_T:
        fx.ring(fg, t, NUM_T, 774, 650, RED, r1=360); fx.burst(fg, t, NUM_T, 774, 650, RED, n=12, seed=22)
        fx.sparkles(fg, t, 774, 650, 360, 160, n=6, seed=23)
        k = popin(t, NUM_T + 0.1)
        blit(fg, fx.big('badge', 'WEEK AND YEAR', '#ffd23f', '#1a1a2e', '#e8b923', s=7), 560, 880, k, k, 3 + 2 * math.sin(t * 4), anchor='center')
    img.alpha_composite(fg)
    return CAM2.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 3: 1822 = week 18 of 2022
T3 = 7.55
SPLIT, WK, YR = ws(30), ws(31), ws(33)                # 'week', '18', '2022'
CAM3 = Camera(W, H, [(T3, (540, 940, 1.0)), (SPLIT, (540, 940, 1.06), 'io'), (10.5, (540, 920, 1.1), 'io')],
              kicks=[(ws(28), 0.12, 540, 1070), (SPLIT, 0.1, 540, 1070), (WK, 0.12, 300, 1070), (YR, 0.12, 780, 1070)],
              shakes=[(ws(28), 0.2, 8)])


def shot_code(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    sp = oc(prog(t, SPLIT, 0.35))
    k0 = popin(t, ws(28) - 0.05, 0.25) * (fx.slam(t, ws(28) - 0.05, k=0.5))
    if k0 > 0:
        lx, rx = lerp(450, 280, sp), lerp(630, 800, sp)
        blit(fg, fx.big('badge', '18', '#ffd23f', '#1a1a2e', '#e8b923', s=16), lx, 1070, k0, k0, -3 * sp, anchor='center')
        blit(fg, fx.big('badge', '22', '#ffd23f', '#d6303a', '#e8b923', s=16), rx, 1070, k0, k0, 3 * sp, anchor='center')
        if t >= WK:
            kw = popin(t, WK)
            blit(fg, fx.big('label', 'WEEK', '#ffffff'), 280, 1225, kw, kw, anchor='center')
        if t >= YR:
            ky = popin(t, YR)
            blit(fg, fx.big('label', 'YEAR', '#ff5a5a'), 800, 1225, ky, ky, anchor='center')
    if t >= SPLIT - 0.1:                               # calendar flips through the weeks to 18, then shows 2022
        kc = popin(t, SPLIT - 0.1)
        wk = 18 if t >= WK else max(1, min(17, int(1 + (t - SPLIT) / (WK - SPLIT) * 17)))
        flip = (t - SPLIT) * 30 % 1 if t < WK else 0
        blit(fg, up(calendar(wk, 2022), 10), 540, 900 + 30 * flip, kc, kc * (1 - 0.3 * flip), -2 + 2 * math.sin(t * 3))
        if t >= WK: fx.burst(fg, t, WK, 540, 650, GLOW, n=12, seed=31); fx.ring(fg, t, WK, 540, 650, GLOW)
        if t >= YR: fx.confetti(fg, t, YR, 540, 500, n=26, seed=32)
    img.alpha_composite(fg)
    return CAM3.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 4: tyres age anyway
T4 = 10.45
CAM4 = Camera(W, H, [(T4, (540, 980, 1.08)), (11.8, (540, 1000, 1.22), 'io')],
              kicks=[(ws(36), 0.12, 540, 900), (ws(40), 0.1, 540, 900)])


def shot_age(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    cr = clamp((t - T4 - 0.1) / 1.2)
    fx.contact_shadow(fg, 540, GROUND, 520)
    blit(fg, up(tyre(0, round(cr * 12) / 12), TS), 540, GROUND)
    for k in range(int(cr * 6)):
        fx.dust(fg, t, T4 + 0.2 + k * 0.2, 540 + 180 * math.cos(k * 1.7), GROUND - 300 + 150 * math.sin(k * 2.3), n=4, seed=40 + k)
    kc = popin(t, T4 + 0.05)
    step = int((t - T4) * 14)
    blit(fg, up(clock(step % 120), 10), 220, 640, kc, kc, 4 * math.sin(t * 12) * clamp(t - T4), anchor='center')
    fx.speed_lines(fg, 0.25, int(t * 12) % 5, col=(120, 124, 140))
    img.alpha_composite(fg)
    return CAM4.apply(img.convert('RGB'), t, (14, 15, 18))


# ================================================================== shot 5: the torch check
T5 = 11.80
P5 = Presenter([
    (T5, dict(path=Track([(T5, (1300, 500)), (T5 + 0.35, (820, GROUND), 'oc')]), size=7, legs='auto', arms='fly', expr='grin', face=-1, ground=None)),
    (T5 + 0.35, dict(ground=GROUND, squash=True, arms='point', point=(380, GROUND - 260), look=(380, GROUND - 260), expr='think')),
    (T5 + 1.0, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
], words=WORDS, base_size=7)
CAM5 = Camera(W, H, [(T5, (540, 980, 1.12)), (END_T, (520, 1000, 1.2), 'io')], kicks=[(T5 + 0.35, 0.08, 820, 1100), (T5 + 0.5, 0.1, 380, 950)])


def shot_torch(t):
    img = GAR.frame(t).convert('RGBA'); fg = layer()
    fx.contact_shadow(fg, 380, GROUND, 420)
    blit(fg, up(tyre(0, 0.6), 7), 380, GROUND)
    if t >= T5 + 0.4:                                  # torch beam from his hand onto the sidewall
        a = 90 * clamp((t - T5 - 0.4) / 0.15) * (1 if t < T5 + 1.0 else popout(t, T5 + 1.0, 0.2))
        ImageDraw.Draw(fg).polygon([(740, GROUND - 250), (330, GROUND - 400), (330, GROUND - 120)], fill=(255, 244, 190, int(a)))
        blit(fg, up(sidewall(1, 2), 3), 380, GROUND - 170, 1, 1, 0, anchor='center') if t < T5 + 1.0 else None
        fx.sparkles(fg, t, 380, GROUND - 260, 300, 200, n=5, seed=51)
    P5.draw(fg, t)
    GAR.reflect(img, fg)
    return finish(img, fg, CAM5, t)


def shot_loop(t): return shot_cake(t - DUR)


def overlay(cv, t):
    headline(cv, t, 2.35, HOOK, y=360, sz=104)
    if t >= END_T and t - DUR > -0.45: headline(cv, max(-0.35, t - DUR), 2.35, HOOK, y=360, sz=104)
    kit.photo_hq(cv, t, PH0, PH1, 'dot_code', 540, 1040, 660, rot=-3, label='A REAL DOT CODE')
    sticker(cv, t, CM0, T3 - 0.1, ('Reply with YOUR tyre\'s', '4-digit code below'), 1130, rot=-2)
    title(cv, t, ws(37), T5 - 0.1, 'even if you barely drive', WHITE, 400, 84, -2)
    sticker(cv, t, T5 + 0.1, END_T - 0.05, ('Send this to someone', 'who never checks.'), 520, rot=2)


SHOTS = [(-3.0, shot_cake), (T2, shot_dot), (T3, shot_code), (T4, shot_age), (T5, shot_torch), (END_T, shot_loop)]
TRANS = {1: (T2, T2 + 0.2, 'whip', dict(dx=0, dy=1)), 2: (T3, T3 + 0.2, 'push', None), 3: (T4, T4 + 0.2, 'whip', dict(dx=1)),
         4: (T5, T5 + 0.2, 'push', None), 5: (END_T, END_T + 0.2, 'whip', dict(dx=-1))}
KEYCOL = {'old': RED, 'checked': YEL, 'dot': YEL, 'four': RED, 'numbers': RED, '1822': RED, '18': YEL, '2022': RED, 'age,': RED, 'age': RED, 'week': YEL, 'year': RED}
CUES = [(0.0, 'whoosh', 0.6), (LAND, 'thump', 0.7), (LAND + 0.02, 'pop', 0.4), (CR1, 'creak', 0.7), (CR1 + 0.05, 'crash', 0.25),
        (1.45, 'thump', 0.4), (DOT_T, 'ding', 0.7), (DOT_T + 0.02, 'sparkle', 0.5), (PH0, 'pop', 0.7), (NUM_T, 'ding', 0.8),
        (NUM_T + 0.1, 'pop', 0.5), (CM0, 'pop', 0.7), (ws(28) - 0.05, 'stamp', 0.7), (SPLIT, 'whoosh', 0.5)] + [
        (SPLIT + 0.04 * k, 'click', 0.3) for k in range(int((WK - SPLIT) / 0.04))] + [
        (WK, 'ding', 0.8), (YR, 'cha_ching', 0.6), (YR + 0.02, 'confetti', 0.5), (T4 + 0.05, 'pop', 0.5)] + [
        (T4 + 0.15 + 0.12 * k, 'click', 0.35) for k in range(11)] + [
        (ws(37), 'pop', 0.5), (T5 + 0.35, 'thump', 0.4), (T5 + 0.4, 'click', 0.7), (T5 + 1.0, 'ding', 0.6), (T5 + 0.1, 'pop', 0.6)]

kit.setup(HERE, WORDS, DUR, END_T, SHOTS, TRANS, CUES, KEYCOL, overlay=overlay, bar_car='silver', gauge=False, loud=True, crisp=True,
          end=False, flash=False, tag='corner')

if __name__ == '__main__':
    kit.main()
