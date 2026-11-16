"""Sound for same-v8 (all synthesised): riser + falling glyph ticks + landing into each cascade, soft impacts on
the price reveals, key clicks for the typed code, a whoosh per engine-cover jump, near-silence before the final
question. Quiet effects bed so the user's own music fits on top. VO: one Gemini Orus clip, lead trimmed.
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


hit(R.LAND_U, 0.30)
hit(R.LAND_Q, 0.30)
hit(R.LAND_GAP, 0.38)
hit(R.wend('eight') + 0.05, 0.18)
for j0, j1 in (R.JUMP1, R.JUMP2):                                    # cover jumps: short whoosh + click on landing
    i0, i1 = int(j0 * SR), int(j1 * SR); n = i1 - i0; u = np.arange(n) / n
    fx[i0:i1] += (filt(rng.standard_normal(n), 'band', [500, 3500]) * np.sin(np.pi * u) ** 2 * 0.16)[:, None]
    hit(j1, 0.10)

# ---------------------------------------------------------------- reverb on the effects bus (stereo exponential-noise IR)
irn = int(0.9 * SR); ti = np.arange(irn) / SR
ir = filt(rng.standard_normal((irn, 2)), 'low', 5000) * np.exp(-ti / 0.25)[:, None]
ir /= np.abs(ir).sum(0)
wet = np.stack([fftconvolve(fx[:, c], ir[:, c])[:N] for c in range(2)], 1)
fx = fx + 2.2 * wet

# ---------------------------------------------------------------- mix: VO on top, ducking, near-silence before the question
vo = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', sys.argv[1], '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                  capture_output=True, check=True).stdout, np.float32).astype(np.float64)
vo = vo[int(R.VO_TRIM * SR):]
vo = np.pad(vo, (0, max(0, N - len(vo))))[:N]
fade = np.ones(N); k = int(0.02 * SR); fade[-k:] = np.linspace(1, 0, k)
venv = smooth(np.abs(vo), 0.10); venv /= venv.max()
duck = (1 - 0.5 * np.clip(venv * 3, 0, 1))[:, None]
hush = 1 - 0.92 * ctl(lambda t: R.sstep(R.HUSH[0], R.HUSH[0] + 0.06, t) * (1 - R.sstep(R.HUSH[1], R.HUSH[1] + 0.05, t)))
sfx = 0.55 * fx * duck * hush[:, None]
mix = (np.stack([vo, vo], 1) + sfx) * fade[:, None]
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
