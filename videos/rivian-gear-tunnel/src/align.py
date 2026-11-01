"""Align this episode's voiceover (OpenAI.fm 'cedar' TTS, v2 read with a hook and a closing question).

out/<ep>/voiceover_src.wav is clip 4 of out/voiceover2/full_voiceover.wav (blocks joined with 2 s of silence, split at
the silence after each episode). It is used as is, minus 1.0 s of leading join silence.
words.json is aligned to the audio that ships (out/<ep>/voiceover.wav)."""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = 'Where would you hide a gear tunnel in a pickup truck? The Rivian R1T has one, behind the rear seats. You reach it from inside the cabin, by folding down the armrest and sliding a door up. Would you ever find it without being told?'
SAY = {'R1T': 'r one t'}
EXTRA = {'rivian': 'R IH V IY AH N'}
TARGET = None
OUT = os.path.join(HERE, '..', '..', '..', 'out', 'rivian-gear-tunnel')
J = lambda f: os.path.join(OUT, f)
if TARGET:
    src = align(SCRIPT, J('voiceover_src.wav'), os.path.join(HERE, 'words_src.json'), say=SAY, extra=EXTRA)
    tighten(J('voiceover_src.wav'), src, J('voiceover_tight.mp3'), target=TARGET, max_tempo=1.12, sent=0.4, comma=0.25, inner=0.25)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', J('voiceover_tight.mp3'), '-ar', '24000', '-ac', '1', J('voiceover.wav')], check=True)
else:
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '1.0', '-i', J('voiceover_src.wav'), '-c:a', 'pcm_s16le', J('voiceover.wav')], check=True)   # drop 1 s of the join gap
align(SCRIPT, J('voiceover.wav'), os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
