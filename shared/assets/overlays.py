"""Sharp full-res overlays for the 3D pixel episodes (and any episode that needs a caption safe zone).

The 3D scene is rendered at 270x480 and upscaled 4x nearest (`upscale`), then these draw on top at 1080x1920 with
smooth resampling, so text never gets pixelated. Every text element records its bounding box in BOXES, so an episode
can assert that all text stays inside the TikTok safe zone (12-62 % of the height, left 85 % of the width).

    from assets import overlays as ov      # with shared/ on sys.path
    ov.chip(cv, t, t0, t1, 'NO LAW', x, y, col=ov.RED)
    ov.stamp(cv, t, t0, t1, ('SECRET', 'DEAL'), x, y)
    ov.poll(cv, t, t0, t1, 'Remove the limit?', x, y, scale)
Uses shared/episode.py fonts and the poll sticker art, so the look matches the 2D episodes exactly.
"""
import math, random
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter
import episode as kit
from episode import W, H, NAVY, RED, YEL, GRN, WHITE, font, text_img, headline_img
from pixanim.motion import prog, ob
from pixanim.fx import popin, popout

SAFE = (0, round(0.12 * H), round(0.85 * W), round(0.62 * H))    # x0, y0, x1, y1 for text
SAFE_CX = (SAFE[0] + SAFE[2]) // 2 + 10                             # centre column of the safe zone (~470)
BOXES = []                                                          # (label, (x0, y0, x1, y1)) drawn this frame
INK = (10, 10, 16)


def reset(): BOXES.clear()


def upscale(path, k=4):
    """270x480 frame -> 1080x1920, nearest neighbour (every 3D pixel becomes a crisp k x k block)."""
    im = Image.open(path).convert('RGB')
    return im.resize((im.width * k, im.height * k), Image.NEAREST)


def place(cv, img, cx, cy, k=1.0, rot=0.0, label='text'):
    """Paste img centred at (cx, cy), scaled by k and rotated (smooth resampling: text stays sharp); records its box."""
    if k <= 0.01: return None
    if abs(k - 1) > 0.003: img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.BICUBIC)
    if rot: img = img.rotate(rot, resample=Image.BICUBIC, expand=True)
    x, y = round(cx - img.width / 2), round(cy - img.height / 2)
    cv.paste(img, (x, y), img)
    bb = img.getchannel('A').getbbox()
    if bb and label: BOXES.append((label, (x + bb[0], y + bb[1], x + bb[2], y + bb[3])))
    return img


def violations():
    x0, y0, x1, y1 = SAFE
    return [(lab, b) for lab, b in BOXES if b[0] < x0 or b[1] < y0 or b[2] > x1 or b[3] > y1]


def clamp_to_safe(cx, cy, w, h, pad=6):
    """Move a w x h box centred at (cx, cy) inside the safe zone."""
    x0, y0, x1, y1 = SAFE
    return (min(max(cx, x0 + w / 2 + pad), x1 - w / 2 - pad), min(max(cy, y0 + h / 2 + pad), y1 - h / 2 - pad))


def draw_safe(cv):
    """Preview aid: shade everything outside the text safe zone and outline it."""
    x0, y0, x1, y1 = SAFE
    sh = Image.new('RGBA', (W, H), (255, 0, 80, 60)); d = ImageDraw.Draw(sh)
    d.rectangle((x0, y0, x1, y1), fill=(0, 0, 0, 0)); d.rectangle((x0, y0, x1, y1), outline=(0, 255, 120, 255), width=4)
    cv.paste(sh, (0, 0), sh)


