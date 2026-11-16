"""2D structure-matched ASCII E92 from the supplied photo. Fixed framing (no zoom/pan/roll).

python ascii_car.py still OUTDIR 0 2.5 4.5
python ascii_car.py video OUT.mp4
Motion: rolling front wheel, sliding perspective floor dots, speed streaks, light sweep, heat glow.
Reuses render.py for timeline, terminal/HUD overlay, glitch/bloom post and the encoder settings.
"""
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import render as RD
import source as SRCM

DUR = 5.0
W, H, FPS, SUB, N = RD.W, RD.H, RD.FPS, RD.SUB, RD.N
CW, CH = 10, 18
COLS, ROWS, Y0 = W // CW, (H - 12) // CH, 6
PRE = RD.PRE
EMA = 0.6
X0, YOFF = 0, 720                    # photo placement (1:1 scale, whole photo width in frame)

# ---------------------------------------------------------------- target luminance (descreened + sharpened)
g = SRCM.SRC.astype(np.float32) / 255
base = cv2.GaussianBlur(g, (0, 0), 3.0)
base = base / np.percentile(base, 99.7)
sharp = np.clip(base + 1.1 * (base - cv2.GaussianBlur(base, (0, 0), 5.0)), 0, 1)
CAR = np.zeros((H, W), np.float32)
CARM = np.zeros((H, W), np.float32)
sh, sw = g.shape
CAR[YOFF:YOFF + sh, X0:X0 + min(sw, W)] = (sharp * SRCM.MASK)[:, :W]
CARM[YOFF:YOFF + sh, X0:X0 + min(sw, W)] = SRCM.MASK[:, :W]
WCX, WCY, WRX, WRY = SRCM.WHEEL[0] + X0, SRCM.WHEEL[1] + YOFF, SRCM.WHEEL[2], SRCM.WHEEL[3]
INTAKE = (SRCM.INTAKE[0] + X0, SRCM.INTAKE[1] + YOFF)
FLOOR0 = SRCM.FLOOR_Y + YOFF
GX, GY = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
EL = ((GX - WCX) / WRX) ** 2 + ((GY - WCY) / WRY) ** 2
INW = EL < 0.97
SPIN = 10 * 2 * math.pi / 5          # 10 spoke periods per loop

# ---------------------------------------------------------------- side view (user's reference sheet, top-right car)
_V = cv2.imread(str(Path(__file__).resolve().parents[1] / 'assets/views_src.png'), cv2.IMREAD_GRAYSCALE)
_C = (955, 10, 2010, 330)                                   # crop: whole car facing left
_sv = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(6, 12)).apply(_V[_C[1]:_C[3], _C[0]:_C[2]])
_sv = (_sv.astype(np.float32) / 255) ** 1.35                 # darker panels, details/highlights stand out
SS = 1040 / (_C[2] - _C[0])
SX0 = (W - 1040) // 2
SY0 = int(round(FLOOR0 - (325 - _C[1]) * SS))               # wheels sit on the same floor line as the front
_sv = cv2.resize(_sv, (1040, int(round(_sv.shape[0] * SS))), interpolation=cv2.INTER_AREA)
_sm = (cv2.GaussianBlur(_sv, (0, 0), 2.0) > 0.03).astype(np.float32)
_sb = cv2.GaussianBlur(_sv, (0, 0), 0.8)
_sb = _sb / np.percentile(_sb[_sm > 0], 99.5)
_ss = np.clip(_sb + 1.1 * (_sb - cv2.GaussianBlur(_sb, (0, 0), 5.0)), 0, 1)
_ss = _ss ** 1.5                                            # darker panels so details separate
_k = np.ones((5, 5), np.uint8)
_ol = cv2.dilate(_sm, _k) - cv2.erode(_sm, _k)              # silhouette outline only
_ss = np.clip(np.maximum(_ss, 0.95 * cv2.GaussianBlur(_ol, (0, 0), 1.0)), 0, 1)
SIDE = np.zeros((H, W), np.float32)
SIDEM = np.zeros((H, W), np.float32)
SIDE[SY0:SY0 + _sv.shape[0], SX0:SX0 + 1040] = _ss * _sm
SIDEM[SY0:SY0 + _sv.shape[0], SX0:SX0 + 1040] = _sm


