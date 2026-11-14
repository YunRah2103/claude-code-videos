"""Gold engine bay - "mission brief" cut with the documentary voice.

Four visual layers under one brief layout (black, thin rules, data cards, yellow highlighter,
centred captions):  white wireframe (question) -> ASCII (V12) -> thermal (carbon + gold)
-> LiDAR (16 g) -> wireframe (your call). All times come from timing.json (aligned voice).

  python brief.py still OUTDIR T [T ...]
  python brief.py video OUT.mp4 VOICE.wav [START END]
"""
import math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import combo
import pc
import render as R
import scene
import styles as ST
from render import B, DUR, FPS, W, H, WORDS, clamp, prog, io, oc, heat_i, foil_p

F32 = np.float32
INTER = "/usr/share/fonts/opentype/inter/Inter-"
JB = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-"
_F = {}
def sans(size, w="SemiBold"):
    k = ("s", size, w)
    if k not in _F: _F[k] = ImageFont.truetype(INTER + w + ".otf", int(size))
    return _F[k]
def mono(size, w="Medium"):
    k = ("m", size, w)
    if k not in _F: _F[k] = ImageFont.truetype(JB + w + ".ttf", int(size))
    return _F[k]

WHITE = (236, 236, 232); GREY = (138, 138, 136); DIM = (90, 90, 92); HL = (236, 212, 58); INK = (12, 12, 14)
X0, X1 = 64, R.SAFE_X1 - 10                     # text column
CAP_Y = 1060

def wstart(word, n=1):
    hits = [w for w in WORDS if w["w"].strip("?.,").lower() == word.lower()]
    return hits[n - 1]["s"]

# ---------- sections ----------
SECTIONS = [  # (visual, start, brief no., title)
    ("wire", 0.0, 1, "THE QUESTION"),
    ("ascii", B["reveal"] - 0.2, 2, "HEAT SOURCE"),
    ("thermal", wstart("and") - 0.2, 3, "THE PROBLEM"),
    ("lidar", B["lined"] - 0.1, 4, "THE FIX"),
    ("wire", B["question"] - 0.25, 5, "YOUR CALL"),
]
XF = 0.35                                          # crossfade


# ---------- white wireframe visual ----------
_PANEL = {}
def panel_grid():
    """Thin grid lines across the carbon panels (they turn gold as the foil wraps)."""
    if not _PANEL:
        A, Bv, wr = [], [], []
        for y in np.arange(0.1, 1.36, 0.1):
            A.append((-1.25, y, -0.58)); Bv.append((1.6, y, -0.58)); wr.append(0.30 + 0.70 * 0.0 + 0.05 * (y - 0.6))
            A.append((-0.76, y, -0.58)); Bv.append((-0.76, y, 0.02 if y < 1.1 else -0.58)); wr.append(0.0 + 0.05 * (y - 0.6))
        for x in np.arange(-1.2, 1.6, 0.1):
            A.append((x, 0.0, -0.58)); Bv.append((x, 1.36, -0.58))
            wr.append(float(scene.wrap_order(np.array([[x, 0.6, -0.58]]), np.array([False]))[0]))
        for z in np.arange(-0.55, 0.02, 0.1):
            A.append((-0.76, 0.0, z)); Bv.append((-0.76, 1.1, z))
            wr.append(float(scene.wrap_order(np.array([[-0.76, 0.6, z]]), np.array([True]))[0]))
        _PANEL.update(A=np.array(A, F32), B=np.array(Bv, F32), wrap=np.array(wr, F32))
    return _PANEL

def draw_segs(d, cam, A, Bv, cols, alphas, width):
    xa, ya, za = pc.proj(A, cam); xb, yb, zb = pc.proj(Bv, cam)
    for i in np.nonzero((za > 0.05) & (zb > 0.05))[0]:
        d.line((xa[i], ya[i], xb[i], yb[i]), fill=(*cols[i], int(255 * alphas[i])), width=width)

