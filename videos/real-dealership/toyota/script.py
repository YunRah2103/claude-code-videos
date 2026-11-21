"""The real Toyota dealership experience. (speaker, text, scene). B = buyer (Fenrir, series voice), S = salesman (Charon).
Scenes: 1 showroom, 2 Supra stage, 3 twins corner, 4 EV corner, 5 Land Cruiser queue outside, 6 Prius test drive,
7 after-hours confession, 8 closing. Every number is in FACTS.md."""
LINES = [
    ("B", "I want an exciting Toyota!", 1),
    ("S", "This is a Toyota dealership.", 1),
    ("B", "So what's fun here?", 1),
    ("S", "Have you considered a Corolla?", 1),
    ("B", "A Corolla?!", 1),
    ("S", "Over fifty million sold. Best-selling car ever.", 1),
    ("B", "Fifty million people can't all be bored!", 1),
    ("S", "They can. Quietly.", 1),
    ("B", "Then the Supra! A legend!", 2),
    ("S", "Built in Austria. With a BMW engine.", 2),
    ("B", "BMW?!", 2),
    ("S", "It shares a platform with the BMW Z4.", 2),
    ("B", "I'll take it anyway!", 2),
    ("S", "Production ended in March.", 2),
    ("B", "Of course it did.", 2),
    ("S", "Have you considered a Corolla?", 2),
    ("B", "GR86! That's pure Toyota.", 3),
    ("S", "Built by Subaru.", 3),
    ("B", "Then what's that?", 3),
    ("S", "The Subaru BRZ.", 3),
    ("B", "It's the same car!", 3),
    ("S", "Different bumper.", 3),
    ("B", "Fine. Something electric.", 4),
    ("S", "The bZ4X.", 4),
    ("B", "The what?", 4),
    ("S", "Nobody could say it. Now it's just bZ.", 4),
    ("B", "Is it any good?", 4),
    ("S", "In 2022, a recall. The wheels could come off.", 4),
    ("B", "The wheels?!", 4),
    ("S", "Toyota offered to buy them back.", 4),
    ("S", "Have you considered a Corolla?", 4),
    ("B", "Land Cruiser. Final answer.", 5),
    ("S", "Please take a number.", 5),
    ("B", "How long's the wait?", 5),
    ("S", "In Japan, up to four years. Then they stopped taking orders.", 5),
    ("B", "Four years?!", 5),
    ("S", "Bring snacks.", 5),
    ("S", "Let's test drive a Prius.", 6),
    ("B", "A Prius?!", 6),
    ("S", "First mass-produced hybrid. 1997.", 6),
    ("B", "Wait... this actually looks cool.", 6),
    ("S", "Don't tell anyone.", 6),
    ("B", "Be honest. What do you drive?", 7),
    ("S", "A 1998 Corolla.", 7),
    ("B", "Seriously?", 7),
    ("S", "I've been trying to kill it for years. It won't die.", 7),
    ("B", "Why kill it?!", 7),
    ("S", "So I can buy a Supra. Too late now.", 7),
    ("B", "Fine. One Corolla.", 8),
    ("S", "Congratulations. It will outlive you.", 8),
    ("B", "Good. Something should.", 8),
]
CUT = {1: [0]}   # "Sir," spoken in the TTS take, cut so the hook lands by 3 s
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Charon")}
HOLD = {3: .3, 7: .4, 13: .35, 15: .35, 21: .5, 27: .2, 29: .4, 30: .3, 36: .4, 41: .35, 43: .45, 45: .3, 47: .5, 49: .4}
SPOKEN = {"best-selling": "best selling", "bmw": "b m w", "z4": "z four", "gr86": "g r eighty six", "brz": "b r z",
          "bz4x": "b z four x", "bz": "b z", "2022": "twenty twenty two", "mass-produced": "mass produced",
          "1997": "nineteen ninety seven", "1998": "nineteen ninety eight"}
DIRECTION = ("TTS this fast-paced comedy sketch set in a Toyota showroom. The Salesman is extremely calm, polite and sensible, "
             "speaking softly with a light, natural Japanese accent, completely deadpan, never excited, never reacting. "
             "The Buyer starts pumped up and eager, then gets more and more frustrated with every answer, shouting at "
             "'A Corolla?!', 'BMW?!', 'It's the same car!' and 'The wheels?!', briefly surprised and impressed at 'Wait... this "
             "actually looks cool', then completely deflated, quiet and tired on 'Fine. One Corolla.' and 'Good. Something "
             "should.' Say BMW as 'B M W', Z4 as 'Z four', GR86 as 'G R eighty-six', BRZ as 'B R Z', bZ4X as 'B Z four X', "
             "bZ as 'B Z', 2022 as 'twenty twenty-two', 1997 as 'nineteen ninety-seven', 1998 as 'nineteen ninety-eight'. "
             "Snappy sitcom timing, no long pauses between lines.\n\n")
TTS_TEXT = {1: 'Sir, this is a Toyota dealership.'}   # the line as sent to the one TTS call
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {TTS_TEXT.get(i, t)}" for i, (s, t, _) in enumerate(LINES)) + "\n"
