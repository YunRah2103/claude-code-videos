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
SCRIPT = ("In January 1985, Sir Clive Sinclair launched the C5. It was a small electric vehicle, sold by mail order for £399. Riders felt exposed in traffic, and there was no protection from the weather. Sales slowed to a trickle, and production stopped in March, about three months after launch. Sometimes the idea is right, and the timing is wrong.")
SAY = {'1985': 'nineteen eighty five', 'C5': 'c five', '£399': 'three hundred ninety nine pounds'}
EXTRA = {}
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'), max_tempo=1.3, sent=0.24, comma=0.15, inner=0.18)
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
