"""Gold engine bay, LiDAR point-cloud style. Same timing.json beats and scene geometry.

The bay is sampled by three virtual LiDAR scanners (spherical ray grids, so points fall on
scan rings), cached once; every frame is a true 3D camera render: bilinear point splats,
coarse z-buffer ghosting of hidden points, depth of field and bloom. Text is made of points.

  python pc.py still OUTDIR T [T ...]
  python pc.py video OUT.mp4 [START END]
"""
import math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import render as R
import scene
from render import B, FPS, W, H, clamp, prog, io, oc, heat_i, warm_r, foil_p

CACHE = R.OUT / "cache" / f"pc5_{scene.scene_key()}.npz"
F32 = np.float32
BG = np.array([0.018, 0.019, 0.022], F32)

# ---------- sampling (once) ----------
SCANNERS = [((0.1, 2.6, 3.1), 1900, 760)]

def trace(o, d, S):
    t_ = np.full(len(d), np.inf); n_ = np.zeros((len(d), 3)); m_ = np.zeros(len(d), np.int8); p_ = np.zeros(len(d), np.int8)
    for s in S:
        t, nn, _ = s.hit(o, d)
        w = t < t_
        t_[w] = t[w]; n_[w] = nn[w]; m_[w] = s.mat; p_[w] = s.part
    return t_, n_, m_, p_

def sample():
    if CACHE.exists():
        return dict(np.load(CACHE))
    S = scene.build_scene()
    out = {k: [] for k in ("P", "N", "mat", "part", "inten")}
    target = np.array([0.0, 0.5, -0.15])
    for pos, na, ne in SCANNERS:
        pos = np.array(pos, float)
        f = scene.nrm(target - pos); r = scene.nrm(np.cross(f, [0, 1, 0])); u = np.cross(r, f)
        az = np.radians(np.linspace(-58, 58, na)); el = np.radians(np.linspace(-52, 42, ne))
        A, E = np.meshgrid(az, el)
        d = (np.cos(E)[..., None] * (np.cos(A)[..., None] * f + np.sin(A)[..., None] * r) + np.sin(E)[..., None] * u).reshape(-1, 3)
        for c in range(0, len(d), 200000):
            dd = d[c:c + 200000]; o = np.broadcast_to(pos, dd.shape)
            t, n, m, p = trace(o, dd, S)
            ok = np.isfinite(t)
            P = o[ok] + dd[ok] * t[ok, None]; n = n[ok]
            n[(n * dd[ok]).sum(1) > 0] *= -1
            out["P"].append(P.astype(F32)); out["N"].append(n.astype(F32)); out["mat"].append(m[ok]); out["part"].append(p[ok])
            out["inten"].append(np.abs((n * dd[ok]).sum(1)).astype(F32))
    z = {k: np.concatenate(v) for k, v in out.items()}
    face = (z["mat"] == scene.CARBON) & (np.abs(z["N"][:, 1]) < 0.9)
    u, v, _ = scene.wall_uv(z["P"].astype(float), z["N"].astype(float))
    horiz, cross = scene.carbon_tex(u, v)
    z["weave"] = np.where(face, np.where(horiz, 1.0, 0.45) * (0.6 + 0.4 * np.sin(cross * np.pi)), 1.0).astype(F32)
    z["face"] = face
    z["dhit"] = np.min([np.linalg.norm(z["P"] - h.astype(F32), axis=1) for h in scene.HITS], axis=0).astype(F32)
    side = np.abs(z["N"][:, 0]) > 0.7
    z["wrap"] = np.where(face, scene.wrap_order(z["P"].astype(float), side), 9).astype(F32)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE, **z)
    return z

COL = {scene.FLOOR: (0.16, 0.17, 0.19), scene.CARBON: (0.62, 0.66, 0.74), scene.ALLOY: (0.80, 0.82, 0.86),
       scene.COPPER: (1.0, 0.56, 0.30), scene.CHROME: (0.95, 0.96, 1.0), scene.HEADER: (1.0, 0.32, 0.12),
       scene.RUBBER: (0.22, 0.22, 0.24), scene.RIM: (0.62, 0.63, 0.66), scene.FUEL: (0.55, 0.60, 0.70),
       scene.DARK: (0.42, 0.42, 0.45)}

