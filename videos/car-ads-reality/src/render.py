"""Car Ads vs Reality: long-form landscape episode (1920x1080 @30) + vertical Shorts (1080x1920).
Reuses the series cast rig (person(), D, easing, sfx) from bmw-heated-seats/src/render.py; the buyer is the series
buyer, the salesman gets a new look (silver slick hair, moustache, bow tie, burgundy suit) for this episode.
Each claim: whip to an original parody-ad cutaway (our style, claim text only) -> whip to a location where the real
CC-licensed photo plays on a screen behind the cast. Running gag: the fine print (an asterisk) grows every scene.
Usage: python render.py video VOICE.wav OUT.mp4 | still T OUT.png [VOICE] | sheet OUT.png [VOICE] | meta OUT.json
       python render.py short N VOICE.wav OUT.mp4 | shortstill N T OUT.png [VOICE] | thumb OUT.png | sthumb N OUT.png"""
import importlib.util, json, math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_spec = importlib.util.spec_from_file_location('series', os.path.join(HERE, '..', '..', 'bmw-heated-seats', 'src', 'render.py'))
R = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(R)
import sfx
from script import LINES as SLINES
D, font, person, POSES, OUTBEND, ik, spline = R.D, R.font, R.person, R.POSES, R.OUTBEND, R.ik, R.spline
clamp, prog, oc, io, ob, popin, window, mix, hexc, OL = R.clamp, R.prog, R.oc, R.io, R.ob, R.popin, R.window, R.mix, R.hexc, R.OL
FONT_B, FONT_X = R.FONT_B, R.FONT_X

W, H, FPS, K = 1920, 1080, 30, 2
SW, SH = 1080, 1920                                         # Shorts
ASSETS, MUSIC = os.path.join(HERE, '..', 'assets'), os.path.join(HERE, '..', 'music')
WORDS = json.load(open(os.path.join(HERE, 'words.json')))
VOICE_CACHE = os.path.expanduser('~/.cache/car-ads-reality/voice.wav')
TAG, RED, GREEN, INK = (255, 214, 64), (226, 48, 58), (70, 200, 120), (20, 18, 24)

# ================================================================ timeline
LN = {}
for w in WORDS: LN.setdefault(w['line'], []).append(w)
LS = {k: v[0]['s'] for k, v in LN.items()}
LE = {k: v[-1]['e'] for k, v in LN.items()}
NSC = max(SLINES[k][2] for k in LN) + 1                     # scenes actually voiced
SC_LINES = {s: [k for k in sorted(LN) if SLINES[k][2] == s] for s in range(NSC)}
HAS_END = NSC == 9
def wt(line, txt, nth=0):
    hits = [w['s'] for w in LN[line] if txt.lower() in w['w'].lower()]
    return hits[nth] if hits else LS[line]
TR = 0.36                                                   # whip length
AD, LOC = {}, {}                                            # per scene: parody-ad window, location start
for s in range(NSC):
    f0 = LS[SC_LINES[s][0]]
    if s == 0:
        LOC[s] = 0.0
    elif s == 8:
        LOC[s] = LE[SC_LINES[7][-1]] + 0.45
    else:
        a0 = LE[SC_LINES[s - 1][-1]] + 0.45
        AD[s] = (a0, f0 - 0.5)
        LOC[s] = f0 - 0.5
END_T = LE[max(LN)]
T_CARD = END_T + (0.35 if HAS_END else 2.6)               # no voiced ending: hold on the buyer buried in fine print
DUR = round(T_CARD + (3.2 if HAS_END else 3.8), 2)
CUTS = sorted([a for a, _ in AD.values()] + list(LOC.values())[1:])
def seg_at(t):
    """('ad', s) or ('loc', s)."""
    best = ('loc', 0); bt = -1
    for s, (a0, a1) in AD.items():
        if a0 <= t and a0 > bt: best, bt = ('ad', s), a0
    for s, l0 in LOC.items():
        if l0 <= t and l0 >= bt: best, bt = ('loc', s), l0
    return best
def lines_of(s): return SC_LINES.get(s, [])

# ================================================================ scene data (facts: see ../FACTS.md)
SCN = [
    dict(loc='showroom', photo='maverick', brand='FORD', model='Ford Maverick', ad=('STARTING AT', '$28,145'),
         says=('THE AD', 'Starting MSRP $28,145'), real=("FORD'S FOOTNOTE", 'Excludes destination/delivery,', 'taxes and fees'),
         music='Monkeys_Spinning_Monkeys', fact_line=3),
    dict(loc='pump', photo='corolla', brand='TOYOTA', model='Toyota Corolla Hybrid', ad=('UP TO', '50 MPG'),
         says=('THE AD', 'Up to 50 mpg combined'), real=('EPA (fueleconomy.gov)', 'FWD: 50 combined', 'SE AWD: 44 combined'),
         music='Fluffing_a_Duck', fact_line=10),
    dict(loc='showroom', photo='elantra', brand='HYUNDAI', model='Hyundai', ad=("AMERICA'S BEST", 'WARRANTY'),
         says=('THE AD', '10-yr / 100,000-mi powertrain'), real=("HYUNDAI'S TERMS", 'Original owner only.', 'Next owner: 5-yr / 60,000-mi'),
         music='Pixel_Peeker_Polka_-_faster', fact_line=17),
    dict(loc='strip', photo='plaid', brand='TESLA', model='Tesla Model S Plaid', ad=('0-60 MPH', '1.99 s'),
         says=('THE AD', '0-60 mph in 1.99 s'), real=('THE FOOTNOTE', '1-ft rollout subtracted.', 'MotorTrend, from 0: 2.28 s'),
         music='Sneaky_Snitch', fact_line=22),
    dict(loc='towlot', photo='f150', brand='FORD', model='Ford F-150', ad=('MAX TOWING', '13,500 LBS'),
         says=('THE AD', '13,500 lbs max available towing'), real=("FORD'S TOWING GUIDE", '3.5L + Tow/Haul + Max Tow Axle.', 'Standard 2.7L: up to 8,400'),
         music='Monkeys_Spinning_Monkeys', fact_line=34),
    dict(loc='charger', photo='lightning', brand='FORD', model='Ford F-150 Lightning', ad=('RANGE', '320 MILES'),
         says=('THE AD', '320 mi EPA est. (extended range)'), real=('CONSUMER REPORTS', 'Steady 70 mph: 270 mi.', '22 EVs: nearly half fell short'),
         music='Investigations', fact_line=42),
    dict(loc='stage', photo='charger', brand='DODGE', model='Dodge Charger Daytona', ad=('FRATZONIC', 'EXHAUST'),
         says=('THE AD', 'Fratzonic Chambered Exhaust'), real=('DODGE', 'Amplifier + tuning chamber.', 'Up to 126 dB'),
         music='Volatile_Reaction', fact_line=51),
    dict(loc='track', photo='model3', brand='TESLA', model='Tesla', ad=('FULL', 'SELF-DRIVING'),
         says=('THE AD', 'Full Self-Driving'), real=('TESLA', '(Supervised). Requires active', 'supervision. Not autonomous.'),
         music='Volatile_Reaction', fact_line=61),
    dict(loc='showroom', photo=None, brand='', model='', music='Local_Forecast_-_Elevator', fact_line=None),
]
ONSCREEN = []
for s_ in SCN[:8]:
    ONSCREEN += [s_['ad'][0], s_['ad'][1] + '*', s_['says'][0], s_['says'][1], *s_['real']]

# ================================================================ scaled drawing
class DS(D):
    """D with a uniform scale + offset: design (x, y) -> frame (x*s + tx, y*s + ty)."""
    def __init__(self, img, s=1.0, tx=0.0, ty=0.0):
        super().__init__(img); self.s, self.tx, self.ty = s, tx, ty; self.k = K * s
    def p(self, x, y): return ((x * self.s + self.tx) * K, (y * self.s + self.ty) * K)

@lru_cache(None)
def photo(name, w, h):
    """Centre-cropped photo at frame size w x h (K-scaled)."""
    ph = Image.open(os.path.join(ASSETS, name + '.jpg')).convert('RGB')
    r = w / h
    if ph.width / ph.height > r:
        nw = int(ph.height * r); x0 = (ph.width - nw) // 2; ph = ph.crop((x0, 0, x0 + nw, ph.height))
    else:
        nh = int(ph.width / r); y0 = (ph.height - nh) // 2; ph = ph.crop((0, y0, ph.width, y0 + nh))
    return ph.resize((int(w * K * 1.12), int(h * K * 1.12)), Image.LANCZOS)

def screen_photo(img, name, x0, y0, x1, y1, t, t0):
    """Real photo on an in-scene screen with a slow Ken Burns drift and a scanline sheen."""
    w, h = x1 - x0, y1 - y0
    ph = photo(name, w, h)
    k = clamp((t - t0) / 12)
    ox = int((ph.width - w * K) * (0.15 + 0.7 * k)); oy = int((ph.height - h * K) * 0.5)
    crop = ph.crop((ox, oy, ox + w * K, oy + h * K))
    img.paste(crop, (int(x0 * K), int(y0 * K)))
    d = D(img)
    d.rect(x0, y0, x1, y0 + 6, (255, 255, 255, 40))

def bezel(d, x0, y0, x1, y1, r=10):
    d.rect(x0 - 14, y0 - 14, x1 + 14, y1 + 14, (18, 18, 22), r=r + 8)
    d.rect(x0 - 4, y0 - 4, x1 + 4, y1 + 4, (40, 42, 50), r=r)

def grad(w, h, c0, c1):
    a = np.linspace(0, 1, h)[:, None, None]
    g = (np.array(c0)[None, None] * (1 - a) + np.array(c1)[None, None] * a).repeat(w, 1)
    return Image.fromarray(g.astype(np.uint8), 'RGB').convert('RGBA')

