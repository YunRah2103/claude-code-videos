"""Align this episode's voiceover (OpenAI.fm 'cedar' TTS, v2 read with a hook and a closing question).

out/<ep>/voiceover_src.wav is clip 1 of out/voiceover2/full_voiceover.wav (blocks joined with 2 s of silence, split at
the silence after each episode). vo.tighten() trims its long pauses (and a gentle atempo, at most 1.12x) towards TARGET s.
words.json is aligned to the audio that ships (out/<ep>/voiceover.wav)."""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = "What happens when you put four electric motors in one car? The Rimac Nevera makes 1,914 horsepower. Rimac claims it does the quarter mile in 8.58 seconds. That's at 167 miles an hour. Would you be brave enough to launch it?"
SAY = {'1,914': 'one thousand nine hundred fourteen', '8.58': 'eight point five eight', '167': 'one hundred sixty seven'}
EXTRA = {'rimac': 'R IY M AA T S', 'nevera': 'N EH V EH R AH'}
TARGET = 15.0
OUT = os.path.join(HERE, '..', '..', '..', 'out', 'rimac-nevera-1914')
J = lambda f: os.path.join(OUT, f)
if TARGET:
    src = align(SCRIPT, J('voiceover_src.wav'), os.path.join(HERE, 'words_src.json'), say=SAY, extra=EXTRA)
    tighten(J('voiceover_src.wav'), src, J('voiceover_tight.mp3'), target=TARGET, max_tempo=1.12, sent=0.4, comma=0.25, inner=0.25)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', J('voiceover_tight.mp3'), '-ar', '24000', '-ac', '1', J('voiceover.wav')], check=True)
else:
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', J('voiceover_src.wav'), '-c:a', 'pcm_s16le', J('voiceover.wav')], check=True)
align(SCRIPT, J('voiceover.wav'), os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
