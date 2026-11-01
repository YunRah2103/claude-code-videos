"""Align this episode's voiceover (OpenAI.fm 'cedar' TTS, v2 read with a hook and a closing question).

out/<ep>/voiceover_src.wav is clip 6 of out/voiceover2/full_voiceover.wav (blocks joined with 2 s of silence, split at
the silence after each episode). It is used as is.
words.json is aligned to the audio that ships (out/<ep>/voiceover.wav)."""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = "How long does it take to go to 400 km/h and stop again? Koenigsegg's Jesko Absolut was reportedly timed at 27.83 seconds, from 0 to 400 km/h and back to zero."
SAY = {"Koenigsegg's": 'koenigseggs', '27.83': 'twenty seven point eight three', '0': 'zero', '400': 'four hundred', 'km/h': 'kilometers per hour'}
EXTRA = {'koenigseggs': 'K OW N IH G S EH G Z', 'jesko': 'Y EH S K OW'}
TARGET = None
OUT = os.path.join(HERE, '..', '..', '..', 'out', 'jesko-0-400-0')
J = lambda f: os.path.join(OUT, f)
if TARGET:
    src = align(SCRIPT, J('voiceover_src.wav'), os.path.join(HERE, 'words_src.json'), say=SAY, extra=EXTRA)
    tighten(J('voiceover_src.wav'), src, J('voiceover_tight.mp3'), target=TARGET, max_tempo=1.12, sent=0.4, comma=0.25, inner=0.25)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', J('voiceover_tight.mp3'), '-ar', '24000', '-ac', '1', J('voiceover.wav')], check=True)
else:
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', J('voiceover_src.wav'), '-c:a', 'pcm_s16le', J('voiceover.wav')], check=True)
align(SCRIPT, J('voiceover.wav'), os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
