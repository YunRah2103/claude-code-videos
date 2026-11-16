"""Smoothness checks for the ASCII loop: pacing, duplicates, flicker, motion per second, jerk, loop seam, bitrate."""
import json
import subprocess
import sys

import cv2
import numpy as np

mp4 = sys.argv[1]
meta = json.load(open(mp4[:-4] + '.frames.json'))
FPS = 30
R = {}

pts = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'frame=pts_time',
                      '-of', 'csv=p=0', mp4], capture_output=True, text=True).stdout.split()
pts = np.array([float(p.strip(',')) for p in pts if p.strip(',')])
d = np.diff(pts)
R['frames'] = len(pts)
R['frame_dur_ms'] = [round(d.min() * 1e3, 3), round(d.max() * 1e3, 3)]
R['pacing_ok'] = bool(np.allclose(d, 1 / FPS, atol=1e-3)) and len(pts) == len(meta)
md5 = [l.split(',')[-1].strip() for l in subprocess.run(['ffmpeg', '-v', 'error', '-i', mp4, '-f', 'framemd5', '-'],
       capture_output=True, text=True).stdout.splitlines() if l and not l.startswith('#')]
R['dup_consecutive'] = int(sum(a == b for a, b in zip(md5, md5[1:] + md5[:1])))
R['unique_frames'] = len(set(md5))

t = np.array([m['t'] for m in meta])
car = np.array([m['car'] for m in meta])
cen = np.array([m['centroid'] for m in meta])
fl = np.array([m['flicker'] for m in meta])
spd = np.linalg.norm(np.diff(car, axis=0, append=car[:1]), axis=1)          # px/frame, wraps for the loop
slow = (spd < np.percentile(spd, 40)) & (t > 1.7) & (t < 4.6)
R['flicker_slow_cam_pct'] = round(100 * fl[slow].mean(), 2)
R['flicker_slow_cam_frames'] = int(slow.sum())
flr = np.array([m['flicker_raw'] for m in meta])
R['flicker_raw_id_change_slow_cam_pct'] = round(100 * flr[slow].mean(), 2)
R['flicker_all_bright_pct'] = round(100 * fl[(t > 1.7) & (t < 4.6)].mean(), 2)

# optical flow on the encoded video
cap = cv2.VideoCapture(mp4)
prev, flow, flowc, diffs, frames = None, [], [], [], []
while True:
    ok, f = cap.read()
    if not ok:
        break
    g = cv2.cvtColor(cv2.resize(f, (270, 480), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    g = cv2.GaussianBlur(g, (0, 0), 2.5)                                   # ~1 cell: remove the glyph grid
    g = cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX)                   # dim intro/outro still tracked
    frames.append(g)
for a, b in zip(frames, frames[1:] + frames[:1]):
    fw = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    mag = np.linalg.norm(fw, axis=2)
    w = (a > 25)
    wc = w.copy(); wc[:175] = False                                    # below the terminal panel (y > 700 px)
    flowc.append(float((mag * wc).sum() / max(wc.sum(), 1)) * 4)
    flow.append(float((mag * w).sum() / max(w.sum(), 1)) * 4)          # full-res px/frame on lit pixels
    diffs.append(float(np.abs(a.astype(int) - b).mean()))
flow = np.array(flow)
R['flow_px_per_frame_by_second'] = [round(flow[i * 30:(i + 1) * 30].mean(), 2) for i in range(len(flow) // 30)]
R['car_speed_px_per_frame_by_second'] = [round(spd[i * 30:(i + 1) * 30].mean(), 2) for i in range(len(spd) // 30)]
flowc = np.array(flowc)
R['car_region_flow_by_second'] = [round(flowc[i * 30:(i + 1) * 30].mean(), 2) for i in range(len(flowc) // 30)]
R['car_region_flow_min_over_max'] = round(min(R['car_region_flow_by_second']) / max(R['car_region_flow_by_second']), 2)
R['flow_min_over_max_block'] = round(min(R['flow_px_per_frame_by_second']) / max(R['flow_px_per_frame_by_second']), 2)

# geometric motion: grid of points on the car, 4-sub-frame averaged like the render
sys.path.insert(0, __import__('os').path.dirname(__file__))
import render as RD
PTS = [(x, y) for x in range(80, 1060, 120) for y in range(80, 540, 90) if RD.source.MASK[y, x] > 0]
geo = np.array([np.mean([[RD.project(p, RD.camera(i / FPS + (k - 1.5) / (FPS * 4))) for p in PTS] for k in range(4)], 0)
                for i in range(len(meta))])
gsp = np.linalg.norm(np.roll(geo, -1, 0) - geo, axis=2).mean(1)
gac = np.linalg.norm(np.roll(geo, -1, 0) - 2 * geo + np.roll(geo, 1, 0), axis=2).mean(1)
R['geo_speed_px_per_frame_by_second'] = [round(gsp[i * 30:(i + 1) * 30].mean(), 2) for i in range(len(gsp) // 30)]
R['geo_speed_min_frame'] = round(float(gsp.min()), 2)
R['geo_accel_px_per_frame2'] = dict(rms=round(float(np.sqrt((gac ** 2).mean())), 3), max=round(float(gac.max()), 3))

def jerk(p):
    a = np.roll(p, -1, 0) - 2 * p + np.roll(p, 1, 0)                     # periodic second difference
    return np.linalg.norm(a, axis=1)
j = jerk(car)
R['car_accel_px_per_frame2'] = dict(rms=round(float(np.sqrt((j ** 2).mean())), 3), max=round(float(j.max()), 3))
R['car_speed_px_per_frame'] = dict(mean=round(float(spd.mean()), 2), max=round(float(spd.max()), 2))
jc = jerk(cen)
R['mask_centroid_accel_px_per_frame2'] = dict(rms=round(float(np.sqrt((jc ** 2).mean())), 3), max=round(float(jc.max()), 3))
R['loop_seam_diff_vs_neighbours'] = round(diffs[-1] / np.median(diffs[-6:-1] + diffs[:5]), 2)
br = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=bit_rate,duration', '-of', 'json', mp4],
                    capture_output=True, text=True).stdout
fmt = json.loads(br)['format']
R['bitrate_mbps'] = round(int(fmt['bit_rate']) / 1e6, 2)
R['duration_s'] = float(fmt['duration'])
json.dump(R, open(mp4[:-4] + '.checks.json', 'w'), indent=1)
for k, v in R.items():
    print(f'{k}: {v}')
