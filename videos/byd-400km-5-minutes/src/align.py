"""Align this episode's voiceover clip (split from the shared OpenAI.fm 'cedar' blocks by shared/vo_split.py).

out/byd-400km-5-minutes/voiceover.wav is clip 1 of out/voiceover/full_voiceover.wav, used untouched; words.json is its forced alignment.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = "BYD says its new megawatt charger can add about 400 kilometres in five minutes. That's 1,000 kilowatts, twice the peak power of Tesla's latest Supercharger, according to BYD. Claimed, of course. But the race to charge faster is on. Follow for the next one."
SAY = {'BYD': 'b y d', '400': 'four hundred', "That's": "that's", '1,000': 'one thousand', "Tesla's": 'teslas', 'Supercharger': 'super charger', 'megawatt': 'mega watt', 'kilometres': 'kilometers'}
EXTRA = {'teslas': 'T EH S L AH Z'}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'byd-400km-5-minutes', 'voiceover.wav')
align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
