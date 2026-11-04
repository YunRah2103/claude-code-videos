"""Original soundtrack: 96 bpm lo-fi synth track + rain, thunder, whooshes and a flat-six engine that follows the picture."""
import wave
import numpy as np

SR = 44100
BPM = 96
BEAT = 60 / BPM            # 0.625 s, bar = 2.5 s -> every scene cut lands on a bar line
DUR = 27.5
rng = np.random.default_rng(911)


def mtof(m): return 440 * 2 ** ((m - 69) / 12)


def T(d): return np.arange(int(SR * d)) / SR


def lp(x, k):
    k = max(1, int(k)); return np.convolve(x, np.ones(k) / k, mode='same')


def fftconv(x, ir):
    n = len(x) + len(ir)
    return np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[:len(x)]


def add(buf, sig, t0):
    i = int(t0 * SR)
    if i >= len(buf): return
    j = min(len(buf), i + len(sig)); buf[i:j] += sig[:j - i]


CHORDS = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60, 64], [48, 52, 55, 59]]   # Fmaj7 Em7 Dm9 Cmaj7
ROOTS = [41, 40, 38, 36]


def pad(n, d):
    t = T(d); out = np.zeros_like(t)
    vib = 1 + 0.0025 * np.sin(2 * np.pi * 0.6 * t)
    for m in n:
        for det in (-0.07, 0.0, 0.08):
            f = mtof(m + det) * vib
            ph = np.cumsum(2 * np.pi * f / SR)
            out += (2 * ((ph / (2 * np.pi)) % 1) - 1) * 0.5 + np.sin(ph) * 0.6
    env = np.minimum(1, t / 0.6) * np.minimum(1, (d - t) / 0.5).clip(0, 1)
    return lp(lp(out, 18), 10) * env / len(n)


def pluck(m, d=0.45):
    t = T(d); f = mtof(m)
    s = np.sign(np.sin(2 * np.pi * f * t)) * 0.4 + np.sin(2 * np.pi * f * t)
    return lp(s, 6) * np.exp(-t * 9) * np.minimum(1, t / 0.003)


def kick():
    t = T(0.45); f = 48 + 110 * np.exp(-t * 28)
    return np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-t * 7) * 1.1


def snare():
    t = T(0.35)
    return (lp(rng.standard_normal(len(t)), 3) * np.exp(-t * 16) * 0.55 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25) * 0.4)


def hat(open_=False):
    t = T(0.25 if open_ else 0.06)
    n = rng.standard_normal(len(t)); n = n - lp(n, 4)
    return n * np.exp(-t * (14 if open_ else 70)) * 0.22


def music():
    n = int(SR * DUR); L = np.zeros(n); R = np.zeros(n); drums = np.zeros(n); arp = np.zeros(n); bass = np.zeros(n)
    bars = int(DUR / (4 * BEAT))
    for b in range(bars):
        t0 = b * 4 * BEAT; ch = CHORDS[b % 4]
        p = pad(ch, 4 * BEAT + 0.6)
        add(L, p * 0.55, t0); add(R, np.roll(p, 300) * 0.55, t0)
        if b >= 1:
            for k, off in enumerate((0, 1.5, 2.5, 3.5)):
                dd = 0.9 * BEAT if k == 0 else 0.4 * BEAT
                tt = T(dd); f = mtof(ROOTS[b % 4] + (12 if k == 2 else 0))
                bs = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 2.5) * np.minimum(1, tt / 0.01)
                add(bass, bs * (0.0 if b >= 10 else 1.0), t0 + off * BEAT)
        if b >= 1 and b < 10:
            seq = ch + [ch[1] + 12, ch[2] + 12]
            for s16 in range(16):
                if b < 2 and s16 % 2: continue
                m = seq[(s16 * 3 + b) % len(seq)] + 12
                add(arp, pluck(m) * (0.5 if s16 % 4 else 0.75), t0 + s16 * BEAT / 4 + (0.02 if s16 % 2 else 0))
        if 1 <= b < 10:
            sw = 0.055
            for beat in range(4):
                tb = t0 + beat * BEAT
                if beat in (0, 2): add(drums, kick(), tb)
                if beat == 2 and b % 2: add(drums, kick() * 0.7, tb + BEAT * 0.75)
                if beat in (1, 3): add(drums, snare(), tb)
                add(drums, hat(), tb); add(drums, hat() * 0.7, tb + BEAT / 2 + sw)
                if b >= 4 and beat == 3: add(drums, hat(True), tb + BEAT / 2 + sw)
    # light echo on arp
    ad = int(SR * BEAT * 0.75); echo = arp.copy()
    for k in range(1, 4): echo[ad * k:] += arp[:-ad * k] * (0.45 ** k)
    ir = rng.standard_normal(int(SR * 1.6)) * np.exp(-np.arange(int(SR * 1.6)) / SR * 3.2)
    ir /= np.abs(ir).sum() / 12
    wet = fftconv(echo * 0.3 + drums * 0.08 + (L + R) * 0.1, ir) * 0.05
    # sidechain duck from kicks
    duck = np.ones(n)
    for b in range(1, 10):
        for beat in (0, 2):
            i = int((b * 4 + beat) * BEAT * SR); d = np.arange(int(0.3 * SR))
            duck[i:i + len(d)] = np.minimum(duck[i:i + len(d)], 0.55 + 0.45 * (d / len(d)) ** 0.7)
    Lm = (L * duck + echo * 0.18 + bass * 0.32 * duck + drums * 0.42 + wet)
    Rm = (R * duck + np.roll(echo, 900) * 0.18 + bass * 0.32 * duck + drums * 0.42 + np.roll(wet, 700))
    crack = (rng.random(n) < 0.0006) * rng.uniform(-0.25, 0.25, n)
    return Lm + crack, Rm + crack


