"""Align voiceover.mp3 (OpenAI.fm 'cedar' TTS, supplied with the brief) to the script -> words.json."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = ("Mercedes wanted a car that cut through the air like nothing else. So they looked to the sea. The yellow boxfish is almost perfectly shaped for moving through water. In 2005, Mercedes built the Bionic concept car on that same shape. Sometimes the best engineers are fish.")
align(SCRIPT, os.path.join(HERE, 'voiceover.mp3'), os.path.join(HERE, 'words.json'), say={'2005': 'two thousand five'}, extra={'boxfish': 'B AA K S F IH SH'})
