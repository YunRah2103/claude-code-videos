"""Style comparison reel: the story timeline played once, cutting between seven looks.

A LiDAR point cloud | B ASCII | C wireframe CAD + exploded view | D thermal / CFD flow |
E holographic HUD + telemetry | F voxel grid | G X-ray ghosting with moving internals.
All share scene geometry, scan points, timing.json and the 3D camera path in pc.py.

  python styles.py still OUTDIR T [T ...]
  python styles.py video OUT.mp4 [START END]
"""
import itertools, math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import ascii as AS
import pc
import render as R
import scene
from render import B, FPS, W, H, clamp, prog, io, oc, heat_i, warm_r, foil_p

F32 = np.float32
REEL = 20.0
SEGS = [("A", "LIDAR POINT CLOUD"), ("B", "ASCII"), ("C", "WIREFRAME CAD"), ("D", "THERMAL / CFD"),
        ("E", "HOLO HUD"), ("F", "VOXEL GRID"), ("G", "X-RAY GHOST")]
SEG_T = REEL / len(SEGS)
JB = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-"
def mono(size, w="ExtraBold"): return ImageFont.truetype(JB + w + ".ttf", int(size))
SAFE_X1, SAFE_Y0, SAFE_Y1 = R.SAFE_X1, R.SAFE_Y0, R.SAFE_Y1

def seg_of(t): return min(len(SEGS) - 1, int(t / SEG_T))
def seg_prog(t, i, a=0.0, d=1.0): return prog(t, i * SEG_T + a, d)


# ---------- shared geometry ----------
_WIRE = {}
def wire():
    """Wireframe segments of every primitive: (A, B, part, mat)."""
    if not _WIRE:
        A, Bv, P_, M_ = [], [], [], []
        def add(a, b, s): A.append(a); Bv.append(b); P_.append(s.part); M_.append(s.mat)
        for s in scene.build_scene():
            if isinstance(s, scene.Box):
                cs = {sg: s.c + s.R @ (s.h * np.array(sg)) for sg in itertools.product((-1, 1), repeat=3)}
                for a, b in itertools.combinations(cs, 2):
                    if sum(x != y for x, y in zip(a, b)) == 1: add(cs[a], cs[b], s)
            elif isinstance(s, scene.Cyl):
                ang = np.linspace(0, 2 * np.pi, 17)
                for yy in (-s.hh, s.hh):
                    ring = [s.c + s.R @ np.array([s.r * math.cos(a), yy, s.r * math.sin(a)]) for a in ang]
                    for a, b in zip(ring[:-1], ring[1:]): add(a, b, s)
                for a in ang[:-1:4]:
                    add(s.c + s.R @ np.array([s.r * math.cos(a), -s.hh, s.r * math.sin(a)]),
                        s.c + s.R @ np.array([s.r * math.cos(a), s.hh, s.r * math.sin(a)]), s)
            else:
                ax = s.b - s.a; L = np.linalg.norm(ax); ax = ax / L
                e1 = np.cross(ax, [0, 1, 0]); e1 = e1 / (np.linalg.norm(e1) + 1e-9) if np.linalg.norm(e1) > 1e-3 else np.array([1.0, 0, 0])
                e2 = np.cross(ax, e1)
                ang = np.linspace(0, 2 * np.pi, 13)
                for c in (s.a, (s.a + s.b) / 2, s.b):
                    ring = [c + s.r * (math.cos(a) * e1 + math.sin(a) * e2) for a in ang]
                    for a, b in zip(ring[:-1], ring[1:]): add(a, b, s)
                for a in ang[:-1:3]:
                    o = s.r * (math.cos(a) * e1 + math.sin(a) * e2); add(s.a + o, s.b + o, s)
        _WIRE.update(A=np.array(A, F32), B=np.array(Bv, F32), part=np.array(P_), mat=np.array(M_))
    return _WIRE

GROUP_VEC = {}  # part id -> exploded offset (metres)
for names, v in ((("back panel", "frame rails"), (0.0, 0.18, -0.45)), (("bulkhead", "fuel cell"), (-0.5, 0.05, 0.0)),
                 (("crankcase", "cyl banks", "cam covers", "intake trumpets", "exhaust headers", "gearbox", "coil packs"), (0.0, 0.32, 0.12)),
                 (("wheel", "suspension"), (0.45, 0.0, 0.15))):
    for n in names: GROUP_VEC[scene.P[n]] = np.array(v, F32)

