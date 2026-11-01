"""Align this episode's voiceover (OpenAI.fm 'cedar' TTS, v2 read with a hook and a closing question).

out/<ep>/voiceover_src.wav is clip 2 of out/voiceover2/full_voiceover.wav (blocks joined with 2 s of silence, split at
the silence after each episode). It is used as is.
words.json is aligned to the audio that ships (out/<ep>/voiceover.wav)."""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = "Where would you put your speedometer if you could put it anywhere? Bugatti's Tourbillon makes 1,800 horsepower, from a V16 and three electric motors. Its gauges sit inside the steering wheel, so they stay visible as the wheel turns. Would you want your dials in the wheel?"
SAY = {"Bugatti's": 'bugattis', '1,800': 'one thousand eight hundred', 'V16': 'v sixteen'}
EXTRA = {'bugattis': 'B UW G AA T IY Z', 'tourbillon': 'T UH R B IY Y AO N'}
TARGET = None
OUT = os.path.join(HERE, '..', '..', '..', 'out', 'tourbillon-wheel-gauges')
J = lambda f: os.path.join(OUT, f)
if TARGET:
    src = align(SCRIPT, J('voiceover_src.wav'), os.path.join(HERE, 'words_src.json'), say=SAY, extra=EXTRA)
    tighten(J('voiceover_src.wav'), src, J('voiceover_tight.mp3'), target=TARGET, max_tempo=1.12, sent=0.4, comma=0.25, inner=0.25)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', J('voiceover_tight.mp3'), '-ar', '24000', '-ac', '1', J('voiceover.wav')], check=True)
else:
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', J('voiceover_src.wav'), '-c:a', 'pcm_s16le', J('voiceover.wav')], check=True)
align(SCRIPT, J('voiceover.wav'), os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
