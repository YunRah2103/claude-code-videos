import importlib.util, json, tempfile, unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "videos/gold-engine-bay/src/timing.py"
spec = importlib.util.spec_from_file_location("gold_timing", SRC)
timing = importlib.util.module_from_spec(spec); spec.loader.exec_module(timing)


class GoldTiming(unittest.TestCase):
    def test_estimate_rate_and_beat_order(self):
        words, _ = timing.estimate()
        span = words[-1]["e"] - words[0]["s"]
        self.assertAlmostEqual(len(words) / span, 2.7, delta=0.15)
        with tempfile.TemporaryDirectory() as d:
            timing.OUT = Path(d) / "t.json"
            timing.build(words, "test")
            b = json.load(open(timing.OUT))["beats"]
        order = ["open", "push", "reveal", "v12", "heat", "carbon", "protect", "gold", "infrared",
                 "lined", "about", "grams", "question", "poll", "outro", "end"]
        self.assertEqual([b[k] for k in order], sorted(b[k] for k in order))

    def test_aligned_words_move_beats(self):
        words, _ = timing.estimate()
        shifted = [[{"w": w["w"], "s": w["s"] + 1, "e": w["e"] + 1} for w in words]]   # align.py shape
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "w.json"; json.dump(shifted, open(p, "w"))
            timing.OUT = Path(d) / "t.json"
            timing.build(*timing.from_words(p))
            t = json.load(open(timing.OUT))
        self.assertAlmostEqual(t["beats"]["grams"], words[[timing.key(w["w"]) for w in words].index("16")]["s"] + 0.9, 3)


if __name__ == "__main__":
    unittest.main()
