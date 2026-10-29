"""Tighten and align the voiceover (OpenAI.fm 'cedar' TTS, supplied with the brief).

voiceover_src.mp3 is the supplied read; vo.tighten() shortens its pauses into voiceover.mp3, which is aligned
again so words.json matches the audio that ships.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = ("Rolls-Royce has put the Spirit of Ecstasy on its bonnets since 1911. The sculptor was Charles Sykes. Rolls-Royce says the model was Eleanor Thornton. Thornton worked for the company's managing director, and she died in 1915 when a ship was torpedoed off Crete. Every time you see that figure, you're looking at a story. Follow for the next one.")
SAY = {'Rolls-Royce': 'rolls royce', '1911': 'nineteen eleven', '1915': 'nineteen fifteen'}
EXTRA = {'bonnets': 'B AA N AH T S'}
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'))
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
