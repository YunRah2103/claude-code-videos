"""Tighten and align the voiceover (OpenAI.fm 'cedar' TTS, supplied with the brief).

voiceover_src.mp3 is the supplied read; vo.tighten() shortens its pauses into voiceover.mp3, which is aligned
again so words.json matches the audio that ships.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = ("At the Cybertruck reveal in 2019, the chief designer threw a steel ball at the truck. The driver's window shattered. Then the rear window broke too. Elon Musk's response: We'll fix it in post.")
SAY = {'Cybertruck': 'cyber truck', '2019': 'two thousand nineteen', "Musk's": 'musks'}
EXTRA = {'elon': 'IY L AA N', 'musks': 'M AH S K S'}
TARGET = 14.0
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'), target=TARGET, max_tempo=1.12, sent=0.5, comma=0.3, inner=0.3)
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
