# Pixel-stickman style (pixel6) — measured from the reference teaser

Reference: 1280x720, 30 fps, 10.1 s (picture ends at ~5.1 s, then black). Frames studied at 0.2 s,
0.5 s (dark cut), 1.5 s, 2.7 s, 3.4 s, 4.1 s (dark cut), with 3x nearest crops.

| Measure | Reference | pixel6 |
|---|---|---|
| Pixel block | 7.7–8.3 px at 720p (FFT of gradients): ~1/90 of frame height, ~1/160 of width; slightly non-integer (camera zoom) | 270x480 art, integer 4x nearest -> 1/270 of width (finer; 360x640 x3 would be finer still) |
| Colours | ~100–240 block-centre colours cover 90 % of a frame (12-level bins, compression inflates) | 94–144 unique colours per frame (measured every 0.5 s) |
| Shading | painted clumps + hand banding; no ordered dither; soft grey-white cumulus, horizontal brush streaks on hills | noise-driven clumps quantised onto 4–9 tone ramps; banded sky with wobbly edges; no dither |
| Figure | ~13–16 blocks tall; limbs ~1 block; head ~3–4 blocks (~25 % of height); cape a big wedge ~half the figure | ~56 px tall wide (12 % of frame, ref ~14 %); limbs 2 px, torso 3 px; head r 5–6 px (~20 %); cape 7-node Verlet wedge ~30 px |
| Slash | clean white crescent, thick middle tapering to points, 1-block soft edge + faint glow, red bits on big hits | 4x-supersampled crescent coverage -> 3 shade levels, 1-px glow at 16 %, red trailing edge on fire hits |
| Bursts | red/orange blobs, single-pixel red embers, a few glowing red dots | jagged core blobs, falling 1-px embers, every 5th ember 2x2 with a glow |
| Dark cut | mean luma ~38 (normal 108–176); navy-black grade, painting faintly visible; capes and effects keep colour | bg * (.09,.11,.13) + navy(14,19,28); 3 frames on kicks, 4 on the finisher, 2 at the cut to the transition |

Rules kept in code: all positions and camera offsets rounded to whole art pixels; parallax layers pasted
at integer offsets; limbs are Bresenham lines with a fixed square brush redrawn every 60 fps frame; no
sprite rotation/scaling, no AA on the art layer except the slash coverage shading; light 2-step vignette.