def poster(d, x, y, w, h, bg, lines, rot_col=(30, 30, 36)):
    d.rect(x + 6, y + 8, x + w + 6, y + h + 8, (0, 0, 0, 60), r=6)
    d.rect(x, y, x + w, y + h, bg, r=6, ol=rot_col, w=4)
    n = len(lines); yy = y + h / (n + 1)
    for txt, size, col in lines:
        while R.font(size * K).getlength(txt) / K > w - 24: size -= 1
        d.text(x + w / 2, yy, txt, size, col); yy += h / (n + 1)

# ================================================================ backgrounds (static, cached; K-scaled RGBA)
FLOOR = 900
SCREENS = {'showroom': (720, 150, 1200, 420), 'pump': (1300, 150, 1700, 380), 'strip': (760, 110, 1160, 330),
           'towlot': (1440, 110, 1860, 350), 'charger': (130, 120, 590, 380), 'stage': (720, 90, 1200, 360),
           'track': (1320, 110, 1760, 360)}

@lru_cache(None)
def bg(loc):
    img = Image.new('RGBA', (W * K, H * K)); d = D(img)
    if loc == 'showroom':
        img.paste(grad(W * K, H * K, (226, 232, 242), (196, 204, 220)), (0, 0))
        for i in range(5):                                   # tall windows with sky + city
            x0 = 40 + i * 380
            if 600 < x0 < 1300: continue
            d.rect(x0, 70, x0 + 300, 640, (150, 196, 236))
            d.rect(x0, 420, x0 + 300, 640, (176, 210, 238))
            for j in range(5):
                bx = x0 + 10 + j * 58; bh = 90 + (j * 53 + i * 31) % 120
                d.rect(bx, 640 - bh, bx + 44, 640, (126, 150, 180))
            d.rect(x0, 70, x0 + 300, 640, None, ol=(230, 234, 240), w=12)
            d.line([(x0 + 150, 70), (x0 + 150, 640)], (230, 234, 240), 8)
        d.rect(0, 640, W, 668, (238, 240, 246))                 # window ledge
        d.rect(0, 668, W, FLOOR, (214, 220, 232))
        img.paste(grad(W * K, (H - FLOOR) * K, (176, 184, 200), (120, 128, 146)), (0, FLOOR * K))
        for i in range(9): d.line([(i * 240 - 200, H), (W / 2 + (i - 4) * 60, FLOOR)], (200, 206, 220, 70), 3)
        d.rect(640, 60, 1280, 500, (60, 64, 78), r=16)            # feature wall + screen
        bezel(d, *SCREENS['showroom'])
        poster(d, 690, 520, 250, 120, (255, 248, 230), [('EMPLOYEE OF THE MONTH', 15, INK), ('*', 58, (220, 160, 20))])
        poster(d, 980, 520, 250, 120, (30, 34, 44), [('DAYS SINCE LAST', 16, (230, 230, 236)), ('FOOTNOTE: 0', 30, TAG)])
        d.ell(1520, 210, 70, 70, (250, 250, 252), (40, 40, 50), 8)    # clock with an asterisk for twelve
        d.text(1520, 158, '*', 40, INK)
        for a_ in range(1, 12):
            d.ell(1520 + 52 * math.sin(a_ * math.pi / 6), 210 - 52 * math.cos(a_ * math.pi / 6), 4, 4, INK)
        poster(d, 1640, 300, 200, 260, (212, 40, 50), [('NO', 40, (255, 255, 255)), ('HAGGLING*', 30, (255, 255, 255)),
                                                       ('*haggling sold', 14, (255, 220, 220)), ('separately', 14, (255, 220, 220))])
        for px_ in (90, 1830):                                   # plants
            d.rect(px_ - 34, 800, px_ + 34, 900, (230, 232, 238), r=8, ol=(120, 124, 140), w=3)
            for k_ in range(7):
                a_ = -1.2 + k_ * .4
                d.ell(px_ + 70 * math.sin(a_), 760 - 60 * math.cos(a_), 26, 50, (60, 150, 90))
    elif loc == 'pump':
        img.paste(grad(W * K, H * K, (255, 190, 120), (120, 140, 200)), (0, 0))
        d.ell(300, 420, 120, 120, (255, 236, 170))
        for i in range(12): d.rect(i * 170, 560 - (i * 37) % 90, i * 170 + 140, 700, (90, 96, 130))
        d.rect(0, 700, W, H, (70, 74, 86))
        for i in range(10): d.rect(i * 220, 980, i * 220 + 120, 994, (236, 210, 90))
        d.rect(80, 120, 1840, 190, (236, 64, 60), r=6); d.rect(80, 190, 1840, 210, (200, 200, 206))
        d.text(560, 156, 'GAS  +  SNACKS  +  REALITY', 44, (255, 255, 255))
        for x_ in (200, 1760): d.rect(x_ - 24, 210, x_ + 24, 900, (220, 222, 228))
        bezel(d, *SCREENS['pump'])
        for x_ in (300, 1600):                                   # pumps
            d.rect(x_ - 70, 520, x_ + 70, 900, (240, 240, 244), r=14, ol=(60, 60, 70), w=5)
            d.rect(x_ - 50, 560, x_ + 50, 640, (30, 40, 50), r=6)
            d.text(x_, 600, '88.8', 36, (120, 255, 160))
            d.line([(x_ + 70, 700), (x_ + 110, 740), (x_ + 100, 860)], (30, 30, 34), 10)
        poster(d, 830, 420, 260, 120, (255, 255, 255), [('MPG MAY VARY', 22, INK), ('mostly downward', 16, (180, 40, 40))])
    elif loc == 'strip':
        img.paste(grad(W * K, H * K, (120, 180, 240), (230, 240, 250)), (0, 0))
        for i in range(30): d.rect(i * 66, 520, i * 66 + 60, 640, mix((200, 60, 60), (60, 90, 200), (i % 5) / 4))   # stands crowd
        d.rect(0, 500, W, 520, (90, 94, 110))
        d.rect(0, 640, W, H, (88, 90, 98))
        d.poly([(560, 640), (1360, 640), (2300, H), (-380, H)], (60, 62, 70))
        d.rect(950, 640, 970, H, (240, 240, 240))
        d.rect(0, 860, W, 876, (255, 255, 255))                   # start line
        bezel(d, *SCREENS['strip'])
        d.rect(1600, 360, 1640, 900, (40, 40, 46))               # christmas tree
        for j in range(5):
            for s_ in (-1, 1): d.ell(1620 + s_ * 40, 400 + j * 70, 18, 18, (50, 50, 56), (20, 20, 24), 3)
        poster(d, 120, 300, 300, 140, (20, 20, 24), [('TIMING STARTS', 24, TAG), ('EVENTUALLY', 30, (255, 255, 255))])
        d.rect(1240, 150, 1480, 240, (20, 20, 24), r=8); d.text(1360, 195, '0.00', 52, (255, 70, 60))
    elif loc == 'towlot':
        img.paste(grad(W * K, H * K, (130, 190, 240), (236, 230, 210)), (0, 0))
        d.poly([(0, 560), (300, 330), (520, 470), (800, 280), (1100, 500), (1400, 340), (1920, 560)], (150, 160, 180))
        d.poly([(300, 330), (360, 380), (240, 390)], (250, 250, 255)); d.poly([(800, 280), (870, 340), (730, 340)], (250, 250, 255))
        d.rect(0, 560, W, H, (176, 160, 130))
        for i in range(40): d.ell((i * 97) % W, 600 + (i * 53) % 400, 8, 4, (150, 136, 110))
        bezel(d, *SCREENS['towlot'])
        d.rect(1640, 350, 1660, 600, (80, 80, 86))
        d.rect(60, 640, 470, 700, (110, 70, 40)); d.rect(80, 700, 100, 800, (110, 70, 40)); d.rect(430, 700, 450, 800, (110, 70, 40))
        poster(d, 70, 560, 390, 80, (255, 255, 255), [('MAX TOW: ASK THE AXLE', 26, INK)])
    elif loc == 'charger':
        img.paste(grad(W * K, H * K, (60, 50, 110), (250, 140, 90)), (0, 0))
        for i in range(60): d.ell((i * 331) % W, (i * 137) % 400, 2, 2, (255, 255, 255, 180))
        d.rect(0, 620, W, H, (54, 56, 66))
        d.rect(0, 700, W, 760, (40, 42, 50)); [d.rect(i * 200, 726, i * 200 + 100, 734, (230, 220, 120)) for i in range(10)]
        bezel(d, *SCREENS['charger'])
        d.rect(350, 380, 370, 620, (80, 80, 90))
        for x_ in (1500, 1760):                                  # chargers
            d.rect(x_ - 50, 500, x_ + 50, 900, (236, 240, 246), r=18, ol=(40, 44, 60), w=5)
            d.rect(x_ - 32, 540, x_ + 32, 610, (40, 200, 140), r=8)
            d.line([(x_ + 50, 640), (x_ + 90, 700), (x_ + 70, 880)], (24, 24, 30), 9)
        poster(d, 700, 440, 300, 110, (255, 255, 255), [('RANGE: VIBES', 34, INK), ('results may vary at 70', 14, (160, 40, 40))])
    elif loc == 'stage':
        img.paste(grad(W * K, H * K, (20, 16, 30), (60, 30, 70)), (0, 0))
        for i in range(7): R.spot(img, 200 + i * 260, 0, 30, 220, 900, 28) if hasattr(R, 'spot') else None
        d = D(img)
        d.rect(0, 860, W, H, (30, 26, 36))
        bezel(d, *SCREENS['stage'])
        for x_ in (300, 1620):                                   # speaker stacks
            for j in range(3):
                y_ = 420 + j * 160
                d.rect(x_ - 130, y_, x_ + 130, y_ + 150, (24, 24, 28), r=10, ol=(70, 70, 80), w=4)
                d.ell(x_, y_ + 75, 56, 56, (50, 50, 56), (90, 90, 100), 6); d.ell(x_, y_ + 75, 18, 18, (80, 80, 90))
        poster(d, 760, 420, 400, 90, (240, 30, 40), [('QUIET PLEASE  (126 dB)', 30, (255, 255, 255))])
    elif loc == 'track':
        img.paste(grad(W * K, H * K, (150, 200, 250), (210, 236, 250)), (0, 0))
        for i in range(6): d.ell(200 + i * 330, 600, 220, 90, (110, 180, 110))
        d.rect(0, 600, W, H, (120, 176, 100))
        d.poly([(820, 600), (1100, 600), (1900, H), (0, H)], (80, 82, 90))
        for i in range(6): d.rect(940 - i * 4, 620 + i * 80, 980 + i * 4, 650 + i * 90, (240, 240, 240))
        bezel(d, *SCREENS['track'])
        for i, (cx_, cy_) in enumerate(((700, 700), (1220, 700), (560, 820), (1380, 820))):
            d.poly([(cx_ - 30, cy_ + 40), (cx_ + 30, cy_ + 40), (cx_, cy_ - 40)], (255, 120, 30), (60, 30, 10), 3)
            d.rect(cx_ - 16, cy_ - 8, cx_ + 16, cy_ + 4, (255, 255, 255))
        poster(d, 120, 260, 360, 140, (255, 255, 255), [('TEST TRACK', 30, INK), ('hands on the wheel, please', 18, (160, 40, 40))])
    return img

