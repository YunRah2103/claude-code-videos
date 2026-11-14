"""Generic mid-engine rear section, ray-traced once into lit layers (cached in out/).

Analytic primitives (oriented boxes, capped cylinders, capsules) + key-light shadows,
screen-space AO, a studio environment for reflections and procedural textures
(carbon twill, crinkled gold foil, cast alloy, ribbed copper). render.py only blends
these layers per frame, so the 3D look costs nothing per frame.
"""
import hashlib
import numpy as np
from pathlib import Path

PW, PH = 1440, 2560                    # plate (4/3 of the 1080x1920 output)
CAM = dict(pos=(0.80, 2.25, 3.60), look=(-0.12, 0.50, -0.22), vfov=42.0)
F32 = np.float32


# ---------- small numpy helpers ----------
def nrm(v): return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)
def dot(a, b): return (a * b).sum(-1)
def sstep(a, b, x): x = np.clip((x - a) / (b - a), 0, 1); return x * x * (3 - 2 * x)

def rot(axis, deg):
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    return {"x": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]),
            "y": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
            "z": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])}[axis]

def blur(a, r):
    """Separable 3-pass box blur (~gaussian) with edge clamping, any trailing channels."""
    r = int(r)
    if r < 1: return a
    out = a.astype(F32)
    for ax in (0, 1):
        for _ in range(3):
            pad = [(0, 0)] * out.ndim; pad[ax] = (r + 1, r)
            c = np.cumsum(np.pad(out, pad, mode="edge"), axis=ax, dtype=np.float64)
            hi = np.take(c, np.arange(2 * r + 1, c.shape[ax]), axis=ax)
            lo = np.take(c, np.arange(0, c.shape[ax] - 2 * r - 1), axis=ax)
            out = ((hi - lo) / (2 * r + 1)).astype(F32)
    return out

_G = {}
def vnoise(u, v, freq, seed=0):
    """Smooth value noise in [0,1] on a wrapped 256 lattice."""
    g = _G.setdefault(seed, np.random.default_rng(seed).random((256, 256)).astype(F32))
    x, y = u * freq, v * freq
    xi, yi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = x - xi, y - yi
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = g[yi & 255, xi & 255], g[yi & 255, (xi + 1) & 255]
    c, d = g[(yi + 1) & 255, xi & 255], g[(yi + 1) & 255, (xi + 1) & 255]
    return (a + (b - a) * fx) + ((c + (d - c) * fx) - (a + (b - a) * fx)) * fy


# ---------- primitives ----------
class Prim:
    def __init__(self, mat, part, R=None):
        self.mat, self.part = mat, part
        self.R = np.eye(3) if R is None else np.asarray(R, float)

class Box(Prim):
    def __init__(self, lo, hi, mat, part, R=None, c=None):
        super().__init__(mat, part, R)
        lo, hi = np.asarray(lo, float), np.asarray(hi, float)
        self.h = (hi - lo) / 2
        self.c = (lo + hi) / 2 if c is None else np.asarray(c, float)

    def hit(self, o, d):
        oL, dL = (o - self.c) @ self.R, d @ self.R
        with np.errstate(divide="ignore", invalid="ignore"):
            inv = 1.0 / np.where(np.abs(dL) < 1e-9, 1e-9, dL)
            t1, t2 = (-self.h - oL) * inv, (self.h - oL) * inv
        tn, tf = np.minimum(t1, t2), np.maximum(t1, t2)
        tmin, tmax = tn.max(1), tf.min(1)
        ok = (tmax >= tmin) & (tmin > 1e-4)
        k = tn.argmax(1)
        nL = np.zeros_like(oL)
        nL[np.arange(len(k)), k] = -np.sign(dL[np.arange(len(k)), k])
        t = np.where(ok, tmin, np.inf)
        return t, nL @ self.R.T, np.zeros(len(t), bool)

