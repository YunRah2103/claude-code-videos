"""Dialogue for the bmw-dealership-experience skit. (speaker, text, scene). Speakers: B = buyer (Fenrir), S = salesman (Orus).
Scenes 1-6 BMW showroom (M5 -> 3 Series -> Z4 M40i on the platform), 7 front desk."""
LINES = [
    ("B", "Hi, I'm looking to buy a BMW.", 1),
    ("S", "Welcome, sir. Our flagship, the M5. Listen to that engine.", 1),
    ("B", "It's loud inside the car.", 2),
    ("S", "Yes. Part of that comes through the speakers.", 2),
    ("B", "The speakers?!", 2),
    ("S", "BMW calls it Active Sound Design. The engine is real. The volume is assisted.", 2),
    ("B", "Fine. What about the heated seats?", 3),
    ("S", "At the time, in some countries, those were a subscription. About eighteen dollars a month.", 3),
    ("B", "A month?! For seats?!", 4),
    ("S", "Or a hundred and eighty a year. Or about four-fifteen, unlimited. If you stop paying, the seats turn off.", 4),
    ("B", "They're already in the seat!", 5),
    ("S", "The hardware is yours, sir. The warmth is rented. Now, the Z4 M40i. Three-litre inline-six, eight-speed automatic, built in Austria.", 5),
    ("B", "I saw a Toyota Supra with the same engine.", 6),
    ("S", "Same engine. Same gearbox. Same factory. Different badge.", 6),
    ("B", "Okay. I'll take the Z4.", 7),
    ("S", "Wonderful. Would you like to add heated seats?", 7),
    ("B", "How much?", 7),
    ("S", "Eighteen dollars a month.", 7),
    ("S", "Would you pay a monthly fee for heated seats?", 7),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
DIRECTION = ("TTS this fast-paced comedy skit at a BMW dealership. The Salesman is completely flat, calm and deadpan the whole "
             "time, never reacting, same polite bored tone on every answer, even when admitting embarrassing things. Say BMW as "
             "'B M W', M5 as 'M five', Z4 as 'Z four', M40i as 'M forty i', and four-fifteen as 'four fifteen'. The Buyer starts "
             "cheerful and keen, then gets more and more incredulous: surprised at 'The speakers?!', shouting at 'A month?! For "
             "seats?!' and 'They're already in the seat!', suspicious at the Supra line, then flat and defeated at 'How much?'. "
             "The Salesman's last line is said slowly and straight to the camera, as a question to the audience. Snappy timing, "
             "no long pauses between lines.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t}" for s, t, _ in LINES) + "\n"
