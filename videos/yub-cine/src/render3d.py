"""Cinematic soft-lit software renderer (numpy): deferred G-buffer raster with perspective-correct, smooth-shaded
triangles and bilinear textures; sun shadow map with soft PCF; screen-space ambient occlusion; hemisphere sky light;
point and spot lights; glossy specular + fresnel sky reflections; additive glow pass (light beams, halos, sprites);
fog; bloom; depth of field; ACES tonemap and grade.
render(scene, cam, env) -> uint8 (H, W, 3)."""
import math
import numpy as np
from PIL import Image
from geo import TEX, WHITE, MATS, GLOW, rgb, P, cat

W, H = 810, 1440                     # internal 3D resolution (upscaled to 1080x1920 by the runner)

class Env:
    def __init__(s, sky_top=(40, 90, 200), sky_hor=(250, 170, 150), ground=(70, 60, 60), sun_dir=(-0.5, 0.6, 0.45),
                 sun=(255, 230, 200), sun_i=2.6, amb_i=0.9, fog=(25, 120), fog_col=None, exposure=1.0, stars=0.0,
                 points=(), spots=(), shadow_size=14.0, shadow_center=None, bloom=0.7, sun_disc=True, sat=1.12, ao=0.9):
        s.sky_top, s.sky_hor, s.ground = rgb(sky_top), rgb(sky_hor), rgb(ground)
        L = np.float32(sun_dir); s.L = L / np.linalg.norm(L); s.sun = rgb(sun) * sun_i; s.amb_i = amb_i
        s.fog = fog; s.fog_col = rgb(fog_col) if fog_col else s.sky_hor; s.exposure = exposure; s.stars = stars
        s.points = points; s.spots = spots; s.shadow_size = shadow_size; s.shadow_center = shadow_center
        s.bloom = bloom; s.sun_disc = sun_disc; s.sat = sat; s.ao = ao

# ---------------------------------------------------------------- sky
_STAR = np.random.default_rng(5)
_STARS = (_STAR.random((H, W)) > 0.9993).astype(np.float32) * _STAR.uniform(0.3, 1.0, (H, W)).astype(np.float32)

def env_color(env, d):
    """Sky radiance for world directions d (..., 3)."""
    y = d[..., 1:2]
    t = np.clip(y, 0, 1) ** 0.55
    sky = env.sky_hor * (1 - t) + env.sky_top * t
    gnd = env.ground * 0.6
    c = np.where(y >= 0, sky, gnd * np.clip(1 + y * 3, 0.3, 1) + sky * np.clip(1 + y * 3, 0, 1) * 0.15)
    if env.sun_disc:
        mu = np.clip((d * env.L).sum(-1, keepdims=True), 0, 1)
        c = c + env.sun * (0.25 * mu ** 8 + 0.6 * mu ** 64 + 6.0 * (mu > 0.9993))
    return c

def _rays(cam):
    f = (H / 2) / math.tan(math.radians(cam.fov) / 2)
    xs = (np.arange(W, dtype=np.float32) + 0.5 - W / 2) / f; ys = -(np.arange(H, dtype=np.float32) + 0.5 - H / 2) / f
    dc = np.stack(np.broadcast_arrays(xs[None, :], ys[:, None], np.float32(-1)), -1)        # camera-space ray (z=-1)
    return dc, f

# ---------------------------------------------------------------- raster
def _to_view(p, cam):
    v = (p.t - cam.eye) @ cam.R.T
    return v

def _clip_near(v, attrs, near):
    d = -v[..., 2]; inside = d > near; keep = inside.all(1)
    part = np.nonzero(inside.any(1) & ~keep)[0]
    out_v = [v[keep]]; out_a = [[a[keep] for a in attrs]]
    nv, na = [], [[] for _ in attrs]
    for i in part:
        poly = []
        for j in range(3):
            a, b = j, (j + 1) % 3
            if inside[i, a]: poly.append(tuple([v[i, a]] + [A[i, a] for A in attrs if A.ndim == 3]))
            if inside[i, a] != inside[i, b]:
                s = (d[i, a] - near) / (d[i, a] - d[i, b])
                poly.append(tuple([v[i, a] + s * (v[i, b] - v[i, a])] + [A[i, a] + s * (A[i, b] - A[i, a]) for A in attrs if A.ndim == 3]))
        for j in range(1, len(poly) - 1):
            tri = (poly[0], poly[j], poly[j + 1])
            nv.append([q[0] for q in tri]); vi = 1
            for ai, A in enumerate(attrs):
                if A.ndim == 3: na[ai].append([q[vi] for q in tri]); vi += 1
                else: na[ai].append(A[i])
    if nv:
        out_v.append(np.float32(nv)); out_a.append([np.asarray(x, dtype=attrs[ai].dtype) for ai, x in enumerate(na)])
    v = np.concatenate(out_v); attrs = [np.concatenate([o[ai] for o in out_a]) for ai in range(len(attrs))]
    return v, attrs

