"""Tighten and align the voiceover (OpenAI.fm 'cedar' TTS, supplied with the brief).

voiceover_src.mp3 is the supplied read; vo.tighten() shortens its pauses into voiceover.mp3, which is aligned
again so words.json matches the audio that ships.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = ("Cadillac put tailfins on its cars in 1948. Designers reportedly took the idea from fighter planes, including the twin tail of the Lockheed P-38. Through the 1950s, the fins grew bigger and sharper, just like the jets of the time. Soon, Buick, Ford, Mercedes-Benz and Volvo all had them too. Earl reportedly said the fins almost started a war inside GM. Why did cars grow fins? Follow for the next one.")
SAY = {'1948': 'nineteen forty eight', 'P-38': 'p thirty eight', '1950s': 'nineteen fifties', 'Mercedes-Benz': 'mercedes benz', 'GM': 'g m'}
EXTRA = {'tailfins': 'T EY L F IH N Z'}
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'), max_tempo=1.25, sent=0.24, comma=0.15, inner=0.18)
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
