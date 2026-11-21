"""03 Civic Type R vs Golf R: "Pick one."  B = buyer (Fenrir), S = salesman (Orus).
Scenes: 1 two-brand showroom, 2 race track, 3 snowy mountain road, 4 price office, 5 rainy city night, 6 sunset lot."""
SLUG = 'civic_vs_golf'
LINES = [
    ("B", "Fifty grand. One hot hatch. Which one?!", 1),
    ("S", "Civic Type R, or Golf R. Pick one.", 1),
    ("B", "Civic first!", 2),
    ("S", "Three hundred fifteen horsepower. A real six-speed manual.", 2),
    ("B", "A manual! Sold!", 2),
    ("S", "Front-wheel drive only.", 2),
    ("B", "Okay... the Golf?", 3),
    ("S", "Three twenty-eight horsepower. All-wheel drive.", 3),
    ("B", "Snow? Rain? Who cares!", 3),
    ("S", "Automatic only. No manual.", 3),
    ("B", "Then the cheaper one wins.", 4),
    ("S", "The Civic. About forty-eight thousand.", 4),
    ("B", "And the Golf?", 4),
    ("S", "About fifty-one.", 4),
    ("B", "So which one is better?!", 5),
    ("S", "Love shifting? Civic. Hate rain? Golf.", 5),
    ("B", "That doesn't help!", 5),
    ("S", "Which one are you taking?", 6),
]
DIRECTION = ("TTS this fast-paced comedy skit at a car dealership. Keep the pace high and snappy, no long pauses. The Salesman "
             "is flat, calm and deadpan the whole time, same bored tone on every answer. Say 'Type R' clearly and 'Golf R' "
             "as 'Golf Are'. The Buyer is excited and torn: thrilled on 'A manual! Sold!', deflated on 'Okay... the Golf?', "
             "pumped on 'Snow? Rain? Who cares!', confident on 'Then the cheaper one wins.', then exasperated shouting 'That "
             "doesn't help!'. The Salesman says the last line slowly, straight to camera.\n\n")
SPOKEN = {"six-speed": "six speed", "front-wheel": "front wheel", "all-wheel": "all wheel", "twenty-eight": "twenty eight",
          "forty-eight": "forty eight", "fifty-one": "fifty one"}
HOLD = {1: .4, 3: .4, 5: .45, 7: .4, 9: .45, 11: .5, 13: .6, 15: .4}
GAPS = (0.25, 0.6, 1.0)

# ---------------------------------------------------------------- picture (anchors: see render.A)
ODD = 'octopus'                                 # an octopus juggling oranges on a traffic cone, every scene, never mentioned
SALES = {'suit': '4a4e58', 'pants': '4a4e58', 'tie': 'b01e2a'}
BADGE = (30, 60, 140)
MUSIC_AT = 45.0
C = 459
SCN = [
    dict(bg='showroom', brand='duo', cars=[dict(kind='civic', x0=40, g=900, L=380), dict(kind='golf', x0=490, g=900, L=380)], odd=(960, 945, .55)),
    dict(bg='track', cars=[dict(kind='civic', x0=C - 280, g=930, L=560, anim='in_right')], odd=(90, 800, .45)),
    dict(bg='snow', cars=[dict(kind='golf', x0=C - 280, g=950, L=560, anim='in_left')], odd=(930, 830, .5)),
    dict(bg='office', odd=(880, 940, .55)),
    dict(bg='night', cars=[dict(kind='civic', x0=10, g=905, L=420), dict(kind='golf', x0=520, g=905, L=420)], odd=(475, 915, .38)),
    dict(bg='lot', time='dusk', cars=[dict(kind='civic', x0=40, g=905, L=380), dict(kind='golf', x0=490, g=905, L=380)], odd=(960, 940, .55)),
]
X = dict(brows='up', eyes='wide', smile=1); WS = dict(brows='angry', eyes='wide', sweat=1)
BPOSE = {'open': ('point', 'up', X), 0: ('up', 'point', X), 2: ('point', 'rest', X), 4: ('up', 'up', X),
         '5:Front': ('chin', 'rest', dict(brows='worried')), 6: ('shrug', 'shrug', dict(brows='worried', tired=.2)),
         8: ('up', 'point', X), '9:Automatic': ('head', 'head', WS), 10: ('hip', 'hip', dict(brows='up', smile=1)),
         '11:forty': ('rest', 'point', X), 12: ('chin', 'rest', dict(brows='up')), '13:fifty': ('head', 'rest', dict(brows='up', eyes='wide')),
         14: ('shrug', 'shrug', dict(brows='angry')), 16: ('up', 'up', WS), '17:Which': ('rest', 'rest', dict(brows='up', eyes='wide', look=0))}
