"""Tesla episode: sets, real-photo displays, cutaways, overlays, poses and cues for src/engine.py.
Running gag: everything is 'in the app' (salesman holds out his phone, notification ding).
Background oddity (never mentioned): a penguin plugged into a wall charger, battery bar filling on its belly.
Wall easter eggs: 'EMPLOYEE OF THE MONTH' frame holding a smartphone; a 'DELIVERY ESTIMATE' clock with no hands."""
from engine import *
from PIL import ImageEnhance

VOICE = os.path.expanduser('~/.cache/real-dealership/tesla/voice.wav')
FAST = False
TRED = (214, 26, 36)
SALES = dict(skin=hexc('f0c6a2'), skin2=hexc('d9a882'), hair=hexc('e3bd57'), suit=hexc('3a3d44'), suit2=hexc('2a2c32'),
             shirt=hexc('141416'), tie=None, pants=hexc('202226'), shoe=hexc('f2f2f2'), glasses=False, hairstyle='part', lids=0.45)
def badge(d, x, y):
    d.rect(x - 16, y - 12, x + 16, y + 12, (245, 245, 248), r=4)
    d.rect(x - 9, y - 8, x + 9, y - 5, TRED); d.rect(x - 2, y - 6, x + 2, y + 9, TRED)
FOCUS = {'interior.jpg': (0.42, 0.55), 'screen.jpg': (0.5, 0.5), 'doorhandle.jpg': (0.4, 0.5), 'cybertruck.jpg': (0.42, 0.5),
         'cybertruck_b.jpg': (0.5, 0.6), 'roadster_b.jpg': (0.5, 0.6), 'modely.jpg': (0.5, 0.55), 'model3_b.jpg': (0.5, 0.55)}
def grade(im):                                              # one cool, crisp grade for every photo in this video
    im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(0.9)).enhance(1.08)
    return Image.blend(im, Image.new('RGB', im.size, (226, 236, 252)), 0.05)

# ---- key times
L = SCRIPT.LINES
T_APP = [word_t(li, 'app') for li in range(NL) if ' app' in L[li][1].lower()]
T_399, T_DOUBLE = word_t(7, '$39,900'), word_t(9, 'double')
T_TOUGH, T_46, T_FALL = word_t(10, 'tough'), word_t(11, 'Forty-six'), word_t(11, 'fall')
T_GLUE = word_t(13, 'glue')
T_595, T_SCREEN, T_CEIL = word_t(15, '$595'), word_t(16, 'touchscreen'), word_t(18, 'ceiling')
T_99, T_SUBS = word_t(22, '$99'), word_t(24, 'Subscription')
T_BRAKE = LE[26] + 0.18
T_POPS, T_HIDDEN, T_2027 = word_t(32, 'pops'), word_t(34, 'hidden'), word_t(36, '2027')
T_2017, T_2020, T_2028 = word_t(38, '2017'), word_t(38, '2020'), word_t(40, '2028')
T_CONF, T_GARAGE = word_t(44, 'Confession'), word_t(46, 'This')
SC = {i + 1: s for i, s in enumerate(SCENES)}

# ---- sets
def wall_floor(wall, floor):
    arr = np.concatenate([grad(WALL_Y * K, W * K, *wall), grad((H - WALL_Y) * K, W * K, *floor)])
    return Image.fromarray(arr.astype(np.uint8))
def grad(h, w, c0, c1):
    a = np.linspace(0, 1, h)[:, None, None]
    return np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3))
DISP = (99, 196, 720, 470)                                  # LED wall box (x0, y0, w, h)

def easter_eggs(d):
    d.rect(26, 706, 196, 900, (40, 40, 44), r=6); d.rect(36, 716, 186, 890, (250, 250, 250), r=3)
    d.text(111, 734, 'EMPLOYEE', 18, (30, 30, 34), path=FONT_X); d.text(111, 756, 'OF THE MONTH', 15, (30, 30, 34), path=FONT_X)
    d.rect(86, 772, 136, 872, (22, 22, 26), r=10); d.rect(91, 780, 131, 862, (60, 120, 220), r=4)      # the phone
    d.rect(104, 812, 118, 816, (255, 255, 255)); d.rect(109, 812, 113, 830, (255, 255, 255))
    d.ell(840, 790, 62, 62, (250, 250, 250), (40, 40, 44), 7)                                            # handless clock
    for a in range(12):
        r = math.radians(a * 30); d.line([(840 + 48 * math.cos(r), 790 + 48 * math.sin(r)), (840 + 54 * math.cos(r), 790 + 54 * math.sin(r))], (40, 40, 44), 4)
    d.text(840, 880, 'DELIVERY ESTIMATE', 15, (60, 60, 66), path=FONT_X)

