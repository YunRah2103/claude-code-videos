"""Synthesised fight SFX and taiko/drone score (reuses new-car-trap sfx primitives)."""
import os, sys, wave
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'new-car-trap', 'src'))
import sfx as base
from sfx import SR, T, lp, sweep, dec, fade

rng = np.random.default_rng(11)
def noise(d): return rng.standard_normal(int(SR*d))
def hp(x, k=6): return x - lp(x, k)

def punch():
    s = base.thump(0.22) * 1.1
    c = hp(noise(0.05), 3) * dec(0.05, 70); s[:len(c)] += c * 0.9
    return s
def bighit():
    s = base.boom(0.9) * 1.1
    c = hp(noise(0.12), 2) * dec(0.12, 30); s[:len(c)] += c * 1.2
    p = punch(); s[:len(p)] += p * 0.8
    return s
def block():
    s = base.thump(0.15) * 0.6
    c = hp(noise(0.04), 2) * dec(0.04, 90); s[:len(c)] += c * 0.8
    return s
def clang():
    d = 0.9; t = T(d); s = np.zeros(len(t))
    for f, a in ((1870, 1), (2730, .7), (3910, .5), (5220, .35), (6650, .2)):
        s += np.sin(2*np.pi*f*t) * a * dec(d, 6 + f/900)
    c = hp(noise(0.03), 2) * dec(0.03, 100); s[:len(c)] += c * 2
    return fade(s) * 0.45
def shing():
    d = 1.0; t = T(d)
    s = sum(np.sin(2*np.pi*f*t*(1 + 0.03*t)) * a for f, a in ((2400, 1), (3610, .6), (5130, .4))) * dec(d, 4)
    n = hp(noise(d), 2) * np.exp(-((t-0.08)/0.06)**2) * 0.8
    return fade(s*0.3 + n*0.5) * 0.7
def cut():
    w = base.whoosh(0.22, 6) * 0.9
    s = np.zeros(int(SR*1.2)); s[:len(w)] += w
    sh = shing() * 0.6; s[int(SR*0.05):int(SR*0.05)+len(sh)] += sh[:len(s)-int(SR*0.05)]
    b = bighit() * 0.7; s[int(SR*0.04):int(SR*0.04)+len(b)] += b[:len(s)-int(SR*0.04)]
    return s
def slam(): return base.crash(1.0) * 1.1
def land(): return base.thump(0.3) * 0.9
def skid():
    d = 0.6; n = lp(noise(d), 3) * np.linspace(1, 0, int(SR*d))**1.5
    return fade(n) * 0.5
def heart():
    s = np.zeros(int(SR*0.5)); a = base.thump(0.18); s[:len(a)] += a
    b = base.thump(0.16) * 0.7; i = int(SR*0.22); s[i:i+len(b)] += b
    return lp(s, 20) * 1.6
def rumble():
    d = 2.6; t = T(d); n = lp(noise(d), 120) * 9
    s = (n + np.sin(2*np.pi*42*t)*0.4) * np.clip(t/1.8, 0, 1)**2 * np.exp(-np.clip(t-2.0, 0, 9)*6)
    return fade(s) * 0.9
def chin():
    d = 0.6; t = T(d)
    s = (np.sin(2*np.pi*3300*t) + .6*np.sin(2*np.pi*5010*t)) * dec(d, 18)
    c = hp(noise(0.01), 2); s[:len(c)] += c
    return fade(s) * 0.4
def whoosh(): return base.whoosh(0.3, 10) * 0.9
def fall():
    d = 0.6; t = T(d); n = lp(noise(d), 8) * (t/d)**2
    return fade(n) * 0.6

LIB = dict(bighit=bighit, block=block, clang=clang, shing=shing, cut=cut, slam=slam, land=land, skid=skid,
           heart=heart, rumble=rumble, chin=chin, whoosh=whoosh, fall=fall, boom=lambda: base.boom(1.4) * 1.2)

