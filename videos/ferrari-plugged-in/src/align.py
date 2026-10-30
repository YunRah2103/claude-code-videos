"""Pace and align this episode's voiceover clip (OpenAI.fm 'cedar' TTS, split from out/voiceover/full_voiceover.wav
by shared/split_vo.py into out/ferrari-plugged-in/voiceover.wav). The audio that ships is out/ferrari-plugged-in/vo_final.wav; words.json is
aligned on it, so captions follow the recorded words (no scaled or invented timings).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'shared'))
from align import align
from vo import tighten, pace
SCRIPT = ("Ferrari's first plug-in hybrid road car is the SF90 Stradale. It makes about 1,000 horsepower, and it can be "
          "plugged in to charge. Follow for the next one.")
SAY = {"Ferrari's": 'ferraris', 'plug-in': 'plug in', 'SF90': 's. f. ninety', '1,000': 'one thousand'}
EXTRA = {'ferraris': 'F ER AA R IY Z', 'stradale': 'S T R AH D AA L EY'}
CLIP, OUT = os.path.join(ROOT, 'out', 'ferrari-plugged-in', 'voiceover.wav'), os.path.join(ROOT, 'out', 'ferrari-plugged-in', 'vo_final.wav')
src = align(SCRIPT, CLIP, os.path.join(HERE, 'words_src.json'), say=SAY, extra=EXTRA)
pace(CLIP, src, OUT, add=0.6, lead=1.8)   # a 9.6 s read: a silent hook beat first, room for a visual beat per sentence
align(SCRIPT, OUT, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
