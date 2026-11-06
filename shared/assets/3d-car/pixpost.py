"""Post-process for the 3D-pixel look: ID/light/depth tiles from stage.js -> fixed-palette pixel art.

    from pixpost import post, up, PALETTE
    img = post('f_12.png', xray=0.5)       # 180x320 RGB: flat palette ramps + Bayer dither + navy outlines (+ x-ray shell)
    big = up(img)                          # 1080x1920, every pixel a crisp 6x6 block

Tiles (1440x640): [info | depth | info without shell | depth without shell]; info R = material id (toon.js ID),
G = light / 1.25, B = cool rim. All colours come from RAMPS (32 incl. outline; <= 40 asserted on import).
"""
import numpy as np
from PIL import Image

HEX = lambda s: tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))
OUTLINE = '#0b0c1e'
R_BACK = ['#0d0f24', '#181b38', '#2b3052']
R_SAND = ['#6e5642', '#a8875f', '#c9a676', '#e2c79c']
R_BODY = ['#4a3638', '#a9845f', '#e6c38e', '#fff2d6']
RIMC = '#bfe3e6'
R_GLASS = ['#142a3a', '#2f6672', '#8fd0c4']
R_TYRE = ['#14141f', '#262636', '#3e3e52']
R_METAL = ['#4a4658', '#9d98a6', '#e8e4ea']
R_GLOW = ['#7a2a18', '#e0602a', '#ffb24a', '#ffe08a']
R_TAIL = ['#5a1028', '#b02446', '#ff5a6e']
R_HEAD = ['#2a3878', '#5470c8', '#d8e6ff']
# id -> (ramp, light gain, light offset, takes rim)
RAMPS = {0: (R_BACK, 0, 0, 0), 1: (R_BODY, 1, 0, 1), 2: (R_GLASS, 1, 0, 1), 3: (R_TYRE, 1, 0, 0), 4: (R_METAL, 1.1, 0.05, 1),
         5: (R_TYRE, 0.45, 0, 0), 6: (R_HEAD, 1.1, 0.05, 0), 7: (R_TAIL, 1.1, 0.1, 0), 8: (R_METAL, 1, 0, 1), 9: (R_GLOW, 1.05, 0.08, 0),
         10: (R_SAND, 1, 0, 0), 11: (R_BACK, 1, 0, 0), 12: (R_TAIL, 1.1, 0.1, 0), 13: (R_GLOW, 1.05, 0.15, 0), 14: (R_SAND, 1.05, 0.15, 0),
         15: (R_TYRE, 1.2, 0, 0), 16: (R_BODY, 1.0, 0.3, 1), 17: (R_BACK, 1.3, 0.25, 0), 18: (R_SAND, 0.78, 0, 0), 19: (R_TYRE, 1, 0, 0),
         20: (R_GLOW, 1, 0.1, 0)}
