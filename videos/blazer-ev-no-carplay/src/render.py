"""blazer-ev-no-carplay: Chevrolet showroom skit on the shared showroom engine (videos/showroom-kit/engine.py).
Usage: python render.py video VOICE.wav OUT.mp4 | still T OUT.png [VOICE] | meta OUT.json | thumb OUT.png"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'showroom-kit'))
import engine
DUR = 45.0                                  # approximate; the real length comes from words.json (for tools/video.py preview)
if __name__ == '__main__':
    engine.main(HERE)
