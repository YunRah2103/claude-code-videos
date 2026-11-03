"""One Gemini TTS request for the whole script -> out/speed-limit-deal-2d/voiceover.wav (resumable); copy it to out/speed-limit-deal-3d/ for the 3D version.

    python videos/speed-limit-deal-2d/src/voiceover.py
Model gemini-3.1-flash-tts-preview, prebuilt voice Fenrir, one request. The raw JSON response is saved before any
processing (raw_response.json) and reused on later runs, so the job never re-requests. HTTP 429: exponential back-off
30/60/120/240 s honouring Retry-After, giving up after ~10 min. Key: GEMINI_API_KEY or GOOGLE_API_KEY (never printed);
in the hosted cloud the proxy injects it, so a placeholder is sent. Post: the raw read is 18.3 s, over 15 s at 0.95x and 1.0x,
so pauses are capped at PAUSE s and a pitch-preserving atempo (1.219) lands it on TARGET s; lead silence <=0.15 s.
"""
import base64, json, os, subprocess, sys, time, urllib.error, urllib.request, wave
import numpy as np

MODEL, VOICE = 'gemini-3.1-flash-tts-preview', 'Fenrir'
STYLE = 'Say the following in an energetic, conversational short-form explainer style:'
SCRIPT = ("Your BMW could go faster. Three German brands reportedly agreed it wouldn't. BMW, Mercedes, Audi. "
          "No law, just a gentleman's agreement. A limit of 155 miles an hour. Porsche reportedly never joined. "
          "Some can be unlocked. Would you remove the limit?")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
OUT = os.path.join(ROOT, 'out', 'speed-limit-deal-2d')
RAW, LOG = os.path.join(OUT, 'raw_response.json'), os.path.join(OUT, 'tts_log.json')
PAUSE, TARGET = 0.14, 13.7
API = 'https://generativelanguage.googleapis.com/v1beta/models'


def key(): return os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or 'proxy-injected'


def request():
    body = {'contents': [{'parts': [{'text': STYLE + ' ' + SCRIPT}]}],
            'generationConfig': {'responseModalities': ['AUDIO'],
                                 'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': VOICE}}}}}
    req = urllib.request.Request(f'{API}/{MODEL}:generateContent', json.dumps(body).encode(),
                                 {'Content-Type': 'application/json', 'x-goog-api-key': key()})
    log = {'model': MODEL, 'voice': VOICE, 'requests': 0, 'http429': 0, 'waited_s': 0}
    t_start = time.time()
    for delay in (30, 60, 120, 240, None):
        log['requests'] += 1
        try:
            data = urllib.request.urlopen(req, timeout=300).read()
            open(RAW, 'wb').write(data); json.dump(log, open(LOG, 'w')); return
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf8', 'replace')[:400]
            if e.code == 404:
                lst = json.load(urllib.request.urlopen(urllib.request.Request(f'{API}?pageSize=200', headers={'x-goog-api-key': key()})))
                names = [m['name'] for m in lst.get('models', []) if 'tts' in m['name']]
                json.dump(dict(log, error=msg, tts_models=names), open(LOG, 'w'))
                sys.exit(f'model not found: {MODEL}; TTS models listed: {names}')
            if e.code != 429 or delay is None or time.time() - t_start > 600:
                json.dump(dict(log, error=f'{e.code} {msg}'), open(LOG, 'w')); sys.exit(f'HTTP {e.code}: {msg}')
            log['http429'] += 1
            ra = e.headers.get('Retry-After'); wait = max(delay, int(ra) if ra and ra.isdigit() else 0)
            print(f'429, waiting {wait}s', flush=True); time.sleep(wait); log['waited_s'] += wait


def process():
    r = json.load(open(RAW))
    part = r['candidates'][0]['content']['parts'][0]['inlineData']
    mime = part['mimeType']                         # e.g. audio/L16;codec=pcm;rate=24000
    rate = int(next((p.split('=')[1] for p in mime.split(';') if p.strip().startswith('rate=')), 24000))
    assert 'l16' in mime.lower() or 'pcm' in mime.lower(), mime
    src = os.path.join(OUT, 'voiceover_raw.wav')
    with wave.open(src, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(base64.b64decode(part['data']))
    dst, tight = os.path.join(OUT, 'voiceover.wav'), os.path.join(OUT, 'voiceover_tight.wav')
    y = np.frombuffer(open(src, 'rb').read()[44:], '<i2').astype(np.float64)
    raw_dur = len(y) / rate
    # Fenrir's read is ~18.3 s raw (~15 s of speech), so 0.95x / 1.0x cannot meet the 15 s cap: cap every pause at
    # PAUSE s (cuts only inside silences, 10 ms fades), then a pitch-preserving atempo lands the read on TARGET s.
    det = subprocess.run(['ffmpeg', '-i', src, '-af', 'silencedetect=n=-40dB:d=0.12', '-f', 'null', '-'], capture_output=True, text=True).stderr
    st = [float(l.split('silence_start: ')[1]) for l in det.splitlines() if 'silence_start' in l]
    en = [float(l.split('silence_end: ')[1].split()[0]) for l in det.splitlines() if 'silence_end' in l]
    keep, pos, f = [], 0, int(0.01 * rate)
    for a, b in zip(st, en):
        a, b = int(a * rate), int(b * rate)
        if a == 0: pos = max(0, b - int(0.03 * rate)); continue          # lead silence: drop
        cut0, cut1 = a + int(PAUSE / 2 * rate), b - int(PAUSE / 2 * rate)
        if b >= len(y) - 1: cut1 = len(y)                                 # tail silence: drop
        if cut1 > cut0:
            seg = y[pos:cut0].copy(); seg[-f:] *= np.linspace(1, 0, f); keep.append(seg); pos = cut1
    if len(y) - pos > f: seg = y[pos:].copy(); seg[:f] *= np.linspace(0, 1, f); keep.append(seg)
    y = np.concatenate(keep)
    with wave.open(tight, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(y.astype('<i2').tobytes())
    tempo = round(max(1.0, len(y) / rate / TARGET), 3)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tight, '-af', f'atempo={tempo},adelay=120', '-ar', '24000', '-ac', '1', dst], check=True)
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', dst],
                               capture_output=True, text=True).stdout)
    log = json.load(open(LOG)); log.update(mime=mime, rate=rate, raw_s=round(raw_dur, 3), pause_cap=PAUSE, tempo=tempo, duration=round(dur, 3))
    json.dump(log, open(LOG, 'w'))
    print(json.dumps(log))


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    if not os.path.isfile(RAW): request()
    process()
