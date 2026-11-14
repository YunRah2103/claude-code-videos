"""Combined look: LiDAR -> ASCII -> thermal flow -> LiDAR -> ASCII, handing off on story beats
with a sweeping scan-line. ASCII here is its own renderer: the scene is ray-traced at sub-cell
resolution and every cell picks the printable character whose shape best matches it.

  python combo.py still OUTDIR T [T ...]
  python combo.py video OUT.mp4 [START END]
"""
import math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import pc
import render as R
import scene
import styles as ST
from render import B, FPS, W, H, clamp, prog, io, oc, heat_i, warm_r, foil_p

F32 = np.float32
END = 20.0
B.setdefault("reflect", B["lined"] + 0.7)
JB = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-"
def mono(size, w="ExtraBold"): return ImageFont.truetype(JB + w + ".ttf", int(size))

# ---------- section schedule ----------
SECTIONS = [("lidar", 0.0), ("ascii", B["reveal"] - 0.1), ("thermal", B["carbon"] - 0.15),
            ("lidar", B["lined"] - 0.2), ("ascii", B["question"] - 0.25)]
WIPE = 0.55

# LiDAR point-text for this cut (headline at the open, then the gold beats)
pc.LABELS = [
    ("headline", [(64, 238, "McLAREN F1 · ENGINE BAY", pc.JB, 58, pc.COPPER, ()),
                  (64, 330, "WHY IS THERE", pc.FD + "Inter-Black.otf", 104, pc.WHITE, ()),
                  (64, 442, "GOLD IN THIS", pc.FD + "Inter-Black.otf", 104, pc.WHITE, ("GOLD",)),
                  (64, 554, "ENGINE?", pc.FD + "Inter-Black.otf", 104, pc.WHITE, ())], None, "reveal"),
    ("reflected", [(64, 470, "REFLECTED", pc.JB, 76, pc.GOLDC, ())], "reflect", "question"),
    ("goldfoil", [(64, 600, "GOLD FOIL ≈ 16 g", pc.JB, 76, pc.GOLDC, ())], "grams", "question"),
]


# ---------- ASCII: shape-matched characters over a ray-traced G-buffer ----------
CW, CH = 12, 24
COLS, ROWS = W // CW, H // CH                       # 90 x 80
SX, SY = 4, 6                                       # sub-samples per cell
CHARS = list(" .`',:;-_~=+*^\"/\\|()<>[]{}!ilIjtfr7LTYVXo0O#%@&$")
PHOS = np.array([0.90, 0.92, 0.84], F32); HOT = np.array([1.0, 0.36, 0.14], F32)
GOLDA = np.array([1.0, 0.78, 0.28], F32); COP = np.array([0.95, 0.66, 0.42], F32)
ALB = {scene.FLOOR: 0.22, scene.CARBON: 0.40, scene.ALLOY: 0.80, scene.COPPER: 0.78, scene.CHROME: 0.95,
       scene.HEADER: 0.55, scene.RUBBER: 0.15, scene.RIM: 0.6, scene.FUEL: 0.5, scene.DARK: 0.45}

