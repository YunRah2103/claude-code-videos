"""seatbelt-fight voiceover: ONE Gemini TTS request (Fenrir) -> raw response on disk -> WAV -> 0.95x -> trim -> -16 LUFS
-> faster-whisper word timings. Resumable: reuses out/seatbelt-fight/tts_raw.json if it exists.
    python videos/seatbelt-fight/src/make_voiceover.py [--again]   (--again: one re-request after a failed check)
Key: the cloud proxy injects it (or GEMINI_API_KEY / GOOGLE_API_KEY locally). Never printed or saved."""
import base64, json, os, re, subprocess, sys, time, urllib.error, urllib.request, wave
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'shared'))
OUT = os.path.join(ROOT, 'out', 'seatbelt-fight')
MODEL, VOICE = 'gemini-3.1-flash-tts-preview', 'Fenrir'
STYLE = 'Say the following in an energetic, conversational short-form explainer style, reading every sentence in full:'
SCRIPT = open(os.path.join(HERE, 'script.txt')).read().strip()
RAW, LOG = os.path.join(OUT, 'tts_raw.json'), os.path.join(OUT, 'tts_log.json')


def request():
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or 'dummy'
    body = {'contents': [{'parts': [{'text': STYLE + ' ' + SCRIPT}]}],
            'generationConfig': {'responseModalities': ['AUDIO'],
                                 'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': VOICE}}}}}
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent'
    log = json.load(open(LOG)) if os.path.exists(LOG) else {'requests': 0, 'http429': 0, 'waits': []}
    t_start = time.time()
    for wait in (30, 60, 120, 240, 240):
        req = urllib.request.Request(url, json.dumps(body).encode(), {'Content-Type': 'application/json', 'x-goog-api-key': key})
        log['requests'] += 1
        try:
            data = urllib.request.urlopen(req, timeout=240).read()
            open(RAW, 'wb').write(data); json.dump(log, open(LOG, 'w')); return
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print('model not found:', e.read()[:300]); sys.exit(2)
            if e.code != 429: raise
            log['http429'] += 1
            ra = e.headers.get('Retry-After'); wait = max(wait, int(ra) if ra and ra.isdigit() else 0)
            if time.time() - t_start + wait > 600: break
            log['waits'].append(wait); json.dump(log, open(LOG, 'w')); print('429, waiting', wait); time.sleep(wait)
    json.dump(log, open(LOG, 'w')); print('still 429 after ~10 min; rerun this script to resume'); sys.exit(3)


def to_wav():
    part = json.load(open(RAW))['candidates'][0]['content']['parts'][0]['inlineData']
    mime = part['mimeType']; rate = int(re.search(r'rate=(\d+)', mime).group(1)) if 'rate=' in mime else 24000
    assert 'l16' in mime.lower() or 'pcm' in mime.lower(), mime
    pcm = base64.b64decode(part['data']); open(os.path.join(OUT, 'tts_raw.pcm'), 'wb').write(pcm)   # raw PCM first
    with wave.open(os.path.join(OUT, 'tts_raw.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
    return mime, rate


def ff(src, dst, af):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-af', af, '-ar', '24000', '-ac', '1', dst], check=True)


def dur(p): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))


def main():
    os.makedirs(OUT, exist_ok=True)
    if '--again' in sys.argv or not os.path.exists(RAW): request()
    mime, rate = to_wav()
    raw = os.path.join(OUT, 'tts_raw.wav'); vo = os.path.join(OUT, 'voiceover.wav')
    tempo = 0.95 if dur(raw) / 0.95 <= 11.4 else 1.0   # VO starts at 3.0 s, plus a ~1.6 s fight gap; video <= 16 s
    trim = 'silenceremove=start_periods=1:start_threshold=-45dB,adelay=150:all=1,'   # lead-in exactly 0.15 s
    ff(raw, vo, trim + (f'atempo={tempo},' if tempo != 1 else '') + 'areverse,silenceremove=start_periods=1:start_threshold=-45dB,'
       'areverse,apad=pad_dur=0.25,loudnorm=I=-16:TP=-1.5:LRA=11')
    from align_fw import align
    align(vo, os.path.join(HERE, 'words.json'), SCRIPT)
    words = json.load(open(os.path.join(HERE, 'words.json')))
    n = len(SCRIPT.split()); ok = sum(1 for w in words if not w.get('est'))
    rep = {'model': MODEL, 'voice': VOICE, 'mime': mime, 'rate': rate, 'tempo': tempo, 'raw_s': round(dur(raw), 2),
           'vo_s': round(dur(vo), 2), 'script_words': n, 'aligned': ok, 'aligned_pct': round(100 * ok / n, 1)}
    rep.update(json.load(open(LOG)))
    json.dump(rep, open(os.path.join(OUT, 'vo_report.json'), 'w'), indent=1); print(rep)
    if rep['aligned_pct'] < 95 or rep['vo_s'] < 9: print('CHECK FAILED'); sys.exit(4)


if __name__ == '__main__':
    main()
