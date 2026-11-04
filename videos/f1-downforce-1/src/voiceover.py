"""Voiceover for the f1-downforce series (all three episodes, one resume command):
    python videos/f1-downforce-1/src/voiceover.py [1 2 3]
Gemini TTS, model gemini-3.1-flash-tts-preview, prebuilt voice Fenrir, one request per episode, ~60 s apart.
Backs off on HTTP 429 (30/60/120/240 s, honours Retry-After, gives up after ~10 min). The raw JSON response is saved
before processing (out/<ep>/tts_raw.json); the PCM is wrapped as WAV at the stated rate, slowed with atempo
(0.86x ep 1, 0.95x eps 2-3; 1.0x if that would pass 15 s), leading silence trimmed to <= 0.15 s -> out/<ep>/voiceover.wav.
Word timings: faster-whisper word timestamps on the real audio, matched to the script -> videos/<ep>/src/words.json.
The key comes from GEMINI_API_KEY / GOOGLE_API_KEY if set; otherwise the session proxy injects it. It is never printed.
"""
import base64, difflib, json, os, re, subprocess, sys, time, urllib.error, urllib.request, wave
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
MODEL, VOICE = 'gemini-3.1-flash-tts-preview', 'Fenrir'
STYLE = 'Say the following in an energetic, conversational short-form explainer style: '
SCRIPTS = {
    1: "This formula one car could drive upside down. Reportedly. Its wings push it onto the track. That push is called "
       "downforce. At speed, it can be more than the car's own weight. Would it stay on the ceiling?",
    2: "Downforce sucks the car onto the track. The tyres grip harder, so it slides less in corners. But it also creates "
       "drag, which slows the car down on straights.",
    3: "So why not run maximum downforce all the time? The rear wing flattens on straights, for less drag. Then it snaps "
       "back up for corners. Would you drive it upside down?",
}
TEMPO = {1: 0.86, 2: 0.95, 3: 0.95}
URL = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent'


def request(text):
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or 'proxy-injected'
    body = {'contents': [{'parts': [{'text': STYLE + text}]}],
            'generationConfig': {'responseModalities': ['AUDIO'],
                                 'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': VOICE}}}}}
    t_start, waits = time.time(), iter((30, 60, 120, 240, 240))
    while True:
        try:
            req = urllib.request.Request(URL, json.dumps(body).encode(), {'Content-Type': 'application/json', 'x-goog-api-key': key})
            return urllib.request.urlopen(req, timeout=300).read(), None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                lst = urllib.request.urlopen(urllib.request.Request(
                    'https://generativelanguage.googleapis.com/v1beta/models?pageSize=200', headers={'x-goog-api-key': key})).read()
                names = [m['name'] for m in json.loads(lst)['models'] if 'tts' in m['name']]
                return None, f'404 model not found; TTS models available: {names}'
            if e.code != 429: return None, f'HTTP {e.code}: {e.read()[:300]!r}'
            w = next(waits, None); ra = e.headers.get('Retry-After')
            if ra and ra.isdigit(): w = max(w or 0, int(ra))
            if w is None or time.time() - t_start + w > 600: return None, '429 rate limit: gave up after ~10 min'
            print(f'  429 -> waiting {w} s', flush=True); time.sleep(w)


def ff(args, data=None):
    return subprocess.run(['ffmpeg', '-v', 'error', *args], input=data, capture_output=True, check=True).stdout