class Cyl(Prim):
    """Capped cylinder along local y. top cap flagged (hollow trumpets, wheel faces)."""
    def __init__(self, c, r, hh, mat, part, R=None):
        super().__init__(mat, part, R)
        self.c, self.r, self.hh = np.asarray(c, float), r, hh

    def hit(self, o, d):
        oL, dL = (o - self.c) @ self.R, d @ self.R
        ox, oy, oz = oL.T; dx, dy, dz = dL.T
        a = dx * dx + dz * dz; b = ox * dx + oz * dz; cc = ox * ox + oz * oz - self.r ** 2
        disc = b * b - a * cc
        with np.errstate(divide="ignore", invalid="ignore"):
            ts = (-b - np.sqrt(np.maximum(disc, 0))) / np.where(a < 1e-12, 1e-12, a)
        ys = oy + ts * dy
        side = (disc > 0) & (np.abs(ys) <= self.hh) & (ts > 1e-4)
        t = np.where(side, ts, np.inf)
        nL = np.stack([ox + ts * dx, np.zeros_like(ox), oz + ts * dz], 1) / self.r
        top = np.zeros(len(t), bool)
        for s in (1.0, -1.0):
            with np.errstate(divide="ignore", invalid="ignore"):
                tc = (s * self.hh - oy) / np.where(np.abs(dy) < 1e-12, 1e-12, dy)
            px, pz = ox + tc * dx, oz + tc * dz
            cap = (px * px + pz * pz <= self.r ** 2) & (tc > 1e-4) & (tc < t)
            t = np.where(cap, tc, t)
            nL[cap] = (0, s, 0)
            if s > 0: top = cap
        top &= np.isfinite(t)
        return t, nL @ self.R.T, top

class Cap(Prim):
    """Capsule a-b radius r (tubes, dampers, cam covers)."""
    def __init__(self, a, b, r, mat, part):
        super().__init__(mat, part)
        self.a, self.b, self.r = np.asarray(a, float), np.asarray(b, float), r

    def hit(self, o, d):
        ba = self.b - self.a; oa = o - self.a
        baba = ba @ ba; bard = d @ ba; baoa = oa @ ba; rdoa = dot(d, oa); oaoa = dot(oa, oa)
        A = baba - bard * bard; B = baba * rdoa - baoa * bard
        C = baba * oaoa - baoa * baoa - self.r ** 2 * baba
        h = B * B - A * C
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (-B - np.sqrt(np.maximum(h, 0))) / np.where(np.abs(A) < 1e-12, 1e-12, A)
        y = baoa + t * bard
        t = np.where((h > 0) & (y > 0) & (y < baba) & (t > 1e-4), t, np.inf)
        for end in (self.a, self.b):
            oc = o - end; b2 = dot(d, oc); c2 = dot(oc, oc) - self.r ** 2; h2 = b2 * b2 - c2
            tc = -b2 - np.sqrt(np.maximum(h2, 0))
            t = np.where((h2 > 0) & (tc > 1e-4) & (tc < t), tc, t)
        p = o + d * np.where(np.isfinite(t), t, 0)[:, None]
        k = np.clip(dot(p - self.a, np.broadcast_to(ba, p.shape)) / baba, 0, 1)
        n = (p - (self.a + k[:, None] * ba)) / self.r
        return t, n, np.zeros(len(t), bool)


# materials
FLOOR, CARBON, ALLOY, COPPER, CHROME, HEADER, RUBBER, RIM, FUEL, DARK, CUT = range(1, 12)
WALLS = (CARBON,)
# part groups (for element counting): name per id
PARTS = ["bg", "floor", "back panel", "bulkhead", "crankcase", "cyl banks", "cam covers",
         "intake trumpets", "exhaust headers", "gearbox", "fuel cell", "wheel", "suspension",
         "coil packs", "frame rails"]
P = {n: i for i, n in enumerate(PARTS)}

