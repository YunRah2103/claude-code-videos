"""Align this episode's voiceover (OpenAI.fm 'cedar' TTS, v2 read with a hook and a closing question).

out/<ep>/voiceover_src.wav is clip 5 of out/voiceover2/full_voiceover.wav (blocks joined with 2 s of silence, split at
the silence after each episode). vo.tighten() trims its long pauses (and a gentle atempo, at most 1.12x) towards TARGET s.
words.json is aligned to the audio that ships (out/<ep>/voiceover.wav)."""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = "How fast can a front-wheel-drive car lap the Nürburgring? Honda's Civic Type R set a 7 minutes 44.881 second lap in April 2023. It was reported as the fastest front-wheel-drive production car around the track. Would you bet against a front-wheel-drive car on a track?"
SAY = {'7': 'seven', '44.881': 'forty four point eight eight one', 'Nürburgring': 'nurburgring', '2023': 'twenty twenty three', 'front-wheel-drive': 'front wheel drive'}
EXTRA = {'nurburgring': 'N ER B ER G R IH NG'}
TARGET = 15.2
OUT = os.path.join(HERE, '..', '..', '..', 'out', 'civic-type-r-7-44')
J = lambda f: os.path.join(OUT, f)
if TARGET:
    src = align(SCRIPT, J('voiceover_src.wav'), os.path.join(HERE, 'words_src.json'), say=SAY, extra=EXTRA)
    tighten(J('voiceover_src.wav'), src, J('voiceover_tight.mp3'), target=TARGET, max_tempo=1.12, sent=0.4, comma=0.25, inner=0.25)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', J('voiceover_tight.mp3'), '-ar', '24000', '-ac', '1', J('voiceover.wav')], check=True)
else:
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', J('voiceover_src.wav'), '-c:a', 'pcm_s16le', J('voiceover.wav')], check=True)
align(SCRIPT, J('voiceover.wav'), os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