_A = {}
def ascii_setup():
    if not _A:
        f = mono(20, "Bold")
        bank = np.zeros((len(CHARS), CH, CW), F32)
        for i, c in enumerate(CHARS):
            im = Image.new("L", (CW, CH), 0)
            ImageDraw.Draw(im).text((CW / 2, CH / 2), c, font=f, fill=255, anchor="mm")
            bank[i] = np.asarray(im, F32) / 255
        pat = bank.reshape(len(CHARS), SY, CH // SY, SX, CW // SX).mean((2, 4)).reshape(len(CHARS), -1)
        pat = pat / pat.mean(1).max() * 0.85                    # densest glyph ~ bright flat surface
        _A.update(bank=bank, pat=pat, g2=(pat ** 2).sum(1), S=scene.build_scene())
    return _A

def gbuffer(cam):
    pos, f, r, u, th, _ = cam
    xs = (np.arange(COLS * SX) + 0.5) * (W / (COLS * SX)); ys = (np.arange(ROWS * SY) + 0.5) * (H / (ROWS * SY))
    X, Y = np.meshgrid(xs, ys)
    d = f + ((X - W / 2) / (H / 2) * th)[..., None] * r + ((H / 2 - Y) / (H / 2) * th)[..., None] * u
    d = (d / np.linalg.norm(d, axis=-1, keepdims=True)).reshape(-1, 3)
    o = np.broadcast_to(pos, d.shape)
    t_, n, m, p = pc.trace(o, d, ascii_setup()["S"])
    hit = np.isfinite(t_)
    P = o + d * np.where(hit, t_, 0)[:, None]
    n[(n * d).sum(1) > 0] *= -1
    return P, n, m, p, hit, d, np.where(hit, t_, 50.0)

def ascii_frame(t, titles=()):
    A = ascii_setup()
    cam = pc.camera(t)
    P, n, m, part, hit, d, depth = gbuffer(cam)
    alb = np.zeros(len(m), F32)
    for k, v in ALB.items(): alb[m == k] = v
    face = (m == scene.CARBON) & (np.abs(n[:, 1]) < 0.9)
    if face.any():
        uu, vv, _ = scene.wall_uv(P[face], n[face]); horiz, _ = scene.carbon_tex(uu, vv)
        alb[face] *= np.where(horiz, 1.15, 0.75)
    ndl = np.clip(n @ scene.KEY, 0, 1)
    rim = (1 - np.clip(-(n * d).sum(1), 0, 1)) ** 3
    L = alb * (0.16 + 0.84 * ndl) + 0.25 * rim * hit
    # story state: hot headers, warming carbon, gold foil
    hot = (m == scene.HEADER).astype(F32) * min(1.0, 0.7 + 0.3 * heat_i(t))
    dh = np.min([np.linalg.norm(P - h, axis=1) for h in scene.HITS], axis=0)
    warm = np.clip((warm_r(t) - dh) / 0.1, 0, 1) * face
    side = np.abs(n[:, 0]) > 0.7
    gold = np.clip((foil_p(t) - np.where(face, scene.wrap_order(P, side), 9)) / 0.012, 0, 1)
    warm *= 1 - gold
    hot = np.maximum(hot, warm)
    L = np.where(gold > 0, 0.55 + 0.45 * ndl, L)
    L = np.maximum(L, hot * 0.85)
    # silhouettes and creases become strokes
    shp = (ROWS * SY, COLS * SX)
    pg, dg = part.reshape(shp), depth.reshape(shp)
    e = np.zeros(shp, bool)
    e[1:] |= (pg[1:] != pg[:-1]) | (np.abs(dg[1:] - dg[:-1]) > 0.03 * dg[1:])
    e[:, 1:] |= (pg[:, 1:] != pg[:, :-1]) | (np.abs(dg[:, 1:] - dg[:, :-1]) > 0.03 * dg[:, 1:])
    Lg = np.where(e, np.maximum(L.reshape(shp), 0.8), L.reshape(shp))
    Lg = np.clip((Lg - 0.04) / 0.8, 0, 1) ** 0.85
    # shape matching: best glyph per cell
    pat = Lg.reshape(ROWS, SY, COLS, SX).transpose(0, 2, 1, 3).reshape(ROWS * COLS, -1)
    dist = (pat ** 2).sum(1)[:, None] - 2 * pat @ A["pat"].T + A["g2"][None]
    ch = dist.argmin(1).reshape(ROWS, COLS)
    cell = lambda a: a.reshape(shp).reshape(ROWS, SY, COLS, SX).mean((1, 3))
    hc, gc = cell(hot), cell(gold)
    cop = cell((m == scene.COPPER).astype(F32))
    lum = cell(Lg)
    col = PHOS[None, None] * np.ones((ROWS, COLS, 1), F32)
    col = col * (1 - cop[..., None] * 0.6) + COP * cop[..., None] * 0.6
    col = col * (1 - gc[..., None]) + GOLDA * gc[..., None]
    col = col * (1 - np.clip(hc * 1.4, 0, 1)[..., None]) + HOT * np.clip(hc * 1.4, 0, 1)[..., None]
    col *= (0.55 + 0.65 * np.clip(lum * 1.4, 0, 1))[..., None]
    # titles: clear a halo, then draw decoding terminal text on top
    rng = np.random.default_rng(int(t * FPS))
    live = []
    for items, k_in, k_out in titles:
        halo = np.zeros((ROWS, COLS), bool)
        for x, y, text, size, c in items:
            f = mono(size); x1 = x + f.getlength(text)
            assert x1 <= R.SAFE_X1 and y >= R.SAFE_Y0 and y + size * 1.2 <= R.SAFE_Y1, text
            r0, r1 = int((y - 8) // CH), int((y + size * 1.25) // CH) + 1
            c0, c1 = int((x - 12) // CW), int((x1 + 12) // CW) + 1
            halo[max(0, r0):r1, max(0, c0):c1] = True
        ch = np.where(halo & (1 - k_out > 0.5), 0, ch)
        live.append((items, k_in, k_out))
    g = A["bank"][ch] * 1.0
    img = (g[..., None] * col[:, :, None, None, :]).transpose(0, 2, 1, 3, 4).reshape(H, W, 3)
    sm = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255)).resize((W // 4, H // 4), Image.BILINEAR)
    img = img + np.asarray(sm.filter(ImageFilter.GaussianBlur(4)).resize((W, H), Image.BILINEAR), F32) / 255 * 0.6
    im = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255))
    d_ = ImageDraw.Draw(im)
    pool = "#@%&$/\\|<>*+=01ABCDEFGHJKLMNPRSTUVWXYZ"
    for items, k_in, k_out in live:
        n_tot = sum(len(it[2]) for it in items); order = np.random.default_rng(n_tot).permutation(n_tot) / n_tot * 0.97
        k = 0; last = None
        for x, y, text, size, c in items:
            f = mono(size); cx = x
            for chx in text:
                o = order[k]; k += 1
                if chx != " " and (k_out - 0.18) <= o < k_in + 0.18:
                    ok = o < k_in and o >= k_out
                    d_.text((cx, y), chx if ok else pool[rng.integers(len(pool))], font=f,
                            fill=tuple(int(255 * min(1, v * (1 if ok else 0.65))) for v in c))
                    last = (cx + f.getlength(chx), y, f)
                cx += f.getlength(chx)
        if last and k_in < 1 and int(t * 4) % 2 == 0:
            x_, y_, f = last; l, tp, rr, bb = f.getbbox("M", anchor="la")
            d_.rectangle((x_ + 4, y_ + tp, x_ + 4 + (rr - l), y_ + bb), fill=(235, 235, 225))
    return im

def ascii_titles(t):
    T = []
    def add(items, a0, a1=None):
        if t < a0 - 0.01 or (a1 is not None and t > a1 + 0.9): return
        T.append((items, prog(t, a0, 0.7), 0.0 if a1 is None else prog(t, a1 - 0.1, 0.8)))
    WH, CO, RD, GD = (0.93, 0.94, 0.9), (1.0, 0.62, 0.36), (1.0, 0.36, 0.2), (1.0, 0.78, 0.3)
    add([(64, 640, "V12 · 6.1 L", 80, CO)], B["v12"], B["question"] - 0.6)
    add([(64, 430, "INFRARED HEAT", 80, RD)], B["heat"], B["question"] - 0.6)
    if t >= B["question"] - 0.3:
        add([(64, 300, "WOULD YOU LINE", 88, WH), (64, 410, "YOUR CAR", 88, WH), (64, 520, "WITH GOLD?", 88, GD)], B["question"])
        for lab, x0, wkey in (("[ YES ]", 64, "yes"), ("[ NO ]", 520, "no")):
            wi = [w for w in R.WORDS if w["w"].strip("?").lower() == wkey][0]
            on = wi["s"] - 0.05 <= t < wi["e"] + 0.35
            add([(x0, 680, lab, 84, GD if on else WH)], B["question"] + 0.5)
    return T


# ---------- thermal flow with reflection off the foil ----------
def thermal_frame(t, labels=True):
    z = pc.data(); cam = pc.camera(t)
    if "dh" not in ST._DH:
        hp = np.stack(scene.HOT).astype(F32)
        ST._DH["dh"] = np.min(np.linalg.norm(z["P"][:, None, :] - hp[None], axis=2), axis=1)
    P = z["P"]; x, y, dd = pc.proj(P, cam)
    ok = (dd > 0.05) & (x > -2) & (x < W + 1) & (y > -2) & (y < H + 1)
    hi = heat_i(t)
    fm = np.clip((foil_p(t) - z["wrap"]) / 0.012, 0, 1)
    temp = 0.8 * np.exp(-ST._DH["dh"] / 0.28) * hi
    temp = temp + 0.75 * np.clip((warm_r(t) - z["dhit"]) / 0.18, 0, 1) * z["face"] * (1 - fm)
    temp = temp + 0.06 * np.sin(ST._DH["dh"] * 28 - t * 7)
    temp = np.where(z["mat"] == scene.HEADER, 1.0, temp) + 0.08
    temp = temp * (1 - fm) + 0.05 * fm                             # the foil stays cold: it reflects
    col = ST.turbo(temp)[ok] * (0.45 + 0.55 * z["inten"][ok])[:, None]
    acc = np.zeros((H, W, 3), F32); pc.splat(acc, x[ok], y[ok], col * 1.6)
    # streaklines: absorbed into bare carbon, bounced back where foil covers the landing point
    zz = pc.data(); n = 1100
    hs, hh, ph, ph2 = zz["hs"][:n], zz["hh"][:n], zz["hph"][:n], zz["hph2"][:n]
    src = np.stack(scene.HOT).astype(F32)[hs] + zz["hj0"][:n]
    hit = np.stack(scene.HITS).astype(F32)[hh] + zz["hj1"][:n]
    hw = np.array(R.layers()["hitwipe"], F32)[hh]
    cov = np.clip((foil_p(t) - hw) / 0.05, 0, 1)
    nrm = np.where((np.abs(np.stack(scene.HITS)[hh][:, 0] + 0.76) < 0.01)[:, None], np.array([1, 0, 0], F32), np.array([0, 0, 1], F32))
    dv = hit - src; dn = dv / np.linalg.norm(dv, axis=1, keepdims=True)
    rf = dn - 2 * (dn * nrm).sum(1, keepdims=True) * nrm
    outp = hit + rf * 0.45
    for lag, kw in ((0, 1), (.01, .8), (.02, .65), (.03, .5), (.04, .35), (.05, .2)):
        u = np.clip((t * 0.6 + ph) % 1 - lag, 0, 1)
        a1 = np.clip(u / 0.6, 0, 1); a2 = np.clip((u - 0.6) / 0.4, 0, 1)
        Pp = src + dv * a1[:, None] + (outp - hit) * (a2 * cov)[:, None]
        sd = np.cross(dv, np.array([0, 1, 0], F32)); sd /= np.linalg.norm(sd, axis=1, keepdims=True) + 1e-6
        Pp = Pp + sd * (0.035 * np.sin(np.pi * a1) * np.sin(2 * np.pi * (u * 2.5 + ph2)))[:, None]
        vis = np.where(u < 0.6, 1.0, cov)                              # absorbed streaks stop at the wall
        tc = np.where(u < 0.6, 1 - 0.6 * a1, 0.55 - 0.1 * a2)
        c_ = ST.turbo(tc) * (3.0 * kw * hi * vis)[:, None]
        c_ = np.where((u >= 0.6)[:, None], np.array([1.0, 0.8, 0.35], F32) * (3.0 * kw * hi * cov)[:, None], c_)
        hx, hy, hz = pc.proj(Pp, cam); v = hz > 0.05
        pc.splat(acc, hx[v], hy[v], c_[v])
    img = np.array([0.02, 0.02, 0.03], F32) + (1 - np.exp(-acc * 2.0))
    sm = Image.fromarray(np.uint8(np.clip(img - 0.4, 0, 1) * 255)).resize((W // 4, H // 4), Image.BILINEAR)
    img += np.asarray(sm.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR), F32) / 255 * 0.9
    im = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255)); d = ImageDraw.Draw(im, "RGBA")
    for j in range(300):                                               # colour scale, right margin (decoration)
        c = tuple(int(255 * v) for v in ST.turbo(1 - j / 300))
        d.line((W - 70, 520 + j * 3, W - 46, 520 + j * 3), fill=c, width=3)
    if not labels: return im
    ax_, ay_, _ = pc.proj(np.array([[0.35, 0.72, -0.58]], F32), cam)
    ST.label(d, "CARBON FIBRE", 64, 860, 66, (235, 240, 255), (ax_[0], ay_[0]), min(1, max(0, (t - B["carbon"]) / 0.3)))
    hx, hy, _ = pc.proj(np.array([[0.02, 0.92, -0.3]], F32), cam)
    ST.label(d, "INFRARED HEAT", 64, 430, 66, (255, 120, 80), (hx[0], hy[0]))
    if t >= B["gold"]:
        gx, gy, _ = pc.proj(np.array([[-0.76, 0.62, -0.25]], F32), cam)
        ST.label(d, "GOLD FOIL", 64, 640, 66, (255, 205, 100), (gx[0], gy[0]), min(1, (t - B["gold"]) / 0.3))
    return im


