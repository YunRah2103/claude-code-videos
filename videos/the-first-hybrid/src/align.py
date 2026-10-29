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
SCRIPT = ("In 1997, Toyota launched the Prius in Japan. It's known as the first mass-produced hybrid car. It used a petrol engine and two motors working together. By 1998, about 20,000 had been built in Japan alone. Almost every hybrid on the road today owes it something.")
SAY = {'1997': 'nineteen ninety seven', 'mass-produced': 'mass produced', '1998': 'nineteen ninety eight', '20,000': 'twenty thousand'}
EXTRA = {}
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'), max_tempo=1.15, sent=0.24, comma=0.15, inner=0.18)
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
