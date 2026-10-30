"""Tighten and align the voiceover (OpenAI.fm 'cedar' TTS, supplied with the brief).

voiceover_src.mp3 is the supplied read; vo.tighten() shortens its pauses into voiceover.mp3, which is aligned
again so words.json matches the audio that ships.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = ("Tesla's Model S Plaid was claimed to hit 60 miles an hour in 1.99 seconds. It launched in June 2021, with three motors. Over 1,000 horsepower, according to the company. Faster than you can blink.")
SAY = {'60': 'sixty', '1.99': 'one point nine nine', '2021': 'twenty twenty one', '1,000': 'one thousand', "Tesla's": 'teslas', 'S': 's.'}
EXTRA = {'teslas': 'T EH S L AH Z'}
TARGET = 15.4
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'), target=TARGET, max_tempo=1.12, sent=0.5, comma=0.3, inner=0.3)
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
