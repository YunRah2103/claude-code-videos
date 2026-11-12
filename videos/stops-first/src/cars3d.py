"""Original 3D hypercar models built from real overall proportions (metres), plus procedural materials.

Local frame: x forward (0 = tail, L = nose), y left, z up. Shapes are original lofted surfaces, not copies:
- CHIRON-like: wide, low, horseshoe-style tall oval front opening, C-shaped side line around a side intake.
- NEVERA-like: smooth cab-forward teardrop with dark canopy, long sloping rear, full-width rear light bar.
"""
import math
import numpy as np
from r3d import grid_faces, grid_normals, smooth_curve, catmull, inpoly, dist_poly, path, norm

# material ids
PAINT, BLACK, GLASS, CHROME, LED, MESH, TYRE, RIM, DISC, CALIPER, LINER, CARBON, TAIL, SEAM, PAINT_D, RIMBLUR = range(16)


def spec(name):
    if name == 'chiron':
        return dict(
            name='CHIRON', L=4.544, axles=(0.90, 3.611), R=(0.355, 0.34), tw=(0.34, 0.28), track=0.86,
            top=[(0, 0.80), (0.06, 0.95), (0.30, 0.99), (0.80, 1.02), (1.30, 1.07), (1.70, 1.16), (2.05, 1.212), (2.40, 1.19),
                 (2.72, 1.07), (3.00, 0.90), (3.40, 0.80), (3.90, 0.70), (4.25, 0.60), (4.47, 0.49), (4.544, 0.40)],
            bot=[(0, 0.36), (0.25, 0.20), (0.6, 0.12), (4.2, 0.11), (4.45, 0.16), (4.544, 0.26)],
            W=[(0, 0.90), (0.15, 0.98), (0.9, 1.019), (1.5, 0.99), (2.1, 0.955), (2.8, 0.975), (3.6, 1.005), (4.2, 0.95),
               (4.45, 0.84), (4.544, 0.66)],
            sh=[(0, 0.80), (0.5, 0.85), (0.9, 0.87), (1.6, 0.81), (2.4, 0.77), (3.0, 0.75), (3.6, 0.71), (4.2, 0.58),
                (4.5, 0.44), (4.544, 0.36)],
            Wt=[(0, 0.76), (0.9, 0.80), (1.4, 0.70), (1.8, 0.56), (2.6, 0.53), (2.9, 0.62), (3.3, 0.80), (4.544, 0.5)],
            fin=(0.25, 1.95, 0.035), mirror=(2.80, 1.00, 0.86), wb_end=(0.10, 0.24))
    return dict(
        name='NEVERA', L=4.75, axles=(1.0, 3.745), R=(0.36, 0.35), tw=(0.315, 0.275), track=0.85,
        top=[(0, 0.74), (0.05, 0.86), (0.25, 0.90), (0.7, 0.95), (1.3, 1.05), (1.9, 1.16), (2.45, 1.208), (2.85, 1.17),
             (3.15, 1.03), (3.45, 0.87), (3.85, 0.74), (4.3, 0.64), (4.6, 0.52), (4.75, 0.40)],
        bot=[(0, 0.30), (0.3, 0.16), (0.7, 0.11), (4.4, 0.11), (4.65, 0.17), (4.75, 0.28)],
        W=[(0, 0.88), (0.2, 0.96), (1.0, 0.993), (1.6, 0.97), (2.4, 0.945), (3.1, 0.965), (3.75, 0.985), (4.35, 0.93),
           (4.6, 0.83), (4.75, 0.62)],
        sh=[(0, 0.81), (0.4, 0.83), (1.0, 0.81), (1.8, 0.77), (2.6, 0.745), (3.2, 0.725), (3.75, 0.70), (4.3, 0.58),
            (4.6, 0.46), (4.75, 0.36)],
        Wt=[(0, 0.80), (0.5, 0.78), (1.2, 0.66), (1.8, 0.56), (2.6, 0.55), (3.1, 0.62), (3.5, 0.78), (4.75, 0.5)],
        fin=None, mirror=(3.22, 0.99, 0.80), wb_end=(0.12, 0.26))


