"""One lane of the 3D scene: a car on a white blueprint floor, tracked by its own camera.

render_lane(car, st, W, H) -> uint8 (H, W, 3). Rendered at 2x and box-filtered down (anti-aliasing).
st: dict(dist, kmh, pitch, heave, spin, yaw, elev, cam_d, fov, heat, ink, colour)
"""
import math
import numpy as np
from r3d import Cam, raster, norm
import cars3d as C

SSAA = 2
PAPER = np.array([0.985, 0.985, 0.972])
INK = np.array([0.07, 0.07, 0.085])
HEAT = np.array([(30, 60, 220), (0, 190, 230), (40, 200, 90), (250, 225, 40), (250, 130, 20), (230, 30, 30)], float) / 255
KEY = norm(np.array([0.45, -0.75, 0.6]))


def heat_col(v):
    v = np.clip(v, 0, 1) * (len(HEAT) - 1); i = np.clip(v.astype(int), 0, len(HEAT) - 2); f = (v - i)[..., None]
    return HEAT[i] * (1 - f) + HEAT[i + 1] * f


def rot_y(P, a):
    c, s = math.cos(a), math.sin(a)
    return np.stack([P[:, 0] * c + P[:, 2] * s, P[:, 1], -P[:, 0] * s + P[:, 2] * c], 1)


def assemble(car, st):
    """World meshes for the current state. Car centred at x=0; the body pitches about mid-wheelbase."""
    s = car.s; L = s['L']; xm = 0.5 * sum(s['axles'])
    a = math.radians(st['pitch'])
    piv = np.array([xm, 0, 0.35])
    meshes, info = [], []

    def place(m, obj, kind, rigid=True):
        V = m['Lc'] if 'Vl' not in m else m['Vl']
        if rigid:
            W_ = rot_y(V - piv, a) + piv; Nw = rot_y(m['N'], a)
        else:
            W_, Nw = V, m['N']
        W_ = W_ - np.array([xm, 0, -st['heave']]) if rigid else W_
        d = dict(V=W_, N=Nw, F=m['F'], Lc=m['Lc'], obj=obj, cull=m.get('cull', True))
        if 'discard' in m: d['discard'] = m['discard']
        meshes.append(d); info.append(kind)

    b = dict(car.body); b['discard'] = car.body_discard
    place(b, 0, ('body',))
    for e in car.extras: place(e, len(meshes), ('mirror',))
    for ln in car.liners: place(ln, len(meshes), ('liner',))
    spk = 10 if car.key == 'chiron' else 5
    for k, (xw, R) in enumerate(zip(s['axles'], s['R'])):
        wp = car.wheels[k]; tw = s['tw'][k]; Rr = wp['Rr']
        for sg in (-1, 1):
            yw = sg * (float(car.f['W'](xw)) - tw / 2 + 0.015)
            ctr = np.array([xw - xm, yw, R])
            for part in ('tyre', 'face', 'barrel', 'disc'):
                m = wp[part]
                spin = st['spin'] if part != 'disc' else st['spin'] * 0.0 + st['spin']
                V = m['Lc'] * [1, sg, 1]; N = m['N'] * [1, sg, 1]
                c, s_ = math.cos(-spin), math.sin(-spin)
                V = np.stack([V[:, 0] * c - V[:, 2] * s_, V[:, 1], V[:, 0] * s_ + V[:, 2] * c], 1) + ctr
                N = np.stack([N[:, 0] * c - N[:, 2] * s_, N[:, 1], N[:, 0] * s_ + N[:, 2] * c], 1)
                d = dict(V=V, N=N, F=m['F'], Lc=m['Lc'], obj=len(meshes), cull=part != 'barrel')
                if part == 'face' and st['blur'] < 0.5:
                    d['discard'] = (lambda Rr_, sp: (lambda Lc: car.rim_hole(Lc, Rr_, sp)))(Rr, spk)
                meshes.append(d); info.append(('wheel', part, Rr))
            # caliper: fixed arc at the front-top of the disc
            aa = np.linspace(math.radians(25), math.radians(80), 10)
            rr = np.array([Rr * 0.55, Rr * 0.86])
            G = np.stack([rr[None, :] * np.cos(aa)[:, None], np.full((10, 2), (tw / 2 - 0.10)), rr[None, :] * np.sin(aa)[:, None]], -1)
            V = G.reshape(-1, 3) * [1, sg, 1] + ctr
            from r3d import grid_faces
            Nn = np.tile([0, sg, 0.0], (len(V), 1))
            meshes.append(dict(V=V, N=Nn, F=grid_faces(10, 2), Lc=G.reshape(-1, 3), obj=len(meshes), cull=False))
            info.append(('caliper',))
    return meshes, info