def side_pt(x, y):
    """reference-sheet pixel -> screen"""
    return SX0 + (x - _C[0]) * SS, SY0 + (y - _C[1]) * SS


SWHEELS = [side_pt(1145, 258), side_pt(1780, 258)]
SWR = 66 * SS
for _cx, _cy in SWHEELS:                                     # lift the dark wheels so spokes read as glyphs
    _d = np.hypot(GX - _cx, GY - _cy)
    SIDE = np.where(_d < SWR, np.clip(SIDE * 2.2, 0, 1), SIDE)
S_INTAKE = side_pt(1035, 224)
S_GILL = side_pt(1262, 180)

# ---------------------------------------------------------------- glyph atlas (10x18) + 5x9 match features
GLYPHS = list(" .,:;'`\"-_~=+*^<>/\\|()[]!il1xvo0O#%@")
FONT = ImageFont.truetype(RD.FONT, 16)


def build_atlas():
    S = 4
    f = ImageFont.truetype(RD.FONT, 16 * S)
    asc, desc = f.getmetrics()
    at = np.zeros((len(GLYPHS), CH, CW), np.float32)
    for i, ch in enumerate(GLYPHS):
        im = Image.new('L', (CW * S, CH * S), 0)
        d = ImageDraw.Draw(im)
        w = d.textlength(ch, font=f)
        d.text(((CW * S - w) / 2, (CH * S - (asc + desc)) / 2), ch, font=f, fill=255)
        at[i] = np.asarray(im, np.float32).reshape(CH, S, CW, S).mean((1, 3)) / 255
    return at


ATLAS = build_atlas()
_AB = np.stack([cv2.GaussianBlur(a, (0, 0), 1.4) for a in ATLAS])            # blurred: fair tone comparison
GF = _AB.reshape(len(GLYPHS), 9, 2, 5, 2).mean((2, 4)).reshape(len(GLYPHS), 45)
GF2 = (GF ** 2).sum(1)
GMEAN = GF.mean(1)
TONE = 40.0                           # weight of the mean-coverage (tone) term vs per-pixel shape term
GAMMA = 0.80                          # lum -> coverage scale (densest glyphs cover ~60%)
SCR = np.array([GLYPHS.index(c) for c in '01x%<>#@'])


def patches(img):
    img = cv2.GaussianBlur(img, (0, 0), 1.4)
    c = img[Y0:Y0 + ROWS * CH, :COLS * CW].reshape(ROWS, 9, 2, COLS, 5, 2).mean((2, 5))
    return c.transpose(0, 2, 1, 3).reshape(ROWS, COLS, 45)


# ---------------------------------------------------------------- per-subframe luminance canvas
def car_canvas(t):
    a = SPIN * t
    ca, sa = math.cos(a), math.sin(a)
    u = (GX - WCX) / WRX
    v = (GY - WCY) / WRY
    mx = np.where(INW, WCX + (u * ca - v * sa) * WRX, GX).astype(np.float32)
    my = np.where(INW, WCY + (u * sa + v * ca) * WRY, GY).astype(np.float32)
    lum = cv2.remap(CAR, mx, my, cv2.INTER_LINEAR)
    # light sweep across the body during the pass (eased, off-car at the loop seam)
    p = RD.sstep(1.55, 3.35, t)
    if 0 < p < 1:
        pos = -250 + 1600 * p
        band = np.exp(-(((GX - pos) + 0.45 * (GY - 900)) / 70) ** 2)
        lum = lum + 0.55 * band * CARM
    # heat: intake + front brake glow
    hl = RD.heat_lvl(t)
    hi = np.exp(-(((GX - INTAKE[0]) / 150) ** 2 + ((GY - INTAKE[1]) / 40) ** 2))
    hb = np.exp(-((np.sqrt(EL) - 0.55) / 0.16) ** 2) * INW
    lum = lum + (hl - 0.2) * (0.6 * hi + 0.35 * hb) * CARM
    return np.clip(lum, 0, 1.2)


