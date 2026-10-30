"""Pace and align this episode's voiceover clip (OpenAI.fm 'cedar' TTS, split from out/voiceover/full_voiceover.wav
by shared/split_vo.py into out/ford-gt-2016/voiceover.wav). The audio that ships is out/ford-gt-2016/vo_final.wav; words.json is
aligned on it, so captions follow the recorded words (no scaled or invented timings).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'shared'))
from align import align
from vo import tighten, pace
# The supplied read ends at "in 1966" with no outro; pace() appends the same voice's
# "Follow for the next one." from the lucid-749-miles clip so the script is complete.
import json
LUCID = os.path.join(ROOT, "videos", "lucid-749-miles", "src", "words_src.json")   # run lucid-749-miles/src/align.py first
fw = json.load(open(LUCID))[-5:]                                                       # "Follow for the next one." in the same voice
TAIL = (os.path.join(ROOT, "out", "lucid-749-miles", "voiceover.wav"), fw[0]["s"] - 0.06, fw[-1]["e"] + 0.2)
BODY = "In 2016, the Ford GT won its class at Le Mans. It was 50 years after Ford's first overall win there, in 1966."
SCRIPT = BODY + " Follow for the next one."
SAY = {'2016': 'twenty sixteen', 'GT': 'g. t.', '50': 'fifty', "Ford's": 'fords', '1966': 'nineteen sixty six'}
EXTRA = {'le': 'L AH', 'mans': 'M AA N Z'}
CLIP, OUT = os.path.join(ROOT, 'out', 'ford-gt-2016', 'voiceover.wav'), os.path.join(ROOT, 'out', 'ford-gt-2016', 'vo_final.wav')
src = align(BODY, CLIP, os.path.join(HERE, 'words_src.json'), say=SAY, extra=EXTRA)
pace(CLIP, src, OUT, add=0.6, lead=1.8, tail=TAIL)
align(SCRIPT, OUT, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