def build_scene():
    S = []
    add = S.append
    # chassis floor + frame rails
    add(Box((-1.6, -0.06, -0.75), (1.8, 0.0, 1.3), FLOOR, P["floor"]))
    add(Box((-1.25, 1.36, -0.66), (1.6, 1.42, -0.52), ALLOY, P["frame rails"]))
    add(Box((-0.84, 1.10, -0.6), (-0.72, 1.16, 0.0), ALLOY, P["frame rails"]))
    # carbon body panels: back wall (faces camera) + bulkhead (cut away low at the front)
    add(Box((-1.25, 0.0, -0.66), (1.6, 1.36, -0.58), CARBON, P["back panel"]))
    add(Box((-0.84, 0.0, -0.58), (-0.76, 1.10, 0.02), CARBON, P["bulkhead"]))
    add(Box((-0.84, 0.0, 0.02), (-0.76, 0.34, 0.7), CARBON, P["bulkhead"]))
    # fuel cell behind the bulkhead (seen through the cut)
    add(Cyl((-1.12, 0.42, 0.05), 0.30, 0.55, FUEL, P["fuel cell"], rot("x", 90)))
    for z in (-0.25, 0.1, 0.42):
        add(Cyl((-1.12, 0.42, z), 0.305, 0.025, DARK, P["fuel cell"], rot("x", 90)))
    # V12: crankcase, sump, two banks at 60 degrees
    add(Box((-0.52, 0.08, -0.21), (0.50, 0.36, 0.21), ALLOY, P["crankcase"]))
    add(Box((-0.46, 0.02, -0.16), (0.44, 0.10, 0.16), ALLOY, P["crankcase"]))
    add(Box((-0.60, 0.12, -0.17), (-0.52, 0.62, 0.17), ALLOY, P["crankcase"]))   # timing cover
    for x, r, y in ((-0.645, 0.085, 0.20), (-0.645, 0.05, 0.40)):
        add(Cyl((x, y, 0.04), r, 0.03, RIM, P["crankcase"], rot("z", 90)))
    for s in (1, -1):
        Rb = rot("x", -30 * s)
        up = Rb @ np.array([0, 1, 0.0])
        base = np.array([0, 0.30, 0.0]) + up * 0.2 + np.array([0, 0, 0.04 * s])
        add(Box((-0.5, -0.15, -0.09), (0.5, 0.15, 0.09), ALLOY, P["cyl banks"], Rb, c=base))
        top = base + up * 0.17
        add(Cap(top + (-0.46, 0, 0), top + (0.46, 0, 0), 0.085, COPPER, P["cam covers"]))
        for i in range(6):                                        # coil packs
            cp = top + up * 0.075 + np.array([-0.38 + i * 0.152, 0, 0])
            add(Box((-0.03, -0.015, -0.035), (0.03, 0.015, 0.035), DARK, P["coil packs"], Rb, c=cp))
        out = np.array([0, -np.sin(np.radians(30)), np.cos(np.radians(30))]) * s   # bank outward normal
        for i in range(6):                                        # exhaust headers
            x = -0.38 + i * 0.152
            p0 = base + out * 0.10 + np.array([x, -0.02, 0])
            p1 = p0 + out * 0.10 + np.array([0, -0.07, 0])
            p2 = np.array([0.18 + i * 0.06, 0.13, 0.36 * s])
            p3 = np.array([0.68, 0.11, 0.30 * s])
            for a, b in ((p0, p1), (p1, p2), (p2, p3)):
                add(Cap(a, b, 0.032, HEADER, P["exhaust headers"]))
    for row in (-0.075, 0.075):                                   # intake trumpets in the V
        for i in range(6):
            add(Cyl((-0.38 + i * 0.152, 0.66, row), 0.045, 0.08, CHROME, P["intake trumpets"]))
            add(Cyl((-0.38 + i * 0.152, 0.745, row), 0.056, 0.008, CHROME, P["intake trumpets"]))
    # transaxle + rear suspension + wheel
    add(Box((0.50, 0.06, -0.2), (1.02, 0.42, 0.2), ALLOY, P["gearbox"]))
    add(Cyl((0.92, 0.24, 0.0), 0.22, 0.2, ALLOY, P["gearbox"], rot("x", 90)))
    add(Cap((0.95, 0.30, 0.25), (1.30, 0.33, 0.58), 0.035, RIM, P["suspension"]))
    add(Cap((1.02, 0.2, 0.45), (0.95, 0.62, 0.25), 0.05, COPPER, P["suspension"]))
    add(Cap((0.72, 0.12, 0.2), (1.22, 0.17, 0.55), 0.025, RIM, P["suspension"]))
    add(Cyl((1.34, 0.36, 0.7), 0.36, 0.17, RUBBER, P["wheel"], rot("x", 90)))
    add(Cyl((1.34, 0.36, 0.72), 0.25, 0.17, RIM, P["wheel"], rot("x", 90)))
    return S

# heat sources (header bends) and ray landing points on the carbon panels
HOT = [np.array(p) for p in [(-0.3, 0.38, 0.40), (0.0, 0.33, 0.40), (0.3, 0.26, 0.40),
                              (-0.25, 0.68, 0.0), (0.15, 0.68, 0.0), (0.55, 0.2, 0.36)]]
HITS = [np.array(p) for p in [(-0.55, 1.05, -0.58), (-0.15, 1.18, -0.58), (0.25, 1.10, -0.58),
                               (0.62, 1.00, -0.58), (0.92, 0.88, -0.58), (-0.76, 0.85, -0.25),
                               (-0.76, 0.55, -0.45), (0.45, 0.78, -0.58)]]


# ---------- camera ----------
def basis():
    pos, look = np.array(CAM["pos"], float), np.array(CAM["look"], float)
    f = nrm(look - pos); r = nrm(np.cross(f, [0, 1, 0])); u = np.cross(r, f)
    return pos, f, r, u, np.tan(np.radians(CAM["vfov"]) / 2)

