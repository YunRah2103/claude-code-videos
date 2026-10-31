"""Align the voiceover clip for this episode (OpenAI.fm 'cedar' TTS, three chunks supplied with the brief).

out/voiceover/full_voiceover.wav joins the three loudness-matched chunks with 2 s gaps; shared/vo_split.py cuts it
into one clip per episode, saved as out/project-one-275/voiceover.wav (not committed). The audio is used as read: no
tightening or tempo change. words_v1.json keeps the previous read's timings, which render.py maps onto this one.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = ("More than a thousand people applied for one car. Only 275 got the chance to buy one. It's Mercedes' Project One, a road car built using Formula One engineering. A 1.6-litre V6 hybrid, with over 1,000 horsepower in total. Would you have applied?")
SAY = {'1.6-litre': 'one point six liter', 'V6': 'v. six', '1,000': 'one thousand', '275': 'two hundred seventy five', "Mercedes'": 'mercedes'}
EXTRA = {}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'project-one-275', 'voiceover.wav')
if __name__ == '__main__':
    align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