def offsets(part, k):
    return np.stack([GROUP_VEC.get(int(p), np.zeros(3, F32)) for p in part]) * k

def lines(d, cam, A, Bv, col, width=2, alpha=1.0):
    xa, ya, za = pc.proj(A, cam); xb, yb, zb = pc.proj(Bv, cam)
    ok = (za > 0.05) & (zb > 0.05)
    c = col if isinstance(col, np.ndarray) and col.ndim == 2 else None
    for i in np.nonzero(ok)[0]:
        cc = tuple(int(v) for v in c[i]) if c is not None else col
        d.line((xa[i], ya[i], xb[i], yb[i]), fill=(*cc, int(255 * alpha)), width=width)

def glow_add(img, layer, r=8, k=1.4):
    g = np.asarray(layer.filter(ImageFilter.GaussianBlur(r)), F32) / 255
    s = np.asarray(layer, F32) / 255
    return img + g[..., :3] * g[..., 3:] * k + s[..., :3] * s[..., 3:]

def heat_paths(t, n=900, lags=(0.0,)):
    """Heat particle positions (per lag) along wavy paths from headers to the panels."""
    z = pc.data()
    hs, hh, ph, ph2 = z["hs"][:n], z["hh"][:n], z["hph"][:n], z["hph2"][:n]
    src = np.stack(scene.HOT).astype(F32)[hs] + z["hj0"][:n]
    dst = np.stack(scene.HITS).astype(F32)[hh] + z["hj1"][:n]
    dv = dst - src; side = np.cross(dv, np.array([0, 1, 0], F32)); side /= np.linalg.norm(side, axis=1, keepdims=True) + 1e-6
    up = np.cross(side, dv); up /= np.linalg.norm(up, axis=1, keepdims=True) + 1e-6
    out = []
    for lag in lags:
        u = np.clip((t * 0.6 + ph) % 1 - lag, 0, 1)
        a = 2 * np.pi * (u * 2.5 + ph2)
        rad = 0.045 * np.sin(np.pi * u)
        out.append((src + dv * u[:, None] + (side * np.cos(a)[:, None] + up * np.sin(a)[:, None]) * rad[:, None], u))
    return out

def label(d, text, x, y, size, col, anchor_xy=None, a=1.0, w="ExtraBold"):
    f = mono(size, w)
    x1 = x + f.getlength(text); y1 = y + size * 1.15
    assert x1 <= SAFE_X1 and y >= SAFE_Y0 and y1 <= SAFE_Y1, text
    d.text((x, y), text, font=f, fill=(*col, int(255 * a)))
    if anchor_xy is not None:
        tx, ty = anchor_xy
        sx = x1 + 10 if tx > x1 else x - 10
        d.line((sx, y + size * 0.6, tx, ty), fill=(*col, int(200 * a)), width=2)
        d.ellipse((tx - 6, ty - 6, tx + 6, ty + 6), outline=(*col, int(255 * a)), width=2)
    return x1


