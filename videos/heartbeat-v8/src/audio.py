"""Sound for heartbeat-v8: synthesised V8 tied to the on-screen counters, heartbeat, risers, cascade rain,
impacts, near-silence before the final question; VO ducking; loudnorm to -14 LUFS; mux with the silent render.
python audio.py VO.wav SILENT.mp4 FINAL.mp4
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

import importlib.util
_spec = importlib.util.spec_from_file_location('hb_render', Path(__file__).with_name('render.py'))
R = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(R)

SR = 48000
N = int(R.DUR * SR)
T = np.arange(N) / SR
rng = np.random.default_rng(7)


def smooth_env(x, sec):
    k = max(int(sec * SR), 1)
    return np.convolve(x, np.ones(k) / k, mode='same')


def lp(x, fc):
    from scipy.signal import butter, sosfilt
    return sosfilt(butter(2, fc, 'low', fs=SR, output='sos'), x)


def hp(x, fc):
    from scipy.signal import butter, sosfilt
    return sosfilt(butter(2, fc, 'high', fs=SR, output='sos'), x)


def bp(x, f0, f1):
    from scipy.signal import butter, sosfilt
    return sosfilt(butter(2, [f0, f1], 'band', fs=SR, output='sos'), x)


vec = np.vectorize


# ---------------------------------------------------------------- engine: firing frequency follows the counters
def firing_hz(t):
    c0, c1, c2, c3, c4 = R.CASC[:5]
    if t < c0[0] + 0.5:
        return 0.0, 0.0
    if t < c1[0] + 0.45:                                   # scene 1: counter to 560 = firing frequency
        f = max(45.0, 560 * R.eout((t - (c0[0] + 0.7)) / (R.HIT560 - c0[0] - 0.7)))
        return f, R.sstep(c0[0] + 0.4, c0[0] + 0.8, t)
    if t < c2[0] + 0.45:                                   # scene 2: counter to 280 (slow-motion cutaway)
        return max(45.0, 280 * R.eout((t - (c1[0] + 0.7)) / (R.HIT280 - c1[0] - 0.7))), 0.85
    if t < c4[0] + 0.1:                                    # scenes 3/4: rpm counter -> rpm / 60 * 4
        return R.rpm(t) / 60 * 4, 1.0
    return 50.0, 0.35 * min(R.hl_v8(t), 1.0)               # poll: idle burble while "V8" is highlighted


ctl = np.array([firing_hz(t) for t in np.arange(0, R.DUR, 1 / 1000)])
f_eng = np.interp(T, np.arange(len(ctl)) / 1000, ctl[:, 0])
g_eng = smooth_env(np.interp(T, np.arange(len(ctl)) / 1000, ctl[:, 1]), 0.08)
ph = 2 * np.pi * np.cumsum(f_eng) / SR
eng = sum((1 / k ** 0.9) * np.sin(k * ph) for k in range(1, 9))
eng += 0.45 * np.sin(ph / 4) + 0.30 * np.sin(ph / 2 + 0.7)          # crossplane burble
eng += 0.9 * rng.standard_normal(N) * (0.5 + 0.5 * np.cos(ph)) ** 6   # combustion noise per firing
eng = lp(np.tanh(1.6 * eng / 3), 5200) * g_eng

# ---------------------------------------------------------------- heartbeat (lub-dub when each spike reaches the trace head)
heart = np.zeros(N)


def thump(t0, f, amp, dec=0.11):
    i = int(t0 * SR)
    if i >= N or i < 0:
        return
    n = min(int(0.4 * SR), N - i)
    tt = np.arange(n) / SR
    heart[i:i + n] += amp * np.sin(2 * np.pi * f * tt * (1 - 0.25 * tt)) * np.exp(-tt / dec)


for k in range(17):
    tb = (k + 0.31) * R.BP
    if tb < R.CASC[0][0] + 0.3 or tb > R.CASC[-1][0] - 0.1:
        thump(tb, 58, 1.0); thump(tb + 0.27, 50, 0.7)

# ---------------------------------------------------------------- risers, cascade rain, impacts, EV whine
fx = np.zeros(N)
for (t0, d, a, b) in R.CASC:
    i0, i1 = int((t0 - 0.55) * SR), int(t0 * SR)
    n = i1 - i0
    u = np.arange(n) / n
    sweep = np.sin(2 * np.pi * np.cumsum(300 * (5 ** u)) / SR)
    noise = hp(rng.standard_normal(n), 900) * (0.3 + 0.7 * u)
    fx[i0:i1] += (0.35 * sweep + 0.5 * noise) * u ** 2.2 * 0.5
    j0, j1 = i1, min(int((t0 + d) * SR), N)                          # character rain during the cascade
    for _ in range(int(130 * d)):
        k = rng.integers(j0, max(j0 + 1, j1 - 400))
        m = 300
        fx[k:k + m] += 0.18 * hp(rng.standard_normal(m), 2500) * np.exp(-np.arange(m) / 60)


def impact(t0, amp):
    i = int(t0 * SR); n = min(int(0.9 * SR), N - i)
    tt = np.arange(n) / SR
    body = np.sin(2 * np.pi * (52 - 14 * tt) * tt) * np.exp(-tt / 0.28)
    snap = lp(rng.standard_normal(n), 2500) * np.exp(-tt / 0.025)
    fx[i:i + n] += amp * (0.9 * body + 0.5 * snap)


impact(R.HIT560, 0.9)
impact(R.HIT280, 0.5)
ev = np.array([min(R.hl_ev(t), 1.0) for t in np.arange(0, R.DUR, 1 / 1000)])
fx += 0.05 * smooth_env(np.interp(T, np.arange(len(ev)) / 1000, ev), 0.05) * (np.sin(2 * np.pi * 1760 * T) + 0.4 * np.sin(2 * np.pi * 3520 * T))

# ---------------------------------------------------------------- mix
vo = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', sys.argv[1], '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                  capture_output=True, check=True).stdout, np.float32).astype(np.float64)
vo = np.pad(vo, (0, max(0, N - len(vo))))[:N]
vo_env = smooth_env(np.abs(vo), 0.12)
vo_env /= vo_env.max()
duck = 1 - 0.5 * np.clip(vo_env * 3, 0, 1)
near_silence = 1 - 0.96 * np.array([R.sstep(R.CASC[4][0] + 0.02, R.CASC[4][0] + 0.10, t) * (1 - R.sstep(R.wt('loud') - 0.08, R.wt('loud'), t))
                                    for t in T[::48]]).repeat(48)[:N]
sfx = (0.28 * eng + 0.55 * heart + 0.55 * fx) * duck * near_silence
mix = vo * 1.0 + sfx
mix = np.stack([mix, mix], 1)
mix /= np.abs(mix).max() * 1.12
out = Path(sys.argv[3]).resolve()
wav = out.with_name('mix.wav')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f64le', '-ar', str(SR), '-ac', '2', '-i', '-', str(wav)],
               input=mix.astype(np.float64).tobytes(), check=True)
# two-pass loudnorm to -14 LUFS, -1.5 dBTP
m = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(wav), '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                   capture_output=True, text=True).stderr
js = json.loads(m[m.rindex('{'):m.rindex('}') + 1])
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}:"
      f"measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true,aresample=48000")
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', sys.argv[2], '-i', str(wav), '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                '-af', af, '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest', '-movflags', '+faststart', str(out)], check=True)
print('wrote', out)
