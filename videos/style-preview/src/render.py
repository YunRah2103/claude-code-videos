"""Post + procedural renderer for the 6-style preview.

python render.py frames STYLE [--from A --to B]   -> out/style-preview/frames/sSTYLE/%04d.png
python render.py encode STYLE                      -> out/style-preview/style-STYLE.mp4
python render.py preview [--music PATH]            -> out/style-preview/preview.mp4
Styles 1, 2, 4 composite Blender frames from out/style-preview/blender/sN (scene.py).
Styles 3, 5, 6 are drawn here with numpy + PIL (5 uses car_mesh.json from scene.py)."""
import sys, os, json, math, subprocess, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import beat
from beat import FPS, N, speed, drag, DRAG_AT

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
OUT = os.path.join(ROOT, 'out/style-preview')
BL = os.path.join(OUT, 'blender')
W, H = 1080, 1920
SAFE_X0, SAFE_X1, SAFE_Y0, SAFE_Y1 = 54, 918, 230, 1190    # left 85 %, 12-62 % height
NAMES = {1: 'LIGHT TUNNEL', 2: 'TILT-SHIFT MINI', 3: 'SATISFYING LOOP',
         4: 'CUTAWAY', 5: 'HOLO WIREFRAME', 6: 'KINETIC TYPE'}
FI = '/usr/share/fonts/opentype/inter/'
FM = '/usr/share/fonts/truetype/dejavu/'
_fc = {}
def font(name, size):
    k = (name, size)
    if k not in _fc:
        path = FM + name if name.startswith('DejaVu') else FI + name
        _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]

def ease_out_back(u, s=1.7):
    u = min(max(u, 0), 1) - 1
    return u * u * ((s + 1) * u + s) + 1

def smoothstep(a, b, x):
    u = min(max((x - a) / (b - a), 0.0), 1.0)
    return u * u * (3 - 2 * u)

# ------------------------------------------------------------------ image utils
def box1d(a, r, axis):
    if r < 1:
        return a
    pad = [(0, 0)] * a.ndim; pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode='edge'), axis=axis, dtype=np.float32)
    n = a.shape[axis]
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return (hi - lo) / (2 * r + 1)

