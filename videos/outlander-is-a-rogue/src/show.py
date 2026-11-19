"""Cars, scenes, cards and oddities for outlander-is-a-rogue (engine: videos/showroom-kit/engine.py).
The two photos are front three-quarter shots from opposite sides, so the pair always stands facing each other:
Rogue on the left (its photo is cropped at the rear, faded out at the far left), Outlander on the right."""
BRAND = 'mitsubishi'
SALES = dict(suit='4a4e57', tie='e60012', badge='e60012')            # grey suit, Mitsubishi-red tie
CARS = {'outlander': dict(img='mitsubishi_outlander', label='MITSUBISHI OUTLANDER', sub='2022'),
        'rogue': dict(img='nissan_rogue', label='NISSAN ROGUE', sub='2021', scale=.96)}
PAIR = ('rogue', 'outlander')
SCENES = [
    dict(cars=('outlander',), odd='llama', cards=[
        dict(kind='card', at=(1, 'Alliance'), rows=(("Mitsubishi: “a shared", 50, 'ink'), ("Alliance platform”", 50, 'ink'),
                                                    ("Reviewers: “the Rogue’s”", 54, 'red')))]),
    dict(cars=PAIR, odd='dino', cards=[
        dict(kind='chips', at=(5, 'CMF-CD'), rows=[
            ('PLATFORM', 'CMF-CD (RENAULT-NISSAN)', 'red', (5, 'CMF-CD')), ('ALSO UNDER', 'NISSAN ROGUE', 'red', (5, 'Rogue')),
            ('OUTLANDER', '4TH GEN, LAUNCHED 2021', 'blue', (7, 'Fourth'))])]),
    dict(cars=PAIR, odd='giraffe', cards=[
        dict(kind='chips', at=(9, "Nissan's"), rows=[('ENGINE', 'NISSAN 2.5 L 4-CYLINDER', 'red', (9, "Nissan's")),
                                                     ('GEARBOX', 'CVT', 'red', (9, 'CVT'))])]),
    dict(cars=('outlander',), odd='bear', cards=[
        dict(kind='chips', at=(13, 'styling'), rows=[('STYLING', 'MITSUBISHI', 'green', (13, 'styling')),
                                                     ('TUNING', 'MITSUBISHI', 'green', (13, 'tuning'))])]),
    dict(cars=PAIR, odd='vending', cards=[
        dict(kind='card', at=(17, 'About'), rows=(("Outlander vs Rogue:", 52, 'ink'), ("about 200 lb heavier", 58, 'red'),
                                                  ("(reviewer figure)", 44, 'ink')))]),
    dict(cars=PAIR, odd='banana'),
]
FINAL_Q = ('Rogue or', 'Outlander?')
THUMB = dict(headline=('MITSUBISHI', 'IS A NISSAN?!'), cars=PAIR)
