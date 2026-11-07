"""Verify final.mp4 against the pixel/audio rules. Exit 1 if any check fails.

python verify.py <outdir>   (expects final.mp4, master_silent_yuv444.mp4, text_report.json)
Writes <outdir>/verify_report.md and 4x zoom crops of the tyre and the bar.
"""
import json, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import render as r  # noqa: E402

OW, OH, BS = 1080, 1920, 8
TOL = 6          # per-channel tolerance for "uniform" 8x8 blocks after lossy decode


def probe(path, entries):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', entries, '-of', 'json', str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def frames(path):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         stdout=subprocess.PIPE)
    n = OW * OH * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).reshape(OH, OW, 3)
    p.wait()


def block_uniform(fr):
    b = fr.reshape(OH // BS, BS, OW // BS, BS, 3).astype(np.int16)
    rng = b.max((1, 3)) - b.min((1, 3))
    return (rng.max(-1) <= TOL)


CROP_FRAMES = (75, 165, r.FLUSH_F - 1, r.FLUSH_F, r.FLUSH_F + 1)
MAX_STRAIGHT = 20   # native px: longest allowed perfectly straight edge in background structures
FLAT = 13           # a single-colour square this size (i.e. larger than 12x12) fails


def longest_straight(a):
    """Longest perfectly straight edge: a run of adjacent boundary pixels along one row/column where
    the two sides differ and at least one side keeps one colour the whole way. Returns (len_px, where)."""
    best, where = 0, None
    for name, arr in (('horizontal', a), ('vertical', a.T)):
        A, B = arr[:-1].astype(int), arr[1:].astype(int)
        diff = A != B
        for side, same in (('a', A[:, 1:] == A[:, :-1]), ('b', B[:, 1:] == B[:, :-1])):
            link = diff[:, 1:] & diff[:, :-1] & same
            cur = np.zeros(link.shape[0], int)
            for x in range(link.shape[1]):
                cur = (cur + 1) * link[:, x]
                m = int(cur.max())
                if m + 1 > best:
                    best, where = m + 1, (name, int(cur.argmax()), x + 1)
    return best, where


def flat_region(a, n=FLAT, skip=(254,)):
    """First n x n block of one colour (sky sentinel skipped), or None."""
    for c in np.unique(a):
        if c in skip:
            continue
        m = np.pad((a == c).astype(np.int32), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        win = m[n:, n:] - m[:-n, n:] - m[n:, :-n] + m[:-n, :-n]
        hit = np.argwhere(win == n * n)
        if len(hit):
            return int(c), (int(hit[0][1]), int(hit[0][0]))
    return None


def main(out):
    out = Path(out)
    final, master = out / 'final.mp4', out / 'master_silent_yuv444.mp4'
    res = []

    def check(name, ok, detail):
        res.append((name, bool(ok), detail))

    info = probe(final, 'stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,sample_rate,duration,color_space')
    v = [s for s in info['streams'] if s['codec_type'] == 'video'][0]
    a = [s for s in info['streams'] if s['codec_type'] == 'audio']
    check('Output 1080x1920 H.264 30fps yuv420p', (v['width'], v['height'], v['codec_name'], v['r_frame_rate'], v['pix_fmt'])
          == (1080, 1920, 'h264', '30/1', 'yuv420p'), f"{v['width']}x{v['height']} {v['codec_name']} {v['r_frame_rate']} {v['pix_fmt']} {v.get('color_space')}")

    # decoded frames: block uniformity + stepped animation
    uni, n, same, prev, decoded = [], 0, 0, None, []
    for fr in frames(final):
        uni.append(block_uniform(fr).mean())
        if prev is not None and np.abs(fr.astype(np.int16) - prev).mean() < 0.5:
            same += 1
        prev = fr.astype(np.int16)
        if n in CROP_FRAMES:
            decoded.append(fr.copy())
        n += 1
    check('Decoded frames: >=99% of 8px blocks uniform', min(uni) >= 0.99,
          f'worst frame {min(uni) * 100:.2f}%, mean {np.mean(uni) * 100:.2f}% (tolerance +/-{TOL} per channel, final yuv420p)')
    muni = [block_uniform(fr).mean() for i, fr in enumerate(frames(master)) if i % 15 == 0]
    check('Master yuv444p: 8px blocks uniform', min(muni) >= 0.999, f'worst sampled frame {min(muni) * 100:.3f}%')
    check('Frame count 390 (13.0s @30)', n == 390, f'{n} frames')
    check('>=40% consecutive decoded frames identical', same / (n - 1) >= 0.40, f'{same}/{n - 1} = {same / (n - 1) * 100:.1f}%')

    # background structures (street layers rendered alone, open sky masked; UI, car and tyre scenes excluded)
    worst, wf, nbg = (0, None), None, 0
    for kf in r.KEYS:
        t = kf / r.FPS
        if 3.45 <= t < 6.0:          # tread close-up / punch-in: kept as-is, not a street frame
            continue
        bg = r.street(t, r.KEY_IDX[kf], sentinel=True)
        nbg += 1
        L, pos = longest_straight(bg)
        if L > worst[0]:
            worst = (L, f't={t:.2f}s {pos}')
        f = flat_region(bg)
        if f and wf is None:
            wf = f't={t:.2f}s colour {f[0]} at {f[1]}'
    check(f'Background: no straight edge > {MAX_STRAIGHT} native px', worst[0] <= MAX_STRAIGHT,
          f'longest {worst[0]} px over {nbg} background drawings ({worst[1]})')
    check('Background: no flat area > 12x12 without a shading step', wf is None,
          wf or f'none in {nbg} background drawings (open sky excluded)')

    # pre-encode native frames
    nat = r.all_native()
    cols = np.unique(np.concatenate([f.reshape(-1, 3) for f in nat[::1]]), axis=0)
    check('Pre-encode frames <=32 unique colours (cap raised from 16 at your request)', len(cols) <= 32, f'{len(cols)} colours over all {len(nat)} native frames')
    nsame = sum(np.array_equal(nat[i], nat[i + 1]) for i in range(len(nat) - 1))
    holds = np.diff(r.KEYS + [r.NF])
    check('Stepped 8-12 fps unique drawings, uneven holds', 8 <= len(r.KEYS) / r.DUR <= 12 and len(set(holds)) > 1,
          f'{len(r.KEYS)} drawings = {len(r.KEYS) / r.DUR:.1f}/s, holds {sorted(set(holds.tolist()))} frames; native identical pairs {nsame}/{len(nat) - 1}')

    # text
    tr = json.load(open(out / 'text_report.json'))
    bad = [k for k, t in tr.items() if not t['fits']]
    check('No text overflow / clipping', not bad and len(tr) >= 10, f'{len(tr)} text items measured; failures: {bad or "none"}')
    low = {k: t['contrast'] for k, t in tr.items() if t['contrast'] < 7}
    check('Headline/captions contrast >= 7:1 (WCAG AAA)', not low,
          'min ' + str(min(t['contrast'] for t in tr.values())) + (f' low: {low}' if low else ''))

    # audio
    if a:
        ad = float(a[0]['duration'])
        check('Audio 13.0s +/-0.1s, AAC 48kHz', abs(ad - 13.0) <= 0.1 and a[0]['codec_name'] == 'aac' and a[0]['sample_rate'] == '48000',
              f"{ad:.3f}s {a[0]['codec_name']} {a[0]['sample_rate']}Hz")
        pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(final), '-f', 'f32le', '-ac', '1', '-ar', '48000', '-'],
                             capture_output=True, check=True).stdout
        x = np.frombuffer(pcm, np.float32)
        check('No clipping', np.abs(x).max() < 0.999, f'peak {20 * np.log10(np.abs(x).max()):.2f} dBFS')
        tm = json.load(open(HERE / 'build' / 'timing.json'))
        with wave.open(str(HERE / 'build' / 'vo.wav')) as w:
            vo = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
        hop = 480
        envv = np.array([np.abs(vo[i:i + hop]).max() for i in range(0, len(vo), hop)])
        offs = []
        for L in tm['lines']:
            s0 = int(L['slot'][0] * 100)
            onset = s0 + int(np.argmax(envv[s0:] > 0.02))
            offs.append(onset / 100 - L['slot'][0])
        check('Each VO line starts within 0.15s of its slot', all(0 <= o <= 0.15 for o in offs),
              ', '.join(f'L{i + 1} +{o:.2f}s' for i, o in enumerate(offs)))
        check('VO time-fit within +/-8% tempo', all(L['fits'] and L['tempo'] <= 1.08 for L in tm['lines']),
              ', '.join(f"L{L['line']} x{L['tempo']}" for L in tm['lines']))
    else:
        check('Audio present', False, 'no audio stream (silent render)')

    # flush moment: one white frame on the worn tyre, on the click, on "...level with the BAR"
    cx, cy = r.PROG_C[1]
    box = (slice(cy - 30, cy + 30), slice(cx - 30, cx + 30))
    wf = [float((nat[f][box] == r.PAL[r.WH]).all(-1).mean()) for f in (r.FLUSH_F - 1, r.FLUSH_F, r.FLUSH_F + 1)]
    tm = json.load(open(HERE / 'build' / 'timing.json'))
    click = [t for nm, t in tm['sfx'] if nm == 'click'][0]
    check('Flush: one-frame white flash exactly on the click', wf[1] > 0.4 and wf[0] < 0.1 and wf[2] < 0.1
          and abs(click - r.FLUSH_T) < 1 / 30,
          f'frame {r.FLUSH_F} ({r.FLUSH_T:.2f}s) white {wf[1]:.0%} vs {wf[0]:.0%}/{wf[2]:.0%} either side; click at {click:.2f}s')
    # tread scene: the bar is the brightest colour in frame
    lums = [r.lum(i) for i in range(32)]
    bad = []
    for f in range(150, 180):
        idx = np.unique(r.frame_idx(f))
        if max(idx, key=lambda i: lums[i]) != r.BY:
            bad.append(f)
    check('Tread scene: wear bar is the brightest colour', not bad, f'frames failing: {bad or "none"} (5.0-6.0 s)')
    # no empty dark plates (UI); the zoom close-up's wheel-spoke holes are excluded
    empty = None
    for f in range(0, r.NF, 3):
        if 90 <= f < 150:
            continue
        fl = flat_region((nat[f] == r.PAL[r.K]).all(-1).astype(np.uint8), 24, skip=(0,))
        if fl:
            empty = f'frame {f} at {fl[1]}'; break
    check('No empty dark rectangle (24x24 navy area) in UI frames', empty is None, empty or 'none')

    # 4x crops (from the decoded final)
    hook, rev, f0, f1, f2 = decoded
    Image.fromarray(hook[1040:1720, 392:1072]).resize((2720, 2720), Image.NEAREST).save(out / 'zoom4x_tyre.png')
    Image.fromarray(rev[880:1248, 400:672]).resize((1088, 1472), Image.NEAREST).save(out / 'zoom4x_bar.png')
    fx, fy = cx * 8, cy * 8
    tri = [Image.fromarray(fr_[fy - 296:fy - 40, fx - 168:fx + 168]).resize((1344, 1024), Image.NEAREST) for fr_ in (f0, f1, f2)]
    sheet = Image.new('RGB', (1344 * 3 + 32, 1024), (23, 26, 46))
    for i, im in enumerate(tri):
        sheet.paste(im, (i * (1344 + 16), 0))
    sheet.save(out / 'zoom4x_flush.png')

    ok = all(o for _, o, _ in res)
    md = ['# verify.py report', '', f'Overall: **{"PASS" if ok else "FAIL"}**', '', '| Check | Result | Detail |', '|---|---|---|']
    md += [f'| {n_} | {"PASS" if o else "FAIL"} | {d} |' for n_, o, d in res]
    md += ['', 'Crops (4x of the 1080x1920 output): zoom4x_tyre.png (hook, 2.5s), zoom4x_bar.png (tread scene, 5.5s), '
           f'zoom4x_flush.png (frames {r.FLUSH_F - 1}/{r.FLUSH_F}/{r.FLUSH_F + 1}: before / flash / after).']
    (out / 'verify_report.md').write_text('\n'.join(md) + '\n')
    print('\n'.join(md))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else '../../../out/tyre-wear-bars'))