def project(p):
    """World point -> plate pixel (x, y) and depth."""
    pos, f, r, u, th = basis()
    v = np.asarray(p, float) - pos
    z = v @ f
    x = (v @ r) / (z * th) * (PW / PH)
    y = (v @ u) / (z * th)
    return ((x / (PW / PH)) * 0.5 * PH + PW / 2, PH / 2 - y * 0.5 * PH, z)

def rays(y0, y1):
    pos, f, r, u, th = basis()
    ys, xs = np.mgrid[y0:y1, 0:PW].astype(np.float64)
    sx = (xs + 0.5 - PW / 2) / (PH / 2) * th
    sy = (PH / 2 - ys - 0.5) / (PH / 2) * th
    d = nrm(f + sx[..., None] * r + sy[..., None] * u).reshape(-1, 3)
    return np.broadcast_to(pos, d.shape).copy(), d


# ---------- shading ----------
KEY = nrm(np.array([-0.55, 0.95, 0.75])); FILL = nrm(np.array([0.9, 0.35, 0.4]))
RIM_L = nrm(np.array([0.3, 0.6, -1.0]))

def env(r):
    """Studio environment: dark room, overhead softbox, left strip, faint warm floor bounce."""
    y = r[:, 1]
    e = 0.025 + 0.06 * np.clip(y, 0, 1)
    e = e + 3.2 * sstep(0.80, 0.9, y) * sstep(-0.55, -0.2, r[:, 2] * -1 + 0.3 * r[:, 0])
    strip = dot(r, nrm(np.array([-0.85, 0.35, 0.45])))
    e = e + 1.6 * sstep(0.93, 0.97, strip)
    rimb = dot(r, nrm(np.array([0.6, 0.25, -0.75])))
    e = e + 0.9 * sstep(0.9, 0.97, rimb)
    return np.stack([e, e * 0.98, e * 0.95], 1)

ALB = {FLOOR: (0.03, 0.03, 0.034), CARBON: (0.03, 0.03, 0.032), ALLOY: (0.20, 0.205, 0.21),
       COPPER: (0.55, 0.22, 0.09), CHROME: (0.42, 0.43, 0.45), HEADER: (0.10, 0.09, 0.085),
       RUBBER: (0.025, 0.025, 0.027), RIM: (0.22, 0.225, 0.235), FUEL: (0.12, 0.12, 0.125),
       DARK: (0.06, 0.06, 0.065), CUT: (0.4, 0.4, 0.42)}
# (diffuse k, spec power, spec k, env reflect k, metal)
SPEC = {FLOOR: (1, 30, 0.15, 0.05, 0), CARBON: (1, 120, 0.9, 0.10, 0), ALLOY: (1, 25, 0.35, 0.12, 1),
        COPPER: (1, 60, 0.9, 0.55, 1), CHROME: (0.4, 200, 1.6, 0.9, 1), HEADER: (1, 40, 0.4, 0.10, 1),
        RUBBER: (1, 12, 0.1, 0.02, 0), RIM: (1, 50, 0.6, 0.3, 1), FUEL: (1, 18, 0.15, 0.04, 0),
        DARK: (1, 30, 0.25, 0.06, 0), CUT: (1, 20, 0.2, 0.05, 0)}

def wall_uv(P_, N_):
    """Panel coordinates: back wall (x, y), bulkhead (z, y)."""
    side = np.abs(N_[:, 0]) > 0.7
    return np.where(side, P_[:, 2], P_[:, 0]), P_[:, 1], side

def carbon_tex(u, v):
    """2x2 twill: returns (tow is horizontal, cross-tow coordinate 0..1)."""
    w = 0.022
    iu, iv = np.floor(u / w).astype(np.int64), np.floor(v / w).astype(np.int64)
    horiz = ((iu + iv) % 4) < 2
    cross = np.where(horiz, (v / w) % 1, (u / w) % 1)
    return horiz, cross

def foil_height(u, v):
    h = 0.0
    for f, a, s in ((7, 1.0, 11), (17, 0.55, 12), (41, 0.3, 13), (90, 0.12, 14)):
        h = h + a * np.abs(vnoise(u + 3.1, v + 1.7, f, s) * 2 - 1)    # ridged = creases
    return h

