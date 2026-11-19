"""Dialogue for gr86-vs-brz. (speaker, text, scene, pose). B = buyer (Fenrir), S = salesman (Orus).
'*' marks an emphasis word (camera punch + hit); it is stripped from captions and TTS.
Scenes: 1 hook, 2 same line, 3 the 2005 deal, 4 the same engine, 5 the tiny differences, 6 the question."""
LINES = [
    ("B", "Wait... my Toyota was built by *Subaru?", 1, 'shock'),
    ("S", "Same factory as the BRZ.", 1, 'open'),
    ("B", "Which *factory?!", 1, 'angry'),
    ("S", "Subaru's Gunma Main Plant. Ota, Japan.", 1, 'present'),
    ("B", "The same *building?!", 2, 'up'),
    ("S", "The same production line.", 2, 'offer'),
    ("B", "Since *when?!", 3, 'angry'),
    ("S", "Toyota and Subaru agreed to work together in 2005.", 3, 'open'),
    ("B", "Does Toyota *own Subaru?", 3, 'ask'),
    ("S", "In 2008, Toyota raised its stake to 16.5 percent.", 3, 'present'),
    ("B", "At least the engine's *Toyota?", 4, 'chin'),
    ("S", "Subaru boxer. 2.4 litres. No turbo.", 4, 'present'),
    ("B", "In *both cars?!", 4, 'up'),
    ("S", "Both. Rear-wheel drive. Six-speed manual or automatic.", 4, 'open'),
    ("B", "So what's *different?!", 5, 'shrug'),
    ("S", "Badges. Front bumpers. Tuning.", 5, 'offer'),
    ("B", "And the *weight?", 5, 'ask'),
    ("S", "Within about twenty pounds.", 5, 'open'),
    ("B", "Which badge would you buy?", 6, 'final'),
    ("S", "Let them decide.", 6, 'final'),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
SPOKEN = {"brz": "b r z", "2005": "two thousand five", "2008": "two thousand eight", "165": "sixteen and a half",
          "24": "two point four", "litres": "liters"}
DICT = {"gunma": "G UH N M AH", "subaru's": "S UW B ER UW Z"}
HOLD = {5: 0.2, 11: 0.15, 17: 0.15}
GAPS = (0.04, 0.34, 0.7)
PAD = (0.05, 0.08)
DIRECTION = ("TTS this fast-paced comedy skit at a Toyota dealership. The Salesman is completely flat, calm and deadpan the "
             "whole time, never reacting, same bored tone on every answer. Read exactly: BRZ = 'B R Z', Gunma = 'GOON-mah', "
             "Ota = 'OH-tah', 2005 = 'two thousand five', 2008 = 'two thousand eight', 16.5 = 'sixteen and a half', 2.4 = "
             "'two point four'. The Buyer is shocked from the very first word: 'Wait... my Toyota was built by Subaru?' is a "
             "stunned, personal, disbelieving question, with no pause before 'Wait'. His outrage escalates with each answer, "
             "shouting at 'In both cars?!', then asks 'Which badge would you buy?' quietly and sincerely, straight to the "
             "viewer. Snappy timing, no long pauses between lines.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t.replace('*', '')}" for s, t, *_ in LINES) + "\n"
