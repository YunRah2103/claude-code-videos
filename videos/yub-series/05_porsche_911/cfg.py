"""05 Porsche 911: 'Why is the engine in the wrong place?' Lines: (speaker, text, scene, buyer mood[, word, mood])."""
SLUG = 'porsche_911'
LINES = [
    ("B", "Your engine is in the wrong place!", 0, 'angry', 'wrong', 'point'),
    ("S", "Behind the rear axle. On purpose.", 0, 'shock'),
    ("B", "Who builds a car like that?!", 0, 'furious'),
    ("S", "Porsche. In the 911. Since 1963.", 0, None),
    ("B", "Sixty years and nobody fixed it?!", 1, 'furious'),
    ("S", "It debuted as the 901. Peugeot objected to the name.", 1, 'confused'),
    ("B", "Focus! Why the back?!", 1, 'angry'),
    ("S", "The engine's weight sits over the driven wheels. More traction.", 2, 'curious'),
    ("B", "And braking?", 2, 'curious'),
    ("S", "Porsche says it helps there too.", 2, 'impressed'),
    ("B", "But doesn't the tail swing out?!", 3, 'worried'),
    ("S", "Early ones had that reputation. Engineers kept taming it.", 3, None),
    ("B", "Did they ever try to replace it?", 4, 'curious'),
    ("S", "Reportedly, yes. With the front-engined 928.", 4, 'shock'),
    ("B", "And?!", 4, 'point'),
    ("S", "The 928 is gone. The 911 is still here.", 4, 'impressed'),
    ("B", "So it was never a mistake?", 5, 'deflated'),
    ("S", "Genius or mistake? Comment below.", 5, None),
]
DIRECTION = ("TTS this fast-paced comedy skit at a Porsche showroom. The Salesman is completely flat, calm and deadpan the "
             "whole time, same bored tone on every answer. Say 911 as 'nine eleven', 901 as 'nine oh one', 928 as 'nine "
             "twenty-eight', 1963 as 'nineteen sixty-three' and Porsche as 'POR-sha'. The Buyer is outraged from the first word "
             "that the engine sits behind the rear axle, shouts 'Focus! Why the back?!', gets curious about braking, worried "
             "about the tail, and finally deflates on 'So it was never a mistake?'. The Salesman's last line is asked straight "
             "to the audience, still deadpan. Snappy timing, no long pauses between lines.")
SPOKEN = {"911": "nine eleven", "901": "nine oh one", "928": "nine twenty eight", "1963": "nineteen sixty three",
          "frontengined": "front engined"}
DICT = {"engined": "EH N JH AH N D", "peugeot": "P UW ZH OW"}
HOLD = {5: 0.15}
GAPS = (0.08, 0.3, 0.6)
TEMPO = 1.05                     # voice sped up 5% (pitch kept) to land near 45 s
BRAND = dict(logo='porsche_911_logo.png', name='PORSCHE 911', accent=(190, 24, 32), wall=((22, 22, 24), (48, 48, 52)),
             floor=((72, 74, 78), (112, 114, 118)), panel=(34, 34, 38), ceil=(40, 40, 44), fascia=(244, 244, 246),
             logo_white=False, logo_white_on_dark=True)
SETS = [dict(kind='showroom', photo='901_red.jpg', fy=.6),
        dict(kind='gallery', photos=['901_white.jpg', '901_red.jpg'], labels=['1964', '1964'], fy=.6),
        dict(kind='track', photo='901_red.jpg', fy=.6),
        dict(kind='garage', photo='901_rear.jpg', fy=.55),
        dict(kind='office', photo='928.jpg', fy=.6),
        dict(kind='lot', photo='901_white.jpg', fy=.6)]
CLOSE = (3, 'Porsche')
CARDS = [dict(kind='photo', img='901_rear.jpg', label='1964 PORSCHE 901 / 911', at=(3, 'Porsche'), y=470),
         dict(kind='info', rows=(("Shown in 1963", 60, 'ink'), ("as the 901.", 60, 'ink'), ("Renamed: 911", 60, 'red')), at=(5, '901'), y=470),
         dict(kind='info', rows=(("Engine weight over", 56, 'ink'), ("the driven wheels", 56, 'ink'), ("= more traction", 60, 'red')), at=(7, 'weight'), until=(9, 'Porsche'), y=470),
         dict(kind='stamp', txt='BRAKES TOO', col=(40, 160, 80), at=(9, 'helps'), y=560),
         dict(kind='photo', img='901_engine.jpg', label='ENGINE: AT THE BACK', at=(10, 'tail'), y=470, rot=3),
         dict(kind='photo', img='928.jpg', label='PORSCHE 928 (FRONT ENGINE)', at=(13, '928'), until=(15, 'gone'), y=470),
         dict(kind='stamp', txt='STILL HERE', col=(40, 160, 80), at=(15, '911'), y=560)]
PUNCH = [((0, 'wrong'), .05), ((1, 'purpose'), .03), ((3, '1963'), .04), ((6, 'Focus'), .06), ((7, 'traction'), .04),
         ((13, '928'), .04), ((15, 'still'), .05)]
SHAKE = [(6, 'Focus')]
SFX = [((7, 'traction'), 'vroom', .3), ((10, 'swing'), 'screech', .2), ((15, 'gone'), 'poof', .3)]
ODDITY, ODD_S, ODD_DRIFT = 'jet_snail', 1.3, -4
ODD_X = [860, 870, 860, 880, 860, 870]
FINAL = [("Genius or mistake?", 80, 'tag'), ("Comment below.", 64, 'white'),
         ("Follow for more cars", 58, 'grey'), ("that broke the rules.", 58, 'grey')]
THUMB_T = (0, 'wrong', .3)
THUMB = [("THE ENGINE IS IN", 'white'), ("THE WRONG PLACE?!", 'tag')]
THUMB_PHOTO, THUMB_LABEL = '901_rear.jpg', 'PORSCHE 911, SINCE 1963'
