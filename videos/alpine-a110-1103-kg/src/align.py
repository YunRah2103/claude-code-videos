"""Align this episode's voiceover clip (split from the shared OpenAI.fm 'cedar' blocks by shared/vo_split.py).

out/alpine-a110-1103-kg/voiceover.wav is clip 6 of out/voiceover/full_voiceover.wav, used untouched; words.json is its forced alignment.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = "The Alpine A110 weighs 1,103 kilograms. It has an aluminium body, and its engine sits behind the seats. It makes 249 horsepower, and in 2020, it won Britain's Best Car."
SAY = {'A110': 'a one ten', '1,103': 'one thousand one hundred three', '249': 'two hundred forty nine', '2020': 'twenty twenty', "Britain's": 'britains', 'aluminium': 'aluminum'}
EXTRA = {}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'alpine-a110-1103-kg', 'voiceover.wav')
align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