_Z = {}
def data():
    if not _Z:
        z = sample()
        col = np.zeros((len(z["mat"]), 3), F32)
        for m, c in COL.items(): col[z["mat"] == m] = c
        cut = (z["mat"] == scene.CARBON) & ~z["face"]
        col[cut] = (0.95, 0.6, 0.35)
        z["col"] = col * (0.35 + 0.65 * z["inten"])[:, None] * z["weave"][:, None]
        _Z.update(z)
        rng = np.random.default_rng(3)                          # heat particles
        n = 1100
        _Z["hs"] = rng.integers(0, len(scene.HOT), n); _Z["hh"] = rng.integers(0, len(scene.HITS), n)
        _Z["hph"] = rng.random(n).astype(F32); _Z["hph2"] = rng.random(n).astype(F32)
        _Z["hj0"] = (rng.normal(size=(n, 3)) * 0.035).astype(F32); _Z["hj1"] = (rng.normal(size=(n, 3)) * 0.06).astype(F32)
        _Z["eng"] = np.nonzero(np.isin(z["part"], [scene.P[k] for k in ("cam covers", "cyl banks", "intake trumpets", "exhaust headers")]))[0]
    return _Z


# ---------- camera ----------
CAMKEYS = [  # beat, azimuth deg, radius, height, look-at, fov, move seconds
    ("open", 34, 3.3, 1.95, (0.0, 0.60, -0.12), 44, 0),
    ("push", 20, 2.55, 1.6, (0.0, 0.58, -0.1), 44, 2.4),
    ("reveal", -30, 3.7, 2.5, (-0.1, 0.5, -0.1), 46, 1.0),
    ("v12", -14, 2.35, 1.6, (0.0, 0.55, 0.0), 44, 0.8),
    ("heat", 8, 2.5, 1.35, (0.0, 0.75, -0.3), 46, 0.8),
]

def camera(t):
    az, r, h, look, fov = CAMKEYS[0][1], CAMKEYS[0][2], CAMKEYS[0][3], np.array(CAMKEYS[0][4]), CAMKEYS[0][5]
    for name, a2, r2, h2, l2, f2, mv in CAMKEYS[1:]:
        k = io(prog(t, B[name], mv))
        az += (a2 - az) * k; r += (r2 - r) * k; h += (h2 - h) * k; look = look + (np.array(l2) - look) * k; fov += (f2 - fov) * k
    az += 2.2 * t                                                    # never fully still
    pos = look + np.array([r * math.sin(math.radians(az)), h - look[1], r * math.cos(math.radians(az))])
    f = scene.nrm(look - pos); rr = scene.nrm(np.cross(f, [0, 1, 0])); u = np.cross(rr, f)
    return pos, f, rr, u, math.tan(math.radians(fov) / 2), float(np.linalg.norm(look - pos))

def proj(P, cam):
    pos, f, r, u, th, _ = cam
    v = P - pos.astype(F32)
    z = v @ f.astype(F32)
    x = (v @ r.astype(F32)) / (z * th) * (H / 2) + W / 2
    y = H / 2 - (v @ u.astype(F32)) / (z * th) * (H / 2)
    return x, y, z


# ---------- splatting ----------
def splat(acc, x, y, w):
    """Bilinear additive splat of N points with N x 3 weights into acc (H, W, 3)."""
    x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64); fx = (x - x0).astype(F32); fy = (y - y0).astype(F32)
    flat = acc.reshape(-1, 3)
    for dx, dy, k in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        xi, yi = x0 + dx, y0 + dy
        ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
        idx = yi[ok] * W + xi[ok]
        for c in range(3):
            flat[:, c] += np.bincount(idx, weights=w[ok, c] * k[ok], minlength=W * H)

