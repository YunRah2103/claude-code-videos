"""Align this episode's voiceover clip (split from out/voiceover/full_voiceover.wav, OpenAI.fm 'cedar' TTS supplied
with the brief) to its script: words.json is the timing spine for captions and cues. The clip is used as is."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = "Four electric motors make 1,914 horsepower in the Rimac Nevera. Rimac claims it does the quarter mile in 8.58 seconds. That's at 167 miles an hour. Follow for the next one."
SAY = {'1,914': 'one thousand nine hundred fourteen', '8.58': 'eight point five eight', '167': 'one hundred sixty seven'}
EXTRA = {'rimac': 'R IY M AA T S', 'nevera': 'N EH V EH R AH'}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'rimac-nevera-1914', 'voiceover.wav')
align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