# ------------------------------------------------------------------ text pieces
@lru_cache(None)
def chip_img(txt, col=YEL, sz=56, sub=None):
    """Plain text chip: dark plate with a coloured edge, white bold text (brand names, hedges, labels)."""
    f = font(sz); fs = font(int(sz * 0.6)); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    tw = d0.textlength(txt, font=f); sw = d0.textlength(sub, font=fs) if sub else 0
    w = int(max(tw, sw) + 64); h = int(sz * 1.25 + (sz * 0.78 if sub else 0) + 26)
    img = Image.new('RGBA', (w + 12, h + 14), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((10, 12, w + 10, h + 12), 20, fill=NAVY)
    d.rounded_rectangle((0, 0, w, h), 20, fill=INK, outline=col, width=7)
    d.text(((w - tw) / 2, 12), txt, font=f, fill=col if col != WHITE else WHITE)
    if sub: d.text(((w - sw) / 2, 12 + sz * 1.18), sub, font=fs, fill=WHITE)
    return img


def chip(cv, t, t0, t1, txt, x, y, col=YEL, sz=56, rot=0.0, sub=None, clamp=True):
    if not (t0 <= t < t1 + 0.2): return
    img = chip_img(txt, col, sz, sub)
    k = popin(t, t0, 0.26) * popout(t, t1, 0.18)
    if clamp: x, y = clamp_to_safe(x, y, img.width + 30, img.height + 30)
    place(cv, img, x, y, k, rot + 1.2 * math.sin(t * 3 + x), 'chip ' + txt)


@lru_cache(None)
def stamp_img(lines=('SECRET', 'DEAL'), col=(224, 48, 58), sz=118):
    """Rubber stamp: double red border, heavy text, ink speckle knocked out (deterministic)."""
    f = font(sz); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    tw = max(d0.textlength(ln, font=f) for ln in lines); w, h = int(tw + 110), int(len(lines) * sz * 1.05 + 90)
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((6, 6, w - 6, h - 6), 26, outline=col + (255,), width=14)
    d.rounded_rectangle((26, 26, w - 26, h - 26), 16, outline=col + (255,), width=5)
    for i, ln in enumerate(lines):
        lw = d0.textlength(ln, font=f); d.text(((w - lw) / 2, 34 + i * sz * 1.05), ln, font=f, fill=col + (255,))
    rnd = random.Random(7); a = img.getchannel('A'); da = ImageDraw.Draw(a)
    for _ in range(260):
        x, y, r = rnd.uniform(0, w), rnd.uniform(0, h), rnd.choice((2, 3, 3, 4, 6))
        da.ellipse((x - r, y - r, x + r, y + r), fill=rnd.choice((0, 60, 120)))
    img.putalpha(a.point(lambda v: int(v * 0.94)))
    return img


def stamp(cv, t, t0, t1, lines, x, y, rot=-12.0, scale=1.0):
    """Stamp slams in at t0 (drops from 1.35x to 1x with a wobble), holds, pops out at t1."""
    if not (t0 <= t < t1 + 0.2): return
    u = prog(t, t0, 0.13)
    k = (1.35 - 0.35 * u * u if u < 1 else 1 + 0.06 * math.exp(-(t - t0 - 0.13) * 14) * math.cos((t - t0) * 50)) * popout(t, t1, 0.18)
    place(cv, stamp_img(tuple(lines)), x, y, k * scale, rot, 'stamp')


def headline(cv, t, t1, lines, x=SAFE_CX, y=420, sz=104, maxw=800):
    """2D-episode hook headline (episode.headline_img: white, black outline, one highlighted word on a plate)."""
    if t >= t1 + 0.2: return
    img = headline_img(lines, sz)
    k = (1 + 0.14 * math.exp(-max(t, 0) * 9) * math.cos(max(t, 0) * 22)) * popout(t, t1, 0.2) * (1 + 0.02 * math.sin(t * 7))
    k *= min(1, maxw / img.width)
    place(cv, img, x, y, k, -2 + 1.5 * math.sin(t * 3), 'headline')


def poll(cv, t, t0, t1, question, x, y, scale=1.0, opts=(('YES', GRN), ('NO', RED)), rot=-3.0):
    """The 2D poll sticker (white card, bold YES / NO buttons that light up in turn) at any scale."""
    if not (t0 <= t < t1 + 0.2): return
    sel = int((t - t0) * 2.5) % len(opts)
    img = kit._sticker_img((question,), tuple(opts), sel, 860)
    k = popin(t, t0, 0.3) * popout(t, t1, 0.2) * (1 + 0.02 * math.sin(t * 6)) * scale
    place(cv, img, x, y, k, rot + 2 * math.sin(t * 2.5), 'poll')


def tag(cv, x=60, y=SAFE[1] + 4):
    """'car stuff, explained' series tag, top-left, inside the safe zone."""
    img = text_img('car stuff, explained', WHITE, 40)
    place(cv, img, x + img.width / 2, y + img.height / 2, 1.0, 0, 'tag')


def captions(cv, t, y, x=SAFE_CX, maxw=840):
    """episode.captions (chunks of <=3 words, spoken word bounces, one highlighted keyword), inside the safe zone."""
    E = kit.E
    if t >= E['end_t']: return
    words = E['words']
    for ci, (st, en, idxs) in enumerate(E['chunks']):
        if st <= t < en:
            act = max([i for i in idxs if words[i]['s'] <= t] or [-1]); pop = 0
            if act >= 0:
                u = (t - words[act]['s']) / 0.18
                pop = round(4 * (math.sin(min(u, 1) * math.pi) if u < 1 else 0.5 * math.exp(-(u - 1) * 2)))
            img = kit.caption_img(ci, act, pop)
            k = (0.72 + 0.28 * ob(prog(t, st, 0.16))) * min(1, maxw / img.width); dy = 18 * (1 - ob(prog(t, st, 0.2)))
            place(cv, img, x, y + dy, k, 0, 'caption')
            return


@lru_cache(None)
def credit_img(text, maxw=820):
    f = font(24); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    while d0.textlength(text, font=f) > maxw - 20: text = text[:-4] + '...'
    img = Image.new('RGBA', (int(d0.textlength(text, font=f)) + 24, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, img.width - 1, 39), 10, fill=(10, 10, 16, 170))
    d.text((12, 6), text, font=f, fill=(214, 218, 226, 240))
    return img


def credit(cv, text, y, x=SAFE_CX):
    img = credit_img(text); place(cv, img, x, y, 1.0, 0, 'credit')


# ------------------------------------------------------------------ clean kinetic text (no offset copy behind it)
@lru_cache(None)
def word_img(txt, col=WHITE, sz=100):
    """One word: fill colour, a single dark outline and a soft blurred drop shadow (no hard offset duplicate)."""
    f = font(sz); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1))); st = max(6, sz // 12)
    l, _, r, _ = d0.textbbox((0, 0), txt, font=f, stroke_width=st); _, tp, _, b = d0.textbbox((0, 0), 'ÁHgy', font=f, stroke_width=st)
    pad = 34                                                    # shared vertical metrics: every word sits on one baseline
    img = Image.new('RGBA', (r - l + 2 * pad, b - tp + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img); d.text((pad - l, pad - tp), txt, font=f, fill=col, stroke_width=st, stroke_fill=INK)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); a = img.getchannel('A').filter(ImageFilter.GaussianBlur(12))
    sh.putalpha(a.point(lambda v: int(v * 0.6)))
    out = Image.new('RGBA', img.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 10)); out.alpha_composite(img)
    return out


