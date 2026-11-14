"""Gold engine bay, blueprint style: line drawing on a navy sheet; only the hot headers,
the carbon panel and the gold foil turn "real". Same timing.json, camera and audio as render.py.

  python render_bp.py still OUTDIR T [T ...]
  python render_bp.py video OUT.mp4 [START END]
  python render_bp.py elements T [T ...]
"""
import math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import render as R
import scene
from render import (B, DUR, FPS, W, H, WORDS, LOOP, clamp, prog, io, oc, ob, cam, crop, font, rgba,
                    heat_i, warm_r, foil_p, dim, wave, reflect, RAYS, beat, caption)

NAVY = (11, 30, 58); LINE = (222, 236, 255); GRIDC = (120, 170, 235)
GOLD = (246, 196, 82); HEATC = (255, 84, 48); PALE = (150, 190, 240)
SAFE_X1, SAFE_Y0, SAFE_Y1 = int(W * 0.85), int(H * 0.12), int(H * 0.62)
def f3(c): return np.array(c, np.float32) / 255

# ---------- extra plate layers (computed once per process from the cached render) ----------
_X = {}
def extra():
    if not _X:
        z = np.load(R.CACHE)
        lum = z["base"].astype(np.float32) @ np.array([0.3, 0.59, 0.11], np.float32) / 255
        surf = z["depth"] < 30
        yy, xx = np.mgrid[0:scene.PH, 0:scene.PW]
        hatch = surf & (lum < 0.13) & (((xx + yy) % 13) < 2)
        hatch |= surf & (lum < 0.06) & (((xx - yy) % 13) < 2)          # cross-hatch in deep shadow
        dg = z["diag"]; lo, hi = dg[surf].min(), dg[surf].max()
        dm = np.where(surf, (dg - lo) / (hi - lo), 0).astype(np.float32)
        _X["hatch"] = Image.fromarray((hatch * 255).astype(np.uint8))
        _X["draw"] = Image.fromarray(dm, "F")
        _X["lum"] = Image.fromarray((np.clip(lum, 0, 1) * 255).astype(np.uint8))
    return _X

def xcrop(name, box, rs=Image.BILINEAR):
    a = np.asarray(extra()[name].resize((W, H), rs, box=box))
    return a.astype(np.float32) / 255.0 if a.dtype == np.uint8 else a.astype(np.float32)


# ---------- timeline ----------
def draw_p(t):
    """How much of the drawing is penned on: 45% at frame 1, complete by 1.6 s, erases back for the loop."""
    up = 0.45 + 0.6 * io(prog(t, 0, 1.6))
    return up - 0.6 * io(prog(t, B["outro"], B["end"] - B["outro"] - 0.04))

def explode(t):
    return io(prog(t, B["reveal"] + 0.1, 0.7)) * (1 - io(prog(t, B["heat"] - 0.55, 0.6)))

def carbon_real(t):
    return 1.25 * io(prog(t, B["carbon"] - 0.1, 0.9)) * (1 - io(prog(t, B["outro"], B["end"] - B["outro"] - 0.04)))

GROUPS = [  # back to front: part names, plate-px offset when exploded
    (("back panel", "frame rails"), (40, -300)),
    (("bulkhead", "fuel cell"), (-260, -60)),
    (("crankcase", "cyl banks", "cam covers", "intake trumpets", "exhaust headers", "gearbox", "coil packs"), (20, 60)),
    (("wheel", "suspension"), (240, 40)),
]
GIDS = [[scene.P[n] for n in names] for names, _ in GROUPS]

def goff(gi, t, s):
    k = explode(t); ox, oy = GROUPS[gi][1]
    return ox * k * s, oy * k * s

def group_of(p):
    if abs(p[0] + 0.76) < 0.02: return 1
    if abs(p[2] + 0.58) < 0.02: return 0
    return 2

def scr(box, p, t, gi=None):
    s = W / (box[2] - box[0])
    x, y = R.to_screen(box, p)
    if gi is None: gi = group_of(p)
    dx, dy = goff(gi, t, s)
    return x + dx, y + dy

