"""Toyota episode: sets, real-photo displays, cutaways, overlays, poses and cues for src/engine.py.
Running gag: 'Have you considered a Corolla?' (the Corolla photo slides in, chime) - and the salesman's own 1998 Corolla.
Background oddity (never mentioned): a cow in a vibrating massage chair reading a newspaper (asleep after hours).
Wall easter eggs: 'EMPLOYEE OF THE MONTH' frame holding a Corolla photo; a 'SINCE 1937' plaque."""
from engine import *
from PIL import ImageEnhance

VOICE = os.path.expanduser('~/.cache/real-dealership/toyota/voice.wav')
FAST = False
TRED = (235, 10, 30)
SALES = dict(skin=hexc('f0c6a2'), skin2=hexc('d9a882'), hair=hexc('e3bd57'), suit=hexc('5a5f69'), suit2=hexc('474b54'),
             shirt=hexc('f7f7fa'), tie=TRED, pants=hexc('4c5059'), shoe=hexc('2a2220'), glasses=False, hairstyle='part', lids=0.45)
def badge(d, x, y):
    d.rect(x - 18, y - 12, x + 18, y + 12, (245, 245, 248), r=4)
    d.ell(x, y, 12, 8, None, TRED, 2.5); d.ell(x, y - 2, 5, 5, None, TRED, 2)
FOCUS = {'engine.jpg': (0.5, 0.45), 'prius.jpg': (0.45, 0.6), 'twins.jpg': (0.5, 0.97), 'supra.jpg': (0.5, 0.6),
         'corolla.jpg': (0.5, 0.6), 'landcruiser.jpg': (0.5, 0.5), 'z4.jpg': (0.45, 0.65), 'gr86.jpg': (0.5, 0.6),
         'bz4x.jpg': (0.5, 0.6), 'corolla_1998.jpg': (0.5, 0.6)}
def grade(im):                                              # one warm, clean grade for every photo in this video
    im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.05)).enhance(1.06)
    return Image.blend(im, Image.new('RGB', im.size, (255, 240, 222)), 0.05)

L = SCRIPT.LINES
T_GAG = [LS[li] for li in range(NL) if 'considered a Corolla' in L[li][1]]
T_50, T_AUSTRIA, T_ENGINE = word_t(5, 'fifty'), word_t(9, 'Austria'), word_t(9, 'engine')
T_Z4, T_ENDED = word_t(11, 'Z4'), word_t(13, 'ended')
T_SUBARU, T_THAT, T_BRZ, T_BUMPER = word_t(17, 'Subaru'), word_t(18, 'that'), word_t(19, 'BRZ'), word_t(21, 'bumper')
T_BZ4X, T_JUSTBZ, T_2022, T_WHEELS = word_t(23, 'bZ4X'), word_t(25, 'bZ.'), word_t(27, '2022'), word_t(27, 'wheels')
T_BUY = word_t(29, 'buy')
T_NUMBER, T_JAPAN, T_FOUR, T_STOPPED = word_t(32, 'number'), word_t(34, 'Japan'), word_t(34, 'four'), word_t(34, 'stopped')
T_SNACKS = word_t(36, 'snacks')
T_1997, T_COOL = word_t(39, '1997'), word_t(40, 'cool')
T_1998, T_DIE = word_t(43, '1998'), word_t(45, 'die')
T_SUPRA2 = word_t(47, 'Supra')
SC = {i + 1: s for i, s in enumerate(SCENES)}

def grad(h, w, c0, c1):
    a = np.linspace(0, 1, h)[:, None, None]
    return np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3))
def wall_floor(wall, floor):
    return Image.fromarray(np.concatenate([grad(WALL_Y * K, W * K, *wall), grad((H - WALL_Y) * K, W * K, *floor)]).astype(np.uint8))
@lru_cache(None)
def spot(cx, top, w0, w1, h, a=60):
    cone = Image.new('L', (W * K, H * K), 0)
    ImageDraw.Draw(cone).polygon([(p * K, q * K) for p, q in [(cx - w0, top), (cx + w0, top), (cx + w1, top + h), (cx - w1, top + h)]], fill=a)
    return cone.filter(ImageFilter.GaussianBlur(28 * K))