def shade(Pp, N, D, mat, part, top, shadow, ao, gold=False):
    """Linear RGB for one chunk. gold=True turns carbon panels into crinkled gold foil."""
    n = len(mat); col = np.zeros((n, 3), F32)
    V = -D
    m_hit = mat > 0
    Nn = N.copy()
    alb = np.zeros((n, 3), F32); spk = np.zeros((n, 5), F32)
    for m in ALB:
        sel = mat == m
        alb[sel] = ALB[m]; spk[sel] = SPEC[m]
    # textures
    sel = mat == ALLOY
    if sel.any():
        g = 0.85 + 0.3 * vnoise(Pp[sel, 0] + Pp[sel, 2], Pp[sel, 1] + Pp[sel, 2] * 0.5, 60, 3)
        alb[sel] *= g[:, None]
    sel = mat == COPPER
    if sel.any():                                         # fins along the cam covers
        fin = 0.5 + 0.5 * np.cos(Pp[sel, 0] * 2 * np.pi / 0.03)
        alb[sel] *= (0.7 + 0.3 * fin)[:, None]
    sel = mat == FLOOR
    if sel.any():
        g = 0.8 + 0.4 * vnoise(Pp[sel, 0], Pp[sel, 2], 9, 5) + 0.12 * vnoise(Pp[sel, 0], Pp[sel, 2], 80, 6)
        alb[sel] *= g[:, None]
    sel = (mat == CHROME) & top                           # hollow trumpet mouths
    alb[sel] = (0.01, 0.01, 0.01); spk[sel] = (1, 10, 0.0, 0.0, 0)
    sel = (mat == RIM) & top & (part == P["wheel"])
    alb[sel] = (0.16, 0.165, 0.17)
    walls = (mat == CARBON)
    cut = walls & (np.abs(N[:, 1]) > 0.9)                 # cut faces of the panels
    alb[cut] = ALB[CUT]; spk[cut] = SPEC[CUT]
    face = walls & ~cut
    weave = np.zeros(n, F32)
    if face.any():
        u, v, side = wall_uv(Pp[face], N[face])
        horiz, cross = carbon_tex(u, v)
        bulge = np.sin(cross * np.pi)
        # tow sheen: horizontal and vertical tows catch the light at different angles
        sweep = 0.5 + 0.5 * np.sin((u * 1.3 - v * 0.9) * 3.0)
        sheen = np.where(horiz, sweep, 1 - sweep) * (0.35 + 0.65 * bulge)
        weave[face] = sheen
        alb[face] = np.array(ALB[CARBON]) * (0.6 + 2.6 * sheen)[:, None]
    if gold and face.any():
        u, v, _ = wall_uv(Pp[face], N[face])
        e = 0.004
        h0 = foil_height(u, v)
        du = (foil_height(u + e, v) - h0) / e; dv = (foil_height(u, v + e) - h0) / e
        nf = N[face].copy()
        side = np.abs(nf[:, 0]) > 0.7
        tu = np.where(side[:, None], np.array([0, 0, 1.0]), np.array([1.0, 0, 0]))
        tv = np.array([0, 1.0, 0])
        k = 0.012
        Nn[face] = nrm(nf - k * (du[:, None] * tu + dv[:, None] * tv))
        alb[face] = (1.0, 0.72, 0.30)
        spk[face] = (0.25, 150, 2.4, 1.0, 1)
    dk, pw, sk, ek, metal = spk.T
    ndl = np.clip(dot(Nn, KEY), 0, 1) * shadow
    diff = alb * (1.25 * ndl[:, None] * np.array([1.0, 0.97, 0.92])
                  + 0.22 * np.clip(dot(Nn, FILL), 0, 1)[:, None] * np.array([0.75, 0.85, 1.0])
                  + (0.10 * (0.55 + 0.45 * Nn[:, 1]) * ao)[:, None])
    H1 = nrm(KEY + V); H3 = nrm(RIM_L + V)
    sp = (sk * np.clip(dot(Nn, H1), 0, 1) ** pw * shadow + 0.5 * sk * np.clip(dot(Nn, H3), 0, 1) ** (pw * 0.5))
    R = 2 * dot(Nn, V)[:, None] * Nn - V
    fres = 0.04 + 0.96 * (1 - np.clip(dot(Nn, V), 0, 1)) ** 5
    tint = np.where(metal[:, None] > 0, alb / np.maximum(alb.max(1, keepdims=True), 1e-3), 1.0)
    refl = env(R) * (ek * np.where(metal > 0, 1.0, fres * 4))[:, None] * tint * (0.35 + 0.65 * ao[:, None])
    col = dk[:, None] * diff + sp[:, None] * tint + refl
    col[~m_hit] = 0
    return col.astype(F32), weave


