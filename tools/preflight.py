"""Pre-delivery checks for a vertical short.
Usage: python tools/preflight.py VIDEO.mp4 --meta META.json --words WORDS.json --facts FACTS.md [--align-pct N]
META.json comes from the renderer (`render.py meta`): caption boxes, on-screen texts, size, fps."""
import argparse, json, re, subprocess, sys

NUMWORDS = {'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve',
            'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty', 'thirty',
            'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety', 'hundred', 'thousand', 'million', 'half',
            'sixteenth', 'first', 'second', 'third'}

def numtokens(s):
    toks = set(re.findall(r"\d[\d,.]*\d|\d", s))
    for w in re.findall(r"[a-z]+", s.lower()):
        if w in NUMWORDS: toks.add(w)
    return {t.rstrip('.,') for t in toks}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video'); ap.add_argument('--meta', required=True); ap.add_argument('--words', required=True)
    ap.add_argument('--facts', required=True); ap.add_argument('--align-pct', type=float)
    ap.add_argument('--lufs', type=float, default=-14.0); ap.add_argument('--max-mbps', type=float, default=15.0)
    a = ap.parse_args()
    meta, words = json.load(open(a.meta)), json.load(open(a.words))
    fails, notes = [], []
    def check(ok, msg): (notes if ok else fails).append(('PASS ' if ok else 'FAIL ') + msg)

    # container / stream
    pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', a.video],
                                   capture_output=True, text=True, check=True).stdout)
    v = next(s for s in pr['streams'] if s['codec_type'] == 'video')
    au = [s for s in pr['streams'] if s['codec_type'] == 'audio']
    w, h = meta['size']
    check((v['width'], v['height']) == (w, h), f"resolution {v['width']}x{v['height']}")
    num, den = map(int, v['r_frame_rate'].split('/'))
    check(abs(num / den - meta['fps']) < .01, f"fps {num / den:.2f}")
    check(bool(au), 'audio stream present')
    mbps = int(pr['format']['bit_rate']) / 1e6
    check(mbps <= a.max_mbps, f"bitrate {mbps:.2f} Mbps (<= {a.max_mbps})")
    dur = float(pr['format']['duration'])
    check(abs(dur - meta['duration']) < 0.5, f"duration {dur:.2f}s")

    # loudness
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', a.video, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]); tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])
    check(abs(I - a.lufs) <= 1.0, f"integrated loudness {I:.1f} LUFS (target {a.lufs})")
    check(tp < 0.0, f"true peak {tp:.1f} dBTP (no clipping)")

    # alignment + caption/audio word match
    if a.align_pct is not None:
        check(a.align_pct >= 95, f"word alignment {a.align_pct:.1f}%")
    cap_words = ' '.join(c['text'] for c in meta['captions']).split()
    spoken = [x['w'].lstrip('.') for x in words]
    check(cap_words == spoken, f"captions match spoken words ({len(cap_words)}/{len(spoken)})")

    # caption safe zone
    bad = []
    for c in meta['captions']:
        if not (0.12 * h <= c['y0'] and c['y1'] <= 0.62 * h and c['x0'] >= 0 and c['x1'] <= 0.85 * w):
            bad.append(f"'{c['text']}' box {c['x0']},{c['y0']}-{c['x1']},{c['y1']}")
        if c['cap_height'] < 0.025 * h:
            bad.append(f"'{c['text']}' cap height {c['cap_height']}px < {0.025 * h:.0f}px")
    check(not bad, 'caption zones/size' + ('' if not bad else ': ' + '; '.join(bad[:5])))

    # numbers vs FACTS.md "Allowed numbers" table
    facts = open(a.facts).read()
    allowed_block = facts.split('## Allowed numbers', 1)[-1]
    allowed = set()
    for line in allowed_block.splitlines():
        if line.startswith('|'):
            allowed |= numtokens(line.split('|')[1])
    texts = [c['text'] for c in meta['captions']] + meta.get('onscreen', [])
    stray = sorted({t for s in texts for t in numtokens(s)} - allowed)
    check(not stray, 'numbers sourced in FACTS.md' + ('' if not stray else ': unsourced ' + ', '.join(stray)))

    # nothing generated tracked by git
    g = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'], capture_output=True, text=True).stdout.split()
    g += subprocess.run(['git', 'diff', '--cached', '--name-only', '--diff-filter=AM'], capture_output=True, text=True).stdout.split()
    gen = [f for f in g if re.search(r'\.(mp4|wav|raw)$', f)]
    check(not gen, 'no MP4/WAV staged or untracked-unignored' + ('' if not gen else ': ' + ', '.join(gen[:5])))

    for n in notes + fails: print(n)
    print(f"preflight: {len(notes)} passed, {len(fails)} failed")
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    main()
