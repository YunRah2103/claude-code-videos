"""One two-speaker Gemini TTS call (Buyer=Fenrir, Salesman=Orus) -> 24 kHz mono WAV. No retries: stop on any HTTP error.
Usage: python tts.py VIDEO_DIR OUT.wav"""
import base64, json, os, subprocess, sys, wave, importlib.util
spec = importlib.util.spec_from_file_location('script', os.path.join(sys.argv[1], 'src', 'script.py'))
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"
prompt = S.DIRECTION + "\n".join(f"{S.VOICES[s][0]}: {t}" for s, t, _ in S.LINES) + "\n"
cfg = [{"speaker": n, "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": v}}} for n, v in S.VOICES.values()]
body = {"contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["AUDIO"],
                             "speechConfig": {"multiSpeakerVoiceConfig": {"speakerVoiceConfigs": cfg}}}}
# the network proxy injects the real key; the header value is a placeholder
r = subprocess.run(["curl", "-sS", "-m", "240", "-w", "\n%{http_code}", "-X", "POST", URL, "-H", "Content-Type: application/json",
                    "-H", "x-goog-api-key: placeholder", "-d", json.dumps(body)], capture_output=True, text=True)
out, code = r.stdout.rsplit("\n", 1)
if code != "200": sys.exit(f"HTTP {code}: {out[:300]}")
data = json.loads(out)["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(base64.b64decode(data))
print("ok", sys.argv[2])