def kinetic(cv, t, lines, times, y, t1=99.0, sz=100, x=SAFE_CX, maxw=770, label='headline'):
    """Headline built word by word: lines = [[(word, colour or None), ...], ...]; times = one appear time per word
    (flat). Each word pops in with a small overshoot at its time; the layout is fixed, so nothing jumps."""
    if t >= t1 + 0.2: return
    d0 = ImageDraw.Draw(Image.new('RGB', (1, 1))); f = font(sz); sp = d0.textlength(' ', font=f)
    widths = [[d0.textlength(w, font=f) for w, _ in ln] for ln in lines]
    k0 = min(1.0, maxw / max(sum(ws) + sp * (len(ws) - 1) for ws in widths)); lh = sz * 1.12 * k0
    i = 0
    for li, (ln, ws) in enumerate(zip(lines, widths)):
        cx = x - (sum(ws) + sp * (len(ws) - 1)) * k0 / 2; cy = y + (li - (len(lines) - 1) / 2) * lh
        for (w, col), wd in zip(ln, ws):
            ti = times[i]; i += 1
            k = (popin(t, ti, 0.24) if ti is not None else 1.0) * popout(t, t1, 0.18)
            if k > 0.02: place(cv, word_img(w, col or WHITE, sz), cx + wd * k0 / 2, cy, k * k0, 0.0, label)
            cx += (wd + sp) * k0


