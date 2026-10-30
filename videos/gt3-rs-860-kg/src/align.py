"""Align this episode's voiceover clip (split from the shared OpenAI.fm 'cedar' blocks by shared/vo_split.py).

out/gt3-rs-860-kg/voiceover.wav is clip 3 of out/voiceover/full_voiceover.wav, used untouched; words.json is its forced alignment.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = 'At 177 miles an hour, the Porsche 911 GT3 RS makes 860 kilograms of downforce. Its rear wing opens automatically above 62 miles an hour, at nearly full throttle. When it does, it cuts downforce by 30 percent.'
SAY = {'177': 'one hundred seventy seven', '911': 'nine eleven', 'GT3': 'g t three', 'RS': 'r s', '860': 'eight hundred sixty', '62': 'sixty two', '30': 'thirty'}
EXTRA = {'downforce': 'D AW N F AO R S'}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'gt3-rs-860-kg', 'voiceover.wav')
align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
