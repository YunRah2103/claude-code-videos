"""Align the voiceover clip for this episode (OpenAI.fm 'cedar' TTS, three chunks supplied with the brief).

out/voiceover/full_voiceover.wav joins the three loudness-matched chunks with 2 s gaps; shared/vo_split.py cuts it
into one clip per episode, saved as out/bugatti-envelope/voiceover.wav (not committed). The audio is used as read: no
tightening or tempo change. words_v1.json keeps the previous read's timings, which render.py maps onto this one.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = ('What would you draw on the back of an envelope? In 1997, Ferdinand Piëch reportedly sketched a 16-cylinder engine. Four turbochargers. Sixteen cylinders, in a W shape. By 2001, the first version was running at about 1,000 horsepower. Would you have bet on that sketch?')
SAY = {'1997': 'nineteen ninety seven', 'Piëch': 'piech', '16-cylinder': 'sixteen cylinder', 'W': 'double u', '2001': 'two thousand one', '1,000': 'one thousand', 'turbochargers': 'turbo chargers'}
EXTRA = {}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'bugatti-envelope', 'voiceover.wav')
if __name__ == '__main__':
    align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
