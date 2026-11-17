"""Dialogue for the Supra/Z4 skit. (speaker, text, scene). Speakers: B = buyer (Fenrir), S = salesman (Orus)."""
LINES = [
    ("B", "Why does this Toyota Supra have a BMW engine?!", 1),
    ("S", "...It's a very good engine.", 1),
    ("B", "The old Supra had a Toyota engine!", 1),
    ("S", "The old one did.", 1),
    ("B", "What else is BMW?", 1),
    ("S", "The platform. The gearbox.", 1),
    ("B", "The switches too?!", 2),
    ("S", "Window motors. Lock switches. Parking brake button. All BMW parts.", 2),
    ("B", "So what did Toyota do?", 2),
    ("S", "Its own suspension tuning. Its own body.", 2),
    ("B", "Where's it built?", 3),
    ("S", "Austria. Same factory as the BMW Z4.", 3),
    ("B", "So it's a BMW?", 3),
    ("S", "Toyota says it's a Supra.", 3),
    ("B", "Is it a real Supra?", 4),
    ("S", "Let them decide.", 4),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
DIRECTION = ("TTS this fast-paced comedy skit at a car dealership. The Salesman is completely flat, calm and deadpan "
             "the whole time, never reacting. The Buyer starts outraged, gets baffled, then ends resigned; real heat "
             "and shouting on 'The old Supra had a Toyota engine!'. Snappy timing, no long pauses between lines.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t}" for s, t, _ in LINES) + "\n"