@lru_cache(None)
def bg(kind):
    if kind == 'gallery':
        img = wall_floor(((250, 250, 251), (236, 237, 240)), ((214, 216, 220), (244, 244, 246))); d = D(img)
        d.rect(0, 0, W, 70, (255, 255, 255)); d.rect(0, 66, W, 72, (220, 222, 226))
        for x in (140, 459, 778): d.rect(x - 110, 30, x + 110, 42, (255, 252, 240), r=6)
        for x in range(0, W, 240): d.line([(x, 72), (x, WALL_Y)], (228, 229, 232), 3)
        d.rect(0, WALL_Y - 6, W, WALL_Y, (200, 202, 206))
        for i, y in enumerate(range(WALL_Y + 70, H, 150)): d.line([(0, y), (W, y)], (230, 231, 234), 2)
        screen_frame(d, DISP[0], DISP[1], DISP[0] + DISP[2], DISP[1] + DISP[3], glow=(230, 232, 238))
        easter_eggs(d)
        d.rect(500, 800, 560, 900, (246, 246, 248), r=14, ol=(200, 200, 206), w=3)                     # wall charger
        d.rect(520, 820, 540, 832, (60, 200, 120), r=4)
        paste_logo(img, 'logo.png', CX, 132, 56)
        return img
    if kind == 'cyber':
        img = wall_floor(((70, 74, 80), (112, 116, 122)), ((56, 58, 62), (92, 94, 98))); d = D(img)
        for i in range(-2, 8):
            x = i * 170
            d.poly([(x, 80), (x + 170, 80), (x + 85, 520)], (98, 102, 110)); d.poly([(x + 85, 520), (x + 255, 520), (x + 170, 80)], (84, 88, 96))
            d.poly([(x, WALL_Y), (x + 170, WALL_Y), (x + 85, 520)], (90, 94, 102))
        d.rect(0, 0, W, 80, (40, 42, 46)); d.rect(0, 74, W, 80, (230, 232, 236))
        d.rect(0, WALL_Y - 8, W, WALL_Y, (190, 194, 200))
        screen_frame(d, DISP[0], DISP[1], DISP[0] + DISP[2], DISP[1] + DISP[3], glow=(150, 156, 166))
        paste_logo(img, 'logo.png', 900, 760, 70)
        return img
    if kind == 'stage':
        img = wall_floor(((18, 18, 22), (34, 34, 40)), ((40, 40, 46), (70, 70, 78))); d = D(img)
        screen_frame(d, DISP[0], DISP[1], DISP[0] + DISP[2], DISP[1] + DISP[3], bez=(8, 8, 10), glow=(60, 20, 24))
        for x in (40, 878):
            d.rect(x - 6, 820, x + 6, 1000, (200, 170, 90)); d.ell(x, 816, 16, 16, (220, 190, 100))
        d.arc(459, 900, 420, 80, 0, 180, (150, 20, 30), 14)                                             # velvet rope
        d.text(CX, 740, 'COMING SOON', 46, (230, 230, 236), path=FONT_X)
        paste_logo(img, 'logo.png', CX, 120, 56)
        return img
    if kind == 'garage':
        img = wall_floor(((176, 168, 152), (150, 142, 128)), ((120, 118, 114), (150, 148, 142))); d = D(img)
        for y in range(90, WALL_Y, 34): d.line([(0, y), (W, y)], (162, 154, 140), 2)                    # breeze-block wall
        d.rect(0, 0, W, 80, (96, 90, 82))
        d.rect(-10, 120, 140, 930, (210, 210, 206), ol=(120, 120, 116), w=6)                            # garage door
        for y in range(150, 930, 54): d.line([(0, y), (138, y)], (170, 170, 166), 4)
        d.rect(150, 150, 300, 330, (196, 160, 110), ol=(110, 80, 50), w=4)                               # pegboard + tools
        for x in range(162, 300, 16):
            for y in range(162, 330, 16): d.ell(x, y, 2, 2, (120, 92, 60))
        d.line([(180, 180), (200, 300)], (120, 120, 130), 8); d.ell(240, 220, 22, 22, None, (200, 40, 40), 6)
        d.rect(268, 180, 278, 290, (70, 70, 76))
        d.rect(170, 74, 760, 190, (196, 150, 96), ol=(130, 92, 50), w=4)                                # cardboard sign
        d.text(465, 132, 'TESLA DEALERSHIP', 56, (200, 30, 36), path=FONT_B)
        d.line([(195, 172), (735, 168)], (200, 30, 36), 4)
        d.rect(300, 240, 760, 560, (226, 226, 220), r=4)                                                 # the 'LED wall': a printout
        for cx_, cy_ in ((310, 246), (750, 246), (310, 554), (750, 554)): d.rect(cx_ - 22, cy_ - 8, cx_ + 22, cy_ + 8, (236, 220, 150), r=2)
        d.rect(780, 760, 940, 940, (60, 140, 70), r=10, ol=(30, 60, 34), w=4)                            # lawn mower
        d.rect(800, 700, 812, 770, (40, 40, 44)); d.line([(806, 700), (900, 640)], (40, 40, 44), 8)
        d.ell(800, 940, 20, 20, (30, 30, 32)); d.ell(920, 940, 20, 20, (30, 30, 32))
        d.rect(500, 800, 560, 900, (246, 246, 248), r=14, ol=(200, 200, 206), w=3)                     # same charger, extension lead
        d.line([(530, 900), (600, 940), (980, 936)], (240, 140, 20), 6)
        return img
    if kind == 'drive':
        img = Image.new('RGB', (W * K, H * K), (178, 210, 236)); d = D(img)
        d.rect(0, 560, W, 900, (110, 160, 100))
        for x, h_, col in ((20, 260, (232, 224, 206)), (330, 300, (214, 204, 186))):
            d.rect(x, 600 - h_, x + 280, 760, col); d.poly([(x - 20, 600 - h_), (x + 140, 520 - h_), (x + 300, 600 - h_)], (150, 70, 60))
            d.rect(x + 40, 640 - h_, x + 110, 700 - h_, (150, 190, 220)); d.rect(x + 170, 640 - h_, x + 240, 700 - h_, (150, 190, 220))
        d.rect(10, 520, 320, 760, (110, 100, 92))                                                        # garage (open)
        d.rect(30, 540, 300, 760, (70, 64, 58))
        d.rect(-10, 880, W, H, (128, 128, 132))                                                          # driveway
        for y in range(940, H, 90): d.line([(0, y), (W, y)], (140, 140, 144), 3)
        d.rect(640, 150, 1000, 400, (240, 240, 240), ol=(60, 60, 66), w=8)                               # billboard
        d.rect(800, 400, 830, 880, (80, 80, 86))
        d.rect(0, 860, W, 900, (220, 220, 214))                                                         # fence rail
        for x in range(0, W, 46): d.rect(x, 800, x + 18, 890, (236, 236, 230))
        return img
    return Image.new('RGB', (W * K, H * K), (0, 0, 0))

