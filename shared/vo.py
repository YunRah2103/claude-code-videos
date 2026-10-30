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


def _save(y, out, af=()):
    codec = ['-c:a', 'pcm_s16le'] if out.endswith('.wav') else ['-c:a', 'libmp3lame', '-b:a', '192k']
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-', *af, *codec, out],
                   input=y.astype(np.float32).tobytes(), check=True)


def pace(src, words, out, add=0.0, lead=0.0, tail=None, tail_gap=0.7):
    """The opposite of tighten for very short reads: `lead` s of silence first, `add` s more silence in each gap
    after a sentence, then optionally `tail`=(path, t0, t1), a span of another clip (same voice), after `tail_gap` s.
    Only silence is inserted; every word stays as recorded. Re-align the result afterwards."""
    x = _load(src); z = lambda d: np.zeros(int(d * SR))
    pieces, pos = [z(lead)], 0
    for a, b in zip(words, words[1:]):
        if a['w'][-1] in '.!?' and add > 0:
            cut = int((a['e'] + b['s']) / 2 * SR); pieces += [x[pos:cut], z(add)]; pos = cut
    pieces.append(x[pos:])
    if tail:
        y = _load(tail[0]); pieces += [z(tail_gap), y[int(tail[1] * SR):int(tail[2] * SR)]]
    y = np.concatenate(pieces); _save(y, out)
    print(f'pace: {len(x) / SR:.2f}s -> {len(y) / SR:.2f}s')


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
    _save(y, out, af)
    print(f'tighten: {len(x) / SR:.2f}s -> {len(y) / SR:.2f}s, tempo {tempo:.3f} -> {len(y) / SR / tempo:.2f}s')
    return tempo
