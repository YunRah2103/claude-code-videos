"""Sound for tyre-patch (all synthesised). Clean, musical bed + road/tyre roar that follows the wheel speed, soft UI.

Music: warm detuned pad (Am9 - Fmaj7 - C - G), soft sub pulse at 96 bpm with off-beat ticks, filter opens through the
video and closes for the last line. Road: band-passed noise + tyre whine scaled by the on-screen wheel speed.
UI: quiet key ticks while captions type, sine pings with the radar rings, rounded sub hits on hand / sheet / fourteen,
airy whooshes + falling glints on the two waterfall transitions.
python audio.py VO.wav SILENT.mp4 FINAL.mp4
"""
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

_spec = importlib.util.spec_from_file_location('tp_render', Path(__file__).with_name('render.py'))
R = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(R)

SR = 48000
N = int(R.DUR * SR)
T = np.arange(N) / SR
rng = np.random.default_rng(7)


def filt(x, kind, fc, order=2):
    return sosfilt(butter(order, fc, kind, fs=SR, output='sos'), x, axis=0)


def ctl(fn, rate=500):
    tt = np.arange(0, R.DUR + 1 / rate, 1 / rate)
    return np.interp(T, tt, np.array([float(fn(t)) for t in tt]))


def smooth(x, sec):
    k = max(int(sec * SR), 1)
    return np.convolve(x, np.ones(k) / k, mode='same')


def mtof(m):
    return 440 * 2 ** ((m - 69) / 12)


def add(buf, i, sig, pan=0.5):
    if i >= N:
        return
    n = min(len(sig), N - max(i, 0))
    if i < 0:
        sig, n, i = sig[-i:], n, 0
    buf[i:i + n] += sig[:n, None] * np.array([math.sqrt(1 - pan), math.sqrt(pan)])


# ---------------------------------------------------------------- music: pad
BPM = 96.0
BEAT = 60 / BPM
CHORDS = [[45, 57, 60, 64, 67, 71], [41, 53, 57, 60, 64, 69], [48, 55, 60, 64, 67, 74], [43, 55, 59, 62, 67, 71]]
BAR = 4 * BEAT
pad = np.zeros((N, 2))
for b in range(int(R.DUR / BAR) + 2):
    ch = CHORDS[b % 4]
    t0 = b * BAR - 0.15
    i0 = max(0, int(t0 * SR)); i1 = min(N, int((t0 + BAR + 0.9) * SR))
    if i1 <= i0:
        continue
    tt = np.arange(i1 - i0) / SR + (i0 / SR - t0)
    env = np.clip(tt / 0.6, 0, 1) * np.clip((BAR + 0.9 - tt) / 0.9, 0, 1)
    for j, m in enumerate(ch):
        for dt, pan in ((-0.07, 0.25), (0.07, 0.75)):
            f = mtof(m + dt)
            s = sum(np.sin(2 * np.pi * f * h * tt + rng.random() * 6) / h ** 1.6 for h in (1, 2, 3, 4))
            g = (0.5 if m < 50 else 0.22)
            pad[i0:i1] += (g * env * s)[:, None] * np.array([math.sqrt(1 - pan), math.sqrt(pan)])
# slowly opening low-pass (two fixed filters cross-faded by a control)
openness = ctl(lambda t: 0.25 + 0.75 * R.sstep(0.0, R.T_14, t) * (1 - R.sstep(R.T_AND - 0.3, R.T_AND + 0.3, t)) + 0.35 * R.sstep(R.T_AND + 0.3, R.DUR, t))
pad = filt(pad, 'low', 700) * (1 - openness[:, None]) + filt(pad, 'low', 3200) * openness[:, None]
pad = filt(pad, 'high', 60)

# ---------------------------------------------------------------- music: sub pulse + off-beat ticks (rests while the schematic explains)
beat = np.zeros((N, 2))
drive = ctl(lambda t: R.sstep(0.0, 0.3, t) * (1 - R.sstep(R.T_AND - 0.4, R.T_AND, t)) + 0.0)
for k in range(int(R.DUR / BEAT) + 1):
    tb = k * BEAT
    n = int(0.42 * SR); tt = np.arange(n) / SR
    f = 46 + 70 * np.exp(-tt / 0.03)
    kick = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.18) * (1 - np.exp(-tt / 0.002))
    add(beat, int(tb * SR), 0.55 * kick)
    m = int(0.05 * SR)
    tick = filt(rng.standard_normal(m), 'high', 7000) * np.exp(-np.arange(m) / SR / 0.012)
    add(beat, int((tb + BEAT / 2) * SR), 0.10 * tick, 0.62)
beat *= drive[:, None]

# ---------------------------------------------------------------- road: tyre roar + whine follow the wheel speed (side scene only)
w = ctl(R.omega)
side = ctl(lambda t: 1.0 if R.scene_at(t)[0] == 'side' else 0.0)
side = smooth(side, 0.35)
roar_n = rng.standard_normal((N, 2))
spd = np.clip(w / 14.0, 0, 1)
roar = (filt(roar_n, 'band', [120, 700]) * (0.30 + 0.9 * spd)[:, None]
        + filt(roar_n, 'band', [900, 3500]) * (0.05 + 0.6 * spd ** 1.5)[:, None])
whine_f = 40 + 55 * w                                       # tread-block whine pitch rises with speed
whine = 0.12 * spd ** 1.3 * np.sin(2 * np.pi * np.cumsum(whine_f) / SR)
roar = roar + whine[:, None]
roar *= (0.35 * side)[:, None]

