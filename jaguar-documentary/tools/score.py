"""Original synthesised score + engine/sfx for 'The Rise and Fall of Jaguar'. Pure numpy, no samples."""
import numpy as np, sys, wave
SR = 44100
TOTAL = 306.0
N = int(TOTAL * SR)
rng = np.random.default_rng(11)

def z(): return np.zeros(N, np.float32)
def T(n): return np.arange(n) / SR
def put(buf, x, t0, gain=1.0):
    i = int(t0 * SR)
    if i >= N: return
    j = min(N, i + len(x))
    buf[i:j] += (x[:j - i] * gain).astype(np.float32)
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def adsr(n, a, d, s, r):
    e = np.ones(n)
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na = max(1, min(na, n)); e[:na] = np.linspace(0, 1, na)
    nd = min(nd, n - na)
    if nd > 0: e[na:na + nd] = np.linspace(1, s, nd)
    e[na + nd:] = s
    nr = min(nr, n)
    if nr > 0: e[n - nr:] *= np.linspace(1, 0, nr)
    return e
def lp(x, fc, order=1):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    H = 1 / (1 + (f / fc) ** (2 * order)) ** 0.5
    return np.fft.irfft(X * H, len(x))
def hp(x, fc):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    H = (f / fc) ** 2 / (1 + (f / fc) ** 4) ** 0.5
    return np.fft.irfft(X * H, len(x))
def bp(x, lo, hi): return hp(lp(x, hi), lo)
def noise(n): return rng.normal(0, 1, n)

# ---------------- instruments ----------------
def pad(m, dur, vel=0.3, bright=1200, att=1.5, rel=2.0, det=0.12):
    n = int((dur + rel) * SR); t = T(n); f = mtof(m); x = np.zeros(n)
    for d in (-det, 0, det):
        ff = f * 2 ** (d / 12)
        ph = (ff * t) % 1.0
        x += (2 * ph - 1)
        x += 0.5 * np.sign(np.sin(2 * np.pi * ff * 0.5 * t))
    x = lp(x, bright, 2) * adsr(n, att, 0.1, 1.0, rel) * vel / 3
    return x
def piano(m, dur=3.0, vel=0.35):
    n = int(dur * SR); t = T(n); f = mtof(m); x = np.zeros(n)
    for h in range(1, 14):
        fh = f * h * (1 + 0.0004 * h * h)
        if fh > 9000: break
        amp = vel / h ** 1.1 * (0.6 + 0.4 * np.cos(h * 1.3))
        x += amp * np.sin(2 * np.pi * fh * t + h) * np.exp(-t * (1.1 + 0.55 * h) / (1 + (m - 40) / 40))
    x *= 1 - np.exp(-t * 400)
    return x
def bell(m, dur=2.5, vel=0.25):
    n = int(dur * SR); t = T(n); f = mtof(m)
    x = np.sin(2 * np.pi * f * t + 1.5 * np.sin(2 * np.pi * f * 3.5 * t) * np.exp(-t * 4)) * np.exp(-t * 1.6)
    x += 0.4 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 2.5)
    return x * vel * (1 - np.exp(-t * 600))
def brass(m, dur, vel=0.3, att=0.35, rel=0.8, bright=1800):
    n = int((dur + rel) * SR); t = T(n); f = mtof(m); x = np.zeros(n)
    for d in (-0.07, 0.07):
        ph = (f * 2 ** (d / 12) * t) % 1.0; x += 2 * ph - 1
    x = lp(x, bright, 2) * adsr(n, att, 0.2, 0.8, rel) * vel / 2
    return x
def strings_stac(m, dur=0.22, vel=0.3):
    n = int(dur * SR); t = T(n); f = mtof(m)
    x = (2 * ((f * t) % 1) - 1) + (2 * ((f * 1.004 * t) % 1) - 1)
    return lp(x, 2200, 2) * adsr(n, 0.01, 0.05, 0.6, 0.08) * vel / 2