# ---------- graphic (cel) look ----------
OFF = (0.91, 0.90, 0.87); INKC = (0.055, 0.055, 0.06)
LIME = (0.80, 1.0, 0.10); BLUE = (0.20, 0.38, 1.0)
TOON = {  # light, mid, shadow bands
    FLOOR: ((0.74, 0.74, 0.71), (0.62, 0.62, 0.60), (0.47, 0.47, 0.46)),
    CARBON: ((0.17, 0.17, 0.18), (0.115, 0.115, 0.125), (0.07, 0.07, 0.08)),
    CUT: (LIME, (0.66, 0.86, 0.06), (0.45, 0.6, 0.03)),
    ALLOY: ((0.64, 0.66, 0.68), (0.48, 0.50, 0.53), (0.31, 0.32, 0.35)),
    COPPER: ((0.84, 1.0, 0.22), (0.64, 0.86, 0.06), (0.38, 0.55, 0.02)),
    CHROME: ((0.80, 0.81, 0.83), (0.52, 0.53, 0.56), (0.26, 0.26, 0.28)),
    HEADER: ((0.36, 0.34, 0.34), (0.25, 0.23, 0.23), (0.15, 0.14, 0.14)),
    RUBBER: ((0.13, 0.13, 0.14), (0.09, 0.09, 0.10), (0.06, 0.06, 0.065)),
    RIM: ((0.56, 0.57, 0.59), (0.41, 0.42, 0.44), (0.27, 0.28, 0.30)),
    FUEL: ((0.34, 0.52, 1.0), (0.20, 0.36, 0.92), (0.11, 0.20, 0.62)),
    DARK: ((0.95, 0.95, 0.92), (0.80, 0.80, 0.78), (0.58, 0.58, 0.57)),
}
GOLD_T = ((1.0, 0.84, 0.26), (0.90, 0.63, 0.12), (0.63, 0.40, 0.06))

def toon(Pp, N, D, mat, part, top, shadow, ao, pix, gold=False):
    """Flat 3-band cel shading + hard specular + halftone dots in the shadow band."""
    n = len(mat); col = np.zeros((n, 3), F32)
    m = mat.copy()
    walls = mat == CARBON
    m[walls & (np.abs(N[:, 1]) > 0.9)] = CUT
    face = walls & (m != CUT)
    Nn = N.copy()
    if gold and face.any():
        u, v, _ = wall_uv(Pp[face], N[face]); e = 0.004
        h0 = foil_height(u, v)
        du = (foil_height(u + e, v) - h0) / e; dv = (foil_height(u, v + e) - h0) / e
        side = np.abs(N[face, 0]) > 0.7
        tu = np.where(side[:, None], np.array([0, 0, 1.0]), np.array([1.0, 0, 0]))
        Nn[face] = nrm(N[face] - 0.007 * (du[:, None] * tu + dv[:, None] * np.array([0, 1.0, 0])))
    L = np.clip(dot(Nn, KEY), 0, 1) * shadow * 0.85 + 0.25 * np.clip(dot(Nn, FILL), 0, 1) + 0.12 * ao
    band = np.where(L > 0.58, 0, np.where(L > 0.26, 1, 2))
    for k, tones in TOON.items():
        sel = m == k
        if gold and k == CARBON: sel = sel & ~face
        for b in range(3):
            col[sel & (band == b)] = tones[b]
    if gold:
        for b in range(3): col[face & (band == b)] = GOLD_T[b]
    if face.any() and not gold:                                  # twill: alternate tows lighter
        u, v, _ = wall_uv(Pp[face], N[face]); horiz, cross = carbon_tex(u, v)
        col[face] *= np.where(horiz, 1.35, 0.85)[:, None] * (0.85 + 0.3 * np.sin(cross * np.pi))[:, None]
    col[(mat == CHROME) & top] = INKC
    H1 = nrm(KEY - D)
    sp = np.clip(dot(Nn, H1), 0, 1) ** np.where(face & gold, 60, 90) * shadow
    shiny = np.isin(m, (ALLOY, COPPER, CHROME, RIM, FUEL, HEADER)) | (face & gold)
    col[shiny & (sp > 0.55)] = (0.99, 0.99, 0.96)
    col[face & ~np.bool_(gold) & (sp > 0.7)] = (0.32, 0.32, 0.34)
    # halftone: dot screen in the shadow band (pitch 9 plate px)
    px, py = pix
    cx, cy = (px % 9) - 4, (py % 9) - 4
    dots = (cx * cx + cy * cy) < (2.2 + 1.6 * (1 - ao)) ** 2
    col[(band == 2) & dots & (m != CUT)] *= 0.72
    col[mat == 0] = OFF
    return col


def tonemap(x):
    x = x * 0.72
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    y = np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)
    return y ** (1 / 2.2)