def _bilinear(T, u, v):
    th, tw = T.shape[:2]
    x = u * tw - 0.5; y = v * th - 0.5
    x0 = np.floor(x).astype(np.int32); y0 = np.floor(y).astype(np.int32); fx = (x - x0)[:, None]; fy = (y - y0)[:, None]
    x0m, x1m = x0 % tw, (x0 + 1) % tw; y0m, y1m = y0 % th, (y0 + 1) % th
    return (T[y0m, x0m] * (1 - fx) + T[y0m, x1m] * fx) * (1 - fy) + (T[y1m, x0m] * (1 - fx) + T[y1m, x1m] * fx) * fy

def raster(p, cam, gb=None, additive=False, near=0.05):
    """Rasterise P into G-buffer gb (dict) or, additive, into gb['add'] with depth test."""
    v = _to_view(p, cam)
    v, (uv, nv, c, k, e, m) = _clip_near(v, [p.uv, p.nv, p.c, p.k, p.e, p.m], near)
    d = -v[..., 2]
    f = (H / 2) / math.tan(math.radians(cam.fov) / 2)
    sx = W / 2 + v[..., 0] / d * f; sy = H / 2 - v[..., 1] / d * f
    keep = (sx.max(1) >= 0) & (sx.min(1) < W) & (sy.max(1) >= 0) & (sy.min(1) < H)
    idx = np.nonzero(keep)[0]
    idx = idx[np.argsort(d[idx].min(1))]
    Z = gb["z"]
    for i in idx:
        x0, x1, x2 = sx[i]; y0, y1, y2 = sy[i]
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(area) < 1e-3: continue
        mnx, mxx = int(max(math.floor(min(x0, x1, x2)), 0)), int(min(math.ceil(max(x0, x1, x2)), W - 1))
        mny, mxy = int(max(math.floor(min(y0, y1, y2)), 0)), int(min(math.ceil(max(y0, y1, y2)), H - 1))
        if mnx > mxx or mny > mxy: continue
        X = np.arange(mnx, mxx + 1, dtype=np.float32)[None, :] + 0.5
        Y = np.arange(mny, mxy + 1, dtype=np.float32)[:, None] + 0.5
        w0 = ((x1 - X) * (y2 - Y) - (x2 - X) * (y1 - Y)) / area
        w1 = ((x2 - X) * (y0 - Y) - (x0 - X) * (y2 - Y)) / area
        w2 = 1 - w0 - w1
        msk = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not msk.any(): continue
        dz = d[i]; inv = w0 / dz[0] + w1 / dz[1] + w2 / dz[2]; z = 1 / np.maximum(inv, 1e-9)
        sub = Z[mny:mxy + 1, mnx:mxx + 1]
        if additive: msk &= z < sub + 0.02
        else: msk &= z < sub
        if not msk.any(): continue
        zz = z[msk]; iv = inv[msk]
        b0 = (w0[msk] / dz[0]) / iv; b1 = (w1[msk] / dz[1]) / iv; b2 = 1 - b0 - b1
        if k[i] != WHITE:
            U = b0 * uv[i, 0, 0] + b1 * uv[i, 1, 0] + b2 * uv[i, 2, 0]; Vv = b0 * uv[i, 0, 1] + b1 * uv[i, 1, 1] + b2 * uv[i, 2, 1]
            alb = _bilinear(TEX[k[i]], U, Vv) * c[i]
        else:
            alb = np.broadcast_to(c[i], (len(zz), 3))
        if additive:
            soft = np.clip((sub[msk] - zz) / 0.35, 0, 1)[:, None]
            gb["add"][mny:mxy + 1, mnx:mxx + 1][msk] += alb * e[i] * soft
            continue
        sub[msk] = zz
        n = b0[:, None] * nv[i, 0] + b1[:, None] * nv[i, 1] + b2[:, None] * nv[i, 2]
        gb["n"][mny:mxy + 1, mnx:mxx + 1][msk] = n
        gb["a"][mny:mxy + 1, mnx:mxx + 1][msk] = alb
        gb["e"][mny:mxy + 1, mnx:mxx + 1][msk] = alb * e[i]
        gb["m"][mny:mxy + 1, mnx:mxx + 1][msk] = m[i]

