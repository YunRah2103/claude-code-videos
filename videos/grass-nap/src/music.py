"""Original lo-fi loop (EP chords, bass, soft drums, music-box melody, vinyl, birds).
Seamless: rendered over three cycles and the middle cycle is kept, so tails wrap around.
python music.py out.wav
"""
import sys
import wave

import numpy as np

from render import DUR, BEAT

SR = 44100
N = int(round(DUR * SR))
rng = np.random.default_rng(7)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def ep(f, d, v):
    """Rhodes-like electric piano tone."""
    t = np.arange(int(d * SR)) / SR
    env = np.exp(-t * 1.6) * (1 - np.exp(-t * 400))
    mod = np.sin(2 * np.pi * f * t) * 1.6 * np.exp(-t * 5)
    x = np.sin(2 * np.pi * f * t + mod) * env + 0.25 * np.sin(4 * np.pi * f * t) * np.exp(-t * 4)
    return v * x


def pluck(f, d, v):
    """Music-box / kalimba pluck."""
    t = np.arange(int(d * SR)) / SR
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 3.2) + 0.35 * np.sin(2 * np.pi * f * 4.02 * t) * np.exp(-t * 9)
    return v * x * (1 - np.exp(-t * 900))


def bass(f, d, v):
    t = np.arange(int(d * SR)) / SR
    x = np.tanh(1.6 * np.sin(2 * np.pi * f * t)) * np.exp(-t * 1.2) * (1 - np.exp(-t * 200))
    return v * x * np.clip((d - t) * 20, 0, 1)


def kick(v):
    t = np.arange(int(0.45 * SR)) / SR
    f = 45 + 80 * np.exp(-t * 28)
    return v * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)


def snare(v):
    t = np.arange(int(0.3 * SR)) / SR
    n = rng.standard_normal(len(t))
    n = np.convolve(n, np.ones(4) / 4, 'same') - np.convolve(n, np.ones(40) / 40, 'same')
    return v * (0.7 * n * np.exp(-t * 18) + 0.5 * np.sin(2 * np.pi * 185 * t) * np.exp(-t * 25))


def hat(v):
    t = np.arange(int(0.08 * SR)) / SR
    n = rng.standard_normal(len(t))
    n = n - np.convolve(n, np.ones(6) / 6, 'same')
    return v * n * np.exp(-t * 60)


def chirp(v):
    out = []
    for _ in range(int(rng.integers(2, 5))):
        d = rng.uniform(0.05, 0.11)
        t = np.arange(int(d * SR)) / SR
        f0 = rng.uniform(3200, 4200)
        f = f0 + rng.uniform(800, 1600) * np.sin(np.pi * t / d)
        out.append(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / d) ** 2)
        out.append(np.zeros(int(rng.uniform(0.03, 0.08) * SR)))
    return v * np.concatenate(out)


CHORDS = [  # one per bar (MIDI notes); root for the bass
    (53, [57, 60, 64, 67]),      # Fmaj9 (A C E G)
    (52, [55, 59, 62, 65]),      # Em7(b6-ish colour) G B D F -> soft
    (50, [57, 60, 64, 65]),      # Dm9 (A C E F)
    (48, [55, 59, 62, 64]),      # Cmaj9 (G B D E)
    (53, [57, 60, 64, 67]),
    (52, [55, 59, 62, 67]),
    (50, [57, 60, 62, 65]),
    (55, [57, 60, 62, 65]),      # G9sus -> back to F
]
MELODY = [  # (beat, midi, length beats) bars 1-8, pentatonic-ish
    (0.5, 76, 1), (1.5, 74, .5), (2, 72, 1.5), (4.5, 74, .5), (5, 76, 1), (6.5, 79, 1.5),
    (8.5, 77, .5), (9, 76, 1), (10.5, 72, 1.5), (13, 74, 1), (14, 72, .5), (14.5, 69, 1.5),
    (16.5, 76, .5), (17, 79, 1), (18.5, 81, 1), (20, 79, .5), (20.5, 76, 1.5),
    (24.5, 77, .5), (25, 76, .5), (25.5, 74, 1), (27, 72, 1), (28.5, 74, .5), (29, 72, 1), (30, 69, 1.5),
]


def swing(b):
    return b + (0.08 if (b * 2) % 2 == 1 else 0)


