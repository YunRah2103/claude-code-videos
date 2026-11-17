"""Dialogue for the toyota-key-fob-subscription skit. (speaker, text, scene). B = buyer (Fenrir), S = salesman (Orus).
Scenes: 1 snowy driveway, 2 Toyota showroom, 3 server room, 4 Toyota press room, 5 frozen car park at night."""
LINES = [
    ("B", "I pressed my key fob three times and Toyota wants eight dollars a month?!", 1),
    ("S", "Sir, that's remote start.", 1),
    ("B", "It's my key! It's my truck!", 2),
    ("S", "Remote start needs an active subscription. Eight dollars a month, or eighty a year.", 2),
    ("B", "The key doesn't even use the internet!", 3),
    ("S", "The truck has to phone home first, sir.", 3),
    ("B", "I bought a truck, not a subscription!", 4),
    ("S", "Toyota says it was unintentional.", 4),
    ("B", "Unintentional?!", 4),
    ("S", "Nobody's forcing you, sir. You can warm it up the old way. By sitting in it.", 5),
    ("S", "Would you pay eight dollars a month to start your own truck? Let them decide.", 5),
]
SPOKEN = {}
EXTRA_WORDS = {}
HOLD = {0: 0.25, 1: 0.5, 2: 0.25, 3: 0.6, 4: 0.25, 5: 0.7, 6: 0.2, 7: 0.7, 8: 0.5, 9: 0.6}   # deadpan holds (retime.py)
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
DIRECTION = ("TTS this fast-paced comedy skit. The Salesman is completely flat, calm and deadpan the whole time, bored, "
             "never reacting, as if explaining something obvious. The Buyer is freezing cold and already outraged from the "
             "very first word, shouting; furious at 'It's my key! It's my truck!', incredulous at 'The key doesn't even use "
             "the internet!', screaming 'I bought a truck, not a subscription!', and a short disbelieving shriek on "
             "'Unintentional?!'. In the last line the Salesman turns and asks the viewer directly, same flat voice. "
             "Snappy timing, no long pauses between lines.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t}" for s, t, _ in LINES) + "\n"
