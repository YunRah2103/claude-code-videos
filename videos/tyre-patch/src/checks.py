"""Delivery checks for tyre-patch. python checks.py FINAL.mp4 FRAMES.json"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

import importlib.util
_spec = importlib.util.spec_from_file_location('tp_render', Path(__file__).with_name('render.py'))
R = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(R)

mp4, meta = sys.argv[1], json.load(open(sys.argv[2]))
W, H, FPS = R.W, R.H, R.FPS
out = {}


def run(*a):
    return subprocess.run(list(a), capture_output=True, text=True)


# pacing + duplicates
pts = [float(x.strip(',')) for x in run('ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'frame=pts_time',
                                        '-of', 'csv=p=0', mp4).stdout.split() if x.strip(',')]
d = np.diff(pts)
out['frames'] = len(pts)
out['pacing'] = f'{d.min() * 1e3:.3f}-{d.max() * 1e3:.3f} ms, constant={bool(np.allclose(d, 1 / FPS, atol=1e-3))}'
md5 = [l.split(',')[-1].strip() for l in run('ffmpeg', '-v', 'error', '-i', mp4, '-map', '0:v', '-f', 'framemd5', '-').stdout.splitlines()
       if l and not l.startswith('#')]
out['duplicate_consecutive_frames'] = sum(a == b for a, b in zip(md5, md5[1:]))

# motion: % of lit pixels whose luma changes by > 10 levels frame to frame (half-res)
cap = cv2.VideoCapture(mp4)
fr = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    fr.append(cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (W // 2, H // 2), interpolation=cv2.INTER_AREA))
mot = []
for a, b in zip(fr, fr[1:] + fr[:1]):
    a, b = a.astype(np.int16), b.astype(np.int16)
    lit = (a > 18) | (b > 18)
    mot.append(100 * float((np.abs(a - b) > 10)[lit].mean()))
mot = np.array(mot)
blocks = [round(float(mot[i:i + 2 * FPS].mean()), 1) for i in range(0, len(mot) - FPS, 2 * FPS)]
out['motion_pct_by_2s_block'] = blocks
out['motion_min_block'] = min(blocks)
out['motion_first2s_vs_median'] = f'{mot[:2 * FPS].mean():.1f} vs median {np.median(mot):.1f}'
diffs = [float(np.abs(a.astype(np.int16) - b).mean()) for a, b in zip(fr, fr[1:])]
out['loop_seam_diff_vs_median_step'] = round(float(np.abs(fr[-1].astype(np.int16) - fr[0]).mean()) / float(np.median(diffs)), 2)

# flicker in held (non-cascade) frames: share of lit glyph cells that change per frame
gc = [m['glyph_change'] for m in meta if m['glyph_change'] is not None]
out['glyph_change_held_mean_pct (includes real motion)'] = round(100 * float(np.mean(gc)), 2)
fl = [m['flicker'] for m in meta if m.get('flicker') is not None]
out['flicker_pct (glyph swaps on unchanged image)'] = f'mean {100 * float(np.mean(fl)):.3f}, max {100 * float(np.max(fl)):.3f}'

# text layout (code cards): every text box inside 12-62% height and the left 85%, size >= 2.5% of height
bad = []
for m in meta:
    for x0, y0, x1, y1 in m['boxes']:
        if y0 < 0.12 * H or y1 > 0.62 * H or x1 > 0.85 * W:
            bad.append((m['i'], x0, y0, x1, y1))
out['text_boxes_outside_zone'] = len(bad)
out['min_caption_font_px'] = f"{min(f.size for _, f, *_ in R.captions(0))} px = {100 * min(f.size for _, f, *_ in R.captions(0)) / H:.2f}% of height"

# audio: loudness, peak, silences
eb = run('ffmpeg', '-hide_banner', '-i', mp4, '-af', 'ebur128=peak=true', '-f', 'null', '-').stderr
summ = eb[eb.rindex('Summary:'):]
out['integrated_LUFS'] = float(summ.split('I:')[1].split('LUFS')[0])
out['true_peak_dBFS'] = float(summ.split('Peak:')[1].split('dBFS')[0])
sil = run('ffmpeg', '-hide_banner', '-i', mp4, '-af', 'silencedetect=noise=-45dB:d=1', '-f', 'null', '-').stderr
out['silent_gaps_over_1s'] = sil.count('silence_start')

fmt = json.loads(run('ffprobe', '-v', 'error', '-show_entries', 'format=bit_rate,duration', '-of', 'json', mp4).stdout)['format']
out['bitrate_mbps'] = round(int(fmt['bit_rate']) / 1e6, 2)
out['duration_s'] = round(float(fmt['duration']), 2)

# beats vs words
out['beats'] = {f'cascade {a}->{b}': f'{T:.2f}-{T + D:.2f} s' for T, D, a, b in R.CASC}
for w in ('speeding', 'braking', 'turning', 'hand', 'sheet', 'fourteen', 'road'):
    out['beats'][w] = f"{R.wt(w):.2f} s"
json.dump(out, open(Path(mp4).with_suffix('.checks.json'), 'w'), indent=1)
for k, v in out.items():
    print(f'{k}: {v}')
