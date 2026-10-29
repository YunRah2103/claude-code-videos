"""Align voiceover.mp3 (OpenAI.fm 'cedar' TTS, supplied with the brief) to the script -> words.json."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = ("In 1959, Britain was short on fuel. So engineer Alec Issigonis had one job: fit a whole car into a tiny space. He turned the engine sideways, which freed up room for passengers. Heating was even an optional extra. That tiny car became one of the most loved cars ever made. Follow for the next one.")
align(SCRIPT, os.path.join(HERE, 'voiceover.mp3'), os.path.join(HERE, 'words.json'), say={'1959': 'nineteen fifty nine'}, extra={'issigonis': 'IH S IH G OW N IH S'})