# ---------- C: wireframe CAD with exploded view ----------
def style_cad(t):
    cam = pc.camera(t); i = 2
    img = np.zeros((H, W, 3), F32) + np.array([0.03, 0.038, 0.05], F32)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for x in np.arange(-1.6, 1.81, 0.1):                              # matte grid floor
        maj = abs(x * 2 - round(x * 2)) < 1e-6
        lines(d, cam, np.array([[x, 0, -0.75]], F32), np.array([[x, 0, 1.3]], F32), (60, 110, 160), 1, 0.45 if maj else 0.18)
    for zz in np.arange(-0.7, 1.31, 0.1):
        maj = abs(zz * 2 - round(zz * 2)) < 1e-6
        lines(d, cam, np.array([[-1.6, 0, zz]], F32), np.array([[1.8, 0, zz]], F32), (60, 110, 160), 1, 0.45 if maj else 0.18)
    k = io(seg_prog(t, i, 0.15, 0.8)) * (1 - io(seg_prog(t, i, 2.1, 0.6)))
    wv = wire()
    off = offsets(wv["part"], k)
    col = np.tile(np.array([[90, 190, 255]]), (len(off), 1))
    eng = np.isin(wv["part"], [scene.P[n] for n in ("crankcase", "cyl banks", "cam covers", "intake trumpets", "gearbox", "coil packs")])
    col[eng] = (255, 165, 80); col[wv["mat"] == scene.HEADER] = (255, 70, 45)
    lines(d, cam, wv["A"] + off, wv["B"] + off, col, 2, 0.85)
    if k > 0.02:                                                     # exploded vectors
        for pid, v in [(scene.P["back panel"], None), (scene.P["bulkhead"], None), (scene.P["crankcase"], None), (scene.P["wheel"], None)]:
            m = wv["part"] == pid
            c0 = ((wv["A"][m] + wv["B"][m]) / 2).mean(0)
            c1 = c0 + GROUP_VEC[pid] * k
            x0, y0, _ = pc.proj(c0[None], cam); x1, y1, _ = pc.proj(c1[None], cam)
            L = math.hypot(x1[0] - x0[0], y1[0] - y0[0])
            for j in range(int(L // 18)):
                a0, a1 = j * 18 / L, min(1, (j * 18 + 10) / L)
                d.line((x0[0] + (x1[0] - x0[0]) * a0, y0[0] + (y1[0] - y0[0]) * a0, x0[0] + (x1[0] - x0[0]) * a1, y0[0] + (y1[0] - y0[0]) * a1),
                       fill=(230, 240, 255, 200), width=2)
            ang = math.atan2(y1[0] - y0[0], x1[0] - x0[0])
            d.polygon([(x1[0], y1[0]), (x1[0] - 16 * math.cos(ang - 0.4), y1[0] - 16 * math.sin(ang - 0.4)),
                       (x1[0] - 16 * math.cos(ang + 0.4), y1[0] - 16 * math.sin(ang + 0.4))], fill=(230, 240, 255, 230))
    # XYZ gizmo + engine dimension line
    o = np.array([[-1.2, 0.0, 1.0]], F32)
    for v, c, nm in (((0.25, 0, 0), (255, 80, 80), "X"), ((0, 0.25, 0), (90, 255, 120), "Y"), ((0, 0, 0.25), (90, 160, 255), "Z")):
        lines(d, cam, o, o + np.array([v], F32), c, 3)
        xx, yy, zz = pc.proj(o + np.array([v], F32) * 1.25, cam)
        if zz[0] > 0: d.text((xx[0], yy[0]), nm, font=mono(26), fill=(*c, 255), anchor="mm")
    eo = GROUP_VEC[scene.P["crankcase"]] * k
    a3 = np.array([[-0.52, 0.02, 0.3]], F32) + eo; b3 = np.array([[0.5, 0.02, 0.3]], F32) + eo
    lines(d, cam, a3, b3, (230, 240, 255), 2)
    for p_ in (a3, b3): lines(d, cam, p_ - np.array([[0, 0.05, 0]], F32), p_ + np.array([[0, 0.05, 0]], F32), (230, 240, 255), 2)
    # heat as orange flow
    for P_, u in heat_paths(t, 700, lags=(0.0, 0.015, 0.03)):
        x, y, z_ = pc.proj(P_, cam); ok = z_ > 0.05
        for xi, yi, ui in zip(x[ok], y[ok], u[ok]):
            d.point((xi, yi), fill=(255, int(150 - 90 * ui), 60, 220))
    img = glow_add(img, lay, 6, 1.6)
    im = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255)); d = ImageDraw.Draw(im, "RGBA")
    ax_, ay_, _ = pc.proj(np.array([[-0.15, 0.64, 0.14]], F32) + eo, cam)
    if t >= B["v12"]: label(d, "V12 · 6.1 L", 64, 640, 66, (255, 175, 90), (ax_[0], ay_[0]), min(1, (t - B["v12"]) / 0.3))
    hx, hy, _ = pc.proj(np.array([[0.02, 0.92, -0.3]], F32), cam)
    if t >= B["heat"]: label(d, "INFRARED HEAT", 64, 420, 66, (255, 110, 70), (hx[0], hy[0]), min(1, (t - B["heat"]) / 0.3))
    return im


