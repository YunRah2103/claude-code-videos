"""Dialogue for blazer-ev-no-carplay. (speaker, text, scene, pose). B = buyer (Fenrir), S = salesman (Orus).
'*' marks an emphasis word (camera punch + hit); it is stripped from captions and TTS.
Scenes: 1 hook, 2 GM's own system, 3 the safety claim, 4 your phone still works, 5 the Honda twist, 6 the question."""
LINES = [
    ("B", "A 2024 electric car with *no CarPlay?", 1, 'shock'),
    ("S", "No Apple CarPlay. No Android Auto.", 1, 'open'),
    ("B", "Who *decided that?!", 1, 'angry'),
    ("S", "GM. In March 2023.", 1, 'present'),
    ("B", "So what's on the *screen?", 2, 'ask'),
    ("S", "GM's own system. Built on Google.", 2, 'offer'),
    ("B", "I wanted *my phone on it!", 2, 'point'),
    ("B", "*Why?!", 3, 'up'),
    ("S", "GM cited safety. Dropped connections. Slow responses.", 3, 'present'),
    ("B", "Is it actually *safer?", 3, 'ask'),
    ("S", "Critics, including Motor1, say it doesn't reduce distraction.", 3, 'open'),
    ("B", "So my phone is *useless?", 4, 'shrug'),
    ("S", "It still works. For music.", 4, 'offer'),
    ("B", "And GM's *gas cars?", 4, 'ask'),
    ("S", "They keep CarPlay.", 4, 'open'),
    ("B", "And the Honda *Prologue?", 5, 'point'),
    ("S", "Same platform. Same plant. It has CarPlay.", 5, 'present'),
    ("B", "The *Honda twin gets it?!", 5, 'up'),
    ("S", "Reports say CarPlay returns on the 2027 Silverado and Sierra.", 5, 'open'),
    ("B", "Would you buy it without CarPlay?", 6, 'final'),
    ("S", "Let them decide.", 6, 'final'),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
SPOKEN = {"2024": "twenty twenty four", "2023": "twenty twenty three", "2027": "twenty twenty seven", "carplay": "car play",
          "motor1": "motor one", "gm": "g m"}
DICT = {"gm's": "JH IY EH M Z"}
HOLD = {3: 0.1, 16: 0.12}
GAPS = (0.02, 0.28, 0.6)
TEMPO = 1.1
PAD = (0.04, 0.07)
DIRECTION = ("TTS this fast-paced comedy skit at a Chevrolet dealership. The Salesman is completely flat, calm and deadpan "
             "the whole time, never reacting, same bored tone on every answer. Read exactly: 2024 = 'twenty twenty-four', "
             "2023 = 'twenty twenty-three', 2027 = 'twenty twenty-seven', GM = 'G M', Motor1 = 'Motor One', CarPlay = "
             "'Car Play'. The Buyer is shocked from the very first word: 'A 2024 electric car with no CarPlay?' is a stunned, "
             "personal, disbelieving question, with no pause before it. His outrage escalates with each answer, shouting at "
             "'Why?!' and 'The Honda twin gets it?!', then asks 'Would you buy it without CarPlay?' quietly and sincerely, "
             "straight to the viewer. Snappy timing, no long pauses between lines.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t.replace('*', '')}" for s, t, *_ in LINES) + "\n"