SPOSE = {1: ('open', 'open', {}), 3: ('present', 'clasp', {}), 5: ('offer', 'clasp', {}), 7: ('present', 'clasp', {}),
         9: ('open', 'clasp', {}), 11: ('present', 'clasp', {}), 13: ('offer', 'clasp', {}), 15: ('open', 'open', {}),
         17: ('open', 'clasp', dict(look=0))}
OVER = [
    dict(k='vs', pair=[('ctr_front.jpg', 'CIVIC TYPE R', 'logo_honda.png'), ('gr_front.jpg', 'GOLF R', 'logo_vw.png')], a='L1+.1', b='S1+.05', y=520),
    dict(k='card', rows=[('Civic Type R', 46, 'ink'), ('315 HP', 92, 'red'), ('6-speed manual only', 44, 'ink')], a='3:Three-.05', b='L5-.05', y=560),
    dict(k='stamp', txt='FRONT-WHEEL DRIVE', col='R', a='5:Front-.05', b='S2+.05', y=560, size=64, rot=-6),
    dict(k='card', rows=[('Golf R', 46, 'ink'), ('328 HP', 92, 'red'), ('all-wheel drive', 44, 'ink')], a='7:Three-.05', b='L9-.05', y=560),
    dict(k='stamp', txt='NO MANUAL', col='R', a='9:Automatic-.05', b='S3+.05', y=560, size=90, rot=-6),
    dict(k='tag', txt='$48,090', sub='2026 CIVIC TYPE R · INCL. DEST.', a='11:forty-.05', b='S4+.05', y=470, w=720),
    dict(k='tag', txt='$50,730', sub='2026 GOLF R · INCL. DEST.', a='13:fifty-.05', b='S4+.05', y=700, w=720, col='B', rot=3),
    dict(k='chips', rows=[('LOVE SHIFTING?', 'CIVIC TYPE R', 'R', '15:shifting'), ('HATE RAIN?', 'GOLF R', 'B', '15:rain')], a='L15', b='S5+.05', y=560),
    dict(k='vs', pair=[('ctr_front.jpg', 'CIVIC TYPE R', 'logo_honda.png'), ('gr_front.jpg', 'GOLF R', 'logo_vw.png')], a='S5+.25', b='CARD', y=520),
]
FINAL = [('Civic or Golf?', 84, 'Y'), ('Which one are', 66, 'W'), ('you taking?', 66, 'W')]
PUNCH = [('1:Pick', .04), ('3:Three', .04), ('5:Front', .05), ('7:Three', .04), ('9:Automatic', .05), ('11:forty', .04), ('13:fifty', .05), ('16:help', .06)]
SHAKE = ['16:help']
FLASH = []
CUES = [('S1', 'vroom', .45), ('S1+.7', 'screech', .3), ('4:Sold', 'ding', .2), ('5:Front', 'buzzer', .2), ('S2', 'vroom', .4),
        ('9:Automatic', 'buzzer', .2), ('11:forty+.2', 'cha', .3), ('13:fifty+.2', 'cha', .3), ('16:help', 'boom', .25)]
THUMB = dict(t='13:fifty+.5', photos=[('ctr_front.jpg', 'CIVIC TYPE R', 'logo_honda.png'), ('gr_front.jpg', 'GOLF R', 'logo_vw.png')],
             text=[('PICK', 120, 'W'), ('ONE.', 150, 'Y')])
