"""toyota-loom-origin: dialogue, exhibits, look. Rendered by videos/origin-kit/engine.py."""
LINES = [
    ("B", "Wait, my Toyota's company made looms?!", 1),
    ("S", "Welcome, sir. Toyota started with weaving looms.", 1),
    ("B", "Looms?!", 2),
    ("S", "Sakichi Toyoda built an automatic loom in 1924. The Type G.", 2),
    ("B", "So how did looms become cars?", 3),
    ("S", "His son, Kiichiro, started an automobile department inside the loom company in 1933.", 3),
    ("B", "Where did the money come from?", 4),
    ("S", "The loom patent rights were sold to a British company in 1929. The money reportedly went to car research.", 4),
    ("B", "And the name? Toyoda?", 5),
    ("S", "Toyoda became Toyota. Toyota Motor Company was established in 1937.", 5),
    ("B", "So the biggest carmaker started with thread.", 6),
    ("S", "With looms, sir. Please don't say thread.", 6),
    ("S", "Which car brand has the strangest beginning? Let them decide.", 6),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
DIRECTION = ("TTS this snappy comedy skit in a car showroom. The Salesman is calm, precise and completely deadpan, the same "
             "polite flat tone on every line. The Buyer is baffled from the first word: astonished on 'Wait, my Toyota's "
             "company made looms?!', near-shouting 'Looms?!', then curious, then smug on 'So the biggest carmaker started "
             "with thread.' The Salesman's 'Please don't say thread' is quietly offended but still flat. On the last line the "
             "Salesman turns to the audience. Toyoda is 'toy-OH-da', Toyota is 'toy-OH-ta', Sakichi is 'SAH-kee-chee', "
             "Kiichiro is 'kee-EE-chee-roh'. Say the years as 'nineteen twenty-four', 'nineteen thirty-three', 'nineteen "
             "twenty-nine' and 'nineteen thirty-seven'. Quick timing, no long pauses.\n\n")
SPOKEN = {"1924": "nineteen twenty four", "1933": "nineteen thirty three", "1929": "nineteen twenty nine",
          "1937": "nineteen thirty seven"}
PHONES = {"kiichiro": "K IY IY CH IY R OW", "sakichi": "S AA K IY CH IY"}
EXHIBITS = {
    'today': dict(file='toyota_current.jpg', label='TOYOTA TODAY', crop=(.0, .15, 1, .92)),
    'loom':  dict(file='type_g_loom.jpg', label='TYPE G AUTOMATIC LOOM', crop=(.08, .06, 1, .86), erase=[(.785, .48, 1, .74)]),
    'aa':    dict(file='toyota_aa.jpg', label='AN EARLY TOYOTA', crop=(.02, .17, .92, .875), keep=[(.138, .6, .289, .9), (.788, .668, .909, .89)]),
}
SCENE_EXHIBIT = ['today', 'loom', 'loom', 'loom', 'aa', 'today']
CHIPS = {3: (3, 'G', 'TYPE G: 1924'), 5: (5, '1933', '1933: CAR DEPARTMENT'), 7: (7, 'research', '1929: PATENT SOLD'),
         9: (9, '1937', 'TOYODA → TOYOTA, 1937')}
PUNCH = [(0, 'looms'), (2, 'Looms'), (3, 'G'), (5, '1933'), (7, 'British'), (9, 'Toyota'), (10, 'thread'), (11, 'thread')]
ODDITIES = [('octopus', 'R'), ('cat', 'L'), ('cow_balloon', 'R'), ('dino', 'L'), ('pigeon', 'R'), ('snowman', 'L')]
BRAND = dict(name='TOYOTA', wall=((236, 238, 242), (200, 204, 212)), floor=((40, 44, 52), (14, 16, 20)), trim=(214, 22, 36),
             accent=(235, 10, 30), namecol=(204, 16, 30), panel=(226, 228, 233), hexes=False, sky=((120, 190, 255), (250, 210, 160)))
SALES = dict(skin='e8c09a', skin2='c99c76', hair='121216', suit='4a4f58', suit2='33373e', shirt='f7f7fa', tie='d61624',
             pants='3c4048', shoe='1a1a1c', hairstyle='part', lids=0.5, glasses=True, frame='1a1a1e', badge=(214, 22, 36))
HEADLINE = ["TOYOTA", "MADE LOOMS?!"]
THUMB_EXHIBIT = 'loom'
FINAL = ["Comment below.", "Next: another brand's", "strange beginning."]
