"""Align this episode's voiceover clip (split from the shared OpenAI.fm 'cedar' blocks by shared/vo_split.py).

out/gr-yaris-three-cylinder/voiceover.wav is clip 2 of out/voiceover/full_voiceover.wav, used untouched; words.json is its forced alignment.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = 'The Toyota GR Yaris has a 1.6-litre, three-cylinder turbo engine, making 257 horsepower. Its all-wheel drive sends 60 percent to the front by default. Switch to Sport, and 70 percent goes to the rear. Track mode splits it evenly. Follow for the next one.'
SAY = {'GR': 'g r', '1.6-litre': 'one point six liter', 'three-cylinder': 'three cylinder', '257': 'two hundred fifty seven', '60': 'sixty', '70': 'seventy', 'all-wheel': 'all wheel'}
EXTRA = {'yaris': 'Y AA R IH S'}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'gr-yaris-three-cylinder', 'voiceover.wav')
align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
