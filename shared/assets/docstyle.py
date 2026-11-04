"""Mini-documentary kit: real photos with eased Ken Burns, parallax over a blurred copy, kinetic headlines, name chips,
pills, a timeline with a year counter, speech card, segmented progress bar, colour grade, film grain and vignette.
Text goes through overlays.place, so overlays.violations() checks the TikTok safe zone. First used by
videos/brand-story-lamborghini.

    from assets import docstyle as ds          # with shared/ on sys.path
    ds.PHOTO_DIR = '<episode>/assets'          # photos are <name>_original.jpg (else <name>.jpg)
    img = ds.parallax('hero', t, t0, t1, crop=(0, 0, 1, 1), z=(1.0, 1.2), pan=((.5, .5), (.6, .5)))
    ds.headline(cv, t, t0, t1, 'BECAUSE OF A BAD CLUTCH', hi={'BAD', 'CLUTCH'}, beats=[(t_word, 'CLUTCH')])
    ds.finish(img, t)                          # grain + vignette, last
Upscaling of the sharp photo is capped at MAX_UP (1.5x): parallax() raises if a crop would need more.
"""
import math, os
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from episode import W, H, NAVY, YEL, RED, WHITE, font
from pixanim.motion import prog, ob, io, ic, clamp
from pixanim.fx import popin, popout
from assets import overlays as ov

PHOTO_DIR = '.'
MAX_UP = 1.5
INK = (10, 10, 16)
STATS = {'max_up': 0.0}


def ease(u): return io(clamp(u))


# ------------------------------------------------------------------ photos
@lru_cache(None)
def graded(name):
    """One consistent grade for every photo: a touch of contrast, slightly muted colour, teal shadows, warm highlights."""
    p = os.path.join(PHOTO_DIR, name + '_original.jpg')
    im = Image.open(p if os.path.isfile(p) else os.path.join(PHOTO_DIR, name + '.jpg')).convert('RGB')
    im = ImageEnhance.Color(ImageEnhance.Contrast(im).enhance(1.1)).enhance(0.9)
    a = np.asarray(im).astype(np.float32) / 255
    lum = a.mean(2, keepdims=True); sh = (1 - lum) ** 2; hl = lum ** 2
    a = a + sh * np.array([-0.035, 0.01, 0.03]) + hl * np.array([0.035, 0.012, -0.03])
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def _crop(name, crop):
    im = graded(name); x0, y0, x1, y1 = crop
    return im.crop((round(x0 * im.width), round(y0 * im.height), round(x1 * im.width), round(y1 * im.height)))


@lru_cache(None)
def cropped(name, crop): return _crop(name, crop)


@lru_cache(None)
def _blur_bg(name, crop, dark=0.45):
    """Blurred, darkened cover of the frame (overscanned 15 % so it can drift); built from a small copy (it is a blur)."""
    im = cropped(name, crop); k = max(W * 1.15 / im.width, H * 1.15 / im.height)
    small = im.resize((max(1, round(im.width * k / 8)), max(1, round(im.height * k / 8))), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(5))
    big = small.resize((round(im.width * k), round(im.height * k)), Image.BICUBIC)
    return ImageEnhance.Brightness(big).enhance(dark)


def kb_window(iw, ih, z, c):
    """Crop window (x0, y0, x1, y1) of an iw x ih image at zoom z (>= 1) centred on c=(fx, fy), kept inside."""
    w, h = iw / z, ih / z
    cx = min(max(c[0] * iw, w / 2), iw - w / 2); cy = min(max(c[1] * ih, h / 2), ih - h / 2)
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def kenburns(name, crop, t, t0, t1, out_w, out_h=None, z=(1.0, 1.15), pan=((.5, .5), (.5, .5)), e=ease):
    """Eased pan-and-zoom of a photo crop, Lanczos-scaled to out_w (height keeps the crop's proportion unless out_h)."""
    im = cropped(name, crop); u = e(prog(t, t0, t1 - t0))
    zz = z[0] + (z[1] - z[0]) * u; c = (pan[0][0] + (pan[1][0] - pan[0][0]) * u, pan[0][1] + (pan[1][1] - pan[0][1]) * u)
    if out_h is None: out_h = round(out_w * im.height / im.width)
    ar = out_w / out_h                                       # fit the window to the output aspect (never stretch)
    iw, ih = (im.width, im.width / ar) if im.width / im.height < ar else (im.height * ar, im.height)
    x0, y0, x1, y1 = kb_window(iw, ih, zz, c)
    ox, oy = (im.width - iw) * c[0], (im.height - ih) * c[1]
    up = out_w / (x1 - x0); STATS['max_up'] = max(STATS['max_up'], up)
    if up > MAX_UP + 1e-3: raise ValueError(f'{name}: {up:.2f}x upscale > {MAX_UP}')
    return im.resize((out_w, out_h), Image.LANCZOS, box=(x0 + ox, y0 + oy, x1 + ox, y1 + oy))