DISP = (99, 196, 720, 470)

def eggs(img, d, night=False):
    d.rect(24, 700, 198, 904, (120, 96, 60), r=6); d.rect(34, 710, 188, 894, (252, 250, 244), r=3)
    d.text(111, 728, 'EMPLOYEE', 18, (30, 30, 34), path=FONT_X); d.text(111, 750, 'OF THE MONTH', 15, (30, 30, 34), path=FONT_X)
    display(img, 'corolla.jpg', 44, 768, 134, 110, 0, 0, drift=0)
    d.rect(744, 744, 900, 830, (200, 170, 100), r=8, ol=(120, 96, 50), w=4)
    d.text(822, 772, 'SINCE', 22, (60, 44, 20), path=FONT_X); d.text(822, 804, '1937', 34, (60, 44, 20))

@lru_cache(None)
def bg(kind):
    if kind in ('show', 'night'):
        img = wall_floor(((250, 250, 250), (234, 234, 236)), ((222, 222, 224), (246, 246, 247))); d = D(img)
        d.rect(0, 0, W, 76, (255, 255, 255)); d.rect(0, 70, W, 76, TRED)
        for x in (140, 459, 778): d.rect(x - 110, 30, x + 110, 42, (255, 250, 236), r=6)
        d.rect(0, WALL_Y - 10, W, WALL_Y, TRED)
        for y in range(WALL_Y + 70, H, 150): d.line([(0, y), (W, y)], (232, 232, 234), 2)
        screen_frame(d, DISP[0], DISP[1], DISP[0] + DISP[2], DISP[1] + DISP[3], glow=(236, 236, 238))
        paste_logo(img, 'logo.png', CX, 130, 46)
        eggs(img, D(img))
        if kind == 'night':
            arr = np.array(img).astype(np.float32) * np.array([0.42, 0.46, 0.62]); img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
            d.ell(800, 120, 26, 26, (250, 246, 220))                                                    # moon through the skylight
        return img
    if kind == 'gr':
        img = wall_floor(((16, 16, 18), (30, 30, 34)), ((44, 44, 48), (74, 74, 80))); d = D(img)
        for i in range(6): d.poly([(-200 + i * 260, WALL_Y), (-60 + i * 260, 80), (0 + i * 260, 80), (-140 + i * 260, WALL_Y)], (40, 40, 44))
        d.rect(0, 80, W, 92, TRED); d.rect(0, WALL_Y - 8, W, WALL_Y, TRED)
        screen_frame(d, DISP[0], DISP[1], DISP[0] + DISP[2], DISP[1] + DISP[3], bez=(8, 8, 10), glow=(90, 14, 20))
        d.text(CX, 740, 'GAZOO RACING', 40, (240, 240, 244), path=FONT_X)
        return img
    if kind == 'twins':
        img = wall_floor(((226, 40, 50), (196, 20, 32)), ((60, 62, 66), (98, 100, 104))); d = D(img)
        d.rect(CX, 0, W, WALL_Y, (24, 70, 160))                                                          # Toyota red | Subaru blue
        d.rect(CX - 4, 0, CX + 4, WALL_Y, (255, 255, 255))
        for i in range(6):                                                                               # six-star cluster, generic
            d.text(CX + 140 + (i % 3) * 60, 760 + (i // 3) * 54, '*', 64, (255, 255, 255))
        screen_frame(d, DISP[0], DISP[1], DISP[0] + DISP[2], DISP[1] + DISP[3], glow=(250, 250, 250))
        paste_logo(img, 'logo_sym.png', 180, 790, 76)
        return img
    if kind == 'ev':
        img = wall_floor(((236, 246, 240), (214, 232, 222)), ((200, 206, 204), (236, 240, 238))); d = D(img)
        for x in range(60, W, 200):
            d.rect(x, 760, x + 70, 880, (250, 250, 250), r=12, ol=(120, 170, 140), w=4); d.rect(x + 26, 790, x + 44, 812, (60, 190, 120), r=3)
        d.rect(0, 70, W, 82, (60, 190, 120))
        screen_frame(d, DISP[0], DISP[1], DISP[0] + DISP[2], DISP[1] + DISP[3], glow=(220, 240, 228))
        d.text(CX, 120, 'ELECTRIFIED', 40, (40, 120, 80), path=FONT_X)
        return img
    if kind == 'street':
        img = Image.new('RGB', (W * K, H * K), (186, 216, 240)); d = D(img)
        d.rect(0, 120, W, 940, (236, 236, 238)); d.rect(0, 120, W, 190, (255, 255, 255)); d.rect(0, 184, W, 192, TRED)
        paste_logo(img, 'logo.png', CX, 156, 40)
        d = D(img)
        d.rect(60, 240, 860, 720, (60, 70, 84)); d.rect(72, 252, 848, 708, (150, 186, 214))              # showroom window
        d.rect(0, 940, W, 1100, (180, 180, 176)); d.rect(0, 1100, W, H, (112, 114, 118))                  # pavement + road
        for x in range(0, W, 160): d.rect(x, 1460, x + 90, 1476, (236, 236, 230))
        d.rect(880, 760, 960, 960, (70, 74, 80), r=8); d.rect(890, 780, 950, 830, (240, 200, 60), r=4)   # ticket machine
        d.text(920, 806, 'TAKE A', 12, (40, 30, 10), path=FONT_X); d.text(920, 822, 'NUMBER', 12, (40, 30, 10), path=FONT_X)
        return img
    return Image.new('RGB', (W * K, H * K), (0, 0, 0))

@lru_cache(None)
def cabin(kind):
    return cabin_base((206, 206, 210), (176, 176, 182), (120, 122, 128))

def background(sc, t):
    return {1: lambda: bg('show'), 2: lambda: bg('gr'), 3: lambda: bg('twins'), 4: lambda: bg('ev'), 5: lambda: bg('street'),
            6: lambda: cabin('p'), 7: lambda: bg('night'), 8: lambda: bg('show')}[sc]()

def cow(img, x, fy, t, s=1.0, asleep=False):
    d = D(img)
    jx = (math.sin(t * 55) * 2.5 if not asleep else 0)                     # massage chair buzz
    cx = x + jx
    d.rect(cx - 90 * s, fy - 200 * s, cx + 90 * s, fy - 60 * s, (120, 40, 44), r=30 * s, ol=OL, w=3)     # chair back
    d.rect(cx - 110 * s, fy - 90 * s, cx + 110 * s, fy - 20 * s, (140, 50, 54), r=20 * s, ol=OL, w=3)
    d.rect(cx - 70 * s, fy - 20 * s, cx - 56 * s, fy, (40, 40, 44)); d.rect(cx + 56 * s, fy - 20 * s, cx + 70 * s, fy, (40, 40, 44))
    d.ell(cx, fy - 120 * s, 64 * s, 60 * s, (250, 250, 248), OL, 3)                                    # body
    d.ell(cx - 26 * s, fy - 130 * s, 20 * s, 16 * s, (30, 30, 32)); d.ell(cx + 30 * s, fy - 100 * s, 16 * s, 12 * s, (30, 30, 32))
    hy = fy - 196 * s
    for sd in (-1, 1):
        d.poly([(cx + sd * 30 * s, hy - 30 * s), (cx + sd * 46 * s, hy - 62 * s), (cx + sd * 40 * s, hy - 26 * s)], (240, 230, 200))
        d.ell(cx + sd * 54 * s, hy - 16 * s, 18 * s, 9 * s, (250, 250, 248), OL, 2)
    d.ell(cx, hy, 44 * s, 46 * s, (250, 250, 248), OL, 3)
    d.ell(cx + 16 * s, hy - 18 * s, 14 * s, 12 * s, (30, 30, 32))
    d.ell(cx, hy + 26 * s, 30 * s, 18 * s, (244, 170, 180), OL, 2)
    for sd in (-1, 1):
        if asleep: d.line([(cx + sd * 16 * s - 7 * s, hy - 4 * s), (cx + sd * 16 * s + 7 * s, hy - 4 * s)], OL, 3 * s)
        else: d.ell(cx + sd * 16 * s, hy - 4 * s, 6 * s, 7 * s, OL)
    if asleep:
        for i in range(3):
            ph = ((t * .6 + i / 3) % 1)
            d.text(cx + 50 * s + 30 * ph * s, hy - 50 * s - 70 * ph * s, 'z', (20 + 16 * ph) * s, (230, 230, 250, int(255 * (1 - ph))))
    else:                                                                    # newspaper
        d.poly([(cx - 70 * s, fy - 150 * s), (cx + 10 * s, fy - 140 * s), (cx + 10 * s, fy - 60 * s), (cx - 70 * s, fy - 70 * s)], (236, 234, 226), OL, 2)
        for i in range(4): d.line([(cx - 60 * s, fy - (130 - i * 16) * s), (cx, fy - (122 - i * 16) * s)], (150, 150, 150), 2 * s)

def corolla_card(img, t):
    """The running gag: the Corolla slides in from the right."""
    for tg in T_GAG:
        a = window(t, tg - .15, tg + 2.0, .1, .3)
        if a > 0:
            k = oc(prog(t, tg - .15, .35))
            x = 1120 - 330 * k
            card = photo_card_cached()
            put(img, card, x, 470, .9, a, rot=4 - 4 * k)
            d = D(img); d.text(x, 300, 'COROLLA', 44 * k + 1, (255, 255, 255, int(255 * a)), stroke=6, sc=(10, 10, 16, int(255 * a)))
@lru_cache(None)
def photo_card_cached(): return photo_card('corolla.jpg', 'TOYOTA COROLLA', TRED, (255, 255, 255), 380)

def wheel_roll(img, t):
    k = prog(t, T_WHEELS + .1, 1.5)
    if 0 < k < 1:
        d = D(img); x = 1100 - 1300 * k; y = 1690 - 40 * abs(math.sin(k * 9)); r = 90; ang = -k * 12
        d.ell(x, y, r, r, (30, 30, 32), OL, 4); d.ell(x, y, 56, 56, (190, 194, 200), OL, 3)
        for i in range(5):
            a_ = ang + i * 2 * math.pi / 5
            d.line([(x, y), (x + 50 * math.cos(a_), y + 50 * math.sin(a_))], (150, 154, 160), 9)
        d.ell(x, y, 14, 14, (110, 114, 120))

def queue(img, t):
    d = D(img)
    for i, (key, x) in enumerate((('cust1', 470), ('cust3', 560), ('cust2', 650), ('cust4', 740), ('walker', 830))):
        st = mk('rest', 'rest', look=-1, brows='flat', tired=.4); st['blink'] = ((t + i * .7) % 3.7) < .12
        st['dy'] = math.sin(t * 1.4 + i) * 2
        npc(img, x, 1000, .36, NPC[key], st)

def behind(img, t, sc):
    if sc == 1:
        show_seq(img, [(0, 'corolla.jpg')], DISP, t, 0); cow(img, 470, 1006, t, .62)
    elif sc == 2:
        show_seq(img, [(0, 'supra.jpg')], DISP, t, SC[2])
        if t >= T_Z4 - .1:                                          # split screen: Supra | Z4
            a = prog(t, T_Z4 - .1, .25); half = DISP[2] // 2
            display(img, 'supra.jpg', DISP[0], DISP[1], half - 4, DISP[3], t, T_Z4, a=a, drift=0)
            display(img, 'z4.jpg', DISP[0] + half + 4, DISP[1], half - 4, DISP[3], t, T_Z4, a=a, drift=0)
            d = D(img); d.rect(DISP[0] + half - 4, DISP[1], DISP[0] + half + 4, DISP[1] + DISP[3], (255, 255, 255, int(255 * a)))
        img.paste((255, 236, 226), (0, 0, W * K, H * K), spot(CX, 80, 60, 420, 900))
    elif sc == 3:
        show_seq(img, [(0, 'gr86.jpg'), (T_THAT - .1, 'twins.jpg')], DISP, t, SC[3])
    elif sc == 4:
        show_seq(img, [(0, 'bz4x.jpg')], DISP, t, SC[4])
    elif sc == 5:
        display(img, 'landcruiser.jpg', 72, 252, 776, 456, t, SC[5])
        queue(img, t)
    elif sc == 6:
        road_life(img, t, 1, phase=(t - SC[6]) * .45, side=(120, 170, 110))
    elif sc == 7:
        show_seq(img, [(0, 'corolla.jpg'), (T_1998 - .15, 'corolla_1998.jpg'), (T_SUPRA2 - .1, 'supra.jpg'), (LE[47] + .1, 'corolla_1998.jpg')],
                 DISP, t, SC[7])
        dim = Image.new('L', img.size, 0); ImageDraw.Draw(dim).rectangle((DISP[0] * K, DISP[1] * K, (DISP[0] + DISP[2]) * K, (DISP[1] + DISP[3]) * K), fill=70)
        img.paste((10, 14, 40), (0, 0, W * K, H * K), dim)
        cow(img, 470, 1006, t, .62, asleep=True)
    elif sc == 8:
        show_seq(img, [(0, 'corolla.jpg')], DISP, t, SC[8]); cow(img, 470, 1006, t, .62)

def front(img, t, sc):
    if sc == 4: wheel_roll(img, t)
    if sc == 6:
        cabin_front(img, t, (70, 72, 78), (24, 26, 30), screen=(470, 1420, 740, 1580), trim=(150, 154, 162), accent2=TRED)
        display(img, 'prius.jpg', 478, 1428, 254, 144, t, SC[6], drift=0)
        d = D(img); d.text(605, 1604, 'PRIUS', 22, (230, 230, 236), path=FONT_X)

def jolt(t, sc, who): return (0, 0)
def cam_extra(t, sc, z, sx, sy):
    if sc == 7: z += 0.06 * io(prog(t, T_1998 - .1, 2.5))              # slow push-in on the confession
    return z, sx, sy

STAGE = {6: dict(walk='none', bx=262, sx=640, fy=1820), 7: dict(walk='slow'), 8: dict(walk='none')}
CAM = {1: dict(z=1.05), 2: dict(z=1.06), 3: dict(z=1.05), 4: dict(z=1.05), 5: dict(z=1.05), 6: dict(z=1.06, follow=30),
       7: dict(z=1.08, follow=55), 8: dict(z=1.04)}
HARD_CUT = {5, 6}                                           # into the test drive, and into the after-hours confession
PUNCH = [(word_t(1, 'Toyota'), .03), (LS[4], .05), (T_ENGINE + .1, .04), (T_ENDED, .05), (T_BUMPER, .05), (T_WHEELS, .05),
         (T_FOUR, .04), (T_1998, .06), (T_DIE, .04), (word_t(50, 'should'), .04)]
SHAKE = [(LS[4], .4, 10), (LS[28], .5, 14), (LS[35], .4, 10)]
FLASH = []
CUTAWAYS = [(T_ENGINE - .05, T_ENGINE + 1.35, 'engine.jpg', 'GR Supra engine bay: BMW B58 straight-six'),
            (T_COOL - .1, T_COOL + 1.4, 'prius.jpg', 'Toyota Prius (2023)')]
B_START = ('up', 'point', dict(brows='up', eyes='wide', smile=1))
def mood(li):
    sc = SCN[li]
    if li < 4: return dict(brows='up', smile=1)
    if sc == 8: return dict(brows='worried', tired=0.55, smile=-1)
    if sc == 6 and li >= 40: return dict(brows='up')
    if li < 16: return dict(brows='flat')
    return dict(brows='angry')
POSE = {0: ('up', 'up', dict(brows='up', eyes='wide', smile=1)), 3: ('clasp', 'present', {}), 15: ('clasp', 'present', {}),
        30: ('clasp', 'present', {}), 7: ('rest', 'rest', {}), 21: ('clasp', 'raise1', {}), 20: ('point', 'point', WD_),
        18: ('point', 'rest', dict(brows='up')), 32: ('clasp', 'offer', {}), 36: ('rest', 'rest', {}), 40: ('open', 'open', dict(brows='up', eyes='wide', smile=1)),
        41: ('chin', 'clasp', {}), 43: ('chin', 'clasp', {}), 45: ('clasp', 'clasp', {}), 47: ('open', 'clasp', {}),
        48: ('rest', 'rest', {}), 49: ('open', 'clasp', {}), 50: ('rest', 'rest', {})}
REACT = {5: ('cross', 'cross', dict(brows='angry', smile=-1)), 13: ('head', 'head', WD_), 21: ('cross', 'cross', A_),
         25: ('shrug', 'shrug', dict(brows='up')), 34: ('head', 'head', WD_, 'early'), 43: ('head', 'rest', dict(brows='up', eyes='wide', smile=-1)),
         47: ('chin', 'rest', dict(brows='worried')), 49: ('rest', 'rest', dict(brows='worried', tired=.6))}
EXTRA_POSES = [('B', T_NUMBER + .2, 'rest', 'offer', dict(brows='flat'))]

INK2, DRED = (24, 20, 16), (176, 20, 30)
def overlays(img, t):
    used = False
    corolla_card(img, t)
    used |= any(window(t, tg - .15, tg + 2.0) > 0 for tg in T_GAG)
    a = window(t, T_50 - .05, SC[2], .1, .3)
    if a > 0: used = True; put(img, stamp_img('50,000,000+ SOLD', (30, 120, 60), 70), CX, 760, popin(t, T_50 - .05, .3) * .85, a, rot=-5)
    a = window(t, T_AUSTRIA - .05, T_ENGINE - .05, .1, .1) or window(t, T_ENGINE + 1.35, LS[11], .1, .25)
    if a > 0: used = True; put(img, info_card((("Built by Magna Steyr", 50, INK2), ("Graz, Austria", 58, DRED))), CX, 760, .85, a, rot=-1.5)
    a = window(t, T_ENDED - .05, LS[15], .1, .3)
    if a > 0: used = True; put(img, stamp_img('DISCONTINUED', RED, 84), CX, 740, popin(t, T_ENDED - .05, .3) * .85, a, rot=-9)
    a = window(t, T_SUBARU - .05, T_THAT - .1, .1, .2)
    if a > 0: used = True; put(img, stamp_img('BUILT BY SUBARU', (24, 70, 160), 70), CX, 740, popin(t, T_SUBARU - .05, .3) * .85, a, rot=-5)
    a = window(t, T_BUMPER - .05, SC[4], .1, .3)
    if a > 0:
        used = True; d = D(img); k = popin(t, T_BUMPER - .05, .3)
        for bx_ in (222, 655):
            d.ell(bx_, 438, 105 * k, 42 * k, None, (255, 230, 40, int(255 * a)), 9)
        d.text(CX, 720, 'SPOT THE DIFFERENCE', 44 * k + 1, (255, 255, 255, int(255 * a)), stroke=7, sc=(10, 10, 16, int(255 * a)))
    a = window(t, T_BZ4X - .05, LS[26], .1, .3)
    if a > 0:
        used = True; d = D(img); k = popin(t, T_BZ4X - .05, .3)
        d.text(CX, 760, 'bZ4X', 110 * k + 1, (255, 255, 255, int(255 * a)), stroke=8, sc=(10, 10, 16, int(255 * a)))
        if t >= T_JUSTBZ - .1:
            c = prog(t, T_JUSTBZ - .1, .25)
            d.line([(CX - 10, 790), (CX - 10 + 150 * c, 730)], RED + (int(255 * a),), 14)
    a = window(t, T_2022 - .05, LS[30] - .1, .1, .3)
    if a > 0: used = True; put(img, stamp_img('RECALL 2022', RED, 80), CX, 740, popin(t, T_2022 - .05, .3) * .85, a, rot=-7)
    a = window(t, T_JAPAN - .05, SC[6], .1, .3)
    if a > 0:
        used = True
        put(img, info_card((("Japan: wait up to", 54, INK2), ("4 years", 74, DRED), ("orders suspended (2022)", 48, INK2))), CX, 560,
            popin(t, T_JAPAN - .05, .35), a, rot=-1.5)
    a = window(t, T_1997 - .05, T_COOL - .15, .1, .2)
    if a > 0:
        used = True; put(img, info_card((("1997:", 64, DRED), ("first mass-produced", 50, INK2), ("hybrid car", 50, INK2))), CX, 560,
                         popin(t, T_1997 - .05, .35), a, rot=-2)
    a = window(t, T_DIE - .05, LS[46] + .9, .1, .3)
    if a > 0:
        used = True
        put(img, info_card((("Consumer Reports:", 50, INK2), ("Toyota ranked No. 1", 58, DRED), ("for reliability", 50, INK2))), CX, 760,
            popin(t, T_DIE - .05, .35), a, rot=1.5)
    return used

def cues(add, sfx):
    for tg in T_GAG: add(tg - .15, sfx.whoosh(.3, 30), .3); add(tg + .2, sfx.ding(1568, .9), .2); add(tg + .32, sfx.ding(2093, .9), .14)
    add(T_50 - .05, sfx.stamp(), .3)
    for c in CUTAWAYS: add(c[0] - .05, sfx.whoosh(.25, 30), .3)
    add(T_ENGINE + .15, sfx.vroom(), .35)
    add(T_Z4 - .1, sfx.pop(), .25); add(T_ENDED - .05, sfx.stamp(), .35); add(T_ENDED + .1, sfx.slide_down(), .2)
    add(T_SUBARU - .05, sfx.stamp(), .3); add(T_THAT - .1, sfx.pop(), .2)
    add(T_BUMPER - .05, sfx.sparkle(), .25)
    add(T_BZ4X, sfx.pop(), .25); add(T_JUSTBZ - .1, sfx.whoosh(.2, 40), .25)
    add(T_2022 - .05, sfx.stamp(), .3)
    for k in range(5): add(T_WHEELS + .15 + k * .3, sfx.thump(.15), .25)
    add(T_WHEELS + 1.5, sfx.crash(.6), .25)
    add(T_NUMBER, sfx.coin_clink(), .3)
    add(T_JAPAN - .05, sfx.stamp(), .25); add(T_FOUR, sfx.buzzer(.3), .2)
    add(T_1997 - .05, sfx.pop(), .25); add(T_COOL - .1, sfx.sparkle(), .25)
    add(T_1998 - .1, sfx.boom(.8), .25); add(T_DIE, sfx.thump(), .3)
    add(T_SUPRA2, sfx.vroom(.6), .2)
    add(LS[48] - .25, sfx.slide_down(), .18)

FINAL = [("The real Toyota", 76, TAG), ("dealership experience.", 66, TAG), ("Which brand", 60, (255, 255, 255)),
         ("should he visit next?", 60, (255, 255, 255)), ("Comment below.", 54, (210, 214, 224))]
THUMB = [("THE REAL TOYOTA", 100, (255, 255, 255)), ("DEALERSHIP", 104, TAG), ("EXPERIENCE", 104, (255, 255, 255))]
ONSCREEN = (['EMPLOYEE', 'OF THE MONTH', 'SINCE', '1937', 'GAZOO RACING', 'ELECTRIFIED', 'TAKE A', 'NUMBER', 'PRIUS', 'COROLLA',
             'TOYOTA COROLLA', '50,000,000+ SOLD', 'Built by Magna Steyr', 'Graz, Austria', 'DISCONTINUED', 'BUILT BY SUBARU',
             'SPOT THE DIFFERENCE', 'bZ4X', 'RECALL 2022', 'Japan: wait up to', '4 years', 'orders suspended (2022)',
             '1997:', 'first mass-produced', 'hybrid car', 'Consumer Reports:', 'Toyota ranked No. 1', 'for reliability']
            + [c[3] for c in CUTAWAYS] + [f[0] for f in FINAL])
