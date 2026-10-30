"""Tighten and align the voiceover (OpenAI.fm 'cedar' TTS, supplied with the brief).

voiceover_src.mp3 is the supplied read; vo.tighten() shortens its pauses into voiceover.mp3, which is aligned
again so words.json matches the audio that ships.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = ('Bugatti says two people spend six days building one of its W16 engines. It has 3,712 parts. And it watches every spark plug, checking for problems. If it spots one, it can shut down a cylinder or pull back the boost. Precision you can count. Follow for the next one.')
SAY = {'W16': 'double u sixteen', '3,712': 'three thousand seven hundred and twelve'}
EXTRA = {}
TARGET = 16.4
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'), target=TARGET, max_tempo=1.12, sent=0.26, comma=0.16, inner=0.18)
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