def boxblur(a, r):
    return scene.blur(a, r)


# ---------- point text ----------
FD = "/usr/share/fonts/opentype/inter/"
JB = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf"
GOLDC = np.array([1.0, 0.78, 0.30], F32); WHITE = np.array([0.95, 0.96, 1.0], F32)
COPPER = np.array([1.0, 0.58, 0.32], F32); REDC = np.array([1.0, 0.32, 0.18], F32)
_T = {}
def text_points(key, items, step=3):
    """items: (x, y, text, font path, size, colour, gold words). Returns screen points + colours."""
    if key not in _T:
        xs, ys, cs = [], [], []
        for x, y, text, fp, size, col, golds in items:
            f = ImageFont.truetype(fp, size)
            cx = x
            for tok in text.split(" "):
                im = Image.new("L", (W, H), 0); ImageDraw.Draw(im).text((cx, y), tok, font=f, fill=255)
                a = np.asarray(im)[::step, ::step]
                yy, xx = np.nonzero(a > 110)
                c = GOLDC if tok.strip("?") in golds else col
                xs.append(xx * step); ys.append(yy * step); cs.append(np.broadcast_to(c, (len(xx), 3)))
                cx += f.getlength(tok + " ")
        rng = np.random.default_rng(len(key))
        x = np.concatenate(xs).astype(F32); y = np.concatenate(ys).astype(F32)
        _T[key] = (x, y, np.concatenate(cs).astype(F32), rng.random(len(x)).astype(F32), rng.normal(size=(len(x), 2)).astype(F32))
        assert x.max() <= R.SAFE_X1 and y.min() >= R.SAFE_Y0 and y.max() <= R.SAFE_Y1, key
    return _T[key]

LABELS = [  # key, items, assemble beat, leave beat
    ("headline", [(64, 238, "McLAREN F1 · ENGINE BAY", JB, 58, COPPER, ()),
                  (64, 330, "WHY IS THERE", FD + "Inter-Black.otf", 104, WHITE, ()),
                  (64, 442, "GOLD IN THIS", FD + "Inter-Black.otf", 104, WHITE, ("GOLD",)),
                  (64, 554, "ENGINE?", FD + "Inter-Black.otf", 104, WHITE, ())], None, "reveal"),
    ("v12", [(64, 700, "V12 · 6.1 L", JB, 76, COPPER, ())], "v12", None),
    ("ir", [(64, 420, "INFRARED HEAT", JB, 76, REDC, ())], "heat", None),
]


def vprog(t, a, d): return np.clip((t - a) / d, 0, 1)
def vio(x): return np.where(x < 0.5, 4 * x ** 3, 1 - (-2 * x + 2) ** 3 / 2)
def voc(x): return 1 - (1 - x) ** 3


