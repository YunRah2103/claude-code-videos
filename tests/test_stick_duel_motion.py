import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / 'videos' / 'stick-duel' / 'src'
sys.path.insert(0, str(SRC))


class FootSlideTests(unittest.TestCase):
    """Fighters must step, not glide: limit how far a planted foot slides across the fight."""

    def test_planted_feet_barely_slide(self):
        import render as r
        from PIL import Image, ImageDraw
        d = ImageDraw.Draw(Image.new('RGBA', (r.W, r.H)))
        total, prev = 0.0, {}
        for i in range(int(r.ACTION * r.FPS)):
            t = i / r.FPS
            z = r.piece(t, r.CZ)
            gy = (r.GROUND - r.piece(t, r.CY)) * z + 360
            for keys, cl in ((r.GK, 'green'), (r.RK, 'red')):
                r.draw_fighter(d, keys, t, cl, z, gy)
                joints, _ = r.LASTJ[cl]
                idx = max((7, 9), key=lambda j: joints[j][1])
                foot = joints[idx]
                grounded = abs(foot[1] - gy) < 6
                if grounded and cl in prev and prev[cl][0] == idx and prev[cl][2]:
                    total += abs(foot[0] - prev[cl][1])
                prev[cl] = (idx, foot[0], grounded)
        # before the stepping fix this was ~1800 px; stepping keeps it near 600 px
        self.assertLess(total, 900)

    def test_fast_ground_dash_leaves_the_ground(self):
        import render as r
        _, y, *_ = r.fighter_state(r.RK, 1.85)   # 1.8 -> 1.9 s is a 213 px dash in 0.1 s
        self.assertLess(y, -10)


if __name__ == '__main__':
    unittest.main()