def render(cache):
    """Ray-trace the plate and write every layer render.py needs to `cache` (npz)."""
    S = build_scene()
    n = PW * PH
    T = np.full(n, np.inf, F32); N = np.zeros((n, 3), F32); M = np.zeros(n, np.int8)
    PART = np.zeros(n, np.int8); TOP = np.zeros(n, bool)
    step = 160
    for y0 in range(0, PH, step):
        o, d = rays(y0, min(PH, y0 + step))
        sl = slice(y0 * PW, y0 * PW + len(d))
        t_, n_, m_, p_, tp_ = T[sl].astype(np.float64), N[sl], M[sl], PART[sl], TOP[sl]
        for s in S:
            t, nn, tp = s.hit(o, d)
            w = t < t_
            t_[w] = t[w]; n_[w] = nn[w]; m_[w] = s.mat; p_[w] = s.part; tp_[w] = tp[w]
        T[sl] = t_
    pos, *_ = basis()
    Dall = np.concatenate([rays(y0, min(PH, y0 + step))[1] for y0 in range(0, PH, step)]).astype(F32)
    hit = np.isfinite(T)
    Pp = pos + Dall * np.where(hit, T, 0)[:, None]
    # flip normals that face away (thin caps)
    flip = dot(N, Dall) > 0
    N[flip] *= -1
    # shadows from the key light
    SH = np.ones(n, F32)
    for y0 in range(0, n, step * PW):
        sl = slice(y0, min(n, y0 + step * PW))
        idx = np.nonzero(hit[sl])[0] + y0
        if not len(idx): continue
        o = Pp[idx].astype(np.float64) + N[idx] * 2e-3
        dd = np.broadcast_to(KEY, o.shape).copy()
        occ = np.zeros(len(idx), bool)
        for s in S:
            occ |= np.isfinite(s.hit(o, dd)[0])
        SH[idx] = np.where(occ, 0.0, 1.0)
    depth = np.where(hit, T, 40.0).reshape(PH, PW).astype(F32)
    SH = 0.15 + 0.85 * blur(SH.reshape(PH, PW), 2).reshape(-1)        # soft shadow edge
    # screen-space AO: darker where the surroundings sit closer to camera
    ao = 1 - np.clip((depth - blur(depth, 22)) * 3.0, 0, 1) * 0.75
    ao = ao * (1 - np.clip((depth - blur(depth, 6)) * 8.0, 0, 1) * 0.5)
    ao = ao.reshape(-1).astype(F32)
    base = np.zeros((n, 3), F32); gold = np.zeros((n, 3), F32); weave = np.zeros(n, F32)
    for y0 in range(0, n, step * PW):
        sl = slice(y0, min(n, y0 + step * PW))
        args = (Pp[sl], N[sl], Dall[sl], M[sl], PART[sl], TOP[sl], SH[sl], ao[sl])
        base[sl], weave[sl] = shade(*args)
        gold[sl], _ = shade(*args, gold=True)
    # graphic layers: cel colour + ink outline mask
    ys_, xs_ = np.divmod(np.arange(n), PW)
    toonc = np.zeros((n, 3), F32); toong = np.zeros((n, 3), F32)
    for y0 in range(0, n, step * PW):
        sl = slice(y0, min(n, y0 + step * PW))
        args = (Pp[sl], N[sl], Dall[sl], M[sl], PART[sl], TOP[sl], SH[sl], ao[sl], (xs_[sl], ys_[sl]))
        toonc[sl] = toon(*args); toong[sl] = toon(*args, gold=True)
    P2, D2, N3 = PART.reshape(PH, PW), depth, N.reshape(PH, PW, 3)
    ink = np.zeros((PH, PW), bool)
    for a_, b_ in (((slice(1, None), slice(None)), (slice(None, -1), slice(None))),
                   ((slice(None), slice(1, None)), (slice(None), slice(None, -1)))):
        e_ = ((P2[a_] != P2[b_]) | (np.abs(D2[a_] - D2[b_]) > 0.012 * D2[a_])
              | (((N3[a_] * N3[b_]).sum(-1) < 0.75) & (D2[a_] < 30) & (D2[b_] < 30)))
        ink[a_] |= e_
    ink2 = ink.copy()                                            # dilate to ~3 px
    ink2[1:] |= ink[:-1]; ink2[:-1] |= ink[1:]; ink2[:, 1:] |= ink[:, :-1]; ink2[:, :-1] |= ink[:, 1:]
    # bevel highlight on normal edges (fakes rounded edges)
    N2 = N.reshape(PH, PW, 3)
    edge = np.zeros((PH, PW), F32)
    edge[1:, :] += np.linalg.norm(N2[1:] - N2[:-1], axis=-1)
    edge[:, 1:] += np.linalg.norm(N2[:, 1:] - N2[:, :-1], axis=-1)
    edge = np.clip(blur(np.clip((edge - 0.35) * 3, 0, 1), 1) * 1.6, 0, 1).reshape(-1) * hit
    lit = np.clip(dot(N, KEY), 0, 1) * 0.6 + 0.25
    base += (edge * lit * 0.22)[:, None]
    gold += (edge * lit * 0.22)[:, None]
    # background: charcoal gradient with a soft pool of light behind the panels
    yy, xx = np.mgrid[0:PH, 0:PW]
    bgc = 0.018 + 0.03 * np.exp(-(((xx - PW * 0.45) / (PW * 0.7)) ** 2 + ((yy - PH * 0.35) / (PH * 0.5)) ** 2))
    bgc = bgc.reshape(-1)[:, None] * np.array([1.0, 1.0, 1.05])
    base[~hit] = bgc[~hit]; gold[~hit] = bgc[~hit]
    # heat light: red bounce from the hot headers onto nearby surfaces
    heat = np.zeros((n, 3), F32)
    for hp in HOT[:3] + HOT[5:]:
        L = hp - Pp; dist = np.linalg.norm(L, axis=1)
        heat += (np.clip(dot(N, L / dist[:, None]), 0, 1) / (1 + (dist / 0.28) ** 2))[:, None]
    heat = heat * np.array([1.0, 0.22, 0.06]) * hit[:, None] * 0.55
    # header emission strength (hotter near the ports, mottled)
    em = np.zeros(n, F32)
    hs = M == HEADER
    em[hs] = (0.55 + 0.45 * sstep(0.1, 0.42, Pp[hs, 1])) * (0.75 + 0.5 * vnoise(Pp[hs, 0] * 3, Pp[hs, 1] * 3 + Pp[hs, 2], 9, 21))
    em[hs] *= 0.55 + 0.45 * np.clip(dot(N[hs], -Dall[hs]), 0, 1)
    # panel maps: distance to ray landing points (warming) and foil wrap order
    face = (M == CARBON) & (np.abs(N[:, 1]) < 0.9)
    warm = np.full(n, 9.0, F32); wipe = np.full(n, 9.0, F32)
    pf = Pp[face]
    dmin = np.min([np.linalg.norm(pf - h, axis=1) for h in HITS], axis=0)
    warm[face] = dmin + 0.06 * vnoise(pf[:, 0] + pf[:, 2], pf[:, 1], 14, 31)
    wipe[face] = wrap_order(pf, np.abs(N[face, 0]) > 0.7) + 0.035 * vnoise(pf[:, 0] + pf[:, 2], pf[:, 1], 10, 33)
    diag = ((Pp[:, 0] + Pp[:, 2]) * 0.6 - Pp[:, 1] * 0.4).astype(F32)
    out = dict(base=(tonemap(base) * 255).astype(np.uint8).reshape(PH, PW, 3),
               gold=(tonemap(gold) * 255).astype(np.uint8).reshape(PH, PW, 3),
               heat=np.clip(heat * 255, 0, 255).astype(np.uint8).reshape(PH, PW, 3),
               emis=np.clip(em * 255, 0, 255).astype(np.uint8).reshape(PH, PW),
               weave=np.clip(weave * 255, 0, 255).astype(np.uint8).reshape(PH, PW),
               warm=warm.reshape(PH, PW), wipe=wipe.reshape(PH, PW), diag=diag.reshape(PH, PW),
               depth=depth, part=PART.reshape(PH, PW),
               toon=(np.clip(toonc, 0, 1) * 255).astype(np.uint8).reshape(PH, PW, 3),
               toongold=(np.clip(toong, 0, 1) * 255).astype(np.uint8).reshape(PH, PW, 3),
               ink=(ink2 * 255).astype(np.uint8))
    Path(cache).parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache, **out)
    return out


def wrap_order(p, side):
    """Foil wrap order 0..1: along the bulkhead (front to back), then across the back wall."""
    p = np.atleast_2d(p)
    s = np.where(side, 0.30 * (0.7 - p[:, 2]) / 1.3, 0.30 + 0.70 * (p[:, 0] + 0.76) / 2.36)
    return s + 0.05 * (p[:, 1] - 0.6)


def scene_key():
    return hashlib.sha1(Path(__file__).read_bytes()).hexdigest()[:10]
