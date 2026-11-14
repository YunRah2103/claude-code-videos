"""Documentary narration: the whole script as ONE clip (natural pacing), then mastered.

  python3 tts.py OUT_DIR gemini VOICE      -> OUT_DIR/vo_<VOICE>.wav  (Gemini TTS, director's-notes prompt)
  python3 tts.py OUT_DIR openai VOICE      -> OUT_DIR/vo_openai_<VOICE>.wav (gpt-4o-mini-tts, comparison)
  python3 tts.py master IN.wav OUT.wav     -> EQ + compression + loudness (narration polish)
The proxy injects API keys; header values here are placeholders.
"""
import base64, json, subprocess, sys, time, wave
from pathlib import Path

import timing

# what the narrator reads (spoken forms); alignment still uses timing.SCRIPT word-for-word
SPOKEN = timing.SCRIPT.replace("F1's", "F-one's").replace("V12", "V-twelve")

GEMINI_PROMPT = """# AUDIO PROFILE
A seasoned documentary narrator: deep, resonant chest voice, warm and completely self-assured.

## THE SCENE
A quiet recording booth. He is narrating a premium automotive documentary, close to the microphone.

### DIRECTOR'S NOTES
Style: grounded, intriguing and authoritative, like a high-end streaming documentary. Natural human phrasing,
never sing-song and never monotone. Lean into the key words: "real gold", "not for show", "huge heat",
"carbon fibre", "reflects", "sixteen grams". Open with quiet curiosity; land the final question with a hint of a smile.
Pace: steady and confident, slightly brisk, with short breaths between sentences.

#### TRANSCRIPT
"""

OPENAI_INSTR = ("Voice: deep, resonant, confident male documentary narrator. Tone: grounded and intriguing, "
                "like a premium automotive documentary. Natural human phrasing with subtle emphasis on key words "
                "(real gold, huge heat, carbon fibre, reflects, sixteen grams). Steady, slightly brisk pace; short pauses "
                "between sentences. End the question with a warm, conversational lift.")

def curl(url, headers, body):
    r = subprocess.run(["curl", "-sS", "-m", "180", "-X", "POST", url, *sum((["-H", h] for h in headers), []),
                        "-d", json.dumps(body)], capture_output=True, check=True)
    return r.stdout

def gemini(voice, dst):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"
    body = {"contents": [{"parts": [{"text": GEMINI_PROMPT + SPOKEN}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    for attempt in range(4):
        d = json.loads(curl(url, ["Content-Type: application/json", "x-goog-api-key: placeholder"], body))
        if "candidates" in d:
            pcm = base64.b64decode(d["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
            with wave.open(str(dst), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
            return
        print("gemini retry:", d.get("error", {}).get("message", "")[:160], file=sys.stderr); time.sleep(25 * (attempt + 1))
    raise SystemExit("gemini failed")

def openai(voice, dst):
    raw = curl("https://api.openai.com/v1/audio/speech", ["Content-Type: application/json", "Authorization: Bearer placeholder"],
               {"model": "gpt-4o-mini-tts", "voice": voice, "input": SPOKEN, "instructions": OPENAI_INSTR,
                "response_format": "wav"})
    if raw[:4] != b"RIFF":
        raise SystemExit("openai failed: " + raw[:300].decode(errors="replace"))
    dst.write_bytes(raw)

def master(src, dst):
    """Narration polish: trim, rumble cut, chest + presence EQ, gentle compression, -16 LUFS."""
    chain = ("highpass=f=70,equalizer=f=140:t=q:w=1.0:g=3,equalizer=f=320:t=q:w=1.2:g=-2.5,"
             "equalizer=f=3200:t=q:w=1.4:g=2.5,equalizer=f=7500:t=q:w=2:g=-1.5,"
             "acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=3,"
             "loudnorm=I=-16:TP=-1.5:LRA=7")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", chain, "-ar", "48000", "-ac", "1", str(dst)], check=True)

if __name__ == "__main__":
    if sys.argv[1] == "master":
        master(sys.argv[2], sys.argv[3]); sys.exit(0)
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    engine, voice = sys.argv[2], sys.argv[3]
    dst = out / (f"vo_{voice}.wav" if engine == "gemini" else f"vo_openai_{voice}.wav")
    (gemini if engine == "gemini" else openai)(voice, dst)
    with wave.open(str(dst)) as w: print(engine, voice, round(w.getnframes() / w.getframerate(), 2), "s ->", dst)
