"""Align this episode's voiceover clip (split from out/voiceover/full_voiceover.wav, OpenAI.fm 'cedar' TTS supplied
with the brief) to its script: words.json is the timing spine for captions and cues. The clip is used as is."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = "Bugatti's Tourbillon makes 1,800 horsepower, from a V16 and three electric motors. Its gauges sit inside the steering wheel, so they stay visible as the wheel turns. Follow for the next one."
SAY = {"Bugatti's": 'bugattis', '1,800': 'one thousand eight hundred', 'V16': 'v sixteen'}
EXTRA = {'bugattis': 'B UW G AA T IY Z', 'tourbillon': 'T UH R B IY Y AO N'}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'tourbillon-wheel-gauges', 'voiceover.wav')
align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
