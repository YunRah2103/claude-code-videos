# Asset credits & licensing manifest — "The Rise and Fall of Jaguar"

## Summary
No third-party photographs, video footage, logos, music or sound-effect samples are used in this film.
The build environment's network policy blocked Wikimedia Commons, Pexels, Pixabay and Jaguar's media site,
so rights-cleared real footage could not be retrieved or verified. Rather than use unverified material or
fake "archive" imagery, everything on screen was created for this project.

| Asset | Source | Licence / status |
|---|---|---|
| Narration (5 clips, ~4m57s) | Supplied by the project owner: OpenAI.fm "Alloy" text-to-speech (`openai-fm-alloy-audio*.mp3`) | **Synthetic voice** — not a human narrator. Owner is responsible for OpenAI.fm terms. Lightly EQ'd/compressed/pitch-shifted (-0.6 semitone) in the mix. |
| Music score | Composed procedurally in `tools/score.py` (numpy synthesis) | Original, no samples. Free to use. |
| Engine, Le Mans and impact sounds | Synthesised in `tools/score.py` | Original. **Not recordings** of real Jaguar engines. |
| Car illustrations (E-Type, D-Type, C-Type, XK120, XJ, XF/S/X-Type saloons, F-Type, F-Pace, I-Pace, Group C racer, "Type 00/01") | Hand-drawn vector paths, `src/kit/carData.ts` | Original. Stylised side-profile drawings, labelled "illustration" on screen. The Type 00/01 drawing is a generic stylised GT and **not** the real production design. |
| Map of Great Britain, Circuit de la Sarthe | Hand-simplified outlines, `src/kit/maps.ts` | Original, schematic, not to scale. |
| Charts, timelines, gauges, ownership diagrams | Code (`src/kit`, `src/scenes`) | Original. |
| Typefaces | Cormorant Garamond, Inter via `@fontsource` (npm) | SIL Open Font License 1.1. |
| Film grain texture | Generated noise (`public/grain.png`) | Original. |
| Render stack | Remotion 4.0.533, React, FFmpeg | Remotion is source-available with its own company licence — check eligibility for your use. |

Jaguar, E-Type, D-Type, XK120, F-Type, I-Pace, Range Rover, Defender, BMW, Mercedes-Benz, Audi, Ford and Tata
are trademarks of their owners and are used here editorially, as names only (no logos).

## Facts to double-check before publishing
The environment was offline for research, so figures come from the supplied narration and general knowledge:
- Sales: "more than 180,000 (FY2018/19)" and "under 67,000 (FY2023/24)" are as stated in the narration. Only those two years are plotted; intermediate years are intentionally not drawn.
- Type 01: "electric four-door grand tourer", "more than 1,000 hp", "from £130,000", unveiled October 2026, customers in 2027 are as stated in the narration/brief. The on-screen "orders early 2027 / deliveries later 2027" follows the brief.
- Final combustion-engine car, December 2025 (shown without a model name on screen).
- Historical figures added on screen from memory: Ford ≈ $2.5bn (1989), Tata ≈ $2.3bn (2008), 1984 flotation, XJR-9 (1988) / XJR-12 (1990), E-Type 3.8-litre / 265 bhp, Le Mans 1957 1-2-3-4-6.
- 2024 discontinued models shown: XE, XF, E-Pace, F-Type.