def body_mesh(s, nu=300, nv=96):
    L = s['L']
    f = {k: smooth_curve(s[k]) for k in ('top', 'bot', 'W', 'sh', 'Wt')}
    u = np.linspace(0, 1, nu); xs = L * (0.5 - 0.5 * np.cos(np.pi * u)) * 0.6 + L * u * 0.4
    rr, rf = s['wb_end']
    G = np.zeros((nu, 2 * nv - 2, 3))
    for i, x in enumerate(xs):
        zb, zt, W, zs, Wt = f['bot'](x), f['top'](x), f['W'](x), f['sh'](x), f['Wt'](x)
        Wt = min(Wt, W * 0.95); zs = min(zs, zt - 0.04)
        P = [(0, zb), (0.78 * W, zb), (0.975 * W, zb + 0.05), (W, zb + 0.5 * (zs - zb)), (0.985 * W, zs),
             (Wt + 0.30 * (W - Wt), zs + 0.42 * (zt - zs)), (Wt, zt - 0.05 * (zt - zs) - 0.02), (0.45 * Wt, zt - 0.006), (0, zt)]
        half = catmull(P, nv)
        if s['fin'] and s['fin'][0] < x < s['fin'][1]:
            k = math.sin(math.pi * (x - s['fin'][0]) / (s['fin'][1] - s['fin'][0])) ** 0.5
            half[:, 1] += s['fin'][2] * k * np.exp(-(half[:, 0] / 0.04) ** 2) * (half[:, 1] > zs)
        sec = np.concatenate([half, half[-2:0:-1] * [-1, 1]])           # +y side up, then -y side down
        e = 1.0
        if x < rr: e = math.sqrt(max(0, 1 - ((rr - x) / rr) ** 2))
        if x > L - rf: e = math.sqrt(max(0, 1 - ((x - (L - rf)) / rf) ** 2))
        zc = 0.5 * (zb + zt)
        G[i, :, 0] = x; G[i, :, 1] = sec[:, 0] * (0.35 + 0.65 * e); G[i, :, 2] = zc + (sec[:, 1] - zc) * (0.25 + 0.75 * e)
    ref = np.stack([G[..., 0], np.zeros_like(G[..., 0]), np.full_like(G[..., 0], 0.0)], -1)
    ref[..., 2] = 0.5 * (G[..., 2].max(1, keepdims=True) + G[..., 2].min(1, keepdims=True))
    N = grid_normals(G, ref)
    nvv = G.shape[1]
    F = grid_faces(nu, nvv, wrap_v=True)
    # end caps: fans
    caps = []
    for i0 in (0, nu - 1):
        c = len(G.reshape(-1, 3)) + len(caps)
        caps.append(G[i0].mean(0))
    V = np.concatenate([G.reshape(-1, 3), np.array(caps)])
    Nn = np.concatenate([N.reshape(-1, 3), np.array([[-1, 0, 0], [1, 0, 0]], float)])
    fan = []
    for k, i0 in enumerate((0, nu - 1)):
        ci = nu * nvv + k
        for j in range(nvv):
            a, b = i0 * nvv + j, i0 * nvv + (j + 1) % nvv
            fan.append((ci, a, b))
    F = np.concatenate([F, np.array(fan)])
    return dict(V=V, N=Nn, F=F, Lc=V.copy(), f=f)


def lathe(profile, n=72, a0=0, a1=2 * math.pi):
    """Surface of revolution about the y axis: profile = (k,2) of (radius, y)."""
    a = np.linspace(a0, a1, n)
    r, y = profile[:, 0], profile[:, 1]
    G = np.stack([r[None, :] * np.cos(a)[:, None], np.broadcast_to(y, (n, len(y))), r[None, :] * np.sin(a)[:, None]], -1)
    return G


def mesh_from_grid(G, ref, wrap=False):
    N = grid_normals(G, ref)
    F = grid_faces(G.shape[0], G.shape[1], wrap_v=wrap)
    V = G.reshape(-1, 3)
    return dict(V=V, N=N.reshape(-1, 3), F=F, Lc=V.copy())