def wire_frame(t):
    cam = pc.camera(t)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for x in np.arange(-1.5, 1.81, 0.25):                                   # floor grid, very quiet
        ST.lines(d, cam, np.array([[x, 0, -0.58]], F32), np.array([[x, 0, 1.3]], F32), (70, 70, 74), 1, 0.6)
    for z_ in np.arange(-0.5, 1.31, 0.25):
        ST.lines(d, cam, np.array([[-1.6, 0, z_]], F32), np.array([[1.8, 0, z_]], F32), (70, 70, 74), 1, 0.6)
    pg = panel_grid(); fp = foil_p(t)
    gold = (fp - pg["wrap"]) > 0
    cols = np.where(gold[:, None], np.array([[226, 178, 60]]), np.array([[60, 60, 64]]))
    draw_segs(d, cam, pg["A"], pg["B"], cols, np.where(gold, 0.9, 0.7), 1)
    wv = ST.wire()
    if "vec" not in _PANEL:
        _PANEL["vec"] = ST.offsets(wv["part"], 1.0)
        _PANEL["dist"] = np.linalg.norm((wv["A"] + wv["B"]) / 2 - np.array([0.0, 0.45, 0.0], F32), axis=1)
    kx = io(prog(t, B["push"] + 0.15, 0.8)) * (1 - io(prog(t, B["reveal"] - 1.0, 0.7)))   # exploded view
    off = _PANEL["vec"] * kx
    A_, B_ = wv["A"] + off, wv["B"] + off
    s0 = 0.0 if t < SECTIONS[1][1] else SECTIONS[4][1]                     # draw-on at the open and at the finale
    rad = 0.2 + 2.6 * oc(prog(t, s0, 1.5))
    lead = np.clip(1 - (rad - _PANEL["dist"]) / 0.14, 0, 1) * (rad < 2.7)
    vis = _PANEL["dist"] < rad
    _, _, dz = pc.proj((A_ + B_) / 2, cam)
    alpha = np.clip(1.5 - dz / 4.2, 0.25, 1.0) * vis
    cols = np.tile(np.array([[232, 232, 228]]), (len(dz), 1)).astype(F32)
    hot = wv["mat"] == scene.HEADER
    cols[hot] = (255, 96, 60)
    cols[wv["mat"] == scene.CARBON] = (170, 170, 168)
    cols = cols * (1 - lead[:, None]) + np.array([[180, 235, 255]]) * lead[:, None]       # bright scan front
    draw_segs(d, cam, A_, B_, cols.astype(int), np.clip(alpha + lead * 0.4, 0, 1), 2)
    for P_, u in ST.heat_paths(t, 500, lags=(0.0, 0.012, 0.024)):          # faint heat flow
        x, y, z_ = pc.proj(P_, cam); ok = z_ > 0.05
        for xi, yi, ui in zip(x[ok], y[ok], u[ok]):
            d.point((xi, yi), fill=(255, int(120 - 60 * ui), 70, int(150 * math.sin(math.pi * ui) * min(1.0, heat_i(t)))))
    base = Image.new("RGBA", (W, H), (6, 6, 7, 255))
    glow = lay.filter(ImageFilter.GaussianBlur(5))
    base.alpha_composite(glow); base.alpha_composite(lay)
    return base.convert("RGB")

GAIN = {"wire": 1.0, "ascii": 1.08, "thermal": 1.25, "lidar": 1.3}       # lift the murkier looks

def visual(name, t):
    im = _visual(name, t)
    if GAIN[name] == 1.0: return im
    a = np.asarray(im, F32) / 255
    a = 1 - (1 - np.clip(a * GAIN[name], 0, 1)) ** 1.08                    # brighten, soft shoulder
    return Image.fromarray(np.uint8(np.clip(a, 0, 1) * 255))

def _visual(name, t):
    if name == "wire": return wire_frame(t)
    if name == "ascii": return combo.ascii_frame(t, ())
    if name == "thermal": return combo.thermal_frame(t, labels=False)
    return pc.frame(t, text=False, tags=False)


# ---------- brief layout ----------
def text_w(f, s): return f.getlength(s)