def taiko(big=False):
    d = 0.6 if big else 0.35
    s = sweep(110 if big else 150, 55 if big else 80, d) * dec(d, 7 if big else 11)
    c = lp(noise(0.03), 4) * dec(0.03, 60); s[:len(c)] += c*0.6
    return fade(s)
def hat():
    return hp(noise(0.05), 2) * dec(0.05, 70) * 0.25

def pad(d, freqs, vol):
    t = T(d); s = np.zeros(len(t))
    for f in freqs:
        for det in (-0.004, 0.0, 0.005):
            ph = 2*np.pi*f*(1+det)*t
            s += (np.sin(ph) + 0.35*np.sin(2*ph) + 0.15*np.sin(3*ph))
    s = lp(s, 30) / (len(freqs)*3)
    env = np.minimum(1, t/1.2) * np.minimum(1, (d - t)/1.2)
    return s * env * vol

def place(out, s, t):
    i = int(t*SR)
    if i >= len(out) or i < -len(s): return
    if i < 0: s, i = s[-i:], 0
    n = min(len(s), len(out) - i); out[i:i+n] += s[:n]

def score(R, dur):
    out = np.zeros(int(SR*dur) + SR)
    D, F, A_, C, G = 73.4, 87.3, 110.0, 130.8, 98.0
    # drones
    place(out, pad(R(6.6), [D/2, D, A_], 0.30), 0.0)
    place(out, pad(R(16.0)-R(6.4), [D, F, A_, D*2], 0.26), R(6.4))
    place(out, pad(R(19.6)-R(15.9), [D/2, D, G/2*2], 0.32), R(15.9))
    place(out, pad(R(24.75)-R(19.5), [D, F, A_, C, D*2], 0.30), R(19.5))
    place(out, pad(dur - R(24.76), [D/2, D, A_, D*2, F*2], 0.34), R(24.76))
    # rhythm sections (anim start, anim end, bpm, density)
    for a, b, bpm, dens in ((6.8, 15.9, 150, 1), (19.55, 24.6, 165, 2)):
        r0, r1 = R(a), R(b); beat = 60/bpm; t = r0; i = 0
        while t < r1:
            place(out, taiko(i % 8 == 0) * (0.9 if i % 2 == 0 else 0.55), t)
            if dens > 1 or i % 2: place(out, hat(), t + beat/2)
            if i % 4 == 2: place(out, taiko() * 0.5, t + beat*0.75)
            # bass ostinato
            f = (D, D, F, G, D, D, C/2*2/2*2, A_/2)[i % 8] / 2
            bs = np.sin(2*np.pi*f*T(beat*0.9)) * dec(beat*0.9, 5) * 0.28
            place(out, fade(bs), t)
            t += beat; i += 1
    for a in (3.95, 4.75): place(out, taiko(True) * 1.0, R(a))
    return out[:int(SR*dur)]

def wind(dur):
    n = lp(noise(dur), 60) * 2.2
    t = np.arange(len(n))/SR
    return n * (0.6 + 0.4*np.sin(t*0.7)) * 0.35

def write(path, cues, warp, dur, t0=0.0, t1=None):
    t1 = dur if t1 is None else t1
    out = score(warp.R, dur) * 0.55 + wind(dur)
    for ta, name, vol in cues:
        place(out, LIB[name]() * vol * 0.8, warp.R(ta))
    # brief silence before the final delayed cut
    s0, s1 = int(warp.R(24.7)*SR) + int(0.05*SR), int((warp.R(24.7) + 0.45)*SR)
    out[s0:s1] *= np.linspace(1, 0.15, s1 - s0)
    out = np.tanh(out * 0.9)
    seg = out[int(t0*SR):int(t1*SR)]
    st = np.stack([seg, np.roll(seg, 180)], 1)
    pcm = (st / max(1e-6, np.abs(st).max()) * 0.92 * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
