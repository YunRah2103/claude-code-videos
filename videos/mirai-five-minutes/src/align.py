"""Voiceover for the Mirai episode: the supplied OpenAI.fm 'cedar' read of SCRIPT.

1. out/mirai-five-minutes/voiceover_src.wav = the supplied mp3 with its 0.62 s lead-in silence trimmed (hook lands sooner)
2. words_src.json = forced alignment of that file
3. out/mirai-five-minutes/voiceover.wav = shared/vo.tighten() of it (pauses capped, gentle atempo)
4. words.json = forced alignment of the tightened file (timings come from the audio that ships, never from scaling)
Usage: python align.py <supplied.mp3>
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten

SCRIPT = ("You can fill this car up in five minutes. So why can't you find anywhere to do it? "
          "Toyota's Mirai runs on hydrogen, and it refuels in about five minutes. "
          "But in 2023, there were only 59 hydrogen stations in the whole US. Most of them in California. "
          "Would you drive one, if your nearest station was a long way off?")
SAY = {"Toyota's": 'toyotas', '2023': 'twenty twenty three', '59': 'fifty nine', 'US': 'u s'}
EXTRA = {'toyotas': 'T OY OW T AH Z', 'mirai': 'M IH R AY', 'refuels': 'R IY F Y UW AH L Z'}
OUT = os.path.join(HERE, '..', '..', '..', 'out', 'mirai-five-minutes')
SRC, VO = os.path.join(OUT, 'voiceover_src.wav'), os.path.join(OUT, 'voiceover.wav')

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '0.62', '-i', sys.argv[1], '-ac', '1', '-c:a', 'pcm_s16le', SRC], check=True)
    words = align(SCRIPT, SRC, os.path.join(HERE, 'words_src.json'), say=SAY, extra=EXTRA)
    tighten(SRC, words, VO, target=15.9)
    align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
