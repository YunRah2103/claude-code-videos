"""Align voiceover.mp3 (OpenAI.fm 'cedar' TTS, supplied with the brief) to the script -> words.json."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from align import align
SCRIPT = ("Ferruccio Lamborghini made tractors. One day he bought a Ferrari, and it kept breaking the same part. He opened it up and found the same clutch he was using in his tractors. He told Enzo Ferrari. Ferrari told him to stick to tractors. So he built his own sports car.")
align(SCRIPT, os.path.join(HERE, 'voiceover.mp3'), os.path.join(HERE, 'words.json'), say={}, extra={'ferruccio': 'F ER UW CH OW'})