# ================================================================ cast
BUYER = dict(R.BUYER)
SALES = dict(skin=hexc('8d5a3b'), skin2=hexc('6f4430'), hair=hexc('c9ccd4'), suit=hexc('6e1f2e'), suit2=hexc('4a1220'),
             shirt=hexc('f3ead2'), tie=None, pants=hexc('2a1a20'), shoe=hexc('1a1412'), glasses=False, hairstyle='part',
             lids=0.55, badge=False)
CAST_S = 0.7
BX, SX = 600, 1330                                          # buyer / salesman floor x

def hand_pos(x, fy, st, side, s=CAST_S, dy=0):
    top = fy - 800 + dy
    S = (x + side * 108, top + 30)
    key = 'lpose' if side < 0 else 'rpose'
    ox, oy = st[key]
    E, T = ik(S, (S[0] + side * ox, S[1] + oy), side, st.get('out_' + key, False))
    dx, dy_ = T[0] - E[0], T[1] - E[1]; n = math.hypot(dx, dy_) or 1
    return T[0] + dx / n * 10, T[1] + dy_ / n * 10

def sales_extras(d, x, fy, st):
    """New-look salesman: moustache + bow tie + a silver quiff, on top of the series rig."""
    top = fy - 800 + st.get('dy', 0); hx = x + st.get('look', 0) * 0.3; hy = top - 105
    d.poly([(x - 34, top - 22), (x - 2, top - 8), (x - 34, top + 6)], (200, 160, 40), OL, 3)
    d.poly([(x + 34, top - 22), (x + 2, top - 8), (x + 34, top + 6)], (200, 160, 40), OL, 3)
    d.ell(x, top - 8, 8, 8, (170, 130, 30), OL, 3)
    m = st.get('mouth', 0.0)
    my = hy + 34 - (3 if m > .08 else 0)
    d.poly(spline([(hx - 34, my + 6), (hx - 18, my - 6), (hx, my - 2), (hx + 18, my - 6), (hx + 34, my + 6), (hx, my + 4)], 5),
           (200, 202, 210), OL, 3)
    d.poly(spline([(hx - 60, hy - 64), (hx - 20, hy - 112), (hx + 40, hy - 108), (hx + 70, hy - 70), (hx + 20, hy - 84)], 5),
           SALES['hair'], OL, 3)

def buyer_extras(d, x, fy, st, sc, t):
    if st.get('ads'):                                       # the stack of ads in his left hand
        hx, hy = hand_pos(x, fy, st, -1, dy=st.get('dy', 0))
        for k_ in range(4):
            d.rect(hx - 70 + k_ * 5, hy - 96 - k_ * 6, hx + 30 + k_ * 5, hy + 30 - k_ * 6, (252, 252, 246), r=3, ol=(90, 90, 100), w=2)
        d.text(hx - 18, hy - 50 - 18, 'AD', 26, RED)

# ---- performance schedules built from the script: buyer escalates scene by scene, salesman stays flat
def buyer_sched():
    s = [(0.0, 'up', 'up', dict(brows='up', eyes='wide', smile=1, ads=1))]
    for li in sorted(LN):
        spk, txt, sc = SLINES[li]
        if spk != 'B': continue
        heat = sc / 7.0
        shout = txt.count('!') + 2 * txt.count('?!') + sum(1 for w in txt.split() if w.isupper() and len(w) > 2)
        if sc == 8:
            ex = dict(brows='worried', tired=0.55, smile=-1); g = ('rest', 'rest')
        elif shout >= 3 or ('?!' in txt and sc >= 3):
            ex = dict(brows='angry', eyes='wide', sweat=1 if sc >= 4 else 0); g = ('up', 'up') if li % 2 else ('head', 'head')
        elif '?' in txt:
            ex = dict(brows='worried', eyes='wide' if heat > .4 else None); g = ('shrug', 'shrug')
        elif '!' in txt:
            ex = dict(brows='up' if sc < 3 else 'angry', eyes='wide', smile=1 if sc < 2 else 0); g = ('point', 'up') if li % 2 else ('rest', 'point')
        else:
            ex = dict(brows='flat', tired=0.2 + .3 * heat); g = ('rest', 'chin')
        ex = {k: v for k, v in ex.items() if v}
        if sc == 0: ex['ads'] = 1
        s.append((LS[li] - .08, g[0], g[1], ex))
        s.append((LE[li] + .25, 'cross' if sc >= 4 else 'rest', 'cross' if sc >= 4 else 'rest',
                  dict(brows='angry' if sc >= 3 else 'flat', smile=-1 if sc >= 2 else 0, **({'ads': 1} if sc == 0 else {}))))
    s.insert(1, (0.18, 'rest', 'rest', dict(brows='up', eyes='wide', smile=1, ads=1)))   # the slam
    return sorted(s, key=lambda e: e[0])

def sales_sched():
    s = [(0.0, 'clasp', 'clasp', dict(blink=1, brows='worried'))]   # already wincing on frame 1
    s.append((0.9, 'clasp', 'clasp', {}))
    G = ['open', 'present', 'offer', 'shrug', 'open']
    for i, li in enumerate(k for k in sorted(LN) if SLINES[k][0] == 'S'):
        g = G[i % len(G)]
        if SLINES[li][2] == 8 and li == max(LN): g = 'open'
        s += [(LS[li] - .06, g, 'clasp', {}), (LE[li] + .25, 'clasp', 'clasp', {})]
    return sorted(s, key=lambda e: e[0])
BS, SS_ = buyer_sched(), sales_sched()
def pose_at(sched, t, tr=0.18):
    i = max(j for j, e in enumerate(sched) if e[0] <= t)
    cur, prev = sched[i], sched[max(0, i - 1)]
    k = io(prog(t, cur[0], tr))
    lp = [a + (b - a) * k for a, b in zip(POSES[prev[1]], POSES[cur[1]])]
    rp = [a + (b - a) * k for a, b in zip(POSES[prev[2]], POSES[cur[2]])]
    src = cur if k > 0.5 else prev
    ex = dict(src[3]); ex['out_lpose'], ex['out_rpose'] = src[1] in OUTBEND, src[2] in OUTBEND
    return lp, rp, ex

MOUTH = None
def load_mouth(voice):
    global MOUTH
    raw = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', voice, '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'],
                                       capture_output=True, check=True).stdout, np.float32)
    n = int(DUR * FPS) + 2; hop = 48000 // FPS
    rms = np.array([np.sqrt((np.mean(raw[i * hop:(i + 1) * hop] ** 2) if i * hop < len(raw) else 0) + 1e-9) for i in range(n)])
    lev = np.clip((20 * np.log10(rms) + 38) / 22, 0, 1)
    M = {'S': np.zeros(n), 'B': np.zeros(n)}
    for w in WORDS:
        a, b = int((w['s'] - .03) * FPS), int((w['e'] + .03) * FPS) + 1
        M[w['spk']][a:b] = lev[a:b]
    f = np.arange(n)
    for k_ in M: M[k_] = M[k_] * (0.75 + 0.25 * np.abs(np.sin(f * 1.9)))
    MOUTH = M
def talking(spk, t): return any(w['spk'] == spk and w['s'] - .05 <= t <= w['e'] + .05 for w in WORDS)

# ================================================================ running gag: the fine print
def asterisk(d, x, y, r, t, face=True, col=(255, 200, 40), rot=0.0):
    pts = []
    for i in range(12):
        a_ = rot + i * math.pi / 6; rr = r if i % 2 == 0 else r * .5
        pts.append((x + rr * math.cos(a_), y + rr * math.sin(a_)))
    d.poly(pts, col, OL, max(3, r * .06))
    if face:
        bl = (t % 2.7) < .12
        for s_ in (-1, 1):
            if bl: d.line([(x + s_ * r * .2 - r * .08, y - r * .08), (x + s_ * r * .2 + r * .08, y - r * .08)], OL, max(2, r * .05))
            else: d.ell(x + s_ * r * .2, y - r * .08, r * .07, r * .1, OL)
        d.arc(x, y + r * .02, r * .2, r * .14, 20, 160, OL, max(2, r * .05))

def fine_lines(d, x0, y0, x1, y1, a=255, size=13, seed=0):
    """Rows of unreadable fine print."""
    rng = np.random.default_rng(seed); y = y0
    while y < y1:
        x = x0
        while x < x1 - 20:
            wl = rng.integers(14, 60); d.rect(x, y, min(x1, x + wl), y + size * .45, (40, 40, 48, a)); x += wl + 8
        y += size * .9

