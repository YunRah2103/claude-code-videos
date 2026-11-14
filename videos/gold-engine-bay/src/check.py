"""Checks for a render: ffprobe, contact sheet, motion per second, loop seam, loudness, stills.

  python check.py OUT_DIR/preview.mp4
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np

mp4 = Path(sys.argv[1]); od = mp4.parent
W, H = 1080, 1920

def sh(*a): return subprocess.run(a, capture_output=True, text=True, check=True)

p = json.loads(sh("ffprobe", "-v", "error", "-show_entries",
                  "format=duration:stream=codec_name,width,height,avg_frame_rate,nb_frames",
                  "-of", "json", str(mp4)).stdout)
print("ffprobe:", [(s.get("codec_name"), s.get("width"), s.get("height"), s.get("avg_frame_rate"), s.get("nb_frames"))
                   for s in p["streams"]], "dur", p["format"]["duration"])
sh("ffmpeg", "-v", "error", "-y", "-i", str(mp4), "-vf", "fps=1,scale=180:-2,tile=8x3", "-frames:v", "1", str(od / "contact.jpg"))
for name, t in (("still_frame1", 0), ("still_6s", 6.0), ("still_13s", 13.0)):
    sh("ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(mp4), "-frames:v", "1", str(od / f"{name}.png"))
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vf", "scale=270:480,format=gray",
                      "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
f = np.frombuffer(raw, np.uint8).reshape(-1, 480, 270).astype(np.float32)
diff = np.abs(np.diff(f, axis=0)).mean((1, 2))
changed = (np.abs(np.diff(f, axis=0)) > 6).mean((1, 2)) * 100
print(f"motion: frames {len(f)}; first 2 s mean |dI| {diff[:60].mean():.2f}, min {diff[:60].min():.2f}, "
      f"pixels changing >6/255 per frame {changed[:60].mean():.1f}% (min {changed[:60].min():.1f}%)")
print("per-second mean |dI|:", " ".join(f"{diff[i:i + 30].mean():.1f}" for i in range(0, len(diff), 30)))
print(f"loop seam |last - first| {np.abs(f[-1] - f[0]).mean():.2f} vs typical frame step {np.median(diff):.2f}")
vol = sh("ffmpeg", "-i", str(mp4), "-af", "volumedetect", "-f", "null", "-").stderr
print("audio:", " ".join(l.split("] ")[1] for l in vol.splitlines() if "mean_volume" in l or "max_volume" in l))
