"""Tighten and align the voiceover (OpenAI.fm 'cedar' TTS, supplied with the brief).

voiceover_src.mp3 is the supplied read; vo.tighten() shortens its pauses into voiceover.mp3, which is aligned
again so words.json matches the audio that ships.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = ("In 1981, Mercedes put a driver's airbag into production. More than 100 S-Class cars got it in the first two months. Before that, engineers ran 250 crash tests and over 2,500 sled tests. The idea was older. A German patent was filed back in 1951. It just needed sensors and gas that worked fast enough. Follow for the next one.")
SAY = {'1981': 'nineteen eighty one', '100': 'one hundred', 'S-Class': 's class', 'airbag': 'air bag', '250': 'two hundred fifty', '2,500': 'two thousand five hundred', '1951': 'nineteen fifty one'}
EXTRA = {}
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'), max_tempo=1.3, sent=0.24, comma=0.15, inner=0.18)
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
