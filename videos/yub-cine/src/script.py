"""Narration for the three cinematic Yub shorts (one narrator, Gemini voice Charon). Facts and sources: ../SUMMARY.md."""
VOICE = "Charon"
BASE = ("Read this as an energetic, funny short-video car-channel narrator: confident, warm, slightly amused, quick but clear. "
        "Hit the first word hard, no intro breath. Short pauses between sentences. ")
V = {
 "ioniq": dict(lines=[
    "Hyundai made an electric car with a fake gearbox.",
    "The Ioniq 5 N is a seriously fast EV.",
    "So Hyundai added a feature called N e-Shift.",
    "It fakes an eight-speed dual-clutch gearbox by controlling the motors' torque, cutting power for a split second at each shift.",
    "It even plays fake engine and exhaust sounds.",
    "And Hyundai says you can even miss shifts. In a car with no gears.",
    "Car and Driver tested it: with fake gears on, zero to sixty took three point five seconds. Slower.",
    "Hyundai built a fast car, then added a way to make it slower. On purpose.",
    "Fake gears: genius, or gimmick?"],
    direction="Say 'Ioniq' as 'eye-ON-ick' and 'N e-Shift' as 'N, ee-shift'. Deliver 'In a car with no gears.' and 'On purpose.' deadpan, "
              "with a short beat before each. End with a genuine, light question.",
    spoken={"ioniq": "eye on nick", "5": "five", "ev": "e v", "eshift": "e shift", "eightspeed": "eight speed", "dualclutch": "dual clutch", "motors'": "motors"}),
 "gm": dict(lines=[
    "GM wants your car to forget your iPhone.",
    "Plug your phone into a new GM EV, and... nothing.",
    "Starting in 2023, GM stopped offering CarPlay and Android Auto in most of its new EVs.",
    "GM's CEO says gas cars should lose them too, with a new computer platform around 2028.",
    "GM says it's moving to a better, more integrated experience.",
    "Your phone? No thanks.",
    "But Cars.com says nearly nine in ten shoppers value smartphone integration, and forty-six percent call it a must-have.",
    "Nearly half of shoppers say they must have it. GM says: how about no.",
    "Would you buy a car without CarPlay? Yes, or no?"],
    direction="Say '2023' as 'twenty twenty-three', '2028' as 'twenty twenty-eight', 'GM' as 'G M', 'EV' as 'E V'. Deliver 'Your phone? "
              "No thanks.' as a snooty robot butler. Deliver 'how about no' deadpan. End with a genuine, light question.",
    spoken={"gm": "g m", "gm's": "g m's", "2023": "twenty twenty three", "2028": "twenty twenty eight", "iphone": "i phone", "carplay": "car play",
            "fortysix": "forty six", "musthave": "must have", "ev": "e v", "evs": "e v's", "carscom": "cars dot com"}),
 "jeep": dict(lines=[
    "Jeep drivers have a secret rule.",
    "Pass another Jeep, and the driver waves at you.",
    "It's called the Jeep Wave, a tradition between Jeep drivers.",
    "It's believed to go back to World War Two, when soldiers drove the original Willys Jeeps.",
    "There are no official rules. But the unwritten one is simple: if a fellow Jeep driver waves, you wave back.",
    "Wave at a different brand? Nothing.",
    "Jeep later turned it into an official owner program, called Jeep Wave.",
    "A wave so popular, the company put a name on it.",
    "Should every car brand have a wave? Yes, or no?"],
    direction="Say 'Willys' as 'WILL-iss'. Deliver 'Wave at a different brand? Nothing.' dry and deadpan. "
              "Deliver the punchline with a smile. End with a genuine, light question.",
    spoken={"willys": "willis"}),
}
def prompt(name):
    v = V[name]; return BASE + v["direction"] + "\n\n" + "\n".join(v["lines"]) + "\n"
