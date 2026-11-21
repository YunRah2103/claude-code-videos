"""03 Bugatti Veyron (2005): 'The car that lost money on every sale'. Lines: (speaker, text, scene, buyer mood[, word, mood])."""
SLUG = 'bugatti_veyron'
LINES = [
    ("B", "Over a million euros for ONE car?!", 0, 'furious', 'ONE', 'shock'),
    ("S", "And they reportedly still lost money on it.", 0, 'shock'),
    ("B", "Lost money?! At that price?!", 0, 'furious'),
    ("S", "The Bugatti Veyron. 2005.", 0, None),
    ("B", "What do you even get?", 1, 'point'),
    ("S", "1,001 horsepower.", 1, 'shock'),
    ("B", "A thousand and one?!", 1, 'furious'),
    ("S", "Top speed: 253 miles per hour.", 1, 'shock'),
    ("B", "How is that even possible?!", 2, 'confused'),
    ("S", "Sixteen cylinders. Four turbochargers.", 2, 'shock'),
    ("B", "So how much did they lose?", 3, 'curious'),
    ("S", "Analysts estimated millions of euros. Per car.", 3, 'shock'),
    ("B", "Per CAR?!", 3, 'furious'),
    ("S", "Bugatti said those numbers weren't plausible.", 3, 'cross'),
    ("B", "Why would anyone build that?!", 4, 'confused'),
    ("S", "To build the car nobody else could.", 4, 'impressed'),
    ("B", "Would you buy one?", 5, 'deflated'),
    ("S", "Genius flex, or expensive mistake? Comment below.", 5, None),
]
DIRECTION = ("TTS this fast-paced comedy skit at a Bugatti showroom. The Salesman is completely flat, calm and deadpan the "
             "whole time, same bored tone on every answer, even about huge numbers. Say 2005 as 'two thousand five', 1,001 as "
             "'one thousand and one', 253 as 'two hundred fifty-three', and Veyron as 'vay-ron'. The Buyer can't believe the "
             "price from the first word and escalates: screaming 'A thousand and one?!' and 'Per CAR?!', then goes quiet and "
             "almost tempted on 'Would you buy one?'. The Salesman's last line is asked straight to the audience, still deadpan. "
             "Snappy timing, no long pauses between lines.")
SPOKEN = {"2005": "two thousand five", "1001": "one thousand and one", "253": "two hundred fifty three"}
DICT = {"veyron": "V EY R AA N", "turbochargers": "T ER B OW CH AA R JH ER Z", "bugatti": "B UW G AA T IY"}
HOLD = {5: 0.3, 7: 0.3, 11: 0.2}
GAPS = (0.14, 0.42, 0.75)
BRAND = dict(logo='bugatti_logo.png', name='BUGATTI', accent=(200, 20, 40), wall=((24, 26, 34), (44, 46, 58)),
             floor=((40, 42, 50), (78, 80, 90)), panel=(34, 36, 46), ceil=(18, 18, 24), fascia=(30, 32, 40),
             logo_white=False, logo_white_on_dark=False)
SETS = [dict(kind='showroom', photo='veyron_front.jpg', fy=.62),
        dict(kind='track', photo='veyron_side.jpg', fy=.55),
        dict(kind='factory', photo='veyron_rear.jpg', fy=.45),
        dict(kind='office', photo='veyron_side.jpg', fy=.55),
        dict(kind='vault', photo='veyron_front.jpg', fy=.62),
        dict(kind='gallery', photos=['veyron_front.jpg', 'veyron_side.jpg'], labels=['2005', '407 KM/H'], fy=.6)]
CLOSE = (3, 'Bugatti')
CARDS = [dict(kind='tag', txt='€1,000,000+', sub='2005 BUGATTI VEYRON', at=(2, 'price'), until=(3, 'Bugatti', -.1), y=560),
         dict(kind='photo', img='veyron_front.jpg', label='2005 BUGATTI VEYRON 16.4', at=(3, 'Bugatti'), y=470),
         dict(kind='stat', big='1,001 HP', sub='1,001 PS, Veyron 16.4', at=(5, '1,001'), until=(7, 'Top'), y=420),
         dict(kind='stat', big='253 MPH', sub='407 km/h, type-approved', at=(7, '253'), y=420, col=(255, 120, 120)),
         dict(kind='info', rows=(("16 cylinders", 64, 'ink'), ("4 turbochargers", 64, 'red')), at=(9, 'Sixteen'), y=640),
         dict(kind='info', rows=(("Analysts' estimate:", 54, 'ink'), ("millions lost per car", 54, 'ink'), ("(reported)", 50, 'red')), at=(11, 'Analysts'), until=(13, 'Bugatti'), y=460),
         dict(kind='stamp', txt='DISPUTED', at=(13, 'Bugatti'), y=520),
         dict(kind='photo', img='veyron_rear.jpg', label='16 CYLINDERS, 1 CAR', at=(15, 'nobody'), y=470, rot=3)]
PUNCH = [((0, 'ONE'), .05), ((2, 'Lost'), .04), ((5, '1,001'), .05), ((6, 'thousand'), .05), ((7, '253'), .05),
         ((9, 'Sixteen'), .03), ((12, 'CAR'), .06)]
SHAKE = [(12, 'CAR')]
SFX = [((7, '253'), 'vroom', .3), ((11, 'millions'), 'cha_ching', .3), ((12, 'CAR'), 'crash', .15)]
ODDITY, ODD_S, ODD_DRIFT = 'pig', 1.25, 0
ODD_X = [860, 870, 860, 860, 850, 860]
FINAL = [("Genius flex or", 74, 'tag'), ("expensive mistake?", 74, 'tag'), ("Comment below.", 64, 'white'),
         ("Next: the tractor maker", 58, 'grey'), ("who took on Ferrari.", 58, 'grey')]
THUMB_T = (12, 'CAR', .2)
THUMB = [("IT LOST MONEY", 'white'), ("ON EVERY SALE?!", 'tag')]
THUMB_PHOTO, THUMB_LABEL = 'veyron_front.jpg', '2005 BUGATTI VEYRON'
