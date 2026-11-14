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
        for k in ("toon", "toongold", "base", "gold", "heat"): _L[k] = Image.fromarray(z[k])
        for k in ("emis", "weave", "ink"): _L[k] = Image.fromarray(z[k])
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
    if key not in _F:
        path = (f"/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-{w[4:]}.ttf" if w.startswith("Mono")
                else FD + f"Inter-{w}.otf")
        _F[key] = ImageFont.truetype(path, int(size))
    return _F[key]

LIME = (204, 255, 26); PINK = (255, 46, 116); BLUE = (52, 97, 255); OFFW = (233, 230, 222)
GOLD = (246, 196, 82); RED = (255, 64, 44); INK = (14, 14, 16); WHITE = OFFW; HEATC = (255, 74, 40)
SAFE_X1, SAFE_Y0, SAFE_Y1 = int(W * 0.85), int(H * 0.12), int(H * 0.62)

def rgba(c, a): return (*c[:3], int(255 * clamp(a)))
def f3(c): return np.array(c, np.float32) / 255

def chamfer(x0, y0, x1, y1, c):
    return [(x0 + c, y0), (x1, y0), (x1, y1 - c), (x1 - c, y1), (x0, y1), (x0, y0 + c)]

# ---------- graphic look: thermal mode, scan beams, wipes ----------
ENGINE = [scene.P[n] for n in ("crankcase", "cyl banks", "cam covers", "intake trumpets", "exhaust headers", "gearbox", "coil packs")]
THERM = np.array([[0.04, 0.04, 0.08], [0.12, 0.16, 0.62], [0.55, 0.15, 0.85], [1.0, 0.18, 0.45],
                  [1.0, 0.5, 0.1], [0.85, 1.0, 0.15], [1.0, 1.0, 0.92]], np.float32)
_UV = (np.linspace(0, 1, H)[:, None] * 0.85 + np.linspace(0, 1, W)[None, :] * 0.15).astype(np.float32)

def therm(v):                       # posterised thermal palette (flat bands)
    return THERM[np.clip((v * (len(THERM) - 0.01)).astype(int), 0, len(THERM) - 1)]

def thermal_beams(t):
    """Scan-line positions (screen u) switching thermal view on at "heat" and off at "gold"."""
    return -0.1 + 1.2 * io(prog(t, B["heat"], 0.8)), -0.1 + 1.2 * io(prog(t, B["gold"] - 0.25, 0.8))

def idle_beam(t): return ((t * 4 / DUR + 0.38) % 1) * 1.25 - 0.12

WIPES = ("reveal", "carbon", "gold", "grams", "question")
def wipe_k(t):
    for b in WIPES:
        k = prog(t, B[b] - 0.14, 0.36)
        if 0 < k < 1: return k
    return None

def draw_wipe(im, k):
    """Slanted lime slab with an ink stripe crossing the frame (poster-style cut)."""
    d = ImageDraw.Draw(im)
    x = -700 + (W + 1100) * io(k)
    d.polygon([(x, 0), (x + 330, 0), (x + 330 - 260, H), (x - 260, H)], fill=LIME)
    d.polygon([(x - 70, 0), (x - 20, 0), (x - 280, H), (x - 330, H)], fill=INK)

def words_line(d, x, y, toks, size, t, a, hi_gold=(), spoken=None, col=INK, chip=LIME):
    """Tokens left to right. Spoken word sits on a lime chip; hi_gold words on an ink chip in gold."""
    f = font(size)
    for i, tok in enumerate(toks):
        w = f.getlength(tok)
        c = col
        if tok.strip("?.,").upper() in hi_gold:
            d.rectangle((x - 8, y + size * 0.08, x + w + 8, y + size * 1.08), fill=rgba(INK, a)); c = GOLD
        if spoken and spoken(i):
            d.rectangle((x - 8, y + size * 0.08, x + w + 8, y + size * 1.08), fill=rgba(chip, a)); c = INK
        d.text((x, y), tok, font=f, fill=rgba(c, a))
        x += f.getlength(tok + " ")


