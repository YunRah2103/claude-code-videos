"""02 Ford Mustang Mach-E: 'Is it really a Mustang?' Lines: (speaker, text, scene, buyer mood[, word, mood])."""
SLUG = 'mach_e'
LINES = [
    ("B", "Who put a Mustang badge on an electric SUV?!", 0, 'angry', 'electric', 'furious'),
    ("S", "Ford did. In 2019.", 0, 'shock'),
    ("B", "A Mustang is a muscle car! It needs a roar!", 0, 'furious'),
    ("S", "This one hums. It's the Mach-E.", 0, None),
    ("B", "Mustangs have been two-door cars since 1964!", 1, 'point'),
    ("S", "And in 2019, the family grew. First time in 55 years.", 1, 'shock'),
    ("B", "Fine. Is it at least fast?", 2, 'cross'),
    ("S", "The GT Performance Edition makes 480 horsepower.", 2, 'shock'),
    ("B", "And zero to sixty?", 2, 'curious'),
    ("S", "Ford says 3.5 seconds.", 2, 'impressed'),
    ("B", "That's... actually quick.", 2, 'impressed'),
    ("B", "But where's the engine roar?!", 3, 'furious'),
    ("S", "Electric motors. No roar.", 3, 'worried'),
    ("B", "Purists must hate this!", 4, 'angry'),
    ("S", "Some did. Ford built it anyway.", 4, 'cross'),
    ("B", "So is it a real Mustang or not?", 5, 'confused'),
    ("S", "Mustang or not? Tell me in the comments.", 5, None),
]
DIRECTION = ("TTS this fast-paced comedy skit at a Ford dealership. The Salesman is completely flat, calm and deadpan the whole "
             "time, same bored tone on every answer. Say 2019 as 'twenty nineteen', 1964 as 'nineteen sixty-four', 55 as "
             "'fifty-five', 480 as 'four hundred eighty', 3.5 as 'three point five', Mach-E as 'Mack E' and GT as 'G T'. The Buyer "
             "storms in already angry that an electric SUV wears the Mustang badge, escalates to shouting, goes quiet and "
             "grudgingly impressed on 'That's... actually quick.', then shouts again about the roar, and ends confused. The "
             "Salesman's last line is asked straight to the audience, still deadpan. Snappy timing, no long pauses between lines.")
SPOKEN = {"2019": "twenty nineteen", "1964": "nineteen sixty four", "55": "fifty five", "480": "four hundred eighty",
          "35": "three point five", "mache": "mack e", "suv": "s u v", "gt": "g t", "twodoor": "two door"}
DICT = {"mustangs": "M AH S T AE NG Z"}
HOLD = {7: 0.2, 9: 0.3}
GAPS = (0.12, 0.4, 0.7)
BRAND = dict(logo='ford_logo.png', name='FORD', accent=(22, 70, 160), wall=((214, 222, 234), (236, 240, 246)),
             floor=((60, 64, 74), (100, 104, 114)), panel=(226, 232, 242), ceil=(232, 236, 242), fascia=(250, 250, 252),
             logo_white=False, logo_white_on_dark=False)
SETS = [dict(kind='showroom', photo='mache_2021_show.jpg', fy=.6),
        dict(kind='gallery', photos=['mustang_1965.jpg', 'mache_2021_red.jpg'], labels=['1965', '2021'], fy=.6),
        dict(kind='track', photo='mache_2021_red.jpg', fy=.6),
        dict(kind='charging', photo='mache_2022_black.jpg', fy=.62),
        dict(kind='office', photo='mache_2021_red.jpg', fy=.6),
        dict(kind='lot', photo='mache_2021_show.jpg', fy=.6)]
CLOSE = (3, 'hums')
CARDS = [dict(kind='photo', img='mache_2021_red.jpg', label='FORD MUSTANG MACH-E', at=(3, 'hums'), y=470),
         dict(kind='info', rows=(("Mustang family:", 56, 'ink'), ("first new member", 56, 'ink'), ("in 55 years", 60, 'red')), at=(5, 'First'), y=650),
         dict(kind='stat', big='480 HP', sub='GT Performance Edition', at=(7, '480'), until=(9, 'Ford'), y=420),
         dict(kind='stat', big='3.5 s', sub='0-60 mph (Ford estimate)', at=(9, '3.5'), y=420, col=(120, 220, 255)),
         dict(kind='stamp', txt='NO ROAR', at=(12, 'No'), y=600),
         dict(kind='photo', img='mustang_1965.jpg', label='1965 FORD MUSTANG', at=(13, 'Purists'), y=470, rot=3)]
PUNCH = [((0, 'electric'), .04), ((2, 'roar'), .05), ((5, '55'), .04), ((7, '480'), .05), ((9, '3.5'), .05), ((11, 'roar'), .05)]
SHAKE = [(11, 'roar')]
SFX = [((9, '3.5'), 'vroom', .25), ((12, 'No'), 'buzzer', .2)]
ODDITY, ODD_S, ODD_DRIFT = 'pony', 1.25, 0
ODD_X = [870, 880, 870, 880, 870, 880]
FINAL = [("Mustang or not?", 80, 'tag'), ("Tell me in the comments.", 60, 'white'),
         ("Next: the car that lost", 60, 'grey'), ("money on every sale.", 60, 'grey')]
THUMB_T = (4, 'since', .1)
THUMB = [("IS THIS REALLY", 'white'), ("A MUSTANG?!", 'tag')]
THUMB_PHOTO, THUMB_LABEL = 'mache_2021_red.jpg', 'ELECTRIC. FOUR DOORS.'
