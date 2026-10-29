"""Tighten and align the voiceover (OpenAI.fm 'cedar' TTS, supplied with the brief).

voiceover_src.mp3 is the supplied read; vo.tighten() shortens its pauses into voiceover.mp3, which is aligned
again so words.json matches the audio that ships.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = ("In 1963, Ford tried to buy Ferrari. The talks lasted 22 days, and the offer was reportedly huge. Then Enzo Ferrari walked away. So Ford built its own race car, the GT40, and took on Ferrari at Le Mans. By 1966, Ford was winning. Follow for the next one.")
SAY = {'1963': 'nineteen sixty three', '22': 'twenty two', 'GT40': 'g t forty', '1966': 'nineteen sixty six'}
EXTRA = {}
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'), max_tempo=1.25, sent=0.24, comma=0.15, inner=0.18)
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