def card(ov, x, y, rows, a, w=None):
    """rows: (kind, text[, extra]). kinds: title, meta, big, sub, hl, gap. Returns bottom y."""
    if a <= 0: return y
    spec = {"title": (sans(50), WHITE, 66), "meta": (mono(40), GREY, 54), "big": (mono(76, "SemiBold"), WHITE, 92),
            "sub": (sans(44, "Regular"), GREY, 58), "hl": (sans(44, "SemiBold"), INK, 62), "gap": (None, None, 18)}
    pad = 30
    h = pad * 2 + sum(spec[r[0]][2] for r in rows)
    if w is None:
        w = pad * 2 + max(text_w(spec[r[0]][0], r[1]) + (16 if r[0] == "hl" else 0) for r in rows if r[0] != "gap")
    assert x + w <= R.SAFE_X1 + 1 and y >= R.SAFE_Y0 and y + h <= R.SAFE_Y1, rows
    yo = 14 * (1 - oc(a))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((x, y + yo, x + w, y + h + yo), radius=12, fill=(14, 14, 16, 238), outline=(52, 52, 56, 255), width=2)
    cy = y + pad + yo
    for ri, r in enumerate(rows):
        kind, txt = r[0], r[1] if len(r) > 1 else ""
        f, col, lh = spec[kind]
        rp = oc(clamp(a * 1.8 - ri * 0.11))                                # rows reveal one after another
        if rp <= 0: cy += lh; continue
        if kind not in ("hl", "gap") and rp < 1:
            n = max(1, int(round(len(txt) * rp))); txt = txt[:n]
        if kind == "hl":
            k = r[2] if len(r) > 2 else 1.0                                  # highlighter sweeps in
            tw = text_w(f, txt) + 16
            d.rectangle((x + pad - 4, cy + 4, x + pad - 4 + tw * k, cy + lh - 6), fill=(*HL, 255))
            if k > 0.05: d.text((x + pad + 4, cy + 6), txt, font=f, fill=(*INK, 255))
        elif f is not None:
            d.text((x + pad, cy), txt, font=f, fill=(*col, 255))
        cy += lh
    if a < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    ov.alpha_composite(lay)
    return y + h

def leader(ov, x0, y0, p3, t, a, t0, col=WHITE, box=None):
    """Animated leader from a card edge to a 3D anchor, ending in a pulsing reticle."""
    k = oc(clamp((t - t0) / 0.5))
    if k <= 0 or a <= 0: return
    tx, ty, tz = pc.proj(np.array([p3], F32), pc.camera(t))
    if tz[0] <= 0.05: return
    tx, ty = float(tx[0]), float(ty[0])
    if box is not None and box[0] - 20 < tx < box[2] + 20:          # target below/above the card: leave from that edge
        x0, y0 = clamp(tx, box[0] + 30, box[2] - 30), (box[3] if ty > box[3] else box[1])
        mx = x0
    else:
        mx = x0 + (tx - x0) * 0.35
    pts = [(x0, y0), (mx, y0), (tx, ty)]
    L1 = abs(mx - x0); L2 = math.hypot(tx - mx, ty - y0); tot = L1 + L2 + 1e-6
    dl = k * tot
    d = ImageDraw.Draw(ov)
    al = int(220 * a)
    if dl <= L1: d.line((x0, y0, x0 + (mx - x0) * dl / max(L1, 1e-6), y0), fill=(*col, al), width=2); return
    f = (dl - L1) / max(L2, 1e-6)
    d.line(pts[:2], fill=(*col, al), width=2)
    d.line((mx, y0, mx + (tx - mx) * f, y0 + (ty - y0) * f), fill=(*col, al), width=2)
    if k >= 1:
        q = 12 + 5 * math.sin(t * 7)
        d.ellipse((tx - q, ty - q, tx + q, ty + q), outline=(*col, al), width=2)
        d.ellipse((tx - 4, ty - 4, tx + 4, ty + 4), fill=(*HL, al))

