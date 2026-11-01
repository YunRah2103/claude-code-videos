"""Align this episode's voiceover (OpenAI.fm 'cedar' TTS, v2 read with a hook and a closing question).

out/<ep>/voiceover_src.wav is clip 3 of out/voiceover2/full_voiceover.wav (blocks joined with 2 s of silence, split at
the silence after each episode). vo.tighten() trims its long pauses (and a gentle atempo, at most 1.15x) towards TARGET s.
words.json is aligned to the audio that ships (out/<ep>/voiceover.wav)."""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = "You can fill this car up in 5 minutes. So why can't you find anywhere to do it? Toyota's Mirai fills up with hydrogen in about 5 minutes. Toyota claims it can drive up to 402 miles. But in 2023, there were only 59 hydrogen stations in the US, mostly in California. Would you drive one if your nearest station was a long way off?"
SAY = {'5': 'five', '402': 'four hundred two', '2023': 'twenty twenty three', '59': 'fifty nine', 'US': 'u. s.'}
EXTRA = {'mirai': 'M IH R AY'}
TARGET = 15.4
OUT = os.path.join(HERE, '..', '..', '..', 'out', 'mirai-5-minutes')
J = lambda f: os.path.join(OUT, f)
if TARGET:
    src = align(SCRIPT, J('voiceover_src.wav'), os.path.join(HERE, 'words_src.json'), say=SAY, extra=EXTRA)
    tighten(J('voiceover_src.wav'), src, J('voiceover_tight.mp3'), target=TARGET, max_tempo=1.15, sent=0.32, comma=0.2, inner=0.22)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', J('voiceover_tight.mp3'), '-ar', '24000', '-ac', '1', J('voiceover.wav')], check=True)
else:
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', J('voiceover_src.wav'), '-c:a', 'pcm_s16le', J('voiceover.wav')], check=True)
align(SCRIPT, J('voiceover.wav'), os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
