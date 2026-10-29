"""Tighten and align the voiceover (OpenAI.fm 'cedar' TTS supplied with the brief; its missing closing line is the same voice's 'Follow for the next one' from why-the-911).

voiceover_src.mp3 is the supplied read; vo.tighten() shortens its pauses into voiceover.mp3, which is aligned
again so words.json matches the audio that ships.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = ("Everyone said the rotary engine couldn't win Le Mans. In 1991, Mazda proved them wrong. Their 787B started 23rd on the grid, with four rotors and about 700 horsepower. On June 23, Johnny Herbert crossed the line first. The first Japanese manufacturer to win overall at Le Mans. Follow for the next one.")
SAY = {'1991': 'nineteen ninety one', '787B': 'seven eighty seven b', '23rd': 'twenty third', '700': 'seven hundred', '23': 'twenty third'}
EXTRA = {}
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'))
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
