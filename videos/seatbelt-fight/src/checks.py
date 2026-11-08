"""All quality checks for out/seatbelt-fight/seatbelt-fight.mp4 -> out/seatbelt-fight/checks.json
    python videos/seatbelt-fight/src/checks.py"""
import json, os, subprocess, sys
import numpy as np
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'); OUT = os.path.join(ROOT, 'out', 'seatbelt-fight')
sys.path.insert(0, os.path.join(ROOT, 'shared')); from motion_score import score
V = os.path.join(OUT, 'seatbelt-fight.mp4'); R = {}
pr = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', V]))
v = [s for s in pr['streams'] if s['codec_type'] == 'video'][0]; a = [s for s in pr['streams'] if s['codec_type'] == 'audio'][0]
R['probe'] = dict(size=f"{v['width']}x{v['height']}", fps=v['r_frame_rate'], dar=v.get('display_aspect_ratio'), pix=v['pix_fmt'], vcodec=v['codec_name'],
                  dur=round(float(pr['format']['duration']), 3), acodec=a['codec_name'], abr=int(a.get('bit_rate', 0)))
D = float(pr['format']['duration'])
R['motion_per_s'] = [round(score(V, s, min(s + 1, D - .06))[0], 1) for s in range(int(D))]
def grab(t):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', V, '-frames:v', '1', '-vf', 'scale=108:192,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).astype(float)
last = subprocess.run(['ffmpeg', '-v', 'error', '-sseof', '-0.05', '-i', V, '-update', '1', '-vf', 'scale=108:192,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
lf = np.frombuffer(last, np.uint8).astype(float)[-108 * 192:]
R['loop_diff'] = round(float(np.abs(grab(0) - lf).mean()), 2); R['last_frame_mean'] = round(float(lf.mean()), 1)
B = json.load(open(os.path.join(OUT, 'frames', 'boxes.json'))); bad = []
for f, bx in B.items():
    for b in bx:
        if b['y'] < 0.12 * 1920 - .5 or b['y'] + b['h'] > 0.62 * 1920 + .5 or b['x'] < 0 or b['x'] + b['w'] > 0.85 * 1080 + .5: bad.append((f, b['s'], 'zone'))
    for i in range(len(bx)):
        for j in range(i + 1, len(bx)):
            p, q = bx[i], bx[j]
            if p['x'] < q['x'] + q['w'] and q['x'] < p['x'] + p['w'] and p['y'] < q['y'] + q['h'] and q['y'] < p['y'] + p['h']: bad.append((f, p['s'] + '|' + q['s'], 'overlap'))
R['safe_zone'] = {'frames': len(B), 'violations': len(bad), 'first': bad[:6]}
m = subprocess.run(['ffmpeg', '-v', 'info', '-i', V, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
s = m[m.rindex('Summary:'):]
pick = lambda k: float(s.split(k)[1].split()[0])
R['loudness'] = dict(I_LUFS=pick('I:'), LRA=pick('LRA:'), true_peak_dBFS=pick('Peak:'))
R['voiceover'] = json.load(open(os.path.join(OUT, 'vo_report.json')))
json.dump(R, open(os.path.join(OUT, 'checks.json'), 'w'), indent=1); print(json.dumps(R))
