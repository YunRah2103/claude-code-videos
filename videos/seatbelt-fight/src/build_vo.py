"""Place the one-take voiceover on the 16 s timeline (no re-request; tempo stays 1.0x: 0.95x would pass 18 s):
  A "Quick pause."  -> speech starts at 4.80 s (freeze after the car stops abruptly)
  B explanation     -> right after A; silent gaps longer than 0.2 s are shortened to 0.2 s (cut around the quietest point)
  C "Did you know that?" -> back in the street, after the last hit lands
Writes out/seatbelt-fight/vo_track.wav (48 kHz mono, 18 s), loud.json (per-frame 60 fps loudness 0..1) and
src/words_placed.json (real faster-whisper timings mapped through the cuts; est flags kept).
    python videos/seatbelt-fight/src/build_vo.py"""
import json, os, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..', '..', '..')
OUT = os.path.join(ROOT, 'out', 'seatbelt-fight')
SR, DUR, FPS = 48000, 18.0, 60
A_AT, C_AT, GAP = 4.8, 16.6, 0.2


def load(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ar', str(SR), '-ac', '1', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def main():
    x = load(os.path.join(OUT, 'voiceover.wav')); W = json.load(open(os.path.join(HERE, 'words.json')))
    nA = 2; nC = len(W) - 4          # 'Quick pause.' | ... | 'Did you know that?'
    rms = np.sqrt(np.convolve(x ** 2, np.ones(480) / 480, 'same'))

    def seg(t0, t1):                 # samples + time map; each word gap > GAP loses (gap - GAP) around its quietest point
        i0, i1 = int(t0 * SR), int(t1 * SR); keep = np.ones(i1 - i0, bool)
        for a, b in zip(W, W[1:]):
            g0, g1 = a['e'], b['s']
            if t0 <= g0 and g1 <= t1 and g1 - g0 > GAP + 0.04:
                j0, j1 = int(g0 * SR), int(g1 * SR); cut = int((g1 - g0 - GAP) * SR)
                c = j0 + int(np.argmin(rms[j0:j1])); lo = min(max(c - cut // 2, j0 + int(0.05 * SR)), j1 - int(0.05 * SR) - cut)
                if lo > j0: keep[lo - i0:lo - i0 + cut] = False
        y = x[i0:i1].copy(); n = int(0.012 * SR)
        for e in np.flatnonzero(np.diff(keep.astype(int)) == -1):      # short fades around each cut (no clicks)
            y[max(e - n, 0):e + 1] *= np.linspace(1, 0, len(y[max(e - n, 0):e + 1]))
        for e in np.flatnonzero(np.diff(keep.astype(int)) == 1):
            y[e + 1:e + 1 + n] *= np.linspace(0, 1, len(y[e + 1:e + 1 + n]))
        newpos = np.cumsum(keep) - 1
        return y[keep], lambda t: newpos[min(max(int((t - t0) * SR), 0), len(newpos) - 1)] / SR
    lead = W[0]['s']
    a0, a1 = 0.0, W[nA - 1]['e'] + 0.12          # A -> B gap shortened to ~0.24 s
    b0, b1 = W[nA]['s'] - 0.12, (W[nC - 1]['e'] + W[nC]['s']) / 2
    c0, c1 = b1, len(x) / SR
    A, fa = seg(a0, a1); B, fb = seg(b0, b1); C, fc = seg(c0, c1)
    track = np.zeros(int(SR * DUR))
    a_at = A_AT - fa(lead); b_at = a_at + len(A) / SR
    c_at = C_AT - fc(W[nC]['s'])
    for s, at in ((A, a_at), (B, b_at), (C, c_at)):
        i = int(at * SR); track[i:i + len(s)] += s[:len(track) - i]
    placed = []
    for k, w in enumerate(W):
        if k < nA: f, at, o = fa, a_at, a0
        elif k < nC: f, at, o = fb, b_at, b0
        else: f, at, o = fc, c_at, c0
        placed.append(dict(w=w['w'], s=round(float(at + f(w['s'])), 3), e=round(float(at + f(w['e'])), 3), **({'est': 1} if w.get('est') else {})))
    assert c_at + len(C) / SR <= DUR - 0.25, 'voiceover runs past the end'
    import wave
    with wave.open(os.path.join(OUT, 'vo_track.wav'), 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes((np.clip(track, -1, 1) * 32767).astype('<i2').tobytes())
    hop = SR // FPS; env = np.array([np.sqrt(np.mean(track[i * hop:(i + 1) * hop] ** 2)) for i in range(int(DUR * FPS))])
    loud = np.clip((20 * np.log10(env + 1e-6) + 42) / 30, 0, 1)
    json.dump([round(float(v), 3) for v in loud], open(os.path.join(OUT, 'loud.json'), 'w'))
    json.dump(placed, open(os.path.join(HERE, 'words_placed.json'), 'w'), indent=0)
    json.dump({'words': placed, 'loud': [round(float(v), 3) for v in loud]}, open(os.path.join(OUT, 'data.json'), 'w'))   # scene input
    print('B ends', round(b_at + len(B) / SR, 2), 'C', round(c_at, 2), '-', round(c_at + len(C) / SR, 2),
          'last word', placed[-1])


if __name__ == '__main__':
    main()
