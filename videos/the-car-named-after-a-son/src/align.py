"""Tighten and align the voiceover (OpenAI.fm 'cedar' TTS, supplied with the brief).
The supplied read ends before the scripted "Follow for the next one."; the end card shows that line instead.

voiceover_src.mp3 is the supplied read; vo.tighten() shortens its pauses into voiceover.mp3, which is aligned
again so words.json matches the audio that ships.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = ("The Ferrari Dino is named after Enzo Ferrari's son. Alfredo \"Dino\" Ferrari worked on an early V6 engine design. He died in 1956, at just 24, from Duchenne muscular dystrophy. The Dino car came out in 1968, carrying his name. Every time you see that badge, there's a story behind it.")
SAY = {'1956': 'nineteen fifty six', '24': 'twenty four', '1968': 'nineteen sixty eight', 'V6': 'v six', '"Dino"': 'dino'}
EXTRA = {"ferrari's": 'F ER AA R IY Z'}
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'), max_tempo=1.2)
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
