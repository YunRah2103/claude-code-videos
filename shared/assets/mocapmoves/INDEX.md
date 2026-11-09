# Mocap fight-move library

Retargeted flat-figure moves built from the **CMU Graphics Lab Motion Capture Database**
(http://mocap.cs.cmu.edu/). Licence (FAQ): "The motion capture data may be copied, modified, or
redistributed without permission"; it may not be resold as a mocap product. Credit: "The data used in
this project was obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217."

Each `<name>.npz` holds `Q[frames, 31, 3]` at 120 fps in a canonical frame (x = facing forward,
y = up with ground 0 and the planted ankle at 40 px, z = lateral, root starting at x=z=0), retargeted onto
the flat-figure proportions in `build.py`, plus `names`, `parents`, `kind`, `clip`, `t0`, `t1`, `effector`,
`key` (attack contact = full extension after the effector speed peak; duck bottom; slip apex; block apex;
reaction onset = start of the head whip) and `dur`.
Raw ASF/AMC files are not committed; fetch them with `videos/seatbelt-fight/src/get_mocap.sh`, then run
`python shared/assets/mocapmoves/build.py`. `amc.py` is the ASF/AMC reader and FK.

| Move | Kind | What | Source (licence: CMU, free reuse) | Duration | Key |
|---|---|---|---|---|---|
| `ready` | stance | boxing guard bounce | CMU 14_01 22.40-23.05 s | 0.65 s | 0.000 s  |
| `step_in` | step | boxing step forward | CMU 14_03 19.85-20.30 s | 0.45 s | 0.000 s  |
| `step_back` | step | boxing step back | CMU 14_03 21.15-21.65 s | 0.50 s | 0.000 s  |
| `jab` | attack | lead-hand straight | CMU 14_03 3.50-4.20 s | 0.70 s | 0.367 s (lhand) |
| `cross` | attack | rear-hand straight | CMU 14_03 14.30-15.00 s | 0.70 s | 0.383 s (rhand) |
| `hook` | attack | rear hook (wide arc) | CMU 14_03 11.50-12.30 s | 0.80 s | 0.383 s (rhand) |
| `roundhouse` | attack | mawashi-geri roundhouse kick | CMU 135_07 0.30-1.60 s | 1.30 s | 0.667 s (rtoes) |
| `knee` | attack | knee strike (walking knee kicks) | CMU 86_06 16.25-16.90 s | 0.64 s | 0.267 s (rfemur) |
| `spin_kick` | attack | jumping spin kick (acrobatic, 60 fps source) | CMU 88_06 0.30-1.75 s | 1.45 s | 0.842 s (rtoes) |
| `lunge_punch` | attack | oi-zuki stepping lunge punch (finisher) | CMU 135_09 1.80-3.00 s | 1.20 s | 0.742 s (rhand) |
| `slip` | defence | head slip off the centre line | CMU 13_17 20.10-20.80 s | 0.70 s | 0.267 s  |
| `duck` | defence | duck under a punch | CMU 14_01 22.95-23.65 s | 0.70 s | 0.317 s  |
| `block` | defence | high arm block | CMU 144_26 3.90-4.70 s | 0.80 s | 0.375 s  |
| `stagger` | reaction | small stagger (smallStumble) | CMU 91_59 0.40-1.90 s | 1.50 s | 0.000 s  |
| `knock_back` | reaction | heavy backward lurch (StumbleWalk) | CMU 104_13 3.30-4.58 s | 1.27 s | 0.000 s  |
| `fall` | reaction | backward knock-down (RugPullFall) | CMU 90_18 0.60-3.25 s | 2.59 s | 0.000 s  |

Reactions are oriented so the head is driven backwards; attacks and defences face forward at frame 0.
Used by `videos/seatbelt-fight/src/fight6.py`.
