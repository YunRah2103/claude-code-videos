"""Dialogue for the mercedes-acceleration-subscription skit. (speaker, text, scene). B = buyer (Fenrir), S = salesman (Orus).
Scenes: 1 dealership lot, 2 service bay, 3 dyno room, 4 finance office, 5 Mercedes showroom."""
LINES = [
    ("B", "I bought a Mercedes and they want sixty dollars a month for the horsepower?!", 1),
    ("S", "Sir, that's Acceleration Increase.", 1),
    ("B", "Does it get new motors?", 2),
    ("S", "No. Same car. It's a software unlock.", 2),
    ("B", "How much more power?", 3),
    ("S", "Sixty horsepower. Two-eighty-eight becomes three-forty-eight. Almost a second off zero to sixty.", 3),
    ("B", "Sixty dollars a month?!", 4),
    ("S", "Or six hundred a year. That's about ten dollars a horsepower, every year. Great value.", 4),
    ("B", "I'm renting power I already own!", 5),
    ("S", "Nobody's forcing you, sir. You can stay at two-eighty-eight.", 5),
    ("S", "Would you pay sixty dollars a month for sixty horsepower? Let them decide.", 5),
]
SPOKEN = {}
EXTRA_WORDS = {}
HOLD = {3: 0.15, 5: 0.35, 7: 0.35}                 # reveal holds after key answers (retime.py)
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
DIRECTION = ("TTS this fast-paced comedy skit at a car dealership. The Salesman is completely flat, calm and deadpan the "
             "whole time, bored, never reacting, and he says 'Great value' with zero enthusiasm. The Buyer starts already "
             "outraged, shouting from the very first word, and stays furious: disbelieving on 'Does it get new motors?', "
             "shouting again at 'Sixty dollars a month?!', near-screaming 'I'm renting power I already own!'. In the last "
             "line the Salesman turns and asks the viewer directly, same flat voice. Snappy timing, no long pauses between lines.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t}" for s, t, _ in LINES) + "\n"
