"""Dialogue for the mercedes-acceleration skit. (speaker, text, scene). Speakers: B = buyer (Fenrir), S = salesman (Orus).
Scenes: 1 Mercedes showroom, 2 dyno cell, 3 store screen, 4 drag strip, 5 backlash room, 6 back at the showroom.
SAY maps a displayed token (trailing punctuation stripped) to how it is spoken; the TTS prompt and the aligner both use it."""
LINES = [
    ("S", "Sir, your Mercedes has more power than you paid for.", 1),
    ("B", "It WHAT?!", 1),
    ("S", "This EQE 350 makes 288 horsepower. The motors can make 349.", 2),
    ("B", "Then unlock it!", 2),
    ("S", "$1,200. A year.", 3),
    ("B", "A YEAR?!", 3),
    ("S", "Renew every year, or stay at 288.", 3),
    ("B", "For what?!", 4),
    ("S", "61 more horsepower. Zero to sixty: 6.0 down to 5.1.", 4),
    ("B", "Less than a second?!", 4),
    ("S", "About $20 per horsepower. Per year.", 4),
    ("B", "The car starts at eighty-five grand!", 4),
    ("S", "Mercedes listed it in November 2022. People were furious.", 5),
    ("B", "Good!", 5),
    ("S", "Then Mercedes told The Drive nobody was ever allowed to buy it.", 5),
    ("B", "Nobody?!", 5),
    ("S", "They changed the price and added a one-time purchase.", 5),
    ("B", "So I was furious for nothing?!", 6),
    ("S", "Technically, sir, you were never overcharged.", 6),
    ("S", "Would you pay $1,200 a year to be 0.9 seconds faster? Yes, or no?", 6),
]
SAY = {"EQE": "E Q E", "350": "three fifty", "288": "two eighty-eight", "349": "three forty-nine", "$1,200": "twelve hundred dollars",
       "61": "sixty-one", "6.0": "six point oh", "5.1": "five point one", "$20": "twenty dollars", "2022": "twenty twenty-two",
       "0.9": "zero point nine", "eighty-five": "eighty-five", "one-time": "one-time"}
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
TRAIL = ".,?!:;"
def spoken(word):
    core = word.rstrip(TRAIL)
    return SAY.get(core, core) + word[len(core):]
def say_line(text): return " ".join(spoken(w) for w in text.split())
DIRECTION = ("TTS this fast-paced comedy skit at a Mercedes dealership, with lively, punchy energy and no long pauses. "
             "The Salesman is completely calm, flat and deadpan the whole time, never reacting, crisp and quick, with a tiny smug "
             "pause before 'A year.' and before 'you were never overcharged.' The Buyer starts already confused and his outrage "
             "escalates: shocked at 'It WHAT?!', shouting 'A YEAR?!', exasperated at 'Less than a second?!', near-screaming "
             "'The car starts at eighty-five grand!', then gleeful on 'Good!', stunned on 'Nobody?!', and deflated on 'So I was "
             "furious for nothing?!'. The final question is the Salesman turning to the audience, still deadpan but clear.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {say_line(t)}" for s, t, _ in LINES) + "\n"
