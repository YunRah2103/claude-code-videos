"""Align the voiceover clip for this episode (OpenAI.fm 'cedar' TTS, three chunks supplied with the brief).

out/voiceover/full_voiceover.wav joins the three loudness-matched chunks with 2 s gaps; shared/vo_split.py cuts it
into one clip per episode, saved as out/cybertruck-fix-in-post/voiceover.wav (not committed). The audio is used as read: no
tightening or tempo change. words_v1.json keeps the previous read's timings, which render.py maps onto this one.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = ("What happens when you throw a steel ball at a Cybertruck? At the 2019 reveal, the chief designer did exactly that. The driver's window shattered. Then the rear window broke too. Elon Musk's response: We'll fix it in post. Would you have trusted that window?")
SAY = {'Cybertruck': 'cyber truck', '2019': 'two thousand nineteen', "Musk's": 'musks', 'Cybertruck?': 'cyber truck'}
EXTRA = {'elon': 'IY L AA N', 'musks': 'M AH S K S'}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'cybertruck-fix-in-post', 'voiceover.wav')
if __name__ == '__main__':
    align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
