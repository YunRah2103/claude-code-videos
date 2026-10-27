#!/bin/bash
# Voice processing + ducked mix. usage: mix.sh score.wav out.m4a
set -e
cd "$(dirname "$0")/.."
SC=$1; OUT=$2
VOICE="highpass=f=75,asetrate=24000*0.965,aresample=48000,atempo=1.0363,lowshelf=f=170:g=3:t=q:w=0.7,equalizer=f=3200:t=q:w=1.2:g=2.2,equalizer=f=7500:t=q:w=2:g=-2,acompressor=threshold=-22dB:ratio=3:attack=8:release=140:makeup=4,aecho=0.85:0.9:55|110:0.16|0.08"
ffmpeg -v error -y \
 -i public/audio/n1.mp3 -i public/audio/n2.mp3 -i public/audio/n3.mp3 -i public/audio/n4.mp3 -i public/audio/n5.mp3 -i "$SC" \
 -filter_complex "
 [0:a]${VOICE},adelay=600|600[v1];
 [1:a]${VOICE},adelay=66400|66400[v2];
 [2:a]${VOICE},adelay=125100|125100[v3];
 [3:a]${VOICE},adelay=190400|190400[v4];
 [4:a]${VOICE},adelay=249400|249400[v5];
 [v1][v2][v3][v4][v5]amix=inputs=5:normalize=0:duration=longest,apad=whole_dur=306,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[vo];
 [5:a]aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur=306[mu];
 [vo]asplit=2[vk][vm];
 [mu][vk]sidechaincompress=threshold=0.02:ratio=3:attack=25:release=500:makeup=1[md];
 [md]volume=0.8[md2];
 [vm]volume=1.25[vm2];
 [md2][vm2]amix=inputs=2:normalize=0:duration=longest,loudnorm=I=-14:TP=-1.5:LRA=11,atrim=0:304.5[o]" \
 -map "[o]" -c:a aac -b:a 256k -ar 48000 "$OUT"
