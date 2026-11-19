"""Dialogue for outlander-is-a-rogue. (speaker, text, scene, pose). B = buyer (Fenrir), S = salesman (Orus).
'*' marks an emphasis word (camera punch + hit); it is stripped from captions and TTS.
Scenes: 1 hook, 2 the shared platform, 3 the Nissan engine, 4 the looks are Mitsubishi's, 5 the weight gap, 6 the question."""
LINES = [
    ("B", "Wait... my Mitsubishi is a *Nissan?", 1, 'shock'),
    ("S", "Mitsubishi calls it a shared Alliance platform.", 1, 'open'),
    ("B", "And what do *reviewers call it?", 1, 'ask'),
    ("S", "The Rogue's.", 1, 'present'),
    ("B", "Which *platform?!", 2, 'angry'),
    ("S", "CMF-CD. From Renault and Nissan. Same as the Rogue.", 2, 'offer'),
    ("B", "Since *when?!", 2, 'up'),
    ("S", "The 2022 Outlander. Fourth generation.", 2, 'open'),
    ("B", "Please say the engine's *Mitsubishi.", 3, 'chin'),
    ("S", "Nissan's 2.5-litre four-cylinder. With a CVT.", 3, 'present'),
    ("B", "A *Nissan engine?!", 3, 'up'),
    ("S", "In a Mitsubishi.", 3, 'open'),
    ("B", "So what's *Mitsubishi about it?!", 4, 'shrug'),
    ("S", "The styling. And the tuning.", 4, 'present'),
    ("B", "A Rogue in a *costume?", 4, 'hip'),
    ("S", "A very nice costume.", 4, 'open'),
    ("B", "Is it at least *lighter?", 5, 'ask'),
    ("S", "About two hundred pounds heavier. Reviewers' figure.", 5, 'offer'),
    ("B", "*Heavier?!", 5, 'up'),
    ("B", "Rogue or Outlander?", 6, 'final'),
    ("S", "Let them decide.", 6, 'final'),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
SPOKEN = {"cmf-cd": "c m f c d", "2022": "twenty twenty two", "25-litre": "two point five liter", "cvt": "c v t"}
DICT = {"outlander": "AW T L AE N D ER", "rogue's": "R OW G Z", "reviewers'": "R IY V Y UW ER Z"}
HOLD = {3: 0.15, 9: 0.15, 17: 0.2}
GAPS = (0.05, 0.36, 0.75)
PAD = (0.05, 0.08)
DIRECTION = ("TTS this fast-paced comedy skit at a Mitsubishi dealership. The Salesman is completely flat, calm and deadpan "
             "the whole time, never reacting, same bored tone on every answer. Read exactly: CMF-CD = 'C M F, C D', Renault = "
             "'ruh-NO', 2022 = 'twenty twenty-two', 2.5-litre = 'two point five liter', CVT = 'C V T'. The Buyer is shocked "
             "from the very first word: 'Wait... my Mitsubishi is a Nissan?' is a stunned, personal, disbelieving question, with "
             "no pause before 'Wait'. His outrage escalates with each answer, shouting at 'A Nissan engine?!' and 'Heavier?!', "
             "then asks 'Rogue or Outlander?' quietly and sincerely, straight to the viewer. Snappy timing, no long pauses "
             "between lines.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t.replace('*', '')}" for s, t, *_ in LINES) + "\n"
