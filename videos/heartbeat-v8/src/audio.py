"""Sound for heartbeat-v8 (all synthesised, no recorded car audio).

Engine: physically inspired pulse model. Every 90 deg of crank one cylinder fires (S65 firing order
1-5-4-8-6-3-7-2, banks A=1-4, B=5-8 -> per-bank pattern A B A B B A B A = cross-plane burble). Each firing is an
exhaust pressure pulse into its bank's pipe (stereo L/R), through a pipe comb resonance and an rpm-dependent
muffler; plus induction howl and the high-rpm metallic scream, limiter cuts and overrun crackle.
The rpm follows the on-screen counters (firing rate = counter, rpm = firing rate x 15).
python audio.py VO.wav SILENT.mp4 FINAL.mp4
"""
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, lfilter, sosfilt

_spec = importlib.util.spec_from_file_location('hb_render', Path(__file__).with_name('render.py'))
R = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(R)

SR = 48000
N = int(R.DUR * SR)
T = np.arange(N) / SR
rng = np.random.default_rng(11)


def filt(x, kind, fc, order=2):
    return sosfilt(butter(order, fc, kind, fs=SR, output='sos'), x, axis=0)


def ctl(fn, rate=1000):
    """sample a control function of time at 1 kHz and interpolate to audio rate"""
    tt = np.arange(0, R.DUR, 1 / rate)
    return np.interp(T, tt, np.array([fn(t) for t in tt]))


def smooth(x, sec):
    k = max(int(sec * SR), 1)
    return np.convolve(x, np.ones(k) / k, mode='same')


# ---------------------------------------------------------------- engine control: rpm + load + "slow-motion" amount
def engine_state(t):
    c0, c1, c2, c3, c4 = R.CASC[:5]
    if t < c0[0] + 0.45:
        return 0.0, 0.0, 0.0
    if t < c1[0] + 0.40:                                   # rev to 8400 as the counter races to 560 fires/s
        fires = max(60.0, 560 * R.eout((t - (c0[0] + 0.7)) / (R.HIT560 - c0[0] - 0.7)))
        if t > R.HIT560:
            fires = 560 - 20 * (0.5 + 0.5 * math.sin(2 * math.pi * 7 * t))      # bouncing on the limiter
        return fires * 15, R.sstep(c0[0] + 0.4, c0[0] + 0.75, t), 0.0
    if t < c2[0] + 0.40:                                   # slow-motion cutaway: pitched-down, filtered
        fl = max(60.0, 280 * R.eout((t - (c1[0] + 0.7)) / (R.HIT280 - c1[0] - 0.7)))
        return fl * 15, 0.8, 1.0
    if t < c4[0] + 0.05:                                   # the car: on-screen rpm counter
        return R.rpm(t), 1.0, 0.0
    return 950.0, 0.55 * min(R.hl_v8(t), 1.0), 0.0         # poll: lumpy idle while "V8" is highlighted


st = np.array([engine_state(t) for t in np.arange(0, R.DUR, 1 / 1000)])
tt = np.arange(len(st)) / 1000
rpm = np.interp(T, tt, st[:, 0])
load = smooth(np.interp(T, tt, st[:, 1]), 0.05)
slow = smooth(np.interp(T, tt, st[:, 2]), 0.15)
drpm = np.gradient(smooth(rpm, 0.05)) * SR

crank = 2 * np.pi * np.cumsum(rpm / 60) / SR                        # crank angle
ev = np.nonzero(np.diff(np.floor(crank / (np.pi / 2))) > 0)[0]      # one firing every 90 deg
BANK = [0, 1, 0, 1, 1, 0, 1, 0]                                     # 1-5-4-8-6-3-7-2


def pulse_kernel(r):
    n = int(0.022 * SR)
    t = np.arange(n) / SR
    tau = 0.0032 - 0.0018 * min(r / 8400, 1)                        # sharper pulses at high rpm
    p = (np.exp(-t / tau) - np.exp(-t / 0.00025))
    p += 0.35 * np.sin(2 * np.pi * 165 * t) * np.exp(-t / 0.007)     # pipe body thump
    p += 0.25 * rng.standard_normal(n) * np.exp(-t / 0.0015)          # combustion grit
    return p


