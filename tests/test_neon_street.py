import importlib.util, pathlib, unittest

SRC = pathlib.Path(__file__).resolve().parents[1] / "videos/neon-street-pixel/src/render.py"
spec = importlib.util.spec_from_file_location("neon_render", SRC)
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)


class NeonStreet(unittest.TestCase):
    def test_frame_size_and_scene_cuts(self):
        a, b, c = r.frame(1.0), r.frame(3.5), r.frame(6.5)
        self.assertEqual(a.size, (720, 720))
        self.assertEqual(len({a.tobytes(), b.tobytes(), c.tobytes()}), 3)

    def test_motion_within_scene(self):
        self.assertNotEqual(r.frame(3.0).tobytes(), r.frame(3.1).tobytes())


if __name__ == "__main__":
    unittest.main()