def wheel_parts(R, tw, spokes):
    """Wheel in its own frame: axle along y, outboard = +y. Returns tyre, rim face, barrel, disc meshes (local)."""
    Rr = R * 0.70
    a = np.linspace(-math.pi / 2, math.pi / 2, 9)
    prof = [[Rr, -tw / 2 + 0.02], [R - 0.05, -tw / 2], [R - 0.012, -tw / 2 + 0.012], [R, -tw / 2 + 0.05], [R, tw / 2 - 0.05],
            [R - 0.012, tw / 2 - 0.012], [R - 0.05, tw / 2], [Rr + 0.015, tw / 2 - 0.005], [Rr, tw / 2 - 0.02]]
    tyre = lathe(np.asarray(prof, float), 96)
    rr = np.linspace(0.0, Rr, 26)
    face = lathe(np.stack([rr, tw / 2 - 0.035 - 0.05 * (1 - rr / Rr) ** 1.5], 1), 128)
    barrel = lathe(np.array([[Rr - 0.005, tw / 2 - 0.03], [Rr - 0.01, -tw / 2 + 0.02]]), 64)
    disc = lathe(np.stack([np.linspace(0.06, Rr * 0.9, 6), np.full(6, tw / 2 - 0.13)], 1), 64)
    out = {}
    for k, G, ref in (('tyre', tyre, np.zeros(3)), ('face', face, np.array([0, -5.0, 0])),
                      ('barrel', barrel, np.zeros(3)), ('disc', disc, np.array([0, -5.0, 0]))):
        out[k] = mesh_from_grid(G, ref, wrap=False)
    out['Rr'] = Rr
    return out


def ellipsoid(c, r, n=24):
    u = np.linspace(0, math.pi, n); v = np.linspace(0, 2 * math.pi, n)
    G = np.stack([np.outer(np.sin(u), np.cos(v)) * r[0], np.outer(np.sin(u), np.sin(v)) * r[1], np.outer(np.cos(u), np.ones(n)) * r[2]], -1) + c
    return mesh_from_grid(G, np.array(c, float))


def liner(xw, R, y0, y1, n=40):
    a = np.linspace(-0.15, math.pi + 0.15, n)
    G = np.stack([xw + R * np.cos(a)[:, None] * np.ones(6), np.broadcast_to(np.linspace(y0, y1, 6), (n, 6)),
                  R * 0 + R * 1.0 * np.sin(a)[:, None] * np.ones(6)], -1)
    return G


