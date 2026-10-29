"""Tighten and align the voiceover (OpenAI.fm 'cedar' TTS, supplied with the brief).
The supplied read ends before the scripted "Follow for the next one."; the end card shows that line instead.

voiceover_src.mp3 is the supplied read; vo.tighten() shortens its pauses into voiceover.mp3, which is aligned
again so words.json matches the audio that ships.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = ("The story goes that Land Rover was sketched in the sand. Its designer, Maurice Wilks, had a surplus Willys Jeep on his farm. It was reliable, but rough, and parts were getting harder to find. After the war, steel was scarce, so they used aluminium left over from wartime aircraft. On 30 April 1948, the Series I was unveiled in Amsterdam. From a sketch in the sand to an icon.")
SAY = {'30': 'thirtieth', '1948': 'nineteen forty eight', 'I': 'one', 'aluminium': 'alyoominium'}
EXTRA = {'willys': 'W IH L IY Z', 'alyoominium': 'AE L Y UW M IH N IY AH M'}
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'), max_tempo=1.28, sent=0.24, comma=0.15, inner=0.18)
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
