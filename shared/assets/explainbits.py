"""Pixel props for the ten-episode 'car stuff, explained' series (abs-pumping ... warm-up-myth; videos/<ep>/src).

Small RGBA sprites on a pixel grid; scale with pixanim.grid.up(img, s) (nearest). Callout pills: carbits.pill();
RPM gauge: carbits.rpm_gauge(); poll sticker: overlays.poll(); engine warning lamp: carbits.warn_lamp().
    disc_caliper(rot, clamp, glow)   face-on brake disc + red caliper; clamp 0..1 squeezes / lights the caliper
    pad_section(wear, t)             cutaway: disc edge, pad (friction + backing plate) and the steel wear tab; PAD_TAB(wear)
    wheel_hub(done, hi, n)           face-on hub with n wheel nuts; `done` nuts tightened (green), `hi` glowing
    star_lines(cv, cx, cy, R, k)     full-res star-pattern diagram: numbered nuts, lines drawn in star order up to k
    circle_lines(cv, cx, cy, R, k)   the wrong way: round the circle, red
    headlight(haze)                  headlight front view: housing, chrome reflector, bulb, lens yellowing with haze
    lens_layers(uv, t)               lens cutaway: UV hard-coat (eroding as uv -> 0) over polycarbonate (yellowing)
    coolant_bottle(level, col, sludge, t)  expansion tank with MIN/MAX, coloured coolant, brown sludge settling
    hose(t, block)                   coolant hose cutaway; block 0..1 grows a sludge plug and slows the flow
    car_top(steer, col)              top-down generic car, front wheels steered by `steer` degrees (+ = right)
    traffic_light(state), ss_icon(on)   'red'/'amber'/'green' signal; stop-start 'A' icon (green when active)
    gear_pair(deg)                   small motor pinion driving a big reduction gear (single-speed EV drive)
    thermo(k), pedal(press)          thermometer filling to k; brake pedal + shoe pressed by press 0..1
    torque_graph(cv, x, y, w, h, k)  full-res torque-vs-rpm chart: flat EV line vs rising engine curve, drawn to k
Presenter placement for the whole series: SPOT (same place in every episode).
"""
import math, random
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
from pixanim.grid import outline

NAVY = (26, 26, 46, 255)
STEEL = ((96, 100, 112), (150, 156, 168), (196, 202, 214), (232, 236, 244))
SPOT = dict(open=((200, 1600), 6), mid=((175, 1640), 5), ask=((300, 1600), 9))   # (feet x, y), pixel size per shot


def _img(w, h): return Image.new('RGBA', (w, h), (0, 0, 0, 0))


# ------------------------------------------------------------------ brakes
def disc_caliper(rot=0.0, clamp=0.0, glow=0.0, r=28):
    n = 2 * r + 10; c = n / 2; img = _img(n, n); d = ImageDraw.Draw(img)
    hot = tuple(int(a + (b - a) * glow) for a, b in zip(STEEL[1], (255, 120, 40)))
    d.ellipse((c - r, c - r, c + r, c + r), fill=hot)
    d.ellipse((c - r + 2, c - r + 2, c + r - 2, c + r - 2), outline=STEEL[2])
    for k in range(18):                                              # drilled holes turn with the disc
        a = math.radians(rot + k * 20); rr = r - 6 - 3 * (k % 2)
        x, y = c + rr * math.cos(a), c + rr * math.sin(a); d.rectangle((x - 1, y - 1, x, y), fill=STEEL[0])
    d.ellipse((c - r * 0.5, c - r * 0.5, c + r * 0.5, c + r * 0.5), fill=(70, 74, 86))
    for k in range(5):
        a = math.radians(rot + k * 72); x, y = c + r * 0.3 * math.cos(a), c + r * 0.3 * math.sin(a)
        d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=STEEL[3])
    d.ellipse((c - 4, c - 4, c + 4, c + 4), fill=STEEL[2], outline=STEEL[0])
    squeeze = round(2 * clamp); col = (210 + int(45 * clamp), 40 + int(40 * clamp), 50)
    d.pieslice((c - r - 4 + squeeze, c - r - 4 + squeeze, c + r + 4 - squeeze, c + r + 4 - squeeze), -75, -15, fill=col)
    d.pieslice((c - r + 9, c - r + 9, c + r - 9, c + r - 9), -75, -15, fill=hot)
    d.ellipse((c - r + 13, c - r + 13, c + r - 13, c + r - 13), fill=(70, 74, 86))
    d.ellipse((c - 4, c - 4, c + 4, c + 4), fill=STEEL[2], outline=STEEL[0])
    return outline(img)