SR = 1536
def shadow_map(p, env, center):
    L = env.L; up = np.float32([0, 1, 0]) if abs(L[1]) < 0.95 else np.float32([1, 0, 0])
    u = np.cross(up, L); u /= np.linalg.norm(u); v = np.cross(L, u)
    S = env.shadow_size; C = np.float32(center)
    t = p.t - C
    lx = (t @ u / S * 0.5 + 0.5) * SR; ly = (t @ v / S * 0.5 + 0.5) * SR; ld = -(t @ L)
    SM = np.full((SR, SR), np.inf, np.float32)
    keep = (lx.max(1) >= 0) & (lx.min(1) < SR) & (ly.max(1) >= 0) & (ly.min(1) < SR)
    for i in np.nonzero(keep)[0]:
        x0, x1, x2 = lx[i]; y0, y1, y2 = ly[i]
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(area) < 1e-4: continue
        mnx, mxx = int(max(math.floor(min(x0, x1, x2)), 0)), int(min(math.ceil(max(x0, x1, x2)), SR - 1))
        mny, mxy = int(max(math.floor(min(y0, y1, y2)), 0)), int(min(math.ceil(max(y0, y1, y2)), SR - 1))
        if mnx > mxx or mny > mxy: continue
        X = np.arange(mnx, mxx + 1, dtype=np.float32)[None, :] + 0.5; Y = np.arange(mny, mxy + 1, dtype=np.float32)[:, None] + 0.5
        w0 = ((x1 - X) * (y2 - Y) - (x2 - X) * (y1 - Y)) / area; w1 = ((x2 - X) * (y0 - Y) - (x0 - X) * (y2 - Y)) / area; w2 = 1 - w0 - w1
        msk = (w0 >= -0.02) & (w1 >= -0.02) & (w2 >= -0.02)
        if not msk.any(): continue
        z = w0 * ld[i, 0] + w1 * ld[i, 1] + w2 * ld[i, 2]
        sub = SM[mny:mxy + 1, mnx:mxx + 1]; msk &= z < sub; sub[msk] = z[msk]
    return SM, u, v, C

_PCF = [(0, 0)] + [(math.cos(a) * r, math.sin(a) * r) for r, n in ((1.3, 6), (2.6, 9)) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]
def shadow_lookup(Pw, SM, u, v, C, env, nrm):
    S = env.shadow_size
    t = Pw - C + nrm * 0.03
    lx = (t @ u / S * 0.5 + 0.5) * SR; ly = (t @ v / S * 0.5 + 0.5) * SR; ld = -(t @ env.L)
    vis = np.zeros(len(Pw), np.float32); bias = 0.03 + 0.02 * S / 14
    for dx, dy in _PCF:
        xi = np.clip((lx + dx).astype(np.int32), 0, SR - 1); yi = np.clip((ly + dy).astype(np.int32), 0, SR - 1)
        vis += (ld <= SM[yi, xi] + bias)
    vis /= len(_PCF)
    out = (lx < 0) | (lx >= SR) | (ly < 0) | (ly >= SR)
    vis[out] = 1.0
    return vis