def engine():
    """Flat-six: rpm + level envelopes keyed to each shot."""
    n = int(SR * DUR); t = np.arange(n) / SR
    key = lambda pts: np.interp(t, [p[0] for p in pts], [p[1] for p in pts])
    rpm = key([(0, 2600), (2.4, 3600), (5, 3300), (6.2, 4200), (7.4, 3900), (10, 5200), (12.2, 6900), (12.4, 4600),
               (14.9, 6300), (15, 4200), (17.3, 4500), (20, 4400), (22.6, 4600), (23.6, 7400), (25, 7600), (27.5, 7600)])
    amp = key([(0, 0.15), (2.0, 0.5), (4.8, 0.35), (5, 0.05), (6.8, 0.65), (7.8, 0.6), (9.6, 0.1), (10, 0.75),
               (14.9, 0.8), (15, 0.08), (17.2, 0.6), (19.8, 0.05), (20, 0.45), (22.6, 0.45), (23.4, 0.7),
               (25.5, 0.15), (27.5, 0.0)])
    # doppler on pass-bys
    dop = 1 + 0.05 * (np.exp(-((t - 6.8) / 0.6) ** 2) * np.sign(6.8 - t) + np.exp(-((t - 17.2) / 0.6) ** 2) * np.sign(17.2 - t))
    f = rpm / 60 * 3 / 2 * dop                    # half-order base gives the flat-six burble
    ph = np.cumsum(2 * np.pi * f / SR)
    s = (np.sin(ph) * 0.5 + np.sin(2 * ph) * 0.9 + np.sin(3 * ph + 0.4) * 0.45 + np.sin(4 * ph) * 0.35
         + np.sin(6 * ph) * 0.25 + np.sin(9 * ph) * 0.08)
    fire = 0.6 + 0.4 * np.maximum(0, np.sin(2 * ph))
    s += rng.standard_normal(n) * 0.35 * fire
    s = np.tanh(s * 1.4)
    s = lp(s, 5) * 0.75 + lp(s, 2) * 0.25
    # gear shift crack
    for ts in (12.25, 14.95):
        i = int(ts * SR); d = T(0.08); s[i:i + len(d)] += rng.standard_normal(len(d)) * np.exp(-d * 60) * 2
    return s * amp


def ambience():
    n = int(SR * DUR); t = np.arange(n) / SR
    w = rng.standard_normal(n)
    rain = (w - lp(w, 3)) * 0.5 + lp(w, 12) * 0.6
    lvl = np.interp(t, [0, 15, 15.1, 20, 20.1, 27.5], [0.22, 0.22, 0.34, 0.34, 0.24, 0.18])
    out = rain * lvl
    for tt, k in ((16.2, 1.0), (18.5, 0.8)):
        d = T(3.2); r = lp(lp(rng.standard_normal(len(d)), 60), 40)
        crack = rng.standard_normal(len(d)) * np.exp(-d * 30) * 0.4
        add(out, (r * 9 * np.exp(-d * 1.2) * np.minimum(1, d / 0.05) + crack) * k, tt)
    for tc in (5.0, 10.0, 15.0, 20.0):
        d = T(0.6); nz = rng.standard_normal(len(d)); env = np.sin(np.pi * np.minimum(1, d / 0.6)) ** 2
        add(out, lp(nz, 6) * env * 0.5, tc - 0.35)
    return out


def build(path, t0=0.0, t1=DUR):
    L, R = music()
    e = engine(); a = ambience()
    n = len(L); t = np.arange(n) / SR
    pan = np.interp(t, [0, 2.4, 5, 5.1, 7, 9.6, 10, 15, 15.1, 17.2, 20, 20.1], [-0.7, 0, 0.1, -0.8, 0, 0.8, 0, 0, -0.8, 0, 0.8, 0])
    mus = 0.62
    Lt = L * mus + e * (0.5 - pan * 0.3) + a * 0.9
    Rt = R * mus + e * (0.5 + pan * 0.3) + np.roll(a, 400) * 0.9
    fade = np.minimum(1, t / 0.4) * np.clip((DUR - t) / 1.5, 0, 1)
    Lt *= fade; Rt *= fade
    pk = max(np.abs(Lt).max(), np.abs(Rt).max()) / 0.92
    st = np.stack([Lt, Rt], 1) / pk
    st = st[int(t0 * SR):int(t1 * SR)]
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype('<i2').tobytes())


if __name__ == '__main__':
    import sys
    build(sys.argv[1] if len(sys.argv) > 1 else 'mix.wav')
