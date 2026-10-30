"""Align this episode's voiceover clip (split from the shared OpenAI.fm 'cedar' blocks by shared/vo_split.py).

out/emeya-905-horsepower/voiceover.wav is clip 5 of out/voiceover/full_voiceover.wav, used untouched; words.json is its forced alignment.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = 'The Lotus Emeya has up to 905 horsepower. Lotus claims it goes from 0 to 60 miles an hour in under 2.8 seconds. It also says the car adds 93 miles of range in five minutes on a 350 kilowatt charger. Follow for the next one.'
SAY = {'60': 'sixty', '905': 'nine hundred five', '0': 'zero', '2.8': 'two point eight', '93': 'ninety three', '350': 'three hundred fifty', 'Emeya': 'emaya'}
EXTRA = {'emaya': 'EH M EY AH'}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'emeya-905-horsepower', 'voiceover.wav')
align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
