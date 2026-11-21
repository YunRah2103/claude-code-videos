"""01 Cybertruck: "Would you still buy a Cybertruck?"  (speaker, text, scene). B = buyer (Fenrir), S = salesman (Orus).
Scenes: 1 Tesla showroom, 2 drag strip, 3 desert highway, 4 service centre, 5 rainy city night, 6 showroom at night."""
SLUG = 'cybertruck'
LINES = [
    ("B", "A forty-grand Cybertruck? Where?!", 1),
    ("S", "Thirty-nine nine. Promised in 2019.", 1),
    ("B", "So what does it cost now?", 1),
    ("S", "The top Cyberbeast? About a hundred grand.", 1),
    ("B", "A hundred?! What do I get?", 2),
    ("S", "Zero to sixty in two point six seconds.", 2),
    ("B", "Okay, that's insane.", 2),
    ("S", "And it tows eleven thousand pounds.", 3),
    ("B", "Range?", 3),
    ("S", "Promised five hundred miles. Rated about three twenty.", 3),
    ("B", "I can live with that. What's the catch?", 4),
    ("S", "The steel trim panel. It could fall off.", 4),
    ("B", "On how many?!", 4),
    ("S", "Forty-six thousand trucks. Almost every one built.", 4),
    ("B", "Every one?!", 5),
    ("S", "Tesla replaced it for free.", 5),
    ("B", "So... do I buy it?", 6),
    ("S", "Would you still buy a Cybertruck?", 6),
]
DIRECTION = ("TTS this fast-paced comedy skit at a car dealership. Keep the pace high, snappy, no long pauses between lines. "
             "The Salesman is flat, calm and deadpan the whole time, same bored tone on every answer. Say 2019 as "
             "'twenty nineteen'. The Buyer opens loud and excited, gets more amazed with each spec ('Okay, that's insane!'), "
             "turns suspicious on 'What's the catch?', shouts 'On how many?!' and 'Every one?!', then goes quiet and torn on "
             "'So... do I buy it?'. The Salesman delivers the last line slowly, straight to camera.\n\n")
SPOKEN = {"2019": "twenty nineteen", "cybertruck": "cyber truck", "cyberbeast": "cyber beast", "forty-grand": "forty grand",
          "forty-six": "forty six"}
HOLD = {1: .25, 3: .45, 5: .35, 9: .3, 11: .4, 13: .45, 15: .3}

# ---------------------------------------------------------------- picture (anchors: see render.A)
ODD = 'cow'                                     # a cow in a VR headset, in every scene, never mentioned
SALES = {'shirt': '15161a', 'tie': None}         # Tesla-store salesman: black turtleneck under the suit
BADGE = (220, 30, 40)
MUSIC_AT = 0.5
C = 459
SCN = [
    dict(bg='showroom', brand='tesla', cars=[dict(kind='cybertruck', x0=C - 290, g=894, L=580)], odd=(880, 945, .55)),
    dict(bg='dragstrip', go='5:Zero', cars=[dict(kind='cybertruck', x0=C - 280, g=880, L=560, anim='launch', at='5:Zero')], odd=(330, 720, .32)),
    dict(bg='desert', cars=[dict(kind='cybertruck', x0=40, g=900, L=520)], trailer=(850, 778), odd=(800, 735, .26)),
    dict(bg='workshop', sign='TESLA SERVICE', cars=[dict(kind='cybertruck', x0=C - 290, g=894, L=580, anim='lift', trim_fall='11:fall')], odd=(905, 940, .5)),
    dict(bg='night', cars=[dict(kind='cybertruck', x0=C - 290, g=900, L=580)], odd=(885, 905, .5)),
    dict(bg='showroom', brand='tesla_night', cars=[dict(kind='cybertruck', x0=C - 290, g=894, L=580)], odd=(880, 945, .55)),
]
X = dict(brows='up', eyes='wide', smile=1); WS = dict(brows='angry', eyes='wide', sweat=1)
BPOSE = {'open': ('point', 'up', X), 0: ('up', 'point', X), 2: ('shrug', 'shrug', dict(brows='up')), 4: ('head', 'head', WS),
         6: ('up', 'up', X), 8: ('chin', 'rest', dict(brows='flat')), 10: ('rest', 'open', dict(brows='flat', smile=1)),
         '10:catch': ('cross', 'cross', dict(brows='worried')), 12: ('point', 'point', WS), 14: ('head', 'head', WS),
         16: ('chin', 'rest', dict(brows='worried', tired=.3)), '17:Would': ('rest', 'rest', dict(brows='up', eyes='wide', look=0))}
