"""Cars, scenes, cards and oddities for blazer-ev-no-carplay (engine: videos/showroom-kit/engine.py).
Card refs: int = line start, (line, 'word') = that word, (line, None) = line end; default = scene start/end."""
BRAND = 'chevrolet'
SALES = dict(suit='2b2b30', tie='e8b52a', badge='e8b52a')            # charcoal suit, Chevy-gold tie
CARS = {'blazer': dict(img='chevy_blazer_ev', label='CHEVY BLAZER EV', sub='2024'),
        'prologue': dict(img='honda_prologue', label='HONDA PROLOGUE', sub='2024')}
B = ('blazer',)
SCENES = [
    dict(cars=B, odd='ducks', cards=[
        dict(kind='stamp', text='NO CARPLAY', col='red', at=(1, 'Apple'), until=3),
        dict(kind='card', at=(3, 'March'), rows=(("March 2023: GM drops", 52, 'ink'), ("CarPlay & Android Auto", 52, 'ink'),
                                                 ("from new EVs", 52, 'red')))]),
    dict(cars=B, odd='astronaut', cards=[
        dict(kind='card', at=(5, 'own'), rows=(("Built-in,", 56, 'ink'), ("Google-based system", 56, 'red')))]),
    dict(cars=B, odd='horse', cards=[
        dict(kind='chips', at=(8, 'safety'), until=(9, None), rows=[
            ("GM'S TIM BABBITT", 'SAFETY', 'grey', (8, 'safety')), ('PHONE LINK', 'DROPPED CONNECTIONS', 'red', (8, 'Dropped')),
            ('PHONE LINK', 'SLOW RESPONSES', 'red', (8, 'Slow'))]),
        dict(kind='card', at=(10, 'Critics'), rows=(("Critics, incl. Motor1:", 52, 'ink'), ("it doesn't reduce", 52, 'ink'),
                                                    ("distraction", 52, 'red')))]),
    dict(cars=B, odd='cactus', cards=[
        dict(kind='chips', two_line=True, at=(12, 'works'), rows=[
            ('YOUR PHONE IN THE BLAZER EV', 'STILL PLAYS MUSIC', 'green', (12, 'music')),
            ("GM'S GAS CARS", 'KEEP CARPLAY', 'green', (14, 'keep'))])]),
    dict(cars=('blazer', 'prologue'), odd='fishwalk', cards=[
        dict(kind='chips', two_line=True, at=(16, 'Same'), until=(17, None), rows=[
            ('HONDA PROLOGUE', 'SAME PLATFORM, SAME PLANT', 'blue', (16, 'Same')),
            ('HONDA PROLOGUE', 'HAS CARPLAY', 'green', (16, 'has'))]),
        dict(kind='card', at=(18, 'Reports'), rows=(("Reported:", 50, 'ink'), ("CarPlay returns on the", 52, 'ink'),
                                                    ("2027 Silverado & Sierra", 54, 'red')))]),
    dict(cars=B, odd='ghost'),
]
FINAL_Q = ('Would you buy it', 'without CarPlay?')
THUMB = dict(headline=('NO', 'CARPLAY?!'), cars=B)
