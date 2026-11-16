"""One Gemini TTS call, two speakers (Orus = salesman, Fenrir = buyer), same voices as tesla-locked.
Usage: python tts.py OUT.wav   (key is injected by the proxy; never printed). Stops on any HTTP error, incl. 429."""
import base64, json, subprocess, sys
from align import LINES

URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"
NAME = {"S": "Salesman", "B": "Buyer"}
DIRECTION = ("TTS the following showroom comedy skit, fast-paced with no pauses between lines. "
             "Salesman: completely flat, calm, bored, deadpan the whole time, never reacts. "
             "Buyer: starts outraged and loud, then baffled, then resigned and tired by the end. "
             "Speak every line below exactly as written, in order, starting with the Buyer's first line.\n\n")

if __name__ == '__main__':
    text = DIRECTION + "\n".join(f"{NAME[s]}: {t}" for s, t in LINES)
    body = {"contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"multiSpeakerVoiceConfig": {
                "speakerVoiceConfigs": [
                    {"speaker": "Salesman", "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Orus"}}},
                    {"speaker": "Buyer", "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Fenrir"}}}]}}}}
    r = subprocess.run(["curl", "-sS", "-m", "180", "-w", "\n%{http_code}", "-X", "POST", URL,
                        "-H", "Content-Type: application/json", "-H", "x-goog-api-key: proxy-injected",
                        "--data-binary", "@-"], input=json.dumps(body), capture_output=True, text=True)
    out, code = r.stdout.rsplit("\n", 1)
    if code != "200":
        sys.exit(f"HTTP {code}: {out[:300]}")
    pcm = base64.b64decode(json.loads(out)["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", "-", sys.argv[1]],
                   input=pcm, check=True)
    print("wrote", sys.argv[1], round(len(pcm) / 48000, 2), "s")
