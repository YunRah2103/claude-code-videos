"""Voiceovers for the series tyres-black / seatbelt-pretensioner / catalytic-theft: one Gemini TTS request per
episode (Fenrir), ~60 s apart, raw response saved first (resumable: an episode with tts_raw.json on disk is not
re-requested), PCM wrapped as WAV, leading silence trimmed to 0.15 s, atempo 0.95 (1.0 if over 15 s), -16 LUFS.
Key: GEMINI_API_KEY / GOOGLE_API_KEY, or the cloud proxy injects it; never printed or written.
    python videos/tyres-black/src/make_voiceover.py [episode ...]
"""
import base64, json, os, re, subprocess, sys, time, urllib.error, urllib.request, wave

MODEL, VOICE = 'gemini-3.1-flash-tts-preview', 'Fenrir'
STYLE = 'Say the following in an energetic, conversational short-form explainer style, reading every sentence in full:'
SCRIPTS = {
    'tyres-black': "Why are tyres black? It's not just for looks. A filler called carbon black helps rubber last longer "
                   "and protects it from sunlight. Without it, tyres would wear out faster. Did you know a tyre's colour "
                   "does a job too? Would you have guessed that?",
    # fact check: motor pretensioners exist only in some cars; 'helps' hedges the restraint claim
    'seatbelt-pretensioner': "Your seatbelt can tighten by itself. In a crash, a small charge, or in some cars a motor, "
                             "pulls it snug in a fraction of a second. That's called a pretensioner. It helps hold you "
                             "back before the impact gets worse. Did you know your belt could move like that?",
    'catalytic-theft': "Thieves can steal a catalytic converter in minutes. It's the part of your exhaust that cleans the "
                       "fumes. Inside are precious metals like platinum, palladium and rhodium. That's why it's a target. "
                       "Do you know where yours is?",
}
API = 'https://generativelanguage.googleapis.com/v1beta/models'
KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or 'proxy-injected'
LOG = []


def post(text):
    body = {'contents': [{'parts': [{'text': STYLE + ' ' + text}]}],
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
            print(f'429: waiting {w}s', flush=True); LOG.append(w); time.sleep(w)


def dur(p):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p],
                                capture_output=True, text=True).stdout)


def d_prev_over(out):
    return os.path.exists(f'{out}/voiceover.wav') and _seen.get(out, 0) >= 2


_seen = {}


def cap_pauses(src, dst):
    """flood-save's pause cap (inner silences > 0.25 s shortened to 0.25 s, 10 ms fades; words untouched)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('fs_vo', 'videos/flood-save/src/make_voiceover.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.cap_pauses(src, dst, cap=0.25, ask=0.25)


def build(ep, force=False):
    out = f'out/{ep}'; os.makedirs(out, exist_ok=True); raw_p = f'{out}/tts_raw.json'
    fresh = force or not os.path.exists(raw_p)
    if fresh:
        raw = post(SCRIPTS[ep]); open(raw_p, 'wb').write(raw); print(ep, 'request sent')
    part = json.load(open(raw_p))['candidates'][0]['content']['parts'][0]['inlineData']
    mime = part['mimeType']; rate = int(re.search(r'rate=(\d+)', mime).group(1)) if 'rate=' in mime else 24000
    assert 'l16' in mime.lower() or 'pcm' in mime.lower(), mime
    with wave.open(f'{out}/tts_raw.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(base64.b64decode(part['data']))
    src, capped = f'{out}/tts_raw.wav', False
    for tempo in (0.95, 1.0, 0.95, 1.0):
        if tempo == 0.95 and d_prev_over(out):   # still over 15 s at 1.0x: shorten only the silent gaps, keep every word
            cap_pauses(src, f'{out}/tts_tight.wav'); src, capped = f'{out}/tts_tight.wav', True
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-af',
                        'silenceremove=start_periods=1:start_threshold=-45dB,adelay=120,areverse,'
                        'silenceremove=start_periods=1:start_threshold=-45dB,adelay=80,areverse,'
                        f'atempo={tempo},loudnorm=I=-16:TP=-1.5:LRA=11',
                        '-ar', '48000', '-ac', '1', f'{out}/voiceover.wav'], check=True)
        _seen[out] = _seen.get(out, 0) + 1
        d = dur(f'{out}/voiceover.wav'); print(f'{ep}: mime {mime}, tempo {tempo}: {d:.2f}s', flush=True)
        if d <= 14.4: break
    json.dump({'tempo': tempo, 'dur': d, 'mime': mime, 'pauses_capped': capped}, open(f'{out}/vo_meta.json', 'w'))
    return fresh


if __name__ == '__main__':
    eps = [a for a in sys.argv[1:] if a in SCRIPTS] or list(SCRIPTS); force = '--force' in sys.argv
    for i, ep in enumerate(eps):
        if build(ep, force) and i < len(eps) - 1: time.sleep(60)
    if LOG: print('429 waits:', LOG)
