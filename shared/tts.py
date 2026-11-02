"""Gemini TTS (generativelanguage API; the cloud proxy injects the key) -> one continuous voiceover.

    python shared/tts.py out.wav "block 1" "block 2" ... [--voice Puck] [--gap 2.0]
Each block is read with the same voice and style prompt, loudness-normalised to -16 LUFS, edge silence trimmed, and
the blocks are joined with exactly `gap` s of digital silence (so split_vo.py cuts one clip per block).
"""
import base64, json, os, subprocess, sys, urllib.request
import numpy as np

MODEL = os.environ.get('TTS_MODEL', 'gemini-3.8-flash-tts')
SR = 24000
STYLE = 'Read this like an energetic short-form car explainer: lively and punchy at a natural conversational pace, with a short beat between sentences: '


def speak(text, voice='Puck'):
    body = {'contents': [{'parts': [{'text': STYLE + text}]}],
            'generationConfig': {'responseModalities': ['AUDIO'],
                                 'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice}}}}}
    req = urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent',
                                 json.dumps(body).encode(), {'Content-Type': 'application/json', 'x-goog-api-key': 'dummy'})
    r = json.load(urllib.request.urlopen(req, timeout=180))
    pcm = base64.b64decode(r['candidates'][0]['content']['parts'][0]['inlineData']['data'])
    return np.frombuffer(pcm, '<i2').astype(np.float32) / 32768


def _ff(y, af):
    p = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-', '-af', af,
                        '-ar', str(SR), '-f', 'f32le', '-'], input=y.astype('<f4').tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, '<f4')


def trim(y, db=-45):
    a = np.abs(y); th = 10 ** (db / 20); idx = np.where(a > th)[0]
    return y[max(0, idx[0] - int(0.05 * SR)): idx[-1] + int(0.12 * SR)]


def main():
    args = sys.argv[1:]; voice, gap = 'Puck', 2.0
    if '--voice' in args: i = args.index('--voice'); voice = args[i + 1]; del args[i:i + 2]
    if '--gap' in args: i = args.index('--gap'); gap = float(args[i + 1]); del args[i:i + 2]
    out, blocks = args[0], args[1:]
    parts = []
    for b in blocks:
        y = trim(_ff(speak(b, voice), 'loudnorm=I=-16:TP=-1.5:LRA=11'))
        print(f'{len(y) / SR:.2f}s  {b[:40]}', flush=True); parts.append(y)
    sil = np.zeros(int(round(gap * SR)), np.float32)
    full = np.concatenate([p if i == 0 else np.concatenate([sil, p]) for i, p in enumerate(parts)])
    import wave
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(full, -1, 1) * 32767).astype('<i2').tobytes())


if __name__ == '__main__':
    main()
