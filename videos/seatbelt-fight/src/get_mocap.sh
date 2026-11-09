#!/usr/bin/env bash
# Download the CMU Graphics Lab mocap clips used by mocap_hook.py (see ../MOCAP.md).
set -euo pipefail
D="${MOCAP_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)/out/mocap-cmu}"
mkdir -p "$D"
for c in 14_01 14_02 14_03 13_17 135_04 135_07 135_09 144_07 144_26 86_06 88_06 90_18 91_59 23_12 104_13; do
  s=${c%_*}
  [ -s "$D/$s.asf" ] || curl -fsS -m 120 -o "$D/$s.asf" "http://mocap.cs.cmu.edu/subjects/$s/$s.asf"
  [ -s "$D/$c.amc" ] || curl -fsS -m 300 -o "$D/$c.amc" "http://mocap.cs.cmu.edu/subjects/$s/$c.amc"
done
echo "mocap in $D"
