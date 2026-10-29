"""Regression coverage for invalid preview durations."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TOOL = Path(__file__).resolve().parents[1] / "tools" / "video.py"


class PreviewDurationTest(unittest.TestCase):
    def test_preview_rejects_none_duration_without_creating_sheet(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "src"
            source.mkdir()
            (source / "render.py").write_text("DUR = None\n")
            output = Path(tmp) / "preview"

            result = subprocess.run(
                [sys.executable, str(TOOL), "preview", "--src", str(source),
                 "--out", str(output)],
                cwd=tmp, capture_output=True, text=True,
            )

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("positive numeric DUR constant", result.stderr)
            self.assertFalse((output / "sheet.jpg").exists())


if __name__ == "__main__":
    unittest.main()
