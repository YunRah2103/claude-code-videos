"""Dialogue for the dodge-charger-fake-exhaust skit. (speaker, text, scene). Speakers: B = buyer (Fenrir), S = salesman (Orus).
Scenes: 1 Dodge showroom, 2 garage (speaker rig on a bench), 3 muscle-car meet at night, 4 recording studio,
5 suburban street at dawn, 6 drag strip at night."""
LINES = [
    ("B", "My ELECTRIC Dodge has a fake exhaust that's as loud as a Hellcat?!", 1),
    ("S", "It's a speaker. Not an exhaust.", 1),
    ("B", "A speaker?!", 2),
    ("S", "Speakers, a tuning chamber and an amp. No exhaust gas.", 2),
    ("B", "How loud?", 3),
    ("S", "Dodge says a hundred and twenty-six decibels. Same as the Hellcat V8.", 3),
    ("B", "Fratzonic?", 3),
    ("S", "Named after Dodge's Fratzog logo.", 3),
    ("B", "So it's a recording?", 4),
    ("S", "Dodge says it makes the sound itself. Reviewers say it never shifts gears.", 4),
    ("B", "Can I make it louder?", 5),
    ("S", "Drag and Track modes, yes. Stealth mode is for the neighbours.", 5),
    ("B", "But gas is still faster, right?", 6),
    ("S", "Dodge says zero to sixty in three point three. The gas Scat Pack? Three point nine.", 6),
    ("B", "The fake one wins?!", 6),
    ("B", "Fake exhaust or real engine: which would you take?", 6),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
DIRECTION = ("TTS this fast-paced comedy skit at a car dealership. The Salesman is completely flat, calm and deadpan "
             "the whole time, never reacting, same bored tone on every answer. Say Fratzonic as 'frats-ON-ic' and Fratzog "
             "as 'frats-og', V8 as 'V eight'. The Buyer starts already shocked and loud, stressing ELECTRIC, then is baffled, "
             "curious, excited at 'Can I make it louder?', smug at 'But gas is still faster, right?', stunned at "
             "'The fake one wins?!', then asks the last line calmly and directly to the viewer. Snappy timing, "
             "no long pauses between lines.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t}" for s, t, _ in LINES) + "\n"
