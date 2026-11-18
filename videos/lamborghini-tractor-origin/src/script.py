"""lamborghini-tractor-origin: dialogue, exhibits, look. Rendered by videos/origin-kit/engine.py.
LINES: (speaker, text, scene). B = buyer (Fenrir), S = salesman (Orus). The last line is spoken to the viewer."""
LINES = [
    ("B", "Wait, Lamborghini made tractors?!", 1),
    ("S", "Welcome, sir. Yes. Ferruccio Lamborghini built tractors after the war.", 1),
    ("B", "Then why make supercars?", 2),
    ("S", "The story goes that he owned a Ferrari 250 GT, and its clutch kept failing.", 2),
    ("B", "So he complained?", 3),
    ("S", "He went to see Enzo Ferrari. The story says Enzo told him to stick to tractors.", 3),
    ("B", "And that was it?!", 4),
    ("S", "In 1963, he showed his first car, the 350 GTV, at the Turin Motor Show.", 4),
    ("B", "Is the story even true?", 5),
    ("S", "Historians disagree, sir. Some say Enzo never met him.", 5),
    ("B", "So a tractor maker built a Lamborghini.", 6),
    ("S", "Best revenge in car history, if it happened.", 6),
    ("S", "Did a Ferrari insult really create Lamborghini? Let them decide.", 6),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
DIRECTION = ("TTS this snappy comedy skit in a supercar showroom. The Salesman is calm, dry and completely deadpan, the same "
             "bored, polite tone on every line, never surprised. The Buyer is amazed from the very first word and gets more "
             "hooked with each answer: astonished on 'Wait, Lamborghini made tractors?!', eager, then gleeful on 'And that "
             "was it?!', then suspicious on 'Is the story even true?', then slowly impressed on the tractor maker line. "
             "On the last line the Salesman turns to the audience, still deadpan. Say '250 GT' as 'two fifty G T', '350 GTV' "
             "as 'three fifty G T V', and 1963 as 'nineteen sixty-three'. Ferruccio is 'feh-ROO-cho'. Quick timing, no long "
             "pauses.\n\n")
SPOKEN = {"250": "two fifty", "gt": "g t", "1963": "nineteen sixty three", "350": "three fifty", "gtv": "g t v"}
PHONES = {"ferruccio": "F EH R UW CH OW", "supercars": "S UW P ER K AA R Z"}
EXHIBITS = {
    'today':   dict(file='lambo_current.jpg', label='LAMBORGHINI TODAY', flip=True, plates=[(.684, .665, .764, .725)]),
    'tractor': dict(file='lambo_tractor.jpg', label='LAMBORGHINI TRACTOR', scale=.96),
    'ferrari': dict(file='ferrari_250gt.jpg', label='FERRARI 250 GT', crop=(0, .25, 1, .8), plates=[(.186, .632, .245, .668)]),
    'gtv':     dict(file='lambo_350gtv.jpg', label='LAMBORGHINI 350 GTV', flip=True, crop=(.02, .12, .9, .9), erase_out=[(0, .79, .316, 1)]),
}
SCENE_EXHIBIT = ['today', 'tractor', 'ferrari', 'gtv', 'ferrari', 'tractor']
CHIPS = {2: (1, 'tractors', 'TRACTORS FIRST: ABOUT 1948'), 4: (5, 'stick', 'THE STORY GOES...'),
         7: (7, 'Turin', '1963: TURIN MOTOR SHOW'), 9: (9, 'never', 'DISPUTED')}
PUNCH = [(0, 'tractors'), (1, 'tractors'), (3, 'failing'), (5, 'tractors'), (6, 'it'), (7, '1963'), (9, 'never'), (11, 'revenge')]
ODDITIES = [('giraffe', 'R'), ('penguin', 'L'), ('ufo', 'R'), ('flamingo', 'L'), ('cow_balloon', 'R'), ('llama', 'L')]
BRAND = dict(name='LAMBORGHINI', wall=((10, 10, 12), (34, 32, 30)), floor=((20, 20, 22), (6, 6, 8)), trim=(222, 178, 60),
             accent=(255, 196, 40), namecol=(232, 196, 96), panel=(24, 23, 22), hexes=True, sky=((255, 170, 90), (120, 160, 230)))
SALES = dict(skin='c99272', skin2='a8714f', hair='15110f', suit='141416', suit2='050506', shirt='f3f3f5', tie='e2b23c',
             pants='141416', shoe='111112', hairstyle='slick', lids=0.45, shades=True, pocket='ffc428', badge=(255, 196, 40))
HEADLINE = ["LAMBORGHINI", "MADE TRACTORS?!"]
THUMB_EXHIBIT = 'tractor'
FINAL = ["Comment below.", "Next: another brand's", "strange beginning."]
