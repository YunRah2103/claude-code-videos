"""Motion: mean abs luma diff between consecutive frames (0-255), per 0.5 s and per 2 s block."""
import subprocess, sys, numpy as np
w, h = 135, 240
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', sys.argv[1], '-vf', f'scale={w}:{h}', '-f', 'rawvideo',
                      '-pix_fmt', 'gray', '-'], capture_output=True, check=True).stdout
f = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
if '-v' in sys.argv:
    for i in range(0, len(d), 15):
        print(f"{i/30:4.1f}-{(i+15)/30:4.1f}s  motion {d[i:i+15].mean():5.2f}")
blocks = [d[i:i + 60].mean() for i in range(0, len(d), 60)]
print("2 s blocks:", " ".join(f"{i*2}-{i*2+2}s:{b:.1f}" for i, b in enumerate(blocks)))
print(f"first 2 s mean {d[:60].mean():.2f} | min 2 s block {min(blocks):.2f} | min frame diff {d.min():.2f}")
