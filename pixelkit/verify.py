#!/usr/bin/env python3
"""Pixel-art video checks. Exit code 1 when any hard check fails.

    python -m pixelkit.verify VIDEO [VIDEO ...] [--labels A B ...]
           [--native-dir DIR] [--palette-size 32] [--block N] [--heatmap DIR]

Per video it decodes every frame at full resolution and reports:
  grid      detected block size and phase (or --block)
  nonuni    % of grid blocks that are not one flat colour (codec-tolerant)
  held      % of consecutive frame pairs that are identical at native scale
  ufps      unique frames per second; hold lengths
  colours   estimated palette of the decoded video (5-bit clusters >= 0.05%)
  size      must be exactly 1080x1920
Pre-encode colour count is checked from --native-dir (PNG frames written by
pixelkit.render); applies only to the first video in the list (ours).
"""
import argparse
import glob
import json
import os
import subprocess
import sys

import numpy as np

# Codec tolerances. A block is "non-uniform" when its core (1px trimmed) spans
# more than RANGE_T in any channel; two native frames are "identical" when no
# native pixel (block-core mean) moves more than HOLD_T. Calibrated on the
# decoded Reference (HEVC) and on our x264 renders of flat blocks.
RANGE_T = 24
HOLD_T = 28
MAX_NONUNI = 0.5   # percent
MIN_HELD = 40.0    # percent


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
         "-show_entries", "stream=width,height,r_frame_rate,nb_read_packets,pix_fmt,codec_name",
         "-of", "json", path], capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return dict(w=int(s["width"]), h=int(s["height"]), fps=float(num) / float(den),
                n=int(s["nb_read_packets"]), pix=s["pix_fmt"], codec=s["codec_name"])


def frames(path, w, h):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    size = w * h * 3
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    p.wait()


def detect_grid(sample):
    """Return (block, ox, oy) from edge energy folded modulo candidate sizes."""
    best = {}
    for axis in (1, 0):
        e = 0
        for f in sample:
            d = np.abs(np.diff(f.astype(np.int16), axis=axis)).sum(axis=2)
            e = e + d.sum(axis=1 - axis)
        best[axis] = e
    scores = {}
    for b in range(2, 17):
        sx = [best[1][p::b].sum() for p in range(b)]
        sy = [best[0][p::b].sum() for p in range(b)]
        cx = max(sx) / best[1].sum()
        cy = max(sy) / best[0].sum()
        scores[b] = (min(cx, cy), int(np.argmax(sx)), int(np.argmax(sy)))
    top = max(v[0] for v in scores.values())
    b = max(k for k, v in scores.items() if v[0] >= 0.8 * top)
    conc, px, py = scores[b]
    # diff index p means the edge sits between pixel p and p+1
    return b, (px + 1) % b, (py + 1) % b, conc


def blocks(f, b, ox, oy):
    h, w, _ = f.shape
    nx, ny = (w - ox) // b, (h - oy) // b
    return f[oy:oy + ny * b, ox:ox + nx * b].reshape(ny, b, nx, b, 3).transpose(0, 2, 1, 3, 4)


