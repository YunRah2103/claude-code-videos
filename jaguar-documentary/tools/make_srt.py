import textwrap, re, json
OFF = [0.6, 66.4, 125.1, 190.4, 249.4]
S = {
0: [("There was a time when Jaguar was one of the most admired names in the car industry.", .06, 4.2), ("Its cars were breathtaking.", 4.9, 6.4), ("Its racers conquered Le Mans.", 6.83, 8.6), ("Its badge represented British elegance, with a dangerous edge.", 8.91, 12.8),
 ("Today, that same company has stopped making petrol cars, and gambled everything on an electric reinvention.", 13.2, 20.1), ("How did Jaguar go from building legends to fighting for a new identity?", 20.68, 25.0),
 ("To understand the fall, we need to go back to 1922.", 25.3, 29.3), ("Two young entrepreneurs, William Lyons and William Walmsley, started a business making motorcycle sidecars in Blackpool, England.", 29.5, 37.1),
 ("It was the beginning of a luxury empire.", 37.57, 40.3), ("Lyons had an instinct for design.", 40.53, 42.5), ("By 1935, the first Jaguar-badged car had arrived: stylish, powerful and surprisingly affordable.", 42.78, 50.2),
 ("After the Second World War, the company officially became Jaguar Cars.", 50.51, 54.6), ("Then, in 1948, everything changed.", 54.9, 57.9), ("The XK120 arrived with flowing bodywork and a top speed that made it one of the fastest production cars in the world.", 58.2, 65.1)],
1: [("But Jaguar wanted to prove its speed.", .05, 2.6), ("In 1951, a Jaguar won the 24 Hours of Le Mans.", 2.78, 6.4), ("It won again in 1953.", 6.72, 8.5), ("Then came three consecutive victories, from 1955 to 1957, with the extraordinary D-Type.", 9.0, 16.5),
 ("Jaguar was developing aerodynamics and disc brakes under brutal racing conditions, earning a reputation money couldn't buy.", 17.0, 24.3), ("And then came 1961.", 24.75, 26.7),
 ("The Jaguar E-Type: long bonnet, low roof, sculpted curves, almost 150 miles an hour of performance for far less money than many exotic rivals.", 26.8, 38.0), ("It was a cultural phenomenon.", 38.38, 40.0),
 ("Jaguar had cracked an impossible formula: race-car excitement, genuine luxury, at a price that made the dream feel within reach.", 40.49, 48.3), ("The company followed that elegance with saloons like the XJ.", 48.74, 52.0),
 ("Its identity was clear: grace, space and pace.", 52.0, 55.4), ("But success didn't guarantee stability.", 55.7, 58.0)],
2: [("During the late 1960s, Jaguar was swept into the giant British Leyland group.", .08, 5.5), ("Industrial turmoil, financial problems and quality concerns shook confidence.", 5.74, 10.8), ("The badge survived, but the business was vulnerable.", 11.12, 14.2),
 ("There were flashes of brilliance.", 14.44, 16.4), ("Jaguar regained independence in 1984, and its racing cars won at Le Mans in 1988 and 1990.", 16.69, 24.9), ("Yet the world around it was changing.", 25.11, 27.3),
 ("BMW, Mercedes-Benz and Audi invested heavily in technology, quality and ever-expanding model ranges.", 27.57, 35.4), ("Ford bought Jaguar in 1989 and pushed for growth.", 35.54, 39.2),
 ("Models like the S-Type and X-Type reached new buyers, but chasing volume made the brand's identity harder to define.", 39.44, 46.5), ("In 2008, Tata Motors took ownership.", 47.08, 50.0),
 ("Jaguar fought back with cars like the XF, the supercharged F-Type and later the F-Pace.", 50.08, 55.6), ("The all-electric I-Pace showed Jaguar could still be ambitious.", 55.85, 61.0), ("Some were excellent, but being good wasn't enough.", 61.04, 64.5)],
3: [("Jaguar couldn't match German rivals' scale.", .07, 2.8), ("Even within JLR, Range Rover and Defender became stronger sellers.", 3.31, 7.8), ("The numbers tell the story.", 8.02, 9.4),
 ("Jaguar sold more than 180,000 vehicles in the 2018–2019 financial year.", 10.03, 16.2), ("Just five years later, that figure was under 67,000.", 16.57, 20.5),
 ("And instead of trying to save the old formula, Jaguar made a staggering decision: it would start again.", 20.97, 27.0), ("In 2024, familiar models were discontinued.", 27.34, 30.7),
 ("In December 2025, the final petrol-powered Jaguar left the production line.", 31.12, 38.0), ("The brand that once defined the British sports car was temporarily building no new cars at all.", 38.73, 44.8),
 ("Its 2024 rebrand only intensified the debate.", 45.38, 48.4), ("Bright colours, a new visual identity, and an advert without a single car.", 48.9, 53.3), ("Some called it fearless. Others, a betrayal of Jaguar's heritage.", 53.68, 58.5)],
4: [("Then came the radical Type 00 concept,", .05, 3.3), ("and in October 2026, Jaguar finally revealed the Type 01: an electric four-door grand tourer with more than a thousand horsepower and a starting price of £130,000.", 3.81, 15.0),
 ("It's a bold gamble: rather than chase volume, Jaguar now wants exclusive luxury buyers.", 15.7, 21.5), ("But power figures and daring designs can't automatically rebuild trust.", 21.97, 26.0),
 ("The Type 01 isn't scheduled to reach customers until 2027.", 26.0, 29.5), ("Its real success is still unproven.", 30.1, 32.2), ("Maybe Jaguar is about to pull off the greatest comeback in British motoring,", 32.59, 36.2),
 ("or maybe its golden age will remain exactly where it began: in the past.", 36.51, 40.5), ("One thing is certain:", 41.04, 42.0),
 ("the company that once taught the world what a beautiful, fast car can be now has to convince the world to fall in love with Jaguar all over again.", 42.31, 49.8)],
}
def ts(x):
    h=int(x//3600); m=int(x%3600//60); s=x%60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s-int(s))*1000)):03d}"
def chunks(text, a, b):
    # split long sentences at a comma/colon near the middle so cues stay readable
    if len(text) <= 84: return [(text, a, b)]
    mid = len(text)//2
    cands = [m.end() for m in re.finditer(r'[,:;] ', text)]
    if not cands:
        cands = [m.end() for m in re.finditer(r' ', text)]
    k = min(cands, key=lambda c: abs(c-mid))
    t1, t2 = text[:k].strip(), text[k:].strip()
    f = len(t1)/len(text)
    return [(t1, a, a+(b-a)*f), (t2, a+(b-a)*f, b)]
cues=[]; tr=[]
for i in range(5):
    para=[]
    for text,a,b in S[i]:
        para.append(text)
        for t,x,y in chunks(text,a,b):
            cues.append((t, x+OFF[i], y+OFF[i]))
    tr.append(' '.join(para))
with open('deliverables/jaguar-documentary.srt','w') as f:
    for n,(t,a,b) in enumerate(cues,1):
        f.write(f"{n}\n{ts(a)} --> {ts(b)}\n"+'\n'.join(textwrap.wrap(t,44))+"\n\n")
with open('deliverables/transcript.md','w') as f:
    f.write("# The Rise and Fall of Jaguar — narration transcript\n\nSource: the five supplied voice-over clips (OpenAI.fm “Alloy”), transcribed with an offline speech recogniser and reconstructed from context. Clip boundaries are marked; please proof against your original script.\n\n")
    for i,p in enumerate(tr,1): f.write(f"**Clip {i}**\n\n{p}\n\n")
print(len(cues),'cues')