def build(ep, raw_json, out_dir):
    d = json.loads(raw_json); part = d['candidates'][0]['content']['parts'][0]['inlineData']
    mime = part['mimeType']; rate = int(re.search(r'rate=(\d+)', mime).group(1)) if 'rate=' in mime else 24000
    assert 'l16' in mime.lower() or 'pcm' in mime.lower(), mime
    pcm = base64.b64decode(part['data'])
    raw_wav = os.path.join(out_dir, 'tts_raw.wav')
    with wave.open(raw_wav, 'wb') as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
    def make(tempo):
        y = np.frombuffer(ff(['-i', raw_wav, '-af', f'atempo={tempo}', '-ar', str(rate), '-ac', '1', '-f', 's16le', '-']), '<i2')
        idx = np.where(np.abs(y.astype(np.int32)) > 32768 * 10 ** (-45 / 20))[0]
        return y[max(0, idx[0] - int(0.15 * rate)):]                      # leading silence <= 0.15 s
    tempo = TEMPO[ep]; y = make(tempo)
    if len(y) / rate > 15.0: tempo = 1.0; y = make(tempo)
    out = os.path.join(out_dir, 'voiceover.wav')
    with wave.open(out, 'wb') as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(y.tobytes())
    return out, tempo, len(y) / rate, mime


def norm(w): return re.sub(r"[^a-z0-9']", '', w.lower().replace('’', "'"))


def align(ep, wav, src_dir):
    from faster_whisper import WhisperModel
    m = WhisperModel('small.en', device='cpu', compute_type='int8')
    audio = np.frombuffer(ff(['-i', wav, '-ar', '16000', '-ac', '1', '-f', 'f32le', '-']), '<f4')
    segs, _ = m.transcribe(audio, word_timestamps=True, initial_prompt=SCRIPTS[ep], language='en', beam_size=5)
    hw = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
    disp = SCRIPTS[ep].split()
    a, b = [norm(x) for x in disp], [norm(x[0]) for x in hw]
    words = [None] * len(disp)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size): words[blk.a + k] = dict(w=disp[blk.a + k], s=round(hw[blk.b + k][1], 2), e=round(hw[blk.b + k][2], 2))
    est = 0
    for i, w in enumerate(words):                                       # unmatched (e.g. "one" heard as "1"): fill between neighbours
        if w is None:
            prev = next((words[j]['e'] for j in range(i - 1, -1, -1) if words[j]), 0.0)
            nxt = next((words[j]['s'] for j in range(i + 1, len(words)) if words[j]), prev + 0.3)
            run = [j for j in range(i, len(words)) if words[j] is None]
            run = run[:next((k for k in range(1, len(run)) if run[k] != run[k - 1] + 1), len(run))]
            chars = [len(disp[j]) for j in run]; tot = sum(chars); t = prev
            for j, c in zip(run, chars):
                dt = (nxt - prev) * c / tot; words[j] = dict(w=disp[j], s=round(t, 2), e=round(t + dt, 2), est=True); t += dt; est += 1
    json.dump(words, open(os.path.join(src_dir, 'words.json'), 'w'), indent=0)
    return len(disp) - est, est


def main(eps):
    log, requested = [], 0
    for ep in eps:
        name = f'f1-downforce-{ep}'; out_dir = os.path.join(ROOT, 'out', name); src = os.path.join(ROOT, 'videos', name, 'src')
        os.makedirs(out_dir, exist_ok=True)
        rawp = os.path.join(out_dir, 'tts_raw.json')
        if os.path.isfile(rawp) and b'inlineData' in open(rawp, 'rb').read():   # resume: reuse a saved response
            raw = open(rawp, 'rb').read(); print(f'{name}: reusing saved response', flush=True)
        else:
            if requested: print('waiting 60 s between requests', flush=True); time.sleep(60)
            raw, err = request(SCRIPTS[ep]); requested += 1
            if err: print(f'{name}: {err}'); log.append(dict(ep=name, error=err)); break
            open(rawp, 'wb').write(raw)                                      # raw response saved before processing
        wav, tempo, dur, mime = build(ep, raw, out_dir)
        ok, est = align(ep, wav, src)
        print(f'{name}: {mime}, tempo {tempo}, {dur:.2f} s, words aligned {ok}, estimated {est}', flush=True)
        log.append(dict(ep=name, mime=mime, tempo=tempo, dur=round(dur, 2), aligned=ok, estimated=est))
    json.dump(log, open(os.path.join(ROOT, 'out', 'f1-downforce-1', 'tts_log.json'), 'w'), indent=1)


if __name__ == '__main__':
    main([int(a) for a in sys.argv[1:]] or [1, 2, 3])