def scroll(d, x, y0, y1, w, seed=0):
    d.rect(x - w / 2, y0, x + w / 2, y1, (252, 250, 240), ol=(120, 110, 90), w=3)
    fine_lines(d, x - w / 2 + 10, y0 + 10, x + w / 2 - 10, y1 - 10, 200, 12, seed)
    d.ell(x, y1, w / 2 + 6, 16, (240, 236, 220), (120, 110, 90), 3)

def fineprint_gag(d, sc, t):
    l = lines_of(sc); t0 = LOC[sc]
    if sc == 0:                                              # a tiny asterisk hops off the ad stack onto the desk
        k = prog(t, LS[l[3]] - .2, .6)
        if k > 0:
            x = 900 + 60 * k; y = 760 - 120 * math.sin(math.pi * k) if k < 1 else 760 - abs(math.sin(t * 5)) * 10
            asterisk(d, x, y, 22 + 6 * popin(t, LS[l[6]], .4), t)
    elif sc == 1:                                            # it's back, dragging a scroll across the floor
        k = oc(prog(t, t0 + .3, 1.5)); L = 40 + 900 * oc(prog(t, LS[l[3]], 6))
        scroll(d, 960, 1040 - 20, 1040, 10) if False else None
        d.rect(960 - L / 2, 1000, 960 + L / 2, 1040, (252, 250, 240), ol=(120, 110, 90), w=3)
        fine_lines(d, 960 - L / 2 + 8, 1006, 960 + L / 2 - 8, 1034, 200, 11, 1)
        asterisk(d, 960 + L / 2, 990 - abs(math.sin(t * 4)) * 14, 34, t)
    elif sc == 2:                                            # the fine print unrolls from the ceiling; salesman reads it
        L = 120 + 700 * oc(prog(t, t0 + .2, 4))
        scroll(d, 1600, 0, L, 140, 2)
        asterisk(d, 1600, L + 40, 46, t, rot=t * .5)
    elif sc == 3:                                            # a tyre-sized asterisk on the start line; it "rolls out" one foot
        roll = oc(prog(t, LS[l[1]] + .3, .8)) * 120
        asterisk(d, 960 + roll, 780, 80, t, rot=roll / 80)
        if roll > 5:
            d.line([(960, 880), (960 + roll, 880)], RED, 6); d.text(960 + roll / 2, 908, '1 FT', 24, RED)
    elif sc == 4:                                            # the trailer is loaded with fine print
        pass
    elif sc == 5:                                            # fine print paper wound around like a charging cable
        L = oc(prog(t, t0 + .5, 10))
        pts = [(1500 + 40 * math.sin(i * .5), 600 + i * 6) for i in range(int(60 * L) + 2)]
        pts = [(1450 - i * 14 * L, 900 - 220 * math.sin(i * .13) * L) for i in range(int(70 * L) + 2)]
        if len(pts) > 1: d.line(pts, (252, 250, 240), 22); d.line(pts, (60, 60, 70, 120), 4)
        asterisk(d, pts[-1][0], pts[-1][1] - 30, 40, t)
    elif sc == 6:                                            # the speakers blast fine print
        if t > LS[l[0]] + 1.0:
            for i in range(10):
                ph = ((t * .9 + i / 10) % 1)
                for side, x_ in ((1, 430), (-1, 1490)):
                    x = x_ + side * ph * 500; y = 640 + 60 * math.sin(i * 1.7) + 14 * math.sin(t * 9 + i)
                    d.rect(x - 50, y - 10, x + 50, y + 10, (252, 250, 240, int(255 * (1 - ph))), r=4)
                    fine_lines(d, x - 44, y - 6, x + 44, y + 6, int(200 * (1 - ph)), 8, i)
    elif sc == 7:                                            # fine-print avalanche, rising
        h = 360 * oc(prog(t, t0 + .5, max(1, END_T - t0 - 1))) + (0 if HAS_END else 150 * oc(prog(t, END_T + .2, 1.6)))
        pile(d, h, t)
    elif sc == 8:                                            # buried, then digs out
        h = 360 * (1 - oc(prog(t, LS[l[0]] + .2, 1.4))) + 120
        pile(d, h, t)

def pile(d, h, t):
    if h < 4: return
    pts = [(0, H)] + [(x, H - h - 40 * math.sin(x * .011 + 1) - 18 * math.sin(x * .037)) for x in range(0, W + 40, 40)] + [(W, H)]
    d.poly(pts, (248, 246, 236), (130, 120, 100), 4)
    rng = np.random.default_rng(5)
    for i in range(36):
        x = rng.uniform(40, W - 40); y = H - rng.uniform(10, max(12, h - 10))
        d.rect(x - 60, y - 14, x + 60, y + 14, (255, 254, 248), r=3, ol=(150, 140, 120), w=2)
        fine_lines(d, x - 54, y - 9, x + 54, y + 9, 170, 8, i)
    asterisk(d, 1500, H - h - 70, 60, t, rot=math.sin(t) * .2)

# ================================================================ background oddities (never mentioned)
def pigeon(d, x, y, t, s=1.0, hat=True):
    bob = abs(math.sin(t * 6)) * 4 * s
    d.ell(x, y - 18 * s - bob, 24 * s, 16 * s, (140, 146, 160), OL, 2)
    d.ell(x + 20 * s, y - 34 * s - bob, 10 * s, 10 * s, (120, 126, 140), OL, 2)
    d.poly([(x + 29 * s, y - 35 * s - bob), (x + 38 * s, y - 32 * s - bob), (x + 29 * s, y - 30 * s - bob)], (230, 170, 60))
    d.ell(x + 22 * s, y - 36 * s - bob, 2 * s, 2 * s, OL)
    if hat:
        d.chord(x + 20 * s, y - 40 * s - bob, 12 * s, 10 * s, 180, 360, (250, 200, 30)); d.rect(x + 6 * s, y - 41 * s - bob, x + 34 * s, y - 38 * s - bob, (250, 200, 30))
    for k_ in (-1, 1): d.line([(x + k_ * 6 * s, y - 4 * s), (x + k_ * 6 * s + math.sin(t * 12) * 4 * s * k_, y)], (230, 140, 80), 3 * s)

