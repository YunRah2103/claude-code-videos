"""Cars, scenes, cards and oddities for gr86-vs-brz (engine: videos/showroom-kit/engine.py).
Card refs: int = line start, (line, 'word') = that word, (line, None) = line end; default = scene start/end."""
BRAND = 'toyota'
SALES = dict(suit='1b1b1f', tie='e60012', badge='e60012')            # black suit, GR-red tie
CARS = {'gr86': dict(img='toyota_gr86', label='TOYOTA GR86', sub='2022'),
        'brz': dict(img='subaru_brz', label='SUBARU BRZ', sub='2022')}
SCENES = [
    dict(cars=('gr86',), odd='sheep', cards=[
        dict(kind='stamp', text='BUILT BY SUBARU', col='red', size=84, at=(1, 'factory'), until=3),
        dict(kind='card', at=3, rows=(("Subaru Gunma Main Plant", 54, 'ink'), ("Ōta, Japan", 54, 'red')))]),
    dict(cars=('gr86', 'brz'), odd='penguin', cards=[
        dict(kind='chips', at=(5, 'same'), rows=[('TOYOTA GR86', 'GUNMA, JAPAN', 'red', (5, 'same')),
                                                 ('SUBARU BRZ', 'GUNMA, JAPAN', 'red', (5, 'production')),
                                                 ('PRODUCTION LINE', 'THE SAME ONE', 'red', (5, 'line'))])]),
    dict(cars=('brz', 'gr86'), odd='knight', cards=[
        dict(kind='card', at=(7, 'agreed'), rows=(("Oct 2005: Toyota and Subaru team up", 46, 'ink'),
                                                  ("Apr 2008: Toyota stake raised to 16.5%", 46, 'ink'),
                                                  ("Mar 2012: first-gen production", 46, 'red')))]),
    dict(cars=('gr86', 'brz'), odd='snailrace', cards=[
        dict(kind='chips', at=(11, 'boxer'), rows=[
            ('ENGINE', '2.4 L SUBARU BOXER', 'red', (11, 'boxer')), ('TURBO', 'NONE', 'grey', (11, 'turbo')),
            ('DRIVE', 'REAR-WHEEL', 'red', (13, 'Rear-wheel')), ('GEARBOX', '6-SPEED MANUAL OR AUTO', 'red', (13, 'Six-speed'))])]),
    dict(cars=('brz', 'gr86'), odd='statue', cards=[
        dict(kind='chips', at=(15, 'Badges'), until=(16, None), rows=[
            ('BADGES', 'DIFFERENT', 'gold', (15, 'Badges')), ('FRONT FASCIAS', 'DIFFERENT', 'gold', (15, 'bumpers')),
            ('TUNING', 'DIFFERENT', 'gold', (15, 'Tuning'))]),
        dict(kind='card', at=(17, 'Within'), rows=(("GR86: about 2,811–2,868 lb", 48, 'ink'), ("BRZ: about 2,820–2,881 lb", 48, 'ink'),
                                                   ("Gap: about 15–20 lb", 54, 'red')))]),
    dict(cars=('gr86',), odd='octopus'),
]
FINAL_Q = ('Which badge', 'would you buy?')
THUMB = dict(headline=('TOYOTA BUILT', 'BY SUBARU?!'), cars=('gr86', 'brz'))
