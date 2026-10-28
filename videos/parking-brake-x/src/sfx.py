"""Synthesised sound effects, mixed under the voiceover."""
import numpy as np

SR = 48000
rng = np.random.default_rng(7)

def T(d): return np.arange(int(SR*d)) / SR
def lp(x, k): return np.convolve(x, np.ones(k)/k, mode='same')
def sweep(f0, f1, d, expo=True):
    t = T(d)
    f = f0 * (f1/f0) ** (t/d) if expo else f0 + (f1-f0)*t/d
    return np.sin(2*np.pi*np.cumsum(f)/SR)
def dec(d, rate): return np.exp(-T(d)*rate)
def fade(x, a=0.005, r=0.02):
    n = len(x); e = np.ones(n)
    na, nr = int(a*SR), int(r*SR)
    e[:na] = np.linspace(0, 1, na); e[n-nr:] = np.linspace(1, 0, nr)
    return x*e

def pop():
    d = 0.11
    return fade(sweep(380, 1100, d) * dec(d, 30)) * 0.9

def whoosh(d=0.38, k=24):
    t = T(d)
    n = rng.standard_normal(len(t))
    env = np.sin(np.pi * t/d) ** 2
    a, b = lp(n, k), lp(n, k*4)
    mix = a * (t/d) + b * (1 - t/d)
    return fade(mix * env) * 1.6

def sparkle():
    out = np.zeros(int(SR*0.5))
    for i, f in enumerate([2093, 2637, 3136, 4186, 3520]):
        s = np.sin(2*np.pi*f*T(0.18)) * dec(0.18, 22)
        o = int(i*0.045*SR); out[o:o+len(s)] += s
    return fade(out) * 0.32

def ding(f=1568, d=0.9):
    t = T(d)
    s = np.sin(2*np.pi*f*t) + 0.35*np.sin(2*np.pi*2*f*t) + 0.12*np.sin(2*np.pi*3.01*f*t)
    return fade(s * dec(d, 5)) * 0.4

def thump(d=0.3):
    s = sweep(140, 45, d) * dec(d, 12)
    c = lp(rng.standard_normal(int(SR*0.02)), 6)
    s[:len(c)] += c * 0.5
    return fade(s) * 1.0

def boom(d=1.0):
    s = sweep(110, 38, d) * dec(d, 5)
    n = lp(rng.standard_normal(len(s)), 40) * dec(d, 7) * 2.5
    return fade(s + n) * 0.9

def stamp():
    s = thump(0.25)
    c = rng.standard_normal(int(SR*0.03)) * dec(0.03, 80)
    s[:len(c)] += lp(c, 3) * 0.6
    return s

def confetti():
    out = np.zeros(int(SR*0.7))
    b = rng.standard_normal(int(SR*0.06)) * dec(0.06, 50)
    out[:len(b)] += lp(b, 3) * 1.2
    for _ in range(26):
        o = int(rng.uniform(0.04, 0.6)*SR)
        c = rng.standard_normal(200) * dec(200/SR, 300)
        out[o:o+200] += c * rng.uniform(0.15, 0.4)
    return fade(out) * 0.7

def vroom(d=1.1):
    t = T(d)
    f = 45 + 150 * (t/d) ** 1.4 + 6*np.sin(2*np.pi*9*t)
    ph = np.cumsum(f)/SR
    saw = 2*(ph % 1) - 1
    s = lp(saw, 10) + 0.3*lp(rng.standard_normal(len(t)), 30)
    env = np.minimum(1, t/0.12) * np.minimum(1, (d-t)/0.35)
    return fade(s*env) * 0.55

def screech(d=0.35):
    t = T(d)
    s = np.sin(2*np.pi*np.cumsum(2400 + 300*np.sin(2*np.pi*30*t))/SR)
    n = lp(rng.standard_normal(len(t)), 2) * 0.4
    env = np.sin(np.pi*t/d)
    return fade((s*0.5 + n) * env) * 0.22

def slide_down(d=0.65):
    t = T(d)
    f = 1400 * (350/1400) ** (t/d) * (1 + 0.03*np.sin(2*np.pi*7*t))
    s = np.sin(2*np.pi*np.cumsum(f)/SR)
    env = np.minimum(1, t/0.03) * np.minimum(1, (d-t)/0.1)
    return fade(s*env) * 0.32

def poof(d=0.45):
    t = T(d)
    n = lp(rng.standard_normal(len(t)), 60)
    env = (t/d) ** 0.3 * (1 - t/d) ** 2
    return fade(n*env) * 4.0

def buzzer(d=0.42):
    t = T(d)
    s = np.sign(np.sin(2*np.pi*140*t)) + np.sign(np.sin(2*np.pi*147*t))
    return fade(lp(s, 8) * 0.5) * 0.28

def fall(d=0.35):
    t = T(d)
    s = sweep(2000, 700, d)
    env = np.minimum(1, t/0.05)
    return fade(s * env, r=0.03) * 0.18

def crash(d=0.8):
    s = boom(d) * 0.9
    n = rng.standard_normal(len(s)) * dec(d, 9)
    s += lp(n, 3) * 0.35
    for f in (3150, 4370, 5230):
        s += np.sin(2*np.pi*f*T(d)) * dec(d, 14) * 0.08
    return fade(s)

def coin_clink():
    d = 0.2
    t = T(d)
    return fade((np.sin(2*np.pi*3100*t) + 0.6*np.sin(2*np.pi*4240*t)) * dec(d, 28)) * 0.22

def cha_ching():
    out = np.zeros(int(SR*1.0))
    n = rng.standard_normal(int(SR*0.08)) * dec(0.08, 40)
    out[:len(n)] += lp(n, 2) * 0.5
    for o, f in ((0.0, 2637), (0.12, 3520)):
        s = ding(f, 0.8) * 0.9
        i = int(o*SR); out[i:i+len(s)] += s
    for _ in range(10):
        c = coin_clink() * 0.6
        i = int(rng.uniform(0.05, 0.45)*SR); out[i:i+len(c)] += c
    return out

def click():
    d = 0.06
    n = rng.standard_normal(int(SR*d)) * dec(d, 90)
    return fade(n * 0.7 + np.sin(2*np.pi*2400*T(d)) * dec(d, 120) * 0.6, 0.001, 0.01)

def creak(d=0.7):
    t = T(d)
    f = 180 + 60*np.sin(2*np.pi*3.1*t) + 40*np.sin(2*np.pi*11*t)
    s = np.sign(np.sin(2*np.pi*np.cumsum(f)/SR)) * (0.6 + 0.4*np.sin(2*np.pi*23*t))
    return fade(lp(s, 6) * np.sin(np.pi*t/d) * 0.35, 0.02, 0.1)

LIB = dict(click=click, creak=creak, pop=pop, whoosh=whoosh, sparkle=sparkle, ding=ding, thump=thump, boom=boom, stamp=stamp,
           confetti=confetti, vroom=vroom, screech=screech, slide_down=slide_down, poof=poof, buzzer=buzzer,
           fall=fall, crash=crash, coin=coin_clink, cha_ching=cha_ching)

def render(cues, duration):
    out = np.zeros(int(SR*duration) + SR)
    for t, name, vol in cues:
        s = LIB[name]() * vol
        i = int(t*SR)
        out[i:i+len(s)] += s[:len(out)-i]
    return out[:int(SR*duration)]
