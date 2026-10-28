"""Easing, springs, keyframe tracks and flight paths.

A Track holds keyframes (t, value[, ease]) and interpolates scalars or tuples.
With smooth=True, positions follow a Catmull-Rom curve through the keys, so a flight path
bends through its waypoints instead of moving in straight lines; the ease named on a key
shapes the timing of the segment that arrives at it (anticipation, overshoot, settle).
"""
import math


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, d): return clamp((t - a) / d) if d > 0 else float(t >= a)
def lerp(a, b, u):
    if isinstance(a, (tuple, list)): return tuple(x + (y - x) * u for x, y in zip(a, b))
    return a + (b - a) * u


def lin(x): return x
def ic(x): return x ** 3
def oc(x): return 1 - (1 - x) ** 3
def io(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def iosine(x): return -(math.cos(math.pi * x) - 1) / 2
def oexpo(x): return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)
def ob(x, c1=1.70158):
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def iback(x, c1=1.70158):
    # anticipation: dips back before going forward
    return (c1 + 1) * x ** 3 - c1 * x ** 2
def oelastic(x):
    if x in (0, 1): return x
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi) / 3) + 1
def hold(x): return 0.0 if x < 1 else 1.0

EASES = dict(lin=lin, ic=ic, oc=oc, io=io, sine=iosine, expo=oexpo, ob=ob, back=iback, elastic=oelastic, hold=hold)


def spring(t, t0, frm, to, w=17.0, damp=5.0):
    """Value snapping from frm to to at t0 with a damped overshoot."""
    if t < t0: return frm
    dt = t - t0
    return to + (frm - to) * math.exp(-dt * damp) * math.cos(dt * w)


def springs(t, base, events):
    """Chain of spring moves: events = [(t0, target, w, damp)], each starting from the previous target."""
    v, frm = base, base
    for t0, to, w, damp in events:
        if t < t0: break
        v = spring(t, t0, frm, to, w, damp); frm = to
    return v


def jelly(t, t0, f=32.0, damp=9.0):
    dt = t - t0
    return math.exp(-dt * damp) * math.sin(dt * f) if dt > 0 else 0.0


def wob(t, t0s, amt=0.1):
    """(sx, sy) squash/stretch pair from jelly wobbles started at each time in t0s."""
    j = amt * sum(jelly(t, a) for a in t0s)
    return 1 + j, 1 - j


def _cr(p0, p1, p2, p3, u):
    u2, u3 = u * u, u * u * u
    return tuple(0.5 * ((2 * b) + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u2 + (-a + 3 * b - 3 * c + d) * u3)
                 for a, b, c, d in zip(p0, p1, p2, p3))


class Track:
    def __init__(self, keys, smooth=False, default_ease='io'):
        self.keys = [(k[0], k[1], k[2] if len(k) > 2 else default_ease) for k in sorted(keys, key=lambda k: k[0])]
        self.smooth = smooth

    def at(self, t):
        ks = self.keys
        if t <= ks[0][0]: return ks[0][1]
        if t >= ks[-1][0]: return ks[-1][1]
        for i in range(len(ks) - 1):
            (t0, v0, _), (t1, v1, e) = ks[i], ks[i + 1]
            if t0 <= t < t1:
                u = EASES[e]((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
                if self.smooth and isinstance(v0, tuple):
                    p0 = ks[i - 1][1] if i > 0 else v0
                    p3 = ks[i + 2][1] if i + 2 < len(ks) else v1
                    return _cr(p0, v0, v1, p3, u)
                return lerp(v0, v1, u)
        return ks[-1][1]

    __call__ = at

    def vel(self, t, dt=1 / 120):
        a, b = self.at(t - dt), self.at(t + dt)
        if isinstance(a, tuple): return tuple((y - x) / (2 * dt) for x, y in zip(a, b))
        return (b - a) / (2 * dt)


class Orbit:
    """Circle (ellipse) path around a centre; angle eased from a0 to a1 (degrees). depth() < 0 means behind."""
    def __init__(self, t0, t1, centre, rx, ry, a0, a1, ease='sine'):
        self.t0, self.t1, self.c, self.rx, self.ry, self.a0, self.a1, self.e = t0, t1, centre, rx, ry, a0, a1, ease

    def angle(self, t): return math.radians(lerp(self.a0, self.a1, EASES[self.e](prog(t, self.t0, self.t1 - self.t0))))
    def at(self, t):
        a = self.angle(t)
        return (self.c[0] + self.rx * math.cos(a), self.c[1] + self.ry * math.sin(a))
    __call__ = at
    def depth(self, t): return math.sin(self.angle(t))   # bottom half of the ellipse is nearer the camera


class Seq:
    """Piecewise motion: [(t_start, fn)], each fn(t) used from its start until the next one."""
    def __init__(self, parts): self.parts = sorted(parts, key=lambda p: p[0])
    def at(self, t):
        fn = self.parts[0][1]
        for t0, f in self.parts:
            if t >= t0: fn = f
        return fn(t) if callable(fn) else fn.at(t)
    __call__ = at
    def vel(self, t, dt=1 / 120):
        a, b = self.at(t - dt), self.at(t + dt)
        return tuple((y - x) / (2 * dt) for x, y in zip(a, b))
