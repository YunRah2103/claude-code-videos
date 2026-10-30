"""Tighten and align the voiceover (OpenAI.fm 'cedar' TTS, supplied with the brief).

voiceover_src.mp3 is the supplied read; vo.tighten() shortens its pauses into voiceover.mp3, which is aligned
again so words.json matches the audio that ships.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = ("Ten to eighty percent in about eighteen minutes. That's the Hyundai Ioniq 5, on an 800-volt system. But you need a 350 kilowatt charger to get that speed. Fast charging is only as fast as the charger. Follow for the next one.")
SAY = {'5': 'five', '800-volt': 'eight hundred volt', '350': 'three hundred fifty', 'Ioniq': 'ioniq'}
EXTRA = {'ioniq': 'AY AA N IH K'}
TARGET = 15.6
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'), target=TARGET, max_tempo=1.12, sent=0.5, comma=0.3, inner=0.3)
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
