"""Sample a video for heuristic black frames and freezes; never a visual review."""
import argparse
import io
import json
import math
import subprocess
import sys
from fractions import Fraction
from PIL import Image, ImageChops, ImageStat


def assess_samples(frames, timestamps, black_threshold=8, difference_threshold=1):
    if not frames or len(frames) != len(timestamps):
        raise ValueError('frames and timestamps must be nonempty and match')
    if any(not math.isfinite(t) for t in timestamps):
        raise ValueError('timestamps must be finite')
    small = [frame.convert('RGB').resize((64, 64), Image.Resampling.NEAREST) for frame in frames]
    black = [timestamps[i] for i, frame in enumerate(small)
             if max(ImageStat.Stat(frame).mean) <= black_threshold]
    similar = []
    for i in range(1, len(small)):
        diff = ImageStat.Stat(ImageChops.difference(small[i-1], small[i])).mean
        if sum(diff) / 3 <= difference_threshold:
            similar.append([timestamps[i-1], timestamps[i]])
    warnings = []
    if black:
        warnings.append('Nearly black samples detected; inspect context.')
    if similar:
        warnings.append('Similar sampled frames detected; intentional stills are possible.')
    return {'black_samples': black, 'similar_pairs': similar, 'warnings': warnings}


def inspect(path, count=12):
    if not 2 <= count <= 100:
        raise ValueError('samples must be between 2 and 100')
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                            '-of', 'json', str(path)], capture_output=True, text=True, timeout=60)
    if probe.returncode:
        raise ValueError('ffprobe failed: ' + probe.stderr[-500:])
    data = json.loads(probe.stdout)
    video = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
    if video is None:
        raise ValueError('no video stream')
    duration = float(data['format'].get('duration', 0))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('video duration unavailable or invalid')
    times = [round(duration * (i + .5) / count, 4) for i in range(count)]
    frames = []
    for t in times:
        result = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', str(path),
                                 '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'],
                                capture_output=True, timeout=60)
        if result.returncode or not result.stdout:
            raise ValueError(f'frame extraction failed at {t}s')
        with Image.open(io.BytesIO(result.stdout)) as frame:
            frames.append(frame.copy())
    report = assess_samples(frames, times)
    rate = video.get('avg_frame_rate', '0/1')
    report.update({'duration_seconds': duration, 'width': video.get('width'),
                   'height': video.get('height'), 'fps': float(Fraction(rate)),
                   'samples': count, 'note': 'Heuristics only; review actual motion and art.'})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video')
    parser.add_argument('--samples', type=int, default=12)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.video, args.samples), indent=2))
        return 0
    except (OSError, ValueError, KeyError, ZeroDivisionError, subprocess.TimeoutExpired) as error:
        print(f'Visual QA failed: {error}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
