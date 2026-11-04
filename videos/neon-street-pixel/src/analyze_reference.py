"""Measure a reference pixel-art clip so an original can match its timing, palette and motion.

Usage: python analyze_reference.py REFERENCE.mp4 spec.json
Reads only statistics (no frames are kept). Writes a small JSON spec.
"""
import json, subprocess, sys
import numpy as np
from PIL import Image

FPS_SAMPLE = 10  # frames per second sampled for motion analysis


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,r_frame_rate",
         "-of", "json", path], capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    v = next(s for s in d["streams"] if "width" in s)
    num, den = v["r_frame_rate"].split("/")
    return float(d["format"]["duration"]), int(v["width"]), int(v["height"]), float(num) / float(den)


def frames(path, size):
    """Yield RGB frames at FPS_SAMPLE, downscaled to `size` (w, h) via ffmpeg pipe."""
    w, h = size
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={FPS_SAMPLE},scale={w}:{h}:flags=neighbor",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = len(raw) // (w * h * 3)
    return np.frombuffer(raw, np.uint8)[: n * w * h * 3].reshape(n, h, w, 3)


def main(src, dst):
    dur, W, H, fps = probe(src)
    arr = frames(src, (180, 180)).astype(np.float32)
    motion = np.abs(np.diff(arr, axis=0)).mean(axis=(1, 2, 3))  # per step
    # Per-second motion summary (0..1 scale, 255 = full change)
    per_sec = []
    for s in range(int(dur)):
        seg = motion[s * FPS_SAMPLE:(s + 1) * FPS_SAMPLE]
        per_sec.append(round(float(seg.mean()) / 255, 4) if len(seg) else 0.0)
    # Brightness and palette from a few evenly spaced frames
    idx = np.linspace(0, len(arr) - 1, 8).astype(int)
    pal_img = Image.fromarray(np.concatenate(arr[idx].astype(np.uint8), axis=0)).quantize(colors=16, method=Image.Quantize.MEDIANCUT)
    pal = pal_img.getpalette()[: 16 * 3]
    palette = ["#%02x%02x%02x" % tuple(pal[i:i + 3]) for i in range(0, len(pal), 3)]
    # Colour cast: average of the brightest 10% pixels (neon accents) vs. the rest
    lum = arr.mean(axis=3)
    thr = np.percentile(lum, 90)
    accents = arr[lum >= thr].mean(axis=0)
    spec = {
        "source_duration_s": round(dur, 2),
        "source_size": [W, H],
        "source_fps": round(fps, 2),
        "motion_per_second_0_to_1": per_sec,
        "mean_brightness_0_to_255": round(float(lum.mean()), 1),
        "accent_rgb_top10pct": [int(x) for x in accents],
        "palette_16": palette,
    }
    with open(dst, "w") as fh:
        json.dump(spec, fh, indent=2)
    print(json.dumps({k: spec[k] for k in ("source_duration_s", "source_size", "source_fps",
                                           "mean_brightness_0_to_255", "accent_rgb_top10pct")}))
    print("motion/s:", per_sec)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