def side_canvas(t):
    a = -SPIN * t
    ca, sa = math.cos(a), math.sin(a)
    mx, my = GX.copy(), GY.copy()
    for cx, cy in SWHEELS:
        u, v = GX - cx, GY - cy
        inw = u * u + v * v < SWR * SWR
        mx = np.where(inw, cx + u * ca - v * sa, mx)
        my = np.where(inw, cy + u * sa + v * ca, my)
    return cv2.remap(SIDE, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR)


# ---------------------------------------------------------------- smooth (non-grid) motion layers
ROWSPEC = []                            # perspective floor dot rows: (y, radius, spacing, cycles per loop, alpha)
y = FLOOR0 + 8.0
for k in range(11):
    sc = 1.0 + 0.32 * k
    ROWSPEC.append((y, 1.3 * sc, 15.0 * sc, 36, 0.55 * math.exp(-k / 7)))
    y += 13.0 * sc
STREAKS = [(780 + 37 * i % 380, 120 + (i * 151) % 260, (2 + i % 3), 0.10 + 0.05 * (i % 3)) for i in range(9)]


def motion_layer(t, carm=None):
    """floor dots sliding toward the rear + faint speed streaks; analytic, sub-pixel smooth."""
    out = np.zeros((H, W), np.float32)
    for (yy, r, sp, cyc, al) in ROWSPEC:
        y0, y1 = int(yy - r - 2), int(yy + r + 3)
        shift = sp * cyc * t / DUR                       # whole periods per loop
        xs = np.arange(W, dtype=np.float32)
        dx = ((xs - shift) % sp) - sp / 2
        for yi in range(max(y0, 0), min(y1, H)):
            dd = np.sqrt(dx * dx + (yi - yy) ** 2)
            out[yi] = np.maximum(out[yi], al * np.clip(r - dd + 0.5, 0, 1))
    xs = np.arange(W, dtype=np.float32)
    for (yy, ln, cyc, al) in STREAKS:
        span = W + ln
        head = (cyc * span * t / DUR + yy * 3.1) % span
        tail = np.clip(1 - (head - xs) / ln, 0, 1) * (xs <= head)
        out[YOFF + yy] = np.maximum(out[YOFF + yy], al * tail ** 1.5)
    return out * (1 - (CARM if carm is None else carm))   # behind the car


# ---------------------------------------------------------------- ASCII state
class Matcher:
    def __init__(self):
        self.P = None
        self.gid = np.zeros((ROWS, COLS), np.int32)

    def step(self, lum):
        p = patches(lum)
        self.P = p if self.P is None else EMA * self.P + (1 - EMA) * p
        P = self.P.reshape(-1, 45) * GAMMA
        D = (P ** 2).sum(1)[:, None] - 2 * P @ GF.T + GF2[None]
        D = D + TONE * (P.mean(1)[:, None] - GMEAN[None]) ** 2
        best = D.argmin(1)
        bs = D[np.arange(len(best)), best]
        old = self.gid.reshape(-1)
        os_ = D[np.arange(len(best)), old]
        keep = os_ <= bs * 1.12 + 0.004                   # hysteresis: keep unless clearly worse
        new = np.where(keep, old, best).reshape(ROWS, COLS).astype(np.int32)
        ch = new != self.gid
        self.gid = new
        return ch


def plane_of(gid, inten):
    tiles = ATLAS[gid] * inten[..., None, None]
    return tiles.transpose(0, 2, 1, 3).reshape(ROWS * CH, COLS * CW)


