"""Align this episode's voiceover clip (split from out/voiceover/full_voiceover.wav, OpenAI.fm 'cedar' TTS supplied
with the brief) to its script: words.json is the timing spine for captions and cues. The clip is used as is."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = "Honda's Civic Type R set a 7 minutes 44.881 second lap of the Nürburgring in April 2023. It was reported as the fastest front-wheel-drive production car around the track. Follow for the next one."
SAY = {'7': 'seven', '44.881': 'forty four point eight eight one', 'Nürburgring': 'nurburgring', '2023': 'twenty twenty three', 'front-wheel-drive': 'front wheel drive'}
EXTRA = {'nurburgring': 'N ER B ER G R IH NG'}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'civic-type-r-7-44', 'voiceover.wav')
align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
