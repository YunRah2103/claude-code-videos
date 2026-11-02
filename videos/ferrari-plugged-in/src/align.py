"""Pace and align this episode's voiceover clip (OpenAI.fm 'cedar' TTS, v2 read with an opening and a closing
question, split from out/voiceover/full_voiceover.wav by shared/split_vo.py into out/ferrari-plugged-in/voiceover.wav). The audio
that ships is out/ferrari-plugged-in/vo_final.wav; words.json is aligned on it, so captions follow the recorded words.
words_v1.json is the first read's alignment: render.py maps its animation timeline onto the new words.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'shared'))
from align import align
from vo import tighten, pace
CLIP, OUT = os.path.join(ROOT, 'out', 'ferrari-plugged-in', 'voiceover.wav'), os.path.join(ROOT, 'out', 'ferrari-plugged-in', 'vo_final.wav')
SCRIPT = ("Ferrari has a car you can plug in. Its first plug-in hybrid road car is the SF90 Stradale. It makes about "
          "1,000 horsepower, and it can be plugged in to charge. So, is the future of the supercar a plug or a petrol engine?")
SAY = {'plug-in': 'plug in', 'SF90': 's. f. ninety', '1,000': 'one thousand', 'supercar': 'super car'}
EXTRA = {'stradale': 'S T R AH D AA L EY', 'petrol': 'P EH T R AH L'}
src = align(SCRIPT, CLIP, os.path.join(HERE, 'words_src.json'), say=SAY, extra=EXTRA)
pace(CLIP, src, OUT, lead=0.2)
align(SCRIPT, OUT, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