SPOSE = {1: ('open', 'clasp', {}), 3: ('present', 'clasp', {}), 5: ('offer', 'clasp', {}), 7: ('present', 'clasp', {}),
         9: ('open', 'clasp', {}), 11: ('present', 'clasp', {}), 13: ('open', 'open', {}), 15: ('offer', 'clasp', {}),
         17: ('open', 'clasp', dict(look=0))}
OVER = [
    dict(k='tag', txt='$39,900', sub='PROMISED IN 2019', a='L1+.35', b='L3-.05', y=560),
    dict(k='photo', img='ct_front.jpg', label='TESLA CYBERTRUCK', logo='logo_tesla.png', a='L3-.05', b='S1+.05', y=430),
    dict(k='stamp', txt='~$100K', col='R', a='3:hundred', b='S1+.05', y=760, rot=-8),
    dict(k='card', rows=[('0-60 MPH', 50, 'ink'), ('2.6 SECONDS', 76, 'red'), ('Cyberbeast, Tesla figure', 38, 'ink')], a='5:two-.05', b='E6+.2', y=600),
    dict(k='card', rows=[('TOWING', 50, 'ink'), ('11,000 LB', 80, 'red')], a='7:eleven-.05', b='E7+.25', y=560),
    dict(k='card', rows=[('Promised: 500+ miles', 52, 'ink'), ('EPA rated: ~320 miles', 58, 'red')], a='9:Promised', b='S3+.05', y=560),
    dict(k='stamp', txt='RECALL', col='R', a='11:fall', b='13:Forty-.05', y=520, rot=-10, size=110),
    dict(k='card', rows=[('NHTSA recall 25V-170', 44, 'ink'), ('46,096 TRUCKS', 74, 'red'), ('trim panel could detach', 42, 'ink')],
         a='13:Forty-.05', b='S4+.05', y=560, jolt='13:Almost'),
    dict(k='chips', rows=[('THE CATCH', 'PANEL COULD FALL OFF', 'R', 'L14'), ('THE FIX', 'REPLACED FREE', 'G', '15:free')],
         a='L14', b='S5+.05', y=560),
    dict(k='photo', img='ct_rear.jpg', label='STILL TEMPTED?', logo='logo_tesla.png', a='L16', b='L17-.05', y=470, rot=3),
]
FINAL = [('Would you still', 74, 'Y'), ('buy a Cybertruck?', 74, 'Y'), ('YES or NO below', 64, 'W')]
PUNCH = [('3:hundred', .05), ('5:Zero', .05), ('7:eleven', .03), ('11:fall', .07), ('13:Forty', .05), ('15:free', .03)]
SHAKE = ['12:many']
FLASH = ['11:fall+.6']
CUES = [('3:hundred+.25', 'cha', .35), ('5:Zero', 'vroom', .6), ('5:Zero+.05', 'screech', .3), ('5:Zero+1.35', 'whoosh', .45),
        ('7:tows', 'thump', .3), ('11:fall+.6', 'clank', .7), ('12:many', 'buzzer', .25), ('13:Forty', 'boom', .3), ('15:free', 'ding', .2)]
THUMB = dict(t='11:fall+.7', photos=[('ct_front.jpg', '2024 CYBERTRUCK', 'logo_tesla.png')],
             text=[('WOULD YOU STILL', 92, 'W'), ('BUY ONE?', 140, 'Y')])