# ---------- overlay pieces ----------
PILLS = [  # text, tab colour, appear beat, leave beat, screen xy (top-left), 3D anchor
    ("V12 · 6.1 L", LIME, "v12", "gold", (64, 640), (-0.15, 0.64, 0.14)),
    ("INFRARED HEAT", HEATC, "heat", "question+-0.35", (64, 420), (0.02, 0.92, -0.3)),
    ("CARBON FIBRE", BLUE, "carbon", "question+-0.35", (330, 860), (0.35, 0.72, -0.58)),
    ("REFLECTED", GOLD, "lined+0.7", "question+-0.35", (420, 530), (-0.5, 0.92, -0.42)),
    ("GOLD FOIL ≈ 16 g", GOLD, "grams", "question+-0.35", (64, 640), (-0.76, 0.62, -0.25)),
]
PILL_SIZE, PILL_H = 58, 84

def beat(spec):
    name, _, off = spec.partition("+")
    return B[name] + (float(off) if off else 0.0)

def draw_label(ov, t, idx, text, tab, x, y, a, s, target, hero=0.0):
    """Numbered label block: coloured index tab, off-white body, ink outline + offset shadow."""
    f = font(PILL_SIZE * s, "MonoExtraBold"); fi = font(PILL_SIZE * s, "MonoExtraBold")
    h = PILL_H * s; tw = 92 * s; pad = 20 * s; sh = 8
    w = tw + pad + f.getlength(text) + pad * 1.2
    reveal = io(clamp(a * 1.5))
    d = ImageDraw.Draw(ov)
    if target is not None and reveal > 0.3:              # elbow leader: ink with off-white core
        tx, ty = target
        right = tx > x + w / 2
        sx, sy = (x + w if right else x), y + h / 2
        ex = sx + (40 if right else -40)
        k = oc(prog(reveal, 0.3, 0.7) if reveal < 1 else 1)
        pts = [(sx, sy), (ex, sy), (ex + (tx - ex) * k, sy + (ty - sy) * k)]
        d.line(pts, fill=rgba(INK, a), width=10, joint="curve")
        d.line(pts, fill=rgba(OFFW, a), width=4, joint="curve")
        if k > 0.95:
            q = 13 + 3 * math.sin(t * LOOP * 8)
            d.rectangle((tx - q, ty - q, tx + q, ty + q), fill=rgba(INK, a))
            d.rectangle((tx - q + 5, ty - q + 5, tx + q - 5, ty + q - 5), fill=rgba(tab, a))
    tile = Image.new("RGBA", (int(w) + sh + 2, int(h) + sh + 2), (0, 0, 0, 0)); g = ImageDraw.Draw(tile)
    g.rectangle((sh, sh, w + sh, h + sh), fill=INK)
    body = tuple(int(v) for v in np.array(OFFW) * (1 - hero) + np.array(GOLD) * hero)
    g.rectangle((0, 0, w, h), fill=body, outline=INK, width=3)
    g.rectangle((0, 0, tw, h), fill=tab, outline=INK, width=3)
    g.text((tw / 2, h / 2), f"{idx:02d}", font=fi, fill=INK, anchor="mm")
    n = int(round(len(text) * clamp(a * 1.6 - 0.2)))
    g.text((tw + pad, h / 2), text[:n], font=f, fill=INK, anchor="lm")
    if n < len(text):
        cw = f.getlength(text[:n])
        g.rectangle((tw + pad + cw + 3, h * 0.22, tw + pad + cw + 3 + 0.55 * PILL_SIZE * s, h * 0.78), fill=INK)
    cw = max(1, int(tile.width * reveal))
    tile = tile.crop((0, 0, cw, tile.height))
    if a < 1:
        tile.putalpha(tile.getchannel("A").point(lambda v: int(v * a)))
    ov.alpha_composite(tile, (int(x), int(y)))
    return x + w + sh

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

