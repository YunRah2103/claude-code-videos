"""Original soft lo-fi bed: Rhodes-like keys, music-box lead, pad, soft drums, rain + vinyl."""
import numpy as np
import wave
import sys

SR = 48000
DUR = 8.2
BPM = 72
BEAT = 60 / BPM
N = int(SR * DUR)
rng = np.random.default_rng(8)


def f(m):  # midi -> Hz, tuned slightly sharp for a warm detuned-tape feel
    return 440 * 2 ** ((m - 69 + 0.35) / 12)


def env(n, a, d, s=0.0, r=None):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * (s + (1 - s) * np.exp(-t / d))
    if r:
        e *= np.clip((n / SR - t) / r, 0, 1)
    return e


def rhodes(m, dur, vel=0.5):
    n = int(dur * SR); t = np.arange(n) / SR; fr = f(m)
    mod = np.sin(2 * np.pi * fr * t) * 1.2 * np.exp(-t * 6)
    x = np.sin(2 * np.pi * fr * t + mod) + 0.25 * np.sin(2 * np.pi * 2 * fr * t) * np.exp(-t * 3)
    x *= env(n, 0.004, 0.9, 0.0, 0.08) * (1 + 0.15 * np.sin(2 * np.pi * 4.5 * t))
    return x * vel


def musicbox(m, dur, vel=0.3):
    n = int(dur * SR); t = np.arange(n) / SR; fr = f(m)
    x = np.sin(2 * np.pi * fr * t) + 0.3 * np.sin(2 * np.pi * 3 * fr * t) * np.exp(-t * 9) + \
        0.12 * np.sin(2 * np.pi * 5.4 * fr * t) * np.exp(-t * 16)
    return x * env(n, 0.002, 0.8, 0.0, 0.08) * vel


def pad(ms, dur, vel=0.12):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for m in ms:
        for det in (-0.06, 0.0, 0.07):
            fr = f(m + det)
            ph = rng.uniform(0, 6.28)
            x += np.sin(2 * np.pi * fr * t + ph) + 0.3 * np.sin(4 * np.pi * fr * t + ph)
    a = np.minimum(1, t / 0.6) * np.clip((dur - t) / 0.5, 0, 1)
    return x * a * vel / len(ms)


def kick(vel=0.6):
    n = int(0.35 * SR); t = np.arange(n) / SR
    fr = 48 + 70 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 9) * vel


def snare(vel=0.25):
    n = int(0.3 * SR); t = np.arange(n) / SR
    nz = rng.normal(0, 1, n)
    nz = np.convolve(nz, np.ones(6) / 6, 'same')
    return (nz * np.exp(-t * 16) + 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25)) * vel


def hat(vel=0.06):
    n = int(0.06 * SR); t = np.arange(n) / SR
    nz = rng.normal(0, 1, n); nz = nz - np.convolve(nz, np.ones(4) / 4, 'same')
    return nz * np.exp(-t * 70) * vel


def place(buf, x, t0, pan=0.0):
    i = int(t0 * SR)
    if i >= N:
        return
    x = x[:N - i]
    buf[0, i:i + len(x)] += x * (1 - pan) ** 0.5
    buf[1, i:i + len(x)] += x * (1 + pan) ** 0.5


def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, 'same')


def _freqs(n):
    return np.fft.rfftfreq(n, 1 / SR)


def onepole(x, fc):
    """Gentle 1st-order low-pass applied in the frequency domain."""
    fr = _freqs(len(x))
    return np.fft.irfft(np.fft.rfft(x) / np.sqrt(1 + (fr / fc) ** 2), len(x))


def highpass(x, fc):
    fr = _freqs(len(x))
    g = (fr / fc) ** 2 / (1 + (fr / fc) ** 2)
    return np.fft.irfft(np.fft.rfft(x) * g, len(x))


def reverb(x, dec=1.6, mix=0.3):
    n = int(dec * SR)
    ir = rng.normal(0, 1, n) * np.exp(-np.arange(n) / SR * 5 / dec)
    ir = lowpass(ir, 6)
    ir /= np.sqrt((ir ** 2).sum())
    from numpy.fft import rfft, irfft
    L = len(x) + n
    y = irfft(rfft(x, L) * rfft(ir, L), L)[:len(x)]
    return x * (1 - mix) + y * mix


