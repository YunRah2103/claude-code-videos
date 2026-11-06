"""Render 'Soft energy' (3 pixel-art scenes, 720x682 @30fps, 8.2s) to MP4.

usage: python render.py OUT.mp4            full render
       python render.py --still T OUT.png  single frame at time T
"""
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image

from lib import upscale, bloom, vignette

FPS, OW, OH = 30, 720, 682
DUR = 8.2
CUTS = [(0, 75, 's1', 3), (75, 166, 's2', 2), (166, 246, 's3', 2)]  # frame ranges per scene
BLOOM = {'s1': (160, 7, 0.5), 's2': (175, 7, 0.4), 's3': (130, 7, 0.75)}
_scenes = {}
VIG = vignette(OH, OW, 0.35)


def scene(name):
    if name not in _scenes:
        mod = __import__(name)
        _scenes[name] = getattr(mod, 'Scene' + name[1])()
    return _scenes[name]


def frame(i):
    for (a, b, name, k) in CUTS:
        if a <= i < b:
            t = (i - a) / FPS
            arr = np.clip(scene(name).frame(t), 0, 255).astype(np.uint8)
            img = upscale(arr, k)[:OH, :OW].astype(np.float32)
            th, rad, gain = BLOOM[name]
            img = bloom(img, th, rad, gain) * VIG
            return np.clip(img, 0, 255).astype(np.uint8)
    raise ValueError(i)


def main():
    if sys.argv[1] == '--still':
        t = float(sys.argv[2])
        Image.fromarray(frame(int(round(t * FPS)))).save(sys.argv[3])
        return
    out = sys.argv[1]
    here = os.path.dirname(os.path.abspath(__file__))
    wav = os.path.join(os.path.dirname(out), 'music.wav')
    subprocess.run([sys.executable, os.path.join(here, 'music.py'), wav], check=True)
    n = int(round(DUR * FPS)) + 0
    n = 246
    ff = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}',
                           '-r', str(FPS), '-i', '-', '-i', wav, '-c:v', 'libx264', '-preset', 'slow', '-crf', '14',
                           '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out],
                          stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as p:
        for fr in p.imap(frame, range(n), chunksize=4):
            ff.stdin.write(fr.tobytes())
    ff.stdin.close()
    sys.exit(ff.wait())


if __name__ == '__main__':
    main()
