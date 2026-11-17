"""Dialogue for the tesla-acceleration-boost skit. (speaker, text, scene). Speakers: B = buyer (Fenrir), S = salesman (Orus).
Scenes: 1 Tesla lot, 2 driveway at night, 3 Tesla app (cafe), 4 drag strip, 5 finance office. Line 10 is the salesman to camera."""
LINES = [
    ("B", "I paid for this Tesla and now they want $2,000 to make it faster?!", 1),
    ("S", "Sir, that's the Acceleration Boost.", 1),
    ("B", "Faster how? Does it get a new motor?", 2),
    ("S", "No. Same car. Same motors. It's a software update.", 2),
    ("B", "So it was already fast and you just... kept it locked?", 3),
    ("S", "We prefer the word \"reserved.\" Zero to sixty goes from about 4.4 seconds to 3.9.", 3),
    ("B", "$2,000 for half a second?!", 4),
    ("S", "That's about $400 a tenth of a second. Great value.", 4),
    ("B", "You sold me the speed in pieces!", 5),
    ("S", "Nobody's forcing you, sir. You can stay slow for free.", 5),
    ("S", "Is half a second worth $2,000? Let them decide.", 5),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
DIRECTION = ("TTS this fast-paced comedy skit at a Tesla dealership. The Salesman is completely flat, calm and deadpan the "
             "whole time, never reacting, same bored tone on every answer. Say $2,000 as 'two thousand dollars', $400 as "
             "'four hundred dollars', 4.4 as 'four point four' and 3.9 as 'three point nine'. The Buyer starts the very first "
             "word already furious about his own money and escalates: outraged, then suspicious at 'kept it locked?', shouting "
             "at '$2,000 for half a second?!', then bitter at 'You sold me the speed in pieces!'. The Salesman's final line "
             "'Is half a second worth $2,000? Let them decide.' is said slowly and dryly, straight to the audience. "
             "Snappy timing, no long pauses between lines.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t}" for s, t, _ in LINES) + "\n"
