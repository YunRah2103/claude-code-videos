"""Frame-to-frame motion score of a video: mean absolute grey-level difference (0-255) between consecutive frames,
sampled at 108x192 greyscale and 10 fps (same method for every version).
    python shared/motion_score.py video.mp4 [t0=0] [t1=1]   -> prints the mean score over [t0, t1] and each step
"""
import subprocess, sys
import numpy as np


def score(path, t0=0.0, t1=1.0):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t0), '-i', path, '-t', str(t1 - t0 + 0.05), '-vf', 'fps=10,scale=108:192,format=gray',
                          '-f', 'rawvideo', '-'], capture_output=True, check=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 192, 108).astype(np.float32)
    steps = [float(np.abs(f[i + 1] - f[i]).mean()) for i in range(len(f) - 1)]
    return float(np.mean(steps)), steps


if __name__ == '__main__':
    a = sys.argv[1:]
    m, s = score(a[0], *(float(x) for x in a[1:3]))
    print(f'{m:.1f}', ' '.join(f'{x:.1f}' for x in s))
