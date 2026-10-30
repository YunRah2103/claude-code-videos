"""Join voiceover blocks with a fixed gap and split the result into one clip per episode at detected silences.

    python shared/vo_split.py <out_dir> <gap_s> <block.wav>:<words ep1>,<words ep2>,... ...

The 2 s join gap is the only pause long enough for a plain `silencedetect=d=1.5`, so inside each block the
episode boundaries are the detected pauses (-35 dB, >= MIN_D s) nearest the word-count-proportional cut.
Each clip runs from LEAD s before the end of the pause ahead of it to TAIL s into the pause after it and written as <out_dir>/clip<i>.wav (48 kHz mono).
"""
import json, re, subprocess, sys

NOISE, MIN_D, LEAD, TAIL = '-35dB', 0.5, 0.12, 0.35


def dur(p): return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p], capture_output=True, text=True).stdout)


def silences(path, noise=NOISE, d=MIN_D):
    log = subprocess.run(['ffmpeg', '-i', path, '-af', f'silencedetect=n={noise}:d={d}', '-f', 'null', '-'], capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', log)]
    en = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', log)]
    return list(zip(st, en))


def main(out_dir, gap, blocks):
    full = f'{out_dir}/full_voiceover.wav'
    ins = []
    for i, (p, _) in enumerate(blocks):
        if i: ins += [['-f', 'lavfi', '-t', str(gap), '-i', 'anullsrc=r=48000:cl=mono']]
        ins += [['-i', p]]
    n = len(ins); ins = sum(ins, [])
    graph = ''.join(f'[{k}:a]aresample=48000,aformat=channel_layouts=mono[a{k}];' for k in range(n)) + ''.join(f'[a{k}]' for k in range(n)) + f'concat=n={n}:v=0:a=1'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', graph, full], check=True)
    sil = silences(full)
    cuts, off = [], 0.0
    for bi, (p, words) in enumerate(blocks):
        L = dur(p); tot = sum(words); acc = 0
        inner = [s for s in sil if off < s[0] and s[1] < off + L]
        for w in words[:-1]:
            acc += w; want = off + L * acc / tot
            s = min(inner, key=lambda s: abs((s[0] + s[1]) / 2 - want))
            cuts.append(s)
        if bi < len(blocks) - 1:
            g = next(s for s in sil if s[0] <= off + L + 0.05 and s[1] >= off + L + gap - 0.05)
            cuts.append(g)
        off += L + gap
    ends = [0.0] + [round(s[1] - LEAD, 3) for s in cuts]
    segs = list(zip(ends, [round(s[0] + TAIL, 3) for s in cuts] + [dur(full)]))
    for i, (a, b) in enumerate(segs, 1):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', full, '-ss', str(a), '-to', str(b), '-c:a', 'pcm_s16le', f'{out_dir}/clip{i}.wav'], check=True)
    json.dump(dict(noise=NOISE, min_d=MIN_D, lead=LEAD, tail=TAIL, gap=gap, pauses=cuts, silences=sil, segments=segs), open(f'{out_dir}/split.json', 'w'), indent=1)
    for i, (a, b) in enumerate(segs, 1): print(f'clip{i}: {a:.3f} -> {b:.3f} ({b - a:.2f} s)')


if __name__ == '__main__':
    main(sys.argv[1], float(sys.argv[2]), [(a.split(':')[0], [int(x) for x in a.split(':')[1].split(',')]) for a in sys.argv[3:]])