def shift(a, dx, dy):
    out = np.zeros_like(a); dx, dy = int(round(dx)), int(round(dy))
    ys, yd = (slice(0, H - dy), slice(dy, H)) if dy >= 0 else (slice(-dy, H), slice(0, H + dy))
    xs, xd = (slice(0, W - dx), slice(dx, W)) if dx >= 0 else (slice(-dx, W), slice(0, W + dx))
    out[yd, xd] = a[ys, xs]
    return out


# ---------- frame ----------
def frame(t, info=None):
    t = clamp(t, 0, DUR - 1e-6)
    box, focus = cam(t)
    s = W / (box[2] - box[0])
    part = np.asarray(R.layers()["part"].resize((W, H), Image.NEAREST, box=box))
    surf = (part > 0)[..., None]
    lum = xcrop("lum", box)
    ink = crop("ink", box, Image.BILINEAR)
    hatch = xcrop("hatch", box)
    dm = xcrop("draw", box)
    dp = draw_p(t)
    drawn = np.clip((dp - dm) / 0.02, 0, 1)
    pen = (np.abs(dm - dp) < 0.015) & (ink > 0.35) & (dp < 1.04)
    # line drawing: tinted fill, hatching, outlines
    paper = f3(NAVY)
    img = paper + surf * (0.035 + 0.20 * lum)[..., None] * f3(PALE) * drawn[..., None]
    img = img + (hatch * 0.28 * drawn)[..., None] * f3(LINE)
    a_ink = (ink * drawn)[..., None]
    img = img * (1 - a_ink) + f3(LINE) * a_ink
    img[pen] = f3((255, 255, 255))
    # "real" materials: hot headers always, carbon floods in, gold foil wraps
    base = crop("base", box)
    hdr = (part == scene.P["exhaust headers"])[..., None]
    hi = heat_i(t)
    e = crop("emis", box) * hi
    hot = base + 0.8 * (e[..., None] * np.array([0.95, 0.13, 0.03]) + (e ** 3)[..., None] * np.array([1.0, 0.55, 0.12]))
    img = img * (1 - hdr) + hot * hdr
    wipe = crop("wipe", box, Image.BILINEAR)
    face = (wipe < 5)[..., None]
    cr = np.clip((carbon_real(t) - dm) / 0.05, 0, 1)[..., None] * face
    img = img * (1 - cr) + (base * 1.15 + 0.15 * ink[..., None] * f3(LINE)) * cr
    fp = foil_p(t)
    fm = np.clip((fp - wipe) / 0.012, 0, 1)[..., None]
    img = img * (1 - fm) + crop("gold", box) * fm
    edge = np.exp(-((wipe - fp) / 0.010) ** 2) * (wipe < 5) * (0 < fp < 1.07)
    img += edge[..., None] * np.array([1.0, 0.82, 0.45])
    sweep = io(prog(t, B["grams"], 1.4)) * (1 - prog(t, B["question"], 0.3))
    if 0 < sweep < 1:
        diag = crop("diag", box, Image.BILINEAR)
        img += np.exp(-((diag - (-1.0 + 2.2 * sweep)) / 0.03) ** 2)[..., None] * fm * np.array([1.0, 0.85, 0.55]) * 0.35
    # heat: red light spill + the carbon warming up
    img += crop("heat", box) * (0.45 * hi) * drawn[..., None]
    warm = crop("warm", box, Image.BILINEAR)
    wv = crop("weave", box)
    wm = np.clip((warm_r(t) - warm) / 0.10, 0, 1) * (0.75 + 0.25 * math.sin(t * LOOP * 9))
    img += (wm * (0.35 + 0.9 * wv))[..., None] * (1 - fm) * np.array([0.9, 0.14, 0.05]) * 0.6
    # exploded view: lift each group out and composite back to front
    k = explode(t)
    if k > 0.001:
        out = np.broadcast_to(paper, img.shape).copy()
        moving = np.isin(part, sum(GIDS, []))
        out[~moving] = img[~moving]
        for gi, ids in enumerate(GIDS):
            m = np.isin(part, ids)
            dx, dy = goff(gi, t, s)
            lay = shift(np.where(m[..., None], img, 0), dx, dy); ms = shift(m.astype(np.float32), dx, dy)[..., None]
            out = out * (1 - ms) + lay * ms
        img = out
        part_vis = part                                            # (element count uses the unexploded ids)
    # blueprint grid, locked to the sheet (moves with the camera)
    vw = box[2] - box[0]
    gx = (box[0] + (np.arange(W) + 0.5) * vw / W) % 60
    gy = (box[1] + (np.arange(H) + 0.5) * vw / W) % 60
    tl = 1.3 * vw / W
    g = np.maximum((gy < tl)[:, None] * 1.0, (gx < tl)[None, :] * 1.0)
    gmaj = (box[0] + (np.arange(W) + 0.5) * vw / W) % 300 < tl * 1.6
    gmaj = np.maximum(gmaj[None, :], ((box[1] + (np.arange(H) + 0.5) * vw / W) % 300 < tl * 1.6)[:, None])
    bgm = (np.abs(img - paper).sum(-1) < 0.02)
    img += ((g * 0.07 + gmaj * 0.08) * bgm)[..., None] * f3(GRIDC)
    img *= 1 - dim(t)
    # overlays: guides for the exploded view, heat rays, sparks
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
    if k > 0.02:
        for p, gi in (((-1.0, 1.36, -0.58), 0), ((1.2, 1.36, -0.58), 0), ((-0.76, 1.1, -0.3), 1),
                      ((-0.76, 0.34, 0.6), 1), ((-0.5, 0.1, 0.2), 2), ((0.95, 0.42, 0.2), 2), ((1.2, 0.3, 0.6), 3)):
            x0, y0 = R.to_screen(box, p); x1, y1 = scr(box, p, t, gi)
            L = math.hypot(x1 - x0, y1 - y0)
            for j in range(int(L // 22)):
                a0, a1 = j * 22 / L, min(1, (j * 22 + 12) / L)
                d.line((x0 + (x1 - x0) * a0, y0 + (y1 - y0) * a0, x0 + (x1 - x0) * a1, y0 + (y1 - y0) * a1),
                       fill=rgba(LINE, 0.75 * k), width=3)
            d.ellipse((x0 - 5, y0 - 5, x0 + 5, y0 + 5), outline=rgba(LINE, 0.75 * k), width=2)
    ra = 1.0 - 0.6 * dim(t) / 0.42
    hw = R.layers()["hitwipe"]
    n_ref = 0
    for si, hi_ in RAYS:
        src, hit = scene.HOT[si], scene.HITS[hi_]
        p0, p1 = scr(box, src, t, 2), scr(box, hit, t)
        wave(gd, p0, p1, t, HEATC, 16, 0.6 * ra); wave(d, p0, p1, t, (255, 120, 80), 5, 0.95 * ra)
        covered = clamp((fp - hw[hi_]) / 0.05)
        if covered > 0:
            n_ref += 1
            nrm = np.array([1.0, 0, 0]) if abs(hit[0] + 0.76) < 0.01 else np.array([0, 0, 1.0])
            p2 = scr(box, reflect(src, hit, nrm), t, 2)
            wave(gd, p1, p2, t, GOLD, 16, 0.55 * covered * ra, frac=covered)
            wave(d, p1, p2, t, (255, 220, 130), 5, 0.95 * covered * ra, frac=covered)
            fl = 1 - prog(t, B["gold"] + hw[hi_] * (B["lined"] + 1.1 - B["gold"]), 0.5)
            if 0 < fl < 1:
                r = 34 * (1 - fl) + 8
                gd.ellipse((p1[0] - r, p1[1] - r, p1[0] + r, p1[1] + r), fill=rgba(GOLD, fl))
    rng = np.random.default_rng(4)
    for i in range(30):                                          # rising sparks
        x0, y0 = rng.random() * W, rng.random() * H
        y = (y0 - H * int(rng.integers(1, 3)) * t / DUR) % H
        x = x0 + 22 * math.sin(t * LOOP * int(rng.integers(2, 5)) + rng.random() * 6.28)
        r = 1.5 + 2.5 * rng.random()
        c = (255, 140, 70) if i % 3 else LINE
        d.ellipse((x - r, y - r, x + r, y + r), fill=rgba(c, 0.8))
    glb = np.asarray(gl.filter(ImageFilter.GaussianBlur(9)), np.float32) / 255
    img += glb[..., :3] * glb[..., 3:] * 1.3
    o = np.asarray(ov, np.float32) / 255
    img = img * (1 - o[..., 3:]) + o[..., :3] * o[..., 3:]
    sm = Image.fromarray(np.uint8(np.clip(img - 0.72, 0, 1) * 255)).resize((W // 4, H // 4), Image.BILINEAR)
    img += np.asarray(sm.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR), np.float32) / 255 * 0.6
    img += np.asarray(sm.filter(ImageFilter.GaussianBlur(18)).resize((W, H), Image.BILINEAR), np.float32) / 255 * 0.6
    yy = np.linspace(-1, 1, H)[:, None]; xx = np.linspace(-1, 1, W)[None, :]
    img *= (1 - 0.3 * np.clip(xx ** 2 * 0.6 + yy ** 2 * 0.5, 0, 1))[..., None]
    im = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255))
    els = hud(im, t, box)
    if info is not None:
        ids, cnt = np.unique(part, return_counts=True)
        info["parts"] = [scene.PARTS[i] for i, c in zip(ids, cnt) if i and c > W * H * 0.002]
        info["overlays"] = els + ["heat rays"] + (["reflected rays"] if n_ref else []) + (["explode guides"] if k > 0.02 else []) + ["sparks"]
    return im


# ---------- annotation layer ----------
PILLS = [  # text, accent, appear, leave, screen xy, 3D anchor
    ("V12 · 6.1 L", LINE, "v12", "gold", (64, 640), (-0.15, 0.64, 0.14)),
    ("INFRARED HEAT", HEATC, "heat", "question+-0.35", (64, 420), (0.02, 0.92, -0.3)),
    ("CARBON FIBRE", LINE, "carbon", "question+-0.35", (330, 860), (0.35, 0.72, -0.58)),
    ("REFLECTED", GOLD, "lined+0.7", "question+-0.35", (420, 530), (-0.5, 0.92, -0.42)),
    ("GOLD FOIL ≈ 16 g", GOLD, "grams", "question+-0.35", (64, 640), (-0.76, 0.62, -0.25)),
]
PILL_SIZE, PILL_H = 58, 84

def callout(d, g, t, idx, text, col, x, y, a, s, target, hero=0.0):
    """Drawing-sheet annotation: numbered balloon, outlined box, leader with arrowhead (draws on)."""
    f = font(PILL_SIZE * s, "MonoExtraBold")
    h = PILL_H * s; bal = h; pad = 18 * s
    w = bal + pad + f.getlength(text) + pad * 1.3
    x1, y1 = x + w, y + h
    k = io(clamp(a * 1.5))
    if target is not None and k > 0.2:
        tx, ty = target
        right = tx > x + w / 2
        sx, sy = (x1 if right else x), y + h / 2
        kk = oc(prog(k, 0.2, 0.8) if k < 1 else 1)
        ex, ey = sx + (tx - sx) * kk, sy + (ty - sy) * kk
        d.line((sx, sy, ex, ey), fill=rgba(col, a), width=3)
        if kk > 0.97:
            ang = math.atan2(ty - sy, tx - sx)
            pts = [(tx, ty), (tx - 22 * math.cos(ang - 0.35), ty - 22 * math.sin(ang - 0.35)),
                   (tx - 22 * math.cos(ang + 0.35), ty - 22 * math.sin(ang + 0.35))]
            d.polygon(pts, fill=rgba(col, a))
    if hero > 0:
        g.rectangle((x - 10, y - 10, x1 + 10, y1 + 10), fill=rgba(GOLD, 0.7 * hero * a))
    xr = x + (x1 - x) * k
    d.rectangle((x, y, xr, y1), fill=rgba(NAVY, 0.88 * a), outline=rgba(col, a), width=3)
    if k > 0.5:
        d.ellipse((x + 8 * s, y + 8 * s, x + bal - 8 * s, y1 - 8 * s), outline=rgba(col, a), width=3)
        d.text((x + bal / 2, y + h / 2), str(idx), font=font(44 * s, "MonoExtraBold"), fill=rgba(col, a), anchor="mm")
        n = int(round(len(text) * clamp(a * 1.6 - 0.3)))
        d.text((x + bal + pad, y + h / 2), text[:n], font=f, fill=rgba(GOLD if col == GOLD else LINE, a), anchor="lm")
    return x1

def words_line(d, x, y, toks, size, t, a, hi_gold=(), spoken=None):
    f = font(size)
    for i, tok in enumerate(toks):
        c = GOLD if tok.strip("?.,").upper() in hi_gold else LINE
        wdt = f.getlength(tok)
        if spoken and spoken(i):
            d.rectangle((x - 4, y + size * 1.02, x + wdt + 4, y + size * 1.12), fill=rgba(GOLD, a))
            c = (255, 255, 255) if c == LINE else c
        d.text((x, y), tok, font=f, fill=rgba(c, a))
        x += f.getlength(tok + " ")

def hud(im, t, box):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(gl)
    els = []
    # drawing-sheet frame + title block (lines only)
    d.rectangle((24, 24, W - 24, H - 24), outline=rgba(LINE, 0.5), width=2)
    d.rectangle((34, 34, W - 34, H - 34), outline=rgba(LINE, 0.25), width=1)
    d.rectangle((W - 420, H - 190, W - 34, H - 34), outline=rgba(LINE, 0.45), width=2)
    for yy_ in (H - 138, H - 86):
        d.line((W - 420, yy_, W - 34, yy_), fill=rgba(LINE, 0.35), width=1)
    d.line((W - 230, H - 138, W - 230, H - 34), fill=rgba(LINE, 0.35), width=1)
    for i in range(0, W, 54):
        d.line((i, 24, i, 36), fill=rgba(LINE, 0.4), width=1)
    # headline
    ha = max(1 - prog(t, B["reveal"] - 0.25, 0.25),
             prog(t, (B["outro"] + B["end"]) / 2, (B["end"] - B["outro"]) / 2 - 0.08) if t >= B["outro"] else 0)
    if t < B["reveal"] - 0.25: ha = 1.0
    if ha > 0:
        sc = Image.new("L", (W, H), 0)
        ImageDraw.Draw(sc).rectangle((0, 190, W, 680), fill=int(170 * ha))
        im.paste(Image.new("RGB", (W, H), NAVY), mask=sc.filter(ImageFilter.GaussianBlur(60)))
        d.text((64, 238), "McLAREN F1 — ENGINE BAY", font=font(58, "MonoExtraBold"), fill=rgba(PALE, ha))
        d.line((64, 312, 64 + 780 * min(1, 0.6 + t / 1.6 if t < B["outro"] else 1), 312), fill=rgba(GOLD, ha), width=4)
        for i, line in enumerate(("WHY IS THERE", "GOLD IN THIS", "ENGINE?")):
            words_line(d, 64, 330 + i * 112, line.split(), 104, t, ha, hi_gold=("GOLD",))
        els += ["kicker", "headline"]
    # callouts
    for idx, (text, col, a0, a1, xy, anchor) in enumerate(PILLS, 1):
        t0, t1 = beat(a0), beat(a1)
        if not (t0 <= t < t1 + 0.3): continue
        a = min(prog(t, t0, 0.35), 1 - prog(t, t1, 0.3))
        s, hero = 1.0, 0.0
        if text.startswith("GOLD FOIL"):
            hero = 1 - io(prog(t, t0 + 1.0, 0.6)); s = 1 + 0.15 * hero
        x1 = callout(d, g, t, idx, text, col, xy[0], xy[1], a, s, scr(box, np.array(anchor), t), hero)
        assert x1 <= SAFE_X1 + 1 and SAFE_Y0 <= xy[1] and xy[1] + PILL_H * s <= SAFE_Y1 + 1, text
        els.append("callout:" + text)
    # captions
    cap = caption(t)
    if cap:
        toks, cur, a = cap
        f = font(64)
        wsum = sum(f.getlength(x + " ") for x in toks) - f.getlength(" ")
        x, y = 64, 1082
        d.rectangle((x - 22, y - 16, x + wsum + 22, y + 96), fill=rgba(NAVY, 0.9 * a), outline=rgba(LINE, 0.7 * a), width=2)
        words_line(d, x, y, toks, 64, t, a, spoken=lambda i: i == cur)
        els.append("caption")
    # poll
    a = min(prog(t, B["question"], 0.3), 1 - prog(t, B["outro"], (B["end"] - B["outro"]) / 2))
    if a > 0.01:
        qi = [i for i, w in enumerate(WORDS) if w["w"].lower() == "would"][0]
        n = 0
        for li, line in enumerate(("WOULD YOU LINE", "YOUR CAR", "WITH GOLD?")):
            toks = line.split()
            kq = oc(prog(t, B["question"] + 0.08 * li, 0.35))
            spoken = (lambda base: (lambda i: WORDS[qi + base + i]["s"] <= t < WORDS[qi + base + i]["e"] + 0.1))(n)
            words_line(d, 64, 330 + li * 112 + 30 * (1 - kq), toks, 96, t, a * kq, hi_gold=("GOLD",), spoken=spoken)
            n += len(toks)
        for j, (lab, x0) in enumerate((("YES", 64), ("NO", 512))):
            kb = ob(prog(t, B["question"] + 0.5 + 0.12 * j, 0.45))
            yy0 = 720 + 40 * (1 - kb)
            wi = WORDS[qi + 7 + 2 * j]
            on = wi["s"] - 0.05 <= t < wi["e"] + 0.35
            if on:
                g.rectangle((x0 - 10, yy0 - 10, x0 + 416, yy0 + 190), fill=rgba(GOLD, 0.8 * a))
            d.rectangle((x0, yy0, x0 + 406, yy0 + 180), fill=rgba(GOLD if on else NAVY, 0.92 * a * kb),
                        outline=rgba(GOLD if j == 0 else LINE, a * kb), width=4)
            d.text((x0 + 203, yy0 + 90), lab, font=font(84), fill=rgba(NAVY if on else (GOLD if j == 0 else LINE), a * kb), anchor="mm")
        els += ["poll question", "poll YES", "poll NO"]
    # tiny tags
    d.text((52, 50), "Yub", font=font(34, "ExtraBold"), fill=rgba(LINE, 0.8))
    if R.PREVIEW:
        tf = font(24, "MonoBold"); tw = tf.getlength("PREVIEW")
        d.rectangle((W - 62 - tw, 50, W - 42, 86), outline=rgba(HEATC, 0.9), width=2)
        d.text((W - 52 - tw, 68), "PREVIEW", font=tf, fill=rgba(HEATC, 0.9), anchor="lm")
    base = im.convert("RGBA")
    base.alpha_composite(gl.filter(ImageFilter.GaussianBlur(14))); base.alpha_composite(ov)
    im.paste(base.convert("RGB"))
    return els + ["tag Yub"] + (["tag PREVIEW"] if R.PREVIEW else [])


def _job(i): return np.asarray(frame(i / FPS)).tobytes()

def video(out, a=0.0, b=None):
    from multiprocessing import Pool
    R.layers(); extra()
    b = DUR if b is None else b
    out = Path(out); wav = out.with_suffix(".wav")
    R.audio(wav)
    n0, n1 = int(round(a * FPS)), int(round(b * FPS))
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-ss", str(a), "-t", str((n1 - n0) / FPS), "-i", str(wav), "-c:v", "libx264", "-preset", "medium",
           "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for k, buf in enumerate(pool.imap(_job, range(n0, n1), chunksize=4)):
            p.stdin.write(buf)
            if k % 120 == 0: print(f"frame {n0 + k}/{n1}", flush=True)
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
        video(sys.argv[2], *(float(x) for x in sys.argv[3:5]))
    elif cmd == "elements":
        for s_ in sys.argv[2:]:
            info = {}; frame(float(s_), info)
            print(f"t={s_}: {len(info['parts'])} 3D parts + {len(info['overlays'])} overlays = "
                  f"{len(info['parts']) + len(info['overlays'])}")
