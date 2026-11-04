"""One Gemini TTS request for the whole script -> raw response on disk -> WAV -> atempo 0.95 -> voiceover.wav.
    python videos/brand-story-lamborghini/src/make_voiceover.py
The cloud proxy injects the API key (or GEMINI_API_KEY / GOOGLE_API_KEY is sent if set); the key is never printed or saved.
On HTTP 429 it backs off 30/60/120/240 s (honouring Retry-After) and gives up after ~10 min. Re-running resumes:
an existing raw response is reused, so no second request is made."""
import base64, json, os, re, subprocess, sys, time, urllib.error, urllib.request, wave

MODEL = 'gemini-3.1-flash-tts-preview'
VOICE = os.environ.get('TTS_VOICE', 'Fenrir')
STYLE = os.environ.get('TTS_STYLE', 'Say the following like a confident, engaging documentary narrator, with energy and clear pacing: ')
TAG = os.environ.get('TTS_TAG', '')            # e.g. '_v2' keeps an earlier read on disk
SCRIPT = ('Lamborghini exists because of a bad clutch. Ferruccio Lamborghini made tractors, and he owned Ferraris. '
          'Reportedly, his Ferrari clutch kept failing. He took it to Enzo Ferrari. The story says Enzo told him to stick to tractors. '
          'So Ferruccio built his own sports car company. In 1963, Automobili Lamborghini began. Its first production car was the 350 GT. '
          'Whether the insult really happened is still debated. But the rivalry is real. Do you believe the story?')
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
OUT = os.path.join(ROOT, 'out', 'brand-story-lamborghini')
RAW, PCMWAV, FINAL, LOG = (os.path.join(OUT, n.format(TAG)) for n in ('tts_response{}.json', 'tts_raw{}.wav', 'voiceover{}.wav', 'tts_log{}.json'))


def request():
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or 'dummy'   # proxy replaces the dummy
    body = {'contents': [{'parts': [{'text': STYLE + SCRIPT}]}],
            'generationConfig': {'responseModalities': ['AUDIO'],
                                 'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': VOICE}}}}}
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent'
    log = {'model': MODEL, 'voice': VOICE, 'requests': 0, 'http429': [], 'waits_s': []}
    t_start = time.time(); waits = [30, 60, 120, 240]
    while True:
        log['requests'] += 1
        try:
            req = urllib.request.Request(url, json.dumps(body).encode(), {'Content-Type': 'application/json', 'x-goog-api-key': key})
            data = urllib.request.urlopen(req, timeout=300).read()
            open(RAW, 'wb').write(data); json.dump(log, open(LOG, 'w'), indent=1); return
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors='replace')[:600]
            if e.code == 404:
                lst = urllib.request.urlopen(urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models?pageSize=200',
                                                                    headers={'x-goog-api-key': key})).read()
                names = [m['name'] for m in json.loads(lst)['models'] if 'tts' in m['name']]
                json.dump(log, open(LOG, 'w'), indent=1)
                sys.exit(f'model not found (404). TTS models available: {names}')
            if e.code != 429 or not waits or time.time() - t_start > 600:
                json.dump(log, open(LOG, 'w'), indent=1); sys.exit(f'HTTP {e.code}: {msg}')
            ra = e.headers.get('Retry-After'); w = max(waits.pop(0), int(ra) if ra and ra.isdigit() else 0)
            log['http429'].append(time.strftime('%H:%M:%S')); log['waits_s'].append(w)
            print(f'429, waiting {w}s', flush=True); time.sleep(w)


def main():
    os.makedirs(OUT, exist_ok=True)
    if not os.path.exists(RAW): request()
    part = json.load(open(RAW))['candidates'][0]['content']['parts'][0]['inlineData']
    mime = part['mimeType']; rate = int(re.search(r'rate=(\d+)', mime).group(1)) if 'rate=' in mime else 24000
    assert 'l16' in mime.lower() or 'pcm' in mime.lower(), mime
    with wave.open(PCMWAV, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(base64.b64decode(part['data']))
    for tempo in (0.95, 1.0):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', PCMWAV, '-af',
                        f'silenceremove=start_periods=1:start_threshold=-45dB,adelay=120|120,atempo={tempo}',
                        '-ar', '48000', '-ac', '1', FINAL], check=True)
        d = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', FINAL]))
        if d <= 42 - 1.0: break
    log = json.load(open(LOG)) if os.path.exists(LOG) else {}
    log.update(mime=mime, rate=rate, tempo=tempo, duration=round(d, 2)); json.dump(log, open(LOG, 'w'), indent=1)
    print(json.dumps(log))


if __name__ == '__main__':
    main()
