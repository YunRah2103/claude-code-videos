import unittest
from tools.visual_qa import assess_samples

class VisualQATest(unittest.TestCase):
    def test_black_and_freeze_are_warnings(self):
        from PIL import Image
        black = Image.new('RGB', (8, 8), 'black')
        report = assess_samples([black, black.copy(), black.copy()], [0, 1, 2])
        self.assertEqual(report['black_samples'], [0, 1, 2])
        self.assertEqual(report['similar_pairs'], [[0, 1], [1, 2]])
        self.assertTrue(report['warnings'])

    def test_changes_are_observed(self):
        from PIL import Image
        a = Image.new('RGB', (8, 8), 'red')
        b = Image.new('RGB', (8, 8), 'blue')
        report = assess_samples([a, b], [0, 1])
        self.assertEqual(report['black_samples'], [])
        self.assertEqual(report['similar_pairs'], [])

    def test_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            assess_samples([], [])
        with self.assertRaises(ValueError):
            assess_samples([object()], [])

class MediaIntegrationTest(unittest.TestCase):
    def test_real_ffmpeg_black_video_and_missing_media(self):
        import shutil
        import subprocess
        import tempfile
        from pathlib import Path
        from tools.visual_qa import inspect
        if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
            self.skipTest('FFmpeg unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'black.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            'color=black:s=64x64:r=10:d=1', '-c:v', 'mpeg4', str(path)],
                           check=True, capture_output=True)
            result = inspect(path, 3)
            self.assertEqual((result['width'], result['height']), (64, 64))
            self.assertEqual(result['fps'], 10)
            self.assertEqual(len(result['black_samples']), 3)
            with self.assertRaises(ValueError):
                inspect(Path(tmp) / 'missing.mp4', 3)
