"""Gamer-room wallpaper loop: 10 s, 135x240 native, x8, no captions.

    python episodes/gamer-room/episode.py preview out/gamer-room/sheet.png
    python episodes/gamer-room/episode.py render  out/gamer-room
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from PIL import Image                                   # noqa: E402

from pixelkit.cozyroom import PAL                       # noqa: E402
from pixelkit.gameroom import GameRoom, W, H            # noqa: E402


def main(argv):
    cmd, out = argv[1], argv[2]
    scene = GameRoom()
    if cmd == "preview":
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        times = (0.0, 2.0, 3.5, 5.0, 8.4)
        steps = [scene.clock.step_of[int(tt * 30)] for tt in times]
        ims = [Image.fromarray(PAL.to_rgb(scene.frame(s, scene.clock.t(s)).a)) for s in steps]
        sheet = Image.new("RGB", (W * len(ims), H))
        for i, im in enumerate(ims):
            sheet.paste(im, (i * W, 0))
        sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(out)
        print(out)
    elif cmd == "render":
        os.makedirs(out, exist_ok=True)
        print(scene.render(os.path.join(out, "gamer-room.mp4"),
                           master=os.path.join(out, "gamer-room_master444.mp4"),
                           native_dir=os.path.join(out, "native")))
    else:
        raise SystemExit("usage: episode.py preview SHEET.png | render OUTDIR")


if __name__ == "__main__":
    main(sys.argv)
