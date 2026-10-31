"""Align the voiceover clip for this episode (OpenAI.fm 'cedar' TTS, three chunks supplied with the brief).

out/voiceover/full_voiceover.wav joins the three loudness-matched chunks with 2 s gaps; shared/vo_split.py cuts it
into one clip per episode, saved as out/bugatti-3712-parts/voiceover.wav (not committed). The audio is used as read: no
tightening or tempo change. words_v1.json keeps the previous read's timings, which render.py maps onto this one.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = ('How many parts go into one engine? Bugatti says two people spend six days building one of its W16 engines. It has 3,712 parts. And it watches every spark plug, checking for problems. If it spots one, it can shut down a cylinder or pull back the boost. Would you trust a car that watches every spark plug?')
SAY = {'W16': 'double u sixteen', '3,712': 'three thousand seven hundred twelve'}
EXTRA = {}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'bugatti-3712-parts', 'voiceover.wav')
if __name__ == '__main__':
    align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
