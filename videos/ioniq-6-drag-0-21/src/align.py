"""Align this episode's voiceover clip (split from the shared OpenAI.fm 'cedar' blocks by shared/vo_split.py).

out/ioniq-6-drag-0-21/voiceover.wav is clip 4 of out/voiceover/full_voiceover.wav, used untouched; words.json is its forced alignment.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = 'Hyundai says the Ioniq 6 has a drag coefficient of 0.21, the lowest it has ever achieved. Less drag means less energy spent pushing through the air. Follow for the next one.'
SAY = {'6': 'six', '0.21': 'zero point two one', 'Ioniq': 'ionic'}
EXTRA = {}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'ioniq-6-drag-0-21', 'voiceover.wav')
align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
