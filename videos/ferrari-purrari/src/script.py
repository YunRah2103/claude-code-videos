"""Narration for ferrari-purrari (one narrator, Gemini voice Charon)."""
LINES = [
    "Ferrari can refuse to sell you a car, even if you have the money.",
    "Dealers pick who gets the rare ones.",
    "Buyers reportedly sign a contract: no reselling in the first year.",
    "Then Deadmau5 wrapped his Ferrari 458 as a Nyan Cat.",
    "He called it the Purrari.",
    "Ferrari did not find it funny.",
    "He has said it sent him a cease-and-desist.",
    "Ferrari says it blacklists no one,",
    "but it picks who gets special editions.",
    "It's your money. It's their car.",
    "Should a company be allowed to pick its customers? Yes, or no?",
]
VOICE = "Charon"
DIRECTION = ("Read this as a punchy short-video narrator: confident, deep, slightly amused, fast but clear, like a "
             "late-night documentary trailer. Hit the first word hard, no intro breath. Very short pauses between sentences. "
             "Say 'Deadmau5' as 'dead mouse' and '458' as 'four fifty-eight'. Say 'Purrari' like 'purr-RAH-ree', playful. "
             "Deliver 'It's your money. It's their car.' completely deadpan, with a beat between the two sentences. "
             "End with a genuine question, light and inviting.\n\n")
def prompt():
    return DIRECTION + "\n".join(LINES) + "\n"
