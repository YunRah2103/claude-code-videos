"""Tighten a voiceover for short-form pacing: shorten long pauses between aligned words, then speed it up gently.

tighten(src_mp3, words, out_mp3, target=17.2) keeps every word intact (cuts only inside silences, with short
crossfades), caps pauses at `sent` after a sentence, `comma` after a comma and `inner` elsewhere, then applies a
pitch-preserving atempo of at most `max_tempo` to land near `target` seconds. Re-align the result afterwards:
timings must come from the audio that ships, never from scaling.
"""
import subprocess
import numpy as np

SR = 24000


def _load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def tighten(src, words, out, target=17.2, sent=0.30, comma=0.18, inner=0.22, max_tempo=1.15, xf=0.012):
    x = _load(src)
    n_xf = int(xf * SR)
    pieces, pos = [], 0
    for a, b in zip(words, words[1:]):
        gap = b['s'] - a['e']
        keep = sent if a['w'][-1] in '.!?' else comma if a['w'][-1] in ',:;' else inner
        if gap <= keep + 0.04: continue
        cut0 = int((a['e'] + keep / 2) * SR); cut1 = int((b['s'] - keep / 2) * SR)
        pieces.append(x[pos:cut0]); pos = cut1
    pieces.append(x[pos:])
    y = pieces[0]
    fade = np.linspace(0, 1, n_xf)
    for p in pieces[1:]:                                   # equal-length crossfade at each cut
        if len(y) > n_xf and len(p) > n_xf:
            y = np.concatenate([y[:-n_xf], y[-n_xf:] * (1 - fade) + p[:n_xf] * fade, p[n_xf:]])
        else:
            y = np.concatenate([y, p])
    tempo = min(max_tempo, max(1.0, len(y) / SR / target))
    af = ['-af', f'atempo={tempo:.4f}'] if tempo > 1.001 else []
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-', *af,
                    '-c:a', 'libmp3lame', '-b:a', '192k', out], input=y.astype(np.float32).tobytes(), check=True)
    print(f'tighten: {len(x) / SR:.2f}s -> {len(y) / SR:.2f}s, tempo {tempo:.3f} -> {len(y) / SR / tempo:.2f}s')
    return tempo
