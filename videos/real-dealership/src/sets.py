"""Full dealership sets: one-point-perspective rooms (ceiling light grid, side walls with windows, glossy floor that
reflects the back wall), real cut-out cars on turntables with mirrored floor reflections and contact shadows, props
(desks, kiosks, plants, pendants, chairs) and glass sheen on screens. Everything static is cached per set."""
from engine import *

FLOOR_Y, CEIL_Y = 1000, 210                     # back wall spans CEIL_Y..FLOOR_Y
BX0, BX1 = 110, 970                             # back wall left/right edge
VP = (459, 640)
SCREEN = (209, 400, 500, 270)                   # x0, y0, w, h of the back-wall screen
CAR_GROUND = 1085

def lerp(a, b, k): return a + (b - a) * k
def grad(h, w, c0, c1):
    a = np.linspace(0, 1, h)[:, None, None]
    return np.broadcast_to(np.array(c0) * (1 - a) + np.array(c1) * a, (h, w, 3))
def grade_rgba(c):
    import engine as _E
    rgb = _E.EP.grade(c.convert("RGB")); rgb.putalpha(c.getchannel('A')); return rgb
def shade(c, k): return tuple(int(max(0, min(255, v * k))) for v in c)

@lru_cache(None)
def cutout(name, w):
    c = Image.open(os.path.join(EPDIR, 'assets', f'cut_{name}.png')).convert('RGBA')
    h = int(c.height * w * K / c.width)
    c = c.resize((int(w * K), h), Image.LANCZOS)
    return grade_rgba(c)

def place_car(img, name, cx, ground, w, refl=0.34, shadow=0.55, floor_blur=2):
    """Real cut-out car standing on the floor: contact shadow, mirrored reflection, then the car."""
    c = cutout(name, w)
    x0, y0 = int(cx * K - c.width / 2), int(ground * K - c.height)
    if shadow:
        sh = Image.new('L', img.size, 0); sd = ImageDraw.Draw(sh)
        sd.ellipse((x0 + c.width * .04, ground * K - 26 * K, x0 + c.width * .96, ground * K + 22 * K), fill=int(255 * shadow))
        sh = sh.filter(ImageFilter.GaussianBlur(16 * K))
        img.paste((8, 8, 10), (0, 0), sh)
    if refl:
        r = c.transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(floor_blur * K))
        g = np.linspace(refl, 0, r.height) ** 1.4 * (np.linspace(1, 0, r.height) > 0)
        g[int(r.height * .55):] = 0
        a = np.asarray(r.getchannel('A'), np.float32) * g[:, None]
        r.putalpha(Image.fromarray(a.astype(np.uint8)))
        img.paste(r, (x0, int(ground * K) - 6 * K), r)
    img.paste(c, (x0, y0), c)
    return x0 / K, y0 / K, c.width / K, c.height / K

def turntable(d, cx, ground, w, rim=(200, 200, 206), top=(60, 60, 66)):
    d.ell(cx, ground + 6, w * .62, 46, shade(top, .7))
    d.ell(cx, ground, w * .62, 42, top, rim, 4)
    d.ell(cx, ground - 2, w * .5, 32, shade(top, 1.15))

