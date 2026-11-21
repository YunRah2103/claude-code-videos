"""Dialogue for "Car Ads vs Reality" (long-form, landscape). (speaker, text, scene).
B = buyer (Fenrir, same as the series), S = salesman (Schedar, new for this episode).
Scenes: 0 price (Ford Maverick), 1 mpg (Corolla Hybrid), 2 warranty (Hyundai), 3 0-60 (Model S Plaid),
4 towing (F-150), 5 highway range (F-150 Lightning), 6 Fratzonic (Charger Daytona), 7 FSD (Tesla), 8 ending.
Display tokens with digits are spoken via SPOKEN (used by the TTS prompt and the aligner)."""
LINES = [
    # 0 cold open: starting price
    ("B", "Starting at $28,145! I want that one!", 0),
    ("S", "Starting at. The two most expensive words in this building.", 0),
    ("B", "It's right there! In big letters!", 0),
    ("S", "That's the MSRP. Ford's own footnote says it excludes destination, taxes and fees.", 0),
    ("B", "Destination?! It's going to my driveway!", 0),
    ("S", "Your driveway charges a fee.", 0),
    ("B", "Fine. Fine! It's a little asterisk. I can live with a little asterisk.", 0),
    # 1 up-to mpg
    ("B", "Next! Toyota Corolla Hybrid! Up to 50 miles per gallon!", 1),
    ("S", "Up to. My second favorite phrase.", 1),
    ("B", "Fifty is fifty!", 1),
    ("S", "Fifty combined is the front-wheel-drive one. The EPA rates the SE with all-wheel drive at 44.", 1),
    ("B", "So the cool one gets six less?", 1),
    ("S", "The cool one gets six less.", 1),
    ("B", "Still a hybrid! Still happy! Next!", 1),
    # 2 warranty
    ("B", "Hyundai! Ten years! A hundred thousand miles! America's Best Warranty!", 2),
    ("S", "For the original owner.", 2),
    ("B", "I am extremely original!", 2),
    ("S", "Sell it, and the next owner's powertrain cover drops to five years or 60,000 miles.", 2),
    ("B", "So the warranty doesn't like the next guy?", 2),
    ("S", "It's never met him.", 2),
    ("B", "Okay. Okay. That's actually fair. I'm calm. I'm calm.", 2),
    # 3 0-60
    ("B", "Tesla Model S Plaid! Zero to sixty in 1.99 seconds!", 3),
    ("S", "With one foot of rollout subtracted.", 3),
    ("B", "Subtracted from WHAT?!", 3),
    ("S", "The clock starts after the car has already rolled one foot.", 3),
    ("B", "So zero isn't zero?!", 3),
    ("S", "MotorTrend timed it from a true standstill. 2.28.", 3),
    ("B", "That's still insane!", 3),
    ("S", "It's insanely quick. Just not 1.99 from zero.", 3),
    ("B", "Who starts a race one foot in?!", 3),
    ("S", "Drag strips. It's an old convention.", 3),
    # 4 towing
    ("B", "Ford F-150! 13,500 pounds of towing!", 4),
    ("S", "When properly equipped.", 4),
    ("B", "I will equip it SO properly!", 4),
    ("S", "You need the 3.5 EcoBoost, the Tow Haul Package, and the optional Max Tow Axle.", 4),
    ("B", "And with the standard engine?", 4),
    ("S", "Ford's towing guide says 8,400. At most.", 4),
    ("B", "That's five thousand pounds of difference! That's a whole other boat!", 4),
    ("S", "Please don't tow a whole other boat.", 4),
    # 5 highway range
    ("B", "Fine! Electric! F-150 Lightning! 320 miles of range!", 5),
    ("S", "That's the EPA estimate.", 5),
    ("B", "So?!", 5),
    ("S", "Consumer Reports drove one at a steady 70 miles per hour. It ran out at 270.", 5),
    ("B", "FIFTY MILES! Where did fifty miles GO?!", 5),
    ("S", "The EPA test mixes city and highway driving. At highway speed, EVs use more energy.", 5),
    ("B", "And the other cars?!", 5),
    ("S", "Of 22 EVs they tested, nearly half fell short. Some went farther.", 5),
    ("B", "So my range is a coin toss?!", 5),
    # 6 Fratzonic
    ("B", "At least THIS one is honest. Dodge Charger Daytona! Listen to that exhaust!", 6),
    ("S", "It's electric.", 6),
    ("B", "Then what is THAT?!", 6),
    ("S", "Dodge calls it the Fratzonic Chambered Exhaust. An amplifier and a tuning chamber at the back.", 6),
    ("B", "It's a SPEAKER?!", 6),
    ("S", "Up to 126 decibels. Dodge says that matches a Hellcat.", 6),
    ("B", "My car is doing an impression of a car?!", 6),
    ("S", "There's also a Stealth Mode.", 6),
    ("B", "Of course there is.", 6),
    # 7 FSD
    ("B", "Last one. Tesla. Full. Self. Driving!", 7),
    ("S", "Supervised.", 7),
    ("B", "What?", 7),
    ("S", "The full name is Full Self-Driving, Supervised.", 7),
    ("B", "Supervised by WHO?!", 7),
    ("S", "You. Tesla says it requires active driver supervision and does not make the car autonomous.", 7),
    ("B", "So I drive while it drives?!", 7),
    ("S", "The manual says keep your hands on the wheel and pay attention at all times.", 7),
    ("B", "Then what is the SELF doing?!", 7),
    ("S", "Driving. Supervised.", 7),
    # 8 ending
    ("B", "I've decided.", 8),
    ("S", "Yes?", 8),
    ("B", "From now on, I read the asterisk first.", 8),
    ("S", "The asterisk has fine print too.", 8),
    ("B", "Then I'm buying a bicycle.", 8),
    ("S", "Pedals sold separately.", 8),
    ("S", "Which claim annoyed you the most? Tell us in the comments.", 8),
]
SPOKEN = {"$28,145": "twenty eight thousand one hundred forty five dollars", "50": "fifty", "44": "forty four",
          "60,000": "sixty thousand", "1.99": "one point nine nine", "2.28": "two point two eight",
          "13,500": "thirteen thousand five hundred", "3.5": "three point five", "8,400": "eight thousand four hundred",
          "320": "three twenty", "70": "seventy", "270": "two seventy", "22": "twenty two", "126": "one twenty six",
          "f-150": "f one fifty", "msrp": "m s r p", "epa": "e p a", "evs": "e vees", "se": "s e"}
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Schedar")}
MOOD = {0: "The Buyer is bursting with excitement, slapping a stack of ads on the desk; he gets indignant at 'Destination?!' then forces himself to stay positive.",
        1: "The Buyer is still upbeat and fast, a little defensive, then forces cheer on 'Still a hybrid! Still happy!'.",
        2: "The Buyer is proud and loud, then thrown, then tries very hard to calm himself down on the last line.",
        3: "The Buyer is getting genuinely annoyed: confused shouting on 'Subtracted from WHAT?!' and 'Who starts a race one foot in?!'.",
        4: "The Buyer is aggressive and determined, then exasperated shouting on 'That's a whole other boat!'.",
        5: "The Buyer is angry and loud, screaming 'FIFTY MILES!', then exasperated.",
        6: "The Buyer starts smug and hopeful, then horrified on 'It's a SPEAKER?!', then dead flat and defeated on 'Of course there is.'",
        7: "The Buyer is at peak outrage, near screaming on 'Supervised by WHO?!' and 'Then what is the SELF doing?!'.",
        8: "The Buyer is quiet, exhausted and deflated, almost a whisper, resigned. The Salesman's final question is warm but still dry, said straight to camera."}
def spoken(text):
    out = []
    for w in text.split():
        core = w.strip('!?.,;:')
        key = core.lower() if core.lower() in SPOKEN else core
        if key in SPOKEN:
            out.append(w.replace(core, SPOKEN[key].replace('f one fifty', 'F one-fifty')
                                 .replace('m s r p', 'M S R P').replace('e p a', 'E P A').replace('e vees', 'E Vs').replace('s e', 'S E')))
        else:
            out.append(w)
    return ' '.join(out)
def prompt(scene):
    d = ("TTS this fast-paced comedy skit at a car dealership. High energy, snappy timing, no long pauses between lines. "
         "The Salesman is completely flat, calm and deadpan the whole time, never reacting, same bored dry tone on every answer. "
         + MOOD[scene] + "\n\n")
    return d + "\n".join(f"{VOICES[s][0]}: {spoken(t)}" for s, t, sc in LINES if sc == scene) + "\n"