exh = np.zeros((N, 2))
for k, i in enumerate(ev):
    r = rpm[i]
    if load[i] < 1e-3:
        continue
    a = load[i] * (0.85 + 0.3 * rng.random())
    if r > 8300 and rng.random() < 0.35:                              # rev-limiter ignition cut -> stutter
        continue
    kern = pulse_kernel(r) * a
    b = BANK[k % 8]
    n = min(len(kern), N - i)
    exh[i:i + n, b] += kern[:n]
    exh[i:i + n, 1 - b] += 0.35 * kern[:n]

for ch in range(2):                                                   # exhaust pipe resonance (comb)
    D = int(SR * (0.0062 if ch == 0 else 0.0067))
    a = np.zeros(D + 1); a[0] = 1; a[-1] = -0.42
    exh[:, ch] = lfilter([1.0], a, exh[:, ch])
w = np.clip((rpm - 1500) / 6500, 0, 1)[:, None]                       # muffler opens with rpm
exh = filt(exh, 'low', 700) * (1 - w) + filt(exh, 'low', 4200) * w
exh = filt(exh, 'high', 35)

fire_hz = rpm * 4 / 60
ph = 2 * np.pi * np.cumsum(fire_hz) / SR
scream = (np.sin(ph) + 0.6 * np.sin(2 * ph + 0.3) + 0.35 * np.sin(3 * ph + 1.1) + 0.15 * np.sin(5 * ph))
scream *= np.clip((rpm - 5200) / 3200, 0, 1) ** 2 * load            # S65 high-rpm metallic howl
intake = filt(rng.standard_normal(N), 'band', [350, 2600]) * load * (rpm / 8400) ** 1.6
eng = exh / (np.abs(exh).max() + 1e-9) + 0.22 * scream[:, None] + 0.18 * intake[:, None] * np.array([0.9, 1.0])

pops = np.zeros((N, 2))                                               # overrun crackle when the revs fall
for i in np.nonzero((drpm < -2500) & (rpm > 2500))[0][::400]:
    if rng.random() < 0.55:
        n = int(0.05 * SR); t = np.arange(n) / SR
        p = (filt(rng.standard_normal(n), 'band', [300, 3000]) * np.exp(-t / 0.012) + 0.6 * np.sin(2 * np.pi * 90 * t) * np.exp(-t / 0.02))
        pan = rng.random()
        m = min(n, N - i)
        pops[i:i + m] += p[:m, None] * np.array([1 - 0.5 * pan, 0.5 + 0.5 * pan]) * 0.8
eng = np.tanh(1.4 * (eng + pops)) * (1 - 0.0 * slow[:, None])
eng = eng * (1 - slow[:, None]) + filt(eng, 'low', 900) * slow[:, None] * 1.3  # slow-mo = muffled

# ---------------------------------------------------------------- heartbeat lub-dub
heart = np.zeros(N)


def thump(t0, f0, f1, amp, dec):
    i = int(t0 * SR)
    if not 0 <= i < N:
        return
    n = min(int(0.35 * SR), N - i); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.03)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * (1 - np.exp(-t / 0.004)) * np.exp(-t / dec)
    s += 0.25 * filt(rng.standard_normal(n), 'low', 180) * np.exp(-t / 0.03)
    heart[i:i + n] += amp * s


for k in range(17):
    tb = (k + 0.31) * R.BP
    if tb < R.CASC[0][0] + 0.3 or tb > R.CASC[-1][0]:
        thump(tb, 95, 48, 1.0, 0.10); thump(tb + 0.24, 120, 60, 0.6, 0.07)
heart = np.tanh(1.5 * heart)

