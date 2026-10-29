"""Tighten and align the voiceover (OpenAI.fm 'cedar' TTS supplied with the brief; its missing closing line is the same voice's 'Follow for the next one' from why-the-911).

voiceover_src.mp3 is the supplied read; vo.tighten() shortens its pauses into voiceover.mp3, which is aligned
again so words.json matches the audio that ships.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
from vo import tighten
SCRIPT = ("In 1962, gunmen opened fire on President de Gaulle's car. Two motorcycle bodyguards were killed. The tyres were punctured, but the Citroën DS stayed level. Its hydropneumatic suspension kept it steady, and de Gaulle reached the airport unharmed. After that, he refused to ride in any other car. Follow for the next one.")
SAY = {'1962': 'nineteen sixty two', "Gaulle's": 'gaulles', 'Citroën': 'citroen', 'DS': 'd s'}
EXTRA = {'gaulles': 'G AO L Z', 'hydropneumatic': 'HH AY D R OW N UW M AE T IH K'}
J = lambda f: os.path.join(HERE, f)
src = align(SCRIPT, J('voiceover_src.mp3'), J('words_src.json'), say=SAY, extra=EXTRA)
tighten(J('voiceover_src.mp3'), src, J('voiceover.mp3'))
align(SCRIPT, J('voiceover.mp3'), J('words.json'), say=SAY, extra=EXTRA)