# ---------------------------------------------------------------- UI / transitions
fx = np.zeros((N, 2))
for (txt, f, x, y, t0, t1, em) in R.captions(0):
    if txt.startswith(('100', '14 ')):
        steps = 14 if txt.startswith('14') else 20
        for k in range(steps):
            tk = t0 + 0.8 * (k / steps) ** 0.6
            m = 260
            add(fx, int(tk * SR), 0.05 * np.sin(2 * np.pi * (1800 + 40 * k) * np.arange(m) / SR) * np.exp(-np.arange(m) / 50), 0.4)
        continue
    for k, chx in enumerate(txt):
        if chx == ' ':
            continue
        tk = t0 + k / R.TYPE
        if tk >= t1:
            break
        m = 220
        c = filt(rng.standard_normal(m), 'band', [2500, 7000]) * np.exp(-np.arange(m) / 30)
        add(fx, int(tk * SR), 0.05 * c, 0.3 + 0.4 * rng.random())

# radar pings (match the rings in the schematic: period 1/0.9 s, two rings)
T0p = R.CASC[0][0] + 0.5
for k in range(6):
    tp = R.CASC[0][0] + (k * 0.5 - 0.0) / 0.9 * 1.0
    if not (T0p <= tp <= R.T_FOUR + 2.2):
        continue
    n = int(0.9 * SR); tt = np.arange(n) / SR
    ping = np.sin(2 * np.pi * 1318.5 * tt) * np.exp(-tt / 0.22) * (1 - np.exp(-tt / 0.003))
    add(fx, int(tp * SR), 0.10 * ping, 0.3 + 0.4 * (k % 2))


def hit(t0, amp, f_lo=40):
    n = int(1.6 * SR); tt = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(f_lo + 45 * np.exp(-tt / 0.06)) / SR) * np.exp(-tt / 0.55) * (1 - np.exp(-tt / 0.004))
    air = filt(rng.standard_normal(n), 'band', [300, 2500]) * np.exp(-tt / 0.08) * 0.25
    add(fx, int((t0 - 0.01) * SR), amp * (boom + air))


hit(R.T_HAND, 0.55)
hit(R.T_SHEET, 0.6)
hit(R.T_14, 0.8, 34)

# riser into "fourteen"
i0, i1 = int((R.T_14 - 1.4) * SR), int(R.T_14 * SR)
n = i1 - i0; u = np.arange(n) / n
ris = filt(rng.standard_normal(n), 'band', [800, 6000]) * u ** 3 * 0.18
add(fx, i0, ris)

# waterfall transitions: airy swell + falling glints + soft landing
for (t0, d, a, b) in R.CASC:
    n = int((d + 0.5) * SR); tt = np.arange(n) / SR
    env = np.sin(np.pi * np.clip(tt / (d + 0.5), 0, 1)) ** 2
    nz = rng.standard_normal(n)
    sweep = np.zeros(n)
    for j, (lo, hi) in enumerate([(400, 1500), (1500, 5000)]):
        sweep += filt(nz, 'band', [lo, hi]) * (0.6 if j == 0 else 0.35)
    pan_l = np.clip(0.5 + 0.45 * np.sin(np.pi * tt / (d + 0.5) - np.pi / 2), 0, 1)
    sw = sweep * env * 0.20
    i = int((t0 - 0.25) * SR)
    m = min(n, N - i)
    fx[i:i + m] += np.stack([sw[:m] * np.sqrt(1 - pan_l[:m]), sw[:m] * np.sqrt(pan_l[:m])], 1)
    for _ in range(int(40 * d)):
        k0 = t0 + rng.random() * d * 0.8
        prog = (k0 - t0) / d
        f = 4200 * (0.35 ** prog) * (0.9 + 0.2 * rng.random())
        m = 1400; tt2 = np.arange(m) / SR
        add(fx, int(k0 * SR), 0.045 * np.sin(2 * np.pi * f * tt2) * np.exp(-tt2 / 0.03), rng.random())
    n = int(0.6 * SR); tt = np.arange(n) / SR
    add(fx, int((t0 + 0.92 * d) * SR), 0.30 * np.sin(2 * np.pi * np.cumsum(55 + 30 * np.exp(-tt / 0.05)) / SR) * np.exp(-tt / 0.2))

# reverb (UI + transitions + pad)
irn = int(1.6 * SR); ti = np.arange(irn) / SR
ir = filt(rng.standard_normal((irn, 2)), 'low', 6000) * np.exp(-ti / 0.45)[:, None]
ir /= np.abs(ir).sum(0)


def verb(x, amt):
    return x + amt * np.stack([fftconvolve(x[:, c], ir[:, c])[:N] for c in range(2)], 1)


fx = verb(fx, 3.0)
pad = verb(pad, 1.5)

# ---------------------------------------------------------------- mix
vo = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', sys.argv[1], '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                  capture_output=True, check=True).stdout, np.float32).astype(np.float64)
vo = np.pad(vo, (0, max(0, N - len(vo))))[:N]
vo = vo / np.abs(vo).max() * 0.7
venv = smooth(np.abs(vo), 0.12); venv /= venv.max()
duck = (1 - 0.5 * np.clip(venv * 3, 0, 1))[:, None]
# loop seam: fade the bed in over the first 0.25 s and out over the last 0.3 s so the loop is seamless
edge = np.clip(T / 0.25, 0, 1) * np.clip((R.DUR - T) / 0.3, 0, 1)
bed = (0.40 * pad / np.abs(pad).max() + 0.35 * beat / np.abs(beat).max() + 0.22 * roar / np.abs(roar).max()) * duck
mix = np.stack([vo, vo], 1) + (bed + 0.55 * fx / np.abs(fx).max() * duck) * edge[:, None]
mix = np.tanh(mix * 1.1) / 1.1
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