ENV = [0, 10, 11, 18, 19, 20]                       # never outlined (floor, backdrop)
PALETTE = sorted({OUTLINE, RIMC, *R_BACK, *R_SAND, *R_BODY, *R_GLASS, *R_TYRE, *R_METAL, *R_GLOW, *R_TAIL, *R_HEAD})
assert len(PALETTE) <= 40, len(PALETTE)
PAL = np.array([HEX(c) for c in PALETTE], np.uint8)
PI = {c: i for i, c in enumerate(PALETTE)}
BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16
DITHER = 0.3                                         # width of the dithered band between two ramp steps (in steps)
SW, SH = 360, 640                                   # tile size from stage.js
DOWN = 2                                            # pixel-art grid = tile / DOWN (180x320), then scaled 6x
_B = np.tile(BAYER, (SH // DOWN // 4, SW // DOWN // 4))
LUT = np.zeros((256, 8), np.uint8); NLEV = np.ones(256, np.int32); GAIN = np.ones(256); OFF = np.zeros(256); RIM = np.zeros(256, bool)
for i, (r, g, o, rim) in RAMPS.items():
    LUT[i, :len(r)] = [PI[c] for c in r]; LUT[i, len(r):] = PI[r[-1]]; NLEV[i] = len(r); GAIN[i] = g; OFF[i] = o; RIM[i] = rim


def _tiles(path):
    a = np.asarray(Image.open(path).convert('RGB'), np.int32)
    t = [a[:, k * SW:(k + 1) * SW] for k in range(4)]
    return (*_down(t[0], t[1][..., 0] * 256 + t[1][..., 1]), *_down(t[2], t[3][..., 0] * 256 + t[3][..., 1]))


def _down(info, dep, k=DOWN):
    """k x k blocks -> one pixel: the front-most sample wins (solid silhouettes, thin parts stay visible)."""
    h, w = dep.shape[0] // k, dep.shape[1] // k
    d = dep.reshape(h, k, w, k).transpose(0, 2, 1, 3).reshape(h, w, k * k)
    i = info.reshape(h, k, w, k, 3).transpose(0, 2, 1, 3, 4).reshape(h, w, k * k, 3)
    j = d.argmin(-1)[..., None]
    return np.take_along_axis(i, j[..., None], 2)[:, :, 0], np.take_along_axis(d, j, 2)[..., 0]


def _outline(ids, dep):
    """1-px navy line on the near side of depth jumps and part boundaries (floor and backdrop never outlined)."""
    dm = dep / 65535.0 * 40.0
    env = np.isin(ids, ENV); o = np.zeros(ids.shape, bool)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        qi = np.roll(ids, (dy, dx), (0, 1)); qd = np.roll(dm, (dy, dx), (0, 1))
        jump = qd - dm > 0.05 + 0.03 * dm
        part = (qi != ids) & ((qd > dm + 0.004) | ((np.abs(qd - dm) <= 0.004) & (ids < qi)))
        o |= ~env & (jump | part | np.isin(qi, ENV) & (qi != ids))
    sil = np.zeros(ids.shape, bool)                  # second pixel on the outer silhouette (chunkier line, like hand pixel art)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        qi = np.roll(ids, (dy, dx), (0, 1)); qd = np.roll(dm, (dy, dx), (0, 1))
        sil |= env & ~np.isin(qi, ENV) & (dm - qd > 0.05 + 0.03 * qd)
    o |= sil
    o[0, :] = o[-1, :] = o[:, 0] = o[:, -1] = False
    return o


def post(path, xray=0.0):
    info, dep, info2, dep2 = _tiles(path)
    ids, g, rim = info[..., 0], info[..., 1] / 255 * 1.25, info[..., 2] / 255
    o = _outline(ids, dep)
    if xray > 0:                                     # dithered see-through shell: ordered Bayer coverage = 1 - xray
        cover = (dep < dep2 - 3) & (_B < xray)
        ids2 = info2[..., 0]; o2 = _outline(ids2, dep2)
        ids = np.where(cover, ids2, ids); g = np.where(cover, info2[..., 1] / 255 * 1.25, g)
        rim = np.where(cover, info2[..., 2] / 255, rim); o = np.where(cover, o2 | (o & (_B < xray * 0.35)), o)
    v = np.clip((g * GAIN[ids] + OFF[ids] - 0.12) / 0.92, 0, 1)
    lev = np.floor(v * (NLEV[ids] - 1) + 0.5 + (_B - 0.5) * DITHER).astype(np.int32)
    lev = np.clip(lev, 0, NLEV[ids] - 1)
    pi = LUT[ids, lev]
    pi = np.where(RIM[ids] & (rim + (_B - 0.5) * 0.2 > 0.84), PI[RIMC], pi)
    pi = np.where(o, PI[OUTLINE], pi)
    return Image.fromarray(PAL[pi], 'RGB')


def up(img, k=SW * 3 // (SW // DOWN)): return img.resize((img.width * k, img.height * k), Image.NEAREST)   # 180x320 -> 1080x1920 (6x)
