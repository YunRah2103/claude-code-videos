"""Narration for car_evolution ("How the car was made"): one narrator (Yub, first person asides), Gemini voice Charon.
Facts and sources: ../SUMMARY.md. Only facts from the brief; numbers are never invented."""
VOICE = "Charon"
BASE = ("Read this as an energetic, funny short-video car-channel narrator: confident, warm, slightly amused, quick but clear. "
        "Hit the first word hard, no intro breath. Short pauses between sentences. ")
V = {
 "car": dict(lines=[
    "The first car had less than one horsepower. Here's how it became this.",
    "1886. Karl Benz patents the Benz Patent-Motorwagen.",
    "Three wheels, one cylinder, and 0.75 horsepower. That's three quarters of a horse.",
    "You steered it with a tiller. Top speed? About 10 miles an hour. Still too fast for me.",
    "And early cars had to be hand-cranked. Dangerously.",
    "So in 1912, Cadillac brought in Charles Kettering's electric starter. Click. Done.",
    "Then Ford's Model T launched at $850.",
    "The moving assembly line cut build time from 12.5 hours to 93 minutes.",
    "Over 15 million were built, and the price fell to $260. Finally, a car in my budget.",
    "1959. Volvo engineer Nils Bohlin perfects the three-point seatbelt, and Volvo gives the patent away, free.",
    "Finally, something holding me together.",
    "1977. The Oldsmobile Toronado is the first car with a microprocessor.",
    "Then the code kept coming.",
    "Today, a car can have hundreds of millions of lines of code. A Boeing 737? About 15 million.",
    "And I still can't pair my phone.",
    "Now even features are software. In 2019, Tesla sold an Acceleration Boost for $2,000. My horsepower has a paywall.",
    "Which of these was the biggest upgrade?"],
    direction="Say '1886' as 'eighteen eighty-six', '1912' as 'nineteen twelve', '1959' as 'nineteen fifty-nine', '1977' as 'nineteen seventy-seven', "
              "'2019' as 'twenty nineteen', '0.75' as 'zero point seven five', '12.5' as 'twelve and a half', '$850' as 'eight hundred fifty dollars', "
              "'$260' as 'two hundred sixty dollars', '$2,000' as 'two thousand dollars', '737' as 'seven thirty-seven', 'Bohlin' as 'BOH-leen', "
              "'Toronado' as 'tor-oh-NAH-doh', 'Kettering' as 'KET-er-ing'. The lines in first person ('Still too fast for me.', 'Click. Done.', "
              "'Finally, a car in my budget.', 'Finally, something holding me together.', 'And I still can't pair my phone.', "
              "'My horsepower has a paywall.') are deadpan jokes: a tiny beat before each. End with a genuine, light question.",
    spoken={"1886": "eighteen eighty six", "patentmotorwagen": "patent motor wagon", "perfects": "perfect s", "paywall": "pay wall", "075": "zero point seven five", "10": "ten",
            "handcranked": "hand cranked", "1912": "nineteen twelve", "kettering's": "kettering", "850": "eight hundred fifty dollars",
            "125": "twelve and a half", "93": "ninety three", "15": "fifteen", "260": "two hundred sixty dollars",
            "1959": "nineteen fifty nine", "threepoint": "three point", "bohlin": "bowlin", "1977": "nineteen seventy seven",
            "toronado": "toronado", "737": "seven thirty seven", "2019": "twenty nineteen", "2000": "two thousand dollars",
            "can't": "can't", "here's": "here's", "that's": "that's"}),
}
def prompt(name):
    v = V[name]; return BASE + v["direction"] + "\n\n" + "\n".join(v["lines"]) + "\n"
