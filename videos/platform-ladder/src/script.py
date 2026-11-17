"""Dialogue for the platform-ladder skit. (speaker, text, scene). Speakers: B = buyer (Fenrir), S = salesman (Orus).
Scenes: 1 VW showroom, 2 Porsche, 3 Bentley, 4 Lamborghini, 5 back at VW."""
LINES = [
    ("B", "This Volkswagen shares a platform with a Lamborghini?!", 1),
    ("S", "Yes. The Touareg. The cheap one.", 1),
    ("B", "What else?", 1),
    ("S", "Follow me.", 1),
    ("B", "A Porsche?!", 2),
    ("S", "Same platform. About sixty-nine thousand dollars.", 2),
    ("B", "And a Bentley?!", 3),
    ("S", "Same platform. Well over one hundred and sixty thousand.", 3),
    ("B", "And a Lamborghini?!", 4),
    ("S", "Same platform. About two hundred and thirty thousand.", 4),
    ("B", "So it's all the same car?", 4),
    ("S", "Same platform. Different engines, bodies and badges.", 4),
    ("B", "Then which one should I buy?", 5),
    ("S", "Let them decide.", 5),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
DIRECTION = ("TTS this fast-paced comedy skit at car dealerships. The Salesman is completely flat, calm and deadpan "
             "the whole time, never reacting, same bored tone on every price. The Buyer's outrage escalates with every "
             "showroom: shocked at the Volkswagen, louder at the Porsche, shouting at the Bentley, near-screaming at the "
             "Lamborghini, then deflates into quiet resignation on 'So it's all the same car?' and 'Then which one should "
             "I buy?'. Snappy timing, no long pauses between lines.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t}" for s, t, _ in LINES) + "\n"
