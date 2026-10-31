"""Align the voiceover clip for this episode (OpenAI.fm 'cedar' TTS, three chunks supplied with the brief).

out/voiceover/full_voiceover.wav joins the three loudness-matched chunks with 2 s gaps; shared/vo_split.py cuts it
into one clip per episode, saved as out/ioniq-18-minutes/voiceover.wav (not committed). The audio is used as read: no
tightening or tempo change. words_v1.json keeps the previous read's timings, which render.py maps onto this one.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = ("Ten to eighty percent in about eighteen minutes. Sounds great. That's the Hyundai Ioniq 5, on an 800-volt system. But you need a 350 kilowatt charger to get that speed. Fast charging is only as fast as the charger. What's the slowest charger you've ever waited at?")
SAY = {'5': 'five', '800-volt': 'eight hundred volt', '350': 'three hundred fifty', 'Ioniq': 'ioniq', "What's": "what's"}
EXTRA = {'ioniq': 'AY AA N IH K'}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'ioniq-18-minutes', 'voiceover.wav')
if __name__ == '__main__':
    align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
