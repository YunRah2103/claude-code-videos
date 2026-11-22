# SUMMARY — mercedes-acceleration

**Output:** `mercedes_acceleration.mp4` (1080x1920, 30 fps, 47.2 s) + `mercedes_acceleration_thumbnail.png`.
**Hook:** "Sir, your Mercedes has more power than you paid for." (first word at 0.33 s). The reason it's locked is held
back: the store listing comes at 57% and "nobody was ever allowed to buy it" lands at about 68%.
**Cast:** the series buyer (same character, Gemini voice Fenrir) and a new salesman (silver hair, moustache, EQ-blue tie,
voiced by Orus, the series salesman voice). One Gemini TTS call for the whole video, sped up 1.17x with pitch kept.
**Background oddity (never mentioned):** a cow in a red full-face racing helmet appears in every scene. It reads the dyno
printout, queues with a credit card in its mouth, is staged in the next drag-strip lane, is on the phone in the backlash
room, and lifts its visor and waves at the end.

Checked 2026-11-22. Every number spoken or shown must appear in the "Allowed numbers" table (`tools/preflight.py`).

| # | Fact (as used) | Where | Source |
|---|---|---|---|
| 1 | The Mercedes-EQ EQE 350 4MATIC makes 288 hp. With Acceleration Increase it makes 349 hp, and 0-60 mph drops from 6.0 s to 5.1 s. Spoken: "288 horsepower… the motors can make 349", "61 more horsepower. Zero to sixty: 6.0 down to 5.1". Shown on the gauge, store screen, timing boards and "+61 HP". | Scenes 1–3 | Your brief (verified), from the Mercedes-Benz USA store listing at shop.mbusa.com/en-us/connect/pdp/Acceleration-Increase/709 (Nov 2022). **I could not open that page from this session** (the archive fetch was blocked). Partial support: Fortune (23 Nov 2022) gives 0-60 "0.8 to 0.9 seconds" faster; Electrek (28 Nov 2022) says up to "an entire second"; mbusa.com gives 6.0 s for the EQE 350 4MATIC. |
| 2 | The 0-60 time is 0.9 s faster (6.0 − 5.1). Spoken "Less than a second?!" and "0.9 seconds faster". Shown "-0.9 s". | Scenes 3, 5 | Derived from fact 1; consistent with Fortune's 0.8–0.9 s. |
| 3 | Price listed in November 2022 on the US store: $1,200 per year (plus tax), for EQE and EQS models. Spoken "$1,200. A year." Shown "$1,200 / year", "plus tax · renews annually", and card "November 2022: listed on the US store / EQE and EQS: $1,200/year". | Scenes 2, 4 | Fortune, "Mercedes acceleration paywall $1,200 per year" (23 Nov 2022); Electrek (28 Nov 2022), "only available to US EV owners"; The Drive (27 Nov 2022). "Plus tax" is from your brief. |
| 4 | Renew every year, or stay at 288 hp. Spoken "Renew every year, or stay at 288". Chips "PAY EVERY YEAR → 349 HP" and "STOP PAYING → BACK TO 288 HP". | Scene 2 | Follows from facts 1 and 3 (an annual subscription). |
| 5 | About $20 per horsepower, per year: $1,200 ÷ 61 hp = $19.67. Card "$1,200 ÷ 61 hp ≈ $20 per hp, per year". | Scene 3 | Derived from facts 1 and 3. |
| 6 | The EQE starts at about $85,000 ($84,900 in 2022). Spoken "eighty-five grand"; price tag "$84,900, EQE STARTING PRICE (2022)". | Scene 3 | Fortune (23 Nov 2022): "The EQE starts at $84,900". |
| 7 | People were furious about the listing. The comment bubbles are illustrative, not real quotes. | Scene 4 | Wide backlash coverage: Fortune, Electrek, The Drive (Nov 2022). |
| 8 | In April 2023 a Mercedes spokesperson told The Drive that, despite the November listing, "no one was allowed to purchase the upgrade." Spoken "Then Mercedes told The Drive nobody was ever allowed to buy it." The card quotes the article. | Scene 4 | The Drive, "Mercedes Tweaks EV 'Acceleration Increase' Subscription Offer With New Pricing", Aaron Cole, 26 Apr 2023: https://www.thedrive.com/news/mercedes-updates-performance-subscriptions-with-monthly-yearly-and-lifetime-options |
| 9 | Mercedes then changed the pricing and added a one-time purchase option. Spoken "They changed the price and added a one-time purchase." Chips "PRICING CHANGED", "ONE-TIME PURCHASE ADDED". No new prices are given. | Scene 4 | Same Drive article ($600/$900 yearly, $60/$90 monthly, $1,950/$2,950 lifetime for EQE/EQS); Motor Authority: "Mercedes power boost for EVs now available as one-time purchase". |
| 10 | "Technically, sir, you were never overcharged" is the joke drawn from fact 8: nobody could buy it, so nobody paid. | Scene 5 | Follows from fact 8. |

**Not claimed:** that the subscription was cancelled, that it was ever offered in Europe (The Drive, 27 Nov 2022: it stayed
"a U.S. market service only for the time being"), or any current price.

**Real brand assets:** the EQE photos in `assets/` are "Mercedes-Benz EQE 350 4MATIC V295 Obsidian Black (4)" and "(6)" by
Damian B Oh, Wikimedia Commons, CC BY-SA 4.0. Number plates were already blurred in the originals. Credit is required when
posting, e.g. "EQE photos: Damian B Oh / Wikimedia Commons, CC BY-SA 4.0". The three-pointed star is drawn in code to the
real logo's geometry. Mercedes-Benz, EQE and the star are trademarks of Mercedes-Benz Group AG, used here for commentary.

## Allowed numbers

| Spoken / shown | Fact |
|---|---|
| 350, 4, 288, 349, 61, 6.0, 5.1, zero, sixty, 0-60 | 1 |
| 0.9, second | 2 |
| $1,200, 1,200, twelve, hundred, 2022, November | 3 |
| $20, 20 | 5 |
| $84,900, 84,900, eighty, five | 6 |
| 2023 | 8 |
| one | 9 |
