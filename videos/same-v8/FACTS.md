# same-v8 facts

Each on-screen/voiced claim, its value and its sources. Prices and the gap are hedged "about" on screen and in the voice.

| Claim (screen / voice) | Value used | Sources | Status |
|---|---|---|---|
| Same platform | VW Group MLB Evo (both) | [Wikipedia: Lamborghini Urus](https://en.wikipedia.org/wiki/Lamborghini_Urus); [SlashGear](https://www.slashgear.com/1847613/is-lamborghini-urus-same-as-audi-q8-how-suv-compare) | verified, 2 sources |
| Same V8 (`"4.0 TT V8"`) | 4.0 L twin-turbo V8 in both | [Jalopnik](https://jalopnik.com/2238931/audi-rs-model-with-lamborghini-engine-rs6-gallardo-v10-different); [carwow](https://www.carwow.co.uk/editorial/choosing-a-car/car-comparisons-side-by-side/audi-rsq8-vs-lamborghini-urus); [Lambocars](https://lambocars.com/audi-rs-q8-vs-lamborghini-urus/) | verified, 3 sources |
| AWD (`"AWD"`) | all-wheel drive, both | [iSeeCars 2022 comparison](https://www.iseecars.com/compare/2022-audi-rs_q8-vs-2022-lamborghini-urus) (Urus standard AWD); [Cars.com comparison](https://www.cars.com/research/compare/audi-rs_q8-vs-lamborghini-urus/) (RS Q8 quattro) | verified |
| Engine covers "reportedly" fit each other | covers interchange | [carwow](https://www.carwow.co.uk/editorial/choosing-a-car/car-comparisons-side-by-side/audi-rsq8-vs-lamborghini-urus); supporting: APR aftermarket cover listed for both RS Q8 and Urus ([Vivid Racing](https://www.vividracing.com/apr-carbon-fiber-engine-cover-for-29t30t40t-suv-ms100256-p-156731202.html)) | single editorial source -> hedged "reportedly" |
| Urus price "about $230,000" (`229_495`) | 2022 US base $229,495 | [Supersportiva](https://supersportiva.com/lamborghini-urus-so-expensive/); [CarGurus 2022 Urus](https://www.cargurus.com/research/2022-Lamborghini-Urus-c32051) (original MSRP $229,495) | verified, 2 sources |
| RS Q8 price "about $121,000" (`121_096`) | 2022 US base $121,096 | [Supersportiva](https://supersportiva.com/lamborghini-urus-so-expensive/) (table $121,096, text $121,095); iSeeCars lists $119,900 starting MSRP | one exact source; hedged "about" |
| Gap "about 108k" (`print(urus - rsq8)`) | 229,495 − 121,096 = 108,399 | arithmetic (checked by `snippets/s5.py`) | verified |
| "a bit more power" (`int hp = 641 - 591; // 50`) | Urus 641 hp (650 PS) vs 2022 RS Q8 591 hp -> +50 hp | [Lambocars](https://lambocars.com/audi-rs-q8-vs-lamborghini-urus/) (641 vs 591); [Wikipedia: Urus](https://en.wikipedia.org/wiki/Lamborghini_Urus) (650 PS = 641 hp) | 641 hp: 2 sources. 591 hp: Lambocars, plus a second comparison listing in search results giving the base RS Q8 at 591 hp (page not opened); hedged as "a bit more" |
| "sharper tuning" (`tune DIFFERENT`) | same engine, different output (641 vs 591 hp) = different tune | follows from the power row | verified by the above |
| "badge" (`badge DIFFERENT`) | Lamborghini vs Audi | self-evident | — |

## Dropped (could not verify with a second source)
- Same bore, stroke and firing order: only Jalopnik says so, and the same article quotes different bore/stroke figures.
- Same gearbox: sources disagree (Urus listed as DCT in places, RS Q8 as torque-converter Tiptronic).
- 631 hp RS Q8 Performance (classic.com figure in the brief): that is a later model (2024+), not the 2022 car priced at
  $121,096, so the video compares the 2022 cars (641 vs 591 hp). Using 631 would mix model years.

The car images are the user's reference sheet (`assets/sheet_src.png`). All sound is synthesised; the voice is
Gemini TTS (Orus), one generation.