# ---------- frame ----------
def frame(t):
    z = data()
    cam = camera(t)
    pos, f, r, u, th, fdist = cam
    acc = np.zeros((H, W, 3), F32); blurred = np.zeros((H // 2, W // 2, 3), F32)
    P = z["P"]
    x, y, d = proj(P, cam)
    ok = (d > 0.05) & (x > -2) & (x < W + 1) & (y > -2) & (y < H + 1)
    x, y, d = x[ok], y[ok], d[ok]
    col = z["col"][ok].copy()
    # heat: header glow flicker, warming carbon around the ray landing points
    hi = heat_i(t)
    hdr = z["mat"][ok] == scene.HEADER
    col[hdr] = np.array([1.0, 0.13, 0.04], F32) * (1.5 + 0.9 * hi * (0.8 + 0.2 * np.sin(t * 40 + P[ok][hdr, 0] * 30)))[:, None]
    wm = np.clip((warm_r(t) - z["dhit"][ok]) / 0.10, 0, 1) * z["face"][ok]
    col = col * (1 - wm[:, None]) + (REDC * 1.6 * z["weave"][ok][:, None]) * wm[:, None]
    fm = np.clip((foil_p(t) - z["wrap"][ok]) / 0.012, 0, 1)[:, None]
    col = col * (1 - fm) + GOLDC * 1.4 * (0.5 + 0.5 * z["inten"][ok])[:, None] * fm
    # scan sweeps: a white plane travelling along x, a copper plane down y after "Not for show"
    sx = -1.7 + 3.6 * ((t / 2.8 + 0.35) % 1)
    col += np.exp(-((P[ok][:, 0] - sx) / 0.035) ** 2)[:, None] * np.array([1.4, 1.5, 1.7], F32)
    ky = prog(t, B["reveal"], 1.2)
    if 0 < ky < 1:
        sy = 1.6 - 1.7 * io(ky)
        col += np.exp(-((P[ok][:, 1] - sy) / 0.03) ** 2)[:, None] * COPPER * 1.8
    # hidden points ghosted via a coarse z-buffer
    cs = 6; gw, gh = W // cs + 1, H // cs + 1
    cell = (np.clip(y, 0, H - 1).astype(np.int64) // cs) * gw + np.clip(x, 0, W - 1).astype(np.int64) // cs
    zb = np.full(gh * gw, np.inf, F32); np.minimum.at(zb, cell, d)
    zb = zb.reshape(gh, gw); z2 = zb.copy()                      # 3x3 min filter closes gaps between scan rings
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            z2 = np.minimum(z2, np.roll(np.roll(zb, dy, 0), dx, 1))
    vis = np.where(d <= z2.reshape(-1)[cell] + 0.06, 1.0, 0.04).astype(F32)
    w = col * (vis * np.clip(d / 2.6, 0.6, 1.4) * 2.6)[:, None]
    # depth of field: split each point between sharp and blurred buffers
    coc = np.clip(np.abs(d - fdist) / fdist * 1.6 - 0.2, 0, 0.8)
    splat(acc, x, y, w * (1 - coc)[:, None])
    bacc = np.zeros((H // 2, W // 2, 3), F32)
    xs, ys = x / 2, y / 2
    sv = (xs >= 0) & (xs < W // 2 - 1) & (ys >= 0) & (ys < H // 2 - 1)
    flat = bacc.reshape(-1, 3); idx = ys[sv].astype(np.int64) * (W // 2) + xs[sv].astype(np.int64)
    for c in range(3): flat[:, c] += np.bincount(idx, weights=(w * coc[:, None])[sv, c], minlength=(W // 2) * (H // 2))
    # heat particles: streams from the headers to the panels
    n = len(z["hs"])
    uu = (t * 0.6 + z["hph"]) % 1
    src = np.stack([scene.HOT[i] for i in range(len(scene.HOT))]).astype(F32)[z["hs"]] + z["hj0"]
    dst = np.stack([scene.HITS[i] for i in range(len(scene.HITS))]).astype(F32)[z["hh"]] + z["hj1"]
    dirv = dst - src; side = np.cross(dirv, np.array([0, 1, 0], F32)); side /= np.linalg.norm(side, axis=1, keepdims=True) + 1e-6
    wob = np.sin(2 * np.pi * (uu * 3.5 + z["hph2"]))[:, None] * 0.035
    hp = src + dirv * uu[:, None] + side * wob
    env = np.sin(np.pi * uu) ** 0.6
    hc = (np.array([1.0, 0.75, 0.35], F32) * (1 - uu[:, None]) + REDC * uu[:, None]) * (env * hi * 6.0)[:, None]
    for lag, kw in ((0.0, 1.0), (0.012, 0.7), (0.024, 0.45), (0.036, 0.25)):      # short glowing streaks
        ul = np.clip(uu - lag, 0, 1)
        wl = np.sin(2 * np.pi * (ul * 3.5 + z["hph2"]))[:, None] * 0.035
        hx, hy, hd = proj(src + dirv * ul[:, None] + side * wl, cam)
        hv = hd > 0.05
        splat(acc, hx[hv], hy[hv], hc[hv] * kw)
        splat(acc, hx[hv] + 1, hy[hv], hc[hv] * kw * 0.5)
    # point text (a dark pocket behind the headline keeps it legible)
    if t < B["reveal"] + 0.8:
        k_h = 1 - io(prog(t, B["reveal"], 0.8))
        yy_ = np.arange(H)[:, None]; xx_ = np.arange(W)[None, :]
        pocket = np.exp(-(((yy_ - 450) / 260.0) ** 4 + ((xx_ - 380) / 520.0) ** 4)) * 0.7 * k_h
        acc *= (1 - pocket)[..., None]
    for key, items, a0, a1 in LABELS:
        ta = 0.0 if a0 is None else B[a0]
        if t < ta or (a1 and t > B[a1] + 1.0): continue
        tx, ty, tc, ph, jit = text_points(key, items, step=2)
        k_in = np.ones_like(ph) if a0 is None else voc(vprog(t, ta + ph * 0.25, 0.55))
        k_out = np.zeros_like(ph) if a1 is None else vio(vprog(t, B[a1] - 0.1 + ph * 0.2, 0.8))
        if a0 is not None and k_in.min() < 1:                          # stream in from the engine
            ei = z["eng"][(np.arange(len(tx)) * 7919) % len(z["eng"])]
            sx_, sy_, _ = proj(z["P"][ei], cam)
            px = sx_ + (tx - sx_) * k_in; py = sy_ + (ty - sy_) * k_in
        else:
            px, py = tx.copy(), ty.copy()
        px = px + jit[:, 0] * (0.6 + 160 * k_out ** 1.5) + 0.8 * np.sin(t * 9 + ph * 40)
        py = py + jit[:, 1] * (0.6 + 160 * k_out ** 1.5) + 320 * k_out ** 2
        tw = 0.75 + 0.25 * np.sin(t * 7 + ph * 60)
        lum = tc * (tw * 2.2 * (1 - k_out))[:, None] * (0.4 + 0.6 * np.minimum(1.0, k_in * 1.5))[:, None]
        splat(acc, px, py, lum)
    # compose
    blur_b = boxblur(bacc, 3)
    acc += np.asarray(Image.fromarray(np.uint8(np.clip(blur_b * 60, 0, 255))).resize((W, H), Image.BILINEAR), F32) / 60
    img = BG + (1 - np.exp(-acc * 2.4)) ** 1.15
    small = Image.fromarray(np.uint8(np.clip(img - 0.40, 0, 1) * 255)).resize((W // 4, H // 4), Image.BILINEAR)
    bl = boxblur(np.asarray(small, F32) / 255, 4)
    img += np.asarray(Image.fromarray(np.uint8(np.clip(bl, 0, 1) * 255)).resize((W, H), Image.BILINEAR), F32) / 255 * 1.3
    yy = np.linspace(-1, 1, H)[:, None]; xx = np.linspace(-1, 1, W)[None, :]
    img *= (1 - 0.35 * np.clip(xx ** 2 * 0.6 + yy ** 2 * 0.5, 0, 1))[..., None]
    im = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255))
    d_ = ImageDraw.Draw(im)                                         # tiny corner tags only
    d_.text((40, 52), "Yub", font=ImageFont.truetype(FD + "Inter-ExtraBold.otf", 34), fill=(200, 200, 205))
    if R.PREVIEW:
        tf = ImageFont.truetype(JB.replace("ExtraBold", "Bold"), 24); tw_ = tf.getlength("PREVIEW")
        d_.rectangle((W - 52 - tw_, 50, W - 32, 86), outline=(255, 80, 60), width=2)
        d_.text((W - 42 - tw_, 68), "PREVIEW", font=tf, fill=(255, 80, 60), anchor="lm")
    return im


def _job(i): return np.asarray(frame(i / FPS)).tobytes()

def video(out, a=0.0, b=7.0):
    from multiprocessing import Pool
    data()
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
            if k % 60 == 0: print(f"frame {n0 + k}/{n1}", flush=True)
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