def render():
    L = np.zeros(N * 3 + SR * 4); R = np.zeros_like(L)

    def add(x, at, pan=0.0, rev=False):
        i = int(at * SR)
        gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        L[i:i + len(x)] += x * gl * 1.41
        R[i:i + len(x)] += x * gr * 1.41

    for cyc in range(3):
        base = cyc * DUR
        for bar, (root, notes) in enumerate(CHORDS):
            t0 = base + bar * 4 * BEAT
            for k, m in enumerate(notes):                       # strummed chord + anticipation stab
                add(ep(hz(m), 3.2, 0.11), t0 + k * 0.012, pan=-0.3 + 0.2 * k)
                add(ep(hz(m), 1.4, 0.05), t0 + swing(2.5) * BEAT + k * 0.01, pan=0.3 - 0.2 * k)
            add(bass(hz(root - 12), BEAT * 2.2, 0.26), t0)
            add(bass(hz(root - 12), BEAT * 1.2, 0.18), t0 + swing(2.5) * BEAT)
            for b in range(4):
                if b in (0,) or (b == 2 and bar % 2 == 1):
                    add(kick(0.55), t0 + b * BEAT)
                if b == 2 and bar % 2 == 0:
                    add(kick(0.4), t0 + swing(2.5) * BEAT)
                if b in (1, 3):
                    add(snare(0.11), t0 + b * BEAT, pan=0.05)
            for h in range(8):
                add(hat(0.025 if h % 2 else 0.04), t0 + swing(h / 2) * BEAT, pan=0.35)
        for (b, m, ln) in MELODY:
            add(pluck(hz(m), ln * BEAT + 1.2, 0.09), base + swing(b) * BEAT, pan=0.15)
            add(pluck(hz(m + 12), ln * BEAT + 0.6, 0.02), base + swing(b) * BEAT + 0.003, pan=-0.2)
        for _ in range(5):
            add(chirp(0.035), base + rng.uniform(0, DUR - 1), pan=float(rng.uniform(-0.8, 0.8)))

    # reverb: decaying-noise impulse response, FFT convolution
    ir_t = np.arange(int(1.6 * SR)) / SR
    irL = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 3.2); irR = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 3.2)
    irL[:300] = 0; irR[:300] = 0
    n2 = 1 << int(np.ceil(np.log2(len(L) + len(ir_t))))
    wetL = np.fft.irfft(np.fft.rfft(L, n2) * np.fft.rfft(irL, n2), n2)[:len(L)]
    wetR = np.fft.irfft(np.fft.rfft(R, n2) * np.fft.rfft(irR, n2), n2)[:len(R)]
    L = L + wetL * 0.035; R = R + wetR * 0.035
    # lo-fi tone: gentle low-pass
    for ch in (L, R):
        F = np.fft.rfft(ch)
        f = np.fft.rfftfreq(len(ch), 1 / SR)
        F *= 1 / np.sqrt(1 + (f / 3000) ** 4)
        ch[:] = np.fft.irfft(F, len(ch))
    seg = slice(N, 2 * N)
    L, R = L[seg].copy(), R[seg].copy()
    # vinyl crackle + room hiss (loop-safe: generated at loop length)
    crack = np.zeros(N)
    idx = rng.integers(0, N, 260)
    crack[idx] = rng.uniform(-1, 1, len(idx)) * rng.uniform(0.05, 0.25, len(idx))
    crack = np.convolve(crack, [1, 0.6, 0.3], 'same')
    hiss = np.convolve(rng.standard_normal(N), np.ones(8) / 8, 'same') * 0.0015
    L += crack * 0.12 + hiss; R += np.roll(crack, 37) * 0.12 + np.roll(hiss, 1234)
    st = np.stack([L, R], 1)
    st = np.tanh(st * 1.1) / 1.1
    rms = np.sqrt((st ** 2).mean())
    st *= 10 ** (-17.0 / 20) / rms
    st *= min(1.0, 10 ** (-1 / 20) / np.abs(st).max())
    return st


if __name__ == '__main__':
    st = render()
    with wave.open(sys.argv[1], 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype('<i2').tobytes())
    print('peak dB', round(20 * np.log10(np.abs(st).max()), 2), 'rms dB', round(20 * np.log10(np.sqrt((st ** 2).mean())), 2), 'sec', len(st) / SR)