def room(T):
    """T: theme dict. Returns the K-scale RGB base image (no cars, no people)."""
    img = Image.new('RGB', (W * K, H * K), T['ceil']); d = D(img)
    # ceiling (perspective) with recessed light panels
    d.poly([(0, 0), (W, 0), (BX1, CEIL_Y), (BX0, CEIL_Y)], T['ceil'])
    for i in range(1, 5):
        k = i / 5; y = CEIL_Y * (1 - (1 - k) ** 1.6)
        d.line([(lerp(0, BX0, y / CEIL_Y), y), (lerp(W, BX1, y / CEIL_Y), y)], shade(T['ceil'], .9), 2)
    for row, (ya, yb) in enumerate(((40, 72), (110, 132), (162, 176))):
        for j in range(-2, 3):
            cxp = VP[0] + j * (300 - row * 75)
            wpx = 110 - row * 28
            d.rect(cxp - wpx / 2, ya, cxp + wpx / 2, yb, T['light'], r=4)
    # back wall
    arr = grad((FLOOR_Y - CEIL_Y) * K, (BX1 - BX0) * K, *T['wall'])
    img.paste(Image.fromarray(arr.astype(np.uint8)), (BX0 * K, CEIL_Y * K))
    d = D(img)
    for x in range(BX0 + T.get('panel_w', 172), BX1, T.get('panel_w', 172)):
        d.line([(x, CEIL_Y), (x, FLOOR_Y)], shade(T['wall'][1], .94), 2)
    d.rect(BX0, CEIL_Y, BX1, CEIL_Y + 10, shade(T['wall'][0], .9))
    d.rect(BX0, FLOOR_Y - 14, BX1, FLOOR_Y, T['skirt'])
    # side walls (with tall windows to the street)
    for side in (-1, 1):
        xe, xw = (0, BX0) if side < 0 else (W, BX1)
        poly = [(xe, 0), (xw, CEIL_Y), (xw, FLOOR_Y), (xe, FLOOR_Y + 180)]
        d.poly(poly, T['side'])
        if T.get('windows', True):
            for k0, k1 in ((.1, .5), (.55, .95)):
                xa, xb = lerp(xe, xw, k0), lerp(xe, xw, k1)
                ya0, ya1 = lerp(0, CEIL_Y, k0) + 40, lerp(0, CEIL_Y, k1) + 40
                yb0, yb1 = lerp(FLOOR_Y + 180, FLOOR_Y, k0) - 30, lerp(FLOOR_Y + 180, FLOOR_Y, k1) - 30
                d.poly([(xa, ya0), (xb, ya1), (xb, yb1), (xa, yb0)], T['sky'])
                d.poly([(xa, lerp(ya0, yb0, .62)), (xb, lerp(ya1, yb1, .62)), (xb, yb1), (xa, yb0)], T.get('street', (150, 160, 150)))
                d.poly([(xa, ya0), (xb, ya1), (xb, ya1 + 60), (xa, ya0 + 140)], (255, 255, 255, 60))      # glass glare
                d.line([(xa, ya0), (xa, yb0)], T['mullion'], 6); d.line([(xb, ya1), (xb, yb1)], T['mullion'], 6)
    # floor: gradient + perspective tiles
    fl = grad((H - FLOOR_Y) * K, W * K, *T['floor'])
    img.paste(Image.fromarray(fl.astype(np.uint8)), (0, FLOOR_Y * K))
    d = D(img)
    d.poly([(0, FLOOR_Y + 180), (BX0, FLOOR_Y), (0, FLOOR_Y)], T['side']); d.poly([(W, FLOOR_Y + 180), (BX1, FLOOR_Y), (W, FLOOR_Y)], T['side'])
    # glossy floor: mirror the lower back wall
    if T.get('gloss', .3):
        band = 330
        crop = img.crop((0, (FLOOR_Y - band) * K, W * K, FLOOR_Y * K)).transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(3 * K))
        m = (np.linspace(T['gloss'], 0, band * K) ** 1.3)[:, None] * np.ones((1, W * K))
        img.paste(crop, (0, FLOOR_Y * K), Image.fromarray((m * 255).astype(np.uint8)))
    d = D(img)
    tl = T.get('tile', shade(T['floor'][1], .93))
    for j in range(-12, 13):
        xb = VP[0] + j * 150
        d.line([(lerp(VP[0], xb, (FLOOR_Y - VP[1]) / (H - VP[1])), FLOOR_Y), (xb, H)], tl, 2)
    y = FLOOR_Y; step = 22
    while y < H:
        d.line([(0, y), (W, y)], tl, 2); step *= 1.32; y += step
    return img

