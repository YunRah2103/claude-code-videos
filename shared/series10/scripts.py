"""Scripts for the ten-episode 'car stuff, explained' series (after the fact check; see out/series10/REPORT.md)."""
EPISODES = [
    ('abs-pumping', "Stop pumping your brakes. Most modern cars have ABS. It pulses the brakes for you if the wheels start to lock. Press firmly and hold the pedal. Keep steering too. Did you know that?"),
    ('brake-squeal', "That squeal from your brakes might be a warning. Many brake pads have a small metal tab. When the pad wears thin, the tab scrapes the disc. It's designed to make a noise. Have you heard yours?"),
    ('stop-start', "Why does your engine switch off at red lights? It's called stop-start. It can save fuel when you're stationary. The engine usually restarts when you lift off the brake. Would you turn it off yourself?"),
    ('wheel-nut-order', "The order you tighten wheel nuts matters. Don't go round the circle. Use a star pattern, so the wheel sits flat. Then check the torque in your manual. Did you know that?"),
    ('headlight-yellow', "Why do headlights go yellow? The plastic has a UV coating. Sunlight and age wear it down. The yellow haze can cut your light output. Polishing or a new lens can help. Have yours gone cloudy?"),
    ('coolant-mixing', "Don't mix coolant types. Colour alone won't tell you the chemistry. Some mixes can form a sludge that blocks the system. Check your manual before topping up. Have you ever topped up with the wrong one?"),
    ('hill-wheels', "Which way do you turn your wheels on a hill? Many driving guides say downhill towards the kerb, uphill away. Rules and tests differ by country. Which way do you turn yours?"),
    ('ev-one-gear', "Electric cars have one gear, but not because they're simple. An electric motor makes its full pulling power from a standstill. So a single gear reduction is often enough. Would you miss the gearbox?"),
    ('flashing-check-engine', "A check engine light that flashes is urgent. A steady light means get it checked soon. Flashing can mean an engine misfire. That can damage the catalytic converter. Pull over safely and get help. Would you know the difference?"),
    ('warm-up-myth', "Do you need to warm up your car for minutes? Most modern cars are designed to be driven gently soon after starting. Warming up for a long time can waste fuel. Driving gently warms it up faster than idling. Did you think you needed to?"),
]
NAMES = [n for n, _ in EPISODES]
SCRIPT = dict(EPISODES)
