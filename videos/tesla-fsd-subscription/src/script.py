"""Dialogue for tesla-fsd-subscription. (speaker, text, scene, pose). B = buyer (Fenrir), S = salesman (Orus).
'*' marks an emphasis word (camera punch + hit); it is stripped from captions and TTS.
Scenes: 1 hook, 2 the old one-time price, 3 the maths, 4 what others charge, 5 so you rent it, 6 the question."""
LINES = [
    ("B", "I can't *BUY Full Self-Driving anymore?", 1, 'shock'),
    ("S", "Subscription only. Since February 14th.", 1, 'open'),
    ("B", "Says *who?!", 1, 'angry'),
    ("S", "Elon Musk. He announced it in January.", 1, 'present'),
    ("B", "I could pay *once before!", 2, 'point'),
    ("S", "$8,000. One time.", 2, 'offer'),
    ("B", "And *now?", 2, 'ask'),
    ("S", "$99 a month. Or $999 a year.", 2, 'open'),
    ("B", "How long until that's *$8,000?", 3, 'chin'),
    ("S", "About 80 months. Over six and a half years.", 3, 'present'),
    ("B", "What do the *others charge?", 4, 'ask'),
    ("S", "Rivian: $49.99 a month. GM: three years included, then $39.99.", 4, 'offer'),
    ("B", "And Tesla wants *$99?!", 4, 'up'),
    ("S", "Every month.", 4, 'open'),
    ("B", "So I *rent my self-driving?", 5, 'shrug'),
    ("S", "It's FSD Supervised. You still watch the road.", 5, 'present'),
    ("B", "I pay monthly to *babysit it?!", 5, 'hip'),
    ("S", "Prices as announced. They may change.", 5, 'open'),
    ("B", "Would you rent your self-driving?", 6, 'final'),
    ("S", "Let them decide.", 6, 'final'),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
SPOKEN = {"14th": "fourteenth", "8000": "eight thousand dollars", "99": "ninety nine dollars",
          "999": "nine hundred ninety nine dollars", "80": "eighty", "4999": "forty nine ninety nine",
          "3999": "thirty nine ninety nine", "fsd": "f s d", "gm": "g m", "self-driving": "self driving"}
DICT = {"rivian": "R IH V IY AH N", "elon": "IY L AA N"}
HOLD = {5: 0.08, 9: 0.1}
GAPS = (0.03, 0.3, 0.62)
PAD = (0.05, 0.07)
DIRECTION = ("TTS this fast-paced comedy skit at a Tesla store. The Salesman is completely flat, calm and deadpan the whole "
             "time, never reacting, same bored tone on every answer. Read the numbers exactly like this: '14th' = 'fourteenth', "
             "'$8,000' = 'eight thousand dollars', '$99' = 'ninety-nine dollars', '$999' = 'nine hundred ninety-nine dollars', "
             "'80' = 'eighty', '$49.99' = 'forty-nine ninety-nine', '$39.99' = 'thirty-nine ninety-nine', FSD = 'F S D', "
             "GM = 'G M', Rivian = 'RIV-ee-un'. The Buyer is shocked from the very first word: 'I can't BUY Full Self-Driving "
             "anymore?' is a stunned, personal, disbelieving question that hits hard on BUY, with no pause before it. His outrage "
             "escalates with each answer, shouting at 'And Tesla wants ninety-nine dollars?!' and 'I pay monthly to babysit it?!', "
             "and finally asks 'Would you rent your self-driving?' quietly and sincerely, straight to the viewer. Snappy timing, "
             "no long pauses between lines.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t.replace('*', '')}" for s, t, *_ in LINES) + "\n"
