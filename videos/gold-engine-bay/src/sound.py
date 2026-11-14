"""Sound design for the brief cut (no music: the music bed is added later by the editor).

All cues are synthesised and keyed to timing.json beats, so they follow the voice.
  sfx_track(sections, card_times) -> mono float32 at 48 kHz, peak-safe, sits under the voice
"""
import math
import numpy as np

from render import B, DUR, WORDS, prog, io

SR = 48000
F32 = np.float32
rng = np.random.default_rng(11)

def T(d): return np.arange(int(SR * d)) / SR
def env_ad(n, a=0.005, r=0.1):
    e = np.ones(n, F32); na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.exp(-np.linspace(0, 6, nr))
    return e
def lp(x, k): return np.convolve(x, np.ones(k) / k, mode="same")
def hp(x, k): return x - lp(x, k)
def bp(x, lo_k, hi_k): return lp(hp(x, lo_k), hi_k)

def place(track, sig, t0, gain):
    i = int(t0 * SR)
    if i >= len(track) or i + len(sig) <= 0: return
    if i < 0: sig, i = sig[-i:], 0
    sig = sig[: len(track) - i]
    track[i:i + len(sig)] += gain * sig.astype(F32)


# ---------- engine ----------
def rpm_curve(n):
    t = np.arange(n) / SR
    rpm = 950 + 25 * np.sin(2 * np.pi * 0.7 * t)                                # lumpy idle
    def blip(t0, peak, up, down):
        k = np.clip((t - t0) / up, 0, 1); k = k * k * (3 - 2 * k)
        dec = np.exp(-np.clip(t - t0 - up, 0, None) / down)
        return (t >= t0) * k * dec * peak
    rpm += blip(B["v12"] - 0.1, 2600, 0.35, 0.8)                                # "The V12..." rev
    rpm += blip(B["heat"] - 0.15, 3300, 0.45, 1.4)                              # "huge heat" surge
    rpm += blip(B["question"] - 0.2, 900, 0.3, 0.7)                             # small blip for the question
    rpm += 180 * np.clip((t - B["heat"]) / 1.0, 0, 1) * (1 - np.clip((t - B["lined"]) / 2.0, 0, 1))  # hot, high idle
    return rpm

def engine(n):
    rpm = rpm_curve(n)
    f0 = rpm / 60 * 6                                                            # V12 four-stroke firing frequency
    ph = 2 * np.pi * np.cumsum(f0) / SR
    half = 2 * np.pi * np.cumsum(rpm / 60 * 0.5) / SR                            # per-cylinder irregularity
    x = np.zeros(n)
    for k, a in ((1, 1.0), (2, 0.55), (3, 0.35), (4, 0.22), (6, 0.12), (8, 0.07)):
        x += a * np.sin(k * ph + 0.3 * k)
    x += 0.35 * np.sin(half) * np.sin(ph)                                        # burble
    noise = rng.normal(size=n)
    pulse = (0.5 + 0.5 * np.sin(ph)) ** 6
    x += 0.6 * lp(noise, 6) * pulse                                              # combustion texture
    x = np.tanh(1.6 * x)                                                         # growl
    x = lp(x, 9)
    load = np.clip((rpm - 950) / 3000, 0, 1)
    x *= 0.55 + 0.45 * load
    return x / (np.abs(x).max() + 1e-9)


# ---------- one-shot cues ----------
def whoosh(d=0.55):
    t = T(d); n = len(t)
    x = rng.normal(size=n)
    k = (np.sin(np.pi * t / d) ** 2)
    x = np.convolve(x, np.ones(18) / 18, mode="same") * k
    sub = np.sin(2 * np.pi * (60 - 25 * t / d) * t) * np.exp(-t * 5) * 0.8
    return (x / (np.abs(x).max() + 1e-9) * 0.6 + sub) * env_ad(n, 0.02, 0.15)

def blip(f=1250, d=0.09):
    t = T(d)
    return (np.sin(2 * np.pi * (f - 300 * t / d) * t) + 0.3 * np.sin(4 * np.pi * f * t)) * env_ad(len(t), 0.002, 0.07)

