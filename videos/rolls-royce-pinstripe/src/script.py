"""Narration for rolls-royce-pinstripe (one narrator, Gemini voice Charon). (text, shot-group)."""
LINES = [
    "That stripe on a Rolls-Royce is painted by one man.",
    "His name is Mark Court, and he has done it for over twenty years.",
    "No machine. No sticker. No guide.",
    "Just one brush, made of squirrel hair.",
    "The line is about three millimetres wide,",
    "and it runs the whole side of the car, in one go.",
    "Any wobble, and everyone sees it.",
    "It takes about three hours per side.",
    "And if he slips, there is no quick fix.",
    "Here's the twist. Before Rolls-Royce, he painted pub signs.",
    "Rolls-Royce did not hire a robot.",
    "They hired a pub sign painter.",
    "Would you pay extra for a stripe painted by hand? Yes, or no?",
]
VOICE = "Charon"
DIRECTION = ("Read this as a punchy short-video narrator: confident, deep, slightly amused, fast but clear, like a "
             "late-night documentary trailer. Start strong on the first word. Short natural pauses between sentences. "
             "Deliver 'Rolls-Royce did not hire a robot. They hired a pub sign painter.' completely deadpan. "
             "End with a genuine question, light and inviting.\n\n")
def prompt():
    return DIRECTION + "\n".join(LINES) + "\n"
