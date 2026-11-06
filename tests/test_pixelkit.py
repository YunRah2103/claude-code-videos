import json
import os
import tempfile
import unittest

import numpy as np

from pixelkit import verify
from pixelkit.core import (T, BitmapFont, Canvas, Palette, PixelFont, StepClock, curve_points,
                           render, rotate_nn, rotsprite, scale2x, shade, sprite, texture,
                           wobble_mask)


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


class OrganicTests(unittest.TestCase):
    def test_wobbled_shaded_prop_has_no_long_straight_edge(self):
        r = np.random.default_rng(0)
        pal = Palette()
        c = Canvas(80, 60, 5)
        texture(c.a, [6, 5, 4, 31], r, "grain", 0.2)
        a = shade(wobble_mask(60, 40, r, depth=1, seg=(3, 7)), [27, 28, 29, 30], line=25)
        texture(a, [27, 28, 29, 30], r, "weave", 0.06)
        c.blit(a, 9, 9)
        rgb = pal.to_rgb(c.a).astype(float)
        self.assertLessEqual(verify.straight_edges(rgb)[0], verify.MAX_EDGE)
        self.assertLessEqual(verify.largest_flat(rgb), verify.MAX_FLAT)

    def test_checks_catch_clean_rectangles(self):
        a = np.zeros((60, 60, 3))
        a[10:50, 10:50] = 200
        self.assertEqual(verify.straight_edges(a)[0], 40)
        self.assertGreater(verify.largest_flat(a), verify.MAX_FLAT)

    def test_rotate_nn_and_curves_stay_on_palette(self):
        s = rotate_nn(np.full((4, 12), 7, np.uint8), 30)
        self.assertTrue(set(np.unique(s)) <= {7, T})
        pts = curve_points([(0, 0), (10, 15), (20, 3)])
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            self.assertLessEqual(max(abs(x1 - x0), abs(y1 - y0)), 1)


if __name__ == "__main__":
    unittest.main()