def shade(car, info, obuf, lbuf, nbuf, cam, st, colour):
    H, W = obuf.shape
    img = np.zeros((H, W, 3))
    mat = np.full((H, W), -1, np.int16)
    ys, xs = np.nonzero(obuf >= 0)
    if not len(ys): return img, mat
    o = obuf[ys, xs]; Lc = lbuf[ys, xs]; N = nbuf[ys, xs]
    m = np.zeros(len(o), np.int16)
    for oi in np.unique(o):
        sel = o == oi; kind = info[oi]
        if kind[0] == 'body': m[sel] = car.body_mat(Lc[sel], N[sel])
        elif kind[0] == 'mirror': m[sel] = C.PAINT
        elif kind[0] == 'liner': m[sel] = C.LINER
        elif kind[0] == 'caliper': m[sel] = C.CALIPER
        else: m[sel] = car.wheel_mat(Lc[sel], kind[1], 0, kind[2], st['blur'])
    mat[ys, xs] = m
    Vd = -cam.rays(xs.astype(float) + 0.5, ys.astype(float) + 0.5)
    ndv = np.clip(np.sum(N * Vd, 1), 0, 1)
    N = np.where((np.sum(N * Vd, 1) < 0)[:, None], -N, N); ndv = np.abs(np.sum(N * Vd, 1))
    Rf = 2 * ndv[:, None] * N - Vd
    rz = Rf[:, 2]
    env = np.where(rz > 0, 0.25 + 0.75 * np.clip((rz - 0.05) / 0.6, 0, 1) ** 0.8, 0.22) * (1 - 0.75 * np.exp(-(rz / 0.05) ** 2))
    env = env + 0.35 * np.exp(-((Rf[:, 0] - 0.2) / 0.25) ** 2 - ((rz - 0.55) / 0.2) ** 2)    # softbox highlight
    diff = np.clip(N @ KEY, 0, 1); hemi = 0.5 + 0.5 * N[:, 2]
    Hh = norm(KEY + Vd); sp = np.clip(np.sum(N * Hh, 1), 0, 1) ** 90
    fres = 0.04 + 0.96 * (1 - ndv) ** 5
    base = np.array(colour)
    col = np.zeros((len(m), 3))
    def put(k, v):
        s_ = m == k
        if s_.any(): col[s_] = v[s_] if np.ndim(v) == 2 else v
    ao = (0.55 + 0.45 * np.clip((Lc[:, 2] - 0.08) / 0.45, 0, 1))[:, None]
    paint = base[None] * (0.16 + 0.22 * hemi + 0.72 * diff)[:, None] * ao + (env * (0.10 + 0.85 * fres))[:, None] + 0.9 * sp[:, None]
    put(C.PAINT, paint); put(C.PAINT_D, paint * 0.55)
    put(C.GLASS, (0.05 + env * (0.18 + 0.8 * fres) + 0.8 * sp)[:, None] * [0.85, 0.92, 1.0])
    put(C.CHROME, (0.12 + 0.85 * env + 0.5 * sp)[:, None] * [0.95, 0.96, 1.0])
    put(C.BLACK, (0.03 + env * (0.05 + 0.6 * fres) + 0.5 * sp)[:, None] * np.ones(3))
    pat = (np.sin(Lc[:, 0] * 260) + np.sin(Lc[:, 1] * 260) + np.sin(Lc[:, 2] * 260)) > 0.6
    put(C.MESH, (0.03 + 0.10 * pat + 0.05 * diff)[:, None] * np.ones(3))
    put(C.LED, np.array([0.97, 0.98, 1.0]))
    put(C.TAIL, np.array([0.95, 0.12, 0.10]))
    put(C.TYRE, (0.06 + 0.07 * diff + 0.05 * fres)[:, None] * np.ones(3))
    put(C.RIM, (0.40 + 0.25 * diff + 0.35 * env * 0.6 + 0.4 * sp)[:, None] * [0.92, 0.93, 0.96])
    rr = np.hypot(Lc[:, 0], Lc[:, 2])
    put(C.RIMBLUR, (0.30 + 0.12 * diff + 0.05 * np.sin(rr * 120))[:, None] * [0.92, 0.93, 0.96])
    put(C.DISC, (0.30 + 0.20 * diff)[:, None] * np.ones(3))
    put(C.CALIPER, base[None] * (0.6 + 0.6 * diff)[:, None] + 0.1)
    put(C.LINER, np.array([0.05, 0.05, 0.06]))
    weave = ((np.floor(Lc[:, 0] * 120) + np.floor(Lc[:, 2] * 120) + np.floor(Lc[:, 1] * 120)) % 2) * 0.03
    put(C.CARBON, (0.06 + weave + 0.06 * diff + env * 0.25 * fres)[:, None] * np.ones(3))
    put(C.SEAM, INK)
    if st['heat'] > 0:
        L = car.s['L']
        hv = 0.55 * (0.5 + 0.5 * N[:, 0]) + 0.45 * (Lc[:, 0] / L) + 0.1 * N[:, 2]
        hc = heat_col(hv) * (0.55 + 0.45 * (0.3 * hemi + 0.8 * diff))[:, None] + (0.25 * sp)[:, None]
        col = col * (1 - st['heat']) + hc * st['heat']
    img[ys, xs] = np.clip(col, 0, 1)
    return img, mat