@lru_cache(None)
def _sheen(w, h, a):
    lay = Image.new('L', (int(w * K), int(h * K)), 0); ld = ImageDraw.Draw(lay)
    ld.polygon([(w * .55 * K, 0), (w * .78 * K, 0), (w * .38 * K, h * K), (w * .15 * K, h * K)], fill=a)
    ld.polygon([(w * .83 * K, 0), (w * .88 * K, 0), (w * .48 * K, h * K), (w * .43 * K, h * K)], fill=a // 2)
    return lay.filter(ImageFilter.GaussianBlur(4 * K))
def sheen(img, x0, y0, w, h, a=34):
    """Diagonal glass reflection across a screen (cached mask)."""
    img.paste((255, 255, 255), (int(x0 * K), int(y0 * K)), _sheen(w, h, a))

def screen_slot(d, glow=(0, 0, 0, 0)):
    x0, y0, w, h = SCREEN
    screen_frame(d, x0, y0, x0 + w, y0 + h, glow=glow)

def plant(d, x, fy, s=1.0, pot=(236, 236, 236)):
    d.poly([(x - 34 * s, fy - 80 * s), (x + 34 * s, fy - 80 * s), (x + 26 * s, fy), (x - 26 * s, fy)], pot, shade(pot, .7), 3)
    for i, (dx, dy, r) in enumerate(((-30, -150, 46), (24, -170, 52), (0, -220, 50), (-44, -205, 34), (40, -230, 36), (0, -120, 44))):
        d.ell(x + dx * s, fy + dy * s, r * s, r * s * .9, (52 + i * 8, 120 + i * 6, 64))
    d.line([(x, fy - 80 * s), (x, fy - 200 * s)], (70, 90, 50), 5 * s)

def pendant(d, x, y1, col=(30, 30, 34), lamp=(255, 244, 214)):
    d.line([(x, 0), (x, y1)], (60, 60, 66), 3)
    d.chord(x, y1 + 22, 40, 26, 180, 360, col); d.ell(x, y1 + 22, 26, 6, lamp)

def desk(d, x, fy, s, top=(245, 245, 247), body=(220, 220, 224), screen=True, chair=(30, 30, 34)):
    d.rect(x - 90 * s, fy - 120 * s, x + 90 * s, fy - 106 * s, top, r=4)
    d.rect(x - 80 * s, fy - 106 * s, x + 80 * s, fy, body)
    if screen:
        d.rect(x - 40 * s, fy - 190 * s, x + 40 * s, fy - 136 * s, (26, 26, 30), r=4); d.rect(x - 4 * s, fy - 136 * s, x + 4 * s, fy - 120 * s, (60, 60, 66))
    d.rect(x + 70 * s, fy - 150 * s, x + 120 * s, fy - 70 * s, chair, r=12 * s); d.rect(x + 66 * s, fy - 74 * s, x + 124 * s, fy - 60 * s, chair, r=6)
    d.line([(x + 95 * s, fy - 60 * s), (x + 95 * s, fy)], (90, 90, 96), 5 * s)

def kiosk(d, x, fy, s=1.0, col=(250, 250, 250), scr=(40, 40, 46)):
    d.rect(x - 22 * s, fy - 150 * s, x + 22 * s, fy, col, r=6, ol=shade(col, .8), w=2)
    d.poly([(x - 60 * s, fy - 230 * s), (x + 60 * s, fy - 200 * s), (x + 60 * s, fy - 140 * s), (x - 60 * s, fy - 170 * s)], scr, (20, 20, 22), 3)

def light_cone(img, cx, top, w0, w1, bottom, a=46, col=(255, 248, 230)):
    cone = Image.new('L', img.size, 0)
    ImageDraw.Draw(cone).polygon([(p * K, q * K) for p, q in [(cx - w0, top), (cx + w0, top), (cx + w1, bottom), (cx - w1, bottom)]], fill=a)
    img.paste(col, (0, 0), cone.filter(ImageFilter.GaussianBlur(30 * K)))

def contact_shadow(img, x, fy, w=150, a=70):
    d = D(img); d.ell(x, fy - 4, w / 2, 18, (0, 0, 0, a))
