"""02 Range Rover: "Would you buy a used Range Rover for the price of a Corolla?"  B = buyer (Fenrir), S = salesman (Orus).
Scenes: 1 used-car lot, 2 country road, 3 finance office, 4 workshop, 5 rainy street with tow truck, 6 lot at dusk."""
SLUG = 'range_rover'
LINES = [
    ("B", "A Range Rover? Cheaper than a new Corolla?!", 1),
    ("S", "2016. About eighteen grand.", 1),
    ("B", "It was eighty-five grand new!", 1),
    ("S", "Almost. Yes.", 1),
    ("B", "Leather! Air suspension! The badge!", 2),
    ("S", "All yours.", 2),
    ("B", "I'm basically royalty.", 2),
    ("S", "Basically.", 2),
    ("B", "Where do I sign?!", 3),
    ("S", "Right here.", 3),
    ("B", "Wait. Why is it so cheap?", 3),
    ("S", "RepairPal rates its reliability two out of five.", 4),
    ("B", "Two?!", 4),
    ("S", "Average repairs, about twelve hundred a year.", 4),
    ("B", "And if the air suspension goes?", 5),
    ("S", "Around a thousand dollars. Per corner.", 5),
    ("B", "Per corner?!", 5),
    ("S", "It has four.", 5),
    ("B", "So is it a bargain?", 6),
    ("S", "Bargain, or trap?", 6),
]
DIRECTION = ("TTS this fast-paced comedy skit at a used-car lot. Keep the pace high and snappy, no long pauses. The Salesman "
             "is flat, calm and deadpan the whole time, same bored tone on every answer. Say 2016 as 'twenty sixteen' and "
             "RepairPal as 'Repair Pal'. The Buyer opens thrilled and disbelieving, gets giddy and posh on 'I'm basically "
             "royalty', eager on 'Where do I sign?!', then suspicious on 'Wait. Why is it so cheap?', panics on 'Two?!', "
             "shrieks 'Per corner?!', and ends quiet and unsure. The Salesman says the last line slowly, straight to camera.\n\n")
SPOKEN = {"2016": "twenty sixteen", "repairpal": "repair pal", "eighty-five": "eighty five"}
HOLD = {1: .3, 5: .25, 7: .25, 9: .2, 10: .45, 11: .4, 13: .35, 15: .3, 17: .25}

# ---------------------------------------------------------------- picture (anchors: see render.A)
ODD = 'knight'                                  # a knight in full armour sipping tea, in every scene, never mentioned
SALES = {'suit': '2f4a34', 'pants': '2f4a34', 'tie': '7a1f28'}   # used-luxury salesman: green tweed, burgundy tie
BADGE = (40, 110, 70)
MUSIC_AT = 20.0
C = 459
SCN = [
    dict(bg='lot', time='day', cars=[dict(kind='rangerover', x0=C - 290, g=905, L=580)], odd=(840, 945, .68)),
    dict(bg='country', cars=[dict(kind='rangerover', x0=C - 280, g=955, L=560, anim='in_left')], odd=(90, 840, .45)),
    dict(bg='office', odd=(880, 945, .62)),
    dict(bg='workshop', sign='SERVICE BAY', cars=[dict(kind='rangerover', x0=C - 290, g=894, L=580, anim='lift')], odd=(900, 945, .62)),
    dict(bg='night', tow=True, cars=[dict(kind='rangerover', x0=110, g=905, L=560, sag_at=[('15:corner', .7)], drop_at='17:four')],
         odd=(775, 915, .55)),
    dict(bg='lot', time='dusk', cars=[dict(kind='rangerover', x0=C - 290, g=905, L=580)], odd=(840, 945, .68)),
]
X = dict(brows='up', eyes='wide', smile=1); WS = dict(brows='angry', eyes='wide', sweat=1)
BPOSE = {'open': ('point', 'up', X), 0: ('up', 'point', X), 2: ('head', 'head', dict(brows='up', eyes='wide')), 4: ('open', 'open', X),
         6: ('raise1', 'rest', dict(brows='up', smile=1, tired=.3)), 8: ('rest', 'point', X),
         '10:Wait': ('chin', 'rest', dict(brows='worried')), 12: ('head', 'head', WS), 14: ('shrug', 'shrug', dict(brows='worried')),
         16: ('up', 'up', WS), '17:four': ('head', 'head', WS), 18: ('chin', 'rest', dict(brows='worried', tired=.3)),
         '19:Bargain': ('rest', 'rest', dict(brows='up', eyes='wide', look=0))}
