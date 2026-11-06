"""Episode: why cold kills car batteries (13 s, cozy-room set, 135x240 native, x8).

Only this file changes per episode: headline, captions, beats, the car art,
speed/battery/light/camera curves.

    python episodes/cold-battery/episode.py preview out/cold-battery/sheet.png
    python episodes/cold-battery/episode.py render  out/cold-battery
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from pixelkit.core import tween_int                      # noqa: E402
from pixelkit.cozyroom import (CREAM, MAUVE, SALMON, TAN, WHITE,  # noqa: E402,F401
                               CozyEpisode, DEFAULT_CAR)

BEATS = dict(snow=1.6, night=2.6, dying=7.4, cat_wake=9.0, crank=9.8, crank_end=11.0,
             charge=11.0, go=11.6)


def car_speed(t):           # radians/s around the rug track
    if t < 2.0:
        return 1.3
    if t < BEATS["dying"]:
        return 1.1
    if t < 9.0:
        return 1.1 * (9.0 - t) / (9.0 - BEATS["dying"])
    if t < BEATS["go"]:
        return 0.0
    return min(1.3, (t - BEATS["go"]) * 1.5)


def battery(t):             # percent shown on HUD + monitor
    if t < BEATS["night"]:
        return 100 - 15 * t / BEATS["night"]
    if t < 9.6:
        return 85 - 77 * (t - BEATS["night"]) / (9.6 - BEATS["night"])
    if t < BEATS["charge"]:
        return 8
    return min(70, 8 + (t - BEATS["charge"]) * 40)


def light(t, step):         # palette-swap lighting mode
    if t < BEATS["night"]:
        return "day"
    if t < BEATS["night"] + 0.6:
        return "night" if step % 3 else "day"   # stepped flicker, no fades
    return "night"


def camera(t):              # integer world-y of the camera: locked, like the Reference
    return 3


EPISODE = dict(
    duration=13.0,
    headline=["COLD vs.", "BATTERY"],
    captions=[
        (0.0, 2.3, [("WON'T START ON A", CREAM), ("COLD MORNING?", SALMON)]),
        (2.3, 4.6, [("COLD SLOWS THE", CREAM), ("BATTERY CHEMISTRY", SALMON)]),
        (4.6, 7.4, [("SO IT DELIVERS", CREAM), ("LESS CURRENT...", SALMON)]),
        (7.4, 9.8, [("AND THICK COLD OIL", CREAM), ("NEEDS MORE TO CRANK", SALMON)]),
        (9.8, 11.4, [("LOW POWER, BIG LOAD", CREAM), ("= CLICK. NO START.", MAUVE)]),
        (11.4, 13.01, [("KEEP IT CHARGED.", TAN), ("PARK IT WARM.", CREAM)]),
    ],
    beats=BEATS,
    car_art=DEFAULT_CAR,
    car_speed=car_speed,
    battery=battery,
    light=light,
    camera=camera,
    holds=(3, 3, 2, 4, 3, 3, 2, 4, 3, 3, 3, 2),
)


def main(argv):
    cmd, out = argv[1], argv[2]
    ep = CozyEpisode(EPISODE)
    if cmd == "preview":
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        print(ep.preview(out))
    elif cmd == "render":
        os.makedirs(out, exist_ok=True)
        print(ep.render(os.path.join(out, "cold-battery.mp4"),
                        master=os.path.join(out, "cold-battery_master444.mp4"),
                        native_dir=os.path.join(out, "native")))
    else:
        raise SystemExit("usage: episode.py preview SHEET.png | render OUTDIR")


if __name__ == "__main__":
    main(sys.argv)
