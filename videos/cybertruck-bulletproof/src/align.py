"""Align the voiceover clip for this episode (OpenAI.fm 'cedar' TTS, three chunks supplied with the brief).

out/voiceover/full_voiceover.wav joins the three loudness-matched chunks with 2 s gaps; shared/vo_split.py cuts it
into one clip per episode, saved as out/cybertruck-bulletproof/voiceover.wav (not committed). The audio is used as read: no
tightening or tempo change.
The chunk 3 read stops after 'protection.'; the closing 'So, would you still buy one?' was supplied as its own cedar
file and joined on after a 0.45 s pause (out/voiceover/ep7_end.wav), so voiceover.wav holds the full script. words_v1.json keeps the previous read's timings, which render.py maps onto this one.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = ("Is the Cybertruck bulletproof? Its body is 3 millimetre stainless steel, the same alloy used on SpaceX's Starship. In independent tests, it resisted 9mm rounds. But rifle rounds got through the outer layer. And the windows offer no real bullet protection. So, would you still buy one?")
SAY = {'3': 'three', 'millimetre': 'millimeter', "SpaceX's": "space x's", 'Starship': 'star ship', '9mm': 'nine millimeter', 'bulletproof': 'bullet proof', 'Its': 'its', 'Cybertruck': 'cyber truck', 'bulletproof': 'bullet proof'}
EXTRA = {}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'cybertruck-bulletproof', 'voiceover.wav')
if __name__ == '__main__':
    align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