def analyse(path, block=None, heatmap=None, label=None):
    info = probe(path)
    w, h = info["w"], info["h"]
    if block:
        b, ox, oy, conc = block, 0, 0, float("nan")
    else:
        sample = [f for i, f in enumerate(frames(path, w, h)) if i % 30 == 0][:8]
        b, ox, oy, conc = detect_grid(sample)
    t = 1 if b >= 4 else 0
    nonuni = total = 0
    heat = None
    prev = None
    same = []
    changes = None
    hist = {}
    for f in frames(path, w, h):
        bl = blocks(f, b, ox, oy)
        core = bl[:, :, t:b - t, t:b - t].astype(np.int16)
        rng = (core.max(axis=(2, 3)) - core.min(axis=(2, 3))).max(axis=2)
        bad = rng > RANGE_T
        nonuni += int(bad.sum())
        total += bad.size
        heat = bad.astype(np.int32) if heat is None else heat + bad
        nat = core.mean(axis=(2, 3))
        if prev is not None:
            moved = np.abs(nat - prev).max(axis=2) > HOLD_T
            same.append(not moved.any())
            changes = moved.astype(np.int32) if changes is None else changes + moved
        prev = nat
        q = (nat.astype(np.uint8) >> 3).reshape(-1, 3)
        key = (q[:, 0].astype(np.int32) << 10) | (q[:, 1].astype(np.int32) << 5) | q[:, 2]
        u, c = np.unique(key, return_counts=True)
        for k, v in zip(u.tolist(), c.tolist()):
            hist[k] = hist.get(k, 0) + v
    nfr = len(same) + 1
    holds, run = [], 1
    for s in same:
        if s:
            run += 1
        else:
            holds.append(run)
            run = 1
    holds.append(run)
    px = sum(hist.values())
    est_colours = sum(1 for v in hist.values() if v >= px * 0.0005)
    if heatmap and heat is not None:
        from PIL import Image
        os.makedirs(heatmap, exist_ok=True)
        hm = (255 * heat / max(1, heat.max())).astype(np.uint8)
        name = (label or os.path.basename(path)).replace(" ", "_")
        Image.fromarray(hm).resize((hm.shape[1] * 4, hm.shape[0] * 4), Image.NEAREST).save(
            os.path.join(heatmap, f"{name}_offgrid.png"))
    dur = nfr / info["fps"]
    act = changes[changes >= dur] if changes is not None else np.zeros(0)
    block_fps = float(np.median(act)) / dur if act.size else 0.0
    hc = {}
    for x in holds:
        hc[x] = hc.get(x, 0) + 1
    return dict(path=path, **info, block=b, phase=(ox, oy), grid_conc=conc,
                native=(w // b, h // b), nonuni=100.0 * nonuni / max(1, total),
                held=100.0 * sum(same) / max(1, len(same)),
                ufps=len(holds) / dur, block_fps=block_fps,
                active=100.0 * act.size / max(1, changes.size if changes is not None else 1), holds=dict(sorted(hc.items())),
                est_colours=est_colours, frames=nfr)


def native_colours(d):
    cols = set()
    for p in sorted(glob.glob(os.path.join(d, "*.png"))):
        from PIL import Image
        a = np.asarray(Image.open(p).convert("RGB")).reshape(-1, 3)
        cols.update(map(tuple, np.unique(a, axis=0).tolist()))
    return len(cols)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--labels", nargs="*")
    ap.add_argument("--native-dir", help="pre-encode PNG frames of the FIRST video")
    ap.add_argument("--palette-size", type=int, default=32)
    ap.add_argument("--block", type=int, help="force block size (default: detect)")
    ap.add_argument("--heatmap", help="write per-video off-grid heatmaps here")
    ap.add_argument("--json", help="write raw results here")
    a = ap.parse_args(argv)
    labels = a.labels or [os.path.basename(v) for v in a.videos]
    res = []
    for i, (v, lab) in enumerate(zip(a.videos, labels)):
        r = analyse(v, a.block, a.heatmap, lab)
        r["label"] = lab
        r["pre_colours"] = native_colours(a.native_dir) if (i == 0 and a.native_dir) else None
        res.append(r)

    def checks(r):
        c = {
            "block uniformity <= 0.5%": r["nonuni"] <= MAX_NONUNI,
            "held pairs >= 40%": r["held"] >= MIN_HELD,
            "output 1080x1920": (r["w"], r["h"]) == (1080, 1920),
        }
        if r["pre_colours"] is not None:
            c[f"pre-encode colours <= {a.palette_size}"] = r["pre_colours"] <= a.palette_size
        return c

    rows = [
        ("codec / fps", lambda r: f"{r['codec']} {r['pix']} {r['fps']:g}"),
        ("size", lambda r: f"{r['w']}x{r['h']}"),
        ("frames", lambda r: str(r["frames"])),
        ("grid block (phase)", lambda r: f"{r['block']}px ({r['phase'][0]},{r['phase'][1]})"),
        ("native res", lambda r: f"{r['native'][0]}x{r['native'][1]}"),
        ("non-uniform blocks", lambda r: f"{r['nonuni']:.3f}%"),
        ("held pairs", lambda r: f"{r['held']:.1f}%"),
        ("unique frames/s", lambda r: f"{r['ufps']:.1f}"),
        ("animated blocks (>=1/s)", lambda r: f"{r['active']:.1f}%"),
        ("updates/s per anim block", lambda r: f"{r['block_fps']:.1f}"),
        ("hold lengths", lambda r: " ".join(f"{k}x{v}" for k, v in list(r["holds"].items())[:6])),
        ("est. palette (decoded)", lambda r: str(r["est_colours"])),
        ("pre-encode colours", lambda r: "n/a" if r["pre_colours"] is None else str(r["pre_colours"])),
    ]
    width = max(14, max(len(l) for l in labels) + 2)
    print("metric".ljust(28) + "".join(l.ljust(width) for l in labels))
    for name, fn in rows:
        print(name.ljust(28) + "".join(fn(r)[:width - 1].ljust(width) for r in res))
    print()
    ok_all = True
    for r in res:
        c = checks(r)
        ok = all(c.values())
        print(f"{r['label']}: " + ("PASS" if ok else "FAIL") + "  " +
              ", ".join(("ok " if v else "FAIL ") + k for k, v in c.items()))
        if r is res[0]:
            ok_all = ok
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=1, default=str)
    # Exit status reflects the first video (the one under test).
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