def oddity(d, sc, t):
    t0 = LOC[sc]
    if sc == 0:                                              # pigeon in a hard hat patrolling the window ledge
        x = 140 + ((t * 40) % 420); pigeon(d, x, 642, t)
    elif sc == 1:                                            # raccoon filling a toy car at the pump
        x, y = 1470, 900
        d.rect(x - 70, y - 40, x + 30, y - 8, (230, 40, 60), r=12, ol=OL, w=3)
        for wx in (x - 50, x + 10): d.ell(wx, y - 8, 12, 12, (30, 30, 34))
        rx = x + 80; d.ell(rx, y - 50, 30, 40, (120, 120, 130), OL, 3); d.ell(rx, y - 110, 26, 24, (140, 140, 150), OL, 3)
        d.rect(rx - 22, y - 116, rx + 22, y - 104, (40, 40, 46)); d.ell(rx - 10, y - 110, 4, 4, (255, 255, 255)); d.ell(rx + 10, y - 110, 4, 4, (255, 255, 255))
        for i in range(5): d.rect(rx + 26 + i * 10, y - 60, rx + 34 + i * 10, y - 52, (40, 40, 46) if i % 2 else (140, 140, 150))
        d.line([(1600 + 70, 700), (rx - 20, y - 70), (x + 20, y - 30)], (30, 30, 34), 6)
    elif sc == 2:                                            # a goat on a rotating display plinth, chewing a brochure
        x, y = 260, 880; d.ell(x, y, 150, 30, (90, 94, 110), OL, 3); d.rect(x - 150, y - 20, x + 150, y, (110, 114, 130))
        f = math.cos(t * .8)
        d.ell(x, y - 90, 80 * abs(f) + 30, 40, (240, 238, 232), OL, 3)
        for lx in (-40, -15, 15, 40): d.line([(x + lx * abs(f), y - 60), (x + lx * abs(f), y - 22)], (80, 70, 60), 7)
        hx_ = x + 80 * f; d.ell(hx_, y - 140, 26, 32, (240, 238, 232), OL, 3)
        d.line([(hx_ - 10, y - 170), (hx_ - 22, y - 196)], (150, 130, 100), 5); d.line([(hx_ + 10, y - 170), (hx_ + 22, y - 196)], (150, 130, 100), 5)
        d.rect(hx_ - 4, y - 124 + math.sin(t * 10) * 3, hx_ + 40, y - 104 + math.sin(t * 10) * 3, (255, 214, 64), r=2, ol=OL, w=2)
    elif sc == 3:                                            # a snail in a racing helmet on the start line
        x = 1760 - (t - t0) * 3; y = 880
        d.ell(x, y - 8, 46, 10, (180, 200, 120), OL, 3); d.ell(x + 6, y - 40, 30, 30, (190, 120, 60), OL, 3)
        d.arc(x + 6, y - 40, 16, 16, 0, 300, (120, 70, 30), 4)
        d.ell(x - 40, y - 26, 14, 14, (220, 30, 40), OL, 3); d.rect(x - 50, y - 30, x - 30, y - 24, (40, 40, 60))
    elif sc == 4:                                            # trailer + boat full of fine print, with a sunbathing penguin
        x, y = 1660, 840
        d.rect(x - 260, y + 20, x + 220, y + 40, (60, 60, 66)); d.ell(x - 180, y + 50, 30, 30, (24, 24, 28)); d.ell(x + 140, y + 50, 30, 30, (24, 24, 28))
        d.line([(x - 260, y + 30), (x - 360, y + 44)], (60, 60, 66), 10)
        d.poly([(x - 250, y - 70), (x + 260, y - 70), (x + 200, y + 20), (x - 210, y + 20)], (250, 250, 252), OL, 4)
        d.rect(x - 230, y - 60, x + 230, y - 48, (30, 110, 200))
        for i in range(6):
            d.rect(x - 200 + i * 60, y - 150 + (i % 2) * 20, x - 140 + i * 60, y - 70, (252, 250, 240), ol=(120, 110, 90), w=2)
        px_ = x + 150; d.line([(px_ - 70, y - 100), (px_ + 40, y - 150)], (230, 80, 120), 10)
        d.ell(px_ - 10, y - 140, 26, 40, (30, 30, 36), OL, 3); d.ell(px_ - 10, y - 135, 16, 30, (250, 250, 252))
        d.ell(px_ - 6, y - 186, 20, 20, (30, 30, 36), OL, 3); d.rect(px_ - 22, y - 192, px_ + 12, y - 182, (20, 20, 20), r=3)
        d.poly([(px_ + 10, y - 184), (px_ + 24, y - 180), (px_ + 10, y - 176)], (250, 170, 40))
        d.line([(px_ - 30, y - 150), (px_ - 50 + 10 * math.sin(t * 3), y - 170)], (30, 30, 36), 8)
    elif sc == 5:                                            # a cow plugged into the charger, reading a newspaper
        x, y = 1760, 900
        d.ell(x - 150, y - 110, 100, 60, (250, 250, 250), OL, 4)
        for sx_, sy_ in ((-190, -130), (-120, -90)): d.ell(x + sx_, y + sy_, 26, 18, (30, 30, 30))
        for lx in (-220, -180, -110, -80): d.line([(x + lx, y - 70), (x + lx, y - 4)], (250, 250, 250), 14)
        d.ell(x - 260, y - 150, 40, 34, (250, 250, 250), OL, 4); d.ell(x - 280, y - 136, 22, 14, (240, 170, 170))
        d.rect(x - 250, y - 220 + math.sin(t * .7) * 3, x - 160, y - 150 + math.sin(t * .7) * 3, (236, 236, 228), ol=(90, 90, 90), w=2)
        fine_lines(d, x - 244, y - 212, x - 166, y - 158, 180, 9, 3)
        d.line([(x + 50, 640), (x - 60, y - 140)], (24, 24, 30), 9)
    elif sc == 6:                                            # a sheep in headphones, headbanging on the speaker stack
        x, y = 300, 410; bang = math.sin(t * 9) * 8
        R._sheep(d, x, y, t, .8)
        d.arc(x + 38, y - 62 + bang, 26, 26, 180, 360, (30, 30, 30), 6)
        d.ell(x + 14, y - 58 + bang, 9, 12, (230, 40, 60)); d.ell(x + 62, y - 58 + bang, 9, 12, (230, 40, 60))
    elif sc == 7:                                            # a mime trapped in an invisible box by the cones
        x, y = 360, 900; sw = math.sin(t * 2.2) * 14
        d.rect(x - 90, y - 300, x + 90, y, None, ol=(255, 255, 255, 60), w=2)
        d.rect(x - 30, y - 200, x + 30, y - 60, (30, 30, 34)); [d.rect(x - 30, y - 200 + i * 28, x + 30, y - 186 + i * 28, (240, 240, 240)) for i in range(5)]
        d.ell(x, y - 236, 30, 34, (250, 250, 252), OL, 3); d.rect(x - 22, y - 276, x + 22, y - 262, (20, 20, 20))
        d.line([(x - 30, y - 190), (x - 88, y - 220 + sw)], (240, 240, 240), 14); d.line([(x + 30, y - 190), (x + 88, y - 220 - sw)], (240, 240, 240), 14)
        d.ell(x - 88, y - 220 + sw, 12, 12, (255, 255, 255), OL, 2); d.ell(x + 88, y - 220 - sw, 12, 12, (255, 255, 255), OL, 2)
        d.line([(x - 14, y - 60), (x - 20, y)], (30, 30, 34), 12); d.line([(x + 14, y - 60), (x + 20, y)], (30, 30, 34), 12)
    elif sc == 8:                                            # the pigeon is back, now with three hard-hatted chicks
        x = 220 + ((t * 30) % 300); pigeon(d, x, 642, t)
        for i in range(3): pigeon(d, x - 50 - i * 36, 642, t + i * .3, .55)

