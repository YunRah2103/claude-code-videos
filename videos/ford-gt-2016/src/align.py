"""Pace and align this episode's voiceover clip (OpenAI.fm 'cedar' TTS, v2 read with an opening and a closing
question, split from out/voiceover/full_voiceover.wav by shared/split_vo.py into out/ford-gt-2016/voiceover.wav). The audio
that ships is out/ford-gt-2016/vo_final.wav; words.json is aligned on it, so captions follow the recorded words.
words_v1.json is the first read's alignment: render.py maps its animation timeline onto the new words.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'shared'))
from align import align
from vo import tighten, pace
CLIP, OUT = os.path.join(ROOT, 'out', 'ford-gt-2016', 'voiceover.wav'), os.path.join(ROOT, 'out', 'ford-gt-2016', 'vo_final.wav')
SCRIPT = ("50 years after Ford's first Le Mans win, it came back and won again. In 2016, the Ford GT won its class at "
          "Le Mans. It was 50 years after Ford's first overall win there, in 1966. Would you call that a comeback or a "
          "coincidence?")
SAY = {'2016': 'twenty sixteen', 'GT': 'g. t.', '50': 'fifty', "Ford's": 'fords', '1966': 'nineteen sixty six'}
EXTRA = {'le': 'L AH', 'mans': 'M AA N Z'}
src = align(SCRIPT, CLIP, os.path.join(HERE, 'words_src.json'), say=SAY, extra=EXTRA)
pace(CLIP, src, OUT, lead=0.2)
align(SCRIPT, OUT, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