# ---------------------------------------------------------------- screen-space AO
def ssao(Z, f, radius=0.45):
    z = Z[::2, ::2]; h, w = z.shape; occ = np.zeros_like(z); valid = np.isfinite(z)
    zc = np.where(valid, z, 1e4)
    rpx = np.clip(radius * f / 2 / np.maximum(zc, 0.1), 2, 40)
    dirs = [(math.cos(a), math.sin(a)) for a in np.linspace(0, 2 * math.pi, 10, endpoint=False)]
    yy, xx = np.mgrid[0:h, 0:w]
    for k, (dx, dy) in enumerate(dirs):
        for s in (0.45, 1.0):
            xs = np.clip((xx + dx * rpx * s).astype(np.int32), 0, w - 1); ys = np.clip((yy + dy * rpx * s).astype(np.int32), 0, h - 1)
            zs = zc[ys, xs]; dz = zc - zs
            occ += np.clip(dz / (radius * 0.6), 0, 1) * (dz < radius * 3)
    ao = 1 - occ / (len(dirs) * 2)
    ao = np.where(valid, ao, 1)
    ao = _blur(np.clip(ao, 0, 1)[..., None].astype(np.float32), 2)
    return _resize(ao, W, H)[..., 0]

# ---------------------------------------------------------------- post
def _box1(a, r, ax):
    if r < 1: return a
    pad = [(0, 0)] * a.ndim; pad[ax] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode="edge"), axis=ax, dtype=np.float32)
    n = a.shape[ax]
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=ax); lo = np.take(c, np.arange(0, n), axis=ax)
    return (hi - lo) / (2 * r + 1)

def _blur(img, r):
    """~Gaussian blur (three box passes per axis)."""
    k = max(1, int(round(r / 1.7)))
    for _ in range(3):
        img = _box1(img, k, 0); img = _box1(img, k, 1)
    return img

def _resize(img, w, h):
    return np.stack([np.asarray(Image.fromarray(np.ascontiguousarray(img[..., c], dtype=np.float32), "F").resize((w, h), Image.BILINEAR)) for c in range(img.shape[2])], -1)