# ---------- D: thermal / CFD ----------
def turbo(v):
    stops = np.array([[0.19, 0.07, 0.23], [0.15, 0.45, 0.95], [0.1, 0.85, 0.85], [0.45, 0.98, 0.35],
                      [0.98, 0.85, 0.2], [0.98, 0.45, 0.1], [0.75, 0.05, 0.05]], F32)
    x = np.clip(v, 0, 1) * (len(stops) - 1); i = np.minimum(x.astype(int), len(stops) - 2); f = (x - i)[..., None]
    return stops[i] * (1 - f) + stops[i + 1] * f

_DH = {}
def style_cfd(t):
    z = pc.data(); cam = pc.camera(t)
    if "dh" not in _DH:
        hp = np.stack([w for w in scene.HOT]).astype(F32)
        _DH["dh"] = np.min(np.linalg.norm(z["P"][:, None, :] - hp[None], axis=2), axis=1)
    P = z["P"]; x, y, dd = pc.proj(P, cam)
    ok = (dd > 0.05) & (x > -2) & (x < W + 1) & (y > -2) & (y < H + 1)
    hi = heat_i(t)
    temp = 0.95 * np.exp(-_DH["dh"] / 0.28) * hi * 0.85
    temp = temp + 0.75 * np.clip((warm_r(t) - z["dhit"]) / 0.18, 0, 1) * z["face"]
    temp = temp + 0.06 * np.sin(_DH["dh"] * 28 - t * 7)                 # pulsing iso-bands
    temp = np.where(z["mat"] == scene.HEADER, 1.0, temp) + 0.08
    col = turbo(temp)[ok] * (0.45 + 0.55 * z["inten"][ok])[:, None]
    acc = np.zeros((H, W, 3), F32)
    pc.splat(acc, x[ok], y[ok], col * 1.6)
    # streaklines through the heat field, coloured by temperature along the path
    for (P_, u), kw in zip(heat_paths(t, 1100, lags=(0.0, 0.01, 0.02, 0.03, 0.04, 0.05)), (1, .8, .65, .5, .35, .2)):
        hx, hy, hz = pc.proj(P_, cam); v = hz > 0.05
        pc.splat(acc, hx[v], hy[v], turbo(1 - 0.75 * u[v]) * 3.0 * kw * hi)
    img = np.array([0.02, 0.02, 0.03], F32) + (1 - np.exp(-acc * 2.0))
    sm = Image.fromarray(np.uint8(np.clip(img - 0.4, 0, 1) * 255)).resize((W // 4, H // 4), Image.BILINEAR)
    img += np.asarray(sm.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR), F32) / 255 * 0.9
    im = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255)); d = ImageDraw.Draw(im, "RGBA")
    for j in range(300):                                               # colour scale (decoration, right margin)
        c = tuple(int(255 * v) for v in turbo(1 - j / 300))
        d.line((W - 70, 520 + j * 3, W - 46, 520 + j * 3), fill=c, width=3)
    ax_, ay_, _ = pc.proj(np.array([[0.35, 0.72, -0.58]], F32), cam)
    if t >= B["carbon"]: label(d, "CARBON FIBRE", 64, 860, 66, (235, 240, 255), (ax_[0], ay_[0]), min(1, (t - B["carbon"]) / 0.3))
    hx, hy, _ = pc.proj(np.array([[0.02, 0.92, -0.3]], F32), cam)
    label(d, "INFRARED HEAT", 64, 420, 66, (255, 120, 80), (hx[0], hy[0]))
    return im


