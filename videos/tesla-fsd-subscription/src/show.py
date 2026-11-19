"""Cars, scenes, cards and oddities for tesla-fsd-subscription (engine: videos/showroom-kit/engine.py).
Card refs: int = line start, (line, 'word') = that word, (line, None) = line end; default = scene start/end."""
BRAND = 'tesla'
SALES = dict(suit='17181c', shirt='2a2b30', tie=None, badge='e82127')   # all-black Tesla advisor look
CARS = {'model_y': dict(img='tesla_model_y', label='TESLA MODEL Y', sub='2024')}
Y = ('model_y',)
SCENES = [
    dict(cars=Y, odd='flamingo', cards=[
        dict(kind='stamp', text='SUBSCRIPTION ONLY', col='red', size=80, at=(1, 'Subscription'), until=3),
        dict(kind='card', at=3, rows=(("Announced January 14, 2026", 50, 'ink'), ("Subscription only after", 50, 'ink'),
                                      ("February 14, 2026 (US)", 50, 'red')))]),
    dict(cars=Y, odd=('goat', dict(x=650, fy=490)), cards=[
        dict(kind='chips', at=5, rows=[('BEFORE FEB 14', '$8,000 ONCE', 'green', (5, '$8,000')),
                                       ('MONTHLY', '$99', 'red', (7, '$99')), ('YEARLY', '$999', 'red', (7, '$999'))])]),
    dict(cars=Y, odd='scuba', cards=[
        dict(kind='card', at=(9, 'About'), rows=(("$8,000 / $99", 60, 'ink'), ("= about 80 months", 60, 'ink'),
                                                 ("= over 6.5 years", 60, 'red')))]),
    dict(cars=Y, odd='plant', cards=[
        dict(kind='chips', two_line=True, at=(11, 'Rivian'), rows=[
            ('RIVIAN AUTONOMY+', '$49.99/MONTH OR $2,500 ONCE', 'blue', (11, 'Rivian')),
            ('GM SUPER CRUISE', '3 YEARS INCLUDED, THEN $39.99/MONTH', 'blue', (11, 'GM')),
            ('TESLA FSD (SUPERVISED)', '$99/MONTH, NO ONE-TIME BUY', 'red', (12, '$99'))])]),
    dict(cars=Y, odd='balloon', cards=[
        dict(kind='card', at=(15, 'FSD'), until=17, rows=(("FSD (Supervised):", 56, 'ink'), ("the driver must", 56, 'ink'),
                                                          ("pay attention", 56, 'red'))),
        dict(kind='card', at=17, rows=(("Prices as announced.", 56, 'ink'), ("They may change.", 56, 'red')))]),
    dict(cars=Y, odd='cow'),
]
FINAL_Q = ('Would you rent your', 'self-driving?')
THUMB = dict(headline=("CAN'T BUY", 'FSD?!'), cars=Y)
