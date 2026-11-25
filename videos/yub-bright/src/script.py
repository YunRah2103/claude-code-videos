"""Narration for the three bright Yub shorts (one narrator each, Gemini voice Charon). Facts and sources: ../SUMMARY.md."""
VOICE = "Charon"
BASE = ("Read this as an energetic, funny short-video car-channel narrator: confident, warm, amused, fast but clear. "
        "Hit the first word hard, no intro breath. Very short pauses between sentences. ")
V = {
 "jeep": dict(lines=[
    "Jeep drivers have a secret rule.",
    "Pass another Jeep, and the driver waves.",
    "It's the Jeep Wave, a Jeep driver tradition.",
    "It's believed to go back to World War Two Willys Jeeps.",
    "The unwritten rule: a Jeep driver waves, you wave back.",
    "Other brands? Not so much.",
    "Jeep even named an owner program Jeep Wave.",
    "A wave so popular, the company put a name on it.",
    "Should every car brand have a wave? Yes, or no?"],
    direction="Say 'Willys' as 'WILL-iss'. Deliver 'Other brands? Not so much.' dry and deadpan. "
              "Deliver the punchline with a smile. End with a genuine, light question.",
    spoken={"willys": "willis"}),
 "ioniq": dict(lines=[
    "Hyundai made an electric car with a fake gearbox.",
    "The Ioniq 5 N is a fast EV.",
    "Its N e-Shift fakes an eight-speed gearbox by controlling the motors.",
    "It also plays fake engine and exhaust sounds.",
    "Hyundai says you can even miss shifts.",
    "Car and Driver: with fake gears on, sixty took three point five seconds. Slower.",
    "Hyundai built a fast car, then added a way to make it slower. On purpose.",
    "Fake gears: genius, or gimmick?"],
    direction="Say 'Ioniq' as 'eye-ON-ick', 'N e-Shift' as 'N, ee-shift'. Deliver 'Slower.' and 'On purpose.' deadpan, "
              "with a beat before each. End with a genuine, light question.",
    spoken={"ioniq": "eye on nick", "5": "five", "ev": "e v", "eshift": "e shift", "eightspeed": "eight speed", "motors'": "motors"}),
 "gm": dict(lines=[
    "GM wants your car to forget your iPhone.",
    "Plug in your phone... nothing.",
    "In 2023, GM began dropping CarPlay and Android Auto from new EVs.",
    "Future GM cars follow, around 2028.",
    "GM calls it a better experience.",
    "Your phone? No thanks.",
    "Yet nearly nine in ten shoppers value it, and forty-six percent call it a must-have.",
    "Nearly half of shoppers say they must have it. GM says: how about no.",
    "Would you buy a car without CarPlay? Yes, or no?"],
    direction="Say '2023' as 'twenty twenty-three' and '2028' as 'twenty twenty-eight'. Say 'GM' as 'G M'. Deliver 'Your phone? "
              "No thanks.' as a snooty robot butler. Deliver 'how about no' deadpan. End with a genuine, light question.",
    spoken={"gm": "g m", "2023": "twenty twenty three", "2028": "twenty twenty eight", "iphone": "i phone", "carplay": "car play",
            "fortysix": "forty six", "musthave": "must have", "evs": "e v's"}),
}
def prompt(name):
    v = V[name]; return BASE + v["direction"] + "\n\n" + "\n".join(v["lines"]) + "\n"
