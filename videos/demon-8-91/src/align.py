"""Pace and align this episode's voiceover clip (OpenAI.fm 'cedar' TTS, split from out/voiceover/full_voiceover.wav
by shared/split_vo.py into out/demon-8-91/voiceover.wav). The audio that ships is out/demon-8-91/vo_final.wav; words.json is
aligned on it, so captions follow the recorded words (no scaled or invented timings).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'shared'))
from align import align
from vo import tighten, pace
# The supplied read ends at "151 miles an hour" with no outro; pace() appends the same voice's
# "Follow for the next one." from the lucid-749-miles clip so the script is complete.
import json
LUCID = os.path.join(ROOT, "videos", "lucid-749-miles", "src", "words_src.json")   # run lucid-749-miles/src/align.py first
fw = json.load(open(LUCID))[-5:]                                                       # "Follow for the next one." in the same voice
TAIL = (os.path.join(ROOT, "out", "lucid-749-miles", "voiceover.wav"), fw[0]["s"] - 0.06, fw[-1]["e"] + 0.2)
BODY = ("The Dodge Challenger SRT Demon 170 makes 1,025 horsepower. Its quarter-mile time, certified by the NHRA, "
        "is 8.91 seconds. That's at 151 miles an hour.")
SCRIPT = BODY + " Follow for the next one."
SAY = {'SRT': 's. r. t.', '170': 'one seventy', '1,025': 'one thousand twenty five', 'quarter-mile': 'quarter mile',
       'NHRA': 'n. h. r. a.', '8.91': 'eight point nine one', '151': 'one hundred fifty one'}
EXTRA = {}
CLIP, OUT = os.path.join(ROOT, 'out', 'demon-8-91', 'voiceover.wav'), os.path.join(ROOT, 'out', 'demon-8-91', 'vo_final.wav')
src = align(BODY, CLIP, os.path.join(HERE, 'words_src.json'), say=SAY, extra=EXTRA)
pace(CLIP, src, OUT, add=0.3, lead=0.3, tail=TAIL)
align(SCRIPT, OUT, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
