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
    if key not in _F:
        path = (f"/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-{w[4:]}.ttf" if w.startswith("Mono")
                else FD + f"Inter-{w}.otf")
        _F[key] = ImageFont.truetype(path, int(size))
    return _F[key]

CYAN = (70, 226, 255); PANEL = (8, 14, 20)
GOLD = (246, 196, 82); RED = (255, 64, 44); INK = (22, 23, 27); WHITE = (244, 244, 240)
SAFE_X1, SAFE_Y0, SAFE_Y1 = int(W * 0.85), int(H * 0.12), int(H * 0.62)

def rgba(c, a): return (*c[:3], int(255 * clamp(a)))

def chamfer(x0, y0, x1, y1, c):
    return [(x0 + c, y0), (x1, y0), (x1, y1 - c), (x1 - c, y1), (x0, y1), (x0, y0 + c)]

# ---------- cyber look: scan beams, thermal mode, grid, glitch ----------
ENGINE = [scene.P[n] for n in ("crankcase", "cyl banks", "cam covers", "intake trumpets", "exhaust headers", "gearbox", "coil packs")]
IRON = np.array([[0, 0, 0], [0.12, 0.02, 0.35], [0.55, 0.05, 0.55], [0.92, 0.25, 0.12], [1.0, 0.62, 0.05],
                 [1.0, 0.92, 0.45], [1.0, 1.0, 0.95]], np.float32)
_UV = (np.linspace(0, 1, H)[:, None] * 0.85 + np.linspace(0, 1, W)[None, :] * 0.15).astype(np.float32)

def iron(v):
    x = np.clip(v, 0, 1) * (len(IRON) - 1); i = np.minimum(x.astype(int), len(IRON) - 2); f = (x - i)[..., None]
    return IRON[i] * (1 - f) + IRON[i + 1] * f

def thermal_beams(t):
    """Scan-line positions (screen u) switching thermal view on at "heat" and off at "gold"."""
    return -0.1 + 1.2 * io(prog(t, B["heat"], 0.8)), -0.1 + 1.2 * io(prog(t, B["gold"] - 0.25, 0.8))

def idle_beam(t): return ((t * 4 / DUR + 0.38) % 1) * 1.25 - 0.12

GLITCH = ("reveal", "heat", "carbon", "gold", "question")
def glitch_amt(t): return max(1 - prog(t, B[b], 0.13) if t >= B[b] else 0 for b in GLITCH)