# ---------- E: holographic HUD + telemetry ----------
CYAN = (90, 230, 255); AMBER = (255, 190, 80)
def style_hud(t):
    z = pc.data(); cam = pc.camera(t)
    P = z["P"]; x, y, dd = pc.proj(P, cam)
    ok = (dd > 0.05) & (x > -2) & (x < W + 1) & (y > -2) & (y < H + 1)
    fm = np.clip((foil_p(t) - z["wrap"]) / 0.012, 0, 1)[ok][:, None]
    base = np.array([0.35, 0.85, 1.0], F32) * (0.3 + 0.7 * z["inten"][ok])[:, None]
    col = base * (1 - fm) + np.array([1.0, 0.78, 0.3], F32) * fm * 1.2
    col[z["mat"][ok] == scene.HEADER] = (1.0, 0.3, 0.12)
    acc = np.zeros((H, W, 3), F32); pc.splat(acc, x[ok], y[ok], col * 0.9)
    img = np.array([0.01, 0.025, 0.035], F32) + (1 - np.exp(-acc * 2.2))
    img *= (0.88 + 0.12 * ((np.arange(H) // 3) % 2))[:, None, None]          # scanline texture
    sy = (t * 520) % (H + 300) - 150
    img += (np.exp(-((np.arange(H) - sy) / 6.0) ** 2) * 0.35)[:, None, None] * np.array([0.4, 0.9, 1.0], F32)
    im = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    # tracking reticles locked to the exhaust ports and the foil
    targets = [(scene.HOT[0], "EXH-01", (255, 110, 70)), (scene.HOT[1], "EXH-02", (255, 110, 70)),
               (scene.HOT[2], "EXH-03", (255, 110, 70)), (np.array([-0.76, 0.62, -0.25]), "FOIL", AMBER),
               (scene.HITS[2], "PNL-B", CYAN)]
    for j, (p_, tag, c) in enumerate(targets):
        tx, ty, tz = pc.proj(np.array([p_], F32), cam)
        if tz[0] <= 0.05: continue
        q = 24 + 4 * math.sin(t * 6 + j); rot = t * 1.5 + j
        for a in range(4):
            ang = rot + a * math.pi / 2
            cx_, cy_ = tx[0] + q * math.cos(ang), ty[0] + q * math.sin(ang)
            d.line((cx_, cy_, cx_ + 10 * math.cos(ang + 2.4), cy_ + 10 * math.sin(ang + 2.4)), fill=(*c, 255), width=3)
            d.line((cx_, cy_, cx_ + 10 * math.cos(ang - 2.4), cy_ + 10 * math.sin(ang - 2.4)), fill=(*c, 255), width=3)
        d.text((tx[0] + q + 8, ty[0] - 26), tag, font=mono(22, "Bold"), fill=(*c, 230))
    # telemetry panel: panel temperature trace (qualitative) - rises with the heat, drops once the foil is on
    px0, py0, px1, py1 = 64, 300, 880, 600
    d.rectangle((px0, py0, px1, py1), fill=(0, 20, 30, 150), outline=(*CYAN, 200), width=2)
    d.text((px0 + 20, py0 + 14), "PANEL TEMP", font=mono(58), fill=(*CYAN, 255))
    ts = np.linspace(max(0, t - 6), t, 80)
    vals = [min(1, warm_r(s) / 0.57) * (1 - 0.85 * min(1, foil_p(s))) for s in ts]
    pts = [(px0 + 20 + (px1 - px0 - 40) * j / 79, py1 - 24 - (py1 - py0 - 120) * v) for j, v in enumerate(vals)]
    for gx in range(px0 + 20, px1 - 20, 60): d.line((gx, py0 + 96, gx, py1 - 20), fill=(*CYAN, 40), width=1)
    d.line(pts, fill=(255, 120, 80, 255), width=4)
    d.ellipse((pts[-1][0] - 7, pts[-1][1] - 7, pts[-1][0] + 7, pts[-1][1] + 7), fill=(255, 220, 160, 255))
    if t >= B["lined"] + 0.7: label(d, "REFLECTED", 64, 640, 66, AMBER, None, min(1, (t - B["lined"] - 0.7) / 0.3))
    if t >= B["gold"]: label(d, "GOLD FOIL", 64, 740, 66, AMBER, None, min(1, (t - B["gold"]) / 0.3))
    # rolling hex memory columns (decoration in the right margin)
    rng = np.random.default_rng(int(t * 12))
    for r_ in range(26):
        hx_ = "".join(rng.choice(list("0123456789ABCDEF"), 4))
        d.text((W - 118, 300 + r_ * 44), hx_, font=mono(24, "Bold"), fill=(*CYAN, 110 + 60 * (r_ % 2)))
    out = Image.alpha_composite(im.convert("RGBA"), lay.filter(ImageFilter.GaussianBlur(5)))
    return Image.alpha_composite(out, lay).convert("RGB")


# ---------- F: voxel grid ----------
_VX = {}
def voxels():
    if not _VX:
        z = pc.data(); s = 0.035
        key = np.floor(z["P"] / s).astype(np.int64)
        uniq, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.reshape(-1)
        cnt = np.bincount(inv)
        C = np.stack([np.bincount(inv, weights=z["col"][:, c]) for c in range(3)], 1) / cnt[:, None]
        wr = np.full(len(uniq), 9.0); np.minimum.at(wr, inv, z["wrap"])
        hdr = np.zeros(len(uniq), bool); np.logical_or.at(hdr, inv, z["mat"] == scene.HEADER)
        ctr = (uniq + 0.5) * s
        rng = np.random.default_rng(5)
        _VX.update(ctr=ctr.astype(F32), col=C.astype(F32), wrap=wr.astype(F32), hdr=hdr, s=s,
                   scat=(ctr + rng.normal(size=ctr.shape) * 0.6 + np.array([0, 0.6, 0])).astype(F32), ph=rng.random(len(uniq)).astype(F32))
    return _VX

def style_voxel(t):
    v = voxels(); cam = pc.camera(t); i = 5
    pos_, f, r, u, th, _ = cam
    ka = oc(np.clip((t - i * SEG_T - v["ph"] * 0.5) / 0.7, 0, 1))[:, None]                 # assemble
    kb = np.clip((t - (i + 1) * SEG_T + 0.9 - v["ph"] * 0.4) / 0.5, 0, 1)[:, None]        # dissolve at the end
    ctr = v["scat"] * (1 - ka) + v["ctr"] * ka
    ctr = ctr * (1 - kb) + v["scat"] * kb
    dist = np.linalg.norm(v["ctr"][:, [0, 2]], axis=1)
    rip = 0.05 * np.sin(dist * 9 - (t - B["grams"]) * 9) * np.exp(-np.abs(dist - (t - B["grams"]) * 1.0) * 3) * (t > B["grams"])
    ctr = ctr + np.stack([np.zeros_like(rip), rip, np.zeros_like(rip)], 1).astype(F32)
    fm = np.clip((foil_p(t) - v["wrap"]) / 0.012, 0, 1)[:, None]
    col = v["col"] * (1 - fm) + np.array([1.0, 0.76, 0.28], F32) * fm
    col[v["hdr"]] = (1.0, 0.3, 0.12)
    x, y, dd = pc.proj(ctr, cam)
    ok = (dd > 0.1) & (x > -40) & (x < W + 40) & (y > -40) & (y < H + 40)
    order = np.argsort(-dd[ok]); idx = np.nonzero(ok)[0][order]
    hs = v["s"] * 0.5 * 0.92
    im = Image.new("RGB", (W, H), (6, 7, 9)); d = ImageDraw.Draw(im)
    # visible faces depend on which side of each axis the camera is on
    sx_, sy_, sz_ = np.sign(pos_ - 0.0)
    faces = [((0, 1, 0), 1.0), ((sx_, 0, 0), 0.72), ((0, 0, sz_), 0.52)]
    corners = {}
    for (fx, fy, fz), shade in faces:
        n_ = np.array([fx, fy, fz], F32)
        a1 = np.array([0, 1, 0], F32) if fy == 0 else np.array([1, 0, 0], F32)
        a2 = np.cross(n_, a1)
        quad = [n_ * hs + (a1 * p + a2 * q) * hs for p, q in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        corners[(fx, fy, fz)] = (np.array(quad, F32), shade)
    proj_q = {}
    for key_, (quad, shade) in corners.items():
        pts = ctr[idx][:, None, :] + quad[None]
        qx, qy, qz = pc.proj(pts.reshape(-1, 3), cam)
        proj_q[key_] = (qx.reshape(-1, 4), qy.reshape(-1, 4), shade)
    for n_i, vi in enumerate(idx):
        c = col[vi]
        for key_, (qx, qy, shade) in proj_q.items():
            cc = tuple(int(255 * min(1, c[j] * shade * 1.25)) for j in range(3))
            d.polygon(list(zip(qx[n_i], qy[n_i])), fill=cc)
    # voxel text for the 16 g beat
    if t >= B["grams"]:
        kt = clamp((t - B["grams"]) / 0.5)
        tm = Image.new("L", (W, H), 0); tdm = ImageDraw.Draw(tm); tdm.text((64, 560), "GOLD FOIL", font=mono(96), fill=255); tdm.text((64, 690), "ABOUT 16 g", font=mono(96), fill=255)
        m = np.asarray(tm).reshape(H // 12, 12, W // 12, 12).mean((1, 3)) > 90
        ys, xs = np.nonzero(m)
        rng = np.random.default_rng(9); pp = rng.random(len(xs))
        cells = [(xx, yy) for xx, yy, p_ in zip(xs, ys, pp) if p_ <= kt]
        for xx, yy in cells:
            x0_, y0_ = xx * 12, yy * 12
            assert x0_ + 12 <= SAFE_X1 + 12 and SAFE_Y0 <= y0_ <= SAFE_Y1
            d.rectangle((x0_ - 3, y0_ - 3, x0_ + 13, y0_ + 13), fill=(8, 8, 10))
        for xx, yy in cells:
            x0_, y0_ = xx * 12, yy * 12
            d.rectangle((x0_, y0_, x0_ + 10, y0_ + 10), fill=(250, 246, 232)); d.rectangle((x0_, y0_ + 8, x0_ + 10, y0_ + 10), fill=(255, 200, 80))
    a = np.asarray(im, F32) / 255
    sm = Image.fromarray(np.uint8(np.clip(a - 0.5, 0, 1) * 255)).resize((W // 4, H // 4), Image.BILINEAR)
    a += np.asarray(sm.filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR), F32) / 255 * 0.7
    return Image.fromarray(np.uint8(np.clip(a, 0, 1) * 255))


# ---------- G: X-ray ghost with moving internals ----------
def hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3: return pts
    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0: h.pop()
            h.append(p)
        return h
    lo, up = half(pts), half(pts[::-1])
    return lo[:-1] + up[:-1]

def style_xray(t):
    z = pc.data(); cam = pc.camera(t)
    P = z["P"]; x, y, dd = pc.proj(P, cam)
    ok = (dd > 0.05) & (x > -2) & (x < W + 1) & (y > -2) & (y < H + 1)
    ghost = np.array([0.55, 0.75, 1.0], F32) * (0.30 + 0.25 * z["inten"][ok])[:, None]
    fm = np.clip((foil_p(t) - z["wrap"]) / 0.012, 0, 1)[ok][:, None]
    ghost = ghost * (1 - fm) + np.array([0.5, 0.38, 0.12], F32) * fm
    ghost[z["mat"][ok] == scene.HEADER] = (0.9, 0.2, 0.06)
    acc = np.zeros((H, W, 3), F32); pc.splat(acc, x[ok], y[ok], ghost)
    img = np.array([0.01, 0.012, 0.02], F32) + (1 - np.exp(-acc * 2.0))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    wv = wire(); lines(d, cam, wv["A"], wv["B"], (120, 170, 235), 1, 0.45)
    # internals: crankshaft with six throws, twelve pistons + rods, driveshaft
    om = 2 * np.pi * 2.2 * t
    crank_y, crank_z = 0.2, 0.0
    lines(d, cam, np.array([[-0.5, crank_y, crank_z]], F32), np.array([[0.5, crank_y, crank_z]], F32), (255, 170, 80), 6)
    for side in (1, -1):
        Rb = scene.rot("x", -30 * side); upv = (Rb @ np.array([0, 1, 0.0])).astype(F32)
        for j in range(6):
            xx = -0.38 + j * 0.152
            phase = om + j * (2 * np.pi / 3) + (0 if side > 0 else np.pi / 3)
            pin = np.array([xx, crank_y + 0.05 * math.cos(phase), crank_z + 0.05 * math.sin(phase)], F32)
            base = np.array([xx, 0.30, 0.04 * side], F32)
            pcn = base + upv * (0.07 + 0.035 * math.cos(phase))
            lines(d, cam, np.array([[xx, crank_y, crank_z]], F32), pin[None], (255, 200, 120), 4)
            lines(d, cam, pin[None], pcn[None], (240, 240, 250), 3)
            ang = np.linspace(0, 2 * np.pi, 14, endpoint=False)
            e1 = np.array([1, 0, 0], F32); e2 = np.cross(upv, e1)
            ring = [pcn + upv * hh + 0.034 * (math.cos(a) * e1 + math.sin(a) * e2) for hh in (-0.03, 0.03) for a in ang]
            px_, py_, pz_ = pc.proj(np.array(ring, F32), cam)
            if (pz_ > 0.05).all():
                hp = hull([(float(a), float(b)) for a, b in zip(px_, py_)])
                heat = 0.5 + 0.5 * math.cos(phase)
                d.polygon(hp, fill=(255, int(120 + 100 * heat), 60, 235), outline=(255, 240, 200, 255))
    sp = np.array([[0.95, 0.24, 0.0]], F32); wp = np.array([[1.34, 0.36, 0.55]], F32)
    lines(d, cam, sp, wp, (255, 170, 80), 5)
    for j in range(6):
        k = ((om / (2 * np.pi) * 2 + j / 6) % 1)
        mp = sp + (wp - sp) * k
        lines(d, cam, mp - np.array([[0, 0.03, 0]], F32), mp + np.array([[0, 0.03, 0]], F32), (255, 230, 170), 3)
    img = glow_add(img, lay, 7, 1.5)
    im = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255)); d = ImageDraw.Draw(im, "RGBA")
    # the question, in thin outline type
    if t >= B["question"]:
        a = min(1, (t - B["question"]) / 0.35)
        for li, line in enumerate(("WOULD YOU LINE", "YOUR CAR", "WITH GOLD?")):
            label(d, line, 64, 300 + li * 100, 80, (240, 244, 255) if li < 2 else (255, 205, 100), None, a)
        for j, (lab, x0) in enumerate((("YES", 64), ("NO", 500))):
            wi = [w for w in R.WORDS if w["w"].strip("?").lower() == lab.lower()][0]
            on = wi["s"] - 0.05 <= t < wi["e"] + 0.35
            c = (255, 205, 100) if j == 0 else (180, 220, 255)
            d.rectangle((x0, 640, x0 + 380, 800), outline=(*c, int(255 * a)), width=4, fill=(*c, int(200 * a)) if on else None)
            d.text((x0 + 190, 720), lab, font=mono(84), fill=((10, 10, 14, 255) if on else (*c, int(255 * a))), anchor="mm")
    return im


# ---------- reel ----------
STYLE_FN = [lambda t: pc.frame(t, text=True, tags=False), lambda t: AS.frame(t, tags=False),
            style_cad, style_cfd, style_hud, style_voxel, style_xray]

def frame(t):
    i = seg_of(t)
    im = STYLE_FN[i](t)
    d = ImageDraw.Draw(im, "RGBA")
    code, name = SEGS[i]
    f = mono(26, "Bold"); txt = f"{code}  {name}"; tw = f.getlength(txt)
    d.rectangle((32, 40, 32 + tw + 28, 82), fill=(0, 0, 0, 170), outline=(255, 255, 255, 120), width=1)
    d.text((46, 61), txt, font=f, fill=(255, 255, 255, 235), anchor="lm")
    d.text((40, 136), "Yub", font=ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf", 28), fill=(200, 200, 205, 220))
    tf = mono(24, "Bold"); pw = tf.getlength("PREVIEW")
    d.rectangle((W - 52 - pw, 44, W - 32, 80), outline=(255, 80, 60, 230), width=2)
    d.text((W - 42 - pw, 62), "PREVIEW", font=tf, fill=(255, 80, 60, 230), anchor="lm")
    sp = (t % SEG_T) / SEG_T                                          # segment progress bar
    d.rectangle((32, 86 + 34, 32 + (tw + 28) * sp, 86 + 37), fill=(255, 255, 255, 160))
    return im


def _job(i): return np.asarray(frame(i / FPS)).tobytes()

def video(out, a=0.0, b=REEL):
    from multiprocessing import Pool
    pc.data(); AS.glyphs(); wire(); voxels()
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
