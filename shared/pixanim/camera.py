"""Shot camera: keyframed framing (centre x, centre y, zoom), optional follow target, punch-in kicks and shake.

World and screen share the canvas size; zoom >= 1 frames a region of the world. The view is clamped to the
world so edges never show, which also keeps pixels crisp (NEAREST resampling).
"""
import math
from PIL import Image
from .motion import Track, prog, io


class Camera:
    def __init__(self, w, h, keys, kicks=(), shakes=(), follow=None, clamp_view=True):
        """keys: [(t, (cx, cy, z)[, ease])]; follow: [(t0, t1, fn(t)->(x, y), weight)] blends framing toward a moving target;
        kicks: [(t, amount, x, y)] instant zoom toward a point that eases back; shakes: [(t, dur, amp)]."""
        self.w, self.h = w, h
        self.track = Track(keys, smooth=True)
        self.kicks, self.shakes, self.follow, self.clamp_view = list(kicks), list(shakes), list(follow or ()), clamp_view

    def at(self, t):
        cx, cy, z = self.track.at(t)
        for t0, t1, fn, wgt in self.follow:
            if t0 - 0.3 <= t < t1 + 0.3:
                k = wgt * io(prog(t, t0 - 0.3, 0.3)) * (1 - io(prog(t, t1, 0.3)))
                fx, fy = fn(t)
                cx += (fx - cx) * k; cy += (fy - cy) * k
        for a, amt, px, py in self.kicks:
            if a <= t < a + 0.7:
                k = math.exp(-(t - a) * 9)
                z *= 1 + amt * k
                cx += (px - cx) * k * 0.5; cy += (py - cy) * k * 0.5
        sx = sy = 0.0
        for a, d, amp in self.shakes:
            if a <= t < a + d:
                k = (1 - (t - a) / d) ** 2
                sx += amp * k * math.sin((t - a) * 90); sy += amp * k * math.cos((t - a) * 77)
        z = max(1.0, z) if self.clamp_view else z
        if self.clamp_view:
            hw, hh = self.w / (2 * z), self.h / (2 * z)
            cx = min(max(cx, hw), self.w - hw); cy = min(max(cy, hh), self.h - hh)
        return cx, cy, z, sx, sy

    def apply(self, img, t, fill=(0, 0, 0)):
        cx, cy, z, sx, sy = self.at(t)
        x0 = cx - self.w / (2 * z) - sx / z; y0 = cy - self.h / (2 * z) - sy / z
        return img.transform((self.w, self.h), Image.AFFINE, (1 / z, 0, x0, 0, 1 / z, y0), resample=Image.NEAREST, fillcolor=fill)

    def to_screen(self, t, x, y):
        cx, cy, z, sx, sy = self.at(t)
        return (x - cx) * z + self.w / 2 + sx, (y - cy) * z + self.h / 2 + sy

    def to_world(self, t, x, y):
        cx, cy, z, sx, sy = self.at(t)
        return (x - self.w / 2 - sx) / z + cx, (y - self.h / 2 - sy) / z + cy
