"""Generate the voiceover and word timings (PocketSphinx alignment).
Usage: python voice.py VOICE.onnx OUTDIR        (local Piper voice, one sentence at a time)
       python voice.py gemini:Fenrir OUTDIR     (Gemini TTS, whole script in one take)
-> OUTDIR/voice.wav, OUTDIR/words.json"""
import base64, json, re, subprocess, sys, urllib.request, wave
from pathlib import Path
import numpy as np
from pocketsphinx import Decoder

SCRIPT = [
    "This Formula One car could drive upside down.",
    "And the secret isn't the engine. It's the air.",
    "A Formula One car is basically an airplane wing, flipped upside down.",
    "A plane's wing pushes it up. This wing pushes the car down.",
    "That's called downforce.",
    "Downforce presses the tires into the track, so they grip harder.",
    "More grip means faster corners, without sliding off.",
    "The front wing splits the air, and guides it around the car.",
    "The rear wing pins the back down, so it stays stable.",
    "But the real hero is the floor.",
    "Air rushes underneath, speeds up, and sucks the car onto the track.",
    "At top speed, it makes more downforce than the car weighs.",
    "So on a ceiling, it would just stick there.",
    "The catch? Downforce also creates drag, and drag kills top speed.",
    "So on the straights, the wings flatten out to cut drag. Then they snap back for the corners.",
    "Grip in the corners. Speed on the straights. That's the whole game.",
    "Would you ride upside down? Tell me in the comments.",
]
EXTRA = {'downforce': 'D AW N F AO R S', "plane's": 'P L EY N Z'}
GAP, SRATE = .28, 22050



def decoder():
    d = Decoder(samprate=16000, bestpath=False)
    for w, pr in EXTRA.items():
        if d.lookup_word(w) is None: d.add_word(w, pr, True)
    return d


def align(d, pcm16k, words_norm):
    d.set_align_text(" ".join(words_norm))
    d.start_utt(); d.process_raw(pcm16k.tobytes(), full_utt=True); d.end_utt()
    return [s for s in d.seg() if s.word not in ('<s>', '</s>', '<sil>', '[NOISE]')]


def gemini(voice, out):
    prompt = ("Read this as an energetic, punchy short-form video narrator explaining Formula One, "
              "with a short natural pause between sentences:\n\n" + "\n".join(SCRIPT))
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": "proxy"})
    d = json.load(urllib.request.urlopen(req, timeout=300))
    part = d['candidates'][0]['content']['parts'][0]['inlineData']
    rate = int(re.search(r'rate=(\d+)', part['mimeType']).group(1))
    a = np.frombuffer(base64.b64decode(part['data']), np.int16)
    lead = .35
    a = np.r_[np.zeros(int(rate * lead), np.int16), a]
    a16 = np.interp(np.arange(0, len(a), rate / 16000), np.arange(len(a)), a).astype(np.int16)
    disp, line_of = [], []
    for si, line in enumerate(SCRIPT):
        for w in line.split(): disp.append(w); line_of.append(si)
    norm = [re.sub(r"[^a-z']", "", w.lower()) for w in disp]
    segs = align(decoder(), a16, norm)
    assert len(segs) == len(disp), ('alignment mismatch', len(segs), len(disp))
    words = [dict(w=w, s=round(s.start_frame / 100, 2), e=round((s.end_frame + 1) / 100, 2), line=li)
             for w, s, li in zip(disp, segs, line_of)]
    with wave.open(str(out / 'voice.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(a.tobytes())
    json.dump(words, open(out / 'words.json', 'w'))
    print(f"gemini {voice}: {len(a) / rate:.2f}s, {len(words)} words aligned")


if sys.argv[1].startswith('gemini:'):
    out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    gemini(sys.argv[1].split(':', 1)[1], out); sys.exit(0)

model, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
pcm, words, t0 = [], [], .35
for si, line in enumerate(SCRIPT):
    raw = subprocess.run([sys.executable, '-m', 'piper', '-m', model, '--length-scale', '.95', '--output-raw'],
                         input=line.encode(), capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.int16)
    a16 = np.interp(np.arange(0, len(a), SRATE / 16000), np.arange(len(a)), a).astype(np.int16)
    disp = line.split(); norm = [re.sub(r"[^a-z']", "", w.lower()) for w in disp]
    d = Decoder(samprate=16000, bestpath=False)
    for w, pr in EXTRA.items():
        if d.lookup_word(w) is None: d.add_word(w, pr, True)
    d.set_align_text(" ".join(norm))
    d.start_utt(); d.process_raw(a16.tobytes(), full_utt=True); d.end_utt()
    segs = [s for s in d.seg() if s.word not in ('<s>', '</s>', '<sil>', '[NOISE]')]
    assert len(segs) == len(disp), (line, [s.word for s in segs])
    for w, s in zip(disp, segs):
        words.append(dict(w=w, s=round(t0 + s.start_frame / 100, 2), e=round(t0 + (s.end_frame + 1) / 100, 2), line=si))
    pcm.append(np.zeros(int(SRATE * (t0 - sum(len(p) for p in pcm) / SRATE)), np.int16)); pcm.append(a)
    t0 += len(a) / SRATE + GAP
    print(f"{si:2d} {t0:6.2f}s {line}")
with wave.open(str(out / 'voice.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SRATE); w.writeframes(np.concatenate(pcm).tobytes())
json.dump(words, open(out / 'words.json', 'w'))