def build():
    keys = np.zeros((2, N)); lead = np.zeros((2, N)); drums = np.zeros((2, N)); pads = np.zeros((2, N))
    # F#m9 | Dmaj9 | Bm9 | C#m7 | F#m9  (2 beats each)
    chords = [[54, 57, 61, 64, 68], [50, 54, 57, 61, 64], [47, 50, 54, 57, 61], [49, 52, 56, 59, 64], [54, 57, 61, 64, 68]]
    for i, ch in enumerate(chords):
        t0 = i * 2 * BEAT
        place(pads, pad(ch[1:], 2 * BEAT + 0.6, 0.08), t0)
        place(pads, np.sin(2 * np.pi * f(ch[0]) * np.arange(int(2 * BEAT * SR)) / SR) *
              env(int(2 * BEAT * SR), 0.02, 1.2, 0.3, 0.1) * 0.06, t0)
        # rhodes arpeggio in eighths
        arp = [ch[1], ch[2], ch[3], ch[4], ch[3], ch[2], ch[4] + 0, ch[3]]
        for k, m in enumerate(arp):
            place(keys, rhodes(m + 12, 0.9, 0.22 + 0.06 * (k % 2 == 0)), t0 + k * BEAT / 4 + 0.01 * rng.random(), pan=0.3 * np.sin(k))
    # music-box melody enters at ~2.1s, call-and-answer phrase
    mel = [(2.10, 80), (2.40, 78), (2.48, 76), (2.70, 73), (2.95, 76), (3.40, 81), (3.55, 80), (3.85, 76),
           (4.18, 78), (4.48, 76), (4.70, 73), (4.88, 71), (5.33, 73), (5.50, 76), (5.85, 78), (6.45, 73),
           (6.62, 71), (7.02, 85), (7.20, 83), (7.38, 80), (7.55, 78), (7.78, 80), (7.90, 83), (8.08, 85)]
    for (t0, m) in mel:
        v = 0.30 if t0 < 7 else 0.42
        place(lead, musicbox(m, 1.4, v), t0, pan=-0.2)
        place(lead, musicbox(m - 12, 0.9, v * 0.35), t0, pan=0.2)
    # soft drums from bar 2, fuller after 7s
    t = 2 * BEAT * 2 - BEAT
    while t < DUR:
        b = round((t) / BEAT)
        loud = 1.0 if t >= 6.9 else 0.55
        if b % 2 == 0:
            place(drums, kick(0.3 * loud), t)
        else:
            place(drums, snare(0.22 * loud), t + 0.02)
        for h in range(2):
            place(drums, hat(0.05 * loud), t + h * BEAT / 2 + 0.015 * h)
        t += BEAT
    place(drums, kick(0.35), 7.0)
    # rain + vinyl crackle bed
    nz = rng.normal(0, 1, (2, N))
    rain = np.stack([highpass(onepole(nz[i], 6000), 90) for i in range(2)]) * 0.03
    crack = np.zeros((2, N))
    for _ in range(int(DUR * 25)):
        i = int(rng.integers(0, N - 50)); crack[:, i:i + 3] += rng.normal(0, 0.25, 3)
    mix = keys * 0.8 + lead * 1.1 + pads * 0.7 + drums * 0.6
    # tape wobble: gentle delay modulation
    tt = np.arange(N) / SR
    wob = (0.0018 * np.sin(2 * np.pi * 0.6 * tt) + 0.0006 * np.sin(2 * np.pi * 5.1 * tt)) * SR
    idx = np.clip(np.arange(N) - 120 - wob, 0, N - 1)
    mix = np.stack([np.interp(idx, np.arange(N), mix[i]) for i in range(2)])
    mix = np.stack([reverb(highpass(onepole(mix[i], 7000), 140), 1.8, 0.3) for i in range(2)])
    out = mix + rain + crack * 0.6
    # energy curve: quiet fade-in, steady, lift at 7s (like the reference)
    g = np.interp(tt, [0, 0.4, 2.0, 6.9, 7.0, DUR], [0.07, 0.12, 0.45, 0.55, 1.25, 1.2])
    out *= g
    out[:, :int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
    out[:, -int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))
    out = np.tanh(out * 1.3) / np.tanh(1.3)
    out *= 0.075 / np.sqrt((out ** 2).mean())   # loudness close to the reference (~-19 LUFS)
    out = np.clip(out, -0.98, 0.98)
    return out


if __name__ == '__main__':
    out = build()
    pcm = (out.T * 32767).astype(np.int16)
    with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'music.wav', 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