def background(name, crop, t, t0, t1, drift=(0.0, 0.0), dark=0.45, z=(1.0, 1.06)):
    """Full-frame blurred, darkened copy that drifts slowly (the back layer of the parallax)."""
    bg = _blur_bg(name, crop, dark) if dark == 0.45 else ImageEnhance.Brightness(_blur_bg(name, crop)).enhance(dark / 0.45)
    u = ease(prog(t, t0, t1 - t0)); zz = z[0] + (z[1] - z[0]) * u
    w, h = W / zz, H / zz                                    # bg pixels are 1:1 with the frame at zoom 1 (15 % overscan)
    cx = bg.width / 2 + drift[0] * (u - .5) * (bg.width - w); cy = bg.height / 2 + drift[1] * (u - .5) * (bg.height - h)
    cx = min(max(cx, w / 2), bg.width - w / 2); cy = min(max(cy, h / 2), bg.height - h / 2)
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    return bg.resize((W, H), Image.BILINEAR, box=box)


@lru_cache(None)
def _card_shadow(w, h):
    s = Image.new('RGBA', (w + 120, h + 120), (0, 0, 0, 0))
    ImageDraw.Draw(s).rounded_rectangle((60, 70, w + 60, h + 70), 18, fill=(0, 0, 0, 170))
    return s.filter(ImageFilter.GaussianBlur(22))


def card(cv, img, cx, cy, radius=18, border=(240, 240, 236)):
    """Paste a sharp photo with a soft drop shadow and a thin light border (the front layer of the parallax)."""
    w, h = img.size; s = _card_shadow(w, h); cv.paste(s, (round(cx - w / 2 - 60), round(cy - h / 2 - 60)), s)
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=255)
    x, y = round(cx - w / 2), round(cy - h / 2); cv.paste(img, (x, y), m)
    ImageDraw.Draw(cv).rounded_rectangle((x - 3, y - 3, x + w + 2, y + h + 2), radius + 3, outline=border, width=4)


def parallax(name, t, t0, t1, crop=(0, 0, 1, 1), w=1000, cy=1000, z=(1.0, 1.15), pan=((.5, .5), (.5, .5)),
             drift=(0.6, 0.2), slide=(0, 0), dark=0.45):
    """Blurred background drifting one way + sharp Ken Burns card moving the other way = depth. Returns RGB frame."""
    cv = background(name, crop, t, t0, t1, drift, dark).convert('RGB')
    w = min(w, int(MAX_UP * cropped(name, crop).width / max(z)))      # shrink the card rather than upscale past the cap
    fg = kenburns(name, crop, t, t0, t1, w, z=z, pan=pan)
    u = ease(prog(t, t0, t1 - t0)) - .5
    card(cv, fg, W / 2 - drift[0] * 40 * u + slide[0], cy - drift[1] * 30 * u + slide[1])
    return cv


def shake(img, t, t0, amp=18, decay=4.0, freq=31):
    """Camera shake: decaying jitter + a hair of rotation; the frame is overscanned so no edges show."""
    a = amp * math.exp(-max(0, t - t0) * decay)
    if a < 0.4: return img
    dx, dy = a * math.sin(t * freq), a * math.cos(t * freq * 1.31 + 1)
    k = 1 + 2.4 * a / W
    return img.transform(img.size, Image.AFFINE, (1 / k, 0, (W - W / k) / 2 - dx / k, 0, 1 / k, (H - H / k) / 2 - dy / k), Image.BICUBIC)