# ================================================================ world
def world(t, sc, with_cast=True):
    loc = SCN[sc]['loc']
    img = bg(loc).copy(); d = D(img)
    if SCN[sc]['photo']:
        screen_photo(img, SCN[sc]['photo'], *SCREENS[loc], t, LOC[sc])
        x0, y0, x1, y1 = SCREENS[loc]
        d.rect(x0, y1 - 46, x0 + 22 + font(26 * K).getlength(SCN[sc]['model']) / K, y1, (10, 10, 14, 200))
        d.text(x0 + 12, y1 - 23, SCN[sc]['model'], 26, (255, 255, 255), anchor='lm', path=FONT_X)
    elif sc == 8:
        bike(d, 960, 330, t)
    oddity(d, sc, t)
    f = int(round(t * FPS))
    if with_cast:
        if loc == 'showroom':                               # desk behind the cast's hands
            pass
        for who, x, sched, cfg, spk in (('S', SX, SS_, SALES, 'S'), ('B', BX, BS, BUYER, 'B')):
            lp, rp, ex = pose_at(sched, t)
            st = dict(lpose=lp, rpose=rp, mouth=float(MOUTH[spk][min(f, len(MOUTH[spk]) - 1)]) if MOUTH is not None else 0.0,
                      look=(-1 if who == 'S' else 1))
            st.update(ex)
            if who == 'S' and sc == 8 and HAS_END and t >= LS[max(LN)] - .1: st['look'] = 0
            st['blink'] = bool(ex.get('blink')) or ((t + (0.0 if who == 'S' else 1.3)) % 3.4) < 0.12
            st['dy'] = math.sin(t * 2.2 + (0 if who == 'S' else 1)) * 3 + (-4 if talking(spk, t) and (f // 4) % 2 else 0)
            if who == 'B':
                walk_k = prog(t, LOC[sc], .7) if sc else 1
                xx = x - 260 * (1 - oc(walk_k))
                if walk_k < 1: st['walk'] = t * 13; st['dy'] -= abs(math.sin(t * 13)) * 10
            else:
                xx = x
            if st.get('sweat'): st['sweat'] = t
            ds = DS(img, CAST_S, xx * (1 - CAST_S), FEET * (1 - CAST_S))
            person(ds, xx, FEET, cfg, st)
            if who == 'S': sales_extras(ds, xx, FEET, st)
            else: buyer_extras(ds, xx, FEET, st, sc, t)
        if loc == 'showroom' and sc in (0, 2):
            desk(D(img), t)
    fineprint_gag(D(img), sc, t)
    return img
FEET = 1046

def desk(d, t):
    d.rect(700, 770, 1240, 800, (120, 84, 54), r=6, ol=OL, w=4)
    d.rect(730, 800, 1210, 1080, (150, 108, 70), ol=OL, w=4)
    d.rect(760, 830, 1180, 900, (170, 124, 82), r=6)
    d.text(970, 865, 'SALES', 34, (110, 74, 44))
    if t < 30:                                               # the slammed stack of ads, bouncing on impact
        b = max(0, 1 - prog(t, .2, .4)) * math.sin(prog(t, .2, .4) * 9) * 14
        for k_ in range(6):
            d.rect(840 + k_ * 3, 742 - k_ * 6 - b, 1000 + k_ * 3, 770 - k_ * 6 - b, (252, 252, 246), r=2, ol=(90, 90, 100), w=2)

def bike(d, x, y, t):
    """End scene: the bicycle on the showroom screen... with its own tag."""
    d.rect(720, 150, 1200, 420, (240, 244, 250))
    for wx in (x - 120, x + 120):
        d.ell(wx, y + 30, 70, 70, None, OL, 8); d.ell(wx, y + 30, 8, 8, OL)
    d.line([(x - 120, y + 30), (x - 30, y - 50), (x + 70, y - 50), (x + 120, y + 30)], (230, 50, 60), 9)
    d.line([(x - 30, y - 50), (x, y + 30), (x + 70, y - 50)], (230, 50, 60), 9)
    d.line([(x - 40, y - 74), (x - 10, y - 74)], OL, 10); d.line([(x + 70, y - 50), (x + 80, y - 86), (x + 100, y - 86)], OL, 7)

# ================================================================ parody ads (original, our style, claim text only)
AD_COLS = [((255, 90, 60), (255, 200, 60)), ((40, 180, 120), (180, 240, 120)), ((40, 90, 200), (120, 200, 255)),
           ((200, 30, 40), (40, 20, 30)), ((30, 60, 120), (220, 120, 40)), ((20, 120, 200), (60, 220, 200)),
           ((90, 20, 120), (255, 60, 60)), ((20, 20, 30), (90, 110, 160))]
def parody_ad(t, sc):
    a0, a1 = AD[sc]; k = prog(t, a0, a1 - a0)
    c0, c1 = AD_COLS[sc]
    img = grad(W * K, H * K, c0, c1); d = D(img)
    for i in range(16):                                      # spinning sunburst
        a_ = i * math.pi / 8 + t * .6
        d.poly([(960, 540), (960 + 1600 * math.cos(a_), 540 + 1600 * math.sin(a_)),
                (960 + 1600 * math.cos(a_ + .16), 540 + 1600 * math.sin(a_ + .16))], (255, 255, 255, 34))
    pw, ph_ = 760, 460
    s = popin(t, a0 + .05, .45)
    ph = photo(SCN[sc]['photo'], pw, ph_)
    card = Image.new('RGBA', ((pw + 40) * K, (ph_ + 40) * K), (255, 255, 255, 255))
    card.paste(ph.crop((0, 0, pw * K, ph_ * K)), (20 * K, 20 * K))
    card = card.rotate(-4 + 2 * math.sin(t * 2), resample=Image.BICUBIC, expand=True)
    if s > .05:
        card = card.resize((max(1, int(card.width * s)), max(1, int(card.height * s))), Image.LANCZOS)
        img.alpha_composite(card, (int(560 * K - card.width / 2), int(560 * K - card.height / 2)))
    d = D(img)
    l1, l2 = SCN[sc]['ad']
    k1, k2 = popin(t, a0 + .35, .35), popin(t, a0 + .6, .4)
    wob = 1 + .04 * math.sin(t * 8)
    if k1 > .05: d.text(1440, 380, l1, 74 * k1, (255, 255, 255), stroke=8, sc=INK)
    sz2 = 120
    while font(sz2 * K).getlength(l2) / K > 760: sz2 -= 4
    if k2 > .05:
        d.text(1440, 520, l2, sz2 * k2 * wob, TAG, stroke=10, sc=INK)
        tw = font(int(sz2 * K)).getlength(l2) / K
        asterisk(d, 1440 + tw / 2 + 30, 460, 18 + 8 * sc, t, face=sc >= 3)   # the asterisk grows every ad
    d.rect(40, 40, 330, 104, (0, 0, 0, 150), r=12); d.text(185, 72, 'PARODY AD', 34, (255, 255, 255))
    fsz = 11 + sc * 2                                        # the fine print strip, bigger every time
    d.rect(0, 1080 - fsz * 3.2, W, 1080, (255, 255, 255, 200))
    fine_lines(d, 30, 1080 - fsz * 2.8, W - 30, 1080 - 8, 220, fsz, sc)
    return img

# ================================================================ camera
def punches_for(sc):
    out = []
    for li in lines_of(sc):
        spk, txt, _ = SLINES[li]
        if spk == 'B' and ('!' in txt or '?' in txt): out.append((LS[li], .02 + .01 * min(sc, 6)))
        if li == SCN[sc].get('fact_line'): out.append((LS[li], .05))
    return out
PUNCH = {s: punches_for(s) for s in range(NSC)}
def camera(t, sc):
    t0 = LOC[sc]
    z = 1.04 + 0.03 * io(prog(t, t0, 12)); sx = 30 * math.sin((t - t0) * .25); sy = 0
    for tp, amt in PUNCH[sc]:
        if tp <= t < tp + .45: z += amt * (1 - oc(prog(t, tp, .45)))
    for li in lines_of(sc):                                  # handheld shake on the big outbursts
        txt = SLINES[li][1]
        if SLINES[li][0] == 'B' and sc >= 4 and (txt.count('!') + txt.count('?')) >= 2 and any(w.isupper() and len(w) > 2 for w in txt.split()):
            if LS[li] <= t < LS[li] + .8:
                k_ = 1 - prog(t, LS[li], .8); sx += 12 * k_ * math.sin(t * 61); sy += 8 * k_ * math.sin(t * 47)
    if sc == 0 and t < .5: z += .05 * (1 - prog(t, .15, .35))   # slam punch
    if sc == 8 and HAS_END and t >= LS[max(LN)] - .1:          # salesman turns to camera
        pk = io(prog(t, LS[max(LN)] - .1, .6)); z += .25 * pk; sx += 320 * pk; sy -= 60 * pk
    return z, sx, sy

def shoot(t, seg, cast=True, r=1):
    kind, sc = seg
    if kind == 'ad': return parody_ad(t, sc).resize((W * r, H * r), Image.LANCZOS)
    wimg = world(t, sc, cast)
    z, sx, sy = camera(t, sc)
    cw, ch = W * K / z, H * K / z
    x0 = clamp(W * K / 2 - cw / 2 + sx * K, 0, W * K - cw); y0 = clamp(H * K * .5 - ch / 2 + sy * K, 0, H * K - ch)
    return wimg.resize((W * r, H * r), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))

# ================================================================ overlays: claim vs reality cards
def card(d, x, y, w, head, lines, col, a, k):
    al = int(255 * a)
    h = 64 + 50 * len(lines)
    d.rect(x + 8, y + 10, x + w + 8, y + h + 10, (0, 0, 0, int(90 * a)), r=20)
    d.rect(x, y, x + w * k, y + h, (250, 248, 240, al), r=20, ol=col + (al,), w=6)
    if k > .7:
        d.rect(x, y, x + w, y + 50, col + (al,), r=20); d.rect(x, y + 30, x + w, y + 50, col + (al,))
        d.text(x + 24, y + 26, head, 28, (255, 255, 255, al), anchor='lm', path=FONT_X)
        for i, l in enumerate(lines):
            sz = 34
            while font(sz * K).getlength(l) / K > w - 40: sz -= 1
            d.text(x + 24, y + 88 + 50 * i, l, sz, (24, 22, 30, al), anchor='lm', path=FONT_X)

def overlays(t, seg):
    kind, sc = seg
    if kind == 'ad' or sc >= 8: return None
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0)); d = D(img)
    l = lines_of(sc); fl = SCN[sc]['fact_line']
    end = LOC[sc + 1] if sc + 1 in LOC else DUR
    if sc + 1 in AD: end = AD[sc + 1][0]
    a = window(t, LS[l[0]] + .3, end - .1, .2, .3)
    if a > 0:
        card(d, 40, 40, 560, SCN[sc]['says'][0], [SCN[sc]['says'][1]], (40, 120, 220), a, oc(prog(t, LS[l[0]] + .3, .3)))
    if fl in LS:
        a2 = window(t, LS[fl] - .05, end - .1, .2, .3)
        if a2 > 0:
            card(d, 1320, 40, 560, SCN[sc]['real'][0], list(SCN[sc]['real'][1:]), RED, a2, oc(prog(t, LS[fl] - .05, .3)))
            sk = popin(t, LS[fl] + .6, .3)
            if sk > .05:
                d.text(1600, 270, 'FINE PRINT', 40 * sk, RED + (int(255 * a2),), stroke=4, sc=(255, 255, 255, int(255 * a2)))
    return img

# ================================================================ captions
CAP_SIZE = 66
def ctext(w): return w['w']
def chunks():
    out = []
    for ln in sorted(LN):
        cur = []
        for w in LN[ln]:
            if cur and font(CAP_SIZE).getlength(' '.join(ctext(x) for x in cur + [w])) > 1400:
                out.append(cur); cur = []
            cur.append(w)
            if w['w'][-1] in '.?!,' or len(cur) == 4:
                out.append(cur); cur = []
        if cur: out.append(cur)
    res = []
    for i, c in enumerate(out):
        nxt = out[i + 1][0]['s'] if i + 1 < len(out) else DUR
        end = nxt if nxt - c[-1]['e'] < 0.5 else c[-1]['e'] + 0.4
        res.append(dict(words=c, s=c[0]['s'], e=min(end, T_CARD)))
    return res
CHUNKS = chunks()

