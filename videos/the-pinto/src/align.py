"""Align voiceover.mp3 (OpenAI.fm 'cedar' TTS, supplied with the brief) to the script -> words.json."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = ("The Ford Pinto was meant to be cheap. But its fuel tank could rupture in a rear crash, and the fire could be deadly. Campaigners say internal documents showed Ford weighed the cost of fixing it. In 1978, Ford recalled the cars. Then in 1980, a jury found Ford not guilty in a criminal case. Cheap car. Expensive lesson.")
align(SCRIPT, os.path.join(HERE, 'voiceover.mp3'), os.path.join(HERE, 'words.json'), say={'1978': 'nineteen seventy eight', '1980': 'nineteen eighty'}, extra={})
