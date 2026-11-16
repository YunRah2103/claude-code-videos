#!/usr/bin/env bash
# Runs every on-screen snippet; prints the values the video claims.
set -e
cd "$(dirname "$0")"
echo "s1.py -> $(python3 s1.py)"
echo "s2.py -> $(python3 s2.py)"
g++ -std=c++17 -Wall -o /tmp/s3 s3.cpp && echo "s3.cpp -> $(/tmp/s3)"
g++ -std=c++17 -Wall -o /tmp/s4 s4.cpp && echo "s4.cpp -> $(/tmp/s4)"
echo "s5.py -> $(echo V8 | python3 s5.py)"
