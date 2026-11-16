"""Image-driven car: the supplied halftone photo -> smooth luminance, spinning front wheel, scrolling floor.

Produces the same 7-channel sample buffer the ASCII stage expects:
0 lum 1 spec 2 heat 3 car mask 4 ground 5 edge-material 6 (unused)."""
import math
from pathlib import Path

import cv2
import numpy as np

SRC = cv2.imread(str(Path(__file__).resolve().parents[1] / 'assets/car_src.jpg'), cv2.IMREAD_GRAYSCALE)
SH, SW = SRC.shape                                   # 594 x 1079
FLOOR_Y = 548                                        # below this the photo's own floor is replaced
_g = SRC.astype(np.float32) / 255
LUM = cv2.GaussianBlur(_g, (0, 0), 3.4)              # remove the photo's dot screen, keep shape
LUM = np.clip(LUM / np.percentile(LUM, 99.7), 0, 1) ** 0.85
MASK = (cv2.GaussianBlur(_g, (0, 0), 7.0) > 0.035).astype(np.float32)
MASK[FLOOR_Y:] = 0
LUM = LUM * MASK

WHEEL = (740.0, 450.0, 72.0, 132.0)                  # centre x, y, radius x, radius y (ellipse in photo)
INTAKE = (170.0, 465.0)                              # lower intake (HUD + heat target)
LOOP = 5.0
SPIN = 10 * 2 * math.pi / 5                          # 10 spoke periods (72 deg) per loop
FLOOR_PERIOD = 106.25                                # px; 16 periods per loop at the rolling speed
ROLL_PX = 16 * FLOOR_PERIOD                          # floor travel per loop (near row)
_HOR = 330.0


def sample(mx, my, t, heat_lvl, out):
    """mx, my: source-photo coordinates of every output sample (float32 arrays)."""
    cx, cy, rx, ry = WHEEL
    u = (mx - cx) / rx
    v = (my - cy) / ry
    rr = u * u + v * v
    inw = rr < 0.97
    a = SPIN * t
    ca, sa = math.cos(a), math.sin(a)
    wx = np.where(inw, cx + (u * ca - v * sa) * rx, mx)        # rotate rim (top moves toward the nose)
    wy = np.where(inw, cy + (u * sa + v * ca) * ry, my)
    lum = cv2.remap(LUM, wx, wy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    mask = cv2.remap(MASK, wx, wy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    mask = np.where(inw & (my < cy + ry), 1.0, mask).astype(np.float32)
    # perspective floor: discrete rows, each scrolling a whole number of periods per loop
    floor = (my >= FLOOR_Y) & ~inw
    depth = np.clip((my - _HOR) / (FLOOR_Y + 20 - _HOR), 0.6, 6.0)      # 1 at the car's base
    k = np.floor(np.log(depth / 0.6) / 0.16)
    yk = _HOR + 0.6 * np.exp((k + 0.5) * 0.16) * (FLOOR_Y + 20 - _HOR)
    rowd = depth_k = 0.6 * np.exp((k + 0.5) * 0.16)
    rowp = np.exp(-((my - yk) / (2.2 * rowd + 1.0)) ** 2)
    n = np.maximum(np.rint(16 * depth_k), 1)                            # periods per loop for this row
    per = FLOOR_PERIOD * depth_k
    ph = (mx - 540) / per - n * t / LOOP
    dash = np.clip((np.cos(2 * np.pi * ph) - 0.1) * 2.5, 0, 1)
    contact = 1 - 0.75 * np.exp(-((my - FLOOR_Y) / 20) ** 2) * np.exp(-((mx - 520) / 420) ** 2)
    g = 0.22 * dash * rowp * np.exp(-(depth - 1) / 2.0) * contact
    lum = np.where(floor, g, lum)
    mask = np.where(floor, 0, mask)
    # heat: lower intake + front brake (behind the rim)
    hi = np.exp(-(((mx - INTAKE[0]) / 150) ** 2 + ((my - INTAKE[1]) / 42) ** 2))
    hb = np.exp(-((np.sqrt(rr) - 0.55) / 0.18) ** 2) * inw
    heat = heat_lvl * (0.6 * hi + 0.4 * hb) * mask
    out[0] = lum
    out[1] = np.clip((lum - 0.55) * 2.0, 0, 1)
    out[2] = heat
    out[3] = mask
    out[4] = floor * (g > 0.002)
    out[5] = lum * mask
    out[6] = 0