def _pad_x(wear):
    th = round(20 - 16 * wear)                                       # friction material thickness (grid px)
    return th, 18 + th                                                # thickness, backing-plate x


def PAD_TAB(wear):
    """Grid point of the wear-tab tip (for sparks); it reaches the disc face (x = 17) once the pad is thin."""
    th, bx = _pad_x(wear); return max(17, bx - 15), 60


def pad_section(wear=0.0, t=0.0):
    img = _img(70, 80); d = ImageDraw.Draw(img)
    d.rectangle((4, 2, 17, 77), fill=STEEL[1])                        # disc edge, scrolling machining marks
    for k in range(10):
        y = 2 + (k * 8 + int(t * 90)) % 76; d.line((5, y, 16, y), fill=STEEL[2])
    d.line((17, 2, 17, 77), fill=STEEL[3])
    th, bx = _pad_x(wear)
    d.rectangle((18, 16, bx - 1, 56), fill=(120, 84, 58))             # friction material
    for k in range(0, 40, 6): d.point((18 + (k * 7) % max(1, th - 1), 18 + k), fill=(150, 108, 76))
    d.rectangle((bx, 12, bx + 6, 60), fill=STEEL[0]); d.line((bx + 1, 13, bx + 1, 59), fill=STEEL[2])
    tx, ty = PAD_TAB(wear)                                             # the steel wear tab: down, then towards the disc
    d.line((bx + 2, 60, bx + 2, 64, tx, 64), fill=(220, 226, 236), width=2)
    d.line((tx, 60, tx, 64), fill=(220, 226, 236), width=2)
    d.rectangle((bx + 7, 26, bx + 14, 46), fill=(200, 46, 56))         # caliper piston
    return outline(img)


# ------------------------------------------------------------------ wheel nuts
STAR = {4: (0, 2, 1, 3), 5: (0, 2, 4, 1, 3), 6: (0, 3, 1, 4, 2, 5)}


def nut_xy(i, n=5, R=17, c=35): a = math.radians(-90 + 360 * i / n); return c + R * math.cos(a), c + R * math.sin(a)


def wheel_hub(done=0, hi=-1, n=5):
    img = _img(70, 70); d = ImageDraw.Draw(img); c = 35
    d.ellipse((2, 2, 68, 68), fill=(58, 60, 70)); d.ellipse((5, 5, 65, 65), fill=STEEL[1])
    for k in range(10):                                              # rim spokes
        a = math.radians(k * 36 + 18)
        d.line((c + 22 * math.cos(a), c + 22 * math.sin(a), c + 30 * math.cos(a), c + 30 * math.sin(a)), fill=STEEL[0], width=2)
    d.ellipse((c - 22, c - 22, c + 22, c + 22), fill=STEEL[2]); d.ellipse((c - 6, c - 6, c + 6, c + 6), fill=(70, 74, 86))
    order = STAR[n]
    for j, i in enumerate(order):
        x, y = nut_xy(i, n)
        tight = j < done; col = (255, 210, 63) if i == hi else ((90, 200, 110) if tight else STEEL[3])
        hexa = [(x + 6 * math.cos(math.radians(60 * k + 30)), y + 6 * math.sin(math.radians(60 * k + 30))) for k in range(6)]
        d.polygon(hexa, fill=col, outline=STEEL[0]); d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=STEEL[0])
    return outline(img)


@lru_cache(4)
def _font(sz):
    import episode
    return episode.font(sz)


