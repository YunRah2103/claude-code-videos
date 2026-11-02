"""Build out/voiceover/full_voiceover.wav for fuel-gauge-arrow, tyre-birthday and ev-fake-sound, then split it.

Source read: shared/tts.py (Gemini TTS gemini-3.1-flash-tts-preview, voice Fenrir, one style prompt, -16 LUFS per block),
saved as out/voiceover/full_voiceover_fast.wav. That read was fast (9-12 s), so each block is slowed with a
pitch-preserving atempo and gets a short beat after each sentence (vo.pace: silence only, words untouched). The blocks are
re-joined with exactly 2.0 s of digital silence and split again with silencedetect (-35 dB, >= 1.5 s), which must give 3.
"""
import os, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'shared'))
from align import align
from vo import pace, _load, _save, SR
import split_vo

EPS = {   # name: (script, say, atempo, beat after each sentence)
    'fuel-gauge-arrow': ("Why is there an arrow on your fuel gauge? It shows which side your fuel cap is on. Left arrow, left side. "
                         "Right arrow, right side. Did you already know that? Send this to the friend who always parks on the wrong side.",
                         {}, 0.86, 0.42),
    'tyre-birthday': ("How old are your tyres? Bet you've never checked. Find the letters DOT on the sidewall. The last four numbers are "
                      "the week and year they were made. 1822 means week 18 of 2022. And tyres age, even if you barely drive.",
                      {'1822': 'eighteen twenty two', '18': 'eighteen', '2022': 'twenty twenty two', 'tyres': 'tires', 'sidewall': 'side wall'}, 0.95, 0.14),
    'ev-fake-sound': ("Electric cars are almost silent. So why do they make a fake sound? Because the law says so. In the US, new electric "
                      "cars must warn pedestrians below 18.6 miles an hour. In Europe, below 12. If you could pick the sound, what would it be?",
                      {'18.6': 'eighteen point six', '12.': 'twelve', 'US,': 'u s'}, 0.95, 0.16),
}
SAYK = lambda say: {k.strip('.,:!?'): v for k, v in say.items()}
VO = os.path.join(ROOT, 'out', 'voiceover'); TMP = os.path.join(VO, 'blocks')

if __name__ == '__main__':
    os.makedirs(TMP, exist_ok=True)
    split_vo.split(os.path.join(VO, 'full_voiceover_fast.wav'), TMP, list(EPS))
    blocks = []
    for name, (script, say, tempo, beat) in EPS.items():
        d = os.path.join(TMP, name)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(d, 'voiceover.wav'), '-af', f'atempo={tempo}',
                        '-ar', str(SR), os.path.join(d, 'slow.wav')], check=True)
        w = align(script, os.path.join(d, 'slow.wav'), os.path.join(d, 'slow.json'), say=SAYK(say))
        pace(os.path.join(d, 'slow.wav'), w, os.path.join(d, 'paced.wav'), add=beat)
        y = _load(os.path.join(d, 'paced.wav')); nz = np.where(np.abs(y) > 10 ** (-45 / 20))[0]
        blocks.append(y[max(0, nz[0] - int(0.05 * SR)): nz[-1] + int(0.12 * SR)])
    gap = np.zeros(2 * SR)
    full = np.concatenate([blocks[0], gap, blocks[1], gap, blocks[2]])
    _save(full, os.path.join(VO, 'full_voiceover.wav'))
    print('blocks', [round(len(b) / SR, 2) for b in blocks])
    split_vo.split(os.path.join(VO, 'full_voiceover.wav'), os.path.join(ROOT, 'out'), list(EPS))
    for name, (script, say, _, _) in EPS.items():
        align(script, os.path.join(ROOT, 'out', name, 'voiceover.wav'),
              os.path.join(ROOT, 'videos', name, 'src', 'words.json'), say=SAYK(say))
