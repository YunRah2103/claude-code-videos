"""Dialogue for the polestar-performance-upgrade skit. (speaker, text, scene). B = buyer (Fenrir), S = salesman (Orus).
Scenes: 1 driveway, 2 Polestar showroom, 3 drag strip, 4 cashier's office, 5 underground charging garage."""
LINES = [
    ("B", "I paid for a Polestar and the last sixty-eight horsepower costs twelve hundred dollars extra?!", 1),
    ("S", "Sir, that's the Performance Upgrade.", 1),
    ("B", "Does it need a new motor?", 2),
    ("S", "No. It's a software update. It downloads over the air.", 2),
    ("B", "What do I actually get?", 3),
    ("S", "Four-oh-eight horsepower becomes four-seventy-six. Zero to sixty drops to about four-point-two seconds.", 3),
    ("B", "That's seventeen dollars a horsepower!", 4),
    ("S", "Seventeen-fifty. But it's one payment. At least it isn't a subscription.", 4),
    ("B", "So I'm paying twelve hundred dollars to feel less insulted?", 5),
    ("S", "Nobody's forcing you, sir.", 5),
    ("S", "Is sixty-eight horsepower worth twelve hundred dollars? Let them decide.", 5),
]
SPOKEN = {}
EXTRA_WORDS = {"polestar": "P OW L S T AA R"}
HOLD = {3: 0.15, 5: 0.3, 7: 0.3}                   # reveal holds after key answers (retime.py)
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
DIRECTION = ("TTS this fast-paced comedy skit at a car dealership. The Salesman is completely flat, calm and deadpan the "
             "whole time, bored, never reacting; he says 'At least it isn't a subscription' as if it were generous. Say "
             "'four-oh-eight' as 'four oh eight' and 'four-seventy-six' as 'four seventy-six'. The Buyer starts already "
             "outraged, shouting from the very first word; suspicious on 'Does it need a new motor?', shouting 'That's "
             "seventeen dollars a horsepower!', then bitter and sarcastic on 'So I'm paying twelve hundred dollars to feel "
             "less insulted?'. In the last line the Salesman turns and asks the viewer directly, same flat voice. Snappy "
             "timing, no long pauses between lines.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t}" for s, t, _ in LINES) + "\n"