@lru_cache(None)
def cabin(kind):
    img = cabin_base((30, 30, 34), (22, 22, 26), (40, 40, 46))
    return img

def background(sc, t):
    if sc in (1, 3): return bg('gallery')
    if sc == 2: return bg('cyber')
    if sc in (4, 5): return cabin('t')
    if sc == 6: return bg('stage')
    if sc == 7: return bg('gallery') if t < T_GARAGE else bg('garage')
    return bg('drive')

# ---- live layers
def penguin(img, x, fy, t, s=1.0, charge0=0.0, walking=False):
    d = D(img)
    sway = math.sin(t * (9 if walking else 2.2)) * (8 if walking else 3)
    cx = x + sway * .3
    d.ell(cx - 26 * s, fy - 4, 16 * s, 7 * s, (244, 150, 30)); d.ell(cx + 26 * s, fy - 4, 16 * s, 7 * s, (244, 150, 30))
    d.poly(spline([(cx - 52 * s, fy - 20 * s), (cx - 58 * s, fy - 100 * s), (cx - 36 * s, fy - 160 * s), (cx, fy - 176 * s),
                   (cx + 36 * s, fy - 160 * s), (cx + 58 * s, fy - 100 * s), (cx + 52 * s, fy - 20 * s)], 5), (22, 24, 30), OL, 3)
    d.poly(spline([(cx - 34 * s, fy - 24 * s), (cx - 38 * s, fy - 90 * s), (cx, fy - 128 * s), (cx + 38 * s, fy - 90 * s),
                   (cx + 34 * s, fy - 24 * s)], 5), (246, 246, 246))
    for sd in (-1, 1):
        d.ell(cx + sd * 15 * s, fy - 148 * s, 8 * s, 9 * s, (255, 255, 255)); d.ell(cx + sd * 15 * s, fy - 146 * s, 4 * s, 5 * s, OL)
        d.poly([(cx + sd * 50 * s, fy - 120 * s), (cx + sd * (70 + 6 * math.sin(t * 6)) * s, fy - 60 * s), (cx + sd * 50 * s, fy - 60 * s)], (22, 24, 30))
    d.poly([(cx - 10 * s, fy - 136 * s), (cx + 10 * s, fy - 136 * s), (cx, fy - 120 * s)], (244, 150, 30))
    lvl = clamp(charge0 + t * 0.012)                       # battery on its belly, slowly charging
    d.rect(cx - 20 * s, fy - 88 * s, cx + 20 * s, fy - 62 * s, (40, 40, 44), r=4)
    d.rect(cx - 17 * s, fy - 85 * s, cx - 17 * s + 34 * s * lvl, fy - 65 * s, (70, 210, 110), r=2)
    return cx

