"""Align this episode's voiceover clip (split from out/voiceover/full_voiceover.wav, OpenAI.fm 'cedar' TTS supplied
with the brief) to its script: words.json is the timing spine for captions and cues. The clip is used as is."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = "Koenigsegg's Jesko Absolut was reportedly timed at 27.83 seconds from 0 to 400 km/h and back to zero. Follow for the next one."
SAY = {"Koenigsegg's": 'koenigseggs', '27.83': 'twenty seven point eight three', '0': 'zero', '400': 'four hundred', 'km/h': 'kilometers an hour'}
EXTRA = {'koenigseggs': 'K OW N IH G S EH G Z', 'jesko': 'Y EH S K OW'}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'jesko-0-400-0', 'voiceover.wav')
align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
