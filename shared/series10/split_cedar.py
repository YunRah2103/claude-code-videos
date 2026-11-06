"""Split user-supplied two-episode voiceover chunks (openai.fm, cedar) into per-episode voiceovers.
    python shared/series10/split_cedar.py chunk.mp3 ...
Each chunk holds two consecutive episodes from scripts.EPISODES. faster-whisper identifies which pair it is, the split
falls midway in the gap between episode A's last word and episode B's first, then each half gets the series processing:
lead silence <= 0.15 s, atempo 0.95 (1.0 if over 15 s), -16 LUFS, and real word alignment -> videos/<ep>/src/words.json."""
import difflib, json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path[:0] = [HERE, os.path.join(ROOT, 'shared')]
from scripts import EPISODES
from make_voiceover import process
from align_fw import align

for src in sys.argv[1:]:
    wav = os.path.join(ROOT, 'out', 'series10', 'cedar', os.path.basename(src).rsplit('.', 1)[0] + '.wav')
    os.makedirs(os.path.dirname(wav), exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-ac', '1', '-ar', '48000', wav], check=True)
    # which pair? best fuzzy match of the first words against each episode opening
    best = None
    for i in range(len(EPISODES) - 1):
        (a, sa), (b, sb) = EPISODES[i], EPISODES[i + 1]
        w = align(wav, wav + '.pair.json', sa + ' ' + sb)
        good = sum(1 for x in w if not x.get('est')) / len(w)
        if best is None or good > best[0]: best = (good, i, w)
        if good > 0.9: break
    good, i, w = best
    (a, sa), (b, sb) = EPISODES[i], EPISODES[i + 1]
    na = len(sa.split()); cut = (w[na - 1]['e'] + w[na]['s']) / 2
    print(os.path.basename(src), '->', a, '+', b, f'match {good:.0%}, split at {cut:.2f} s')
    for ep, script, ss, to in ((a, sa, 0, cut), (b, sb, cut, None)):
        os.makedirs(os.path.join(ROOT, 'out', ep), exist_ok=True); os.makedirs(os.path.join(ROOT, 'videos', ep, 'src'), exist_ok=True)
        raw = os.path.join(ROOT, 'out', ep, 'raw_cedar.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-ss', f'{ss:.3f}'] + (['-to', f'{to:.3f}'] if to else []) + [raw], check=True)
        r = process(ep, raw, script); r.update(ep=ep, voice='cedar (openai.fm, user-supplied)', source=os.path.basename(src))
        r['accepted'] = r['aligned_pct'] >= 95 and r['dur'] >= 11
        json.dump(r, open(os.path.join(ROOT, 'out', ep, 'vo_ok.json'), 'w')); print(r)