def phone_glow(img, t):
    for ta in T_APP:
        a = window(t, ta - .25, ta + 1.1, .15, .3)
        if a > 0:
            d = D(img); hx, hy = 330, 1216
            for r, al in ((70, 40), (46, 70), (26, 110)): d.ell(hx, hy, r, r, (120, 200, 255, int(al * a)))
            d.rect(hx - 16, hy - 52, hx + 16, hy + 6, (30, 30, 34), r=6); d.rect(hx - 12, hy - 46, hx + 12, hy, (70, 140, 240), r=3)
            d.rect(hx - 6, hy - 34, hx + 6, hy - 31, (255, 255, 255)); d.rect(hx - 2, hy - 33, hx + 2, hy - 18, (255, 255, 255))

def speed_at(t):
    """Test-drive road speed: cruising, then the phantom stop."""
    if t < SC[4]: return 0
    if t < T_BRAKE: return 0.55
    return 0.55 * max(0, 1 - (t - T_BRAKE) / .12) if t < LS[30] else 0.55 * prog(t, LS[30], 1.5)
def phase_at(t):
    if t < T_BRAKE: return (t - SC[4]) * .55
    if t < LS[30]: return (T_BRAKE - SC[4]) * .55 + .03
    p = prog(t, LS[30], 1.5)
    return (T_BRAKE - SC[4]) * .55 + .03 + .55 * 1.5 * p * p / 2

