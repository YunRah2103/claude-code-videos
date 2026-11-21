"""The real Tesla dealership experience. (speaker, text, scene). B = buyer (Fenrir, series voice), S = salesman (Orus).
Scenes: 1 gallery, 2 Cybertruck bay, 3 interior display, 4 test drive, 5 parked kerb, 6 Roadster plinth, 7 garage reveal,
8 driveway. Every number is in FACTS.md."""
LINES = [
    ("B", "Hi! I'd like to buy a Tesla.", 1),
    ("S", "We don't do dealerships. Download the app.", 1),
    ("B", "You're standing in a dealership!", 1),
    ("S", "It's a gallery. I'm basically furniture.", 1),
    ("B", "Okay, furniture. How much is the Model Y?", 1),
    ("S", "It's in the app.", 1),
    ("B", "The Cybertruck? Wasn't that forty grand?", 2),
    ("S", "In 2019, they said $39,900.", 2),
    ("B", "And now?", 2),
    ("S", "Nearly double.", 2),
    ("B", "At least it's built tough.", 2),
    ("S", "Very. Forty-six thousand recalled. A steel panel could fall off.", 2),
    ("B", "Fall off?!", 2),
    ("S", "Fixed. Better glue.", 2),
    ("B", "Where's the turn signal stalk?", 3),
    ("S", "Buttons on the wheel. Or a stalk retrofit. $595.", 3),
    ("S", "Gears are on the touchscreen.", 3),
    ("B", "And if the screen dies?", 3),
    ("S", "Backup buttons. On the ceiling.", 3),
    ("B", "Can I at least test drive it?", 3),
    ("S", "Book it in the app.", 3),
    ("B", "Does it drive itself?", 4),
    ("S", "Full Self-Driving. Supervised. $99 a month.", 4),
    ("B", "Can't I just buy it?", 4),
    ("S", "Not since February. Subscription only.", 4),
    ("B", "So I pay monthly to supervise it?", 4),
    ("S", "Correct.", 4),
    ("B", "Why did we just brake?!", 4),
    ("S", "Phantom braking. The government investigated.", 4),
    ("B", "There's nothing there!", 4),
    ("S", "Hence, phantom.", 4),
    ("B", "Just let me out. Where's the handle?", 5),
    ("S", "It pops out. Unless the power dies.", 5),
    ("B", "Then what?!", 5),
    ("S", "Find the hidden manual release.", 5),
    ("B", "Hidden?!", 5),
    ("S", "China plans to ban those from 2027.", 5),
    ("B", "Forget it. I want the Roadster!", 6),
    ("S", "Announced 2017. Promised for 2020.", 6),
    ("B", "So it's here?", 6),
    ("S", "Shown again last month. Production: 2028. Reportedly.", 6),
    ("B", "Can I pre-order?", 6),
    ("S", "In the app.", 6),
    ("B", "I want to speak to your manager.", 7),
    ("S", "Okay. Confession. I don't work for Tesla.", 7),
    ("B", "What?!", 7),
    ("S", "Tesla sells direct. This is my garage.", 7),
    ("B", "Then who are you?!", 7),
    ("S", "A guy who really likes the app.", 7),
    ("S", "So... download the app?", 8),
    ("B", "No. I'm buying a Toyota.", 8),
    ("S", "Boring.", 8),
    ("B", "Boring has door handles.", 8),
]
CUT = {1: [0]}   # "Cool." spoken in the TTS take, cut so the hook lands by 3 s
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
HOLD = {5: .3, 9: .35, 13: .3, 18: .35, 26: .5, 30: .35, 42: .35, 44: .6, 46: .3, 48: .5}
SPOKEN = {"2019": "twenty nineteen", "$39,900": "thirty nine thousand nine hundred dollars", "$595": "five hundred ninety five dollars",
          "$99": "ninety nine dollars", "2027": "twenty twenty seven", "2017": "twenty seventeen", "2020": "twenty twenty",
          "2028": "twenty twenty eight", "self-driving": "self driving", "forty-six": "forty six", "pre-order": "pre order",
          "cybertruck": "cyber truck"}
DIRECTION = ("TTS this fast-paced comedy sketch set in a car showroom. The Salesman speaks with a laid-back Californian "
             "tech-startup accent, slight vocal fry, totally flat and deadpan, bored, never excited, never reacting. "
             "The Buyer is friendly and hopeful at first, then gets more and more exasperated with every answer, shouting at "
             "'Fall off?!', 'Why did we just brake?!' and 'Then who are you?!', then completely deflated, quiet and tired for "
             "his last two lines. Say 2019 as 'twenty nineteen', $39,900 as 'thirty-nine thousand nine hundred dollars', "
             "$595 as 'five hundred ninety-five dollars', $99 as 'ninety-nine dollars', 2017 as 'twenty seventeen', 2020 as "
             "'twenty twenty', 2027 as 'twenty twenty-seven', 2028 as 'twenty twenty-eight'. Snappy sitcom timing, no long "
             "pauses between lines.\n\n")
TTS_TEXT = {1: "Cool. We don't do dealerships. Download the app."}   # the line as sent to the one TTS call
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {TTS_TEXT.get(i, t)}" for i, (s, t, _) in enumerate(LINES)) + "\n"