def _route(cv, cx, cy, R, order, k, col, n):
    d = ImageDraw.Draw(cv)
    pts = [(cx + R * math.cos(math.radians(-90 + 360 * i / n)), cy + R * math.sin(math.radians(-90 + 360 * i / n))) for i in order]
    for j in range(len(pts) - 1):
        f = min(1.0, max(0.0, k - j))
        if f <= 0: break
        (x0, y0), (x1, y1) = pts[j], pts[j + 1]; ex, ey = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        d.line((x0, y0, ex, ey), fill=NAVY, width=26); d.line((x0, y0, ex, ey), fill=col, width=14)
    for j, (x, y) in enumerate(pts):
        if k + 1 < j + 0.6: continue
        d.ellipse((x - 34, y - 34, x + 34, y + 34), fill=col, outline=NAVY, width=7)
        d.text((x, y + 2), str(j + 1), font=_font(46), fill=NAVY, anchor='mm')


def star_lines(cv, cx, cy, R, k, n=5): _route(cv, cx, cy, R, STAR[n], k, (255, 210, 63, 255), n)
def circle_lines(cv, cx, cy, R, k, n=5): _route(cv, cx, cy, R, tuple(range(n)) + (0,), k, (232, 52, 63, 255), n)


# ------------------------------------------------------------------ headlights
def headlight(haze=0.0):
    img = _img(84, 50); d = ImageDraw.Draw(img)
    d.rounded_rectangle((1, 1, 82, 48), 10, fill=(40, 42, 52))
    for i, (cx, r) in enumerate(((24, 17), (60, 14))):
        d.ellipse((cx - r, 25 - r, cx + r, 25 + r), fill=STEEL[2]); d.ellipse((cx - r + 3, 25 - r + 3, cx + r - 3, 25 + r - 3), fill=STEEL[3])
        d.ellipse((cx - 5, 20, cx + 5, 30), fill=(255, 250, 220)); d.ellipse((cx - 2, 23, cx + 2, 27), fill=(255, 255, 255))
    lens = _img(84, 50); ld = ImageDraw.Draw(lens)
    ld.rounded_rectangle((3, 3, 80, 46), 9, fill=(230, 190, 70, int(215 * haze)))
    rnd = random.Random(3)
    for _ in range(int(160 * haze)):
        x, y = rnd.randrange(6, 78), rnd.randrange(6, 44); ld.point((x, y), fill=(250, 236, 180, int(200 * haze)))
    ld.line((10, 8, 30, 8), fill=(255, 255, 255, int(160 * (1 - haze))), width=2)          # gloss on a clear lens
    img.alpha_composite(lens)
    return outline(img)