def sub(m, dur, vel=0.5, att=0.5, rel=1.5):
    n = int((dur + rel) * SR); t = T(n)
    return np.sin(2 * np.pi * mtof(m) * t) * adsr(n, att, 0.1, 1, rel) * vel
def boom(dur=2.5, vel=1.0, f0=70):
    n = int(dur * SR); t = T(n)
    ph = 2 * np.pi * (f0 * 0.45 * t + f0 * 0.55 * (1 - np.exp(-t * 6)) / 6)
    x = np.sin(ph) * np.exp(-t * 1.6)
    x += 0.35 * lp(noise(n), 400) * np.exp(-t * 4) * 6
    return np.tanh(x * vel * 1.5) * 0.9
def taiko(vel=1.0):
    n = int(1.6 * SR); t = T(n)
    ph = 2 * np.pi * (55 * t + 40 * (1 - np.exp(-t * 14)) / 14)
    x = np.sin(ph) * np.exp(-t * 3.2) + 0.25 * lp(noise(n), 1500) * np.exp(-t * 30)
    return np.tanh(x * 1.6) * vel * 0.8
def snare(vel=1.0):
    n = int(0.35 * SR); t = T(n)
    return (hp(noise(n), 1500) * np.exp(-t * 18) * 0.5 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25) * 0.4) * vel
def tick(vel=0.5):
    n = int(0.05 * SR); t = T(n)
    return (np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 120) + 0.3 * noise(n) * np.exp(-t * 200)) * vel
def riser(dur, vel=0.4, f0=300, f1=6000):
    n = int(dur * SR); t = T(n)
    ph = np.cumsum(f0 * (f1 / f0) ** (t / dur)) / SR
    x = np.sin(2 * np.pi * ph) * 0.3 + hp(noise(n), 800) * 0.5
    return x * (t / dur) ** 2.2 * vel
def revcymbal(dur, vel=0.4):
    n = int(dur * SR); t = T(n)
    return hp(noise(n), 3000) * (t / dur) ** 3 * vel
def heartbeat(vel=0.5):
    n = int(0.5 * SR); t = T(n)
    a = np.sin(2 * np.pi * 52 * t) * np.exp(-t * 14)
    b = np.zeros(n); k = int(0.18 * SR); b[k:] = (np.sin(2 * np.pi * 46 * t[:n - k]) * np.exp(-t[:n - k] * 16)) * 0.7
    return (a + b) * vel

def engine(dur, rpm_fn, vel=0.5, cyl=6, rasp=0.6):
    n = int(dur * SR); t = T(n)
    rpm = rpm_fn(t)
    f = rpm / 60.0 * cyl / 2.0
    ph = np.cumsum(f) / SR
    x = np.zeros(n)
    for h in range(1, 28):
        amp = 1.0 / h ** 1.05 * (1 + 0.6 * np.cos(h * 0.9))
        x += amp * np.sin(2 * np.pi * h * ph + h * 0.37 * np.sin(2 * np.pi * ph))
    pulse = 0.5 + 0.5 * np.cos(2 * np.pi * ph)
    x += rasp * bp(noise(n), 400, 2400) * pulse * 1.4
    x += 0.25 * lp(noise(n), 120) * 3
    x = np.tanh(x * 1.1)
    x = lp(x, 3200)
    return x * vel

