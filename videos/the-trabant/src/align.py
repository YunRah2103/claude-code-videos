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
SCRIPT = ("The Trabant was built in East Germany, where steel was in short supply. So its body was made from a plastic-like material called Duroplast. It's reportedly made from cotton waste and resin. The early engine was a tiny two-stroke, just 500cc and 18 horsepower. Millions were built, and it became a symbol of an entire country.")
SAY = {'plastic-like': 'plastic like', 'two-stroke': 'two stroke', '500cc': 'five hundred c c', '18': 'eighteen'}
EXTRA = {'trabant': 'T R AH B AE N T', 'duroplast': 'D UH R OW P L AE S T'}
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'), max_tempo=1.25, sent=0.24, comma=0.15, inner=0.18)
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
