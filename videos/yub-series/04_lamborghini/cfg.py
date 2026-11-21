"""04 Lamborghini: 'How an angry tractor maker created a supercar brand'. Lines: (speaker, text, scene, buyer mood[, word, mood])."""
SLUG = 'lamborghini'
LINES = [
    ("B", "Lamborghini started out making TRACTORS?!", 0, 'furious', 'TRACTORS', 'shock'),
    ("S", "Ferruccio Lamborghini built tractors. From 1948.", 0, 'shock'),
    ("B", "Then why make supercars?!", 0, 'confused'),
    ("S", "He owned a Ferrari. And he wasn't happy.", 0, None),
    ("B", "What was wrong with it?", 1, 'curious'),
    ("S", "The story goes, the clutch kept failing.", 1, None),
    ("B", "So he fixed it himself?", 1, 'point'),
    ("S", "Reportedly, it was the same clutch as in his tractors.", 1, 'shock'),
    ("B", "Then what happened?!", 2, 'angry'),
    ("S", "The story goes, Enzo Ferrari told him to stick to tractors.", 2, 'furious'),
    ("B", "He did NOT!", 2, 'furious'),
    ("S", "Nobody can prove it. But Ferruccio built his own car.", 2, 'impressed'),
    ("B", "A tractor guy versus Ferrari?!", 3, 'shock'),
    ("S", "He already knew how to build machines.", 3, None),
    ("B", "When was this?!", 4, 'point'),
    ("S", "1963. Automobili Lamborghini.", 4, 'impressed'),
    ("B", "And the tractors?", 5, 'curious'),
    ("S", "Still made today. Under another owner.", 5, 'impressed'),
    ("S", "Legend or myth? Tell me in the comments.", 5, None),
]
DIRECTION = ("TTS this fast-paced comedy skit at a Lamborghini showroom. The Salesman is completely flat, calm and deadpan the "
             "whole time, telling the origin story like it's a boring fact. Say 1948 as 'nineteen forty-eight', 1963 as "
             "'nineteen sixty-three', Ferruccio as 'feh-ROO-cho', Enzo as 'EN-tso' and Automobili as 'auto-MO-bee-lee'. The Buyer "
             "is outraged from the first word that Lamborghini made tractors, shouts 'He did NOT!', is stunned at 'A tractor guy "
             "versus Ferrari?!', then calms into curiosity. The Salesman's last line is asked straight to the audience after a "
             "short beat, still deadpan. Snappy timing, no long pauses between lines.")
SPOKEN = {"1948": "nineteen forty eight", "1963": "nineteen sixty three"}
DICT = {"ferruccio": "F ER UW CH OW", "automobili": "AO T OW M OW B IY L IY", "lamborghini": "L AE M B ER G IY N IY",
        "supercars": "S UW P ER K AA R Z", "enzo": "EH N Z OW", "ferrari": "F ER AA R IY"}
HOLD = {1: 0.15, 9: 0.3, 15: 0.3}
GAPS = (0.12, 0.38, 0.7)
BRAND = dict(logo='lamborghini_logo.png', name='LAMBORGHINI', accent=(214, 176, 84), wall=((14, 14, 16), (36, 36, 40)),
             floor=((150, 152, 156), (200, 202, 204)), panel=(28, 28, 32), ceil=(20, 20, 22), fascia=(236, 222, 180),
             logo_white=False, logo_white_on_dark=True)
SETS = [dict(kind='showroom', photo='350gt_blue.jpg', fy=.6),
        dict(kind='garage', photo='tractor_1965.jpg', fy=.5),
        dict(kind='office', title='THE STORY GOES...', bars=[], photo='350gt_1965.jpg', fy=.6),
        dict(kind='farm', photo='tractor_1965.jpg', fy=.5),
        dict(kind='factory', photo='350gt_1965.jpg', fy=.6),
        dict(kind='gallery', photos=['tractor_1951.jpg', '350gt_blue.jpg'], labels=['TRACTOR', '350 GT'], fy=.55)]
CLOSE = (3, 'owned')
CARDS = [dict(kind='photo', img='tractor_1965.jpg', label='LAMBORGHINI TRACTOR, 1965', at=(3, 'owned'), y=470),
         dict(kind='info', rows=(("THE STORY GOES:", 54, 'red'), ("the clutch", 60, 'ink'), ("kept failing", 60, 'ink')), at=(5, 'story'), until=(7, 'Reportedly'), y=470),
         dict(kind='stamp', txt='SAME CLUTCH?', col=(230, 150, 30), at=(7, 'clutch'), y=560),
         dict(kind='info', rows=(("THE STORY GOES:", 54, 'red'), ('"Stick to tractors."', 60, 'ink'), ("Never proven.", 54, 'red')), at=(9, 'Enzo'), until=(11, 'Nobody'), y=470),
         dict(kind='stamp', txt='UNPROVEN', at=(11, 'Nobody'), y=520),
         dict(kind='stat', big='1963', sub='Automobili Lamborghini founded', at=(15, '1963'), y=420, col=(214, 176, 84)),
         dict(kind='photo', img='350gt_1965.jpg', label='LAMBORGHINI 350 GT, 1965', at=(17, 'Still'), y=470, rot=3)]
PUNCH = [((0, 'TRACTORS'), .05), ((2, 'supercars'), .04), ((7, 'same'), .04), ((9, 'stick'), .05), ((10, 'NOT'), .06),
         ((12, 'versus'), .04), ((15, '1963'), .05)]
SHAKE = [(10, 'NOT')]
SFX = [((9, 'stick'), 'thump', .4), ((10, 'NOT'), 'crash', .15), ((15, '1963'), 'vroom', .3)]
ODDITY, ODD_S, ODD_DRIFT = 'chicken_tractor', 1.2, -14
ODD_X = [900, 910, 900, 910, 900, 910]
FINAL = [("Legend or myth?", 80, 'tag'), ("Tell me in the comments.", 60, 'white'),
         ("Next: why the 911's engine", 56, 'grey'), ("is in the 'wrong' place.", 56, 'grey')]
THUMB_T = (0, 'TRACTORS', .3)
THUMB = [("FROM TRACTORS", 'white'), ("TO SUPERCARS?!", 'tag')]
THUMB_PHOTO, THUMB_LABEL = 'tractor_1965.jpg', 'LAMBORGHINI TRACTOR'
