"""Pace and align this episode's voiceover clip (OpenAI.fm 'cedar' TTS, split from out/voiceover/full_voiceover.wav
by shared/split_vo.py into out/revuelto-v12/voiceover.wav). The audio that ships is out/revuelto-v12/vo_final.wav; words.json is
aligned on it, so captions follow the recorded words (no scaled or invented timings).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'shared'))
from align import align
from vo import tighten, pace
SCRIPT = ("A Lamborghini Revuelto has a 6.5-litre V12 and three electric motors. Together, that's 1,001 horsepower. "
          "It was unveiled in 2023, as the V12 hybrid successor to the Aventador. Proof that the V12 isn't finished yet. "
          "Follow for the next one.")
SAY = {'6.5-litre': 'six point five liter', 'V12': 'v. twelve', '1,001': 'one thousand and one', '2023': 'twenty twenty three'}
EXTRA = {'revuelto': 'R EH V W EH L T OW', 'aventador': 'AH V EH N T AH D AO R', 'lamborghini': 'L AE M B AO R G IY N IY'}
CLIP, OUT = os.path.join(ROOT, 'out', 'revuelto-v12', 'voiceover.wav'), os.path.join(ROOT, 'out', 'revuelto-v12', 'vo_final.wav')
src = align(SCRIPT, CLIP, os.path.join(HERE, 'words_src.json'), say=SAY, extra=EXTRA)
tighten(CLIP, src, OUT, target=16.6, max_tempo=1.0, sent=0.42, comma=0.25, inner=0.25)   # trim pauses only, no speed-up
align(SCRIPT, OUT, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
