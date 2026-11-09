# Motion-capture sources (hook mocap test)

Source: **CMU Graphics Lab Motion Capture Database**, http://mocap.cs.cmu.edu/
(ASF skeleton + AMC motion, 120 fps; parsed directly by `src/mocap.py`, same data as the BVH conversions).

Licence (from http://mocap.cs.cmu.edu/faqs.php, checked 2026-11-09): "The motion capture data may be
copied, modified, or redistributed without permission." The database asks for this acknowledgement:
"The data used in this project was obtained from mocap.cs.cmu.edu. The database was created with
funding from NSF EIA-0196217." The FAQ also says the data must not be resold directly as a mocap
product; using it inside an animation is allowed.

| Role | Clip | CMU description | Range used |
|---|---|---|---|
| Hero: duck, then straight right | 14_01 | subject 14, "boxing" | 22.3–26.2 s (impact detected at 23.75 s) |
| Opponent before the hit: punch | 14_02 | subject 14, "boxing" (second take) | 13.6–16.0 s |
| Opponent hit reaction | 90_18 | subject 90, "RugPullFall" (backward knock-down) | 0–3.25 s, starting at the detected head-whip onset (1.008 s) |

There is no "get punched" clip in CMU. 91_59 "smallStumble" was tried first, but it barely moves (about 25 px), so the
reaction is a real backward fall, started on the impact frame and oriented so he falls away from the hero.

Raw AMC/ASF files are not committed. Fetch them with `src/get_mocap.sh` (into `out/mocap-cmu/`).
`src/mocap_poses.npz` holds the retargeted per-frame joint positions used for the render
(allowed: the licence permits modified redistribution).

What is processed rather than captured: bone lengths retargeted to our figure, a 1-frame
Gaussian low-pass, foot-plant locking (2-bone IK), the time remap (slow-in, 3-frame hit-stop),
a 0.18 s pose blend from the punch take into the reaction take, a 0.4 s blend back to the
first pose so the loop closes, and ONE added layer: a 260 px eased knock-back slide of the
opponent's root during the fall (`KNOCK` in `mocap_hook.py`) so he lands clear of the hero.
No poses are hand-keyed.

## 6 s fight test (`src/fight6.py`)

Uses the retargeted move library in `shared/assets/mocapmoves/` (see its `INDEX.md` for every move's
clip, time range, duration and key frame). Additional CMU clips: 14_03, 13_17 (boxing), 135_07 (roundhouse),
135_09 (oi-zuki lunge punch), 144_26 (blocks), 86_06 (knee kicks), 88_06 (jump spin kick), 104_13
(StumbleWalk). Same CMU licence. `get_mocap.sh` fetches all of them.
The choreography is new: `fight6_choreo.json` sequences library moves (key-aligned, speed within ±25%,
mirroring). Not captured: the cross-fades, a stage nudge spread over each attack's approach, foot-plant cleanup,
anticipation lean, contact IK, head look-at, hit-stops, and the finisher's launch arc (procedural, disclosed).
