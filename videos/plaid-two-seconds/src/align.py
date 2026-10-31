"""Align the voiceover clip for this episode (OpenAI.fm 'cedar' TTS, three chunks supplied with the brief).

out/voiceover/full_voiceover.wav joins the three loudness-matched chunks with 2 s gaps; shared/vo_split.py cuts it
into one clip per episode, saved as out/plaid-two-seconds/voiceover.wav (not committed). The audio is used as read: no
tightening or tempo change. words_v1.json keeps the previous read's timings, which render.py maps onto this one.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = ("Could a four-door car beat a supercar off the line? Tesla's Model S Plaid was claimed to hit 60 miles an hour in 1.99 seconds. It launched in June 2021, with three motors. Over 1,000 horsepower, according to the company. What would you do with 1.99 seconds?")
SAY = {'60': 'sixty', '1.99': 'one point nine nine', '2021': 'twenty twenty one', '1,000': 'one thousand', "Tesla's": 'teslas', 'S': 's.', 'four-door': 'four door', 'supercar': 'super car'}
EXTRA = {'teslas': 'T EH S L AH Z'}
VO = os.path.join(HERE, '..', '..', '..', 'out', 'plaid-two-seconds', 'voiceover.wav')
if __name__ == '__main__':
    align(SCRIPT, VO, os.path.join(HERE, 'words.json'), say=SAY, extra=EXTRA)