def lens_layers(uv=1.0, t=0.0):
    img = _img(96, 40); d = ImageDraw.Draw(img)
    yel = 1 - uv
    pc = (int(180 + 60 * yel), int(214 - 10 * yel), int(236 - 150 * yel), 255)
    d.rectangle((0, 14, 95, 36), fill=pc)                             # polycarbonate lens body
    for x in range(0, 96, 7): d.point((x + 3, 22 + (x // 7) % 3 * 4), fill=(255, 255, 255, 120))
    rnd = random.Random(5)
    for x in range(96):                                               # UV hard-coat: thin, patchy as it wears
        keep = rnd.random() < uv * 1.15
        if keep: d.line((x, 9, x, 13), fill=(120, 200, 255, 255))
        elif uv < 0.6 and rnd.random() < 0.5 * yel: d.point((x, 13), fill=(200, 160, 60, 255))   # crazed surface
    return outline(img)


# ------------------------------------------------------------------ coolant
def coolant_bottle(level=0.7, col=(60, 200, 110), sludge=0.0, t=0.0):
    img = _img(46, 64); d = ImageDraw.Draw(img)
    d.rectangle((17, 0, 29, 7), fill=(40, 42, 52)); d.rectangle((18, 1, 28, 3), fill=(80, 84, 96))
    d.rounded_rectangle((3, 7, 43, 62), 6, fill=(226, 230, 236))
    top = 58 - int(46 * level)
    for x in range(5, 42):                                            # coolant with a small sloshing surface
        y = top + round(1.2 * math.sin(t * 6 + x * 0.35))
        d.line((x, y, x, 59), fill=col)
        d.point((x, y), fill=tuple(min(255, v + 60) for v in col))
    if sludge > 0:
        h = int(18 * sludge); rnd = random.Random(7)
        d.rectangle((5, 59 - h, 41, 59), fill=(108, 76, 40))
        for _ in range(int(40 * sludge)):
            x, y = rnd.randrange(5, 41), rnd.randrange(max(9, 59 - h - 10), 59); d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=(90, 62, 32))
    d.rectangle((6, 9, 9, 58), fill=(255, 255, 255, 140))             # plastic sheen
    for y, lab in ((18, 'MAX'), (48, 'MIN')): d.line((32, y, 41, y), fill=(40, 42, 52), width=1)
    return outline(img)


def hose(t=0.0, block=0.0):
    img = _img(110, 30); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 2, 109, 27), 6, fill=(40, 42, 52)); d.rectangle((2, 6, 107, 23), fill=(70, 160, 110))
    speed = 60 * (1 - block) + 2
    rnd = random.Random(11)
    for k in range(26):
        x = (rnd.random() * 110 + t * speed * (0.8 + 0.4 * rnd.random())) % 110; y = 8 + rnd.random() * 13
        if block > 0.2 and 46 < x < 64: continue
        d.rectangle((x, y, x + 2, y + 1), fill=(170, 240, 200))
    if block > 0:
        r = 9 * block
        d.ellipse((55 - 1.4 * r, 15 - r, 55 + 1.4 * r, 15 + r), fill=(108, 76, 40)); d.rectangle((55 - 1.4 * r, 6, 55 + 1.4 * r, 6 + 3 * block), fill=(108, 76, 40))
    return outline(img)


