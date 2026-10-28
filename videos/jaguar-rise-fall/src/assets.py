"""Build the Jaguar episode's pixel assets into src/assets/. Run: python assets.py

Generic cars and signs only: no logos, no badges, no trademarked text.
Garage pixel scale is 9 px (S). Gauge needles are full-canvas, pointing up at 0 deg,
so rotate them about the image centre.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from PIL import Image, ImageDraw
from pixanim.guy import guy
from pixanim.car import car
from pixanim.dash import _gauge_face
from pixanim.grid import Grid, text_width, up
from pixanim import sprites as sp

OUT = os.path.join(HERE, 'assets')
S = 9

# (expression, arms, legs) for the presenter, named for the beat they serve
POSES = {
    'wow':     ('wow', 'cheer1', 'stand'),
    'point':   ('smile', 'point', 'stand'),
    'shrug':   ('smirk', 'shrug', 'stand'),
    'think':   ('think', 'think', 'stand'),
    'shock':   ('shock', 'shock', 'stand'),
    'cheer':   ('happy', 'cheer2', 'stand'),
    'present': ('smile', 'present', 'stand'),
    'sad':     ('sad', 'down', 'stand'),
    'hips':    ('smirk', 'hips', 'stand'),
    'wave':    ('grin', 'wave2', 'stand'),
}


def board(text, s=6, body='#f4f1e8', ink='#1a1a2e', edge='#1a1a2e'):
    """Plain sign board with a dark edge: used for the nationalised sign and similar."""
    w, h = text_width(text) + 12, 15
    g = Grid(w, h)
    g.rect(0, 0, w-1, h-1, edge)
    g.rect(1, 1, w-2, h-2, body)
    g.text(6, 4, text, ink)
    return up(g.image(outline=False), s)


def speech(text, s=6, col='#1a1a2e'):
    """White meme bubble with a dark outline and a small tail."""
    w, h = text_width(text) + 10, 15
    g = Grid(w, h + 4)
    g.rect(1, 0, w-2, h-1, '#ffffff')
    g.rect(0, 1, w-1, h-2, '#ffffff')
    g.rect(2, h, 4, h + 2, '#ffffff')
    g.text(5, 4, text, col)
    return up(g.image(), s)


def gauge(label, red_from, needle_col, name_face, name_needle, r=95):
    """Round dial: chrome bezel, ticks, red zone from `red_from`, and a needle layer."""
    size = 2 * r + 24
    c = size // 2
    face = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    _gauge_face(ImageDraw.Draw(face), c, c, r, red_from=red_from, label=label)
    face.save(os.path.join(OUT, name_face))
    needle = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(needle)
    d.polygon([(c - 3, c), (c + 3, c), (c, c - r + 16)], fill=needle_col)
    d.ellipse((c - 7, c - 7, c + 7, c + 7), fill=needle_col)
    needle.save(os.path.join(OUT, name_needle))
    return size


def main():
    os.makedirs(OUT, exist_ok=True)
    made = []

    def save(img, name):
        img.save(os.path.join(OUT, name))
        made.append((name, img.size))

    # presenter poses at garage scale (48x60 sprite x 9)
    for key, (expr, arms, legs) in POSES.items():
        save(up(guy(expr, arms, legs), S), f'presenter_{key}.png')

    # cars: hook (red sports), dream E-Type (blue), X-Type (silver saloon)
    save(up(car('red'), S), 'car_hook_red.png')
    save(up(car('blue'), S), 'car_etype_blue.png')
    save(up(car('silver'), S), 'car_xtype_silver.png')
    save(car('red'), 'car_marker.png')                # native 90x38, for the progress bar

    # signs and labels
    save(board('NATIONALISED'), 'sign_nationalised.png')
    save(up(sp.badge('DEAD END', body='#ffd23f', ink='#d6303a'), 7), 'sign_dead_end.png')
    save(up(sp.badge('NEXT EPISODE'), 6), 'sign_next_episode.png')
    save(sp.arrow().resize((13 * S, 14 * S), Image.NEAREST), 'arrow_cost.png')

    # meme jokes and dream bubble
    save(speech('LOL'), 'bubble_lol.png')
    save(speech('HA HA'), 'bubble_haha.png')
    save(speech('LMAO'), 'bubble_lmao.png')
    save(up(sp.bubble(dots=0), S), 'bubble_dream.png')

    # sparkles and stars for pop-ins
    save(up(sp.sparkle(1), 5), 'sparkle.png')
    save(up(sp.star(), 6), 'star.png')

    # dashboard: quality gauge in the nationalised scene, rev counter in the corner
    q = gauge('QUALITY', 2, '#e0303a', 'quality_gauge_face.png', 'quality_gauge_needle.png')
    r = gauge('RPM', 6, '#e0303a', 'rpm_gauge_face.png', 'rpm_gauge_needle.png')

    # progress bar track: 120 px grid x 9 = 1080 wide, a dark rail with yellow ticks
    g = Grid(120, 6)
    g.rect(0, 2, 119, 3, '#2a2d3a')
    for x in range(0, 120, 12):
        g.rect(x, 0, x, 5, '#ffd23f')
    save(up(g.image(outline=False), S), 'progress_track.png')

    for name, size in made:
        print(f'{name:28s} {size[0]}x{size[1]}')
    print(f'quality gauge {q}px, rpm gauge {r}px')


if __name__ == '__main__':
    main()