def behind(img, t, sc):
    d = D(img)
    if sc == 1:
        show_seq(img, [(0, 'modely.jpg')], DISP, t, 0)
        penguin(img, 470, 1000, t, .7, 0.1)
        d = D(img); d.line([(500, 940), (510, 900), (530, 880)], (60, 60, 66), 5)
    elif sc == 2:
        show_seq(img, [(0, 'cybertruck_b.jpg')], DISP, t, SC[2])
        k = prog(t, T_FALL + .15, .55)                              # a steel strip drops off the display onto the floor
        if k > 0:
            y = 640 + 330 * k * k; rot = 26 * k
            d.poly([(250 + rot, y - 10), (640 + rot, y - 10 + rot * .6), (640 + rot, y + 6 + rot * .6), (250 + rot, y + 6)], (196, 200, 206), (90, 94, 100), 3)
    elif sc == 3:
        show_seq(img, [(0, 'interior.jpg'), (T_SCREEN - .2, 'screen.jpg'), (LS[19], 'model3_b.jpg')], DISP, t, SC[3])
        penguin(img, 470, 1000, t, .7, 0.3)
    elif sc in (4, 5):
        road_life(img, t, speed_at(t), phase=phase_at(t) if sc == 4 else 0.31,
                  side=(108, 150, 96) if sc == 4 else (170, 166, 160))
        if sc == 5:                                                 # parked: kerb-side shop fronts in the rear window
            d = D(img)
            for x in (120, 330, 560): d.rect(x, 380, x + 170, 470, (196, 120, 90)); d.rect(x + 20, 400, x + 150, 450, (150, 200, 230))
    elif sc == 6:
        show_seq(img, [(0, 'roadster_b.jpg')], DISP, t, SC[6])
        img.paste((255, 246, 230), (0, 0, W * K, H * K), spot(CX, 80, 60, 420, 900))
    elif sc == 7:
        if t < T_GARAGE:
            show_seq(img, [(0, 'modely.jpg')], DISP, t, SC[7]); penguin(img, 470, 1000, t, .7, 0.5)
        else:
            display(img, 'modely.jpg', 314, 252, 432, 296, t, T_GARAGE, drift=0)
            penguin(img, 600, 1000, t, .7, 0.5)
    elif sc == 8:
        display(img, 'model3.jpg', 652, 162, 336, 226, t, SC[8])
        d = D(img); d.text(820, 372, 'ORDER ONLINE', 26, (30, 30, 34), path=FONT_X)
        x = 1000 - 60 * (t - SC[8])
        if x > -100: penguin(img, x, 930, t, .55, 0.6, walking=True); d = D(img); d.line([(x + 30, 920), (x + 200, 930), (330, 760)], (240, 140, 20), 4)

@lru_cache(None)
def spot(cx, top, w0, w1, h, a=60):
    cone = Image.new('L', (W * K, H * K), 0)
    ImageDraw.Draw(cone).polygon([(p * K, q * K) for p, q in [(cx - w0, top), (cx + w0, top), (cx + w1, top + h), (cx - w1, top + h)]], fill=a)
    return cone.filter(ImageFilter.GaussianBlur(28 * K))

def front(img, t, sc):
    if sc in (4, 5):
        cabin_front(img, t, (34, 34, 38), (20, 22, 26), screen=(430, 1410, 800, 1620), roof_console=True, trim=(236, 236, 232), accent2=TRED)
        display(img, 'model3_b.jpg', 440, 1420, 350, 190, t, SC[sc], drift=0, a=.95)
        d = D(img); d.text(615, 1640, 'MODEL 3', 22, (220, 220, 226), path=FONT_X)
    phone_glow(img, t)

def jolt(t, sc, who):
    if sc == 4 and T_BRAKE <= t < T_BRAKE + .7:
        k = math.sin(math.pi * prog(t, T_BRAKE, .7)) * (1 - prog(t, T_BRAKE, .7))
        return (0, -40 * k)
    return (0, 0)

def cam_extra(t, sc, z, sx, sy):
    if sc == 7:
        z = 1.2 - 0.17 * oc(prog(t, T_GARAGE, .9)) if t >= T_GARAGE else 1.2 + 0.03 * prog(t, SC[7], 4)
    if sc == 4 and T_BRAKE <= t < T_BRAKE + .5:
        z += .07 * (1 - oc(prog(t, T_BRAKE, .5)))
    return z, sx, sy

STAGE = {4: dict(walk='none', bx=262, sx=640, fy=1820), 5: dict(walk='none', bx=262, sx=640, fy=1820), 7: dict(walk='none'), 8: dict(walk='slow')}
CAM = {1: dict(z=1.05), 2: dict(z=1.06), 3: dict(z=1.05), 4: dict(z=1.06, follow=30), 5: dict(z=1.1, follow=30), 6: dict(z=1.05),
       7: dict(z=1.2), 8: dict(z=1.04)}
HARD_CUT = {3, 4}                                           # SCENES index: cut straight into the car (test drive, parked)
PUNCH = [(word_t(1, 'Download'), .03), (T_DOUBLE, .05), (T_FALL, .05), (T_595, .05), (T_99, .04), (T_2027, .03), (T_2028, .05),
         (word_t(52, 'door'), .04)]
