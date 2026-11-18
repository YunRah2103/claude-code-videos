"""subaru-aircraft-origin: dialogue, exhibits, look. Rendered by videos/origin-kit/engine.py."""
LINES = [
    ("B", "I bought a Subaru and the company built planes?!", 1),
    ("S", "Yes, sir. Subaru comes from Nakajima Aircraft, once Japan's leading aircraft maker.", 1),
    ("B", "Planes?! And after the war?", 2),
    ("S", "It became Fuji Heavy Industries. Its first vehicle was a scooter, in 1946. Reportedly made from aircraft parts.", 2),
    ("B", "A scooter?!", 3),
    ("S", "In the mid-1950s it built its first car prototype. The P-1. Later the Subaru 1500.", 3),
    ("B", "Why is it called Subaru?", 4),
    ("S", "Subaru is the Japanese name for the Pleiades star cluster.", 4),
    ("B", "So that's the logo?", 5),
    ("S", "Six stars. Reportedly one for each company that merged.", 5),
    ("B", "Planes, scooters, then stars.", 6),
    ("S", "Quite a journey, sir.", 6),
    ("S", "Is Subaru's origin the most unexpected of any brand? Let them decide.", 6),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
DIRECTION = ("TTS this snappy comedy skit in a car showroom. The Salesman is calm and completely deadpan, the same polite flat "
             "tone on every line. The Buyer is stunned from the first word: astonished on 'I bought a Subaru and the company "
             "built planes?!', louder on 'Planes?!' and 'A scooter?!', then curious, then dreamy and amazed on 'Planes, "
             "scooters, then stars.' On the last line the Salesman turns to the audience. Subaru is 'SOO-ba-roo', Nakajima is "
             "'na-KA-jee-ma', Pleiades is 'PLEE-uh-deez'. Say 1946 as 'nineteen forty-six', 'mid-1950s' as 'mid nineteen "
             "fifties', 'P-1' as 'P one' and '1500' as 'fifteen hundred'. Quick timing, no long pauses.\n\n")
SPOKEN = {"1946": "nineteen forty six", "mid1950s": "mid nineteen fifties", "p1": "p one", "1500": "fifteen hundred"}
PHONES = {"subaru's": "S UW B AA R UW Z"}
EXHIBITS = {
    'today':  dict(file='subaru_current.jpg', label='SUBARU TODAY', crop=(.0, .12, 1, .92)),
    'rabbit': dict(file='fuji_rabbit.jpg', label='FUJI RABBIT SCOOTER', crop=(.0, .15, 1, .88), flip=True, erase=[(.27, .15, .47, .395), (.8, .1, 1, .3)]),
    'p1':     dict(file='subaru_p1.jpg', label='SUBARU P-1 / 1500', crop=(.08, .0, .95, .97)),
}
SCENE_EXHIBIT = ['today', 'rabbit', 'p1', 'today', 'today', 'today']
CHIPS = {1: (1, 'leading', 'NAKAJIMA AIRCRAFT'), 3: (3, 'parts', '1946: FIRST VEHICLE'),
         5: (5, 'Later', 'MID-1950s: P-1'), 7: (7, 'cluster', 'SUBARU = PLEIADES')}
PUNCH = [(0, 'planes'), (2, 'Planes'), (3, 'scooter'), (4, 'scooter'), (5, 'P-1'), (7, 'Pleiades'), (9, 'Six'), (10, 'stars')]
ODDITIES = [('astronaut', 'R'), ('bear', 'L'), ('sheep', 'R'), ('ufo', 'L'), ('penguin', 'R'), ('octopus', 'L')]
BRAND = dict(name='SUBARU', wall=((8, 20, 64), (18, 44, 112)), floor=((16, 26, 56), (4, 8, 20)), trim=(64, 140, 255),
             accent=(90, 170, 255), namecol=(240, 244, 255), panel=(14, 32, 86), hexes=False, starfield=True,
             sky=((20, 30, 80), (90, 120, 200)))
SALES = dict(skin='f0c8a6', skin2='d4a684', hair='3a2a20', suit='12245a', suit2='0a1840', shirt='f7f7fa', tie='1f6fe0',
             pants='12245a', shoe='1a1a1c', hairstyle='part', lids=0.45, pin=(255, 214, 90), badge=(64, 140, 255))
HEADLINE = ["SUBARU", "BUILT PLANES?!"]
THUMB_EXHIBIT = 'today'
FINAL = ["Comment below.", "Next: another brand's", "strange beginning."]
STARS = (9, 'Six')
