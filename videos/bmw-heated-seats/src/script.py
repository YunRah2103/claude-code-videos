"""Dialogue for the bmw-heated-seats skit. (speaker, text, scene). Speakers: B = buyer (Fenrir), S = salesman (Orus).
Scenes: 1 BMW showroom, 2 map room, 3 payment screen, 4 press conference, 5 back at the showroom."""
LINES = [
    ("B", "My heated seats won't turn on!", 1),
    ("S", "Have you paid this month?", 1),
    ("B", "Paid for what?!", 1),
    ("S", "Eighteen dollars. Per month.", 1),
    ("B", "For heated seats I already own?!", 1),
    ("S", "The hardware's installed. The software's locked.", 1),
    ("B", "Since when?!", 2),
    ("S", "2022. Not in America.", 2),
    ("B", "What if I stop paying?", 3),
    ("S", "The seats turn off.", 3),
    ("B", "And forever?", 3),
    ("S", "About four hundred and fifteen dollars.", 3),
    ("B", "This is outrageous!", 4),
    ("S", "Customers agreed. BMW dropped it.", 4),
    ("B", "So everything's free now?", 4),
    ("S", "Seats, yes. Driving assistance, no.", 4),
    ("B", "Would you pay for heated seats?", 5),
    ("S", "Let them decide.", 5),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
DIRECTION = ("TTS this fast-paced comedy skit at a car dealership. The Salesman is completely flat, calm and deadpan "
             "the whole time, never reacting, same bored tone on every answer. Say 2022 as 'twenty twenty-two' and BMW as "
             "'B M W'. The Buyer starts already upset and his outrage escalates with every answer: annoyed, then shocked, "
             "then shouting at 'For heated seats I already own?!', near-screaming at 'This is outrageous!', then deflates into "
             "quiet resignation on 'So everything's free now?' and 'Would you pay for heated seats?'. Snappy timing, no long "
             "pauses between lines.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t}" for s, t, _ in LINES) + "\n"