def particles(d, t):
    """Flat graphic debris: pink/lime squares and ink plus-marks drifting up."""
    rng = np.random.default_rng(4)
    for i in range(34):
        x0, y0 = rng.random() * W, rng.random() * H
        cyc = rng.integers(1, 3); ph = rng.random() * 6.28
        y = (y0 - H * cyc * t / DUR) % H
        x = x0 + 22 * math.sin(t * LOOP * rng.integers(2, 5) + ph)
        r = 3 + 4 * rng.random()
        kind = i % 3
        if kind == 0:
            d.rectangle((x - r, y - r, x + r, y + r), fill=rgba(PINK, 0.9))
        elif kind == 1:
            d.rectangle((x - r, y - r, x + r, y + r), fill=rgba(LIME, 0.9))
        else:
            d.line((x - 8, y, x + 8, y), fill=rgba(OFFW, 0.8), width=3); d.line((x, y - 8, x, y + 8), fill=rgba(OFFW, 0.8), width=3)


# ---------- frame ----------
def frame(t, info=None):
    t = clamp(t, 0, DUR - 1e-6)
    box, focus = cam(t)
    base, gold = crop("toon", box), crop("toongold", box)
    gold = np.clip(gold * np.array([1.0, 1.1, 1.3], np.float32), 0, 1)     # cleaner yellow-gold
    part = np.asarray(layers()["part"].resize((W, H), Image.NEAREST, box=box))
    wipe = crop("wipe", box, Image.BILINEAR)
    fp = foil_p(t)
    fm = np.clip((fp - wipe) / 0.006, 0, 1)[..., None]
    img = base * (1 - fm) + gold * fm
    edge = (np.abs(wipe - fp) < 0.008) & (wipe < 5) & (0 < fp < 1.07)
    img[edge] = f3((255, 248, 210))
    sweep = io(prog(t, B["grams"], 1.4)) * (1 - prog(t, B["question"], 0.3))
    if 0 < sweep < 1:
        diag = crop("diag", box, Image.BILINEAR)
        band = (np.abs(diag - (-1.0 + 2.2 * sweep)) < 0.025)[..., None] * (fm > 0.5)
        img = np.where(band, f3((255, 250, 225)), img)
    hi = heat_i(t)
    img += crop("heat", box) * (0.3 * hi) * np.array([1.0, 0.4, 0.6], np.float32)
    e = crop("emis", box) * hi
    for thr, c in ((0.15, (230, 30, 70)), (0.45, HEATC), (0.75, (255, 170, 60)), (0.95, (255, 245, 200))):
        img[e > thr] = f3(c)
    warm = crop("warm", box, Image.BILINEAR)
    wv = crop("weave", box)
    wm = np.clip((warm_r(t) - warm) / 0.10, 0, 1) * (0.8 + 0.2 * math.sin(t * LOOP * 9)) * (1 - fm[..., 0])
    for thr, c in ((0.05, (110, 20, 50)), (0.4, (220, 30, 80)), (0.75, HEATC)):
        sel = wm > thr
        img[sel] = f3(c) * (0.7 + 0.5 * wv[sel])[:, None]
    # thermal camera view, wiped in/out by scan beams (posterised bands)
    bon, boff = thermal_beams(t)
    tmask = (np.clip((bon - _UV) / 0.004, 0, 1) * np.clip((_UV - boff) / 0.004, 0, 1))[..., None]
    if tmask.max() > 0:
        eng = np.isin(part, ENGINE)
        lum0 = base @ np.array([0.3, 0.59, 0.11], np.float32)
        tv = (0.06 + 0.10 * lum0 + 0.24 * eng + 0.45 * e + 0.22 * (crop("heat", box) @ np.array([1, 0, 0], np.float32)) * hi
              + 0.38 * wm * (0.6 + 0.4 * wv) - 0.05 * fm[..., 0])
        img = img * (1 - tmask) + therm(tv) * tmask
    # technical floor grid (ink, masked to floor pixels)
    gi = Image.new("L", (W, H), 0); gd = ImageDraw.Draw(gi)
    for x in np.arange(-1.5, 1.8, 0.25):
        gd.line([to_screen(box, (x, 0.001, -0.58)), to_screen(box, (x, 0.001, 1.3))], fill=255, width=2)
    for z in np.arange(-0.5, 1.3, 0.25):
        gd.line([to_screen(box, (-1.6, 0.001, z)), to_screen(box, (1.8, 0.001, z))], fill=255, width=2)
    grid = np.asarray(gi, np.float32) / 255 * (part == scene.P["floor"]) * (1 - tmask[..., 0])
    img *= (1 - 0.22 * grid)[..., None]
    # ink outlines; lime where a scan beam just passed
    ink = crop("ink", box, Image.BILINEAR)[..., None]
    bi = idle_beam(t)
    trail = np.exp(-np.clip(bi - _UV, 0, None) / 0.06) * (_UV < bi)
    for b in (bon, boff):
        if -0.1 < b < 1.1: trail = np.maximum(trail, np.exp(-np.abs(b - _UV) / 0.05))
    inkc = f3(INK) * (1 - trail[..., None]) + f3(LIME) * trail[..., None]
    img = img * (1 - ink) + inkc * ink
    for b, wdt in ((bi, 0.0022), (bon, 0.0035), (boff, 0.0035)):    # beams: lime line, ink edges
        if -0.1 < b < 1.1:
            dd = np.abs(b - _UV)[..., None]
            img = np.where(dd < wdt, f3(LIME), np.where(dd < wdt + 0.0012, f3(INK), img))
    img *= 1 - dim(t)
    # depth of field (focus follows the camera target)
    depth = crop("depth", box, Image.BILINEAR)
    coc = np.clip(np.abs(depth - focus) / 1.4 - 0.1, 0, 1)[..., None]
    small = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255)).resize((W // 2, H // 2), Image.BILINEAR)
    bl = np.asarray(small.filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR), np.float32) / 255
    img = img * (1 - coc) + bl * coc
    # heat rays: flat strokes with ink outline
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    ra = 1.0 - 0.6 * dim(t) / 0.42
    hw = layers()["hitwipe"]
    n_ref = 0
    for si, hi_ in RAYS:
        src, hit = scene.HOT[si], scene.HITS[hi_]
        p0, p1 = to_screen(box, src), to_screen(box, hit)
        wave(d, p0, p1, t, INK, 9, ra); wave(d, p0, p1, t, HEATC, 5, ra)
        covered = clamp((fp - hw[hi_]) / 0.05)
        if covered > 0:
            n_ref += 1
            nrm = np.array([1.0, 0, 0]) if abs(hit[0] + 0.76) < 0.01 else np.array([0, 0, 1.0])
            p2 = to_screen(box, reflect(src, hit, nrm))
            wave(d, p1, p2, t, INK, 9, covered * ra, frac=covered)
            wave(d, p1, p2, t, GOLD, 5, covered * ra, frac=covered)
            fl = 1 - prog(t, B["gold"] + hw[hi_] * (B["lined"] + 1.1 - B["gold"]), 0.5)
            if 0 < fl < 1:
                r = 40 * (1 - fl) + 8
                d.ellipse((p1[0] - r, p1[1] - r, p1[0] + r, p1[1] + r), outline=rgba(GOLD, fl), width=6)
    particles(d, t)
    o = np.asarray(ov, np.float32) / 255
    img = img * (1 - o[..., 3:]) + o[..., :3] * o[..., 3:]
    # glow only from the hottest parts
    sm = Image.fromarray(np.uint8(np.clip(img - 0.85, 0, 1) * 255)).resize((W // 4, H // 4), Image.BILINEAR)
    img += np.asarray(sm.filter(ImageFilter.GaussianBlur(8)).resize((W, H), Image.BILINEAR), np.float32) / 255 * 0.6
    im = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255))
    k = wipe_k(t)
    if k is not None: draw_wipe(im, k)
    els = hud(im, t, box)
    if info is not None:
        ids, cnt = np.unique(part, return_counts=True)
        info["parts"] = [scene.PARTS[i] for i, c in zip(ids, cnt) if i and c > W * H * 0.002]
        info["overlays"] = els + (["heat rays"] if ra > 0 else []) + (["reflected rays"] if n_ref else []) + ["particles"]
    return im


def hud(im, t, box):
    """Graphic layout: slabs, numbered labels, poll blocks, frame furniture. Returns visible element names."""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    els = []
    # frame furniture (decoration only, outside the safe text area)
    off = (t / DUR * round(DUR * 0.8) * 56) % 56
    d.rectangle((W - 62, 340, W - 30, 1500), fill=rgba(INK, 0.95))
    for k_ in range(-2, 24):
        y_ = 340 + k_ * 56 + off
        d.polygon([(W - 58, y_), (W - 34, y_ - 24), (W - 34, y_ - 4), (W - 58, y_ + 20)], fill=rgba(LIME, 1))
    d.rectangle((W - 62, 300, W - 30, 340), fill=rgba(INK, 1)); d.rectangle((W - 62, 1500, W - 30, 1540), fill=rgba(INK, 1))
    rng = np.random.default_rng(11)
    d.rectangle((52, 1770, 330, 1846), fill=rgba(OFFW, 0.95), outline=rgba(INK, 1), width=3)
    x_ = 64
    while x_ < 318:
        bw = int(rng.integers(2, 8)); d.rectangle((x_, 1782, x_ + bw, 1834), fill=rgba(INK, 1)); x_ += bw + int(rng.integers(3, 8))
    for cx_, cy_ in ((W - 70, 1808), (W - 70, 120)):
        d.ellipse((cx_ - 18, cy_ - 18, cx_ + 18, cy_ + 18), outline=rgba(INK, 1), width=4)
        d.line((cx_ - 30, cy_, cx_ + 30, cy_), fill=rgba(INK, 1), width=4); d.line((cx_, cy_ - 30, cx_, cy_ + 30), fill=rgba(INK, 1), width=4)
        d.ellipse((cx_ - 18, cy_ - 18, cx_ + 18, cy_ + 18), outline=rgba(OFFW, 1), width=1)
    # headline: ink kicker strip + lime slab, slides out on "Not", back in for the loop
    kout = io(prog(t, B["reveal"] - 0.14, 0.3))
    kin = io(prog(t, (B["outro"] + B["end"]) / 2, (B["end"] - B["outro"]) / 2 - 0.08))
    xo = -W * (1 - kin) if t >= B["outro"] else -W * kout
    if xo > -W + 1:
        fk = font(58, "MonoExtraBold")
        d.rectangle((48 + xo, 228, 888 + xo, 300), fill=rgba(INK, 1))
        d.text((70 + xo, 264), "McLAREN F1 / ENGINE BAY", font=fk, fill=rgba(LIME, 1), anchor="lm")
        d.rectangle((58 + xo, 310, 898 + xo, 660), fill=rgba(INK, 1))                         # offset shadow
        d.polygon(chamfer(48 + xo, 300, 888 + xo, 650, 0)[:2] + [(888 + xo, 610), (848 + xo, 650), (48 + xo, 650)], fill=rgba(LIME, 1))
        for i, line in enumerate(("WHY IS THERE", "GOLD IN THIS", "ENGINE?")):
            words_line(d, 76 + xo, 312 + i * 110, line.split(), 100, t, 1.0, hi_gold=("GOLD",))
        bx = 700 + xo
        for j in range(16):
            bw = 3 + (j * 7) % 6
            d.rectangle((bx, 560, bx + bw, 620), fill=rgba(INK, 1)); bx += bw + 5
        for j in range(3):
            tx_ = 790 + xo + j * 30
            d.polygon([(tx_, 345), (tx_ + 22, 345), (tx_ + 11, 326)], fill=rgba(INK, 1))
        els += ["kicker", "headline"]
    # numbered callout labels
    for idx, (text, tab, a0, a1, xy, anchor) in enumerate(PILLS, 1):
        t0, t1 = beat(a0), beat(a1)
        if not (t0 <= t < t1 + 0.3): continue
        a = min(prog(t, t0, 0.35), 1 - prog(t, t1, 0.3))
        s, hero = 1.0, 0.0
        if text.startswith("GOLD FOIL"):
            hero = 1 - io(prog(t, t0 + 1.0, 0.6)); s = 1 + 0.15 * hero
        x1 = draw_label(ov, t, idx, text, tab, xy[0], xy[1], a, s, to_screen(box, np.array(anchor)), hero)
        assert x1 <= SAFE_X1 + 1 and SAFE_Y0 <= xy[1] and xy[1] + PILL_H * s <= SAFE_Y1 + 1, text
        els.append("label:" + text)
    d = ImageDraw.Draw(ov)
    # spoken captions: ink slab, current word on a lime chip
    cap = caption(t)
    if cap:
        toks, cur, a = cap
        f = font(64)
        wsum = sum(f.getlength(x + " ") for x in toks) - f.getlength(" ")
        x, y = 70, 1082
        d.rectangle((x - 22 + 8, y - 16 + 8, x + wsum + 24 + 8, y + 92 + 8), fill=rgba(LIME, a))
        d.rectangle((x - 22, y - 16, x + wsum + 24, y + 92), fill=rgba(INK, a))
        words_line(d, x, y, toks, 64, t, a, spoken=lambda i: i == cur, col=OFFW)
        els.append("caption")
    # poll
    a = min(prog(t, B["question"], 0.3), 1 - prog(t, B["outro"], (B["end"] - B["outro"]) / 2))
    if a > 0.01:
        qi = [i for i, w in enumerate(WORDS) if w["w"].lower() == "would"][0]
        k = io(prog(t, B["question"] - 0.1, 0.35)); xs = W * (1 - k)
        d.rectangle((58 + xs, 310, 898 + xs, 660), fill=rgba(INK, a))
        d.rectangle((48 + xs, 300, 888 + xs, 650), fill=rgba(OFFW, a), outline=rgba(INK, a), width=4)
        n = 0
        for li, line in enumerate(("WOULD YOU LINE", "YOUR CAR", "WITH GOLD?")):
            toks = line.split()
            spoken = (lambda base: (lambda i: WORDS[qi + base + i]["s"] <= t < WORDS[qi + base + i]["e"] + 0.1))(n)
            words_line(d, 76 + xs, 318 + li * 108, toks, 90, t, a, hi_gold=("GOLD",), spoken=spoken)
            n += len(toks)
        for j, (lab, x0) in enumerate((("YES", 64), ("NO", 512))):
            kb = ob(prog(t, B["question"] + 0.4 + 0.12 * j, 0.45))
            yy0 = 720 + 60 * (1 - kb)
            wi = WORDS[qi + 7 + 2 * j]
            on = wi["s"] - 0.05 <= t < wi["e"] + 0.35
            sh = 16 if on else 10
            d.rectangle((x0 + sh, yy0 + sh, x0 + 406 + sh - 16, yy0 + 180 + sh - 16), fill=rgba(PINK if on else INK, a * kb))
            d.rectangle((x0, yy0, x0 + 390, yy0 + 164), fill=rgba(LIME if j == 0 else OFFW, a * kb), outline=rgba(INK, a * kb), width=5)
            d.text((x0 + 195, yy0 + 82), lab, font=font(96), fill=rgba(INK, a * kb), anchor="mm")
        els += ["poll question", "poll YES", "poll NO"]
    # corner tags (tiny)
    d.rectangle((36, 40, 112, 82), fill=rgba(INK, 0.9)); d.text((74, 61), "Yub", font=font(30, "ExtraBold"), fill=rgba(LIME, 1), anchor="mm")
    if PREVIEW:
        tf = font(24, "MonoBold"); tw = tf.getlength("PREVIEW")
        d.rectangle((W - 52 - tw, 44, W - 32, 80), fill=rgba(PINK, 0.95))
        d.text((W - 42 - tw, 62), "PREVIEW", font=tf, fill=rgba(INK, 1), anchor="lm")
    base = im.convert("RGBA"); base.alpha_composite(ov)
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