# ---------- assembly ----------
def style_at(name, t):
    if name == "lidar": return pc.frame(t, text=True, tags=False)
    if name == "ascii": return ascii_frame(t, ascii_titles(t))
    return thermal_frame(t)

def frame(t):
    t = clamp(t, 0, END - 1e-6)
    i = max(j for j, (_, s) in enumerate(SECTIONS) if t >= s)
    name, start = SECTIONS[i]
    k = prog(t, start, WIPE) if i > 0 else 1.0
    if k < 1:                                                        # scan-line hand-off, top to bottom
        prev = np.asarray(style_at(SECTIONS[i - 1][0], t), F32)
        cur = np.asarray(style_at(name, t), F32)
        yb = (H + 80) * io(k) - 40
        yy = np.arange(H)[:, None, None]
        m = np.clip((yb - yy) / 18, 0, 1)
        out = cur * m + prev * (1 - m)
        out += np.exp(-((yy - yb) / 5.0) ** 2) * np.array([255, 245, 225], F32) * 0.9
        out += np.exp(-((yy - yb) / 40.0) ** 2) * np.array([255, 180, 120], F32) * 0.25
        im = Image.fromarray(np.uint8(np.clip(out, 0, 255)))
    else:
        im = style_at(name, t)
    d = ImageDraw.Draw(im, "RGBA")
    d.text((40, 52), "Yub", font=ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf", 32), fill=(205, 205, 210, 230))
    tf = mono(24, "Bold"); pw = tf.getlength("PREVIEW")
    d.rectangle((W - 52 - pw, 50, W - 32, 86), outline=(255, 80, 60, 230), width=2)
    d.text((W - 42 - pw, 68), "PREVIEW", font=tf, fill=(255, 80, 60, 230), anchor="lm")
    return im


def _job(i): return np.asarray(frame(i / FPS)).tobytes()

def video(out, a=0.0, b=END):
    from multiprocessing import Pool
    pc.data(); ascii_setup(); R.layers()
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True); wav = out.with_suffix(".wav")
    R.audio(wav)
    n0, n1 = int(round(a * FPS)), int(round(b * FPS))
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-ss", str(a), "-t", str((n1 - n0) / FPS), "-i", str(wav), "-c:v", "libx264", "-preset", "medium",
           "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for k, buf in enumerate(pool.imap(_job, range(n0, n1), chunksize=2)):
            p.stdin.write(buf)
            if k % 90 == 0: print(f"frame {n0 + k}/{n1}", flush=True)
    p.stdin.close()
    assert p.wait() == 0
    wav.unlink(missing_ok=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "still":
        od = Path(sys.argv[2]); od.mkdir(parents=True, exist_ok=True)
        for s_ in sys.argv[3:]:
            frame(float(s_)).save(od / f"f_{s_}.png")
    elif cmd == "video":
        video(sys.argv[2], *(float(v) for v in sys.argv[3:5]))
