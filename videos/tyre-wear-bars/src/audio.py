"""Fit cached VO lines to their slots, add pixel SFX, write 48 kHz mix + timings.

Rules: trim silence, shrink pauses inside a line, then tempo (pitch-kept atempo)
by at most +8%. A line that still does not fit is reported, never sped up more.
Usage: python audio.py  -> build/mix.wav, build/vo.wav, build/timing.json
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from tts import read_wav, write_wav

HERE = Path(__file__).parent
CACHE, BUILD = HERE / 'cache', HERE / 'build'
SR = 48000
DUR = 13.0
MAX_TEMPO = 1.08
# (slot start, slot end, cached file, spoken text, trim end in s or None)
SLOTS = [
    (0.0, 3.0, 'line_1.wav', "Look in the grooves of your tyre. There's a hidden wear bar.", None),
    (3.0, 6.0, 'line_2.wav', "Every tyre has them. The sidewall mark shows where.", None),
    (6.0, 9.0, 'line_3.wav', "When the tread is level with the bar, you're at the limit.", None),
    # Original line 4 is 4.3 s of speech for a 2.0 s slot. DRAFT pending approval:
    # first two sentences of the cached alternative take "Find TWI. Check the groove. Ten seconds."
    (9.0, 11.0, 'alt4_3.wav', "Find TWI. Check the groove.", 'gap2'),
    (11.0, 13.0, 'line_5.wav', "Have you ever looked for yours?", None),
]
LEAD = 0.03         # VO starts this long after the slot start
LATE_OK = 0.12      # a line may start up to this late (verify allows 0.15)
GAP_MIN = 0.07      # shortest pause kept inside a line
SFX_CUES = [('ping', 1.5), ('click', 7.97), ('blip', 11.0)]


def gaps(x, sr, thr=0.012, hop_s=0.01, min_s=0.12):
    hop = int(sr * hop_s)
    loud = np.array([np.abs(x[i:i + hop]).max() > thr for i in range(0, len(x), hop)])
    out, run = [], None
    for k, v in enumerate(loud):
        if not v:
            run = k if run is None else run
        elif run is not None:
            if (k - run) * hop_s >= min_s:
                out.append((run * hop, k * hop))
            run = None
    idx = np.flatnonzero(loud)
    return out, idx[0] * hop, (idx[-1] + 1) * hop


def resample(x, sr_in, tempo=1.0):
    """ffmpeg: 24 kHz -> 48 kHz (soxr-free default), optional atempo."""
    af = f'aresample={SR}' + (f',atempo={tempo:.5f}' if tempo != 1.0 else '')
    p = subprocess.run(['ffmpeg', '-v', 'error', '-f', 's16le', '-ar', str(sr_in), '-ac', '1', '-i', '-',
                        '-af', af, '-f', 's16le', '-ar', str(SR), '-ac', '1', '-'],
                       input=(np.clip(x, -1, 1) * 32767).astype('<i2').tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, '<i2').astype(np.float32) / 32768


def fit_line(path, budget, trim):
    x, sr = read_wav(path)
    g, a, b = gaps(x, sr)
    if trim == 'gap2':          # keep up to the second pause (drop the last sentence)
        b = g[1][0]
        g = g[:1]
    pad = int(0.015 * sr)
    pieces, cur = [], max(0, a - pad)
    g = [(s, e) for s, e in g if a < s and e < b]
    report = {'raw_s': round((b - a) / sr, 3)}
    for s, e in g:
        pieces.append(x[cur:s]); cur = e
    pieces.append(x[cur:min(len(x), b + pad)])
    speech = sum(len(p) for p in pieces) / sr
    n = len(g)
    # pause length needed to fit at tempo 1.0, else minimum pauses + tempo
    pause = (budget - speech) / n if n else 0
    orig = [(e - s) / sr for s, e in g]
    if n:
        pause = max(GAP_MIN, min(pause, min(orig) if orig else pause))
    total = speech + n * pause
    tempo = max(1.0, total / budget)
    report.update(speech_s=round(speech, 3), pause_s=round(pause, 3), tempo=round(tempo, 4))
    if tempo > MAX_TEMPO:
        report['fits'] = False
        tempo = MAX_TEMPO
    else:
        report['fits'] = True
    sil = np.zeros(int(pause * sr), np.float32)
    joined = pieces[0]
    for p in pieces[1:]:
        joined = np.concatenate([joined, sil, p])
    y = resample(joined, sr, tempo)
    report['fitted_s'] = round(len(y) / SR, 3)
    return y, report


# ---------------------------------------------------------------- pixel SFX (square waves)
def sq(f, d, duty=0.5):
    t = np.arange(int(SR * d)) / SR
    return np.where((t * f) % 1 < duty, 1.0, -1.0)


def env(n, a=0.002, rate=18):
    t = np.arange(n) / SR
    e = np.exp(-t * rate)
    na = int(a * SR); e[:na] *= np.linspace(0, 1, na)
    e[-int(0.004 * SR):] *= np.linspace(1, 0, int(0.004 * SR))
    return e


def ping():
    a = sq(1568, 0.06, 0.25); b = sq(2349, 0.32, 0.25)
    x = np.concatenate([a, b]); return x * env(len(x), rate=9) * 0.22


def click():
    n = int(0.05 * SR)
    noise = np.random.default_rng(3).choice([-1.0, 1.0], n)
    x = np.concatenate([noise[:n // 3], sq(880, 0.03, 0.125)])
    return x * env(len(x), rate=60) * 0.28


def blip():
    x = np.concatenate([sq(660, 0.05), sq(990, 0.08)])
    return x * env(len(x), rate=14) * 0.2


def build():
    BUILD.mkdir(exist_ok=True)
    vo = np.zeros(int(SR * DUR), np.float32)
    timing, ok = [], True
    starts = [s for s, *_ in SLOTS] + [DUR]
    prev_end = -1.0
    for i, (s, e, f, text, trim) in enumerate(SLOTS):
        start = max(s + (LEAD if i else 0.0), prev_end + 0.02)
        if start > s + LATE_OK + 1e-3:
            raise SystemExit(f'line {i + 1} would start {start - s:.2f}s late')
        last = i + 1 == len(SLOTS)
        y, rep = fit_line(CACHE / f, starts[i + 1] + (-0.05 if last else 0.02) - start, trim)
        if not rep['fits'] and not last:     # let the next line start a little late
            y, rep = fit_line(CACHE / f, starts[i + 1] + LATE_OK - 0.025 - start, trim)
        if not rep['fits']:
            ok = False
            print(f'LINE {i + 1} TOO LONG: "{text}" needs tempo {rep["tempo"]} (> {MAX_TEMPO}).', file=sys.stderr)
        a = int(start * SR)
        vo[a:a + len(y)] += y[:len(vo) - a]
        prev_end = start + len(y) / SR
        timing.append(dict(line=i + 1, slot=[s, e], start=round(start, 3), end=round(prev_end, 3),
                           text=text, file=f, **rep))
    peak = np.abs(vo).max()
    vo *= 10 ** (-3 / 20) / peak            # voice peaks at -3 dBFS
    fx = np.zeros_like(vo)
    for name, t in SFX_CUES:
        x = {'ping': ping, 'click': click, 'blip': blip}[name]()
        a = int(t * SR); fx[a:a + len(x)] += x[:len(fx) - a]
    mix = vo + fx
    m = np.abs(mix).max()
    if m > 0.95:
        mix *= 0.95 / m
    write_wav(BUILD / 'vo.wav', (vo * 32767).astype('<i2'), SR)
    write_wav(BUILD / 'mix.wav', (mix * 32767).astype('<i2'), SR)
    # mouth envelope for the renderer (RMS per 1/30 s)
    hop = SR // 30
    rms = [float(np.sqrt(np.mean(vo[i:i + hop] ** 2))) for i in range(0, len(vo), hop)]
    json.dump({'lines': timing, 'sfx': SFX_CUES, 'rms30': rms, 'all_fit': ok},
              open(BUILD / 'timing.json', 'w'), indent=1)
    for t in timing:
        print(f"line {t['line']}: {t['start']:.2f}-{t['end']:.2f}s tempo {t['tempo']} pause {t['pause_s']} fits={t['fits']}")
    return ok


if __name__ == '__main__':
    raise SystemExit(0 if build() else 3)