def gblur(a, sigma):
    """Approximate gaussian (3 box passes); big sigmas run on a downscaled copy."""
    if sigma <= 0.5:
        return a
    h, w = a.shape[:2]
    f = int(sigma // 4) if sigma > 8 else 1
    if f > 1:
        ph, pw = -(-h // f) * f, -(-w // f) * f
        a = np.pad(a, [(0, ph - h), (0, pw - w)] + [(0, 0)] * (a.ndim - 2), mode='edge')
        a = a.reshape(ph // f, f, pw // f, f, *a.shape[2:]).mean(axis=(1, 3))
        sigma = sigma / f
    r = max(1, int(round(math.sqrt(4 * sigma * sigma / 3 + 1) / 2)))
    for _ in range(3):
        a = box1d(box1d(a, r, 0), r, 1)
    if f > 1:
        a = np.repeat(np.repeat(a, f, 0), f, 1)[:h, :w]
        a = box1d(box1d(a, f // 2, 0), f // 2, 1)
    return a.astype(np.float32)

def bloom(img, thresh=0.6, strength=0.8, sigmas=(4, 14, 40)):
    hi = np.clip(img - thresh, 0, None)
    acc = sum(gblur(hi, s) for s in sigmas) / len(sigmas)
    return img + acc * strength

def vignette(img, k=0.35):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = ((xx - W / 2) / (W / 2)) ** 2 * 0.8 + ((yy - H / 2) / (H / 2)) ** 2
    return img * (1 - k * np.clip(d, 0, 1.6)[..., None] / 1.6)

def grain(img, i, amt=0.025):
    rng = np.random.default_rng(1000 + i)
    return img + rng.normal(0, amt, (H, W, 1)).astype(np.float32)

def to8(img):
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)

def load_rgb(path):
    im = Image.open(path).convert('RGB')
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255.0

def load_gray(path):
    im = Image.open(path)
    a = np.asarray(im).astype(np.float32)
    a = a / (65535.0 if a.max() > 255 else 255.0)
    if a.shape != (H, W):
        a = np.asarray(Image.fromarray(a).resize((W, H), Image.BILINEAR), np.float32)
    return a

def anchors(style):
    return json.load(open(os.path.join(BL, 's%d' % style, 'anchors.json')))

# ------------------------------------------------------------------ shared overlay
def text_w(d, s, f):
    b = d.textbbox((0, 0), s, font=f)
    return b[2] - b[0]

def fit(d, s, fname, size, maxw):
    while text_w(d, s, font(fname, size)) > maxw and size > 10:
        size -= 2
    return font(fname, size)

def draw_tags(d, style, th):
    """Tiny 'Yub' tag + 'STYLE n/6' in the safe area (top-left)."""
    f = font('Inter-Bold.otf', 26)
    x, y = SAFE_X0, SAFE_Y0 + 6
    yw = text_w(d, 'Yub', f)
    d.rounded_rectangle((x, y, x + yw + 20, y + 38), 10, fill=th['yub_bg'])
    d.text((x + 10, y + 4), 'Yub', font=f, fill=th['yub_fg'])
    f2 = font(th.get('tag_font', 'Inter-SemiBold.otf'), 26)
    d.text((x + yw + 36, y + 4), 'STYLE %d/6 · %s' % (style, NAMES[style]), font=f2, fill=th['tag'])

def draw_hook(d, th, y=None, shadow=True):
    s = 'DOUBLE THE SPEED?'
    f = fit(d, s, th['hook_font'], 96, SAFE_X1 - SAFE_X0)
    y = SAFE_Y0 + 62 if y is None else y
    if th.get('hook_stroke'):
        d.text((SAFE_X0, y), s, font=f, fill=th['hook'], stroke_width=th['hook_stroke'],
               stroke_fill=th['hook_stroke_col'])
    else:
        if shadow:
            d.text((SAFE_X0 + 3, y + 4), s, font=f, fill=(0, 0, 0, 120))
        d.text((SAFE_X0, y), s, font=f, fill=th['hook'])
    return y + f.size + 10

def draw_counter(d, t, th, y, sp=None):
    v = int(round((sp or speed)(t)))
    f = font(th['num_font'], th.get('num_size', 150))
    s = '%d' % v
    st = th.get('num_stroke', 0)
    d.text((SAFE_X0, y), s, font=f, fill=th['num'], stroke_width=st, stroke_fill=th.get('num_stroke_col'))
    # unit sits after the widest possible value so it never jumps
    x = SAFE_X0 + text_w(d, '200', f) + 22
    fu = font(th.get('unit_font', th['num_font']), th.get('unit_size', 48))
    asc = f.getmetrics()[0]
    d.text((x, y + asc - fu.getmetrics()[0]), 'km/h', font=fu, fill=th['unit'],
           stroke_width=min(st, 4), stroke_fill=th.get('num_stroke_col'))
    return y + int(f.size * 1.08)

def overlay(img8, style, th, t, extra=None):
    """img8: uint8 HxWx3. Draws tags, hook, counter and the DRAG x4 readout."""
    im = Image.fromarray(img8).convert('RGBA')
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    draw_tags(d, style, th)
    y = draw_hook(d, th, shadow=th.get('hook_shadow', True))
    if th.get('counter', True):
        y = draw_counter(d, t, th, y + th.get('gap', 20))
        th['_drag_y'] = y + 10
    if extra:
        extra(d, lay, t)
    return np.asarray(Image.alpha_composite(im, lay).convert('RGB'))

# ------------------------------------------------------------------ style 1: light tunnel
CYAN = np.array([0.30, 0.90, 1.00], np.float32)

def streamlines(mask, a, t, i):
    yg = 0.5 * (a['ground_front'][1] + a['ground_rear'][1])
    rear_x, front_x = a['rear'][0], a['front'][0]
    has = mask > 0.5
    anyc = has.any(0)
    top = np.where(anyc, has.argmax(0), yg).astype(np.float32)
    h = np.clip(yg - top, 0, None)
    dr = drag(t)
    k = (dr - 1) / 3.0
    dl = math.exp(-1 / 70.0); wl = 140 + 420 * k
    dw = math.exp(-1 / wl)
    hl = h.copy(); hr = h.copy()
    for x in range(W - 2, -1, -1):
        hl[x] = max(hl[x], hl[x + 1] * dl)
    for x in range(1, W):
        hr[x] = max(hr[x], hr[x - 1] * dw)
    he = box1d(box1d(np.maximum(hl, hr), 18, 0), 18, 0)
    rng = np.random.default_rng(7)
    K = 1100
    u = np.sort(rng.random(K))
    span = 760.0
    y0 = yg - 3 - span * u ** 2.0
    f = np.clip((y0 - (yg - span)) / span, 0, 1)
    bright = 0.35 + 0.65 * rng.random(K)
    ph = rng.random((K, 3)) * 6.283
    xs = np.arange(W, dtype=np.float32)
    disp = he[None, :] * (f[:, None] ** 0.8)
    y = y0[:, None] - disp
    # wake: turbulence behind the rear that grows with drag (v^2)
    wx = np.clip((xs - rear_x + 40) / 160.0, 0, None)
    env = (1 - np.exp(-wx)) * (1 + 0.004 * np.clip(xs - rear_x, 0, None))
    amp = (5 + 95 * k ** 1.4) * env[None, :] * (f[:, None] ** 1.8)
    sp = 260 + 900 * k
    tt = t
    turb = (np.sin(xs[None, :] * 0.021 - tt * sp * 0.021 + ph[:, :1]) * 0.55 +
            np.sin(xs[None, :] * 0.047 - tt * sp * 0.05 + ph[:, 1:2] * 1.7) * 0.3 +
            np.sin(xs[None, :] * 0.11 - tt * sp * 0.12 + ph[:, 2:3]) * 0.15 * (0.4 + k))
    y = y + amp * turb
    # travelling pulses (faster with speed)
    vpx = 700 * speed(t) / 100.0
    lam = 140 + 120 * rng.random(K)
    pulse = np.maximum(0, np.sin(6.283 * (xs[None, :] - vpx * t) / lam[:, None] + ph[:, :1])) ** 5
    topfade = np.clip(f / 0.45, 0, 1) ** 2
    hero = np.where(rng.random(K) < 0.08, 2.2, 1.0)        # a few brighter lines give structure
    inten = (bright * hero * topfade)[:, None] * (0.05 + 0.75 * pulse) * (0.25 + 0.75 * f[:, None] ** 1.5)
    inten *= np.clip(xs[None, :] / 90.0, 0, 1)                      # fade in from the left edge
    inten *= 1 + 0.6 * k * np.clip((xs - rear_x) / 160.0, 0, 1)[None, :]  # hot wake, no hard edge
    yi = np.floor(y).astype(np.int64); fy = (y - yi).astype(np.float32)
    xi = np.broadcast_to(np.arange(W), y.shape)
    acc = np.zeros(H * W, np.float32)
    for dy, wgt in ((0, 1 - fy), (1, fy)):
        yy = yi + dy
        ok = (yy >= 0) & (yy < H)
        acc += np.bincount((yy[ok] * W + xi[ok]), weights=(inten * wgt)[ok], minlength=H * W)
    acc = acc.reshape(H, W) * (1 - 0.9 * mask)
    # faint reflection in the black floor
    yr = int(yg)
    if 0 < yr < H:
        n = min(yr, H - yr)
        fall = np.exp(-np.arange(n, dtype=np.float32) / 40.0)[:, None]
        acc[yr:yr + n] += acc[yr - n:yr][::-1] * 0.10 * fall
    return acc

def style1(i):
    t = i / FPS
    a = anchors(1)[str(i)]
    base = load_rgb(os.path.join(BL, 's1', '%04d.png' % i))
    mask = load_gray(os.path.join(BL, 's1', 'mask_%04d.png' % (i + 1)))
    acc = streamlines(mask, a, t, i)
    light = acc * 0.9 + gblur(acc, 2) * 0.35 + gblur(acc, 14) * 0.45
    L = 1 - np.exp(-light)
    img = base + L[..., None] * CYAN[None, None] + (np.clip(L - 0.75, 0, None) * 1.2)[..., None]
    img = bloom(img, 0.7, 0.5, (6, 24))
    img = vignette(img, 0.25); img = grain(img, i, 0.018)
    th = dict(yub_bg=(77, 230, 255, 255), yub_fg=(0, 0, 0, 255), tag=(140, 200, 215, 255),
              tag_font='DejaVuSansMono.ttf', hook_font='Inter-SemiBold.otf', hook=(240, 250, 255, 255),
              num_font='DejaVuSansMono-Bold.ttf', num=(255, 255, 255, 255), unit=(77, 230, 255, 255),
              unit_font='DejaVuSansMono.ttf', num_size=140, unit_size=42)
    def extra(d, lay, t):
        y = th['_drag_y']
        f = font('DejaVuSansMono.ttf', 30)
        dr = drag(t)
        d.text((SAFE_X0, y), 'drag  x%.2f' % dr, font=f, fill=(140, 200, 215, 255))
        bw = 420
        d.rectangle((SAFE_X0, y + 46, SAFE_X0 + bw, y + 50), fill=(40, 70, 80, 255))
        d.rectangle((SAFE_X0, y + 46, SAFE_X0 + int(bw * dr / 4), y + 50), fill=(77, 230, 255, 255))
        if t >= DRAG_AT:
            n = min(7, int((t - DRAG_AT) * 40))           # typewriter
            s = 'DRAG x4'[:n]
            fb = font('DejaVuSansMono-Bold.ttf', 92)
            yy = y + 74
            d.rectangle((SAFE_X0 - 2, yy, SAFE_X0 + 6, yy + 104), fill=(77, 230, 255, 255))
            d.text((SAFE_X0 + 26, yy + 2), s, font=fb, fill=(77, 230, 255, 255))
    return overlay(to8(img), 1, th, t, extra)

# ------------------------------------------------------------------ style 2: tilt-shift miniature
STOP = sorted({int(k * 2.5) for k in range(48)})

def style2(i):
    src = max(s for s in STOP if s <= i)
    ts = src / FPS                                    # stop-motion time
    a = anchors(2)[str(src)]
    base = load_rgb(os.path.join(BL, 's2', '%04d.png' % src))
    dep = load_gray(os.path.join(BL, 's2', 'depth_%04d.png' % (src + 1)))
    cx, cy = [int(v) for v in a['center']]
    df = float(np.median(dep[max(cy - 20, 0):cy + 20, max(cx - 20, 0):cx + 20]))
    # masked blur: depth distance from the focus plane + a classic horizontal band
    yy = (np.arange(H, dtype=np.float32)[:, None] - cy) / H
    amt = np.clip(np.abs(dep - df) / 0.07, 0, 1) * 0.6 + np.clip(np.abs(yy) * 3.2 - 0.35, 0, 1) * 0.7
    amt = np.clip(amt, 0, 1)
    levels = [base] + [gblur(base, s) for s in (4, 10, 22)]
    pos = amt * 3; lo = np.floor(pos).astype(int); fr = (pos - lo)[..., None]
    stack = np.stack(levels)
    hi = np.minimum(lo + 1, 3)
    img = np.take_along_axis(stack, lo[None, ..., None].repeat(3, -1), 0)[0] * (1 - fr) + \
          np.take_along_axis(stack, hi[None, ..., None].repeat(3, -1), 0)[0] * fr
    # toy look: saturation + contrast
    g = img.mean(-1, keepdims=True)
    img = g + (img - g) * 1.45
    img = (img - 0.5) * 1.12 + 0.52
    # stop-motion jitter per held frame
    rng = np.random.default_rng(src)
    dx, dy = rng.integers(-3, 4, 2)
    img = np.roll(img, (int(dy), int(dx)), (0, 1))
    img *= 1 + rng.normal(0, 0.012)
    img = vignette(img, 0.3)
    im = Image.fromarray(to8(img)).convert('RGBA')
    ribbons(im, a, ts, rng)
    th = dict(yub_bg=(255, 214, 10, 255), yub_fg=(30, 30, 30, 255), tag=(255, 255, 255, 255),
              hook_font='Inter-Black.otf', hook=(255, 255, 255, 255), hook_stroke=7, hook_stroke_col=(30, 30, 40, 255),
              num_font='Inter-Black.otf', num=(255, 214, 10, 255), unit=(255, 255, 255, 255),
              num_stroke=7, num_stroke_col=(30, 30, 40, 255), num_size=150, unit_size=52)
    def extra(d, lay, t):
        if t >= DRAG_AT:
            u = (t - DRAG_AT) * 12 // 1 / 3.0              # pops in 12 fps steps
            sc = ease_out_back(u)
            f = font('Inter-Black.otf', max(10, int(100 * sc)))
            x, y = SAFE_X0, th['_drag_y'] + 10
            s = 'DRAG x4'
            tw = text_w(d, s, f)
            d.rounded_rectangle((x - 6, y, x + tw + 40, y + int(130 * sc)), 26, fill=(255, 60, 90, 255),
                                outline=(30, 30, 40, 255), width=7)
            d.text((x + 16, y + int(8 * sc)), s, font=f, fill=(255, 255, 255, 255))
    return overlay(np.asarray(im.convert('RGB')), 2, th, ts, extra)

def ribbons(im, a, t, rng):
    """Small wind ribbons streaming back off the car; strength 1 -> 3."""
    fx, fy = a['front']; rx, ry = a['rear']; tx, ty = a['roof']
    d = np.array([rx - fx, ry - fy], np.float32); L = np.linalg.norm(d); d /= L
    n = np.array([d[1], -d[0]], np.float32)
    if n[1] > 0:
        n = -n
    s = 1 + 2 * (drag(t) - 1) / 3.0
    lay = Image.new('RGBA', (W * 2, H * 2), (0, 0, 0, 0)); dr = ImageDraw.Draw(lay)
    cols = [(255, 255, 255), (255, 230, 90), (120, 220, 255), (255, 140, 190), (170, 255, 150)]
    cnt = int(round(3 * s))
    r2 = np.random.default_rng(11)
    for k in range(cnt):
        off = 30 + 220 * (k + 0.5) / cnt + r2.uniform(-20, 20)
        start = r2.uniform(0.05, 0.45)
        p0 = np.array([fx, fy]) + d * L * start + n * (off - 40)
        length = (170 + 90 * s) * r2.uniform(0.8, 1.2)
        ampl = 7 * s * r2.uniform(0.7, 1.3)
        phase = r2.random()
        pts = []
        for j in range(26):
            u = j / 25.0
            w = math.sin(6.283 * (u * 1.2 - t * (1.2 + 0.8 * s) + phase)) * ampl * u
            p = p0 + d * (L * 0.2 + length * u) + n * w
            pts.append((float(p[0] * 2), float(p[1] * 2)))
        c = cols[k % len(cols)]
        dr.line(pts, fill=(30, 30, 40, 200), width=16, joint='curve')
        dr.line(pts, fill=c + (255,), width=9, joint='curve')
    lay = lay.resize((W, H), Image.LANCZOS)
    im.alpha_composite(lay)

# ------------------------------------------------------------------ style 3: satisfying loop
LOOP_C = None
def loop_angle(i):
    global LOOP_C
    if LOOP_C is None:
        tot = sum(beat.loop_speed(k / FPS) / 100 for k in range(N))
        sym = 2 * math.pi / 5
        LOOP_C = round(0.17 * tot / sym) * sym / tot     # whole spoke periods per loop
    return LOOP_C * sum(beat.loop_speed(k / FPS) / 100 for k in range(i))

def loop_dist(i):
    tot = sum(beat.loop_speed(k / FPS) / 100 for k in range(N))
    c = round(14.0 * tot / 160) * 160 / tot          # whole dash periods (160 px) per loop
    return c * sum(beat.loop_speed(k / FPS) / 100 for k in range(i))

_wheel = {}
def wheel_sprites():
    if _wheel:
        return _wheel
    S = 2; R = 360
    def layer():
        return Image.new('RGBA', (R * 2 * S, R * 2 * S), (0, 0, 0, 0))
    c = R * S
    # disc (rotates)
    disc = layer(); d = ImageDraw.Draw(disc)
    d.ellipse((c - 232 * S, c - 232 * S, c + 232 * S, c + 232 * S), fill=(196, 200, 207, 255))
    d.ellipse((c - 150 * S, c - 150 * S, c + 150 * S, c + 150 * S), fill=(170, 175, 183, 255))
    for ring, nh in ((190, 20), (165, 20)):   # 20 holes: 5-fold symmetric like the spokes
        for k in range(nh):
            a = k * 2 * math.pi / nh + (0.17 if ring == 165 else 0)
            x, y = c + math.cos(a) * ring * S, c + math.sin(a) * ring * S
            d.ellipse((x - 7 * S, y - 7 * S, x + 7 * S, y + 7 * S), fill=(120, 124, 132, 255))
    # rim + spokes (rotates)
    rim = layer(); d = ImageDraw.Draw(rim)
    d.ellipse((c - 282 * S, c - 282 * S, c + 282 * S, c + 282 * S), fill=(232, 234, 238, 255))
    d.ellipse((c - 252 * S, c - 252 * S, c + 252 * S, c + 252 * S), fill=(0, 0, 0, 0))
    for k in range(5):
        a = k * 2 * math.pi / 5 - math.pi / 2
        pa, pb = a + 0.5 * math.pi, a
        def P(r, da):
            return (c + math.cos(a + da) * r * S, c + math.sin(a + da) * r * S)
        d.polygon([P(70, -0.35), P(258, -0.13), P(258, 0.13), P(70, 0.35)], fill=(238, 240, 244, 255))
        d.polygon([P(70, 0.0), P(258, 0.0), P(258, 0.13), P(70, 0.35)], fill=(200, 204, 212, 255))
    d.ellipse((c - 84 * S, c - 84 * S, c + 84 * S, c + 84 * S), fill=(214, 217, 223, 255))
    d.ellipse((c - 40 * S, c - 40 * S, c + 40 * S, c + 40 * S), fill=(60, 64, 72, 255))
    for k in range(5):
        a = k * 2 * math.pi / 5
        x, y = c + math.cos(a) * 60 * S, c + math.sin(a) * 60 * S
        d.ellipse((x - 9 * S, y - 9 * S, x + 9 * S, y + 9 * S), fill=(90, 94, 102, 255))
    # tyre (static look, rotation invisible) + caliper (static)
    tyre = layer(); d = ImageDraw.Draw(tyre)
    d.ellipse((c - 345 * S, c - 345 * S, c + 345 * S, c + 345 * S), fill=(38, 40, 46, 255))
    d.ellipse((c - 330 * S, c - 330 * S, c + 330 * S, c + 330 * S), outline=(58, 60, 68, 255), width=4 * S)
    d.ellipse((c - 284 * S, c - 284 * S, c + 284 * S, c + 284 * S), fill=(0, 0, 0, 0))
    cal = layer(); d = ImageDraw.Draw(cal)
    d.arc((c - 222 * S, c - 222 * S, c + 222 * S, c + 222 * S), -70, -15, fill=(255, 112, 67, 255), width=62 * S)
    d.arc((c - 222 * S, c - 222 * S, c + 222 * S, c + 222 * S), -66, -19, fill=(255, 140, 100, 255), width=14 * S)
    for k, im in (('disc', disc), ('rim', rim), ('tyre', tyre), ('cal', cal)):
        _wheel[k] = im.resize((R * 2, R * 2), Image.LANCZOS)
    return _wheel

def blur_rot(sprite, ang, span, n):
    acc = None
    for k in range(n):
        a = ang - span * k / max(n - 1, 1)
        r = np.asarray(sprite.rotate(-math.degrees(a), Image.BICUBIC), np.float32)
        acc = r if acc is None else acc + r
    return Image.fromarray((acc / n).astype(np.uint8), 'RGBA')

_bg3 = None
def style3(i):
    global _bg3
    t = (i % N) / FPS
    v = beat.loop_speed(t)
    if _bg3 is None:
        g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        top = np.array([0.93, 0.95, 0.97], np.float32); bot = np.array([0.80, 0.86, 0.92], np.float32)
        _bg3 = np.broadcast_to(top * (1 - g) + bot * g, (H, W, 3)).copy()
    im = Image.fromarray(to8(_bg3)).convert('RGBA')
    sp = wheel_sprites()
    CX, CY, R = 470, 1100, 360
    sym = 2 * math.pi / 5                                    # wheel is 5-fold symmetric
    ang = round(loop_angle(i) % sym, 9) % round(sym, 9)
    om = LOOP_C * v / 100                                     # rad per frame
    d = ImageDraw.Draw(im)
    # ground line + dashes moving left (wheel rolls right)
    gy = CY + 345
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
    ds.ellipse((CX - 330, gy - 26, CX + 330, gy + 26), fill=(40, 60, 90, 60))
    im.alpha_composite(Image.fromarray(gblur(np.asarray(sh, np.float32), 10).astype(np.uint8), 'RGBA'))
    d = ImageDraw.Draw(im)
    d.line((0, gy, W, gy), fill=(150, 165, 185, 255), width=4)
    off = loop_dist(i) % 160
    for k in range(-1, 9):
        x = k * 160 - off
        d.line((x, gy + 30, x + 70, gy + 30), fill=(170, 182, 200, 255), width=6)
    # speed streak arcs (behind the wheel)
    st = Image.new('RGBA', (W * 2, H * 2), (0, 0, 0, 0)); dd = ImageDraw.Draw(st)
    arc_len = 18 + 50 * (v - 100) / 100
    for k, rr in enumerate((372, 392, 412, 432)):
        for j in range(5):                      # 5 per ring so a 72-degree turn maps onto itself
            a0 = math.degrees(ang) + j * 72 + k * 37
            for s in range(8):
                al = int(200 * (1 - s / 8) * (0.5 + 0.5 * (v - 100) / 100))
                seg_a = a0 - arc_len * s / 8
                dd.arc(((CX - rr) * 2, (CY - rr) * 2, (CX + rr) * 2, (CY + rr) * 2),
                       seg_a - arc_len / 8, seg_a, fill=(255, 255, 255, al), width=10)
    im.alpha_composite(st.resize((W, H), Image.LANCZOS))
    span = om * 0.9                                           # 0.9 frame shutter
    nb = min(32, int(span * 260 / 2.5) + 2)                   # ~2.5 px between copies at the rim
    im.alpha_composite(blur_rot(sp['disc'], ang, span, nb), (CX - R, CY - R))
    im.alpha_composite(sp['cal'], (CX - R, CY - R))
    im.alpha_composite(blur_rot(sp['rim'], ang, span, nb), (CX - R, CY - R))
    im.alpha_composite(sp['tyre'], (CX - R, CY - R))
    img = np.asarray(im.convert('RGB'), np.float32) / 255
    th = dict(yub_bg=(30, 40, 60, 255), yub_fg=(255, 255, 255, 255), tag=(90, 105, 125, 255),
              hook_font='Inter-Bold.otf', hook=(30, 40, 60, 255), hook_shadow=False,
              num_font='Inter-SemiBold.otf', num=(30, 40, 60, 255), unit=(110, 125, 145, 255),
              unit_font='Inter-Medium.otf', num_size=140, unit_size=46)
    def extra(d, lay, tt):
        y = th['_drag_y'] + 6
        dr = (v / 100) ** 2
        bw = 700
        d.rounded_rectangle((SAFE_X0, y, SAFE_X0 + bw, y + 44), 22, fill=(255, 255, 255, 200))
        fw = int(bw * dr / 4)
        d.rounded_rectangle((SAFE_X0, y, SAFE_X0 + max(fw, 44), y + 44), 22, fill=(255, 112, 67, 255))
        fl = font('Inter-SemiBold.otf', 26)
        for m in (1, 2, 3, 4):
            x = SAFE_X0 + int(bw * m / 4)
            d.text((x - 34, y + 54), 'x%d' % m, font=fl, fill=(110, 125, 145, 255))
        al = int(255 * smoothstep(3.6, 3.95, dr))
        f = font('Inter-Bold.otf', 64)
        d.text((SAFE_X0, y + 96), 'DRAG x4', font=f, fill=(255, 112, 67, al))
    return overlay_loop(to8(img), th, t, extra)

def overlay_loop(img8, th, t, extra):
    im = Image.fromarray(img8).convert('RGBA')
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    draw_tags(d, 3, th)
    y = draw_hook(d, th, shadow=False)
    y = draw_counter(d, t, th, y + 20, sp=beat.loop_speed)
    th['_drag_y'] = y + 10
    extra(d, lay, t)
    return np.asarray(Image.alpha_composite(im, lay).convert('RGB'))

# ------------------------------------------------------------------ style 4: cutaway
def style4(i):
    t = i / FPS
    a = anchors(4)[str(i)]
    base = load_rgb(os.path.join(BL, 's4', '%04d.png' % i))
    img = vignette(base, 0.18)
    im = Image.fromarray(to8(img)).convert('RGBA')
    lay = Image.new('RGBA', (W * 2, H * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    fx, fy = a['front']; gy = a['ground_front'][1]; ry = a['roof'][1]
    hcar = gy - ry
    k = (drag(t) - 1) / 3
    # pressure glow on the nose
    g = Image.new('RGBA', (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    pr = 60 + 70 * k
    gd.ellipse((fx - pr, fy - pr * 1.2, fx + pr * 0.5, fy + pr * 0.9), fill=(255, 80, 30, int(40 + 90 * k)))
    im.alpha_composite(Image.fromarray(gblur(np.asarray(g, np.float32), 34).clip(0, 255).astype(np.uint8), 'RGBA'))
    # air arrows: rows aimed at the front; they bend over/under when they hit the nose
    vpx = 520 * speed(t) / 100
    rows = 7
    spacing = 230 / (0.6 + 0.4 * speed(t) / 100)
    blue = (40, 110, 255, 255)
    for r in range(rows):
        oy = (r - rows // 2) * hcar * 0.32
        side = -1 if oy < 0 else 1
        y0 = fy + oy
        stop = fx - 30 - abs(oy) * 0.15
        for m in range(-1, 8):
            hx = (m * spacing + vpx * t + r * 37) % (spacing * 7) - spacing * 1.5
            if hx > stop + 200:
                continue
            L = 70 + 40 * k
            pts = []
            for s in np.linspace(hx - L, hx, 8):
                over = max(0.0, s - (stop - 140))
                yy = y0 + side * min(over ** 1.5 * 0.035 * (1 + abs(oy) / hcar), 150)
                if r == rows // 2:
                    yy = y0 - min(over ** 1.5 * 0.03, 150)
                pts.append((s, yy))
            fade = 1.0 - smoothstep(stop - 60, stop + 140, hx)
            if fade <= 0.02:
                continue
            P = [(x * 2, y * 2) for x, y in pts]
            al = int(255 * fade)
            d.line(P, fill=(255, 255, 255, al), width=int(18 + 8 * k), joint='curve')
            d.line(P, fill=blue[:3] + (al,), width=int(10 + 6 * k), joint='curve')
            (x1, y1), (x0, y0_) = P[-1], P[-2]
            ang = math.atan2(y1 - y0_, x1 - x0); hs = 26 + 10 * k
            tri = [(x1 + math.cos(ang) * hs, y1 + math.sin(ang) * hs),
                   (x1 + math.cos(ang + 2.4) * hs, y1 + math.sin(ang + 2.4) * hs),
                   (x1 + math.cos(ang - 2.4) * hs, y1 + math.sin(ang - 2.4) * hs)]
            d.polygon(tri, fill=blue[:3] + (al,), outline=(255, 255, 255, al), width=4)
    # part labels with leader lines
    fl = font('Inter-Bold.otf', 52)
    for key, txt, dx, dy in (('battery', 'BATTERY', -40, 300), ('motor', 'MOTOR', -60, 330)):
        px, py = a[key]
        lx, ly = min(px + dx, 760), min(py + dy, 1500)
        d.line((px * 2, py * 2, lx * 2, (ly - 6) * 2), fill=(40, 44, 52, 255), width=4)
        d.ellipse((px * 2 - 10, py * 2 - 10, px * 2 + 10, py * 2 + 10), fill=(255, 90, 20, 255))
        d.text((lx * 2 - 10, ly * 2 - 6), txt, font=fl, fill=(40, 44, 52, 255))
    im.alpha_composite(lay.resize((W, H), Image.LANCZOS))
    img = grain(np.asarray(im.convert('RGB'), np.float32) / 255, i, 0.012)
    th = dict(yub_bg=(255, 90, 20, 255), yub_fg=(255, 255, 255, 255), tag=(70, 76, 88, 255),
              hook_font='Inter-ExtraBold.otf', hook=(28, 32, 40, 255), hook_shadow=False,
              num_font='Inter-Bold.otf', num=(28, 32, 40, 255), unit=(255, 90, 20, 255),
              unit_font='Inter-SemiBold.otf', num_size=140, unit_size=46)
    def extra(dd, lay2, tt):
        y = th['_drag_y']
        u = smoothstep(DRAG_AT, DRAG_AT + 0.25, tt)
        if u > 0:
            fb = font('Inter-ExtraBold.otf', 84)
            w = int((text_w(dd, 'DRAG x4', fb) + 56) * u)
            dd.rectangle((SAFE_X0, y, SAFE_X0 + w, y + 112), fill=(28, 32, 40, 255))
            dd.rectangle((SAFE_X0, y, SAFE_X0 + 10, y + 112), fill=(255, 90, 20, 255))
            if u > 0.6:
                dd.text((SAFE_X0 + 34, y + 6), 'DRAG x4', font=fb, fill=(255, 255, 255, 255))
        else:
            fs = font('Inter-SemiBold.otf', 30)
            dd.text((SAFE_X0, y + 10), 'AIR HITS THE NOSE → DRAG', font=fs, fill=(70, 76, 88, 255))
    return overlay(to8(img), 4, th, t, extra)

# ------------------------------------------------------------------ style 5: holographic wireframe
_mesh = None
def mesh():
    global _mesh
    if _mesh is None:
        m = json.load(open(os.path.join(BL, 'car_mesh.json')))
        segs, wsegs = [], []
        for o in m['body']:
            v = np.array(o['v'], np.float32); e = np.array(o['e'], np.int64)
            if len(e): segs.append(np.stack([v[e[:, 0]], v[e[:, 1]]], 1))
        for o in m['wheels']:
            v = np.array(o['v'], np.float32); e = np.array(o['e'], np.int64)
            hub = np.array(o['hub'], np.float32)
            if len(e): wsegs.append((np.stack([v[e[:, 0]], v[e[:, 1]]], 1), hub))
        _mesh = (np.concatenate(segs), wsegs)
    return _mesh

def cam5(t):
    az = math.radians(-32 + 5 * t)
    dist = 14.8 - 0.4 * t
    cam = np.array([dist * math.sin(az) - 0.3, -dist * math.cos(az), 3.0], np.float32)
    tgt = np.array([0.25, 0, 0.55], np.float32)
    f = tgt - cam; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1]); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return cam, r, u, f

def project(p, C, S=2):
    cam, r, u, f = C
    q = p - cam
    x, y, z = q @ r, q @ u, q @ f
    foc = (H / 2) / math.tan(math.radians(19)) * S
    return np.stack([W * S / 2 + foc * x / z, 1180 * S - foc * y / z], -1), z

def style5(i):
    t = i / FPS
    S = 2
    C = cam5(t)
    body, wheels = mesh()
    img = Image.new('RGB', (W * S, H * S), (0, 0, 0)); d = ImageDraw.Draw(img)
    # grid floor scrolling backwards with distance travelled
    dist = sum(speed(k / FPS) for k in range(i)) / 100 * 0.09
    off = dist % 1.0
    for gx in np.arange(-24, 24, 1.0):
        x = gx - off
        p = np.array([[x, yy, 0] for yy in np.linspace(-14, 14, 40)], np.float32)
        P, z = project(p, C)
        for a in range(len(P) - 1):
            if z[a] > 0.8 and z[a + 1] > 0.8:
                fade = max(0.0, 1 - z[a] / 26)
                c = int(150 * fade)
                d.line((tuple(P[a]), tuple(P[a + 1])), fill=(c // 2, c // 5, c), width=2)
    for gy in np.arange(-14, 15, 1.0):
        p = np.array([[xx, gy, 0] for xx in np.linspace(-24, 24, 60)], np.float32)
        P, z = project(p, C)
        for a in range(len(P) - 1):
            if z[a] > 0.8 and z[a + 1] > 0.8:
                fade = max(0.0, 1 - z[a] / 26)
                c = int(150 * fade)
                d.line((tuple(P[a]), tuple(P[a + 1])), fill=(c // 2, c // 5, c), width=2)
    # scanning plane sweeps nose -> tail, faster with speed
    ph = (sum(speed(k / FPS) for k in range(i)) / 100 / FPS) / 1.1
    xs = -2.7 + 5.4 * (ph % 1.0)
    quad = np.array([[xs, -1.2, 0], [xs, 1.2, 0], [xs, 1.2, 1.5], [xs, -1.2, 1.5]], np.float32)
    Q, _ = project(quad, C)
    pl = Image.new('RGBA', img.size, (0, 0, 0, 0)); ImageDraw.Draw(pl).polygon([tuple(q) for q in Q], fill=(255, 40, 200, 40))
    img.paste(pl, (0, 0), pl); d = ImageDraw.Draw(img)
    def draw(segs, col):
        P, z = project(segs.reshape(-1, 3), C)
        P = P.reshape(-1, 2, 2)
        mx = segs[:, :, 0].mean(1)
        hot = np.abs(mx - xs) < 0.12
        for k in range(len(P)):
            d.line((tuple(P[k, 0]), tuple(P[k, 1])), fill=(255, 220, 255) if hot[k] else col, width=2)
    draw(body, (40, 220, 255))
    ang = beat.wheel_angle(i)
    for segs, hub in wheels:
        q = segs - hub
        ca, sa = math.cos(ang), math.sin(ang)
        x = q[..., 0] * ca + q[..., 2] * sa
        z = -q[..., 0] * sa + q[..., 2] * ca
        rot = np.stack([x, q[..., 1], z], -1) + hub
        draw(rot, (255, 70, 220))
    arr = np.asarray(img.resize((W, H), Image.LANCZOS), np.float32) / 255
    arr = arr * 1.6
    arr = bloom(arr, 0.15, 1.6, (3, 10, 30, 70))
    # chromatic split + scanlines
    arr[..., 0] = np.roll(arr[..., 0], 2, 1); arr[..., 2] = np.roll(arr[..., 2], -2, 1)
    arr[::4] *= 0.86
    arr = vignette(arr, 0.35); arr = grain(arr, i, 0.02)
    th = dict(yub_bg=(255, 40, 200, 255), yub_fg=(0, 0, 0, 255), tag=(255, 120, 230, 255),
              tag_font='DejaVuSansMono.ttf', hook_font='Inter-Bold.otf', hook=(200, 250, 255, 255),
              num_font='DejaVuSansMono-Bold.ttf', num=(60, 230, 255, 255), unit=(255, 90, 220, 255),
              unit_font='DejaVuSansMono.ttf', num_size=140, unit_size=42)
    def extra(dd, lay, tt):
        y = th['_drag_y']
        fs = font('DejaVuSansMono.ttf', 28)
        dd.text((SAFE_X0, y), '> scan %03d%%   F_drag ~ v^2' % int(100 * (ph % 1.0)), font=fs, fill=(120, 230, 255, 255))
        if tt >= DRAG_AT:
            blink = int((tt - DRAG_AT) * 10) % 2 == 0 or tt > DRAG_AT + 0.5
            fb = font('DejaVuSansMono-Bold.ttf', 96)
            if blink:
                dd.rectangle((SAFE_X0, y + 52, SAFE_X0 + 520, y + 170), outline=(255, 60, 210, 255), width=4)
                dd.text((SAFE_X0 + 26, y + 58), 'DRAG x4', font=fb, fill=(255, 90, 220, 255))
    o = overlay(to8(arr), 5, th, t, extra)
    # glow the overlay text a little
    of = o.astype(np.float32) / 255
    return to8(bloom(of, 0.55, 0.45, (3, 10)))

# ------------------------------------------------------------------ style 6: kinetic type + light trails
_sprite = None
def car_sprite():
    global _sprite
    if _sprite is None:
        im = Image.open(os.path.join(BL, 'car_sprite.png')).convert('RGBA')
        bb = im.getbbox(); im = im.crop(bb)
        w = 420
        _sprite = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    return _sprite

def style6(i):
    t = i / FPS
    rng = np.random.default_rng(5)
    g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    img = np.broadcast_to(np.array([0.02, 0.02, 0.05], np.float32) * (1 - g) +
                          np.array([0.06, 0.02, 0.08], np.float32) * g, (H, W, 3)).copy()
    # light streaks flowing right -> left, long exponential tails
    acc = np.zeros((H, W, 3), np.float32)
    pal = np.array([[1.0, 0.45, 0.1], [1.0, 0.15, 0.55], [0.2, 0.8, 1.0], [1.0, 0.95, 0.85]], np.float32)
    dist = sum(speed(k / FPS) for k in range(i)) / 100
    xs = np.arange(W, dtype=np.float32)
    for k in range(70):
        y = int(rng.uniform(150, 1750)); th_ = int(rng.choice([1, 2, 2, 3, 5]))
        v = rng.uniform(25, 70) * (1.0 + 0.6 * (y > 1150))
        L = rng.uniform(250, 900) * (0.7 + 0.5 * speed(t) / 100)
        period = W + 1600
        hx = W + 200 - ((dist * v + rng.uniform(0, period)) % period)
        tail = np.where(xs >= hx, np.exp(-(xs - hx) / (L / 3)), 0) * (xs < hx + L)
        c = pal[k % 4] * rng.uniform(0.5, 1.2) * (0.45 if 230 < y < 1190 else 1.0)
        acc[max(y - th_, 0):y + th_ + 1] += tail[None, :, None] * c[None, None]
    img += acc
    # small car passing through (left -> right) with tail-light trail
    sp = car_sprite()
    cxp = -460 + 1800 * smoothstep(-0.15, 4.4, t)
    cyp = 1330
    trail = np.zeros((H, W), np.float32)
    tx = int(cxp + 10)
    xs2 = np.arange(W)
    tl = np.where(xs2 < tx, np.exp(-(tx - xs2) / 260.0), 0)
    trail[cyp + sp.height - 92:cyp + sp.height - 84] += tl[None, :] * 1.4
    img += trail[..., None] * np.array([1.0, 0.1, 0.15], np.float32)
    img = bloom(img, 0.25, 1.4, (4, 16, 50))
    im = Image.fromarray(to8(img)).convert('RGBA')
    sm = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for s in range(5, 0, -1):                      # motion smear behind the car
        ghost = sp.copy(); a = np.asarray(ghost).copy(); a[..., 3] = (a[..., 3] * (0.12 * (6 - s) / 5)).astype(np.uint8)
        sm.alpha_composite(Image.fromarray(a), (int(cxp - s * 26), cyp))
    sm.alpha_composite(sp, (int(cxp), cyp))
    im.alpha_composite(sm)
    # kinetic type
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    th = dict(yub_bg=(255, 120, 30, 255), yub_fg=(0, 0, 0, 255), tag=(255, 200, 160, 255),
              hook_font='Inter-Black.otf', hook=(255, 255, 255, 255))
    draw_tags(d, 6, th)
    y0 = draw_hook(d, th) + 34
    v = int(round(speed(t)))
    f = font('InterDisplay-Black.otf', 330)
    s = '%d' % v
    rate = (speed(t) - speed(max(t - 1 / FPS, 0))) * FPS   # km/h per second
    punch = 1 + 0.06 * max(0, 1 - ((t * FPS) % 6) / 3) * (t < beat.RAMP)
    shrink = 1 - 0.32 * smoothstep(DRAG_AT - 0.1, DRAG_AT + 0.2, t)
    sc = punch * shrink
    fs = font('InterDisplay-Black.otf', int(330 * sc))
    bb = d.textbbox((0, 0), s, font=fs)
    nx, ny = SAFE_X0 - bb[0], y0 - bb[1]
    for k in range(6, 0, -1):                     # speed smear trails behind the digits
        al = int(26 * (7 - k) / 6 * min(1, rate / 30 + 0.3))
        d.text((nx + k * (6 + rate / 10), ny), s, font=fs, fill=(255, 120, 30, al))
    d.text((nx, ny), s, font=fs, fill=(255, 255, 255, 255))
    fu = font('Inter-Black.otf', int(64 * sc))
    d.text((SAFE_X0 + 4, ny + bb[3] + 6), 'KM/H', font=fu, fill=(255, 120, 30, 255))
    if t >= DRAG_AT:
        u = (t - DRAG_AT) / 0.35
        k = ease_out_back(u, 2.2)
        big = font('InterDisplay-Black.otf', max(10, int(380 * (2.2 - 1.2 * k))))
        yx = 870
        fl = font('Inter-Black.otf', 84)
        d.text((SAFE_X0, yx - 20), 'DRAG', font=fl, fill=(255, 120, 30, int(255 * min(1, u * 2))))
        bbx = d.textbbox((0, 0), 'x4', font=big)
        al = int(255 * min(1, u * 1.5))
        d.text((SAFE_X0 + 280 - bbx[0], 1190 - bbx[3]), 'x4', font=big, fill=(255, 60, 120, al))
    im.alpha_composite(lay)
    o = np.asarray(im.convert('RGB'), np.float32) / 255
    if DRAG_AT <= t < DRAG_AT + 0.25:              # small shake on the slam
        o = np.roll(o, int(6 * math.sin(t * 90)), 1)
    o = vignette(o, 0.3); o = grain(o, i, 0.02)
    return to8(o)

STYLES = {1: style1, 2: style2, 3: style3, 4: style4, 5: style5, 6: style6}

# ------------------------------------------------------------------ driver
def frames_job(args):
    st, i = args
    out = os.path.join(OUT, 'frames', 's%d' % st, '%04d.png' % i)
    Image.fromarray(STYLES[st](i)).save(out, compress_level=1)
    return i

def cmd_frames(st, a=0, b=N, procs=3):
    os.makedirs(os.path.join(OUT, 'frames', 's%d' % st), exist_ok=True)
    t0 = time.time()
    from multiprocessing import Pool
    with Pool(procs) as p:
        for _ in p.imap_unordered(frames_job, [(st, i) for i in range(a, b)]):
            pass
    dt = time.time() - t0
    print('style %d post frames %d-%d: %.1f s (%.2f s/frame)' % (st, a, b - 1, dt, dt / (b - a)))
    with open(os.path.join(OUT, 'logs', 'post_times.txt'), 'a') as f:
        f.write('style %d frames %d-%d post %.1f s\n' % (st, a, b - 1, dt))

def cmd_encode(st):
    src = os.path.join(OUT, 'frames', 's%d' % st, '%04d.png')
    dst = os.path.join(OUT, 'style-%d.mp4' % st)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', src,
                    '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', '%.3f' % (N / FPS),
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', dst], check=True)
    print(dst)

def cmd_preview(music=None):
    lst = os.path.join(OUT, 'concat.txt')
    with open(lst, 'w') as f:
        for st in range(1, 7):
            f.write("file '%s'\n" % os.path.join(OUT, 'style-%d.mp4' % st))
    dst = os.path.join(OUT, 'preview.mp4')
    if music:
        tmp = os.path.join(OUT, 'preview_silent.mp4')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst,
                        '-c', 'copy', tmp], check=True)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-stream_loop', '-1', '-i', music,
                        '-map', '0:v', '-map', '1:a', '-t', '%.3f' % (6 * N / FPS), '-c:v', 'copy',
                        '-af', 'afade=t=out:st=%.2f:d=1.0,loudnorm=I=-16' % (6 * N / FPS - 1.0),
                        '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', dst], check=True)
    else:
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst,
                        '-c', 'copy', '-movflags', '+faststart', dst], check=True)
    print(dst)

if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'frames':
        st = int(sys.argv[2])
        a = int(sys.argv[sys.argv.index('--from') + 1]) if '--from' in sys.argv else 0
        b = int(sys.argv[sys.argv.index('--to') + 1]) if '--to' in sys.argv else N
        cmd_frames(st, a, b)
    elif c == 'one':                      # single frame for inspection
        st, i = int(sys.argv[2]), int(sys.argv[3])
        os.makedirs(os.path.join(OUT, 'test'), exist_ok=True)
        t0 = time.time(); fr = STYLES[st](i)
        print('style %d frame %d %.2f s' % (st, i, time.time() - t0))
        Image.fromarray(fr).save(os.path.join(OUT, 'test', 'p%d_%04d.png' % (st, i)))
    elif c == 'encode':
        cmd_encode(int(sys.argv[2]))
    elif c == 'preview':
        cmd_preview(sys.argv[sys.argv.index('--music') + 1] if '--music' in sys.argv else None)
