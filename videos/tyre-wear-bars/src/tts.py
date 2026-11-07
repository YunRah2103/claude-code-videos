"""Gemini TTS (voice Fenrir) with disk cache, backoff and quota stop.

One request for the whole script; lines are split on the pauses between them.
Usage: python tts.py            -> cache/script_<hash>.wav + cache/line_N.wav
The API key is read from GEMINI_API_KEY (never printed). In the hosted cloud
session the network proxy injects it, so the variable may be empty there.
"""
import base64, hashlib, json, os, sys, time, wave, urllib.request, urllib.error
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
CACHE = HERE / 'cache'
MODEL = 'gemini-3.1-flash-tts-preview'
VOICE = 'Fenrir'
SR = 24000
URL = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent'

LINES = [
    "Look in the grooves of your tyre. There's a hidden wear bar.",
    "Every tyre has them. The sidewall mark shows where.",
    "When the tread is level with the bar, you're at the limit.",
    "Find TWI, look in the groove. Ten seconds. Don't wait until it's flush.",
    "Have you ever looked for yours?",
]
# Replace with the shared style prompt (file style_prompt.txt wins if present).
DEFAULT_STYLE = ("Read as a short car-tips explainer: confident, warm, punchy and clear, "
                 "brisk pace, slight smile in the voice. Leave a clear one-second pause "
                 "between numbered lines and do not read the numbers.")


class QuotaExhausted(SystemExit):
    pass


def style_prompt():
    f = HERE / 'style_prompt.txt'
    return f.read_text().strip() if f.exists() else DEFAULT_STYLE


def write_wav(path, pcm16, sr=SR):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(np.asarray(pcm16, dtype='<i2').tobytes())


def read_wav(path):
    with wave.open(str(path), 'rb') as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float32) / 32768, w.getframerate()


def request(text, tries=5):
    body = json.dumps({
        'contents': [{'parts': [{'text': text}]}],
        'generationConfig': {'responseModalities': ['AUDIO'],
                             'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': VOICE}}}},
    }).encode()
    headers = {'Content-Type': 'application/json'}
    key = os.environ.get('GEMINI_API_KEY', '')
    if key:
        headers['x-goog-api-key'] = key
    delay = 4.0
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(URL, body, headers), timeout=180) as r:
                data = json.load(r)
            part = data['candidates'][0]['content']['parts'][0]['inlineData']
            return np.frombuffer(base64.b64decode(part['data']), dtype='<i2')
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors='replace')[:400]
            if e.code == 429:
                if 'PerDay' in msg or 'daily' in msg.lower() or attempt == tries - 1:
                    raise QuotaExhausted(f'Gemini quota exhausted (HTTP 429). Cached lines kept in {CACHE}. Try later.')
                wait = float(e.headers.get('Retry-After') or delay)
            elif e.code >= 500:
                wait = delay
            else:
                raise SystemExit(f'Gemini TTS HTTP {e.code}: {msg}')
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == tries - 1:
                raise SystemExit(f'Gemini TTS unreachable: {e}')
            wait = delay
        print(f'retry {attempt + 1} in {wait:.0f}s', file=sys.stderr)
        time.sleep(wait); delay *= 2
    raise SystemExit('Gemini TTS failed after retries')


def split_lines(x, n, sr=SR, thr=0.012, win=0.02):
    """Split on the n-1 longest silences; returns [(start, end)] in samples."""
    hop = int(sr * win)
    env = np.array([np.abs(x[i:i + hop]).max() for i in range(0, len(x), hop)])
    loud = env > thr
    idx = np.flatnonzero(loud)
    first, last = idx[0], idx[-1]
    gaps, run = [], None
    for i in range(first, last + 1):
        if not loud[i]:
            run = i if run is None else run
        elif run is not None:
            gaps.append((i - run, run, i)); run = None
    cuts = sorted(sorted(gaps, reverse=True)[:n - 1], key=lambda g: g[1])
    if len(cuts) < n - 1:
        raise SystemExit('could not find pauses between lines')
    bounds, s = [], first
    for _, a, b in cuts:
        bounds.append((s * hop, a * hop)); s = b
    bounds.append((s * hop, (last + 1) * hop))
    return bounds


# Shorter candidates for line 4 (original is ~4.3s of speech for a 2.0s slot).
ALT_LINES = [
    "Find TWI. Check the groove. Don't wait for flush.",
    "Find TWI, check the groove. Don't wait.",
    "Find TWI. Check the groove. Ten seconds.",
]


def main(lines=LINES, prefix='line', tag='script'):
    CACHE.mkdir(exist_ok=True)
    text = style_prompt() + '\n\n' + '\n\n'.join(f'{i + 1}. {l}' for i, l in enumerate(lines))
    h = hashlib.sha1((MODEL + VOICE + text).encode()).hexdigest()[:10]
    raw = CACHE / f'{tag}_{h}.wav'
    if raw.exists():
        print('cached:', raw.name)
    else:
        pcm = request(text)
        write_wav(raw, pcm)
        print('generated:', raw.name, f'{len(pcm) / SR:.2f}s')
    x, sr = read_wav(raw)
    for i, (a, b) in enumerate(split_lines(x, len(lines), sr)):
        write_wav(CACHE / f'{prefix}_{i + 1}.wav', (x[a:b] * 32767).astype('<i2'), sr)
        print(f'{prefix}_{i + 1}: {(b - a) / sr:.2f}s')
    (CACHE / f'{tag}.json').write_text(json.dumps({'raw': raw.name, 'lines': lines}, indent=1))


if __name__ == '__main__':
    if '--alt' in sys.argv:
        main(ALT_LINES, 'alt4', 'alt4')
    else:
        main()