# ---------------------------------------------------------------- transitions: noise swell -> falling digital rain -> landing thud
fx = np.zeros((N, 2))
for (t0, d, a, b) in R.CASC:
    i0, i1 = int((t0 - 0.5) * SR), int(t0 * SR)
    n = i1 - i0; u = np.arange(n) / n
    swell = np.zeros(n)
    for j, (lo, hi) in enumerate([(300, 900), (900, 2500), (2500, 7000)]):   # rising band of noise
        swell += filt(rng.standard_normal(n), 'band', [lo, hi]) * np.clip(u * 3 - j, 0, 1)
    fx[i0:i1] += (swell * u ** 2.5 * 0.35)[:, None]
    j0, j1 = i1, min(int((t0 + d) * SR), N)
    for _ in range(int(160 * d)):                                    # falling pitched ticks (characters dropping)
        k = int(rng.integers(j0, max(j0 + 1, j1 - 600)))
        prog = (k - j0) / max(j1 - j0, 1)
        f = 3200 * (0.25 ** prog) * (0.85 + 0.3 * rng.random())
        m = 400; tt = np.arange(m) / SR
        blip = np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.0025) * 0.16
        pan = rng.random()
        fx[k:k + m] += blip[:, None] * np.array([1 - pan, pan])
    n = j1 - j0; tt = np.arange(n) / SR                                   # downward whoosh
    wh = filt(rng.standard_normal(n), 'low', 1800) * np.sin(np.pi * np.clip(tt / (d * 0.9), 0, 1)) * 0.22
    fx[j0:j1] += wh[:, None]
    k = int((t0 + d * 0.92) * SR); n = min(int(0.25 * SR), N - k); tt = np.arange(n) / SR
    fx[k:k + n] += (0.35 * np.sin(2 * np.pi * (70 - 25 * tt) * tt) * np.exp(-tt / 0.07))[:, None]   # landing

for (te, sc) in R.typing_events():                                   # terminal key clicks
    k = int(te * SR); m = 300
    if k + m < N:
        c = filt(rng.standard_normal(m), 'band', [1800, 5200]) * np.exp(-np.arange(m) / 40) * 0.12
        pan = 0.35 + 0.3 * rng.random()
        fx[k:k + m] += c[:, None] * np.array([1 - pan, pan])


def hit(t0, amp):
    i = int(t0 * SR); n = min(int(1.4 * SR), N - i); t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(38 + 50 * np.exp(-t / 0.05)) / SR) * np.exp(-t / 0.45)
    crack = filt(rng.standard_normal(n), 'band', [600, 6000]) * np.exp(-t / 0.03)
    fx[i:i + n] += (amp * (1.0 * boom + 0.5 * crack))[:, None]


hit(R.HIT560, 0.9)
hit(R.HIT280, 0.45)
hit(R.SCREAM, 0.35)
ev_hl = ctl(lambda t: min(R.hl_ev(t), 1.0))
ev_tone = 0.035 * smooth(ev_hl, 0.08) * np.sin(2 * np.pi * np.cumsum(700 + 260 * smooth(ev_hl, 0.4)) / SR)
fx += ev_tone[:, None]

# ---------------------------------------------------------------- reverb on the effects bus (stereo exponential-noise IR)
irn = int(0.9 * SR); ti = np.arange(irn) / SR
ir = filt(rng.standard_normal((irn, 2)), 'low', 5000) * np.exp(-ti / 0.25)[:, None]
ir /= np.abs(ir).sum(0)
wet = np.stack([fftconvolve(fx[:, c], ir[:, c])[:N] for c in range(2)], 1)
fx = fx + 2.2 * wet

# ---------------------------------------------------------------- mix: VO on top, ducking, near-silence before the question
vo = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', sys.argv[1], '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                  capture_output=True, check=True).stdout, np.float32).astype(np.float64)
vo = np.pad(vo, (0, max(0, N - len(vo))))[:N]
venv = smooth(np.abs(vo), 0.10); venv /= venv.max()
duck = (1 - 0.45 * np.clip(venv * 3, 0, 1))[:, None]
hush = 1 - 0.95 * ctl(lambda t: R.sstep(R.CASC[4][0] + 0.02, R.CASC[4][0] + 0.10, t) * (1 - R.sstep(R.wt('loud') - 0.08, R.wt('loud'), t)))
sfx = (0.30 * eng + 0.50 * heart[:, None] + 0.60 * fx) * duck * hush[:, None]
mix = np.stack([vo, vo], 1) + sfx
mix /= np.abs(mix).max() * 1.12

out = Path(sys.argv[3]).resolve()
wav = out.with_name('mix.wav')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f64le', '-ar', str(SR), '-ac', '2', '-i', '-', str(wav)],
               input=mix.astype(np.float64).tobytes(), check=True)
m = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(wav), '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                   capture_output=True, text=True).stderr
js = json.loads(m[m.rindex('{'):m.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}:"
      f"measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true,aresample=48000")
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', sys.argv[2], '-i', str(wav), '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                '-af', af, '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest', '-movflags', '+faststart', str(out)], check=True)
print('wrote', out)