@lru_cache(None)
def pill_img(txt, col=YEL, sz=60):
    """Label pill: dark rounded plate, coloured rim, coloured text, soft shadow."""
    f = font(sz); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1))); l, _, r, _ = d0.textbbox((0, 0), txt, font=f)
    _, tp, _, b = d0.textbbox((0, 0), 'HG', font=f)
    w, h, pad = r - l + 70, b - tp + 44, 26
    img = Image.new('RGBA', (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((pad, pad, pad + w, pad + h), h // 2, fill=(12, 16, 22, 235), outline=col, width=6)
    d.text((pad + 35 - l, pad + 22 - tp), txt, font=f, fill=col)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); sh.putalpha(img.getchannel('A').filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.5)))
    out = Image.new('RGBA', img.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 8)); out.alpha_composite(img)
    return out


def pill(cv, t, t0, t1, txt, x, y, col=YEL, sz=60):
    if not (t0 <= t < t1 + 0.2): return
    img = pill_img(txt, col, sz); x, y = clamp_to_safe(x, y, img.width - 40, img.height - 40)
    place(cv, img, x, y, popin(t, t0, 0.24) * popout(t, t1, 0.18), 0.0, 'pill ' + txt)


# ------------------------------------------------------------------ pills pinned to 3D anchors (rear-engine-3d)
@lru_cache(None)
def chip_icon(sz=44, col=YEL):
    """Small microchip glyph (square die, pins on every side) for 'ELECTRONICS'-style pills."""
    img = Image.new('RGBA', (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(img); p = sz // 5; w = max(2, sz // 14)
    for k in range(4):
        o = p + 4 + k * (sz - 2 * p - 8) // 3
        for a in ((o, 0, o + w, p), (o, sz - p, o + w, sz), (0, o, p, o + w), (sz - p, o, sz, o + w)): d.rectangle(a, fill=col)
    d.rounded_rectangle((p, p, sz - p, sz - p), 4, fill=(12, 16, 22, 255), outline=col, width=w)
    d.rectangle((sz // 2 - w * 2, sz // 2 - w * 2, sz // 2 + w * 2, sz // 2 + w * 2), fill=col)
    return img


@lru_cache(None)
def icon_pill_img(txt, col=YEL, sz=60, icon='chip'):
    """pill_img with a small chip glyph in front of the text (same plate, rim and shadow)."""
    f = font(sz); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1))); l, _, r, _ = d0.textbbox((0, 0), txt, font=f)
    _, tp, _, b = d0.textbbox((0, 0), 'HG', font=f); ic = chip_icon(int(sz * 0.85), col)
    w, h, pad = r - l + 70 + ic.width + 14, b - tp + 44, 26
    img = Image.new('RGBA', (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((pad, pad, pad + w, pad + h), h // 2, fill=(12, 16, 22, 235), outline=col, width=6)
    img.alpha_composite(ic, (pad + 30, pad + (h - ic.height) // 2))
    d.text((pad + 44 + ic.width - l, pad + 22 - tp), txt, font=f, fill=col)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); sh.putalpha(img.getchannel('A').filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.5)))
    out = Image.new('RGBA', img.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 8)); out.alpha_composite(img)
    return out


def pin(cv, t, t0, t1, txt, target, x, y, col=YEL, sz=58, icon=None):
    """Pill inside the safe zone with a leader line + dot to a moving screen point (e.g. a projected 3D anchor).
    target: (x, y) in 1080x1920 px or None. The leader is art (not text), so it may run into the bottom 38 %."""
    if not (t0 <= t < t1 + 0.2): return
    img = icon_pill_img(txt, col, sz, icon) if icon else pill_img(txt, col, sz)
    x, y = clamp_to_safe(x, y, img.width * 1.15, img.height * 1.15)     # room for the pop-in overshoot
    k = popin(t, t0, 0.24) * popout(t, t1, 0.18)
    if target and k > 0.3:
        tx, ty = target; d = ImageDraw.Draw(cv); y0 = y + (img.height / 2 - 30) * k * (1 if ty > y else -1)
        e = min(1.0, (t - t0) / 0.25); ex, ey = x + (tx - x) * e, y0 + (ty - y0) * e
        d.line((x, y0, ex, ey), fill=INK, width=12); d.line((x, y0, ex, ey), fill=col, width=5)
        if e >= 1: d.ellipse((tx - 13, ty - 13, tx + 13, ty + 13), fill=INK); d.ellipse((tx - 8, ty - 8, tx + 8, ty + 8), fill=col)
    place(cv, img, x, y, k, 0.0, 'pill ' + txt)