def fwip(d=0.22):
    t = T(d); x = hp(rng.normal(size=len(t)), 6)
    sweep = np.sin(np.pi * t / d) ** 1.5
    return x * sweep * 0.7

def tick(f=2300):
    t = T(0.03)
    return np.sin(2 * np.pi * f * t) * np.exp(-t * 160)

def click():
    t = T(0.05)
    return (np.sin(2 * np.pi * 900 * t) * np.exp(-t * 90) + 0.4 * hp(rng.normal(size=len(t)), 3) * np.exp(-t * 200))

def impact(d=1.2):
    t = T(d)
    return np.sin(2 * np.pi * (48 * np.exp(-t * 1.5) + 30) * t) * np.exp(-t * 3.2) + 0.15 * lp(rng.normal(size=len(t)), 40) * np.exp(-t * 6)


# ---------- texture beds ----------
def sizzle(n, amount):
    x = bp(rng.normal(size=n), 3, 2)
    crack = (rng.random(n) > 0.9993) * rng.normal(size=n) * 4                    # tiny crackles
    return (x * 0.5 + crack) * amount

def crinkle(n, amount):
    grains = (rng.random(n) > 0.997) * rng.normal(size=n)
    g = np.convolve(grains, np.exp(-np.arange(240) / 30), mode="same")
    return hp(g, 4) * amount

def scanner(n, amount):
    t = np.arange(n) / SR
    f = 1800 + 400 * np.sin(2 * np.pi * t / 2.8)
    sweep = np.sin(2 * np.pi * np.cumsum(f) / SR)
    hum = np.sin(2 * np.pi * 180 * t) * 0.6
    return (sweep * 0.25 + hum) * amount * (0.6 + 0.4 * np.sin(2 * np.pi * t * 4) ** 2)

def chatter(n, amount):
    x = np.zeros(n); i = 0
    while i < n:
        d = int(SR * rng.uniform(0.02, 0.06)); f = rng.choice([1600, 2100, 2600, 3100])
        if rng.random() < 0.55:
            seg = np.sin(2 * np.pi * f * np.arange(d) / SR) * env_ad(d, 0.002, 0.01)
            x[i:i + d] += seg[: n - i]
        i += d + int(SR * rng.uniform(0.01, 0.05))
    return x * amount


def window(n, a, b, fade=0.3):
    t = np.arange(n) / SR
    return np.clip((t - a) / fade, 0, 1) * np.clip((b - t) / fade, 0, 1)

def sfx_track(sections, cards, highlights, cube_t0):
    """sections: [(name, start)], cards/highlights: lists of times, cube_t0: first cube time."""
    n = int(DUR * SR)
    out = np.zeros(n, F32)
    eng = engine(n) * 0.22
    eng *= window(n, 0.0, DUR, 0.05) * (1 - 0.35 * window(n, sections[2][1], sections[3][1], 0.8))  # step back during thermal
    out += eng.astype(F32)
    bounds = [s for _, s in sections] + [DUR]
    for (name, s), e in zip(sections, bounds[1:]):
        w_ = window(n, s, e, 0.25)
        if name == "ascii": out += (chatter(n, 0.035) * w_).astype(F32)
        if name == "lidar": out += (scanner(n, 0.018) * w_).astype(F32)
        if name == "thermal":
            heat_amt = np.clip((np.arange(n) / SR - B["carbon"]) / 1.5, 0, 1) * 0.06
            out += (sizzle(n, 1.0) * heat_amt * w_).astype(F32)
    foil = window(n, B["gold"], B["lined"] + 1.4, 0.4)
    out += (crinkle(n, 0.12) * foil).astype(F32)
    place(out, impact(), 0.0, 0.5)                                              # cold-open hit
    for _, s in sections[1:]:
        place(out, whoosh(), s - 0.3, 0.32)
    for c in cards: place(out, blip(), c, 0.16)
    for h in highlights: place(out, fwip(), h, 0.12)
    for i in range(16): place(out, tick(2100 + 40 * i), cube_t0 + i * 0.07, 0.12)
    for w in WORDS:
        if w["w"].strip("?").lower() in ("yes", "no"): place(out, click(), w["s"] - 0.03, 0.22)
    nf = int(0.25 * SR); out[-nf:] *= np.linspace(1, 0, nf)
    return out
