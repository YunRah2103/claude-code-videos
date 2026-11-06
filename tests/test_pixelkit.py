import json
import os
import tempfile
import unittest

import numpy as np

from pixelkit import verify
from pixelkit.core import (T, BitmapFont, Canvas, Palette, PixelFont, StepClock, render,
                           rotsprite, scale2x, sprite)


class CoreTests(unittest.TestCase):
    def test_clock_holds_are_uneven_and_cover_all_frames(self):
        c = StepClock(2.0, 30, (3, 2, 4))
        self.assertEqual(len(c.step_of), 60)
        runs = np.bincount(c.step_of)
        self.assertEqual(list(runs[:6]), [3, 2, 4, 3, 2, 4])

    def test_scale2x_and_rotsprite_keep_exact_colours(self):
        a = sprite("abba\nbaab\nabba", {"a": 1, "b": 2})
        self.assertEqual(set(np.unique(scale2x(a))), {1, 2})
        r, _ = rotsprite(a, 30)
        self.assertTrue(set(np.unique(r)) <= {1, 2, T})

    def test_text_is_one_bit(self):
        for f in (PixelFont(size=10), BitmapFont()):
            c = Canvas(60, 12, 0)
            c.text(f, "CAR 42%", 1, 1, 5, outline_c=3)
            self.assertTrue(set(np.unique(c.a)) <= {0, 3, 5})

    def test_render_duplicates_steps_and_stays_in_palette(self):
        pal = Palette("pico8")
        clock = StepClock(1.0, 30, (3, 2, 4))

        def scene(step, t):
            c = Canvas(20, 32, 1)
            c.rect(step % 18, 4, 2, 2, 8)
            return c

        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "t.mp4")
            render(scene, clock, pal, out, scale=6, native_dir=os.path.join(d, "n"))
            info = verify.probe(out)
            self.assertEqual((info["w"], info["h"], info["n"]), (120, 192, 30))
            with open(os.path.join(d, "n", "frames.json")) as fh:
                self.assertEqual(json.load(fh)["step_of"], clock.step_of)
            self.assertLessEqual(verify.native_colours(os.path.join(d, "n")), 16)
            r = verify.analyse(out, block=6)
            self.assertLess(r["nonuni"], 0.5)
            self.assertGreater(r["held"], 40)


if __name__ == "__main__":
    unittest.main()
