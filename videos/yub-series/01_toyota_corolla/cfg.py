"""01 Toyota Corolla: 'Why is the most boring car the best seller?' Lines: (speaker, text, scene, buyer mood[, word, mood])."""
SLUG = 'toyota_corolla'
LINES = [
    ("B", "You're telling me THIS is the best-selling car on Earth?!", 0, 'angry', 'THIS', 'point'),
    ("S", "The Toyota Corolla. Yes.", 0, 'shock'),
    ("B", "I expected a supercar! Something exciting!", 0, 'furious'),
    ("S", "Supercars are rare. Corollas are everywhere.", 0, None),
    ("B", "How many are we talking?", 1, 'point'),
    ("S", "Over fifty million. Since 1966.", 1, 'shock'),
    ("B", "Fifty MILLION?!", 1, 'furious'),
    ("S", "Toyota calls it the world's best-selling nameplate.", 1, None),
    ("B", "But it's so boring!", 2, 'angry'),
    ("S", "Twelve generations of boring.", 2, 'confused'),
    ("B", "Why does anyone even buy it?", 3, 'confused'),
    ("S", "It's famous for reliability.", 3, None),
    ("B", "That's it?!", 3, 'shock'),
    ("S", "It's affordable. And cheap to run.", 3, 'worried'),
    ("B", "Nobody dreams about a Corolla!", 4, 'furious'),
    ("S", "No. They just keep buying them.", 4, 'deflated'),
    ("B", "So boring wins?", 5, 'deflated'),
    ("S", "Exciting or reliable? Tell me in the comments.", 5, None),
]
DIRECTION = ("TTS this fast-paced comedy skit at a Toyota dealership. The Salesman is completely flat, calm and deadpan the "
             "whole time, same bored tone on every answer. Say 1966 as 'nineteen sixty-six'. The Buyer starts already outraged "
             "(he expected a supercar to be number one) and escalates: shouting 'Fifty MILLION?!' and 'Nobody dreams about a "
             "Corolla!', then deflates into quiet defeat on 'So boring wins?'. The Salesman's last line is asked straight to the "
             "audience, still deadpan. Snappy timing, no long pauses between lines.")
SPOKEN = {"1966": "nineteen sixty six", "bestselling": "best selling"}
DICT = {"corollas": "K ER AA L AH Z", "supercar": "S UW P ER K AA R", "supercars": "S UW P ER K AA R Z"}
HOLD = {5: 0.2}
GAPS = (0.1, 0.35, 0.6)
BRAND = dict(logo='toyota_logo.png', name='TOYOTA', accent=(235, 10, 30), wall=((226, 228, 232), (244, 245, 247)),
             floor=((70, 72, 78), (110, 112, 118)), panel=(236, 238, 241), ceil=(240, 241, 244), fascia=(252, 252, 252),
             logo_white=False, logo_white_on_dark=True)
SETS = [dict(kind='showroom', photo='corolla_2021_le.jpg', fy=.6),
        dict(kind='office', photo='corolla_2020_se.jpg', fy=.6),
        dict(kind='gallery', photos=['corolla_1968.jpg', 'corolla_2021_le.jpg'], labels=['1968', '2021'], fy=.6),
        dict(kind='garage', photo='corolla_2020_se.jpg', fy=.6),
        dict(kind='factory', photo='corolla_2021_le.jpg', fy=.6),
        dict(kind='lot', photo='corolla_2020_se.jpg', fy=.62)]
CLOSE = (3, 'Supercars')
CARDS = [dict(kind='photo', img='corolla_2021_le.jpg', label='TOYOTA COROLLA', at=(3, 'Supercars'), y=470),
         dict(kind='stat', big='50,000,000+', sub='Corollas sold since 1966', at=(5, 'fifty'), until=(7, 'Toyota'), y=430),
         dict(kind='info', rows=(("World's best-selling", 56, 'ink'), ("nameplate", 56, 'ink'), ("(Toyota)", 50, 'red')), at=(7, 'Toyota'), y=440),
         dict(kind='info', rows=(("12 generations", 64, 'ink'), ("since 1966", 56, 'red')), at=(9, 'Twelve'), y=640),
         dict(kind='stamp', txt='RELIABLE', col=(40, 160, 80), at=(11, 'reliability'), until=(13, 'affordable'), y=560),
         dict(kind='stamp', txt='CHEAP TO RUN', col=(40, 160, 80), at=(13, 'cheap'), y=560, rot=6),
         dict(kind='photo', img='corolla_1968.jpg', label='1968 COROLLA', at=(15, 'keep'), y=470, rot=3)]
PUNCH = [((0, 'THIS'), .04), ((2, 'supercar'), .04), ((5, 'fifty'), .04), ((6, 'MILLION'), .06), ((9, 'Twelve'), .03),
         ((12, "That's"), .04), ((14, 'Nobody'), .05)]
SHAKE = [(6, 'MILLION')]
SFX = [((5, 'fifty'), 'cha_ching', .3), ((12, "That's"), 'buzzer', .2)]
ODDITY, ODD_S, ODD_DRIFT = 'penguin', 1.3, -6
ODD_X = [860, 870, 860, 880, 860, 870]
FINAL = [("Exciting or reliable?", 74, 'tag'), ("Tell me in the comments.", 60, 'white'),
         ("Next: is the electric", 60, 'grey'), ("Mustang a Mustang?", 60, 'grey')]
THUMB_T = (6, 'MILLION', .2)
THUMB = [("THE MOST BORING", 'white'), ("CAR WINS?!", 'tag')]
THUMB_PHOTO, THUMB_LABEL = 'corolla_2021_le.jpg', '50,000,000+ SOLD'
