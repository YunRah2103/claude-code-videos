# ascii-terminal-test
5 s silent loop: the supplied halftone car photo (`assets/car_src.jpg`) re-drawn as an ASCII/halftone
grid (10x18 cells, 2 dots per cell + Sobel outline glyphs `/ \ | _`), 120 fps internal with 4-sub-frame
temporal supersampling, EMA 0.6 + hysteresis, periodic C2 camera spline tuned for even screen motion.
Needs numpy, numba, opencv-python-headless, scipy, Pillow, ffmpeg. Renders go to `out/` (never committed).
