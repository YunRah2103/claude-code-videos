"""Re-render frame ranges of a finished short and splice them into the existing MP4 (audio kept as-is).
python splice.py NAME in.mp4 out.mp4 t0:t1 [t0:t1 ...]"""
import importlib, os, subprocess, sys
from multiprocessing import Pool
import numpy as np
import engine3d as E

def _init(name):
    global V; V = importlib.import_module(name).V
def _f(n): return V.frame(n)

if __name__ == "__main__":
    name, src, out = sys.argv[1:4]; ranges = [tuple(float(x) for x in r.split(":")) for r in sys.argv[4:]]
    tmpd = out + ".parts"; os.makedirs(tmpd, exist_ok=True)
    frames = {}
    with Pool(os.cpu_count(), initializer=_init, initargs=(name,)) as pool:
        for i, (a, b) in enumerate(ranges):
            n0, n1 = int(round(a * E.FPS)), int(round(b * E.FPS))
            raw = os.path.join(tmpd, f"seg{i}.rgb")
            with open(raw, "wb") as fh:
                for fr in pool.imap(_f, range(n0, n1), chunksize=2): fh.write(fr.tobytes())
            frames[i] = (n0, n1, raw)
    # build filter: trim the original around each segment and concatenate original pieces with the new segments
    inputs = ["-i", src]; parts = []; filt = []; prev = 0; k = 0
    for i, (n0, n1, raw) in sorted(frames.items(), key=lambda kv: kv[1][0]):
        inputs += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920", "-r", str(E.FPS), "-i", raw]
        filt.append(f"[0:v]trim=start_frame={prev}:end_frame={n0},setpts=PTS-STARTPTS,format=yuv420p[o{k}]"); parts.append(f"[o{k}]")
        filt.append(f"[{i + 1}:v]setpts=PTS-STARTPTS,format=yuv420p[s{k}]"); parts.append(f"[s{k}]")
        prev = n1; k += 1
    filt.append(f"[0:v]trim=start_frame={prev},setpts=PTS-STARTPTS,format=yuv420p[o{k}]"); parts.append(f"[o{k}]")
    filt.append("".join(parts) + f"concat=n={len(parts)}:v=1:a=0[vout]"); last = "[vout]"
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filt), "-map", last, "-map", "0:a", "-c:a", "copy",
           "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-maxrate", "2.3M", "-bufsize", "4.6M", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    print("ok", out)
