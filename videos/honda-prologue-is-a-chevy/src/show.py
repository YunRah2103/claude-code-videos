"""Cars, scenes, cards and oddities for honda-prologue-is-a-chevy (engine: videos/showroom-kit/engine.py).
Card refs: int = line start, (line, 'word') = that word, (line, None) = line end; default = scene start/end."""
BRAND = 'honda'
SALES = dict(suit='2a2d36', tie='d8202e', badge='d8202e')            # charcoal suit, Honda-red tie
CARS = {'prologue': dict(img='honda_prologue', label='HONDA PROLOGUE', sub='2024'),
        'blazer': dict(img='chevy_blazer_ev', label='CHEVY BLAZER EV', sub='2024')}
SCENES = [
    dict(cars=('prologue',), odd='shark', cards=[
        dict(kind='stamp', text='BUILT BY GM', col='red', at=(1, 'General'), until=3),
        dict(kind='card', at=3, rows=(("Honda's first major EV", 54, 'ink'), ("in North America", 54, 'red')))]),
    dict(cars=('prologue', 'blazer'), odd='mime', cards=[
        dict(kind='card', at=(5, 'Ramos'), until=(6, None), rows=(("GM Ramos Arizpe plant", 52, 'ink'), ("Coahuila, Mexico", 52, 'ink'),
                                                              ("Same plant as the Blazer EV", 52, 'red'))),
        dict(kind='chips', at=7, rows=[('PRODUCTION', 'JANUARY 2024', 'blue', (7, 'January')), ('ON SALE', 'MARCH 2024', 'blue', (7, None))])]),
    dict(cars=('blazer', 'prologue'), odd='ufo', cards=[
        dict(kind='chips', at=(9, 'Ultium'), until=(10, None), rows=[
            ('PLATFORM', 'GM ULTIUM (BEV3)', 'red', (9, 'Ultium')), ('FRAME RAILS', 'SHARED', 'red', (9, 'Frame')),
            ('FLOOR', 'SHARED', 'red', (9, 'Floor')), ('SUBFRAMES', 'SHARED', 'red', (9, 'Subframes')),
            ('FIREWALL', 'SHARED', 'red', (9, 'Firewall'))]),
        dict(kind='card', at=11, rows=(("Source: Honda's", 52, 'ink'), ("chief engineer", 52, 'ink'),
                                       ("Also shared: Cadillac Lyriq", 46, 'red')))]),
    dict(cars=('prologue',), odd='pigeon', cards=[
        dict(kind='chips', at=(13, 'body'), rows=[
            ('BODY DESIGN', 'HONDA', 'green', (13, 'body')), ('INTERIOR', 'HONDA', 'green', (13, 'interior')),
            ('STEERING TUNING', 'HONDA', 'green', (13, 'steering')), ('SPRINGS & DAMPERS', 'HONDA', 'green', (13, 'springs'))])]),
    dict(cars=('prologue', 'blazer'), odd='disco', cards=[
        dict(kind='chips', two_line=True, at=(15, 'Apple'), rows=[
            ('HONDA PROLOGUE', 'CARPLAY + ANDROID AUTO', 'green', (15, 'Apple')),
            ('CHEVY BLAZER EV', 'NO CARPLAY, NO ANDROID AUTO', 'red', (15, 'Chevy'))])]),
    dict(cars=('prologue',), odd='snowman'),
]
FINAL_Q = ('Is it still', 'a Honda?')
THUMB = dict(headline=('MY HONDA', 'IS A CHEVY?!'), cars=('prologue', 'blazer'))