SHAKE = [(T_BRAKE, .6, 18), (T_FALL + .7, .3, 8)]
FLASH = [(T_GARAGE, .55)]
CUTAWAYS = [(T_TOUGH - .05, T_TOUGH + 1.05, 'cybertruck.jpg', 'Tesla Cybertruck: stainless steel body'),
            (LS[14] + .05, LS[14] + 1.55, 'interior.jpg', 'Tesla Model 3 (2023 update)'),
            (T_POPS - .1, T_POPS + 1.5, 'doorhandle.jpg', 'Tesla flush door handle')]
B_START = ('point', 'open', dict(brows='up', smile=1))
def mood(li):
    sc = SCN[li]
    if li < 6: return dict(brows='up', smile=1)
    if sc == 8: return dict(brows='worried', tired=0.5, smile=-1)
    if li < 14: return dict(brows='flat')
    return dict(brows='angry')
POSE = {3: ('rest', 'rest', {}), 9: ('raise1', 'clasp', {}), 11: ('clasp', 'present', {}), 12: ('head', 'head', WD_),
        18: ('clasp', 'up', {}), 26: ('clasp', 'clasp', {}), 29: ('point', 'point', A_), 31: ('point', 'shrug', A_),
        35: ('head', 'head', WD_), 44: ('chin', 'clasp', {}), 46: ('open', 'open', {}), 50: ('rest', 'rest', {}),
        52: ('open', 'rest', {}), 28: ('up', 'up', WD_)}
REACT = {9: ('head', 'head', WD_), 24: ('chin', 'rest', dict(brows='worried', smile=-1)), 30: ('cross', 'cross', A_),
         40: ('cross', 'cross', dict(brows='angry', smile=-1)), 46: ('head', 'head', WD_, 'early'), 54: ('rest', 'rest', dict(brows='worried', tired=.6))}
EXTRA_POSES = [('S', T_BRAKE, 'up', 'up', dict(eyes='wide')), ('S', T_BRAKE + .7, 'clasp', 'clasp', {})]

# ---- overlays (all after the 3 s hook)
INK2, DRED = (24, 20, 16), (176, 20, 30)
def chips(img, t, rows, y0):
    d = D(img)
    for i, (txt, col, tn) in enumerate(rows):
        if t < tn - .05: continue
        k = popin(t, tn - .05, .3); w_ = font(40).getlength(txt) / K * K
        y = y0 + i * 84
        d.rect(CX - (w_ / 2 + 30) * k, y - 34, CX + (w_ / 2 + 30) * k, y + 34, col + (235,), r=16)
        if k > .6: d.text(CX, y, txt, 40, (255, 255, 255))
def overlays(img, t):
    used = False
    a = window(t, T_399 - .1, SC[2] + 9, .1, .3) if t < T_FALL else 0
    if a > 0:
        used = True
        put(img, price_tag('$39,900', 'ANNOUNCED 2019', TAG), CX, 770, popin(t, T_399 - .1, .35) * .9, a, rot=-3)
        if t >= T_DOUBLE - .05: put(img, stamp_img('NEARLY 2x', RED), CX + 120, 700, popin(t, T_DOUBLE - .05, .3) * .8, a, rot=-12)
    a = window(t, T_46 - .05, LS[14] - .1, .1, .3)
    if a > 0:
        used = True; put(img, stamp_img('46,096 RECALLED', RED, 76), CX, 760, popin(t, T_46 - .05, .3) * .85, a, rot=-6)
    a = window(t, T_595 - .05, T_SCREEN - .25, .1, .25)
    if a > 0:
        used = True; put(img, price_tag('$595', 'TURN-SIGNAL STALK RETROFIT', TAG, 620), CX, 770, popin(t, T_595 - .05, .35) * .9, a, rot=2)
    a = window(t, T_CEIL - .1, LS[19], .1, .25)
    if a > 0:
        used = True; d = D(img); k = popin(t, T_CEIL - .1, .3); bob = 10 * math.sin(t * 9)
        d.poly([(640, 330 + bob), (720, 430 + bob), (680, 430 + bob), (680, 560 + bob), (600, 560 + bob), (600, 430 + bob), (560, 430 + bob)],
               TAG + (int(255 * a),), (40, 30, 10, int(255 * a)), 6)
        d.text(640, 610, 'BACKUP GEAR BUTTONS', 34 * k, (255, 255, 255, int(255 * a)), stroke=6, sc=(10, 10, 16, int(255 * a)))
    a = window(t, T_99 - .05, LS[25], .1, .3)
    if a > 0:
        used = True; put(img, price_tag('$99/month', 'FULL SELF-DRIVING (SUPERVISED)', TAG, 640), CX, 560, popin(t, T_99 - .05, .35) * .9, a, rot=-2)
        if t >= T_SUBS - .05: put(img, stamp_img('SUBSCRIPTION ONLY', RED, 70), CX, 700, popin(t, T_SUBS - .05, .3) * .85, a, rot=-8)
    a = window(t, T_2027 - .05, SC[6], .1, .3)
    if a > 0:
        used = True; put(img, info_card((("China plans to ban", 54, INK2), ("hidden door handles", 54, INK2), ("from 2027", 60, DRED))),
                         CX, 560, popin(t, T_2027 - .05, .35), a, rot=-1.5)
    a = window(t, T_2017 - .05, LS[41], .1, .3)
    if a > 0:
        used = True
        chips(img, t, [('2017: ANNOUNCED', (40, 44, 54), T_2017), ('2020: PROMISED', (40, 44, 54), T_2020),
                       ('2028: PRODUCTION?', RED, T_2028)], 720)
    return used

