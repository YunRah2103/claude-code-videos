"""Pace and align this episode's voiceover clip (OpenAI.fm 'cedar' TTS, split from out/voiceover/full_voiceover.wav
by shared/split_vo.py into out/taycan-22-minutes/voiceover.wav). The audio that ships is out/taycan-22-minutes/vo_final.wav; words.json is
aligned on it, so captions follow the recorded words (no scaled or invented timings).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'shared'))
from align import align
from vo import tighten, pace
SCRIPT = ("Porsche's Taycan is reportedly the first production car with an 800-volt system. In one test, it charged from "
          "5 to 80 percent in about 22 minutes, on a 270 kilowatt charger. Anyone who's waited behind a slow charger "
          "knows the difference. Follow for the next one.")
SAY = {"Porsche's": 'porsches', '800-volt': 'eight hundred volt', '5': 'five', '80': 'eighty', '22': 'twenty two',
       '270': 'two hundred seventy'}
EXTRA = {'porsches': 'P AO R SH AH Z', 'taycan': 'T AY K AA N'}
CLIP, OUT = os.path.join(ROOT, 'out', 'taycan-22-minutes', 'voiceover.wav'), os.path.join(ROOT, 'out', 'taycan-22-minutes', 'vo_final.wav')
src = align(SCRIPT, CLIP, os.path.join(HERE, 'words_src.json'), say=SAY, extra=EXTRA)
pace(CLIP, src, OUT, lead=0.3)
align(SCRIPT, OUT, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