def gold_streams(ov, t, gx, gy):
    """On "16 grams": gold particles fly out of the foil wall into the cube grid; cube i lands at its tick."""
    t0 = B["grams"] - 0.1
    if not (t0 - 0.45 <= t < t0 + 16 * 0.07 + 0.3): return
    cam = pc.camera(t)
    d = ImageDraw.Draw(ov)
    rng = np.random.default_rng(21)
    src3 = np.column_stack([rng.uniform(-0.7, 1.1, 16 * 14), rng.uniform(0.3, 1.2, 16 * 14), np.full(16 * 14, -0.58)]).astype(F32)
    sx, sy, sz = pc.proj(src3, cam)
    for i in range(16):
        land = t0 + (i + 1) * 0.07
        cx, cy = gx + (i % 4) * 52 + 18, gy + (i // 4) * 52 + 29
        for j in range(14):
            q = i * 14 + j
            u = clamp((t - (land - 0.45) - j * 0.012) / 0.45)
            if u <= 0 or u >= 1 or sz[q] <= 0: continue
            e = u * u * (3 - 2 * u)
            bend = math.sin(math.pi * e) * (60 + 40 * math.sin(q))
            x = sx[q] + (cx - sx[q]) * e + bend
            y_ = sy[q] + (cy - sy[q]) * e - bend * 0.6
            r = 3 + 2 * (1 - e)
            d.ellipse((x - r * 2.5, y_ - r * 2.5, x + r * 2.5, y_ + r * 2.5), fill=(*HL, 40))
            d.ellipse((x - r, y_ - r, x + r, y_ + r), fill=(255, 226, 120, 230))
        if land <= t < land + 0.18:                                    # flash as the cube fills
            k = 1 - (t - land) / 0.18
            d.rectangle((cx - 30, cy - 30, cx + 30, cy + 30), outline=(255, 236, 150, int(220 * k)), width=3)

def count(t, t0, v, dur=0.7):
    return v * io(clamp((t - t0) / dur))

def cubes(ov, x, y, n, a):
    """Reference-style grid of small wireframe cubes (1 cube = 1 g)."""
    d = ImageDraw.Draw(ov)
    s, gap, dep = 36, 16, 11
    for i in range(16):
        if i >= n: break
        cx, cy = x + (i % 4) * (s + gap), y + (i // 4) * (s + gap)
        c = (*HL, int(255 * a)) if i == n - 1 and n < 16 else (226, 226, 222, int(255 * a))
        d.rectangle((cx, cy + dep, cx + s, cy + s + dep), outline=c, width=2)
        d.line((cx, cy + dep, cx + dep, cy, cx + s + dep, cy, cx + s, cy + dep), fill=c, width=2)
        d.line((cx + s + dep, cy, cx + s + dep, cy + s, cx + s, cy + s + dep), fill=c, width=2)

def captions(ov, t):
    """Centred sentence captions, split at punctuation, at most two lines."""
    segs, cur = [], []
    for w in WORDS:
        cur.append(w)
        if w["w"][-1] in ",.?": segs.append(cur); cur = []
    if cur: segs.append(cur)
    for i, sg in enumerate(segs):
        s0 = sg[0]["s"] - 0.12
        s1 = (segs[i + 1][0]["s"] - 0.12) if i + 1 < len(segs) else DUR
        s1 = min(s1, sg[-1]["e"] + 0.9)
        if not (s0 <= t < s1): continue
        a = min(prog(t, s0, 0.18), 1 - prog(t, s1 - 0.15, 0.15))
        f = sans(58, "Medium")
        words = [w["w"] for w in sg]; maxw = R.SAFE_X1 - 2 * X0
        if text_w(f, " ".join(words)) <= maxw:
            lines = [words]
        else:                                                         # two lines, balanced widths (no orphans)
            k = min(range(1, len(words)), key=lambda i: max(text_w(f, " ".join(words[:i])), text_w(f, " ".join(words[i:]))))
            lines = [words[:k], words[k:]]
        d = ImageDraw.Draw(ov)
        cx = (X0 + R.SAFE_X1 - X0) / 2 + 0
        for li, ln in enumerate(lines):
            txt = " ".join(ln)
            y = CAP_Y + li * 72 - (len(lines) - 1) * 36
            assert y >= R.SAFE_Y0 and y + 70 <= R.SAFE_Y1
            d.text((cx, y), txt, font=f, fill=(*WHITE, int(255 * a)), anchor="ma")

# ---------- user-supplied photos (kept in out/, not in git) ----------
PHOTOS = R.OUT / "photos"
_P = {}
def photo(name, crop):
    if name not in _P:
        f = PHOTOS / name
        _P[name] = Image.open(f).convert("RGB").crop(crop) if f.exists() else None
    return _P[name]

def photo_card(ov, name, crop, x, y, w, h, t, t0, t1, label):
    """Evidence photo: framed card, slow push-in, slide/fade in, label on a soft gradient."""
    im = photo(name, crop)
    if im is None or not (t0 <= t < t1 + 0.3): return
    a = min(prog(t, t0, 0.4), 1 - prog(t, t1 - 0.05, 0.3))
    if a <= 0: return
    z = 1.0 + 0.07 * clamp((t - t0) / max(0.1, t1 - t0))
    iw, ih = im.size; cw, ch = iw / z, ih / z
    box = ((iw - cw) / 2, (ih - ch) / 2, (iw + cw) / 2, (ih + ch) / 2)
    pic = im.resize((int(w), int(h)), Image.LANCZOS, box=box)
    arr = np.asarray(pic, F32)
    ks = clamp((t - t0 - 0.15) / 0.6)                                    # halftone -> photo scan
    if ks < 1:
        g = 12; small = np.asarray(pic.resize((int(w) // g, int(h) // g), Image.BILINEAR), F32)
        dots = Image.new("RGB", pic.size, (8, 8, 9)); dd = ImageDraw.Draw(dots)
        for j in range(small.shape[0]):
            for i in range(small.shape[1]):
                c = small[j, i]; r_ = (c.mean() / 255) ** 0.8 * g * 0.55
                cx, cy = i * g + g / 2, j * g + g / 2
                dd.ellipse((cx - r_, cy - r_, cx + r_, cy + r_), fill=tuple(int(v * 1.1) for v in c))
        da = np.asarray(dots, F32)
        line = ks * h
        yy_ = np.arange(int(h))[:, None, None]
        m = np.clip((line - yy_) / 14, 0, 1)
        arr = arr * m + da * (1 - m) + np.exp(-((yy_ - line) / 3.0) ** 2) * np.array([200, 235, 255], F32) * 0.9
    yy = np.linspace(0, 1, int(h))[:, None, None]
    arr = arr * (1 - 0.55 * np.clip((0.28 - yy) / 0.28, 0, 1)) * 0.95          # dark top edge for the label
    pic = Image.fromarray(np.uint8(arr)).convert("RGBA")
    mask = Image.new("L", pic.size, 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=12, fill=int(255 * a))
    yo = int(18 * (1 - oc(a)))
    ov.paste(pic, (int(x), int(y) + yo), mask)
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle((x, y + yo, x + w, y + h + yo), radius=12, outline=(70, 70, 74, int(255 * a)), width=2)
    d.text((x + 22, y + yo + 16), label, font=mono(38), fill=(*WHITE, int(235 * a)))


def brief(im, t, sec):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    _, start, no, title = sec
    y = 290
    if no == 1:
        f = sans(92, "SemiBold")
        d.text((X0, y), "Why is there", font=f, fill=(*WHITE, 255))
        gw = text_w(f, "gold ")
        k = io(prog(t, wstart("gold") - 0.1, 0.35))                   # highlighter sweeps in on "gold"
        if k > 0: d.rectangle((X0 - 6, y + 112 + 8, X0 - 6 + (text_w(f, "gold") + 12) * k, y + 112 + 104), fill=(*HL, 255))
        d.text((X0, y + 112), "gold", font=f, fill=(*(INK if k > 0.5 else HL), 255))
        d.text((X0 + gw, y + 112), "in this engine?", font=f, fill=(*WHITE, 255))
        d.text((X0, y + 248), "McLaren F1 · engine bay", font=mono(40), fill=(*GREY, 255))
    elif no == 2:
        a = prog(t, B["v12"] - 0.2, 0.35)
        hl = io(prog(t, B["heat"] - 0.3, 0.4))
        a = prog(t, B["v12"] - 0.2, 0.6)
        rows = [("title", "Engine · BMW V12"), ("meta", "mid-mounted · behind the cabin"), ("gap",),
                ("big", f"{count(t, B['v12'], 6.1):.1f} L"), ("sub", f"about {count(t, B['v12'] + 0.2, 618):.0f} hp")]
        if hl > 0: rows += [("gap",), ("hl", "huge heat", hl)]
        bot = card(ov, X0, y, rows, a, w=640)
        leader(ov, X0 + 640, y + 60, (-0.15, 0.64, 0.14), t, a, B["v12"] + 0.3, box=(X0, y, X0 + 640, bot))
    elif no == 3:
        a = prog(t, B["carbon"] - 0.25, 0.35)
        hl = io(prog(t, B["protect"] - 0.1, 0.4))
        rows = [("title", "Body · carbon fibre"), ("meta", "monocoque and panels"), ("gap",),
                ("sub", "needs insulating from")]
        rows += [("hl", "engine heat", hl)] if hl > 0 else [("sub", "engine heat")]
        a = prog(t, B["carbon"] - 0.25, 0.6)
        bot = card(ov, X0, y, rows, a, w=640)
        leader(ov, X0 + 640, y + 60, (0.35, 0.72, -0.58), t, a, B["carbon"] + 0.3)
        a2 = prog(t, B["gold"] - 0.2, 0.6)
        hl2 = io(prog(t, B["infrared"] - 0.05, 0.4))
        if a2 > 0:
            rows2 = [("title", "Gold"), ("sub", "reflects infrared well")] + ([("hl", "heat bounces back", hl2)] if hl2 > 0 else [])
            card(ov, X0 + 360, bot + 24, rows2, a2, w=480)
            leader(ov, X0 + 360, bot + 84, (-0.76, 0.62, -0.25), t, a2, B["gold"] + 0.3, HL)
    elif no == 4:
        a = prog(t, B["lined"] - 0.05, 0.6)
        n = int(clamp((t - B["grams"] + 0.1) / 0.07, 0, 16))
        rows = [("title", "Lining · gold foil"), ("meta", "source · Robb Report, SlashGear"), ("gap",),
                ("big", f"≈ {n} g" if n > 0 else "—"), ("sub", "1 cube = 1 g"), ("gap",), ("gap",)]
        bot = card(ov, X0, y, rows, a, w=R.SAFE_X1 - X0)
        if a > 0.5: cubes(ov, X0 + 520, y + 160, n, a)
        gold_streams(ov, t, X0 + 520, y + 160)
    else:
        a = prog(t, B["question"] - 0.1, 0.35)
        f = sans(76, "SemiBold")
        lines = ["Would you line", "your car with gold?"]
        lay_y = y
        for ln in lines:
            d.text((X0, lay_y), ln, font=f, fill=(*WHITE, int(255 * a))); lay_y += 96
        for j, (lab, x0) in enumerate((("Yes", X0), ("No", X0 + 420))):
            wi = [i for i, w in enumerate(WORDS) if w["w"].strip("?").lower() == lab.lower()][-1]
            nxt = WORDS[wi + 2]["s"] - 0.05 if wi + 2 < len(WORDS) else DUR       # "Yes" holds until "no"
            on = WORDS[wi]["s"] - 0.05 <= t < nxt
            kb = prog(t, B["question"] + 0.3 + 0.12 * j, 0.3)
            yb = lay_y + 40
            if on: d.rectangle((x0, yb, x0 + 380, yb + 130), fill=(*HL, int(255 * kb)))
            for k_ in range(0, 380, 14):                                    # dashed outline like the reference
                d.line((x0 + k_, yb, x0 + min(380, k_ + 8), yb), fill=(200, 200, 196, int(255 * kb)), width=2)
                d.line((x0 + k_, yb + 130, x0 + min(380, k_ + 8), yb + 130), fill=(200, 200, 196, int(255 * kb)), width=2)
            for k_ in range(0, 130, 14):
                d.line((x0, yb + k_, x0, yb + min(130, k_ + 8)), fill=(200, 200, 196, int(255 * kb)), width=2)
                d.line((x0 + 380, yb + k_, x0 + 380, yb + min(130, k_ + 8)), fill=(200, 200, 196, int(255 * kb)), width=2)
            d.text((x0 + 190, yb + 65), lab, font=sans(64, "SemiBold"), fill=((*INK, 255) if on else (*WHITE, int(255 * kb))), anchor="mm")
            assert x0 + 380 <= R.SAFE_X1 and yb + 130 <= R.SAFE_Y1
    if no == 1:                                                         # the real car, on "McLaren F1"
        photo_card(ov, "car.jpg", (0, 0, 588, 318), X0, 620, 640, 346, t, wstart("McLaren") - 0.1, SECTIONS[1][1], "McLaren F1")
    if no == 4:                                                         # the real gold-lined bay, on "lined the bay"
        photo_card(ov, "bay.jpg", (0, 200, 918, 700), X0, 688, 551, 300, t, B["lined"] + 0.25, B["question"] - 0.25,
                   "the real engine bay")
    captions(ov, t)
    d.text((40, 52), "Yub", font=sans(30, "ExtraBold"), fill=(*WHITE, 210))
    if R.PREVIEW:
        tf = mono(22, "Bold"); pw = text_w(tf, "PREVIEW")
        d.rectangle((W - 60 - pw - 16, 92, W - 60, 124), outline=(220, 80, 60, 220), width=2)
        d.text((W - 68, 108), "PREVIEW", font=tf, fill=(220, 80, 60, 220), anchor="rm")
    base = im.convert("RGBA")
    # darken behind the text column so cards and captions sit on near-black, like the reference
    sc = np.zeros((H, 1), F32)
    yy = np.arange(H)
    sc[:, 0] = 0.55 * np.clip(1 - np.abs(yy - 520) / 360, 0, 1) ** 0.6 + 0.6 * np.exp(-((yy - CAP_Y - 30) / 110) ** 2)
    arr = np.asarray(base, F32); arr[..., :3] *= (1 - np.clip(sc, 0, 0.8))[..., None]
    base = Image.fromarray(np.uint8(arr))
    base.alpha_composite(ov)
    return base.convert("RGB")


RING = {"wire": (200, 230, 255), "ascii": (235, 240, 220), "thermal": (255, 140, 60), "lidar": (255, 205, 90)}
_YY, _XX = np.mgrid[0:H, 0:W].astype(F32)
_GR = np.random.default_rng(3)

def punch(im, k):
    """Zoom kick: k in 0..1 (decaying)."""
    if k <= 0.002: return im
    z = 1 + 0.035 * k; cw, ch = W / z, H / z
    return im.resize((W, H), Image.BICUBIC, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))

def frame(t):
    t = clamp(t, 0, DUR - 1e-6)
    i = max(j for j, s in enumerate(SECTIONS) if t >= s[1])
    sec = SECTIONS[i]
    im = visual(sec[0], t)
    k = prog(t, sec[1], 0.6) if i > 0 else 1.0
    if k < 1:                                                       # radial ripple reveal from the engine
        prev = np.asarray(visual(SECTIONS[i - 1][0], t), F32)
        cur = np.asarray(punch(im, 1 - io(k)), F32)
        cx, cy, _ = pc.proj(np.array([[0.0, 0.5, 0.0]], F32), pc.camera(t))
        dist = np.hypot(_XX - cx[0], _YY - cy[0])
        r = io(k) * 2300
        m = np.clip((r - dist) / 40, 0, 1)[..., None]
        ring = np.exp(-((dist - r) / 10) ** 2)[..., None] * np.array(RING[sec[0]], F32) * 0.95
        ring += np.exp(-((dist - r) / 60) ** 2)[..., None] * np.array(RING[sec[0]], F32) * 0.25
        im = Image.fromarray(np.uint8(np.clip(cur * m + prev * (1 - m) + ring * (1 - k), 0, 255)))
    kick = max(math.exp(-(t - B[b]) * 5) if t >= B[b] else 0 for b in ("heat", "grams"))
    im = punch(im, kick)
    a = np.asarray(im, F32) * 0.92                                           # slightly muted under the brief
    out = np.asarray(brief(Image.fromarray(np.uint8(a)), t, sec), F32)
    # film finish: edge chromatic aberration, vignette, fine grain
    out[..., 0] = np.roll(out[..., 0], 1, axis=1) * 0.5 + out[..., 0] * 0.5
    out[..., 2] = np.roll(out[..., 2], -1, axis=1) * 0.5 + out[..., 2] * 0.5
    vig = 1 - 0.22 * np.clip(((_XX / W - 0.5) * 1.6) ** 2 + ((_YY / H - 0.5) * 1.3) ** 2, 0, 1)
    out = out * vig[..., None] + np.random.default_rng(int(t * FPS)).normal(0, 3.2, (H, W, 1)).astype(F32)
    return Image.fromarray(np.uint8(np.clip(out, 0, 255)))


# ---------- audio: voice + quiet bed ----------
def mix(voice, out, sfx=False):
    """Voice + sound design (engine bed, cues), SFX ducked under the voice. Also writes stems next to `out`."""
    import sound, wave
    sr = sound.SR
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(voice), "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    v = np.frombuffer(raw, np.int16).astype(F32) / 32768
    n = int(DUR * sr); v = np.pad(v, (0, max(0, n - len(v))))[:n]
    cards = [B["v12"] - 0.2, B["carbon"] - 0.25, B["gold"] - 0.2, B["lined"] - 0.05, B["question"] - 0.1]
    highlights = [wstart("gold") - 0.1, B["heat"] - 0.3, B["protect"] - 0.1, B["infrared"] - 0.05]
    fx = sound.sfx_track([(s[0], s[1]) for s in SECTIONS], cards, highlights, B["grams"] - 0.03) if sfx else np.zeros(n, F32)
    env = np.convolve(np.abs(v), np.ones(2400) / 2400, mode="same")
    duck = 1 - np.clip(env * 9, 0, 0.6)                                       # up to ~8 dB under speech
    fx = fx * np.convolve(duck, np.ones(4800) / 4800, mode="same")
    x = v + fx
    x = x / max(1.0, np.abs(x).max() / 0.95)
    def write(path, sig):
        with wave.open(str(path), "wb") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr); f.writeframes((np.clip(sig, -1, 1) * 32767).astype("<i2").tobytes())
    write(out, x)
    stem = Path(out).with_suffix("")
    write(str(stem) + "_voice.wav", v); write(str(stem) + "_sfx.wav", fx)


def _job(i): return np.asarray(frame(i / FPS)).tobytes()

def video(out, voice, a=0.0, b=None, sfx=False):
    from multiprocessing import Pool
    pc.data(); combo.ascii_setup(); R.layers(); ST.wire(); panel_grid()
    b = DUR if b is None else b
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True); wav = out.parent / (out.stem + "_mix.wav")
    mix(voice, wav, sfx)
    n0, n1 = int(round(a * FPS)), int(round(b * FPS))
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-ss", str(a), "-t", str((n1 - n0) / FPS), "-i", str(wav), "-c:v", "libx264", "-preset", "medium",
           "-crf", "17", "-maxrate", "20M", "-bufsize", "40M", "-profile:v", "high", "-level", "4.2", "-g", "60",
           "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-af", "loudnorm=I=-14:TP=-1:LRA=7", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
           "-shortest", "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for k, buf in enumerate(pool.imap(_job, range(n0, n1), chunksize=2)):
            p.stdin.write(buf)
            if k % 90 == 0: print(f"frame {n0 + k}/{n1}", flush=True)
    p.stdin.close()
    assert p.wait() == 0
    print(f"wrote {out} (+ {wav.name}, _voice / _sfx stems)")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "still":
        od = Path(sys.argv[2]); od.mkdir(parents=True, exist_ok=True)
        for s_ in sys.argv[3:]:
            frame(float(s_)).save(od / f"f_{s_}.png")
    elif cmd == "video":
        video(sys.argv[2], sys.argv[3], *(float(v) for v in sys.argv[4:6]))