def cues(add, sfx):
    for ta in T_APP: add(ta, sfx.ding(2093, .5), .16); add(ta + .12, sfx.ding(2637, .5), .12)
    add(T_399 + .2, sfx.cha_ching(), .3); add(T_DOUBLE - .05, sfx.stamp(), .35)
    add(T_46 - .05, sfx.stamp(), .3); add(T_FALL + .15, sfx.whoosh(.3, 10), .3); add(T_FALL + .7, sfx.crash(), .45)
    add(T_GLUE, sfx.pop(), .2)
    add(T_595 + .2, sfx.cha_ching(), .3); add(T_CEIL - .05, sfx.sparkle(), .25)
    for c in CUTAWAYS: add(c[0] - .05, sfx.whoosh(.25, 30), .3)
    add(T_99 + .2, sfx.cha_ching(), .3); add(T_SUBS - .05, sfx.stamp(), .3)
    add(T_BRAKE - .05, sfx.screech(.5), .55); add(T_BRAKE + .1, sfx.thump(), .5)
    add(T_2027 - .05, sfx.stamp(), .3)
    for tt in (T_2017, T_2020, T_2028): add(tt - .05, sfx.pop(), .25)
    add(T_CONF, sfx.slide_down(), .2)
    add(T_GARAGE - .05, sfx.boom(), .45); add(T_GARAGE, sfx.crash(.5), .2)
    add(LS[52] - .3, sfx.slide_down(), .18)

FINAL = [("The real Tesla", 76, TAG), ("dealership experience.", 66, TAG), ("Next: the real", 60, (255, 255, 255)),
         ("Toyota dealership.", 60, (255, 255, 255)), ("Which brand after that?", 54, (210, 214, 224))]
THUMB = [("THE REAL TESLA", 104, (255, 255, 255)), ("DEALERSHIP", 104, TAG), ("EXPERIENCE", 104, (255, 255, 255))]
ONSCREEN = (['MODEL 3', 'ORDER ONLINE', 'COMING SOON', 'TESLA DEALERSHIP', 'EMPLOYEE', 'OF THE MONTH', 'DELIVERY ESTIMATE',
             '$39,900', 'ANNOUNCED 2019', 'NEARLY 2x', '46,096 RECALLED', '$595', 'TURN-SIGNAL STALK RETROFIT', 'BACKUP GEAR BUTTONS',
             '$99/month', 'FULL SELF-DRIVING (SUPERVISED)', 'SUBSCRIPTION ONLY', 'China plans to ban', 'hidden door handles',
             'from 2027', '2017: ANNOUNCED', '2020: PROMISED', '2028: PRODUCTION?'] + [c[3] for c in CUTAWAYS] + [f[0] for f in FINAL])
