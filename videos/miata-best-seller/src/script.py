"""miata-best-seller: dialogue, exhibits, look. Rendered by videos/origin-kit/engine.py."""
LINES = [
    ("B", "Everyone says buy a Miata. It's not even fast!", 1),
    ("S", "Sir, it's the best-selling two-seat sports car in history.", 1),
    ("B", "How?!", 2),
    ("S", "It launched at the Chicago Auto Show in February 1989.", 2),
    ("B", "And people wanted it?", 3),
    ("S", "Mazda forecast about forty thousand sales a year. In Japan, buyers placed thousands of orders a month. Mazda struggled to keep up.", 3),
    ("B", "What's the secret?", 4),
    ("S", "Lightweight. Two seats. Rear-wheel drive. Modest power. Fifty-fifty weight distribution.", 4),
    ("B", "And the record?", 5),
    ("S", "Guinness certified it in 2000, at about five hundred and thirty thousand built. Mazda passed one million in 2016.", 5),
    ("B", "It's still not fast.", 6),
    ("S", "No, sir. It's fun.", 6),
    ("S", "Is the Miata the best first sports car? Let them decide.", 6),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
DIRECTION = ("TTS this snappy comedy skit in a car showroom. The Salesman is calm and completely deadpan, the same polite flat "
             "tone on every line, with a tiny hint of warmth only on 'It's fun.' The Buyer starts exasperated and sceptical on "
             "'Everyone says buy a Miata. It's not even fast!', shocked on 'How?!', grudgingly curious after that, and "
             "stubborn and sulky on 'It's still not fast.' On the last line the Salesman turns to the audience. Say 1989 as "
             "'nineteen eighty-nine', 2000 as 'two thousand' and 2016 as 'twenty sixteen'. Miata is 'mee-AH-ta'. Quick "
             "timing, no long pauses.\n\n")
SPOKEN = {"1989": "nineteen eighty nine", "2000": "two thousand", "2016": "twenty sixteen", "bestselling": "best selling",
          "twoseat": "two seat", "rearwheel": "rear wheel", "fiftyfifty": "fifty fifty", "lightweight": "light weight"}
PHONES = {}
EXHIBITS = {
    'na': dict(file='miata_na.jpg', label='FIRST MX-5 MIATA', crop=(.08, .38, .96, .8)),
    'nd': dict(file='mx5_nd.jpg', label='MX-5 TODAY', crop=(.0, .1, 1, .97), plates=[(.585, .62, .755, .71)], plate_col=(236, 236, 232)),
}
SCENE_EXHIBIT = ['na', 'na', 'na', 'nd', 'nd', 'nd']
CHIPS = {3: (3, '1989', 'CHICAGO AUTO SHOW, FEB 1989'), 5: (5, 'month', 'FORECAST: ABOUT 40,000 A YEAR'),
         7: (7, 'distribution', '50:50 WEIGHT'), 9: (9, '2016', '1,000,000 BY 2016')}
PUNCH = [(0, 'fast'), (1, 'history'), (2, 'How'), (5, 'thousands'), (7, 'Fifty-fifty'), (9, '2000'), (10, 'fast'), (11, 'fun')]
ODDITIES = [('cat', 'R'), ('astronaut', 'L'), ('sheep', 'R'), ('giraffe', 'L'), ('bear', 'R'), ('pigeon', 'L')]
BRAND = dict(name='MAZDA', wall=((26, 26, 30), (58, 56, 60)), floor=((30, 28, 30), (8, 8, 10)), trim=(196, 18, 40),
             accent=(230, 30, 52), namecol=(222, 224, 230), panel=(40, 38, 42), hexes=False, sky=((120, 200, 255), (255, 228, 180)))
SALES = dict(skin='d9a47c', skin2='b9845e', hair='5a3a26', suit='2c2c30', suit2='18181b', shirt='f7f7fa', tie='c41228',
             pants='2c2c30', shoe='5a3422', hairstyle='part', lids=0.45, hat='cap', hatcol='9a1426', badge=(196, 18, 40))
HEADLINE = ["IT'S NOT", "EVEN FAST!"]
THUMB_EXHIBIT = 'na'
FINAL = ["Comment below.", "Next: another brand's", "strange beginning."]
