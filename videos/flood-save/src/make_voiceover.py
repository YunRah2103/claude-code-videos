"""flood-save voiceover: ONE Gemini TTS request (Fenrir), raw response saved first, PCM wrapped as WAV,
atempo 0.95 (1.0 if over 15 s), leading silence trimmed to <= 0.15 s.  Resumable: skips the request if the raw
response is already on disk.  The key comes from GEMINI_API_KEY / GOOGLE_API_KEY, or the cloud proxy injects it;
it is never printed or written.
    python videos/flood-save/src/make_voiceover.py [out_dir=out/flood-save]
"""
import base64, json, os, re, subprocess, sys, time, urllib.error, urllib.request, wave

MODEL, VOICE = 'gemini-3.1-flash-tts-preview', 'Fenrir'
STYLE = 'Say the following in a calm, thoughtful, conversational short-form explainer style, with a slight pause before the question:'
SCRIPT = ("Heavy rain, flooded street. Which car would you save? A small car sits lower in the water. "
          "An SUV often sits higher. But higher isn't always safer. Would you save the hatchback or the SUV?")
OUT = sys.argv[1] if len(sys.argv) > 1 else 'out/flood-save'
API = 'https://generativelanguage.googleapis.com/v1beta/models'
KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or 'proxy-injected'


def post():
    body = {'contents': [{'parts': [{'text': STYLE + ' ' + SCRIPT}]}],
            'generationConfig': {'responseModalities': ['AUDIO'],
                                 'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': VOICE}}}}}
    req = urllib.request.Request(f'{API}/{MODEL}:generateContent', json.dumps(body).encode(),
                                 {'Content-Type': 'application/json', 'x-goog-api-key': KEY})
    waits, start = [30, 60, 120, 240], time.time()
    for i in range(len(waits) + 1):
        try:
            return urllib.request.urlopen(req, timeout=300).read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                ls = json.load(urllib.request.urlopen(urllib.request.Request(f'{API}?pageSize=1000', headers={'x-goog-api-key': KEY})))
                print('MODEL NOT FOUND. tts models:', [m['name'] for m in ls.get('models', []) if 'tts' in m['name']]); sys.exit(2)
            if e.code != 429 or i == len(waits) or time.time() - start > 600:
                print('HTTP', e.code, e.read()[:300]); sys.exit(3)
            w = max(waits[i], int(e.headers.get('Retry-After') or 0))
            print(f'429: waiting {w}s', flush=True); time.sleep(w)


def cap_pauses(src, dst, db=-40, cap=0.32, ask=0.5):
    """Cut only inside silences: every inner pause > cap is shortened to cap (the pause before the question to `ask`),
    with 10 ms fades at the cut. Words are untouched; the 17.5 s read at 1.0x would not fit the 15 s limit otherwise."""
    import numpy as np
    with wave.open(src) as w: sr = w.getframerate(); y = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32)
    log = subprocess.run(['ffmpeg', '-i', src, '-af', f'silencedetect=n={db}dB:d=0.2', '-f', 'null', '-'], capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', log)]; en = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', log)]
    inner = [(a, b) for a, b in zip(st, en) if a > 0.05 and b < len(y) / sr - 0.05]
    out, pos, f = [], 0, int(0.01 * sr)
    for i, (a, b) in enumerate(inner):
        c = ask if i == len(inner) - 2 else cap   # second-to-last inner pause: 'safer.' -> 'Would you save...'
        if b - a <= c: continue
        k0, k1 = int((a + c / 2) * sr), int((b - c / 2) * sr)
        seg = y[pos:k0].copy(); seg[-f:] *= np.linspace(1, 0, f); out.append(seg)
        pos = k1; y[k1:k1 + f] *= np.linspace(0, 1, f)
    out.append(y[pos:]); z = np.concatenate(out)
    with wave.open(dst, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(z.astype('<i2').tobytes())


def main():
    os.makedirs(OUT, exist_ok=True)
    raw_p = f'{OUT}/tts_raw.json'
    if not os.path.exists(raw_p):
        raw = post(); open(raw_p, 'wb').write(raw); print('requests: 1')
    part = json.load(open(raw_p))['candidates'][0]['content']['parts'][0]['inlineData']
    mime = part['mimeType']; print('mime:', mime)
    rate = int(re.search(r'rate=(\d+)', mime).group(1)) if 'rate=' in mime else 24000
    assert 'l16' in mime.lower() or 'pcm' in mime.lower(), mime
    with wave.open(f'{OUT}/tts_raw.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(base64.b64decode(part['data']))
    cap_pauses(f'{OUT}/tts_raw.wav', f'{OUT}/tts_tight.wav')
    for tempo in (0.95, 1.0):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{OUT}/tts_tight.wav', '-af',
                        f'silenceremove=start_periods=1:start_threshold=-45dB,adelay=120,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,atempo={tempo}',
                        '-ar', '24000', '-ac', '1', f'{OUT}/voiceover.wav'], check=True)
        d = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                                  f'{OUT}/voiceover.wav'], capture_output=True, text=True).stdout)
        print(f'tempo {tempo}: {d:.2f}s')
        if d <= 14.3: break   # leaves the 0.5 s loop tail inside 15 s


if __name__ == '__main__':
    main()
