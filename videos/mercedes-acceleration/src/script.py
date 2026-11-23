"""Dialogue for the mercedes-acceleration skit. (speaker, text, scene). Speakers: B = buyer (Fenrir), S = salesman (Charon).
Scenes: 1 Mercedes showroom, 2 on the road (subscription expires), 3 online store / The Drive, 4 back at the showroom."""
LINES = [
    ("S", "Sir, your Mercedes has more power than you paid for.", 1),
    ("B", "What?", 1),
    ("S", "It makes 288 horsepower. The motors can make 349.", 1),
    ("S", "The rest is $1,200 a year.", 1),
    ("B", "No, no, no, no!", 2),
    ("S", "Mercedes listed it in November 2022.", 3),
    ("S", "A spokesperson later told The Drive nobody was ever allowed to buy it.", 3),
    ("S", "So technically, sir, you were never overcharged.", 4),
    ("S", "Would you pay $1,200 a year for 0.9 seconds? Yes, or no?", 4),
]
SAY = {"288": "two hundred eighty-eight", "349": "three hundred forty-nine", "$1,200": "twelve hundred dollars",
       "2022": "twenty twenty-two", "0.9": "zero point nine"}
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Charon")}
DIRECTION = ("TTS this very fast-paced comedy skit at a car dealership. The Salesman is completely flat, calm and deadpan "
             "the whole time, bored, never reacting. The Buyer is loud and outraged: a shocked shout on 'What?', then pure "
             "panic, screaming 'No, no, no, no!' as his car dies. Snappy timing, no pauses between lines.\n\n")
def spoken(text):
    for k, v in SAY.items(): text = text.replace(k, v)
    return text
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {spoken(t)}" for s, t, _ in LINES) + "\n"
