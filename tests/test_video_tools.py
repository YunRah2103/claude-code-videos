"""Behaviour checks for context-saving helpers; no external API calls."""
import subprocess
import sys
import tempfile
import unittest
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/video.py"


class VideoToolsTest(unittest.TestCase):
    def cli(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(TOOL), *map(str, args)],
                              cwd=cwd or ROOT, text=True, capture_output=True)

    def test_failed_command_keeps_full_log_and_exit_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "logs/failure.log"
            result = self.cli("run", "--log", log, "--", sys.executable, "-c",
                              "print('first'); print('x'*20000); print('last'); raise SystemExit(7)")
            self.assertEqual(result.returncode, 7, result.stderr)
            self.assertLess(len(result.stdout), 5000)
            self.assertIn("last", result.stdout)
            self.assertIn("first", log.read_text())
            self.assertIn("x" * 20000, log.read_text())

    def test_successful_command_reports_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.cli("run", "--log", Path(tmp) / "ok.log", "--",
                              sys.executable, "-c", "print('ready')")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ready", result.stdout)

    def test_preview_runs_outside_repository_and_makes_sheet(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            result = self.cli("preview", "--out", Path(tmp) / "preview", "--times",
                              "1", "13.3", "34.5", cwd=tmp)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            files = list((Path(tmp) / "preview").glob("f_*.png"))
            self.assertEqual(len(files), 3)
            with Image.open(files[0]) as frame:
                self.assertEqual(frame.size, (1080, 1920))
            with Image.open(Path(tmp) / "preview/sheet.jpg") as sheet:
                self.assertEqual(sheet.size, (810, 510))

    def test_invalid_times_fail_before_rendering(self):
        with tempfile.TemporaryDirectory() as tmp:
            for time in ("-1", "38", "nan"):
                with self.subTest(time=time):
                    result = self.cli("preview", "--out", Path(tmp) / "preview",
                                      "--times", time)
                    self.assertNotEqual(result.returncode, 0)
            self.assertFalse((Path(tmp) / "preview/sheet.jpg").exists())

    def test_invalid_dur_fails_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            for dur in (0, -1):
                with self.subTest(dur=dur):
                    source = Path(tmp) / f"ep_{dur}/src"
                    source.mkdir(parents=True)
                    (source / "render.py").write_text(f"DUR = {dur}\n")
                    out = Path(tmp) / f"out_{dur}"
                    result = self.cli("preview", "--src", source, "--out", out)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("render.py must declare a positive numeric DUR constant", result.stderr)
                    self.assertFalse((out / "sheet.jpg").exists())

    def test_another_episode_uses_its_own_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "another-episode/src"
            shutil.copytree(ROOT / "videos/new-car-trap/src", source,
                            ignore=shutil.ignore_patterns("__pycache__"))
            render = source / "render.py"
            render.write_text(render.read_text().replace("DUR = 37.9", "DUR = 2.0"))
            result = self.cli("preview", "--src", source, "--out", Path(tmp) / "frames")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertTrue((Path(tmp) / "frames/sheet.jpg").exists())
            result = self.cli("preview", "--src", source, "--out", Path(tmp) / "bad",
                              "--times", "2.0")
            self.assertNotEqual(result.returncode, 0)

    def test_probe_missing_media_fails(self):
        result = self.cli("probe", "does-not-exist.mp4")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
