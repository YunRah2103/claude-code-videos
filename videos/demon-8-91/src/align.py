"""Pace and align this episode's voiceover clip (OpenAI.fm 'cedar' TTS, v2 read with an opening and a closing
question, split from out/voiceover/full_voiceover.wav by shared/split_vo.py into out/demon-8-91/voiceover.wav). The audio
that ships is out/demon-8-91/vo_final.wav; words.json is aligned on it, so captions follow the recorded words.
words_v1.json is the first read's alignment: render.py maps its animation timeline onto the new words.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'shared'))
from align import align
from vo import tighten, pace
CLIP, OUT = os.path.join(ROOT, 'out', 'demon-8-91', 'voiceover.wav'), os.path.join(ROOT, 'out', 'demon-8-91', 'vo_final.wav')
SCRIPT = ("What does 1,025 horsepower look like on a drag strip? The Dodge Challenger SRT Demon 170 makes it, and it's "
          "certified by the NHRA. Its quarter-mile time is 8.91 seconds. That's at 151 miles an hour. Would you be "
          "ready for that launch?")
SAY = {'SRT': 's. r. t.', '170': 'one seventy', '1,025': 'one thousand twenty five', 'quarter-mile': 'quarter mile',
       'NHRA': 'n. h. r. a.', '8.91': 'eight point nine one', '151': 'one hundred fifty one'}
src = align(SCRIPT, CLIP, os.path.join(HERE, 'words_src.json'), say=SAY)
pace(CLIP, src, OUT, lead=0.2)
align(SCRIPT, OUT, os.path.join(HERE, 'words.json'), say=SAY)