def reverb(x, secs=2.6, wet=0.3, hpc=200):
    n = int(secs * SR); t = T(n)
    ir = noise(n) * np.exp(-t * 3.2 / secs * 1.8)
    ir = lp(ir, 5000)
    ir[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
    ir /= np.sqrt((ir ** 2).sum())
    L = 1 << int(np.ceil(np.log2(len(x) + n)))
    y = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[: len(x)]
    return x * (1 - wet * 0.5) + y * wet

# ---------------- score ----------------
music = z(); fx = z(); eng = z()
def ch_pad(buf, midis, t0, dur, vel=0.25, **k):
    for m in midis: put(buf, pad(m, dur, vel, **k), t0)

# --- HOOK 0-13.4 ---
def rpm_open(t):
    return np.interp(t, [0, 0.5, 0.75, 1.3, 1.9, 2.1, 3.0, 3.4, 4.3, 4.5], [0, 0, 1100, 5200, 3600, 3300, 5800, 4300, 6300, 6300])
e = engine(4.6, rpm_open, vel=0.55); e *= np.clip(T(len(e)) / 0.1, 0, 1) * np.where(T(len(e)) < 0.55, 0.0, 1.0)
put(eng, e, 0.0)
put(fx, boom(3.0, 1.0, 60), 0.45, 1.0)            # ignition
put(fx, boom(2.0, 0.8, 70), 0.0, 0.5)             # sub thump on first frame
for a in (1.5, 3.0): put(fx, taiko(0.9), a)
put(fx, riser(1.4, 0.35), 3.0)
# montage passes (doppler: pitch falls through the pass)
def pass_rpm(r0, r1):
    return lambda t: np.interp(t, [0, 0.45, 0.6, 1.2], [r0, r0 * 1.08, r1 * 0.82, r1 * 0.78])
for k, (a, r0, r1) in enumerate([(4.4, 5200, 5800), (5.5, 4300, 5000), (6.6, 3800, 4600), (8.8, 4200, 5400)]):
    ee = engine(1.2, pass_rpm(r0, r1), vel=0.42, cyl=6 if k != 2 else 6)
    ee *= np.sin(np.pi * np.clip(T(len(ee)) / 1.2, 0, 1)) ** 0.7
    put(eng, ee, a)
    put(fx, taiko(0.8), a)
for i, a in enumerate((7.7, 7.88, 8.05, 8.22, 8.4)): put(fx, taiko(0.7 + 0.06 * i), a); put(fx, snare(0.5), a)
# hook music: driving low strings + brass, Dm
bpm = 126; beat = 60 / bpm
for b in range(0, 29):
    t0 = 3.0 + b * beat / 2
    if t0 > 13.3: break
    m = [38, 38, 45, 38, 41, 38, 45, 43][b % 8]
    put(music, strings_stac(m + 12, 0.2, 0.22), t0)
    put(music, sub(m, 0.3, 0.25, 0.01, 0.1), t0)
ch_pad(music, [50, 57, 62, 65], 3.0, 6.8, 0.2, bright=1800, att=2.5)
put(music, brass(50, 3.0, 0.3, 0.8, 1.2), 9.8)
put(music, brass(57, 3.0, 0.28, 0.8, 1.2), 9.8)
put(music, brass(65, 3.0, 0.22, 0.9, 1.2), 9.8)
put(fx, revcymbal(1.2, 0.3), 8.5)
# --- THE TURN 13.4 - 21.3 : everything cuts, dark ---
cut = 13.4
for i in range(0, 14): put(fx, heartbeat(0.55), 14.2 + i * 1.05)
put(music, sub(26, 8.0, 0.35, 1.5, 2.0), 13.9)
ch_pad(music, [38, 45, 50, 53], 14.0, 7.2, 0.16, bright=700, att=3.0)   # Dm, dark
put(music, piano(62, 4, 0.2), 15.7); put(music, piano(58, 4, 0.2), 17.4); put(music, piano(57, 5, 0.22), 19.2)
for i, a in enumerate(np.arange(19.4, 21.2, 0.15)): put(fx, bell(86 + (i % 3) * 7, 0.6, 0.06), a)   # electric shimmer
put(fx, riser(2.0, 0.3), 19.3)
put(fx, boom(3.5, 1.0, 48), 21.3)                  # "How did Jaguar..."
put(music, sub(26, 5, 0.4, 0.05, 2.5), 21.3)
ch_pad(music, [38, 45, 50, 56], 21.3, 5.0, 0.18, bright=900, att=0.6)
# rewind
put(fx, revcymbal(2.6, 0.35), 25.9)
for i in range(30): put(fx, tick(0.28), 26.1 + i * (2.4 / 30) ** 1.0 * (1 + 0.0))
# --- CH1 28.7-66.4 : warm, hopeful, D major ---
ch_pad(music, [50, 57, 62, 66], 28.7, 7.0, 0.2, bright=1500, att=2.0)
prog1 = [(28.7, [50, 57, 62, 66]), (35.7, [47, 54, 62, 66]), (42.7, [43, 50, 59, 62]), (49.7, [45, 52, 61, 64]), (56.0, [50, 57, 62, 66]), (61.0, [50, 55, 62, 67])]
for t0, ch in prog1[1:]:
    ch_pad(music, ch, t0 - 0.2, 6.0, 0.19, bright=1700, att=2.0)
arp = [74, 78, 81, 78, 74, 78, 81, 86]
for i in range(0, 52):
    t0 = 29.5 + i * 0.7
    if t0 > 55: break
    base = {0: 0, 1: -3, 2: -7, 3: -5}[(int((t0 - 29.5) // 7)) % 4]
    put(music, piano(arp[i % 8] + base - 12, 2.6, 0.17), t0)
put(fx, boom(2.5, 0.5, 60), 28.7)
put(fx, riser(3.2, 0.3), 55.6); put(fx, boom(2.8, 0.9, 55), 58.9)
for a in (0, 1, 2, 3): put(music, brass(50 + [0, 7, 12, 16][a], 4.5, 0.2, 0.6, 1.5), 58.9)
# XK120 engine pass
put(eng, engine(3.6, lambda t: np.interp(t, [0, 1.2, 2.4, 3.6], [1000, 3300, 4300, 3800]), vel=0.26), 60.2)
# --- CH2 66.4-91.4 : racing, driving ---
bpm = 138; beat = 60 / bpm
for b in range(0, 200):
    t0 = 66.4 + b * beat / 2
    if t0 > 91.2: break
    root = [38, 38, 41, 43][int((t0 - 66.4) // (beat * 4)) % 4]
    put(music, strings_stac(root + 24 + [0, 7, 12, 7][b % 4], 0.16, 0.2), t0)
    if b % 2 == 0: put(music, sub(root, 0.4, 0.28, 0.01, 0.15), t0)
    if b % 4 == 0: put(fx, taiko(0.55), t0)
    if b % 8 in (4,): put(fx, snare(0.4), t0)
for a in (69.4, 74.0, 78.1, 78.9, 79.7):
    put(fx, boom(2.5, 0.8, 60), a); put(music, brass(50, 2.5, 0.3, 0.2, 1.0), a); put(music, brass(57, 2.5, 0.28, 0.2, 1.0), a); put(music, brass(62, 2.5, 0.26, 0.2, 1.0), a)
ch_pad(music, [38, 50, 57, 65], 66.4, 12, 0.18, bright=1700, att=2.0)
ch_pad(music, [41, 53, 60, 65], 78.4, 13, 0.2, bright=2200, att=2.0)
put(fx, riser(3.0, 0.3), 81.0)
for a in np.arange(83.5, 88.0, 0.5):
    put(eng, engine(0.6, lambda t: np.interp(t, [0, 0.3, 0.6], [4200, 5600, 5000]), vel=0.13), a)
put(fx, revcymbal(1.5, 0.3), 89.9)
# --- CH3 91.4-122 : E-Type nostalgia, F major piano + strings ---
put(fx, boom(3.0, 0.6, 50), 91.4)
chords3 = [(91.4, [41, 53, 57, 60, 64]), (97.6, [38, 50, 57, 62, 65]), (103.6, [46, 53, 58, 62, 65]), (109.6, [41, 53, 60, 64, 67]), (115.4, [43, 55, 59, 62, 66]), (119.4, [41, 53, 57, 60, 67])]
for t0, ch in chords3: ch_pad(music, ch, t0 - 0.3, 6.5, 0.17, bright=1800, att=2.2)
mel = [72, 76, 79, 77, 76, 72, 74, 69, 72, 74, 76, 79, 84, 81, 79, 76]
for i, m in enumerate(mel * 3):
    t0 = 92.2 + i * 1.8
    if t0 > 121: break
    put(music, piano(m, 4.0, 0.24), t0)
    put(music, piano(m - 12, 4.0, 0.14), t0 + 0.9)
# --- turn at 122 ---
put(music, sub(29, 8, 0.35, 1.0, 2.0), 121.6)
put(fx, boom(3.5, 0.8, 45), 122.0)
# --- CH4 125-190 : dark understated tension ---
put(music, sub(26, 62, 0.28, 3.0, 3.0), 125.0)
ch_pad(music, [38, 45, 50, 53], 125.0, 16, 0.14, bright=700, att=4.0)
ch_pad(music, [36, 43, 48, 51], 141.0, 16, 0.14, bright=750, att=4.0)
ch_pad(music, [34, 41, 46, 49], 157.0, 16, 0.15, bright=800, att=4.0)
ch_pad(music, [38, 45, 50, 57], 173.0, 17, 0.16, bright=1200, att=3.0)
for a in np.arange(125.5, 188.0, 0.8): put(fx, tick(0.1), a) if int(a * 10) % 3 == 0 else None
for i in range(0, 60):
    t0 = 127.0 + i * 1.3
    if t0 > 186: break
    put(music, piano([50, 53, 57, 55, 50, 48, 52, 57][i % 8], 3.0, 0.1), t0)
for a in (143.8, 147.4, 149.1): put(fx, taiko(0.5), a)
for a in (161.0, 172.3): put(fx, boom(2.8, 0.7, 48), a)
put(music, brass(50, 3, 0.18, 0.6, 1.2), 175.2); put(music, brass(57, 3, 0.18, 0.6, 1.2), 175.2); put(music, brass(62, 3, 0.16, 0.6, 1.2), 175.2)
put(fx, riser(2.5, 0.25), 183.0)
put(fx, boom(3.5, 0.8, 42), 186.1)
# --- CH5 190-229 : the fall ---
put(music, sub(24, 38, 0.32, 3.0, 3.0), 190.4)
ch_pad(music, [36, 43, 48, 51], 190.4, 20, 0.13, bright=650, att=4.0)
ch_pad(music, [34, 41, 46, 50], 210.0, 12, 0.13, bright=650, att=4.0)
for a in np.arange(190.4, 221.0, 1.0): put(fx, heartbeat(0.38), a) if False else None
for i in range(0, 30): put(fx, heartbeat(0.42), 192.0 + i * 1.0) if (192.0 + i) < 221 else None
for i in range(0, 24):
    t0 = 199.0 + i * 1.5
    if t0 > 220: break
    put(music, piano([45, 48, 52, 50][i % 4], 4.0, 0.1), t0)
put(fx, boom(3.0, 0.8, 40), 202.0); put(fx, boom(3.0, 0.8, 40), 209.4)
# final combustion car: idle, blip, spool down, silence at 228
def rpm_final(t):
    return np.interp(t, [0, 1.0, 1.4, 2.2, 3.4, 4.8, 5.8, 6.4, 6.6], [800, 800, 3200, 1800, 2600, 1500, 900, 330, 0])
ef = engine(6.7, rpm_final, vel=0.5, cyl=8, rasp=0.9)
ef *= np.clip(T(len(ef)) / 0.5, 0, 1) * np.clip((6.7 - T(len(ef))) / 0.7, 0, 1)
put(eng, ef, 221.6)
ch_pad(music, [43, 50, 55, 58], 221.6, 5.5, 0.1, bright=600, att=3.0, rel=1.5)
# silence 228.3-229.6 (nothing added). then a lone note
put(music, piano(62, 6, 0.22), 229.3); put(music, piano(57, 6, 0.18), 231.2)
put(music, sub(26, 6, 0.2, 1.0, 2.0), 229.5)
# --- CH6 235.8-: tension -> reveal -> uncertain ---
ch_pad(music, [38, 45, 50, 53], 234.0, 14, 0.14, bright=900, att=3.5)
for i in range(0, 40):
    t0 = 235.8 + i * 0.62
    if t0 > 249: break
    put(music, strings_stac(38 + [0, 0, 7, 5][i % 4] + 12, 0.16, 0.1 + 0.09 * (t0 - 235.8) / 13), t0)
for a in (244.1, 246.0): put(fx, taiko(0.5), a)
put(fx, riser(4.5, 0.4), 244.6)
put(fx, boom(3.5, 1.0, 45), 249.4)               # Type 00
put(fx, riser(3.6, 0.4), 249.8)
put(fx, boom(4.0, 1.0, 50), 253.5)               # revealed
for a in (0, 1, 2, 3): put(music, brass(50 + [0, 7, 12, 16][a], 6, 0.24, 0.8, 2.0), 253.4)
# electric shimmer
seq = [74, 81, 86, 90, 93, 90, 86, 81]
for i in range(0, 60):
    t0 = 255.0 + i * 0.5
    if t0 > 285: break
    put(fx, bell(seq[i % 8] - (0 if t0 < 275 else 5), 2.0, 0.07), t0)
ch_pad(music, [38, 50, 57, 62, 65], 254.0, 12, 0.2, bright=1800, att=2.5)
ch_pad(music, [41, 53, 60, 64], 266.0, 10, 0.18, bright=1800, att=2.5)
put(fx, boom(3.0, 0.7, 48), 262.0)
for a in (277.9,): put(fx, boom(2.5, 0.6, 45), a)
# unresolved ending: Dsus, sparse piano
ch_pad(music, [38, 45, 52, 57, 64], 281.0, 24, 0.2, bright=1500, att=4.5, rel=4.0)
put(music, sub(26, 22, 0.28, 3.0, 4.0), 282.0)
for i, m in enumerate([81, 79, 76, 74, 76, 79, 81, 83, 81, 79, 76, 74]):
    put(music, piano(m, 5.0, 0.2), 284.0 + i * 1.7)
put(music, piano(64, 7.0, 0.22), 298.8); put(music, piano(57, 7.0, 0.2), 299.6)
put(fx, boom(4.0, 0.7, 40), 299.6)

# ---------------- mix ----------------
M = reverb(music, 3.2, 0.42)
F = reverb(fx, 1.8, 0.2)
E = reverb(eng, 0.9, 0.12)
def stereo(x, w=0.0):
    d = int(0.012 * SR)
    L = x.copy(); R = np.roll(x, d) * 1.0
    return np.stack([L * (1 - w) + R * w, R * (1 - w) + L * w], 1)
def fade_out(x, a, b):
    i, j = int(a * SR), int(b * SR); x[i:j] *= np.linspace(1, 0, j - i); x[j:] = 0
# hard cut at 13.4 for hook music/engine (the "engine noise stops" moment)
def hardcut(x, t, ramp=0.04):
    i = int(t * SR); r = int(ramp * SR)
    x[i - r:i] *= np.linspace(1, 0, r); x[i:i + int(0.05*SR)] = 0
hook_m = M.copy(); hook_m[int(13.4 * SR):] = 0
rest_m = M.copy(); rest_m[:int(13.4 * SR)] = 0
M2 = hook_m
hardcut(M2, 13.4); hardcut(E, 13.4) if False else None
M = M2 + rest_m
E[int(13.4 * SR):int(13.4 * SR) + int(0.0)] = E[int(13.4 * SR):int(13.4 * SR)]
mix = np.stack([M * 0.9 + F * 0.8 + E * 0.9, M * 0.9 + F * 0.8 + E * 0.9], 1)
# widen a bit via micro delay on the reverb-heavy part
w = stereo(M * 0.9 + F * 0.8, 0.35)
mix = w + np.stack([E * 0.9, E * 0.9], 1)
mix = np.tanh(mix * 0.9) / np.tanh(0.9)
mix /= np.abs(mix).max() / 0.8
out = (mix * 32767).astype(np.int16)
for name, arr in (('score.wav', out),):
    with wave.open(sys.argv[1] if len(sys.argv) > 1 else name, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(arr.tobytes())
print('done', mix.shape)