def front_plane(t, fidx, m):
    gid = m.gid.copy()
    inten = 0.62 + 0.45 * np.sqrt(np.clip(m.P.mean(2), 0, 1))
    rng = np.random.default_rng(fidx * 7919 + 13)
    yc = Y0 + (np.arange(ROWS) + .5) * CH
    yw = RD.wipe_y(t)
    rowb = np.where(yc < yw, 0.0, 1.0) if 1.25 < t < 1.65 else np.ones(ROWS)
    inten = inten * (1 - 0.66 * RD.dim(t) * rowb)[:, None]
    if 1.25 < t < 1.65:
        band = ((yc < yw) & (yc > yw - 110))[:, None]
        pick = band & ((gid > 0) | (rng.random(gid.shape) < .2))
        gid = np.where(pick, rng.choice(SCR, gid.shape), gid)
        inten = np.where(pick, 1.15, inten)
    gl = RD.glitch(t)
    if gl > 0.01:
        pick = (gid > 0) & (rng.random(gid.shape) < 0.06 * gl)
        gid = np.where(pick, rng.choice(SCR, gid.shape), gid)
    plane = plane_of(gid, inten)
    if gl > 0.01:                                         # travelling glitch bands
        rr = np.arange(ROWS)
        bandm = (0.5 + 0.5 * np.sin(0.21 * rr - 11 * t) * np.sin(0.07 * rr + 4 * t)) > 0.62
        shift = np.rint(gl * 18 * np.sin(0.9 * rr + 9 * t) * bandm).astype(int)
        for r in np.nonzero(shift)[0]:
            plane[r * CH:(r + 1) * CH] = np.roll(plane[r * CH:(r + 1) * CH], shift[r], 1)
    return plane


def side_plane(m):
    return plane_of(m.gid, 0.62 + 0.45 * np.sqrt(np.clip(m.P.mean(2), 0, 1)))


# ---------------------------------------------------------------- horizontal waterfall (row-coherent, glyphs kept 1:1)
T1, D1 = 1.60, 0.95                  # front -> side
T2, D2 = 3.95, 0.90                  # side -> front
TRAVEL = 0.62                        # share of D each row spends travelling
_RJ = 0.5 + 0.5 * np.sin(np.arange(ROWS) * 2.3)        # smooth-ish per-row variation (static)


def row_offset(t, T, D):
    """conveyor offset (0..W px) per row; rows cascade top -> bottom, C2 smootherstep easing."""
    k = np.arange(ROWS)
    delay = np.clip((k - 40) / 60.0, 0, 1) * (1 - TRAVEL) * D * 0.92 + 0.08 * (1 - TRAVEL) * D * _RJ
    u = np.clip((t - T - delay) / (TRAVEL * D), 0, 1)
    return W * u * u * u * (u * (6 * u - 15) + 10)


def shift_rows(plane, offs):
    """offs: (SUB, ROWS) sub-frame offsets. Crisp glyphs at the mean offset + a short capped motion trail."""
    out = np.zeros_like(plane)
    for r in range(ROWS):
        strip = plane[r * CH:(r + 1) * CH]
        o = offs[:, r]
        dx = int(round(o.mean()))
        if abs(dx) >= W or not strip.any():
            continue
        span = abs(o[-1] - o[0]) * SUB / (SUB - 1)
        if span > 2:
            k = int(min(span, 22)) | 1
            strip = 0.6 * strip + 0.4 * cv2.blur(strip, (k, 1))
        if dx >= 0:
            out[r * CH:(r + 1) * CH, dx:] = strip[:, :W - dx]
        else:
            out[r * CH:(r + 1) * CH, :W + dx] = strip[:, -dx:]
    return out


def conveyor(p_out, p_in, t, T, D):
    subs = [t + (k - 1.5) / (FPS * SUB) for k in range(SUB)]
    o = np.array([row_offset(ts, T, D) for ts in subs])
    return shift_rows(p_out, o) + shift_rows(p_in, o - W)


