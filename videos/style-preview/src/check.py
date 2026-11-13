"""Checks: ffprobe, contact sheet per style, motion measure, black-first-frame and loop check.
python check.py  -> out/style-preview/checks/ + checks.txt"""
import os, sys, json, subprocess
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import OUT, N, FPS, STYLES

def probe(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                        'stream=codec_name,width,height,r_frame_rate,nb_frames:format=duration',
                        '-of', 'json', p], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)

def frames(st):
    d = os.path.join(OUT, 'frames', 's%d' % st)
    return [np.asarray(Image.open(os.path.join(d, '%04d.png' % i)).convert('L').resize((270, 480)), np.float32)
            for i in range(N)]

def main():
    cd = os.path.join(OUT, 'checks'); os.makedirs(cd, exist_ok=True)
    lines = []
    for p in ['preview.mp4'] + ['style-%d.mp4' % s for s in range(1, 7)]:
        j = probe(os.path.join(OUT, p))
        v = [s for s in j['streams'] if s.get('width')][0]
        a = [s['codec_name'] for s in j['streams'] if not s.get('width')]
        lines.append('%-12s %sx%s %s %s frames=%s dur=%.2fs audio=%s' % (
            p, v['width'], v['height'], v['codec_name'], v['r_frame_rate'], v.get('nb_frames'),
            float(j['format']['duration']), a))
    lines.append('')
    for st in range(1, 7):
        fr = frames(st)
        diffs = [float(np.abs(fr[i + 1] - fr[i]).mean()) for i in range(N - 1)]
        first2 = diffs[:2 * FPS - 1]
        still = sum(1 for x in first2 if x < 0.05)
        lum0 = float(fr[0].mean())
        lines.append('style %d: frame0 mean luma %.1f%s | motion first 2 s: mean %.2f min %.3f, '
                     '%d/%d frame pairs with no change | whole clip mean %.2f' % (
                         st, lum0, ' (BLACK!)' if lum0 < 3 else '', np.mean(first2), min(first2),
                         still, len(first2), np.mean(diffs)))
        # contact sheet: 8 frames, 0.5 s apart
        idx = list(range(0, N, 15))
        full = [Image.open(os.path.join(OUT, 'frames', 's%d' % st, '%04d.png' % i)).convert('RGB').resize((270, 480)) for i in idx]
        sheet = Image.new('RGB', (270 * len(full), 500), (20, 20, 20))
        dd = ImageDraw.Draw(sheet)
        for k, im in enumerate(full):
            sheet.paste(im, (k * 270, 20)); dd.text((k * 270 + 4, 3), 't=%.1fs' % (idx[k] / FPS), fill=(255, 255, 255))
        sheet.save(os.path.join(cd, 'contact_s%d.png' % st))
    # loop check for style 3: frame N (next loop start) must equal frame 0
    f0 = STYLES[3](0).astype(np.float32); fN = STYLES[3](N).astype(np.float32); fL = STYLES[3](N - 1).astype(np.float32)
    f1 = STYLES[3](1).astype(np.float32)
    lines.append('style 3 loop (frame 120 = start of the next loop, computed without wrapping): '
                 '|f120 - f0| = %.3f vs one frame of motion |f1 - f0| = %.3f, |f119 - f0| = %.3f (8-bit levels)'
                 % (np.abs(fN - f0).mean(), np.abs(f1 - f0).mean(), np.abs(fL - f0).mean()))
    txt = '\n'.join(lines); print(txt)
    open(os.path.join(cd, 'checks.txt'), 'w').write(txt + '\n')

if __name__ == '__main__':
    main()
