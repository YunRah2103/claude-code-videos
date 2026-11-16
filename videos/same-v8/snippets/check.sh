#!/usr/bin/env bash
# Runs every on-screen snippet (the on-screen lines verbatim, plus minimal wrappers) and prints the output.
set -e
cd "$(dirname "$0")"
T=$(mktemp -d)
echo "s1.py  -> $(python3 s1.py)"
g++ -std=c++17 -Wall -Werror -o "$T/s2" s2.cpp && echo "s2.cpp -> $("$T/s2")"
echo "s3.py  -> $(python3 s3.py | tr '\n' '|')"
g++ -std=c++17 -Wall -Werror -o "$T/s4" s4.cpp && echo "s4.cpp -> $("$T/s4")"
echo "s5.py  -> $(python3 s5.py)"
g++ -std=c++17 -Wall -Werror -o "$T/s6" s6.cpp && echo "s6.cpp -> $("$T/s6" | tr '\n' '|')"
echo "s7.py  -> $(echo y | python3 s7.py | tr '\n' '|')"
