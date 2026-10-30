"""Align this episode's voiceover clip (split from out/voiceover/full_voiceover.wav, OpenAI.fm 'cedar' TTS supplied
with the brief) to its script: words.json is the timing spine for captions and cues. The clip is used as is."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = "Toyota's Mirai fills up with hydrogen in about 5 minutes. Toyota claims it can drive up to 402 miles. But in 2023, there were only 59 hydrogen stations in the US, mostly in California."
SAY = {'5': 'five', '402': 'four hundred two', '2023': 'twenty twenty three', '59': 'fifty nine', 'US': 'u. s.'}
EXTRA = {'mirai': 'M IH R AY'}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'mirai-5-minutes', 'voiceover.wav')
align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
