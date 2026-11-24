"""Narration for the three Yub low-poly shorts (one narrator each, Gemini voice Charon)."""
VOICE = "Charon"
BASE = ("Read this as a punchy short-video car-channel narrator: confident, deep, slightly amused, fast but clear. "
        "Hit the first word hard, no intro breath. Very short pauses between sentences. ")
V = {
 "toyota": dict(lines=[
    "Toyota can stop your own key from starting your own car.",
    "On many 2018-and-newer Toyotas, remote start from the key fob needs a paid subscription.",
    "When it launched, it cost eight dollars a month, or eighty a year.",
    "The fob sends a radio signal, but the car's software checks that you paid.",
    "After the backlash, Toyota said it wasn't intentional, and that it was reviewing it.",
    "You own the key. You rent the button.",
    "Should a button on your own key cost a subscription? Yes, or no?"],
    direction="Say '2018-and-newer' as 'twenty-eighteen and newer'. Deliver 'You own the key. You rent the button.' deadpan, "
              "with a beat between them. End with a genuine, light question.",
    spoken={"2018andnewer": "twenty eighteen and newer"}),
 "tesla": dict(lines=[
    "Tesla made its own cars faster, then charged $2,000 for it.",
    "In December 2019, Tesla launched Acceleration Boost for the Model 3 Dual Motor Long Range.",
    "It's an over-the-air software upgrade that cut about half a second from zero to sixty.",
    "A month earlier, Tesla had given every Model 3 a smaller power boost, for free.",
    "Free update first. Paid update second.",
    "Would you pay $2,000 for half a second? Yes, or no?"],
    direction="Say '$2,000' as 'two thousand dollars' and '2019' as 'twenty nineteen'. Deliver 'Free update first. Paid update "
              "second.' deadpan, with a beat between them. End with a genuine, light question.",
    spoken={"2000": "two thousand dollars", "2019": "twenty nineteen", "3": "three", "overtheair": "over the air"}),
 "veyron": dict(lines=[
    "A set of Bugatti Veyron tires used to cost $42,000.",
    "Each one was a bespoke Michelin run-flat, glued to the wheel.",
    "With the wheels, a full replacement could reach about $100,000.",
    "Now Bugatti has developed larger wheels that fit modern tires, costing around $3,600 a set.",
    "The catch: owners still have to pay for the new wheels.",
    "Cheaper tires. Just not a cheap fix.",
    "Would you pay $100,000 to change your tires? Yes, or no?"],
    direction="Say '$42,000' as 'forty-two thousand dollars', '$100,000' as 'a hundred thousand dollars' and '$3,600' as "
              "'thirty-six hundred dollars'. Say 'Bugatti' as 'boo-GAH-tee' and 'Veyron' as 'VAY-ron'. Deliver 'Cheaper tires. "
              "Just not a cheap fix.' deadpan. End with a genuine, light question.",
    spoken={"42000": "forty two thousand dollars", "100000": "a hundred thousand dollars", "3600": "thirty six hundred dollars",
            "runflat": "run flat", "veyron": "vey ron", "bespoke": "bee spoke"}),
}
def prompt(name):
    v = V[name]; return BASE + v["direction"] + "\n\n" + "\n".join(v["lines"]) + "\n"