def split(t, t0, left, right, w=540, h=700, cy=960, gap=12):
    """Two photo panels side by side (left / right = (name, crop, flip)), sliding in from opposite edges to meet nose to nose."""
    cv = Image.new('RGB', (W, H), (14, 14, 20))
    u = ob(prog(t, t0, 0.45))
    for i, (name, crop, flip) in enumerate((left, right)):
        img = kenburns(name, crop, t, t0, t0 + 3, w - gap // 2, h, z=(1.0, 1.05))
        if flip: img = img.transpose(Image.FLIP_LEFT_RIGHT)
        x = (0 if i == 0 else w + gap // 2) + (-1 if i == 0 else 1) * (1 - u) * 600
        cv.paste(img, (round(x), round(cy - h / 2)))
    return cv


# ------------------------------------------------------------------ text
@lru_cache(None)
def word_img(txt, col=WHITE, sz=96):
    """One headline word: bold white (or highlight colour) with a thick dark outline and a soft offset shadow."""
    f = font(sz); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1))); tw = d0.textlength(txt, font=f)
    img = Image.new('RGBA', (int(tw) + 50, int(sz * 1.45)), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.text((25 + 5, 10 + 7), txt, font=f, fill=(0, 0, 0, 150), stroke_width=12, stroke_fill=(0, 0, 0, 150))
    d.text((25, 10), txt, font=f, fill=col, stroke_width=11, stroke_fill=INK)
    return img


def layout(words, sz, maxw):
    """Greedy line wrap -> [(word, x_centre_offset, line_index)], line count."""
    sp = sz * 0.34; lines, cur, cw = [], [], 0
    for wd in words:
        ww = word_img(wd, WHITE, sz).width - 50
        if cur and cw + sp + ww > maxw: lines.append((cur, cw)); cur, cw = [], 0
        cur.append((wd, ww)); cw += (sp if len(cur) > 1 else 0) + ww
    lines.append((cur, cw)); out = []
    for li, (ln, lw) in enumerate(lines):
        x = -lw / 2
        for wd, ww in ln: out.append((wd, x + ww / 2, li)); x += ww + sp
    return out, len(lines)


def headline(cv, t, t0, t1, text, hi=(), beats=(), x=ov.SAFE_CX, y=420, sz=96, maxw=820, settled=False):
    """Kinetic headline, one phrase at a time: words pop in one after another from t0 (or are all on at t0 with a punch
    when settled=True, e.g. frame 0), each word kicks when spoken (beats = [(time, word_index)]), and the phrase lifts
    out at t1. Highlighted words (hi, upper-case match) are yellow."""
    if not (t0 <= t < t1 + 0.25): return
    words = text.split(); items, nl = layout(tuple(words), sz, maxw); lh = sz * 1.12
    out = ic(prog(t, t1, 0.25)); kick = {i: tb for tb, i in beats}
    g = (1 + 0.1 * math.exp(-(t - t0) * 9) * math.cos((t - t0) * 24)) if settled else 1.0   # whole-phrase punch
    for i, (wd, dx, li) in enumerate(items):
        k = g if settled else popin(t, t0 + 0.06 * i, 0.24)
        if i in kick and t >= kick[i]: k *= 1 + 0.1 * math.exp(-(t - kick[i]) * 10)
        k *= 1 - out
        col = YEL if wd.strip('.,?!').upper() in hi else WHITE
        ov.place(cv, word_img(wd, col, sz), x + dx * g, y + (li - (nl - 1) / 2) * lh * g - 40 * out, k, 0, 'headline')


@lru_cache(None)
def pill_img(txt, col=YEL, sz=44, fill=INK, tcol=None):
    f = font(sz); tw = ImageDraw.Draw(Image.new('RGB', (1, 1))).textlength(txt, font=f)
    w, h = int(tw + sz * 1.3), int(sz * 1.6)
    img = Image.new('RGBA', (w + 8, h + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((6, 9, w + 6, h + 9), h // 2, fill=(0, 0, 0, 140))
    d.rounded_rectangle((0, 0, w, h), h // 2, fill=fill, outline=col, width=5)
    d.text(((w - tw) / 2, h / 2 - sz * 0.62), txt, font=f, fill=tcol or col)
    return img


def pill(cv, t, t0, t1, txt, x, y, col=YEL, sz=44, fill=INK, tcol=None, flash=0.0, rot=0.0):
    """Small label pill (pops in, gentle wobble). flash=Hz blinks it between filled and outlined (warning labels)."""
    if not (t0 <= t < t1 + 0.2): return
    if flash and int((t - t0) * flash * 2) % 2: fill, tcol = INK, col
    img = pill_img(txt, col, sz, fill, tcol)
    x, y = ov.clamp_to_safe(x, y, img.width, img.height)
    ov.place(cv, img, x, y, popin(t, t0, 0.24) * popout(t, t1, 0.18), rot + 1.0 * math.sin(t * 3 + x), 'pill ' + txt)


@lru_cache(None)
def name_chip_img(txt, sz=40):
    """Name chip: plain grey silhouette icon (head and shoulders, no likeness) + the name on a dark pill."""
    f = font(sz); tw = ImageDraw.Draw(Image.new('RGB', (1, 1))).textlength(txt, font=f)
    h = int(sz * 2.0); w = int(h + tw + sz * 1.0)
    img = Image.new('RGBA', (w + 8, h + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((6, 9, w + 6, h + 9), h // 2, fill=(0, 0, 0, 140))
    d.rounded_rectangle((0, 0, w, h), h // 2, fill=INK, outline=YEL, width=5)
    r = h / 2 - 8; cx, cy = h / 2, h / 2
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(200, 204, 212))
    d.ellipse((cx - r * .36, cy - r * .62, cx + r * .36, cy + r * .1), fill=(70, 74, 86))
    d.pieslice((cx - r * .7, cy + r * .2, cx + r * .7, cy + r * 1.5), 180, 360, fill=(70, 74, 86))
    d.text((h + 4, h / 2 - sz * 0.62), txt, font=f, fill=WHITE)
    return img


def name_chip(cv, t, t0, t1, txt, x, y, sz=40):
    if not (t0 <= t < t1 + 0.2): return
    img = name_chip_img(txt, sz); x, y = ov.clamp_to_safe(x, y, img.width, img.height)
    sl = 60 * (1 - ob(prog(t, t0, 0.35)))
    ov.place(cv, img, x - sl, y, popin(t, t0, 0.3) * popout(t, t1, 0.18), 0, 'name ' + txt)


def year_counter(cv, t, t0, t1, a, b, x=ov.SAFE_CX, y=640, sz=170, end=None):
    """Big year that ticks from a to b between t0 and t1 (eased), then holds; returns the shown year (for tick sounds)."""
    if not (t0 - 0.3 <= t < (end or 1e9) + 0.2): return None
    yr = round(a + (b - a) * ease(prog(t, t0, t1 - t0)))
    k = popin(t, t0 - 0.3, 0.3) * (popout(t, end, 0.18) if end else 1) * (1 + 0.1 * math.exp(-(t - t1) * 8) if t >= t1 else 1)
    ov.place(cv, word_img(str(yr), YEL if yr == b else WHITE, sz), x, y, k, 0, 'year')
    return yr


def timeline(cv, t, t0, t1, a, b, mark=None, x0=90, x1=850, y=830, end=None):
    """Timeline bar from year a to b: rail with ticks, a fill that runs to the marker; only `mark` is labelled."""
    if not (t0 - 0.3 <= t < (end or 1e9) + 0.2): return
    al = popin(t, t0 - 0.3, 0.3) * (popout(t, end, 0.18) if end else 1)
    if al <= 0.01: return
    lay = Image.new('RGBA', (W, 160), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); yy = 60
    d.rounded_rectangle((x0 - 6, yy - 14, x1 + 6, yy + 14), 14, fill=(10, 10, 16, 200))
    d.rounded_rectangle((x0, yy - 6, x1, yy + 6), 6, fill=(236, 236, 242))
    for yr in range(a, b + 1):
        xt = x0 + (x1 - x0) * (yr - a) / (b - a); d.line((xt, yy - 22, xt, yy + 22) if yr % 5 == 0 else (xt, yy - 12, xt, yy + 12), fill=(236, 236, 242), width=4)
    u = ease(prog(t, t0, t1 - t0)); xp = x0 + (x1 - x0) * ((mark or b) - a) / (b - a) * u
    d.rounded_rectangle((x0, yy - 6, max(x0 + 12, xp), yy + 6), 6, fill=YEL)
    r = 20 * (1 + 0.4 * math.exp(-(t - t1) * 10) if t >= t1 else 1)
    d.ellipse((xp - r - 5, yy - r - 5, xp + r + 5, yy + r + 5), fill=INK); d.ellipse((xp - r, yy - r, xp + r, yy + r), fill=YEL)
    if mark and t >= t1:
        f = font(40); tw = d.textlength(str(mark), font=f)
        d.text((xp - tw / 2, yy + 34), str(mark), font=f, fill=YEL, stroke_width=6, stroke_fill=INK)
    if al < 1: lay.putalpha(lay.getchannel('A').point(lambda v: int(v * al)))
    ov.place(cv, lay, W / 2, y, 1.0, 0, 'timeline')


@lru_cache(None)
def speech_img(lines, hi, sz=104, w=820):
    """Speech card: white rounded bubble with a tail, dark bold quote; the highlight word on a dark plate in yellow."""
    f = font(sz); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1))); lh = int(sz * 1.2)
    h = 70 + lh * len(lines) + 40
    img = Image.new('RGBA', (w + 20, h + 90), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for o, c in ((12, (0, 0, 0, 120)), (0, (250, 250, 246, 255))):
        d.rounded_rectangle((o, o, w + o, h + o), 44, fill=c)
        d.polygon([(w * .22 + o, h - 2 + o), (w * .16 + o, h + 80 + o), (w * .38 + o, h - 2 + o)], fill=c)
    d.text((34, -30), '“', font=font(150), fill=(200, 204, 212))
    for i, ln in enumerate(lines):
        tw = d0.textlength(ln, font=f); x = (w - tw) / 2; yy = 60 + i * lh
        if ln == hi:
            d.rounded_rectangle((x - 22, yy - 4, x + tw + 22, yy + sz * 1.12), 22, fill=INK)
            d.text((x, yy - 6), ln, font=f, fill=YEL)
        else: d.text((x, yy - 6), ln, font=f, fill=NAVY)
    return img


def speech(cv, t, t0, t1, lines, hi=None, x=ov.SAFE_CX, y=600, k=1.0):
    if not (t0 <= t < t1 + 0.2): return
    s = popin(t, t0, 0.32) * popout(t, t1, 0.2) * k * (1 + 0.015 * math.sin(t * 5))
    ov.place(cv, speech_img(tuple(lines), hi), x, y, s, -2 + 1.2 * math.sin(t * 2.2), 'speech')


def progress(cv, t, dur, segs, x0=100, x1=W - 100, y=120, h=20, gap=10):
    """Segmented progress bar across the top (series look: navy rim, glow fill); segs = chapter start times."""
    d = ImageDraw.Draw(cv); bounds = list(segs) + [dur]
    d.rounded_rectangle((x0 - 7, y - 7, x1 + 7, y + h + 7), 16, fill=NAVY)
    for a, b in zip(bounds, bounds[1:]):
        sa = x0 + (x1 - x0) * a / dur + (gap / 2 if a > 0 else 0); sb = x0 + (x1 - x0) * b / dur - (gap / 2 if b < dur else 0)
        d.rounded_rectangle((sa, y, sb, y + h), 8, fill=(236, 236, 242))
        if t > a:
            xf = sa + (sb - sa) * clamp((t - a) / (b - a))
            if xf > sa + 4: d.rounded_rectangle((sa, y, xf, y + h), 8, fill=(255, 210, 63))


# ------------------------------------------------------------------ finish
@lru_cache(None)
def _vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.6)) ** 2)
    return (1 - 0.5 * np.clip(r - 0.55, 0, 1) ** 1.6).astype(np.float32)[..., None]


@lru_cache(None)
def _grain(i):
    g = np.random.default_rng(1000 + i).normal(0, 1, (H // 2, W // 2)).astype(np.float32)
    return np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None]


def finish(img, t, grain=7.0, fps=60):
    """Subtle film grain (changes every 2 frames, 8 patterns) and a soft vignette. Returns RGB Image."""
    a = np.asarray(img, dtype=np.float32) * _vignette() + _grain(int(t * fps / 2) % 8) * grain
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
