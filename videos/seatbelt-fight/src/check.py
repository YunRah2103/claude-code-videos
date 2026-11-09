"""Contact sheet (every 0.1 s) + motion/loop/loudness numbers for the hook preview.
Motion(sec) = mean |diff| between the 108x192 greyscale frames at the start and end of that second.
Loop = mean |diff| first vs last frame on the same measure."""
import os, subprocess, sys
import numpy as np
mp4 = sys.argv[1]; out = os.path.dirname(mp4)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', mp4, '-vf', "select='not(mod(n\\,6))',scale=216:384,tile=10x3",
                '-frames:v', '1', os.path.join(out, 'contact-sheet.png')], check=True)
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', mp4, '-vf', 'scale=108:192,format=gray', '-f', 'rawvideo', '-'],
                     capture_output=True, check=True).stdout
g = np.frombuffer(raw, np.uint8).reshape(-1, 192, 108).astype(np.float32)
n = len(g); print('frames', n)
d = lambda a, b: float(np.abs(g[a] - g[b]).mean())
print('motion per second:', [round(d(s * 60, min(s * 60 + 59, n - 1)), 1) for s in range(3)])
print('peak change within each second:', [round(max(d(s * 60, i) for i in range(s * 60, min(s * 60 + 60, n))), 1) for s in range(3)])
print('loop diff first-last: %.2f' % d(0, n - 1))
step = [d(i, i + 1) for i in range(n - 1)]
print('largest frame steps:', sorted(((round(v, 1), i + 1) for i, v in enumerate(step)), reverse=True)[:5])
mean = g.mean((1, 2)); sd = g.std((1, 2))
print('flat frames (std<4):', [i for i in range(n) if sd[i] < 4])
r = subprocess.run(['ffmpeg', '-nostats', '-i', mp4, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
print('loudness:', ' '.join(r.split('Summary:')[1].split()))
print(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,width,height,r_frame_rate,pix_fmt,display_aspect_ratio,bit_rate:format=duration',
                      '-of', 'compact', mp4], capture_output=True, text=True).stdout)