def ground(cam, st, car, W, H):
    yy, xx = np.mgrid[0:H, 0:W]
    d = cam.rays(xx.astype(float) + 0.5, yy.astype(float) + 0.5)
    dz = d[..., 2]; hit = dz < -1e-4
    t = np.where(hit, -cam.eye[2] / np.where(hit, dz, -1), 1e4)
    gx = cam.eye[0] + t * d[..., 0]; gy = cam.eye[1] + t * d[..., 1]
    fw = t / cam.f / np.maximum(-dz, 0.08) * 0.9                            # pixel footprint on the floor (m)
    sx = gx + st['dist']
    blur = st['mps'] / 30.0 * 0.8                                          # motion blur along travel (m per frame)

    def lines(u, period, w, extra=0.0):
        dd = np.abs((u + period / 2) % period - period / 2)
        ww = fw + extra
        return np.clip((w + ww - dd) / ww, 0, 1) * np.minimum(1, w / ww * 2.5 + 0.0) if True else 0

    g = np.zeros((H, W))
    g = np.maximum(g, 0.22 * lines(sx, 1.0, 0.012, blur))
    g = np.maximum(g, 0.22 * lines(gy, 1.0, 0.012))
    g = np.maximum(g, 0.45 * lines(sx, 5.0, 0.02, blur))
    g = np.maximum(g, 0.45 * lines(gy, 5.0, 0.02))
    col = PAPER[None, None] * (1 - g[..., None]) + np.array([0.55, 0.66, 0.82]) * g[..., None]
    lane = np.zeros((H, W))
    for ly in (-2.0, 2.0):
        dash = (np.clip(((sx % 6.0) - 3.0) / (0.05 + blur), -1, 1) * 0.5 + 0.5)
        lane = np.maximum(lane, np.clip((0.06 + fw - np.abs(gy - ly)) / fw, 0, 1) * np.maximum(dash, min(1, blur / 3)))
    col = col * (1 - 0.9 * lane[..., None]) + INK * 0.9 * lane[..., None]
    # contact shadow
    s = car.s; L = s['L']; hw = float(car.f['W'](L / 2))
    qx = np.abs(gx) - (L / 2 - 0.25); qy = np.abs(gy) - (hw - 0.25)
    sd = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0)
    sh = 0.32 * np.exp(-np.maximum(sd, 0) / 0.22) * np.clip(0.6 - sd, 0, 1)
    xm = 0.5 * sum(s['axles'])
    for xw in s['axles']:
        for sg in (-1, 1):
            sh = np.maximum(sh, 0.55 * np.exp(-((gx - (xw - xm)) / 0.22) ** 2 - ((gy - sg * (hw - 0.15)) / 0.14) ** 2))
    col = col * (1 - sh[..., None])
    fog = np.clip((t - 14) / 30, 0, 1)[..., None]
    col = col * (1 - fog) + PAPER * fog
    col[~hit] = PAPER
    return col


