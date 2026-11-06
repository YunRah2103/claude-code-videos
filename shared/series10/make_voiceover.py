"""Gemini TTS (Fenrir) voiceovers for the ten-episode series; resumable (skips episodes whose voiceover is accepted).
    python shared/series10/make_voiceover.py [episode ...]        (SERIES=series6 for the six-episode series)
Per episode: one request -> raw JSON saved to out/<ep>/tts_raw*.json -> WAV at the stated PCM rate -> lead silence <=0.15 s
-> atempo 0.95 (1.0 if over 15 s) -> -16 LUFS -> out/<ep>/voiceover.wav; faster-whisper alignment -> videos/<ep>/src/words.json.
Completeness: re-request once if <95 % of script words aligned or audio < 11 s. 429: back off 30/60/120/240 s (Retry-After
honoured), give up after ~10 min. Batches: first half, 180 s pause, second half; 60 s between requests. Key comes from the proxy
or GEMINI_API_KEY / GOOGLE_API_KEY (never printed or written)."""
import base64, json, os, re, subprocess, sys, time, urllib.error, urllib.request, wave
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SERIES = os.environ.get('SERIES', 'series10')
sys.path.insert(0, os.path.join(ROOT, 'shared', SERIES)); sys.path.insert(0, os.path.join(ROOT, 'shared'))
from scripts import EPISODES, NAMES
MODEL, VOICE = 'gemini-3.1-flash-tts-preview', 'Fenrir'
STYLE = 'Say the following in an energetic, conversational short-form explainer style, reading every sentence in full: '
LOG = os.path.join(ROOT, 'out', SERIES, 'tts_log.json')
HALF = (len(EPISODES) + 1) // 2                 # batch 1 = first half, 180 s pause, batch 2


def log(**k):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    d = json.load(open(LOG)) if os.path.exists(LOG) else []
    d.append(dict(time=time.strftime('%H:%M:%S'), **k)); json.dump(d, open(LOG, 'w'), indent=1)
    print(k, flush=True)


def request(ep, text, tag):
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or 'proxy-injected'
    body = {'contents': [{'parts': [{'text': STYLE + text}]}],
            'generationConfig': {'responseModalities': ['AUDIO'],
                                 'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': VOICE}}}}}
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent'
    path = os.path.join(ROOT, 'out', ep, f'tts_raw{tag}.json')
    t_start, waits = time.time(), [30, 60, 120, 240]
    while not os.path.exists(path):          # a saved raw response is reused, never re-requested
        req = urllib.request.Request(url, json.dumps(body).encode(), {'Content-Type': 'application/json', 'x-goog-api-key': key})
        try:
            data = urllib.request.urlopen(req, timeout=300).read(); open(path, 'wb').write(data); log(ep=ep, request=tag or 'first')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                ms = json.load(urllib.request.urlopen(urllib.request.Request(
                    'https://generativelanguage.googleapis.com/v1beta/models?pageSize=200', headers={'x-goog-api-key': key})))
                log(ep=ep, error='model not found', tts_models=[m['name'] for m in ms['models'] if 'tts' in m['name']]); sys.exit(2)
            if e.code != 429 or not waits or time.time() - t_start > 600:
                log(ep=ep, error=f'HTTP {e.code}', body=e.read()[:300].decode('utf8', 'replace')); sys.exit(3)
            w = max(waits.pop(0), int(e.headers.get('Retry-After') or 0)); log(ep=ep, http=429, wait=w); time.sleep(w)
    raw = open(path, 'rb').read()
    part = json.loads(raw)['candidates'][0]['content']['parts'][0]['inlineData']
    mime = part['mimeType'].lower(); rate = int(re.search(r'rate=(\d+)', mime).group(1)) if 'rate=' in mime else 24000
    assert 'l16' in mime or 'pcm' in mime, mime
    wav = os.path.join(ROOT, 'out', ep, f'raw{tag}.wav')
    with wave.open(wav, 'wb') as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(base64.b64decode(part['data']))
    return wav, mime, rate


def dur(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))


def process(ep, raw, script):
    out = os.path.join(ROOT, 'out', ep, 'voiceover.wav')
    lead = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15"   # keeps <=0.15 s of lead silence
    for tempo in (0.95, 1.0):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-af', f'{lead},atempo={tempo},loudnorm=I=-16:TP=-1.5:LRA=11',
                        '-ar', '48000', '-ac', '1', out], check=True)
        if dur(out) <= 15.0: break
    from align_fw import align
    words = align(out, os.path.join(ROOT, 'videos', ep, 'src', 'words.json'), script)
    pct = 100 * sum(1 for w in words if not w.get('est')) / len(words)
    return dict(tempo=tempo, dur=round(dur(out), 2), words=len(script.split()), aligned_pct=round(pct, 1))


def main(eps):
    first = True
    for i, (ep, script) in enumerate(EPISODES):
        if ep not in eps: continue
        os.makedirs(os.path.join(ROOT, 'out', ep), exist_ok=True); os.makedirs(os.path.join(ROOT, 'videos', ep, 'src'), exist_ok=True)
        if os.path.exists(os.path.join(ROOT, 'out', ep, 'vo_ok.json')): continue
        if not first: time.sleep(180 if i == HALF else 60)
        first = False
        tries = 0
        for tag in ('', '_retry'):
            wav, mime, rate = request(ep, script, tag); tries += 1
            r = process(ep, wav, script); r.update(ep=ep, mime=mime, rate=rate, requests=tries)
            ok = r['aligned_pct'] >= 95 and r['dur'] >= 11
            log(**r, accepted=ok)
            if ok: break
            time.sleep(60)
        json.dump(r, open(os.path.join(ROOT, 'out', ep, 'vo_ok.json'), 'w'))
        if i == HALF - 1 and any(e in eps for e in NAMES[HALF:]): log(note='batch 1 done; 180 s pause')


if __name__ == '__main__':
    main(sys.argv[1:] or NAMES)
