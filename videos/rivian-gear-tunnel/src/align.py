"""Align this episode's voiceover clip (split from out/voiceover/full_voiceover.wav, OpenAI.fm 'cedar' TTS supplied
with the brief) to its script: words.json is the timing spine for captions and cues. The clip is used as is."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = 'The Rivian R1T has a hidden gear tunnel, behind the rear seats. You reach it from inside the cabin, by folding down the armrest and sliding a door up. Follow for the next one.'
SAY = {'R1T': 'r one t'}
EXTRA = {'rivian': 'R IH V IY AH N'}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'rivian-gear-tunnel', 'voiceover.wav')
align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