SPOSE = {1: ('open', 'clasp', {}), 3: ('offer', 'clasp', {}), 5: ('present', 'clasp', {}), 7: ('open', 'clasp', {}),
         9: ('offer', 'clasp', {}), 11: ('open', 'clasp', {}), 13: ('present', 'clasp', {}), 15: ('open', 'clasp', {}),
         17: ('raise1', 'clasp', {}), 19: ('open', 'clasp', dict(look=0))}
OVER = [
    dict(k='vs', pair=[('rr_front.jpg', 'USED 2016 ~$18K', None), ('corolla.jpg', 'COROLLA: ~$23K NEW', 'logo_toyota.png')],
         a='L1-.3', b='L2-.05', y=520),
    dict(k='card', rows=[('2016 Range Rover, new', 48, 'ink'), ('$84,950', 84, 'red'), ('base price', 40, 'ink')], a='L2-.05', b='S1+.05', y=560),
    dict(k='chips', rows=[('LEATHER', 'YES', 'G', '4:Leather'), ('AIR SUSPENSION', 'YES', 'G', '4:Air'), ('THE BADGE', 'YES', 'G', '4:badge')],
         a='4:Leather-.05', b='L6', y=470),
    dict(k='stamp', txt='ROYALTY', col='G', a='6:royalty', b='S2+.05', y=600, rot=-8),
    dict(k='photo', img='rr_rear.jpg', label='SIGN HERE', logo=None, a='L8', b='L10', y=470, rot=2),
    dict(k='stamp', txt='WHY SO CHEAP?', col='R', a='10:cheap-.1', b='S3+.05', y=560, size=72, rot=-6),
    dict(k='card', rows=[('RepairPal reliability, 2016', 42, 'ink'), ('2.0 / 5', 92, 'red'), ('Consumer Reports: Land Rover', 34, 'ink'),
                         ('among the bottom brands', 34, 'ink')], a='11:two-.05', b='13:twelve-.05', y=560, jolt='12:Two'),
    dict(k='card', rows=[('Average repairs', 48, 'ink'), ('~$1,205 / YEAR', 76, 'red'), ('RepairPal estimate', 38, 'ink')],
         a='13:twelve-.05', b='S4+.05', y=560),
    dict(k='card', rows=[('Air spring, one corner', 46, 'ink'), ('~$1,000', 92, 'red'), ('typical shop estimate', 38, 'ink')],
         a='15:thousand-.05', b='L17', y=540, jolt='16:corner'),
    dict(k='stamp', txt='x 4', col='R', a='17:four', b='S5+.05', y=560, size=150, rot=-8),
    dict(k='vs', pair=[('rr_front.jpg', 'BARGAIN?', None), ('lr_badge.jpg', 'OR TRAP?', None)], a='L18', b='L19-.05', y=520),
]
FINAL = [('Bargain', 90, 'Y'), ('or trap?', 90, 'Y'), ('Comment below.', 64, 'W')]
PUNCH = [('1:eighteen', .04), ('2:eighty', .04), ('11:two', .06), ('12:Two', .05), ('15:thousand', .05), ('16:corner', .05), ('17:four', .07)]
SHAKE = ['16:corner', '17:four']
FLASH = ['11:two']
CUES = [('1:eighteen+.2', 'cha', .3), ('S1', 'vroom', .35), ('6:royalty', 'ding', .2), ('L9', 'click', .5), ('11:two', 'buzzer', .25),
        ('12:Two', 'boom', .25), ('15:corner', 'hiss', .5), ('16:corner', 'slide', .3), ('17:four', 'crash', .35), ('17:four', 'hiss', .45)]
THUMB = dict(t='17:four+.5', photos=[('rr_front.jpg', '2016 RANGE ROVER', None), ('corolla.jpg', 'TOYOTA COROLLA', 'logo_toyota.png')],
             text=[('CHEAPER THAN', 92, 'W'), ('A COROLLA?!', 128, 'Y')])