def _down_up(img, k, r):
    h, w = img.shape[:2]
    return _resize(_blur(_resize(img, w // k, h // k), r), w, h)

def aces(x):
    return np.clip(x * (2.51 * x + 0.03) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)

# ---------------------------------------------------------------- frame
def render(scene, cam, env, glow=(), sprites=(), shadow_center=None, dof=None):
    p = scene if isinstance(scene, P) else cat([s for s in scene if s is not None])
    solid = p.m != GLOW
    ps = p.copy().keep(solid); pg = p.copy().keep(~solid)
    if glow: pg = cat([pg] + list(glow)) if len(pg.t) else cat(list(glow))
    gb = dict(z=np.full((H, W), np.inf, np.float32), n=np.zeros((H, W, 3), np.float32), a=np.zeros((H, W, 3), np.float32),
              e=np.zeros((H, W, 3), np.float32), m=np.zeros((H, W), np.int8), add=np.zeros((H, W, 3), np.float32))
    raster(ps, cam, gb)
    Z = gb["z"]; geo = np.isfinite(Z)
    dc, f = _rays(cam)
    Rt = cam.R.T
    dirw = dc @ Rt; dirn = dirw / np.linalg.norm(dirw, axis=-1, keepdims=True)
    img = env_color(env, dirn)
    if env.stars: img = img + (_STARS * env.stars)[..., None] * (dirn[..., 1:2] > 0.05)
    if geo.any():
        Pw = cam.eye + dirw[geo] * Z[geo][:, None]
        N = gb["n"][geo]; N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
        V = -dirn[geo]; flip = (N * V).sum(1) < 0; N[flip] *= -1
        A = gb["a"][geo]; Mt = gb["m"][geo].astype(np.int32); mp = MATS[Mt]
        center = shadow_center if shadow_center is not None else (env.shadow_center if env.shadow_center is not None else cam.eye + (cam.R.T @ np.float32([0, 0, -1])) * min(cam.focus, 12))
        SM, su, sv, sc = shadow_map(ps, env, center)
        vis = shadow_lookup(Pw, SM, su, sv, sc, env, N)
        ao = ssao(Z, f)[geo] if env.ao else np.ones(len(N), np.float32)
        ao = 1 - env.ao * (1 - ao)
        ndl = np.clip(N @ env.L, 0, 1)
        hemi = 0.5 + 0.5 * N[:, 1:2]
        amb = (env.sky_top * 0.35 + env.sky_hor * 0.65) * hemi + env.ground * (1 - hemi) * 0.8
        light = amb * env.amb_i * ao[:, None] + env.sun * (ndl * vis)[:, None]
        Hh = env.L + V; Hh /= np.linalg.norm(Hh, axis=1, keepdims=True)
        spec = (np.clip((N * Hh).sum(1), 0, 1) ** mp[:, 1]) * mp[:, 0] * vis
        specc = env.sun[None] * spec[:, None]
        for pos, col, inten, rad in env.points:
            dv = np.float32(pos) - Pw; dist = np.linalg.norm(dv, axis=1) + 1e-6; Ld = dv / dist[:, None]
            att = inten / (1 + (dist / rad) ** 2) * np.clip(1 - dist / (rad * 4), 0, 1)
            light = light + rgb(col)[None] * (np.clip((N * Ld).sum(1), 0, 1) * att)[:, None]
            Hp = Ld + V; Hp /= np.linalg.norm(Hp, axis=1, keepdims=True)
            specc = specc + rgb(col)[None] * ((np.clip((N * Hp).sum(1), 0, 1) ** mp[:, 1]) * mp[:, 0] * att)[:, None]
        for pos, dr, col, inten, ang, rng in env.spots:
            dv = np.float32(pos) - Pw; dist = np.linalg.norm(dv, axis=1) + 1e-6; Ld = dv / dist[:, None]
            dr = np.float32(dr) / np.linalg.norm(dr); cosang = (-Ld * dr).sum(1)
            cone = np.clip((cosang - math.cos(math.radians(ang))) / (1 - math.cos(math.radians(ang)) + 1e-6) * 3, 0, 1)
            att = inten * cone / (1 + (dist / rng) ** 2)
            light = light + rgb(col)[None] * (np.clip((N * Ld).sum(1), 0, 1) * att)[:, None]
        Rv = 2 * (N * V).sum(1, keepdims=True) * N - V
        fres = 0.04 + 0.96 * (1 - np.clip((N * V).sum(1), 0, 1)) ** 5
        refl = env_color(env, Rv) * (mp[:, 2] * (0.25 + 0.75 * fres) * (0.35 + 0.65 * ao))[:, None]
        col = A * light + specc + refl + gb["e"][geo]
        if env.fog:
            fn, ff = env.fog; fa = np.clip((Z[geo] - fn) / (ff - fn), 0, 1)[:, None] ** 1.3 * 0.85
            col = col * (1 - fa) + env.fog_col * fa
        img[geo] = col
    if len(pg.t): raster(pg, cam, gb, additive=True)
    img = img + gb["add"]
    for pos, colr, size, inten in sprites:        # screen-space glow sprites (lamps, LEDs)
        v = (np.float32(pos) - cam.eye) @ cam.R.T; dd = -v[2]
        if dd < 0.1: continue
        x = W / 2 + v[0] / dd * f; y = H / 2 - v[1] / dd * f; r = size * f / dd
        if x < -r or x > W + r or y < -r or y > H + r: continue
        zx, zy = int(min(max(x, 0), W - 1)), int(min(max(y, 0), H - 1))
        if Z[zy, zx] < dd - 0.15: continue
        x0, x1 = int(max(0, x - r * 3)), int(min(W, x + r * 3)); y0, y1 = int(max(0, y - r * 3)), int(min(H, y + r * 3))
        if x0 >= x1 or y0 >= y1: continue
        yy, xx = np.mgrid[y0:y1, x0:x1]; q = np.hypot(xx - x, yy - y) / max(r, 0.5)
        img[y0:y1, x0:x1] += rgb(colr) * (inten * (np.exp(-q * q * 2.5) + 0.25 * np.exp(-q * 0.9)))[..., None]
    img = img * env.exposure
    # depth of field
    if cam.aperture > 0:
        zf = np.where(geo, Z, 1e4)
        coc = np.clip(np.abs(1 / cam.focus - 1 / zf) * cam.aperture, 0, 1)
        bl = _down_up(img, 4, 2.5)
        img = img * (1 - coc[..., None]) + bl * coc[..., None]
    # bloom
    if env.bloom:
        br = np.clip(img - 0.9, 0, 20)
        b1 = _down_up(br, 4, 4); b2 = _down_up(br, 8, 10)
        img = img + (b1 * 0.5 + b2 * 0.5) * env.bloom
    out = aces(img)
    l = out.mean(-1, keepdims=True); out = np.clip(l + (out - l) * env.sat, 0, 1)
    out = out ** (1 / 2.2)
    out = out + (np.random.default_rng(1).random((H, W, 1)).astype(np.float32) - 0.5) / 255
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
