"""Dialogue for honda-prologue-is-a-chevy. (speaker, text, scene, pose). B = buyer (Fenrir), S = salesman (Orus).
'*' marks an emphasis word (camera punch + hit); it is stripped from captions and TTS.
Scenes: 1 hook, 2 GM's plant, 3 shared parts, 4 what Honda did, 5 the CarPlay twist, 6 the question."""
LINES = [
    ("B", "Wait... my Honda is a *Chevy?", 1, 'shock'),
    ("S", "Built by General Motors.", 1, 'open'),
    ("B", "It says Honda on the *front!", 1, 'point'),
    ("S", "Honda's first big EV in North America.", 1, 'present'),
    ("B", "So where's it *built?!", 2, 'angry'),
    ("S", "GM's Ramos Arizpe plant, in Mexico. Same plant as the Blazer EV.", 2, 'offer'),
    ("B", "Since *when?!", 2, 'up'),
    ("S", "Production began January 2024.", 2, 'open'),
    ("B", "What's actually *shared?", 3, 'ask'),
    ("S", "GM's Ultium platform. Frame rails. Floor. Subframes. Firewall.", 3, 'present'),
    ("B", "That's the whole *car!", 3, 'up'),
    ("S", "Honda's chief engineer said so.", 3, 'open'),
    ("B", "So what did Honda *do?", 4, 'shrug'),
    ("S", "The body. The interior. The steering, springs and dampers.", 4, 'present'),
    ("B", "Then why buy the *Honda?", 5, 'ask'),
    ("S", "Apple CarPlay. The Chevy doesn't have it.", 5, 'offer'),
    ("B", "The Honda is a better *Chevy?!", 5, 'hip'),
    ("B", "Is it still a Honda?", 6, 'final'),
    ("S", "Let them decide.", 6, 'final'),
]
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
SPOKEN = {"2024": "twenty twenty four", "ev": "e v", "carplay": "car play"}
DICT = {"gm's": "JH IY EH M Z", "arizpe": "AA R IY S P EY", "ultium": "AH L T IY AH M", "subframes": "S AH B F R EY M Z"}
HOLD = {5: 0.1, 9: 0.1, 15: 0.2}
DIRECTION = ("TTS this fast-paced comedy skit at a Honda dealership. The Salesman is completely flat, calm and deadpan the "
             "whole time, never reacting, same bored tone on every answer. Say GM as 'G M', EV as 'E V', 2024 as 'twenty "
             "twenty-four', Arizpe as 'ah-REES-peh' and Ultium as 'ULL-tee-um'. The Buyer is shocked from the very first word: "
             "'Wait... my Honda is a Chevy?' is a stunned, personal, disbelieving question, with no pause before 'Wait'. His "
             "outrage escalates with each answer, shouting at 'That's the whole car!', then turns gleefully baffled at 'The Honda "
             "is a better Chevy?!', and finally asks 'Is it still a Honda?' quietly and sincerely, straight to the viewer. Snappy "
             "timing, no long pauses between lines.\n\n")
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t.replace('*', '')}" for s, t, *_ in LINES) + "\n"
