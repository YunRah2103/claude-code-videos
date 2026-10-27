#!/bin/bash
# usage: render.sh out.mp4 startFrame endFrame [scale] [extra args]
cd "$(dirname "$0")"
OUT=$1; A=$2; B=$3; SC=${4:-1}; shift 4
npx remotion render src/index.ts Doc "$OUT" --frames=$A-$B --scale=$SC --browser-executable=/opt/pw-browsers/chromium --gl=swangle --concurrency=4 --codec=h264 --muted "$@"
