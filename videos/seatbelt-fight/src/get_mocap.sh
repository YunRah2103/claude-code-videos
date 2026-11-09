#!/usr/bin/env bash
# Download the CMU Graphics Lab mocap clips used by mocap_hook.py (see ../MOCAP.md).
set -euo pipefail
D="${MOCAP_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)/out/mocap-cmu}"
mkdir -p "$D"
for c in 14_01 14_02 90_18; do
  s=${c%_*}
  [ -s "$D/$s.asf" ] || curl -fsS -m 120 -o "$D/$s.asf" "http://mocap.cs.cmu.edu/subjects/$s/$s.asf"
  [ -s "$D/$c.amc" ] || curl -fsS -m 300 -o "$D/$c.amc" "http://mocap.cs.cmu.edu/subjects/$s/$c.amc"
done
echo "mocap in $D"