class Car:
    def __init__(self, name):
        self.s = s = spec(name); self.key = name
        self.body = body_mesh(s); self.f = self.body['f']
        self.wheels = [wheel_parts(R, tw, 10 if name == 'chiron' else 5) for R, tw in zip(s['R'], s['tw'])]
        mx = s['mirror'][0]; Wm = float(self.f['W'](mx)); zm = float(self.f['sh'](mx))
        self.extras = [ellipsoid((mx, sg * (Wm + 0.03), zm + 0.075), (0.11, 0.06, 0.045)) for sg in (1, -1)]
        self.arch = [(xw, R + 0.045) for xw, R in zip(s['axles'], s['R'])]
        self.liners = []
        for xw, R in zip(s['axles'], s['R']):
            Wx = float(self.f['W'](xw))
            for sg in (1, -1):
                G = liner(xw, R + 0.045, sg * (Wx - 0.42), sg * (Wx + 0.01))
                G[..., 2] += R
                m = mesh_from_grid(G, np.array([xw, sg * 5.0, R + 5.0]))
                m['N'] = -m['N']; m['cull'] = False
                self.liners.append(m)

    # ---------------------------------------------------------------- body discard (wheel arches)
    def body_discard(self, Lc):
        x, y, z = Lc[:, 0], Lc[:, 1], Lc[:, 2]
        out = np.zeros(len(x), bool)
        W = self.f['W'](x)
        for (xw, Ra), R in zip(self.arch, self.s['R']):
            out |= ((x - xw) ** 2 + (z - R) ** 2 < Ra ** 2) & (np.abs(y) > W - 0.43)
        return out

    # ---------------------------------------------------------------- body materials
    def body_mat(self, Lc, N):
        x, y, z = Lc[:, 0], Lc[:, 1], Lc[:, 2]; ay = np.abs(y)
        nx, ny, nz = N[:, 0], N[:, 1], N[:, 2]; any_ = np.abs(ny)
        f = self.f; m = np.full(len(x), PAINT, np.int8)
        zs, zt, W, Wt, zb = f['sh'](x), f['top'](x), f['W'](x), f['Wt'](x), f['bot'](x)
        side = any_ > 0.35
        m[(z < zb + 0.075) & (nz < 0.3)] = CARBON                                   # sills / underbody edge
        if self.key == 'chiron':
            green = (z > zs + 0.025)
            m[green & (x > 2.60) & (x < 3.02) & (nx > 0.12) & (ay < Wt + 0.12)] = GLASS             # windscreen
            sw = inpoly(x, z, [(2.00, 1.16), (2.35, 1.19), (2.62, 1.14), (2.90, 0.94), (2.82, 0.855), (2.32, 0.84),
                                (2.04, 0.86), (1.94, 0.98)])
            m[green & side & sw] = GLASS
            m[(nz > 0.6) & (x > 1.35) & (x < 1.80) & (ay < 0.36)] = GLASS                        # engine glass
            for xx in np.arange(1.40, 1.80, 0.07):
                m[(nz > 0.6) & (np.abs(x - xx) < 0.006) & (ay < 0.36)] = BLACK
            Cl = path((2.02, 1.15), ((1.62, 1.06), (1.36, 0.56), (1.62, 0.38)), ((1.86, 0.26), (2.60, 0.27), (3.18, 0.30)))
            dC = dist_poly(x, z, Cl)
            intake = inpoly(x, z, [(1.97, 1.09), (1.70, 1.00), (1.52, 0.78), (1.52, 0.55), (1.66, 0.48), (1.74, 0.64),
                                   (1.84, 0.88)])
            m[side & intake] = MESH
            m[side & (dC < 0.032)] = CHROME
            m[side & (np.abs(dC - 0.034) < 0.004)] = SEAM
            m[side & (dist_poly(x, z, [(2.88, 0.84), (2.92, 0.60), (3.02, 0.34)]) < 0.004)] = SEAM   # door cut
            front = (nx > 0.30) & (x > 4.0)
            hs = (ay / 0.20) ** 2.4 + (np.abs(z - 0.40) / 0.23) ** 2.4
            m[front & (hs < 1.0)] = MESH                                               # tall oval / horseshoe grille
            m[front & (hs >= 1.0) & (hs < 1.32)] = CHROME
            for cy in (0.60, 0.74):                                                   # quad LED headlights
                for cz in (0.555, 0.62):
                    m[(x > 4.0) & (nx > 0.1) & (np.abs(ay - cy) < 0.045) & (np.abs(z - cz) < 0.009)] = LED
            hl = (x > 4.0) & (nx > 0.1) & (ay > 0.52) & (ay < 0.82) & (z > 0.51) & (z < 0.665) & (m == PAINT)
            m[hl] = BLACK
            m[front & (ay > 0.46) & (ay < 0.86) & (z > 0.18) & (z < 0.36)] = MESH       # corner intakes
            m[(x > 4.0) & (z < 0.17) & (nz < 0.5)] = CARBON
            rear = (nx < -0.35) & (x < 0.5)
            m[rear & (z > 0.44) & (z < 0.84) & (ay < 0.88)] = MESH
            m[rear & (z >= 0.84) & (z < 0.875) & (ay < 0.86)] = TAIL                       # thin tail light
            m[rear & (z < 0.44)] = CARBON
            m[rear & (z < 0.44) & (np.abs(((ay + 0.06) % 0.14) - 0.07) < 0.006)] = SEAM     # diffuser fins
            m[rear & (np.hypot(ay, z - 0.53) < 0.085)] = CHROME                             # central exhaust
            m[rear & (np.hypot(ay, z - 0.53) < 0.06)] = BLACK
            m[(nz > 0.6) & (x > 0.05) & (x < 0.5) & (np.abs(np.minimum(np.abs(ay - 0.85), np.minimum(np.abs(x - 0.05), np.abs(x - 0.5)))) < 0.005)
              & (ay < 0.86)] = SEAM                                                          # flush rear wing outline
        else:
            green = (z > zs + 0.02)
            m[green & (x > 1.55) & (x < 3.50) & (nz > 0.55) & (ay < Wt * 0.9)] = BLACK            # black roof
            m[green & (x > 2.85) & (x < 3.52) & (nx > 0.12) & (ay < Wt + 0.12)] = GLASS           # windscreen
            sw = inpoly(x, z, [(1.50, 0.89), (1.95, 1.07), (2.45, 1.16), (2.88, 1.12), (3.28, 0.93), (3.44, 0.83),
                                (3.00, 0.795), (2.30, 0.795), (1.80, 0.83)])
            m[green & side & sw] = GLASS
            ch = inpoly(x, z, [(3.30, 0.66), (2.70, 0.64), (2.05, 0.60), (1.78, 0.56), (1.66, 0.44), (1.80, 0.42),
                               (2.40, 0.43), (3.05, 0.45), (3.30, 0.50)])
            m[side & ch] = PAINT_D                                                       # sculpted door channel
            m[side & (dist_poly(x, z, [(3.32, 0.66), (2.70, 0.645), (2.05, 0.605), (1.78, 0.565)]) < 0.006)] = SEAM
            m[side & inpoly(x, z, [(1.80, 0.60), (1.55, 0.62), (1.38, 0.52), (1.42, 0.40), (1.66, 0.40), (1.78, 0.48)])] = MESH
            m[side & (dist_poly(x, z, [(3.34, 0.80), (3.36, 0.55), (3.30, 0.36)]) < 0.004)] = SEAM
            front = (nx > 0.28) & (x > 4.1)
            hl = (x > 4.1) & (nx > 0.05) & (ay > 0.50) & (ay < 0.90) & (np.abs(z - (0.555 + 0.10 * (ay - 0.5))) < 0.022)
            m[hl] = LED
            m[front & (ay < 0.78) & (z > 0.17) & (z < 0.36)] = MESH                          # wide low intake
            m[front & (ay < 0.78) & (np.abs(z - 0.265) < 0.012)] = PAINT
            m[front & (ay > 0.82) & (ay < 0.98) & (z > 0.18) & (z < 0.42)] = MESH
            m[(x > 4.2) & (z < 0.17) & (nz < 0.5)] = CARBON
            rear = (nx < -0.3) & (x < 0.6)
            m[rear & (z > 0.42) & (z < 0.735)] = BLACK
            m[(x < 0.6) & (nx < -0.05) & (z >= 0.735) & (z < 0.772) & (ay < 0.93)] = TAIL      # full-width light bar
            m[rear & (z < 0.42)] = CARBON
            m[rear & (z < 0.42) & (np.abs(((ay + 0.05) % 0.16) - 0.08) < 0.006)] = SEAM
        return m

    def wheel_mat(self, Lc, part, spokes, Rr, blur):
        if part == 'tyre': return np.full(len(Lc), TYRE, np.int8)
        if part == 'barrel': return np.full(len(Lc), LINER, np.int8)
        if part == 'disc': return np.full(len(Lc), DISC, np.int8)
        r = np.hypot(Lc[:, 0], Lc[:, 2]) / Rr
        m = np.full(len(Lc), RIMBLUR if blur > 0.5 else RIM, np.int8)
        m[r < 0.16] = BLACK
        m[(r > 0.94)] = RIM
        return m

    def rim_hole(self, Lc, Rr, spokes):
        r = np.hypot(Lc[:, 0], Lc[:, 2]) / Rr; th = np.arctan2(Lc[:, 2], Lc[:, 0])
        if spokes == 10:
            spoke = np.cos(10 * th) > 0.80 - 0.15 * (1 - r)
        else:
            c = np.cos(5 * th); spoke = (c > 0.30) & ~((c > 0.86) & (r > 0.40) & (r < 0.85))
        return (r > 0.22) & (r < 0.90) & ~spoke
