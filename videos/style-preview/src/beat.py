"""Shared beat for all 6 styles (pure python, imported by Blender too)."""
import math
FPS, SEG = 30, 4.0
N = int(FPS * SEG)            # 120 frames per style
RAMP, DRAG_AT = 2.4, 2.5      # counter 100->200 over RAMP s, DRAG x4 pops at DRAG_AT

def speed(t):
    """km/h; out-quad so the counter moves from the very first frame."""
    u = min(max(t / RAMP, 0.0), 1.0)
    return 100 + 100 * (1 - (1 - u) ** 2)

def drag(t):
    return (speed(t) / 100.0) ** 2

def loop_speed(t):
    """Style 3: periodic 100 -> 200 -> 100 over SEG so the clip loops seamlessly."""
    p = (t % SEG) / SEG
    if p < 0.55:   u = 0.5 - 0.5 * math.cos(math.pi * p / 0.55)
    elif p < 0.75: u = 1.0
    else:          u = 0.5 + 0.5 * math.cos(math.pi * (p - 0.75) / 0.25)
    return 100 + 100 * u

def wheel_angle(i, rad_per_frame_at_100=0.42, sp=speed, fps=FPS):
    """Cumulative wheel angle at frame i (stylised: slower than real to avoid strobing)."""
    return sum(rad_per_frame_at_100 * sp(k / fps) / 100 for k in range(i))
