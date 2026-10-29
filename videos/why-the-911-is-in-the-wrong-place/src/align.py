"""Tighten and align the voiceover (OpenAI.fm 'cedar' TTS, supplied with the brief).

voiceover_src.mp3 is the supplied read; vo.tighten() shortens its pauses into voiceover.mp3, which is aligned
again so words.json matches the audio that ships.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = ("Most cars keep the engine in the front. Porsche put the 911's engine behind the rear axle in 1963. It puts weight over the driven wheels, which helps grip, especially in winter. Porsche's chief designer said changing it would mean it's no longer a 911. Eight generations later, it's still there. Follow for the next one.")
SAY = {"911's": 'nine elevens', '911': 'nine eleven', '1963': 'nineteen sixty three', "Porsche's": 'porsches'}
EXTRA = {}
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'))
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