def ink_lines(depth, mat, obuf, nbuf):
    H, W = depth.shape
    e = np.zeros((H, W), bool); sil = np.zeros((H, W), bool)
    dpt = np.where(np.isfinite(depth), depth, 1e4)
    for dy, dx in ((0, 1), (1, 0), (1, 1)):
        a = dpt[:H - dy, :W - dx]; b = dpt[dy:, dx:]
        dz = np.abs(a - b) > 0.04 * np.minimum(a, b) + 0.02
        mm = mat[:H - dy, :W - dx] != mat[dy:, dx:]
        nn = np.sum(nbuf[:H - dy, :W - dx] * nbuf[dy:, dx:], -1) < 0.55
        valid = (obuf[:H - dy, :W - dx] >= 0) | (obuf[dy:, dx:] >= 0)
        s_ = dz & valid; k = (mm | nn) & valid
        sil[:H - dy, :W - dx] |= s_; sil[dy:, dx:] |= s_
        e[:H - dy, :W - dx] |= k; e[dy:, dx:] |= k
    s2 = sil.copy()
    s2[1:] |= sil[:-1]; s2[:, 1:] |= sil[:, :-1]
    return s2, e


def render_lane(car, st, W, H):
    w, h = W * SSAA, H * SSAA
    yaw, el, dist = math.radians(st['yaw']), math.radians(st['elev']), st['cam_d']
    tgt = np.array([st.get('tx', 0.0), 0.0, 0.55])
    eye = tgt + dist * np.array([math.sin(yaw) * math.cos(el), -math.cos(yaw) * math.cos(el), math.sin(el)])
    cam = Cam(eye, tgt, st['fov'], w, h)
    meshes, info = assemble(car, st)
    depth, obuf, lbuf, nbuf = raster(meshes, cam, w, h)
    img = ground(cam, st, car, w, h)
    cimg, mat = shade(car, info, obuf, lbuf, nbuf, cam, st, st['colour'])
    on = obuf >= 0
    img[on] = cimg[on]
    sil, inner = ink_lines(depth, mat, obuf, nbuf)
    ink = st['ink']
    if ink < 1:                                                    # draw-on sweep across the screen
        sweep = np.clip((np.arange(w)[None, :] / w - ink * 1.25 + 0.25) / 0.08, 0, 1)
        k = (1 - sweep)
    else: k = 1.0
    a = (np.maximum(sil * 1.0, inner * 0.85) * k)[..., None]
    img = img * (1 - a) + INK * a
    img = img.reshape(H, SSAA, W, SSAA, 3).mean((1, 3))
    return (np.clip(img, 0, 1) ** (1 / 1.0) * 255).astype(np.uint8)