@lru_cache(None)
def caption_img(ci, active, size=CAP_SIZE, maxw=1500):
    ws = [ctext(w) for w in CHUNKS[ci]['words']]
    while font(size).getlength(' '.join(ws)) > maxw and size > 40: size -= 2
    f = font(size); total = f.getlength(' '.join(ws)); sp = f.getlength(' ')
    img = Image.new('RGBA', (int(maxw + 80), int(size * 2.2)), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    x = (img.width - total) / 2
    for i, w in enumerate(ws):
        spk = CHUNKS[ci]['words'][0]['spk']
        col = TAG if i == active else (255, 255, 255)
        d.text((x, img.height / 2), w, font=f, fill=col, anchor='lm', stroke_width=max(6, size // 9), stroke_fill=(16, 16, 28))
        x += f.getlength(w) + sp
    return img

def captions(img, t, cx, cy, size=CAP_SIZE, maxw=1500):
    live = [ci for ci, c in enumerate(CHUNKS) if c['s'] - 0.02 <= t < c['e']]
    for ci in live[-1:]:
        c = CHUNKS[ci]; act = -1
        for i, w in enumerate(c['words']):
            if w['s'] - .02 <= t: act = i
        ci_img = caption_img(ci, act, size, maxw)
        s = 0.86 + 0.14 * ob(prog(t, c['s'], .12))
        ci_img = ci_img.resize((max(1, int(ci_img.width * s)), max(1, int(ci_img.height * s))), Image.LANCZOS)
        img.alpha_composite(ci_img, (int(cx - ci_img.width / 2), int(cy - ci_img.height / 2)))

def caption_boxes():
    res = []
    for ci, c in enumerate(CHUNKS):
        a = np.array(caption_img(ci, -1).getchannel('A')); ys, xs = np.nonzero(a > 8)
        im = caption_img(ci, -1); ox, oy = W / 2 - im.width / 2, CAP_Y - im.height / 2
        res.append(dict(text=' '.join(ctext(w) for w in c['words']), s=c['s'], e=c['e'], x0=int(xs.min() + ox), x1=int(xs.max() + ox),
                        y0=int(ys.min() + oy), y1=int(ys.max() + oy)))
    return res
CAP_Y = 975

# ================================================================ end card (payoff: the asterisk takes over)
END_Q = [("Which claim annoyed", 84, TAG), ("you the most?", 84, TAG), ("Tell us in the comments*", 54, (255, 255, 255)),
         ("*comments subject to fine print", 26, (200, 200, 210))]
def end_card(img, t, w=W, h=H, cx=None, cy=None, scale=1.0):
    cx = w / 2 if cx is None else cx; cy = h / 2 if cy is None else cy
    k = prog(t, T_CARD, .5)
    base = img; img = Image.new('RGBA', (base.width * K, base.height * K), (0, 0, 0, 0))
    d = D(img)
    d.rect(0, 0, w, h, (14, 12, 22, int(200 * k)))
    asterisk(d, cx, cy, (40 + 700 * oc(k)) * scale, t, col=(255, 200, 40, int(120 * k)), rot=t * .3)
    for i, (txt, size, col) in enumerate(END_Q):
        kk = popin(t, T_CARD + .15 + .1 * i, .3)
        if kk > .05:
            d.text(cx, cy - 170 * scale + i * 110 * scale, txt, size * kk * scale, col, stroke=6, sc=(10, 10, 16))
    base.alpha_composite(img.resize(base.size, Image.LANCZOS))

# ================================================================ frames
def base_frame(t, cast=True, r=1):
    seg = seg_at(t)
    tr = next((c for c in CUTS if c - TR / 2 <= t < c + TR / 2), None)
    if tr is None:
        return shoot(t, seg, cast, r), seg
    k = io(prog(t, tr - TR / 2, TR))                         # whip pan, motion blur
    a, b = shoot(min(t, tr - .001), seg_at(tr - .001), cast, r), shoot(max(t, tr), seg_at(tr), cast, r)
    Wr, Hr = W * r, H * r
    img = Image.new('RGBA', (Wr, Hr), (0, 0, 0, 255)); off = int(Wr * k)
    img.alpha_composite(a, (-off, 0)); img.alpha_composite(b, (Wr - off, 0))
    bl = math.sin(math.pi * k)
    if bl > .05:
        smear = img.resize((Wr // 24, Hr), Image.BILINEAR).resize((Wr, Hr), Image.BILINEAR)
        img = Image.blend(img, smear, min(.85, bl))
    return img, seg_at(t)

def frame(n):
    t = n / FPS
    img, seg = base_frame(t)
    ov = overlays(t, seg) if t < T_CARD else None
    if ov is not None: img.alpha_composite(ov.resize((W, H), Image.LANCZOS))
    if t >= T_CARD: end_card(img, t)
    else: captions(img, t, W / 2, CAP_Y)
    return img.convert('RGB').tobytes()

def contact_sheet(out, times):
    th = [Image.frombytes('RGB', (W, H), frame(int(t * FPS))).resize((480, 270)) for t in times]
    cols = 4; rows = (len(th) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * 480, rows * 290), (0, 0, 0)); d = ImageDraw.Draw(sheet)
    for i, im in enumerate(th):
        sheet.paste(im, ((i % cols) * 480, (i // cols) * 290)); d.text(((i % cols) * 480 + 6, (i // cols) * 290 + 272), f'{times[i]:.1f}s', fill=(255, 255, 0))
    sheet.save(out)

# ================================================================ audio
MUS_CACHE = {}
def load_track(name, SR):
    if name not in MUS_CACHE:
        p = os.path.join(MUSIC, name + '.mp3')
        MUS_CACHE[name] = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                                       capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    return MUS_CACHE[name]

def build_audio(voice, out_wav):
    SR = sfx.SR
    v = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', voice, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                     capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    n = int(DUR * SR); v = np.pad(v, (0, max(0, n - len(v))))[:n]
    rng = np.random.default_rng(3); TT = np.arange(n) / SR
    def tone(f, d, rate, amp=1.0):
        tt = np.arange(int(SR * d)) / SR; return np.sin(2 * np.pi * f * tt) * np.exp(-tt * rate) * amp
    def jingle(sc):
        notes = [523.3, 659.3, 784.0, 1046.5] if sc % 2 else [392.0, 523.3, 659.3, 784.0]
        out = np.zeros(int(SR * 1.6))
        for i, f in enumerate(notes):
            s = tone(f, .5, 6) + tone(f * 2, .5, 9) * .3; o = int(i * .14 * SR); out[o:o + len(s)] += s
        return out * .5
    def rumble(d=2.2):
        tt = np.arange(int(SR * d)) / SR; f = 38 + 30 * np.clip(tt / .6, 0, 1) + 6 * np.sin(tt * 30)
        s = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * .5 + np.sin(2 * np.pi * np.cumsum(f * 2) / SR) * .4
        s = sfx.lp(s + rng.standard_normal(len(tt)) * .3, 30) * np.minimum(1, tt * 8) * np.minimum(1, (d - tt) * 3)
        return s * (1 + .4 * np.sin(tt * 22))
    def scratch():
        return sfx.fade(sfx.sweep(1800, 200, .35) * sfx.dec(.35, 4) + rng.standard_normal(int(SR * .35)) * .3 * sfx.dec(.35, 8)) * .6
    def beep_down():
        out = np.zeros(int(SR * 1.1))
        for i, f in enumerate((880, 660, 440)):
            s = tone(f, .25, 3) * (np.sin(np.linspace(0, 40, int(SR * .25))) > 0); o = int(i * .3 * SR); out[o:o + len(s)] += s
        return out * .5
    def bell():
        return (tone(2400, .9, 4) + tone(3610, .9, 6) * .5) * .5
    def sad_trombone():
        out = np.zeros(int(SR * 2.4))
        for i, (f0, d) in enumerate(((294, .45), (277, .45), (262, .45), (247, 1.0))):
            tt = np.arange(int(SR * d)) / SR; f = f0 * (1 + .015 * np.sin(2 * np.pi * 6 * tt)) * (1 - (.06 * tt if i == 3 else 0))
            s = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.minimum(1, tt * 20) * np.exp(-tt * 1.2)
            o = int(i * .45 * SR); out[o:o + len(s)] += sfx.lp(s, 12)
        return out * .35
    cues = []
    def add(t0, s, vol): cues.append((int(max(0, t0) * SR), s * vol))
    add(0.15, sfx.thump(.3), .8); add(0.17, sfx.poof(), .4)              # the slam
    for c in CUTS: add(c - .2, sfx.whoosh(.42, 18), .45)
    for s, (a0, a1) in AD.items():
        add(a0 + .05, jingle(s), .55); add(a0 + .4, sfx.sparkle(), .4); add(a0 + .65, sfx.pop(), .35)
    for s in range(NSC):
        fl = SCN[s].get('fact_line')
        if fl in LS: add(LS[fl] - .05, sfx.stamp(), .35); add(LS[fl] + .6, sfx.pop(), .25)
        l = lines_of(s)
        if l: add(LS[l[0]] + .3, sfx.pop(), .2)
        for li in l:
            txt = SLINES[li][1]
            if SLINES[li][0] == 'B' and txt.count('!') + txt.count('?') >= 2 and s >= 3: add(LS[li], sfx.thump(.2), .25)
    L = lines_of
    add(LS[L(0)[3]] - .2, sfx.pop(), .3); add(LS[L(0)[4]], sfx.buzzer(.3), .25)
    add(LS[L(1)[4]] + .4, sfx.slide_down(), .3)
    add(LS[L(2)[1]], sfx.ding(1320, .6), .2); add(LS[L(2)[3]] + .3, sfx.slide_down(), .3)
    for i in range(3): add(LOC[3] + .4 + i * .5, tone(880, .3, 5), .35)
    add(LOC[3] + 1.9, tone(1320, .5, 3), .4); add(LS[L(3)[1]] + .3, sfx.vroom(.8), .3)
    add(LS[L(4)[1]], sfx.ding(1568, .6), .2); add(LS[L(4)[6]] + .6, sfx.cha_ching(), .2)
    add(LS[L(5)[3]] + 1.2, beep_down(), .45)
    if NSC > 6:
        add(LE[L(6)[0]] + .1, rumble(2.2), .6); add(LS[L(6)[1]] - .25, scratch(), .5)
        add(LS[L(6)[4]], sfx.crash(), .25)
    if NSC > 7:
        add(LS[L(7)[1]] + .1, sfx.buzzer(.3), .3); add(LS[L(7)[9]], sfx.ding(1046, .9), .2)
    if not HAS_END:
        add(END_T + .4, sad_trombone(), .5); add(T_CARD, sfx.sparkle(), .4)
    if HAS_END:
        add(LS[L(8)[5]] + .1, bell(), .4); add(LE[L(8)[5]] + .1, sad_trombone(), .5); add(T_CARD, sfx.sparkle(), .4)
    fxa = np.zeros(n + SR * 4)
    for i, s in cues: fxa[i:i + len(s)] += s
    # music: a different Kevin MacLeod track per scene, muted for the parody ads, ducked under the voice
    mus = np.zeros(n)
    for s in range(NSC):
        t0 = LOC[s]; t1 = AD[s + 1][0] if s + 1 in AD else (LOC[s + 1] if s + 1 in LOC else DUR)
        tr = load_track(SCN[s]['music'], SR)
        i0, i1 = int(t0 * SR), min(n, int(t1 * SR)); off = int((s * 17.3 % 40) * SR)
        seg = tr[off:off + (i1 - i0)]; seg = np.pad(seg, (0, (i1 - i0) - len(seg)))
        fl = int(.25 * SR); e = np.ones(len(seg)); e[:fl] = np.linspace(0, 1, fl); e[-fl:] = np.linspace(1, 0, fl)
        mus[i0:i1] += seg * e
    env = np.abs(v); k_ = int(SR * .15); env = np.convolve(env, np.ones(k_) / k_, mode='same')
    duck = 1 - 0.55 * np.clip(env / (env.max() * .12 + 1e-9), 0, 1)
    mus *= duck * 0.22
    mixd = v * 1.0 + fxa[:n] * 0.5 + mus
    finish_mix(mixd, SR, out_wav)

def finish_mix(mixd, SR, out_wav):
    mixd = np.clip(mixd / max(1.0, np.abs(mixd).max() / 0.95), -1, 1)
    tmp = out_wav + '.pre.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f64le', '-ar', str(SR), '-ac', '1', '-i', '-', tmp],
                   input=mixd.astype(np.float64).tobytes(), check=True)
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', tmp, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    m = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-af', af, '-ar', '48000', '-ac', '2', tmp + '2.wav'], check=True)
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', tmp + '2.wav', '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    I = float(r.split('I:')[-1].split('LUFS')[0]); tp = float(r.split('Peak:')[-1].split('dBFS')[0])
    g = min(-14.0 - I, -1.5 - tp)                            # trim loudnorm's shortfall, keep 1.5 dB true-peak headroom
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp + '2.wav', '-af', f'volume={g:.2f}dB', out_wav], check=True)
    os.remove(tmp); os.remove(tmp + '2.wav')

# ================================================================ Shorts (vertical, stacked layout)
SHORTS = {1: dict(scenes=[3, 4, 1], hook='Is 0-60 really from zero?', q=('Should 0-60 start', 'at zero?'), name='rollout'),
          2: dict(scenes=[6, 5], hook='Why does this EV have an exhaust?', q=('Fake exhaust sound:', 'yes or no?'), name='fratzonic'),
          3: dict(scenes=[7, 2, 0, 8], hook='"Full Self-Driving"... read the name', q=('Which claim', 'annoyed you most?'), name='fsd')}
def short_segments(n):
    out = []
    for i, s in enumerate(SHORTS[n]['scenes']):
        if s not in LOC or not lines_of(s): continue
        a = LS[lines_of(s)[0]] - .35 if i == 0 or s not in AD else AD[s][0] - .1
        b = (AD[s + 1][0] if s + 1 in AD else LE[lines_of(s)[-1]] + .6)
        if s == 8: b = END_T + .5
        out.append((a, b))
    return out
def short_map(n):
    segs = short_segments(n); m = []; acc = 0.0
    for a, b in segs: m.append((acc, a, b)); acc += b - a
    return m, acc + 2.6
def short_t(n, ts):
    m, tot = short_map(n)
    for acc, a, b in m:
        if ts < acc + (b - a): return a + (ts - acc), (acc, a)
    acc, a, b = m[-1]; return b, None

def short_frame(n, ts):
    t, cur = short_t(n, ts)
    img = Image.new('RGBA', (SW * K, SH * K), (16, 14, 24, 255)); d = D(img)
    seg = seg_at(t)
    base, _ = base_frame(t, r=K)
    if seg[0] == 'ad' and not any(c - TR / 2 <= t < c + TR / 2 for c in CUTS):   # show the whole parody ad, letterboxed
        img.alpha_composite(base.resize((1080 * K, 608 * K), Image.LANCZOS), (0, 820 * K))
    else:
        crop = base.crop((440 * K, 0, 1480 * K, 1080 * K)).resize((1080 * K, 1122 * K), Image.LANCZOS)
        img.alpha_composite(crop, (0, 600 * K))
    sc = seg[1]
    img.paste(grad(SW * K, 600 * K, (40, 30, 70), (16, 14, 24)), (0, 0))
    d.text(SW / 2, 120, SHORTS[n]['hook'], 58, TAG, stroke=6, sc=(10, 10, 16)) if font(58 * K).getlength(SHORTS[n]['hook']) / K < 1000 \
        else d.text(SW / 2, 120, SHORTS[n]['hook'], 46, TAG, stroke=6, sc=(10, 10, 16))
    if sc < 8 and seg[0] == 'loc' and t >= LS[lines_of(sc)[0]] - .3:
        l = lines_of(sc); fl = SCN[sc]['fact_line']
        card(d, 50, 200, 980, SCN[sc]['says'][0], [SCN[sc]['says'][1]], (40, 120, 220), 1.0, oc(prog(t, LS[l[0]] - .3, .3)))
        if fl in LS and t >= LS[fl] - .05:
            card(d, 50, 360, 980, SCN[sc]['real'][0], list(SCN[sc]['real'][1:]), RED, 1.0, oc(prog(t, LS[fl] - .05, .3)))
    m, tot = short_map(n)
    if ts >= tot - 2.6:
        k = prog(ts, tot - 2.6, .4); d.rect(0, 0, SW, SH, (14, 12, 22, int(210 * k)))
        asterisk(d, SW / 2, SH / 2, 60 + 500 * oc(k), ts, col=(255, 200, 40, int(110 * k)), rot=ts * .3)
        for i, txt in enumerate(SHORTS[n]['q'] + ('Comment below!',)):
            kk = popin(ts, tot - 2.4 + .12 * i, .3)
            if kk > .05: d.text(SW / 2, SH / 2 - 120 + i * 120, txt, (80 if i < 2 else 60) * kk, TAG if i < 2 else (255, 255, 255), stroke=6, sc=(10, 10, 16))
    else:
        captions(img, t, SW / 2 * K, 1580 * K, 70 * K, 960 * K)
    return img.resize((SW, SH), Image.LANCZOS).convert('RGB').tobytes()

def short_audio(n, mix_wav, out_wav):
    SR = 48000
    a = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', mix_wav, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                     capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    m, tot = short_map(n); parts = []
    for acc, s0, s1 in m:
        seg = a[int(s0 * SR):int(s1 * SR)].copy(); f = int(.03 * SR); seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
        parts.append(seg)
    tail = np.zeros(int(2.6 * SR)); sp = sfx.sparkle() if sfx.SR == SR else np.zeros(1); tail[:len(sp)] += sp[:len(tail)] * .4
    finish_mix(np.concatenate(parts + [tail]), SR, out_wav)

def encode(frames_fn, n_frames, size, wav, out, voice):
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', str(FPS),
                           '-i', '-', '-i', wav, '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
                           '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
    with Pool(os.cpu_count(), initializer=load_mouth, initargs=(voice,)) as pool:
        for i, buf in enumerate(pool.imap(frames_fn, range(n_frames), chunksize=4)):
            ff.stdin.write(buf)
            if i % 300 == 0: print(f'frame {i}/{n_frames}', flush=True)
    ff.stdin.close(); ff.wait()

_SN = 1
def _short_frame_n(i): return short_frame(_SN, i / FPS)

def thumb(out):
    load_mouth(VOICE_CACHE)
    t = LS[lines_of(3)[4]] + .35
    img, _ = base_frame(t, r=K); d = D(img)
    d.rect(0, 0, W, 250, (10, 10, 18, 215))
    d.text(860, 125, 'CAR ADS vs REALITY', 140, (255, 255, 255), stroke=12, sc=INK)
    d.text(1270, 125, '', 10, TAG)
    asterisk(d, 1780, 130, 105, 0.5, rot=.3)
    d.rect(1180, 700, 1880, 860, RED, r=24, ol=(255, 255, 255), w=6); d.text(1530, 780, 'READ THE *', 84, (255, 255, 255), stroke=6, sc=INK)
    img.resize((W, H), Image.LANCZOS).convert('RGB').save(out)

def sthumb(n, out):
    load_mouth(VOICE_CACHE)
    sc = SHORTS[n]['scenes'][0]
    if sc not in LOC: print('scene not voiced yet'); return
    l = lines_of(sc); t = LS[l[min(4, len(l) - 1)]] + .2
    img = Image.frombytes('RGB', (SW, SH), short_frame(n, t - short_segments(n)[0][0])).convert('RGBA').resize((SW * K, SH * K), Image.LANCZOS); d = D(img)
    d.rect(0, 0, SW, 600, (14, 12, 22, 235))
    rows, cur = [], ''
    for w_ in SHORTS[n]['hook'].split():
        if cur and font(92 * K).getlength(cur + ' ' + w_) / K > 960: rows.append(cur); cur = w_
        else: cur = (cur + ' ' + w_).strip()
    rows.append(cur)
    for i, txt in enumerate(rows):
        d.text(SW / 2, 300 - 60 * (len(rows) - 1) + i * 120, txt, 92, TAG, stroke=9, sc=INK)
    asterisk(d, 930, 520, 70, .5)
    img.resize((SW, SH), Image.LANCZOS).convert('RGB').save(out)

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        load_mouth(sys.argv[4] if len(sys.argv) > 4 else VOICE_CACHE)
        Image.frombytes('RGB', (W, H), frame(int(float(sys.argv[2]) * FPS))).save(sys.argv[3])
    elif mode == 'sheet':
        load_mouth(sys.argv[3] if len(sys.argv) > 3 else VOICE_CACHE)
        ts = []
        for s in range(NSC):
            if s in AD: ts.append(AD[s][0] + 1.4)
            l = lines_of(s); ts += [LS[l[0]] + .4, LS[l[len(l) // 2]] + .3, LE[l[-1]] - .2]
        contact_sheet(sys.argv[2], ts + ([T_CARD + 1.2] if HAS_END else []))
    elif mode == 'meta':
        json.dump(dict(captions=caption_boxes(), onscreen=ONSCREEN, duration=DUR, size=[W, H], fps=FPS, ads=AD, loc=LOC),
                  open(sys.argv[2], 'w'), indent=1)
    elif mode == 'video':
        voice, out = sys.argv[2], sys.argv[3]
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        wav = os.path.splitext(out)[0] + '_mix.wav'
        build_audio(voice, wav)
        nf = int(float(sys.argv[4]) * FPS) if len(sys.argv) > 4 else int(DUR * FPS)
        encode(frame, nf, (W, H), wav, out, voice)
        print('done', out, DUR)
    elif mode == 'short':
        _SN = int(sys.argv[2]); voice, mix_wav, out = sys.argv[3], sys.argv[4], sys.argv[5]
        wav = os.path.splitext(out)[0] + '_mix.wav'
        short_audio(_SN, mix_wav, wav)
        _, tot = short_map(_SN)
        encode(_short_frame_n, int(tot * FPS), (SW, SH), wav, out, voice)
        print('done', out, round(tot, 2))
    elif mode == 'shortstill':
        load_mouth(sys.argv[5] if len(sys.argv) > 5 else VOICE_CACHE)
        Image.frombytes('RGB', (SW, SH), short_frame(int(sys.argv[2]), float(sys.argv[3]))).save(sys.argv[4])
    elif mode == 'thumb':
        thumb(sys.argv[2])
    elif mode == 'sthumb':
        sthumb(int(sys.argv[2]), sys.argv[3])
