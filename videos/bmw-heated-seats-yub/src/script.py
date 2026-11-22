"""Dialogue for the bmw-heated-seats-yub skit. (speaker, text, scene). Speakers: B = buyer (Fenrir), S = BMW salesman (Charon).
Scenes: 1 BMW showroom, 2 BMW store screen, 3 map room, 4 factory line (the why), 5 press conference, 6 showroom again."""
LINES = [
    ("S", "Sir, your seats are already heated. You just haven't paid for it.", 1),
    ("B", "They're right under me!", 1),
    ("S", "Installed at the factory. Locked in software.", 1),
    ("B", "How much to unlock them?!", 2),
    ("S", "Eighteen dollars. A month.", 2),
    ("B", "A month?!", 2),
    ("S", "Or about one seventy-six a year.", 2),
    ("B", "Who even pays this?!", 3),
    ("S", "South Korea. Britain. Germany. From 2022.", 3),
    ("B", "And if I want them forever?", 3),
    ("S", "About four hundred and six dollars.", 3),
    ("B", "Why build a car like this?!", 4),
    ("S", "One car for everyone. Switch it on later. For a fee.", 4),
    ("B", "Did anyone actually pay?", 5),
    ("S", "Not enough. In 2023, BMW dropped it.", 5),
    ("B", "Ha! We won!", 5),
    ("S", "Remote start? A hundred and five a year.", 6),
    ("B", "Would you pay monthly for something already in your car? Yes, or no?", 6),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Charon")}
DIRECTION = ("TTS this fast-paced comedy skit at a car dealership. The Salesman is completely flat, calm and deadpan "
             "the whole time, never reacting, same bored tone on every answer. Say 2022 as 'twenty twenty-two', 2023 as "
             "'twenty twenty-three' and BMW as 'B M W'. The Buyer starts already upset and his outrage escalates with every "
             "answer: annoyed, then shocked, then shouting 'A month?!', then smug and triumphant on 'Ha! We won!', then "
             "deflated. He asks the last question straight to the viewer, slowly and clearly. Snappy timing, no long "
             "pauses between lines.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t}" for s, t, _ in LINES) + "\n"
