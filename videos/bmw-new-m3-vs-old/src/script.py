"""Dialogue for the bmw-new-m3-vs-old skit. (speaker, text, scene). Speakers: B = buyer (Fenrir), S = salesman (Orus).
Scenes 1-7 are all the BMW showroom; the car on the platform changes: 1 E46, 2 G80, 3 E92, 4 E46, 5 G80, 6 G80, 7 G80."""
LINES = [
    ("B", "I want the best M3 ever made. That's the E46, right?", 1),
    ("S", "No, sir. That would be the new one.", 1),
    ("B", "The new one?! It has nostrils!", 2),
    ("S", "Yes. At the time, BMW's own design boss said about twenty percent of people liked the grille.", 2),
    ("B", "The E92 has a V8! Four hundred and fourteen horsepower!", 3),
    ("S", "Yes. The new one has five-oh-three. And over five hundred with all-wheel drive.", 3),
    ("B", "The E46 is lighter!", 4),
    ("S", "It is. About thirty-four hundred pounds. The new one is about thirty-eight-forty. The heaviest M3 ever. "
          "I'm not going to pretend otherwise.", 4),
    ("B", "So why is it better?!", 5),
    ("S", "Zero to sixty. The E46: about five-point-one. The new one: about three-point-eight. "
          "With all-wheel drive, about three-point-four.", 5),
    ("B", "But it doesn't feel like an M3!", 6),
    ("S", "Some reviewers said the same, until they drove it. Then the criticism turned to praise.", 6),
    ("B", "It still looks like a face that's been punched.", 7),
    ("S", "Sir, that part we agree on.", 7),
    ("S", "Old M3 or new M3? Let them decide.", 7),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
DIRECTION = ("TTS this fast-paced comedy skit in a BMW dealership. The Salesman is completely flat, calm and deadpan the "
             "whole time, quietly confident, reading numbers like facts off a sheet, never raising his voice. The Buyer is a "
             "passionate old-school car purist: confident at first, then offended, then increasingly worked up, shouting at "
             "'It has nostrils!' and 'So why is it better?!', pleading on 'But it doesn't feel like an M3!', and bitter but "
             "calmer on the last line. Say M3 as 'M three', E46 as 'E forty-six', E92 as 'E ninety-two', V8 as 'V eight', "
             "BMW as 'B M W'. The Salesman's final line 'Old M3 or new M3? Let them decide.' is said straight to the viewer, "
             "dry. Snappy timing, no long pauses between lines.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t}" for s, t, _ in LINES) + "\n"
