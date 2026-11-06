"""Scripts for the six-episode 'car stuff, explained' series (after the fact check; see out/series6/REPORT.md)."""
EPISODES = [
    ('limp-mode', "Is your car suddenly slow with a warning light? It might be in limp mode. The car cuts power to protect itself from damage. It's usually a protection feature. Have you ever had that happen?"),
    ('timing-belt', "A snapped timing belt can wreck an engine. In some engines, the valves and pistons can collide when it breaks. That's called interference. Your manual lists when to replace it. Do you know when yours is due?"),
    ('speedometer-high', "Your speedometer might read a little high on purpose. Some countries' rules allow it to over-read. It acts as a safety margin, so you're less likely to speed by accident. Does yours read high?"),
    ('blind-spot', "Something might be in your blind spot right now. Your mirrors don't show the whole picture. A quick head check covers the gap. Many cars now have blind spot warnings. Do you check every time?"),
    ('airbag-light', "Airbag light on? That's not just a bulb. It means the airbag system has a fault. It can be a sensor or connector problem. Get it checked soon. Would you know what the light meant?"),
    ('premium-fuel', "Does premium fuel make your car faster? Usually, no. Unless your manual asks for it, most engines run fine on regular fuel. Some high-performance engines can benefit. Did you think it was faster?"),
]
NAMES = [e for e, _ in EPISODES]