def compose(t, fidx, ma, mb):
    """returns the ASCII plane for the current phase"""
    if T1 <= t < T1 + D1:
        return conveyor(front_plane(t, fidx, ma), side_plane(mb), t, T1, D1)
    if T1 + D1 <= t < T2:
        return side_plane(mb)
    if T2 <= t < T2 + D2:
        return conveyor(side_plane(mb), front_plane(t, fidx, ma), t, T2, D2)
    return front_plane(t, fidx, ma)


def which_mask(t):
    if T1 + D1 * 0.5 <= t < T2 + D2 * 0.5:
        return SIDEM
    return CARM


# ---------------------------------------------------------------- explanation layer (side view): ASCII airflow + callouts
_top = np.full(W, np.nan, np.float32)
_cols = SIDEM.any(0)
_top[_cols] = SIDEM[:, _cols].argmax(0)
_xs = np.arange(W)
_top = np.interp(_xs, _xs[_cols], _top[_cols])
_top = cv2.GaussianBlur(_top[None], (0, 0), 25)[0]
STREAMS = [(30, 0.85, 9), (64, 0.65, 8), (104, 0.45, 7)]     # (px above roof line, alpha, particles)
G_TILDE, G_GT = GLYPHS.index('~'), GLYPHS.index('>')


def put_glyph(plane, gi, x, y, a):
    x, y = int(round(x - CW / 2)), int(round(y - CH / 2))
    if a <= 0 or x < 0 or y < 0 or x + CW > W or y + CH > plane.shape[0]:
        return
    plane[y:y + CH, x:x + CW] = np.maximum(plane[y:y + CH, x:x + CW], ATLAS[gi] * a)


