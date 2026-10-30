"""Pace and align this episode's voiceover clip (OpenAI.fm 'cedar' TTS, split from out/voiceover/full_voiceover.wav
by shared/split_vo.py into out/lucid-749-miles/voiceover.wav). The audio that ships is out/lucid-749-miles/vo_final.wav; words.json is
aligned on it, so captions follow the recorded words (no scaled or invented timings).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'shared'))
from align import align
from vo import tighten, pace
SCRIPT = ("In 2025, a Lucid Air Grand Touring drove 749 miles on a single charge. The route ran from St Moritz in "
          "Switzerland to Munich in Germany. Hand-picked drivers, cool weather, and a long downhill helped. "
          "The official EPA rating is 512 miles. Follow for the next one.")
SAY = {'2025': 'twenty twenty five', '749': 'seven hundred forty nine', 'St': 'saint', 'Hand-picked': 'hand picked',
       'EPA': 'e. p. a.', '512': 'five hundred twelve'}
EXTRA = {'moritz': 'M AO R IH T S', 'lucid': 'L UW S IH D'}
CLIP, OUT = os.path.join(ROOT, 'out', 'lucid-749-miles', 'voiceover.wav'), os.path.join(ROOT, 'out', 'lucid-749-miles', 'vo_final.wav')
src = align(SCRIPT, CLIP, os.path.join(HERE, 'words_src.json'), say=SAY, extra=EXTRA)
tighten(CLIP, src, OUT, target=16.6, max_tempo=1.0, sent=0.42, comma=0.25, inner=0.25)
align(SCRIPT, OUT, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
