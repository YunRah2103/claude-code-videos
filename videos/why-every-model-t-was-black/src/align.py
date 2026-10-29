"""Tighten and align the voiceover (Gemini TTS, voice Charon: the supplied cedar file stopped after 'cheap, tough').

voiceover_src.mp3 is the supplied read; vo.tighten() shortens its pauses into voiceover.mp3, which is aligned
again so words.json matches the audio that ships.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = ("Henry Ford reportedly said any customer could have any colour they wanted. As long as it was black. From about 1914 to 1925, black was the only option. It was cheap, tough, and better at resisting moisture. A popular story says it dried faster. The records don't back that up. Follow for the next one.")
SAY = {'colour': 'color', '1914': 'nineteen fourteen', '1925': 'nineteen twenty five'}
EXTRA = {}
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'))
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
