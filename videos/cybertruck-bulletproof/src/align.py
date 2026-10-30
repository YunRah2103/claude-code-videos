"""Tighten and align the voiceover (OpenAI.fm 'cedar' TTS, supplied with the brief).

voiceover_src.mp3 is the supplied read; vo.tighten() shortens its pauses into voiceover.mp3, which is aligned
again so words.json matches the audio that ships.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = ("The Cybertruck's body is 3 millimetre stainless steel, the same alloy used on SpaceX's Starship. In independent tests, it resisted 9mm rounds. But rifle rounds got through the outer layer. And the windows offer no real bullet protection. So is it bulletproof? Not quite. Follow for the next one.")
SAY = {"Cybertruck's": 'cyber trucks', '3': 'three', 'millimetre': 'millimeter', "SpaceX's": 'space x\'s', 'Starship': 'star ship', '9mm': 'nine millimeter', 'bulletproof': 'bullet proof'}
EXTRA = {}
TARGET = 16.4
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'), target=TARGET, max_tempo=1.12, sent=0.26, comma=0.16, inner=0.18)
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
