"""Gold engine bay: preview renderer. Every time comes from timing.json beats/words.

  python render.py still OUTDIR T [T ...]       # f_<T>.png stills
  python render.py video OUT.mp4 [START END]    # 1080x1920 30 fps, quiet placeholder tone
  python render.py elements T [T ...]           # element count per frame
"""
import json, math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "videos/new-car-trap/src"))
import scene  # noqa: E402

DUR = 21.54   # preview-tool hint only; the real length is timing.json "dur" (set below)
TM = json.load(open(HERE / "timing.json"))
DUR, FPS, B, WORDS = TM["dur"], TM["fps"], TM["beats"], TM["words"]
W, H = 1080, 1920
OUT = ROOT / "out/gold-engine-bay"
CACHE = OUT / "cache" / f"plate_{scene.scene_key()}.npz"
PREVIEW = True                       # phase 1 tag; phase 2 sets False

# ---------- easing ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, d): return clamp((t - a) / d) if d > 0 else float(t >= a)
def io(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def oc(x): return 1 - (1 - x) ** 3
def ob(x, k=1.7): return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2
def win(t, a, b, fi=0.25, fo=0.25): return min(prog(t, a, fi), 1 - prog(t, b - fo, fo))
LOOP = 2 * math.pi / DUR             # periodic motion completes whole cycles over DUR


# ---------- timeline states ----------
def heat_i(t):
    flick = 1 + 0.06 * math.sin(t * LOOP * 37) + 0.04 * math.sin(t * LOOP * 61 + 1)
    surge = 0.5 * math.sin(math.pi * prog(t, B["push"], 0.9))
    return (1.0 + surge + 0.35 * win(t, B["heat"], B["gold"], 0.5, 0.8)) * flick

def warm_r(t):            # radius of the warm patch on the carbon (0.12 m at the open)
    grow = 0.12 + 0.45 * io(prog(t, B["carbon"], B["protect"] + 1.0 - B["carbon"]))
    return grow * (1 - io(prog(t, B["outro"], B["end"] - B["outro"]))) + 0.12 * io(prog(t, B["outro"], B["end"] - B["outro"]))

def foil_p(t):            # wrap progress along the panels (wipe map 0..1)
    p = 1.08 * io(prog(t, B["gold"], B["lined"] + 1.1 - B["gold"]))
    return p * (1 - io(prog(t, B["outro"], B["end"] - B["outro"])))

def dim(t): return 0.42 * io(win(t, B["question"], B["end"], 0.5, B["end"] - B["outro"]))

CAMKEYS = [  # (beat, focus point, zoom, move seconds)
    ("open", (0.05, 0.62, -0.25), 1.10, 0.0),
    ("push", (-0.05, 0.52, -0.1), 1.40, 0.0),
    ("reveal", (-0.12, 0.55, -0.1), 1.00, 0.8),
    ("v12", (0.0, 0.48, 0.05), 1.62, 0.7),
    ("heat", (0.05, 0.66, -0.15), 1.42, 1.2),
    ("carbon", (0.0, 0.80, -0.58), 1.40, 0.8),
    ("protect", (0.0, 0.80, -0.58), 1.55, 1.2),
    ("gold", (-0.5, 0.62, -0.2), 1.20, 0.8),
    ("lined", (0.1, 0.66, -0.4), 1.15, 1.2),
    ("grams", (0.05, 0.62, -0.25), 1.02, 0.7),
    ("question", (0.05, 0.58, -0.2), 1.10, 3.5),
    ("outro", (0.05, 0.62, -0.25), 1.10, 0.0),
]

def cam(t):
    """(view box in plate px, focus depth)."""
    f, z = np.array(CAMKEYS[0][1]), CAMKEYS[0][2]
    for name, fp, zz, mv in CAMKEYS[1:]:
        if name == "outro":
            k = io(prog(t, B["outro"], B["end"] - B["outro"] - 0.05))
        elif name == "push":                                    # dolly-in from the very first frame
            k = prog(t, 0, B["reveal"] - 0.1)
        else:
            k = io(prog(t, B[name], mv))
        f = f + (np.array(fp) - f) * k
        z = z + (zz - z) * k
    z *= 1 + 0.012 * math.sin(t * LOOP)
    cx, cy, depth = scene.project(f)
    cx += 10 * math.sin(t * LOOP * 2); cy += 6 * math.sin(t * LOOP * 3 + 1)
    if B["protect"] <= t < B["protect"] + 0.5:                 # small heat-alarm shake
        a = 1 - prog(t, B["protect"], 0.5)
        cx += 6 * a * math.sin(t * 90); cy += 4 * a * math.cos(t * 77)
    vw, vh = scene.PW / z, scene.PH / z
    x0 = clamp(cx - vw / 2, 0, scene.PW - vw); y0 = clamp(cy - vh / 2, 0, scene.PH - vh)
    return (x0, y0, x0 + vw, y0 + vh), depth

def to_screen(box, p):
    x, y, _ = scene.project(p)
    s = W / (box[2] - box[0])
    return ((x - box[0]) * s, (y - box[1]) * s)


# ---------- layers ----------
_L = {}
def layers():
    if not _L:
        if not CACHE.exists():
            print("ray-tracing plate (once)...", flush=True)
            scene.render(CACHE)
        z = np.load(CACHE)
        for k in ("base", "gold", "heat"): _L[k] = Image.fromarray(z[k])
        for k in ("emis", "weave"): _L[k] = Image.fromarray(z[k])
        for k in ("warm", "wipe", "diag", "depth"): _L[k] = Image.fromarray(z[k].astype(np.float32), "F")
        _L["part"] = Image.fromarray(z["part"].astype(np.uint8))
        # where each ray lands on the wrap order (to know when the foil covers it)
        _L["hitwipe"] = [float(scene.wrap_order(h, abs(h[0] + 0.76) < 0.01)[0]) for h in scene.HITS]
    return _L

def crop(name, box, rs=Image.BICUBIC):
    a = np.asarray(layers()[name].resize((W, H), rs, box=box))
    return a.astype(np.float32) / 255.0 if a.dtype == np.uint8 else a.astype(np.float32)


# ---------- fonts / text ----------
FD = "/usr/share/fonts/opentype/inter/"
_F = {}
def font(size, w="Black"):
    key = (int(size), w)
    if key not in _F: _F[key] = ImageFont.truetype(FD + f"Inter-{w}.otf", int(size))
    return _F[key]

GOLD = (246, 196, 82); RED = (255, 64, 44); INK = (22, 23, 27); WHITE = (244, 244, 240)
SAFE_X1, SAFE_Y0, SAFE_Y1 = int(W * 0.85), int(H * 0.12), int(H * 0.62)

def rgba(c, a): return (*c[:3], int(255 * clamp(a)))

def words_line(d, x, y, toks, size, t, a, hi_gold=(), spoken=None):
    """Draw tokens left to right; gold if in hi_gold or currently spoken."""
    f = font(size)
    for i, tok in enumerate(toks):
        col = GOLD if (tok.strip("?.,").upper() in hi_gold or (spoken and spoken(i))) else WHITE
        d.text((x, y), tok, font=f, fill=rgba(col, a))
        x += f.getlength(tok + " ")


# ---------- overlay pieces ----------
PILLS = [  # text, dot colour, appear beat, leave beat, screen xy (top-left), 3D anchor
    ("V12 · 6.1 L", (205, 120, 70), "v12", "gold", (64, 640), (-0.15, 0.64, 0.14)),
    ("INFRARED HEAT", RED, "heat", "question+-0.35", (64, 420), (0.02, 0.92, -0.3)),
    ("CARBON FIBRE", (150, 150, 155), "carbon", "question+-0.35", (330, 860), (0.35, 0.72, -0.58)),
    ("REFLECTED", GOLD, "lined+0.7", "question+-0.35", (420, 530), (-0.5, 0.92, -0.42)),
    ("GOLD FOIL ≈ 16 g", GOLD, "grams", "question+-0.35", (64, 640), (-0.76, 0.62, -0.25)),
]
PILL_SIZE, PILL_H = 58, 84

def beat(spec):
    name, _, off = spec.partition("+")
    return B[name] + (float(off) if off else 0.0)

def draw_pill(d, glow, t, text, dot, x, y, a, s, target, hero=0.0):
    f = font(PILL_SIZE * s, "ExtraBold")
    h = PILL_H * s; pad = 26 * s; r = 11 * s
    w = pad * 2 + r * 2 + 16 * s + f.getlength(text)
    x1, y1 = x + w, y + h
    fill = tuple(int(v) for v in np.array(WHITE) * (1 - hero) + np.array(GOLD) * hero)
    if target is not None and a > 0:
        tx, ty = target
        sx = x1 if tx > x1 else (x if tx < x else (x + x1) / 2)
        sy = y + h / 2 if (tx > x1 or tx < x) else (y1 if ty > y1 else y)
        k = oc(clamp(a * 1.4 - 0.2))
        ex, ey = sx + (tx - sx) * k, sy + (ty - sy) * k
        d.line((sx, sy, ex, ey), fill=rgba(WHITE, 0.8 * a), width=3)
        if k > 0.95:
            pr = 9 + 5 * (0.5 + 0.5 * math.sin(t * LOOP * 8))
            d.ellipse((tx - pr, ty - pr, tx + pr, ty + pr), outline=rgba(WHITE, 0.9 * a), width=3)
            d.ellipse((tx - 5, ty - 5, tx + 5, ty + 5), fill=rgba(dot, a))
    if hero > 0:
        glow.rounded_rectangle((x - 8, y - 8, x1 + 8, y1 + 8), radius=h, fill=rgba(GOLD, 0.8 * hero * a))
    d.rounded_rectangle((x, y, x1, y1), radius=h / 2, fill=rgba(fill, 0.93 * a))
    cy = y + h / 2
    d.ellipse((x + pad, cy - r, x + pad + 2 * r, cy + r), fill=rgba(INK if hero > 0.5 else dot, a))
    d.text((x + pad + 2 * r + 16 * s, cy), text, font=f, fill=rgba(INK, a), anchor="lm")
    return x1

def wave(d, p0, p1, t, col, width, a, amp=11, lam=46, speed=1.0, frac=1.0):
    x0, y0 = p0; x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 4 or a <= 0: return
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    n = max(8, int(L * frac / 6))
    ph = t * LOOP * round(DUR * 1.6 * speed)
    pts = []
    for i in range(n + 1):
        s = frac * i / n
        env = math.sin(math.pi * clamp(s, 0, 1)) ** 0.6
        o = amp * env * math.sin(2 * math.pi * s * L / lam - ph)
        pts.append((x0 + ux * L * s - uy * o, y0 + uy * L * s + ux * o))
    d.line(pts, fill=rgba(col, a), width=width, joint="curve")

RAYS = [(0, 0), (1, 1), (3, 2), (4, 3), (2, 4), (0, 5), (5, 7), (1, 6)]   # HOT idx -> HITS idx

def reflect(src, hit, nrm, length=0.42):
    d = hit - src; d = d / np.linalg.norm(d)
    r = d - 2 * (d @ nrm) * nrm
    return hit + r * length

def particles(d, t, box):
    rng = np.random.default_rng(4)
    for i in range(46):
        x0, y0 = rng.random() * W, rng.random() * H
        cyc = rng.integers(1, 3); ph = rng.random() * 6.28
        y = (y0 - H * cyc * t / DUR) % H
        x = x0 + 26 * math.sin(t * LOOP * rng.integers(2, 5) + ph)
        ember = i < 22
        r = 2 + 3 * rng.random() if ember else 1.5 + 2 * rng.random()
        tw = 0.5 + 0.5 * math.sin(t * LOOP * rng.integers(5, 12) + ph)
        col = (255, 120 + int(60 * rng.random()), 50) if ember else (200, 200, 205)
        a = (0.35 + 0.5 * tw) * (0.9 if ember else 0.35)
        d.ellipse((x - r, y - r, x + r, y + r), fill=rgba(col, a))
    for i in range(5):                                          # out-of-focus foreground bokeh
        x = (rng.random() * W + 40 * math.sin(t * LOOP + i)) % W
        y = (rng.random() * H - H * t / DUR) % H
        r = 26 + 30 * rng.random()
        d.ellipse((x - r, y - r, x + r, y + r), fill=rgba((255, 150, 80), 0.07))


# ---------- frame ----------
def frame(t, info=None):
    t = clamp(t, 0, DUR - 1e-6)
    box, focus = cam(t)
    base, gold = crop("base", box), crop("gold", box)
    wipe = crop("wipe", box, Image.BILINEAR)
    fp = foil_p(t)
    fm = np.clip((fp - wipe) / 0.012, 0, 1)[..., None]
    img = base * (1 - fm) + gold * fm
    edge = np.exp(-((wipe - fp) / 0.010) ** 2) * (wipe < 5) * (0 < fp < 1.07)
    img += edge[..., None] * np.array([1.0, 0.78, 0.42]) * 0.9
    sweep = io(prog(t, B["grams"], 1.4)) * (1 - prog(t, B["question"], 0.3))
    if 0 < sweep < 1:
        diag = crop("diag", box, Image.BILINEAR)
        img += (np.exp(-((diag - (-1.0 + 2.2 * sweep)) / 0.03) ** 2)[..., None] * fm * np.array([1.0, 0.85, 0.55]) * 0.3)
    hi = heat_i(t)
    img += crop("heat", box) * (0.38 * hi)
    e = crop("emis", box) * hi
    img += 0.8 * (e[..., None] * np.array([0.95, 0.13, 0.03]) + (e ** 3)[..., None] * np.array([1.0, 0.55, 0.12]))
    warm = crop("warm", box, Image.BILINEAR)
    wv = crop("weave", box)
    wr = warm_r(t)
    wm = np.clip((wr - warm) / 0.10, 0, 1) * (0.75 + 0.25 * math.sin(t * LOOP * 9))
    img += (wm * (0.35 + 0.9 * wv))[..., None] * (1 - fm) * np.array([0.85, 0.12, 0.04]) * 0.5
    img *= 1 - dim(t)
    # depth of field (focus follows the camera target)
    depth = crop("depth", box, Image.BILINEAR)
    coc = np.clip(np.abs(depth - focus) / 1.1 - 0.08, 0, 1)[..., None]
    small = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255)).resize((W // 2, H // 2), Image.BILINEAR)
    bl = np.asarray(small.filter(ImageFilter.GaussianBlur(7)).resize((W, H), Image.BILINEAR), np.float32) / 255
    img = img * (1 - coc) + bl * coc
    # overlays: heat rays + their glow
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(gl)
    ra = 1.0 - 0.6 * dim(t) / 0.42
    hw = layers()["hitwipe"]
    n_ref = 0
    for si, hi_ in RAYS:
        src, hit = scene.HOT[si], scene.HITS[hi_]
        p0, p1 = to_screen(box, src), to_screen(box, hit)
        wave(g, p0, p1, t, RED, 16, 0.55 * ra); wave(d, p0, p1, t, (255, 90, 60), 5, 0.95 * ra)
        covered = clamp((fp - hw[hi_]) / 0.05)
        if covered > 0:
            n_ref += 1
            nrm = np.array([1.0, 0, 0]) if abs(hit[0] + 0.76) < 0.01 else np.array([0, 0, 1.0])
            p2 = to_screen(box, reflect(src, hit, nrm))
            wave(g, p1, p2, t, GOLD, 16, 0.5 * covered * ra, speed=1.0, frac=covered)
            wave(d, p1, p2, t, (255, 214, 120), 5, 0.95 * covered * ra, frac=covered)
            fl = 1 - prog(t, B["gold"] + (hw[hi_]) * (B["lined"] + 1.1 - B["gold"]), 0.5)
            if 0 < fl < 1:
                r = 30 * (1 - fl) + 10
                g.ellipse((p1[0] - r, p1[1] - r, p1[0] + r, p1[1] + r), fill=rgba(GOLD, fl))
    particles(d, t, box)
    glb = np.asarray(gl.filter(ImageFilter.GaussianBlur(9)), np.float32) / 255
    img += glb[..., :3] * glb[..., 3:] * 1.4
    o = np.asarray(ov, np.float32) / 255
    img = img * (1 - o[..., 3:]) + o[..., :3] * o[..., 3:]
    # bloom
    sm = Image.fromarray(np.uint8(np.clip(img - 0.7, 0, 1) * 255)).resize((W // 4, H // 4), Image.BILINEAR)
    b1 = np.asarray(sm.filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR), np.float32) / 255
    b2 = np.asarray(sm.filter(ImageFilter.GaussianBlur(16)).resize((W, H), Image.BILINEAR), np.float32) / 255
    img += b1 * 0.55 + b2 * 0.7
    yy = np.linspace(-1, 1, H)[:, None]; xx = np.linspace(-1, 1, W)[None, :]
    img *= (1 - 0.35 * np.clip(xx ** 2 * 0.6 + yy ** 2 * 0.5, 0, 1))[..., None]
    im = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255))
    els = hud(im, t, box)
    if info is not None:
        part = np.asarray(layers()["part"].resize((W, H), Image.NEAREST, box=box))
        ids, cnt = np.unique(part, return_counts=True)
        info["parts"] = [scene.PARTS[i] for i, c in zip(ids, cnt) if i and c > W * H * 0.002]
        info["overlays"] = els + (["heat rays"] if ra > 0 else []) + (["reflected rays"] if n_ref else []) + ["particles"]
    return im


def hud(im, t, box):
    """Text, pills, poll, tags. Returns the names of visible overlay elements."""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(gl)
    els = []
    # headline (cold open + loop back)
    ha = max(1 - prog(t, B["reveal"] - 0.25, 0.25), prog(t, (B["outro"] + B["end"]) / 2, (B["end"] - B["outro"]) / 2 - 0.08) if t >= B["outro"] else 0)
    if t < 0.0001 or ha > 0:
        ha = 1.0 if t < B["reveal"] - 0.25 else ha
        sc = Image.new("L", (W, H), 0)
        ImageDraw.Draw(sc).rectangle((0, 180, W, 700), fill=int(150 * ha))
        im.paste(Image.new("RGB", (W, H), (8, 8, 10)), mask=sc.filter(ImageFilter.GaussianBlur(70)))
        d.text((64, 238), "McLAREN F1 · ENGINE BAY", font=font(58, "SemiBold"), fill=rgba((215, 160, 110), ha))
        for i, line in enumerate(("WHY IS THERE", "GOLD IN THIS", "ENGINE?")):
            words_line(d, 64, 318 + i * 112, line.split(), 104, t, ha, hi_gold=("GOLD",))
        els += ["kicker", "headline"]
    # callout pills
    for text, dot, a0, a1, xy, anchor in PILLS:
        t0, t1 = beat(a0), beat(a1)
        if not (t0 <= t < t1 + 0.3): continue
        a = min(prog(t, t0, 0.35), 1 - prog(t, t1, 0.3))
        s = 0.55 + 0.45 * ob(prog(t, t0, 0.4))
        hero = 0.0
        if text.startswith("GOLD FOIL"):
            hero = 1 - io(prog(t, t0 + 1.0, 0.6))
            s *= 1 + 0.18 * hero
        x1 = draw_pill(d, g, t, text, dot, xy[0], xy[1], a, s, to_screen(box, np.array(anchor)), hero)
        assert x1 <= SAFE_X1 + 1 and SAFE_Y0 <= xy[1] and xy[1] + PILL_H * s <= SAFE_Y1 + 1, text
        els.append("pill:" + text)
    # spoken captions (sentences 2-4; the headline and poll carry the others)
    cap = caption(t)
    if cap:
        toks, cur, a = cap
        f = font(64)
        wsum = sum(f.getlength(x + " ") for x in toks) - f.getlength(" ")
        x, y = 64, 1082
        d.rounded_rectangle((x - 22, y - 16, x + wsum + 22, y + 92), radius=18, fill=rgba((12, 12, 14), 0.78 * a), outline=rgba(GOLD, 0.9 * a), width=3)
        words_line(d, x, y, toks, 64, t, a, spoken=lambda i: i == cur)
        els.append("caption")
    # poll
    a = min(prog(t, B["question"], 0.3), 1 - prog(t, B["outro"], (B["end"] - B["outro"]) / 2))
    if a > 0.01:
        qi = [i for i, w in enumerate(WORDS) if w["w"].lower() == "would"][0]
        lines = ("WOULD YOU LINE", "YOUR CAR", "WITH GOLD?")
        n = 0
        for li, line in enumerate(lines):
            toks = line.split()
            k = oc(prog(t, B["question"] + 0.08 * li, 0.35))
            spoken = (lambda base: (lambda i: WORDS[qi + base + i]["s"] <= t < WORDS[qi + base + i]["e"] + 0.1))(n)
            words_line(d, 64, 330 + li * 112 + 30 * (1 - k), toks, 104, t, a * k, hi_gold=("GOLD?",), spoken=spoken)
            n += len(toks)
        for j, (lab, x0) in enumerate((("YES", 64), ("NO", 512))):
            k = ob(prog(t, B["question"] + 0.5 + 0.12 * j, 0.45))
            yy0 = 720 + 40 * (1 - k)
            wi = WORDS[qi + 7 + 2 * j]
            on = wi["s"] - 0.05 <= t < wi["e"] + 0.35
            pulse = 0.5 + 0.5 * math.sin(t * LOOP * 10)
            col = GOLD if j == 0 else (190, 190, 196)
            fill = (40, 32, 14) if j == 0 else (30, 30, 34)
            if on:
                g.rounded_rectangle((x0 - 10, yy0 - 10, x0 + 416, yy0 + 190), radius=44, fill=rgba(col, 0.8 * a))
            d.rounded_rectangle((x0, yy0, x0 + 406, yy0 + 180), radius=36, fill=rgba(fill, 0.92 * a * k),
                                outline=rgba(col, a * k), width=5 + int(3 * pulse * on))
            d.text((x0 + 203, yy0 + 90), lab, font=font(84), fill=rgba(col if not on else WHITE, a * k), anchor="mm")
        els += ["poll question", "poll YES", "poll NO"]
    # corner tags (tiny, outside the safe text area)
    d.text((40, 52), "Yub", font=font(34, "ExtraBold"), fill=rgba(WHITE, 0.75))
    if PREVIEW:
        tf = font(24, "Bold"); tw = tf.getlength("PREVIEW")
        d.rounded_rectangle((W - 52 - tw, 50, W - 32, 86), radius=8, outline=rgba(RED, 0.85), width=2)
        d.text((W - 42 - tw, 68), "PREVIEW", font=tf, fill=rgba(RED, 0.85), anchor="lm")
    glb = gl.filter(ImageFilter.GaussianBlur(14))
    base = im.convert("RGBA")
    base.alpha_composite(glb); base.alpha_composite(ov)
    im.paste(base.convert("RGB"))
    return els + ["tag Yub"] + (["tag PREVIEW"] if PREVIEW else [])


def caption(t):
    """(tokens, index of the current word, alpha) for 1-3 word chunks, or None."""
    i0 = next(i for i, w in enumerate(WORDS) if w["w"] == "Not")
    i1 = next(i for i, w in enumerate(WORDS) if w["w"] == "Would")
    chunks, cur = [], []
    for i in range(i0, i1):
        cur.append(i)
        tok = WORDS[i]["w"]
        if len(cur) == 3 or tok[-1] in ".,?" or sum(len(WORDS[j]["w"]) + 1 for j in cur) > 15:
            chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    for c in chunks:
        s, e = WORDS[c[0]]["s"], WORDS[c[-1]]["e"]
        if s - 0.05 <= t < e + 0.12:
            k = next((j for j, i in enumerate(c) if WORDS[i]["s"] <= t < WORDS[i]["e"] + 0.05), -1)
            return [WORDS[i]["w"] for i in c], k, 1.0
    return None


# ---------- audio (quiet placeholder) ----------
def audio(path):
    import sfx
    sr = sfx.SR; n = int(DUR * sr); tt = np.arange(n) / sr
    x = 0.02 * np.sin(2 * np.pi * 55 * tt) + 0.012 * np.sin(2 * np.pi * 110.5 * tt)
    x *= 0.8 + 0.2 * np.sin(2 * np.pi * tt / DUR)
    for b in ("reveal", "v12", "carbon", "gold", "lined", "grams", "question", "poll"):
        s = sfx.pop() if b not in ("gold", "lined") else sfx.sparkle()
        i = int(B[b] * sr); s = s[: n - i]
        x[i:i + len(s)] += 0.06 * s / max(1e-6, np.abs(s).max())
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    import wave as wv
    with wv.open(str(path), "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr); f.writeframes(pcm.tobytes())


def _job(i): return np.asarray(frame(i / FPS)).tobytes()

def video(out, a=0.0, b=None):
    from multiprocessing import Pool
    layers()
    b = DUR if b is None else b
    out = Path(out); wav = out.with_suffix(".wav")
    audio(wav)
    n0, n1 = int(round(a * FPS)), int(round(b * FPS))
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-ss", str(a), "-t", str((n1 - n0) / FPS), "-i", str(wav), "-c:v", "libx264", "-preset", "medium",
           "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for k, buf in enumerate(pool.imap(_job, range(n0, n1), chunksize=4)):
            p.stdin.write(buf)
            if k % 60 == 0: print(f"frame {n0 + k}/{n1}", flush=True)
    p.stdin.close()
    assert p.wait() == 0
    print(f"wrote {out}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "still":
        od = Path(sys.argv[2]); od.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[3:]:
            frame(float(s)).save(od / f"f_{s}.png")
    elif cmd == "video":
        video(sys.argv[2], *(float(x) for x in sys.argv[3:5]))
    elif cmd == "elements":
        for s in sys.argv[2:]:
            info = {}; frame(float(s), info)
            print(f"t={s}: {len(info['parts'])} 3D parts + {len(info['overlays'])} overlays = "
                  f"{len(info['parts']) + len(info['overlays'])} | {', '.join(info['parts'])} | {', '.join(info['overlays'])}")