# ------------------------------------------------------------------ hill parking
def car_top(steer=0.0, col=(196, 40, 50)):
    img = _img(40, 64); d = ImageDraw.Draw(img); cx = 20
    for (x, y, front) in ((7, 15, 1), (33, 15, 1), (7, 49, 0), (33, 49, 0)):
        a = math.radians(steer if front else 0); hw, hh = 3, 7
        pts = [(x + px * math.cos(a) - py * math.sin(a), y + px * math.sin(a) + py * math.cos(a)) for px, py in
               ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
        d.polygon(pts, fill=(28, 28, 34))
    d.rounded_rectangle((8, 4, 32, 60), 8, fill=col)
    dk = tuple(int(v * 0.7) for v in col)
    d.polygon([(11, 19), (29, 19), (27, 26), (13, 26)], fill=(150, 200, 230))  # windscreen (front = top)
    d.rectangle((12, 27, 28, 44), fill=dk); d.polygon([(13, 45), (27, 45), (28, 50), (12, 50)], fill=(120, 170, 200))
    d.rectangle((10, 4, 13, 6), fill=(255, 250, 210)); d.rectangle((27, 4, 30, 6), fill=(255, 250, 210))
    return outline(img)


# ------------------------------------------------------------------ stop-start, EV, warm-up, ABS
def traffic_light(state='red'):
    img = _img(20, 48); d = ImageDraw.Draw(img)
    d.rounded_rectangle((1, 1, 18, 46), 4, fill=(36, 38, 46))
    for i, (name, on) in enumerate((('red', (240, 50, 50)), ('amber', (255, 170, 40)), ('green', (60, 210, 100)))):
        y = 9 + 14 * i; lit = name == state
        d.ellipse((4, y - 5, 15, y + 6), fill=on if lit else tuple(v // 4 for v in on))
        if lit: d.point((7, y - 2), fill=(255, 255, 255))
    return outline(img)


def ss_icon(on=True):
    img = _img(22, 22); d = ImageDraw.Draw(img); col = (90, 220, 120) if on else (90, 94, 106)
    d.rounded_rectangle((0, 0, 21, 21), 4, fill=(20, 21, 26))
    d.arc((3, 3, 18, 18), 300, 240, fill=col, width=2); d.polygon([(4, 6), (8, 4), (8, 8)], fill=col)
    for x, y in ((9, 14), (10, 12), (11, 9), (12, 12), (13, 14)): d.point((x, y), fill=col)
    d.line((10, 12, 12, 12), fill=col)
    return img


def gear_pair(deg=0.0):
    from assets.garagebits import gear
    img = _img(120, 80)
    big = gear(-deg / 3, 30, 30, (190, 150, 60)); small = gear(deg, 10, 10, STEEL[2])
    img.alpha_composite(big, (48, 4)); img.alpha_composite(small, (17, 26))
    return img


def thermo(k=0.0):
    img = _img(14, 48); d = ImageDraw.Draw(img)
    d.rounded_rectangle((4, 1, 10, 38), 3, fill=(236, 240, 248)); d.ellipse((1, 34, 13, 46), fill=(236, 240, 248))
    col = (int(60 + 180 * k), 120 - int(60 * k), int(230 - 180 * k))
    d.ellipse((3, 36, 11, 44), fill=col); d.rectangle((6, 36 - int(32 * k), 8, 38), fill=col)
    for y in range(6, 34, 6): d.line((10, y, 11, y), fill=STEEL[0])
    return outline(img)


def pedal(press=0.0):
    img = _img(50, 60); d = ImageDraw.Draw(img); px, py = 40, 4
    a = math.radians(105 - 22 * press); L = 42
    ex, ey = px + L * math.cos(a), py + L * math.sin(a)
    d.line((px, py, ex, ey), fill=STEEL[1], width=4); d.ellipse((px - 3, py - 3, px + 3, py + 3), fill=STEEL[0])
    n = (math.cos(a + math.pi / 2), math.sin(a + math.pi / 2))
    pad = [(ex + 8 * math.cos(a + math.pi / 2), ey + 8 * math.sin(a + math.pi / 2)), (ex - 8 * math.cos(a + math.pi / 2), ey - 8 * math.sin(a + math.pi / 2))]
    d.line(pad, fill=(40, 42, 52), width=5)
    sx, sy = ex - 7, ey - 4                                            # shoe pressing the pad
    d.polygon([(sx - 26, sy - 6), (sx + 2, sy - 9), (sx + 4, sy + 7), (sx - 24, sy + 8)], fill=(60, 64, 90))
    d.line((sx - 26, sy + 8, sx + 4, sy + 7), fill=(30, 30, 40), width=2)
    return outline(img)


def torque_graph(cv, x, y, w, h, k=1.0, s=6):
    """Pixel chart drawn straight onto a full-res canvas at (x, y) size (w, h): EV line flat from 0 rpm, engine curve rising."""
    d = ImageDraw.Draw(cv)
    d.rounded_rectangle((x - 30, y - 30, x + w + 30, y + h + 70), 24, fill=(236, 240, 248), outline=NAVY, width=8)
    d.line((x, y, x, y + h, x + w, y + h), fill=NAVY, width=s)
    f = _font(40); d.text((x + 24, y - 24), 'PULL', font=f, fill=NAVY); d.text((x + w, y + h + 10), 'RPM', font=f, fill=NAVY, anchor='ra')
    n = int(60 * k)
    ev = [(x + w * i / 60, y + h * (0.12 if i < 32 else 0.12 + 0.5 * ((i - 32) / 28) ** 1.4)) for i in range(n + 1)]
    ice = [(x + w * i / 60, y + h * (0.95 - 0.75 * math.sin(math.pi * 0.5 * min(1, i / 44)) ** 1.6 + (0.1 * ((i - 44) / 16) if i > 44 else 0)))
           for i in range(n + 1)]
    for pts, col in ((ice, (150, 156, 168)), (ev, (60, 200, 110))):
        if len(pts) > 1:
            d.line([(round(px / s) * s, round(py / s) * s) for px, py in pts], fill=NAVY, width=24, joint='curve')
            d.line([(round(px / s) * s, round(py / s) * s) for px, py in pts], fill=col, width=12, joint='curve')
