"""Tighten and align the voiceover (OpenAI.fm 'cedar' TTS, supplied with the brief).

voiceover_src.mp3 is the supplied read; vo.tighten() shortens its pauses into voiceover.mp3, which is aligned
again so words.json matches the audio that ships.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = ('Mercedes built a road car using Formula One engineering. A 1.6-litre V6 hybrid, with over 1,000 horsepower in total. More than a thousand people applied to buy one. Only 275 buyers got the chance. Follow for the next one.')
SAY = {'1.6-litre': 'one point six liter', 'V6': 'v. six', '1,000': 'one thousand', '275': 'two hundred seventy five'}
EXTRA = {}
TARGET = 15.6
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'), target=TARGET, max_tempo=1.12, sent=0.62, comma=0.3, inner=0.3)
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