def glitch(a, t, k):
    rng = np.random.default_rng(int(t * FPS) + 7)
    out = a.copy()
    for _ in range(7):
        y0 = int(rng.integers(0, H - 80)); h = int(rng.integers(6, 70)); dx = int(rng.integers(-80, 80) * k)
        out[y0:y0 + h] = np.roll(a[y0:y0 + h], dx, axis=1)
    sh = int(10 * k)
    out[..., 0] = np.roll(out[..., 0], sh, axis=1); out[..., 2] = np.roll(out[..., 2], -sh, axis=1)
    return out

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
    f = font(PILL_SIZE * s, "MonoExtraBold")
    h = PILL_H * s; pad = 24 * s; r = 10 * s
    w = pad * 2 + r * 2 + 16 * s + f.getlength(text)
    x1, y1 = x + w, y + h
    edge = dot if dot in (RED, GOLD) else CYAN
    if target is not None and a > 0:                     # elbow leader + square reticle
        tx, ty = target
        right = tx > (x + x1) / 2
        sx, sy = (x1 if right else x), y + h / 2
        ex = sx + (36 if right else -36)
        k = oc(clamp(a * 1.4 - 0.2))
        pts = [(sx, sy), (ex, sy), (ex + (tx - ex) * k, sy + (ty - sy) * k)]
        d.line(pts, fill=rgba(edge, 0.85 * a), width=3, joint="curve")
        if k > 0.95:
            q = 13 + 4 * (0.5 + 0.5 * math.sin(t * LOOP * 8)); c = 7
            for ax, ay in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                cx_, cy_ = tx + ax * q, ty + ay * q
                d.line([(cx_ - ax * c, cy_), (cx_, cy_), (cx_, cy_ - ay * c)], fill=rgba(edge, a), width=3)
            d.rectangle((tx - 3, ty - 3, tx + 3, ty + 3), fill=rgba(WHITE, a))
    if hero > 0:
        glow.polygon(chamfer(x - 10, y - 10, x1 + 10, y1 + 10, 22 * s), fill=rgba(GOLD, 0.85 * hero * a))
    fill = tuple(int(v) for v in np.array(PANEL) * (1 - hero) + np.array((70, 52, 12)) * hero)
    d.polygon(chamfer(x, y, x1, y1, 18 * s), fill=rgba(fill, 0.86 * a), outline=rgba(edge, a), width=3)
    cy = y + h / 2
    d.rectangle((x + pad, cy - r, x + pad + 2 * r, cy + r), fill=rgba(edge, a))
    n = int(round(len(text) * clamp(a * 1.6 - 0.1)))          # typewriter reveal
    tx0 = x + pad + 2 * r + 16 * s
    d.text((tx0, cy), text[:n], font=f, fill=rgba(WHITE, a), anchor="lm")
    if n < len(text):
        cw = f.getlength(text[:n])
        d.rectangle((tx0 + cw + 2, cy - h * 0.28, tx0 + cw + 2 + 0.55 * PILL_SIZE * s, cy + h * 0.28), fill=rgba(edge, a))
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
        col = (255, 120 + int(60 * rng.random()), 50) if ember else CYAN
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
    lum0 = base @ np.array([0.3, 0.59, 0.11], np.float32)
    base = base * 0.55 + lum0[..., None] * np.array([0.74, 0.9, 1.08], np.float32) * 0.4   # cool steel grade
    part = np.asarray(layers()["part"].resize((W, H), Image.NEAREST, box=box))
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
    # thermal camera view, wiped in/out by scan beams
    bon, boff = thermal_beams(t)
    tmask = (np.clip((bon - _UV) / 0.02, 0, 1) * np.clip((_UV - boff) / 0.02, 0, 1))[..., None]
    if tmask.max() > 0:
        eng = np.isin(part, ENGINE)
        tv = (0.06 + 0.10 * lum0 + 0.24 * eng + 0.45 * e + 0.22 * (crop("heat", box) @ np.array([1, 0, 0], np.float32)) * hi
              + 0.38 * wm * (0.6 + 0.4 * wv) * (1 - fm[..., 0]) - 0.05 * fm[..., 0])
        img = img * (1 - tmask) + iron(tv) * 0.95 * tmask
    # holographic floor grid (masked to floor pixels)
    gi = Image.new("L", (W, H), 0); gd = ImageDraw.Draw(gi)
    for x in np.arange(-1.5, 1.8, 0.25):
        gd.line([to_screen(box, (x, 0.001, -0.58)), to_screen(box, (x, 0.001, 1.3))], fill=255, width=2)
    for z in np.arange(-0.5, 1.3, 0.25):
        gd.line([to_screen(box, (-1.6, 0.001, z)), to_screen(box, (1.8, 0.001, z))], fill=255, width=2)
    grid = np.asarray(gi, np.float32) / 255 * (part == scene.P["floor"])
    img += grid[..., None] * np.array(CYAN, np.float32) / 255 * (0.22 + 0.08 * math.sin(t * LOOP * 6))
    # wireframe edges: always faint, bright in the trail of the scan beams
    dpt = crop("depth", box, Image.BILINEAR)
    ed = np.zeros((H, W), np.float32)
    ed[1:] = np.maximum(ed[1:], (part[1:] != part[:-1]) | (np.abs(dpt[1:] - dpt[:-1]) > 0.06))
    ed[:, 1:] = np.maximum(ed[:, 1:], (part[:, 1:] != part[:, :-1]) | (np.abs(dpt[:, 1:] - dpt[:, :-1]) > 0.06))
    ed *= dpt < 30
    bi = idle_beam(t)
    trail = np.exp(-np.clip(bi - _UV, 0, None) / 0.07) * (_UV < bi)
    for b in (bon, boff):
        if -0.1 < b < 1.1: trail = np.maximum(trail, np.exp(-np.abs(b - _UV) / 0.06))
    estr = 0.10 + 0.85 * trail + 0.3 * tmask[..., 0]
    img += (ed * estr)[..., None] * np.array(CYAN, np.float32) / 255
    for b, k in ((bi, 0.35), (bon, 1.0), (boff, 1.0)):                  # the beams themselves
        if -0.1 < b < 1.1:
            img += (np.exp(-((b - _UV) / 0.004) ** 2) * k)[..., None] * np.array([0.5, 0.95, 1.1], np.float32)
            img += (np.exp(-((b - _UV) / 0.03) ** 2) * 0.12 * k)[..., None] * np.array(CYAN, np.float32) / 255
    img *= 1 - dim(t)
    # depth of field (focus follows the camera target)
    depth = dpt
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
    img *= (0.955 + 0.045 * ((np.arange(H) // 2) % 2))[:, None, None]       # scanlines
    im = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255))
    els = hud(im, t, box)
    a = np.asarray(im).copy()
    a[..., 0] = np.roll(a[..., 0], 2, axis=1); a[..., 2] = np.roll(a[..., 2], -2, axis=1)   # chromatic fringe
    gk = glitch_amt(t)
    im = Image.fromarray(glitch(a, t, gk) if gk > 0 else a)
    if info is not None:
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
        d.text((64, 238), "McLAREN F1 // ENGINE BAY", font=font(58, "MonoExtraBold"), fill=rgba(CYAN, ha))
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
        d.polygon(chamfer(x - 26, y - 16, x + wsum + 22, y + 92, 18), fill=rgba(PANEL, 0.84 * a), outline=rgba(CYAN, 0.55 * a), width=2)
        d.rectangle((x - 26, y - 16, x - 18, y + 92 - 18), fill=rgba(CYAN, a))
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
            col = GOLD if j == 0 else CYAN
            fill = (40, 32, 14) if j == 0 else PANEL
            if on:
                g.polygon(chamfer(x0 - 12, yy0 - 12, x0 + 418, yy0 + 192, 40), fill=rgba(col, 0.8 * a))
            d.polygon(chamfer(x0, yy0, x0 + 406, yy0 + 180, 32), fill=rgba(fill, 0.9 * a * k),
                      outline=rgba(col, a * k), width=4 + int(3 * pulse * on))
            d.text((x0 + 203, yy0 + 90), lab, font=font(84), fill=rgba(col if not on else WHITE, a * k), anchor="mm")
        els += ["poll question", "poll YES", "poll NO"]
    # HUD chrome: corner brackets, edge ruler, tiny status line (decoration only)
    for cx_, cy_, sx_, sy_ in ((26, 26, 1, 1), (W - 26, 26, -1, 1), (26, H - 26, 1, -1), (W - 26, H - 26, -1, -1)):
        d.line([(cx_, cy_ + 70 * sy_), (cx_, cy_), (cx_ + 70 * sx_, cy_)], fill=rgba(CYAN, 0.55), width=3)
    for y_ in range(300, 1640, 40):
        L_ = 20 if y_ % 200 == 100 else 9
        d.line([(W - 40 - L_, y_), (W - 40, y_)], fill=rgba(CYAN, 0.35), width=2)
    yb = 300 + 1340 * clamp(idle_beam(t))
    d.polygon([(W - 66, yb), (W - 84, yb - 9), (W - 84, yb + 9)], fill=rgba(CYAN, 0.8))
    bon, boff = thermal_beams(t)
    mode = "THERMAL" if bon > 0.5 and boff < 0.5 else "VISIBLE"
    blink = (int(t * 2) % 2 == 0)
    d.text((130, 56), ("● " if blink else "  ") + f"REC  MODE:{mode}", font=font(24, "MonoBold"), fill=rgba(CYAN, 0.75))
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