def explain(t, plane):
    env = RD.sstep(T1 + D1 - 0.05, T1 + D1 + 0.30, t) * (1 - RD.sstep(T2 - 0.30, T2 + 0.05, t))
    if env <= 0:
        return
    for k, (off, al, _) in enumerate(STREAMS):
        sp = 16.0
        shift = (300 + 90 * k) * t                        # px; air streams over the car front -> rear
        x = (np.arange(-2, W // int(sp) + 3) * sp + shift % sp)
        for xi in x:
            y = np.interp(xi, _xs, _top) - off
            dash = 0.5 + 0.5 * math.sin((xi - shift) / 70.0 + k)  # gaps travel with the flow
            edge = min(1.0, xi / 90, (W - xi) / 90)
            put_glyph(plane, G_TILDE, xi, y - Y0, env * al * max(edge, 0) * dash ** 2)
    ix, iy = S_INTAKE
    gx, gy = S_GILL
    for j in range(6):                                 # cool air into the bumper vent
        u = ((j / 6) + 0.9 * t) % 1.0
        put_glyph(plane, G_TILDE, ix - 170 * (1 - u), iy - Y0, env * 0.9 * math.sin(math.pi * u))
    for j in range(6):                                 # hot air out of the fender gill
        u = ((j / 6) + 0.9 * t) % 1.0
        put_glyph(plane, G_GT, gx + 20 + 200 * u, gy - Y0 + 22 * u, env * 0.95 * math.sin(math.pi * u))


F_CALL = ImageFont.truetype(RD.FONT, 50)
CALLS = [('cool air in', 64, 640, S_INTAKE, 2.65), ('hot air out', 470, 760, S_GILL, 2.95)]


def callouts(t, img):
    out = 1 - RD.sstep(T2 - 0.35, T2 - 0.1, t)
    if t < 2.6 or out <= 0:
        return
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for txt, x, y, (px, py), t0 in CALLS:
        a = RD.sstep(t0, t0 + 0.15, t) * out
        if a <= 0:
            continue
        n = int(len(txt) * RD.sstep(t0, t0 + 0.30, t))
        w = d.textlength(txt, font=F_CALL)
        d.rounded_rectangle((x - 20, y - 14, x + w + 24, y + 78), 12, fill=(0, 0, 0, int(190 * a)))
        d.text((x, y), txt[:n] + ('_' if n < len(txt) else ''), font=F_CALL, fill=(255, 255, 255, int(255 * a)))
        p = RD.sstep(t0 + 0.12, t0 + 0.45, t)
        x0, y0 = x + 4, y + 70
        d.line((x0, y0, x0 + w, y0), fill=(255, 255, 255, int(200 * a)), width=2)
        d.line((x0, y0, x0 + (px - x0) * p, y0 + (py - y0) * p), fill=(255, 255, 255, int(200 * a)), width=2)
        if p > 0.98:
            d.ellipse((px - 20, py - 20, px + 20, py + 20), outline=(255, 255, 255, int(220 * a)), width=2)
    arr = np.asarray(lay, np.float32) / 255
    al = arr[..., 3:4]
    img *= 1 - al * 0.92
    img += arr[..., :3] * al


def frames(indices, want):
    ma, mb = Matcher(), Matcher()
    for i in indices:
        t = (i % N) / FPS
        acc = np.zeros((H, W), np.float32)
        acs = np.zeros((H, W), np.float32)
        mot = np.zeros((H, W), np.float32)
        for k in range(SUB):                               # 120 fps internal, 4-sample shutter
            ts = (t + (k - (SUB - 1) / 2) / (FPS * SUB)) % DUR
            acc += car_canvas(ts)
            acs += side_canvas(ts)
            mot += motion_layer(ts, which_mask(t))
        acc /= SUB; acs /= SUB; mot /= SUB
        cha = ma.step(acc)
        chb = mb.step(acs)
        if i not in want:
            continue
        plane = compose(t, i, ma, mb)
        explain(t, plane)
        img = np.zeros((H, W, 3), np.float32)
        img[Y0:Y0 + ROWS * CH, :COLS * CW] = plane[..., None]
        img += (mot * (1 - 0.66 * RD.dim(t)))[..., None]
        if t < 1.7:
            RD.overlay(t, img, np.array(INTAKE))
        callouts(t, img)
        side_on = T1 + D1 <= t < T2
        m, ch = (mb, chb) if side_on else (ma, cha)
        lit = m.gid > 0
        meta = dict(i=int(i), t=t, view='side' if side_on else 'front',
                    flicker=float(ch[lit | ch].mean()) if (lit | ch).any() else 0.0, car_cells=int(lit.sum()))
        yield i, RD.post(t, img), meta


def main():
    if sys.argv[1] == 'still':
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        for stamp in sys.argv[3:]:
            fi = int(round(float(stamp) * FPS)) % N
            for _, rgb, _ in frames(range(fi - PRE, fi + 1), {fi}):
                Image.fromarray(rgb).save(out / f'f_{stamp}.png')
                print('still', stamp, 'frame', fi)
        return
    dst = Path(sys.argv[2]).resolve(); dst.parent.mkdir(parents=True, exist_ok=True)
    master = dst.with_suffix('.master.mkv')
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                           '-r', str(FPS), '-i', '-', '-c:v', 'ffv1', '-pix_fmt', 'yuv444p', str(master)],
                          stdin=subprocess.PIPE)
    metas, t0 = [], time.time()
    for i, rgb, meta in frames(range(-PRE, N), set(range(N))):
        ff.stdin.write(rgb.tobytes()); metas.append(meta)
        if i % 30 == 0:
            print(f'frame {i}/{N} {time.time() - t0:.0f}s', flush=True)
    ff.stdin.close(); assert ff.wait() == 0
    json.dump(metas, open(dst.with_suffix('.frames.json'), 'w'))
    log = str(dst.with_suffix('')) + '_2pass'
    common = ['-c:v', 'libx264', '-preset', 'slow', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-b:v', '7600k',
              '-maxrate', '8000k', '-bufsize', '8000k', '-r', str(FPS), '-g', str(FPS), '-passlogfile', log, '-an']
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(master), *common, '-pass', '1', '-f', 'null', '-'], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(master), *common, '-pass', '2', '-movflags', '+faststart',
                    str(dst)], check=True)
    for p in dst.parent.glob(Path(log).name + '*'):
        p.unlink()
    master.unlink()
    print('wrote', dst, f'{time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
