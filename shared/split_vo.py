"""Split one long voiceover into episode clips at its long silences (ffmpeg silencedetect).

Usage:  python shared/split_vo.py full.wav out_root name1 name2 ... [--db -35] [--min 1.5] [--pad 0.15]
Writes <out_root>/<name>/voiceover.wav (pcm, source rate) and prints the split timestamps. Fails unless the
silences give exactly one segment per name, so a wrong threshold never ships a half-episode clip.
"""
import os, re, subprocess, sys


def silences(path, db=-35, dmin=1.5):
    err = subprocess.run(['ffmpeg', '-hide_banner', '-i', path, '-af', f'silencedetect=n={db}dB:d={dmin}', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    s = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', err)]
    e = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', err)]
    return list(zip(s, e))


def split(path, out_root, names, db=-35, dmin=1.5, pad=0.15):
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                               capture_output=True, text=True).stdout)
    gaps = [(s, e) for s, e in silences(path, db, dmin) if s > 0.05 and e < dur - 0.05]   # ignore lead-in / tail
    segs, t = [], 0.0
    for s, e in gaps + [(dur, dur)]:
        segs.append((max(0.0, t - pad) if t else 0.0, min(dur, s + pad))); t = e
    if len(segs) != len(names):
        raise SystemExit(f'{len(segs)} segments at {db} dB / {dmin} s, expected {len(names)}: adjust the threshold')
    for name, (a, b) in zip(names, segs):
        os.makedirs(os.path.join(out_root, name), exist_ok=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-ss', f'{a:.3f}', '-to', f'{b:.3f}', '-c:a', 'pcm_s16le',
                        os.path.join(out_root, name, 'voiceover.wav')], check=True)
        print(f'{name}: {a:.3f} -> {b:.3f}  ({b - a:.2f} s)')
    return segs


if __name__ == '__main__':
    a = sys.argv[1:]
    opt = {k: float(a[a.index(k) + 1]) for k in ('--db', '--min', '--pad') if k in a}
    pos = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or not a[i - 1].startswith('--'))]
    split(pos[0], pos[1], pos[2:], opt.get('--db', -35), opt.get('--min', 1.5), opt.get('--pad', 0.15))
