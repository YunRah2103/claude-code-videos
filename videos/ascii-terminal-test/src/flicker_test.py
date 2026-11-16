"""Held-camera flicker test: camera frozen at T, car/wheel/floor keep animating; 40 frames after pre-roll."""
import os
import sys
os.environ['FREEZE_CAM'] = sys.argv[1] if len(sys.argv) > 1 else '2.5'
import numpy as np
import render as R

fl = [m['flicker'] for _, _, m in R.frames(range(48, 100), set(range(60, 100)))]
print(f"held camera @{os.environ['FREEZE_CAM']}s: visible glyph changes {100 * np.mean(fl):.2f}% of lit cells per frame")
