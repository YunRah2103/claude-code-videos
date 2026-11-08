"""ONE vs TWO — original anime-style fight: one swordsman against two attackers.

Usage:
  python render.py still OUTDIR t1 t2 ...      # preview PNGs (real seconds)
  python render.py video OUT.mp4 [start end]  # render (start/end in real seconds)
"""
import math, os, sys, random, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from engine import *

DUR = 36.5

LOOK_H = dict(kind='hero', top='#eef1fb', pants='#25304d', skin='#f4dac8', hair='#171a33',
              hair_hl='#5fe9ff', acc='#3fe3ff', eye='#7ff7ff')
LOOK_A = dict(kind='oni', top='#c0263a', pants='#1c0e15', skin='#2a0c14', hair='#efe3d0',
              acc='#ff5a36', eye='#ffd23a')
LOOK_B = dict(kind='shade', top='#6a3fa6', pants='#160e25', skin='#e9d2c8', hair='#2e1a52',
              acc='#c77dff', eye='#ff6fe0')

HERO, ONI, KAGE = Fighter('hero', LOOK_H), Fighter('oni', LOOK_A), Fighter('kage', LOOK_B)
HERO.sheath_from = 0.0
CAM, WARP = Camera(), Warp()
_FX, CUES, POST, TEXT = [], [], [], []   # anim-timed; converted after the warp is final

def fx(kind, ta, d, layer='front', **kw): _FX.append((ta, kind, d, layer, kw))
def sfx(ta, name, vol=1.0): CUES.append((ta, name, vol))
def post(kind, ta, d, amt=1.0): POST.append((kind, ta, d, amt))
def at(F, ta, joint):
    Wd, _ = F.world(F.anim(ta)); return Wd[joint]

def hit(ta, pos, big=True, col='#ffffff', stop=0.0, shake=0, iframe=False, sound=None, size=1.0, slash=None):
    x, y = pos
    fx('impact' if big else 'spark', ta, 0.45 if big else 0.25, x=x, y=y, col=col, size=size)
    if slash: fx('slash', ta - 0.01, 0.3, x=x, y=y, col=col, **slash)
    if stop: WARP.stop(ta, stop)
    if shake: post('shake', ta, 0.45, shake)
    if iframe: post('iframe', ta, 0.07)
    if big: post('chroma', ta, 0.25, 6 if iframe else 3)
    sfx(ta, sound or ('bighit' if big else 'block'), 1.0)

def ground_hit(ta, x, big=1.0, col='#ffb38a'):
    fx('ring', ta, 0.6, layer='back', x=x, r=300*big, col=col)
    fx('dust', ta, 1.0, layer='back', x=x, n=int(18*big), size=big)
    fx('debris', ta, 1.0, x=x, n=int(12*big))
    fx('crack', ta, 4.0, layer='back', x=x, n=7)
    post('shake', ta, 0.6, 18*big); sfx(ta, 'slam', 0.9*big)

# ================================================================= choreography
Z, A, B = HERO, ONI, KAGE
ACC_H, ACC_A, ACC_B = LOOK_H['acc'], LOOK_A['acc'], LOOK_B['acc']

def strike(F, t, pose, wind=None, wt=0.09, rec=None, rt=0.2, **kw):
    if wind: F.key(t - wt, wind, ease='io')
    F.key(t, pose, ease='back', **kw)
    if rec: F.key(t + rt, rec, ease='io')

def clang(t, F, joint, size=1.3):
    hit(t, at(F, t, joint), big=False, col='#ffffff', stop=0.04, shake=6, sound='clang', size=size)

# ---------------- ACT 1: arrival
Z.key(0, 'stand', x=0, face=1).key(2.6, 'stand', ease='io').key(3.3, 'look', ease='io')
TEXT.append(('title', 0.5, 2.0))
fx('glint', 3.0, 0.35, x=10, y=-152, col='#7ff7ff', size=40); sfx(3.0, 'shing', 0.5)
A.key(0, 'dive', x=-230, alt=2600, face=1).key(3.45, 'dive', alt=1300, ease='lin') \
 .key(3.75, 'land', alt=0, ease='in').key(4.35, 'guard', ease='io')
B.key(0, 'dive', x=230, alt=2600, face=-1).key(4.45, 'dive', alt=1300, ease='lin') \
 .key(4.75, 'land', alt=0, ease='in').key(5.35, 'guard', ease='io')
ground_hit(3.75, -230, 1.4); ground_hit(4.75, 230, 1.4)
sfx(3.4, 'fall', 0.7); sfx(4.4, 'fall', 0.7)
Z.key(3.8, 'look', face=-1, ease='back').key(4.8, 'look', face=1, ease='back').key(5.6, 'guard', ease='io')
TEXT += [('card', 3.85, 1.0, 'AKA ONI', LOOK_A), ('card', 4.85, 1.0, 'KAGE', LOOK_B), ('card', 5.45, 0.6, 'KAZE', LOOK_H)]

# ---------------- ACT 2: hand to hand
# Oni charges, Kaze slips under and answers with a rising elbow
A.key(6.0, 'guard', x=-230).key(6.12, 'run', x=-212, ease='in').key(6.55, 'run', x=-95, ease='lin') \
 .key(6.6, 'guard2', x=-82, ease='io').key(6.7, 'cross', x=-58, ease='back')
sfx(6.62, 'whoosh', 0.8)
Z.key(6.45, 'guard', face=-1, ease='back').key(6.64, 'crouch', ease='back').key(6.78, 'crouch')
strike(Z, 6.88, 'elbow', x=-14)
hit(6.88, at(Z, 6.88, 'fel'), col=ACC_H, stop=0.08, shake=10)
A.key(6.8, 'cross').key(6.9, 'hurt', x=-78, ease='back').key(7.25, 'hurt', x=-140, ease='out').key(7.7, 'guard', x=-170, ease='io')
Z.key(7.1, 'guard', ease='io')
# Kage sprints in: spinning hook kick, Kaze blocks and skids
B.key(6.9, 'guard', x=230).key(7.0, 'run', x=214, ease='in').key(7.34, 'run', x=110, ease='lin') \
 .key(7.42, 'chamber', x=92, face=1, ease='out').key(7.52, 'kick', x=74, face=-1, ease='back')
sfx(7.42, 'whoosh', 0.9)
Z.key(7.25, 'guard', face=1, ease='back').key(7.5, 'block', ease='back')
hit(7.52, at(B, 7.52, 'ftoe'), big=False, col=ACC_B, stop=0.05, shake=9, size=1.5)
Z.key(7.82, 'block', x=-62, ease='out')
fx('dust', 7.53, 0.8, layer='back', x=-30, n=10, dir=1, spread=0.5); sfx(7.55, 'skid', 0.6)
# Kage's combo, Kaze defends then kicks him away
B.key(7.8, 'guard', x=60, ease='io').key(8.0, 'guard', x=-2, ease='io')
strike(B, 8.1, 'jab', wind='guard2', wt=0.07); Z.key(8.1, 'block', ease='back')
hit(8.1, at(B, 8.1, 'fhand'), big=False, col=ACC_B, shake=4)
B.key(8.18, 'guard', ease='io'); strike(B, 8.27, 'cross'); Z.key(8.27, 'block', x=-68, ease='back')
hit(8.27, at(B, 8.27, 'rhand'), big=False, col=ACC_B, shake=4)
B.key(8.36, 'guard', ease='io').key(8.44, 'chamber', ease='io').key(8.55, 'kick', ease='back')
Z.key(8.5, 'crouch', ease='back'); sfx(8.5, 'whoosh', 0.8)
B.key(8.66, 'guard', ease='io')
Z.key(8.66, 'chamber', x=-52, ease='back').key(8.78, 'kick', x=-40, ease='back')
hit(8.78, at(Z, 8.78, 'ftoe'), col=ACC_H, stop=0.1, shake=14, iframe=True, size=1.2)
B.key(8.78, 'guard').key(8.82, 'flyback', alt=30, ease='back') \
 .key(9.3, 'flyback', x=200, alt=40, arc=90, rot=-270, ease='lin').key(9.45, 'lying', x=240, alt=0, rot=-450, ease='in') \
 .key(9.6, 'lying', x=270, alt=32, rot=-440, ease='out').key(9.75, 'lying', x=285, alt=0, rot=-450, ease='in')
ground_hit(9.45, 240, 0.9); fx('dust', 9.75, 0.6, layer='back', x=285, n=8, size=0.6); sfx(9.75, 'land', 0.6)
Z.key(9.05, 'guard', ease='io')
# Oni from behind: Kaze spins into a hook kick, then a point-blank exchange
A.key(9.7, 'guard', x=-170).key(9.8, 'run', x=-160, ease='in').key(10.02, 'run', x=-112, ease='lin').key(10.08, 'guard2', x=-108, ease='io')
Z.key(10.02, 'guard2', face=1, ease='io').key(10.14, 'kick', face=-1, ease='back')
A.key(10.14, 'block', ease='back')
hit(10.14, at(Z, 10.14, 'ftoe'), big=False, col=ACC_H, shake=8, size=1.5)
Z.key(10.24, 'guard', ease='io'); A.key(10.24, 'guard', ease='io')
fx('speedlines', 10.24, 1.25, focus=(-75, -125))
moves = ['jab', 'cross', 'elbow', 'jab', 'cross', 'jab', 'elbow', 'cross']
t = 10.32
for i, mv in enumerate(moves):
    atk, dfn = (A, Z) if i % 2 == 0 else (Z, A)
    atk.key(t - 0.05, 'guard2', ease='io')
    atk.key(t, mv, ease='back'); dfn.key(t, 'block', ease='back')
    hand = {'jab': 'fhand', 'cross': 'rhand', 'elbow': 'fel'}[mv]
    hit(t, at(atk, t, hand), big=False, col=ACC_A if atk is A else ACC_H, shake=5)
    atk.key(t + 0.07, 'guard', ease='io'); dfn.key(t + 0.07, 'guard', ease='io')
    t += 0.13
# fists collide
A.key(11.45, 'guard2', ease='io').key(11.56, 'cross', x=-100, ease='back')
Z.key(11.45, 'guard2', ease='io').key(11.56, 'cross', x=-48, ease='back')
pa, pz = at(A, 11.56, 'rhand'), at(Z, 11.56, 'rhand')
hit(11.56, ((pa[0]+pz[0])/2, (pa[1]+pz[1])/2), col='#ffffff', stop=0.3, shake=20, iframe=True, size=1.7)
fx('ring', 11.56, 0.6, layer='back', x=-74, r=380, col=ACC_H); sfx(11.56, 'boom', 0.9); post('chroma', 11.56, 0.5, 8)
A.key(11.62, 'hurt', x=-120, ease='back').key(12.0, 'guard', x=-230, ease='out')
Z.key(11.62, 'hurt', x=-30, ease='back').key(12.0, 'guard', x=40, ease='out')
fx('dust', 11.62, 0.8, layer='back', x=-120, n=8, dir=-1, spread=0.5); fx('dust', 11.62, 0.8, layer='back', x=-30, n=8, dir=1, spread=0.5)
# Kage recovers in the background
B.key(10.6, 'lying').key(11.2, 'kneel', rot=-360, ease='io').key(11.7, 'guard', x=280, ease='io')

# ---------------- coordinated assault -> Kaze is smashed into the ground
B.key(12.0, 'guard', x=280).key(12.1, 'crouch', ease='io').key(12.45, 'dive', x=95, alt=260, ease='out').key(12.65, 'airkick', x=45, alt=0, ease='in')
sfx(12.12, 'whoosh', 0.8)
Z.key(12.35, 'crouch', face=1, ease='back').key(12.7, 'tuck', x=-62, alt=0, arc=150, rot=-360, ease='lin').key(12.78, 'land', x=-70, ease='out')
sfx(12.38, 'whoosh', 0.7)
ground_hit(12.65, 45, 1.1)
A.key(12.5, 'guard', x=-230).key(12.6, 'run', x=-214, ease='in').key(12.82, 'run', x=-160, ease='lin').key(12.9, 'sweep', x=-132, ease='back')
Z.key(12.84, 'tuck', alt=92, ease='out')
sfx(12.85, 'whoosh', 0.8)
B.key(12.75, 'crouch', x=-12, ease='io').key(12.97, 'upkick', x=-36, face=-1, ease='back')
Z.key(12.97, 'tuck', alt=96, ease='lin')
hit(12.97, at(B, 12.97, 'ftoe'), col=ACC_B, stop=0.1, shake=16, iframe=True, size=1.3)
Z.key(13.02, 'flyback', alt=125, ease='back').key(13.36, 'flyback', x=-62, alt=430, rot=-480, ease='out')
A.key(12.97, 'crouch', x=-130, ease='io').key(13.3, 'axeup', x=-92, alt=470, face=1, ease='out').key(13.42, 'axedown', x=-78, alt=445, ease='back')
WARP.slow(13.15, 0.27, 0.35)
sfx(13.0, 'whoosh', 0.9)
Z.key(13.42, 'flyback', x=-62, alt=432)
hit(13.42, at(A, 13.42, 'ftoe'), col=ACC_A, stop=0.15, shake=26, iframe=True, size=1.6)
post('chroma', 13.42, 0.6, 10)
Z.key(13.64, 'lying', x=-56, alt=0, rot=-450, ease='in')
ground_hit(13.64, -56, 2.0); WARP.stop(13.64, 0.08); post('flash', 13.64, 0.25)
fx('dust', 13.64, 2.2, layer='front', x=-56, n=26, size=2.2, spread=0.7)
A.key(13.92, 'land', x=-150, alt=0, ease='in').key(14.3, 'guard', ease='io')
B.key(13.1, 'guard', x=-40, ease='io').key(13.6, 'guard', x=60, ease='io')
# the approach
A.key(14.5, 'guard', x=-150).key(16.3, 'guard2', x=-125, ease='io')
B.key(14.5, 'guard', x=60).key(16.3, 'guard2', x=20, ease='io')
for tt in (14.8, 15.4, 16.0): sfx(tt, 'heart', 1.0)

# ---------------- ACT 3: awakening
Z.key(16.4, 'lying').key(16.95, 'kneel', rot=-360, ease='io').key(17.6, 'kneel').key(18.0, 'power', ease='io')
fx('glint', 17.35, 0.35, x=-48, y=-120, col='#7ff7ff', size=46); sfx(17.35, 'shing', 0.5)
fx('aura', 17.6, 9.4, fighter='hero', col=ACC_H); sfx(17.4, 'rumble', 1.0)
fx('crack', 17.9, 9.0, layer='back', x=-56, n=12, hot=True, col=ACC_H)
fx('ring', 18.1, 0.7, layer='back', x=-56, r=560, col=ACC_H)
fx('impact', 18.1, 0.5, x=-56, y=-100, col=ACC_H, size=1.6)
post('flash', 18.1, 0.4); post('shake', 18.1, 0.8, 22); post('iframe', 18.1, 0.07); WARP.stop(18.1, 0.1)
sfx(18.1, 'boom', 1.0)
A.key(18.1, 'guard2', x=-125).key(18.2, 'hurt', x=-160, ease='back').key(18.7, 'guard', x=-240, ease='out')
B.key(18.1, 'guard2', x=20).key(18.2, 'hurt', x=60, ease='back').key(18.7, 'guard', x=140, ease='out')
fx('dust', 18.2, 0.8, layer='back', x=-180, n=10, dir=-1); fx('dust', 18.2, 0.8, layer='back', x=80, n=10, dir=1)
Z.key(18.7, 'iai', face=-1, ease='io').hold(19.5)
HERO.glow_from = 17.6

# ---------------- ACT 4: the sword
# draw-cut through Oni
Z.key(19.58, 'swback', x=-110, sw=-150, ease='in').key(19.68, 'swfwd', x=-335, ease='back')
fx('speedlines', 19.55, 0.25, mode='horiz'); sfx(19.56, 'shing', 0.9)
hit(19.66, (-240, -105), col=ACC_H, stop=0.12, shake=14, iframe=True,
    slash=dict(r=100, a0=200, a1=340, w=32, squash=0.45), sound='cut')
A.key(19.66, 'guard', x=-240).key(19.7, 'hurt', x=-226, ease='back').key(20.2, 'hurt', x=-212).key(20.6, 'kneel', x=-206, face=-1, ease='io')
# Kage rushes in: three parries, then a rising cut
B.key(19.6, 'guard', x=140).key(19.7, 'run', x=122, ease='in').key(20.15, 'run', x=-205, ease='lin').key(20.2, 'guard2', x=-258, ease='io')
Z.key(19.95, 'swguard', face=1, ease='back')
strike(B, 20.27, 'jab', x=-266); Z.key(20.27, 'swguard', ease='back'); clang(20.27, B, 'fhand')
B.key(20.33, 'guard2', ease='io'); strike(B, 20.41, 'cross'); Z.key(20.41, 'swhigh', ease='back'); clang(20.41, B, 'rhand')
B.key(20.47, 'chamber', ease='io').key(20.56, 'kick', ease='back'); Z.key(20.56, 'swguard', x=-345, ease='back'); clang(20.56, B, 'ftoe', 1.6)
Z.key(20.68, 'swup', x=-336, ease='back').key(20.8, 'swdown', x=-312, ease='back')
hit(20.8, at(B, 20.8, 'chest'), col=ACC_H, stop=0.1, shake=14, iframe=True,
    slash=dict(r=110, a0=-110, a1=60, w=34), sound='cut')
B.key(20.66, 'guard', ease='io').key(20.8, 'guard').key(20.84, 'flyback', alt=60, ease='back').key(21.22, 'flyback', x=-222, alt=330, rot=-60, ease='out')
# aerial combo
Z.key(20.95, 'crouch', sw=150, ease='io').key(21.2, 'tuck', x=-252, alt=305, sw=200, ease='out')
sfx(20.98, 'whoosh', 0.9)
post('dark', 21.15, 0.8, 0.75); fx('speedlines', 21.15, 0.75, focus=(-230, -400))
WARP.slow(21.2, 0.6, 0.45)
Z.key(21.27, 'swdown', alt=330, face=1, ease='back')
hit(21.27, at(B, 21.27, 'chest'), col=ACC_H, stop=0.05, shake=8, slash=dict(r=95, a0=-80, a1=100, w=28), sound='cut')
B.key(21.27, 'flyback', x=-216, alt=340, rot=-80).key(21.31, 'hurt', x=-206, alt=350, rot=-110, ease='back')
Z.key(21.42, 'swup', alt=360, ease='back')
hit(21.42, at(B, 21.42, 'chest'), col=ACC_H, stop=0.05, shake=8, slash=dict(r=95, a0=100, a1=-60, w=28), sound='cut')
B.key(21.42, 'hurt', x=-198, alt=365, rot=-140).key(21.46, 'flyback', x=-192, alt=380, rot=-180, ease='back')
Z.key(21.5, 'swfwd', alt=380, rot=0, ease='io').key(21.62, 'swfwd', alt=386, rot=360, ease='lin')
fx('slash', 21.56, 0.3, x=-252, y=-420, r=120, a0=0, a1=340, w=14, col=ACC_H); sfx(21.55, 'shing', 0.7)
Z.key(21.68, 'swup', alt=390, ease='back').key(21.76, 'swdown', alt=382, ease='back')
hit(21.76, at(B, 21.76, 'chest'), col=ACC_H, stop=0.1, shake=16, iframe=True, size=1.3, slash=dict(r=110, a0=-100, a1=80, w=34), sound='cut')
B.key(21.76, 'flyback', x=-188, alt=386, rot=-200).key(21.98, 'lying', x=-120, alt=0, rot=-270, ease='in')
ground_hit(21.98, -120, 1.4)
Z.key(22.2, 'land', x=-260, alt=0, ease='in')
fx('dust', 22.2, 0.7, layer='back', x=-260, n=8, size=0.7); sfx(22.2, 'land', 0.7)
# Oni attacks the landing: two parries, then a horizontal cut sends him flying
A.key(21.8, 'kneel').key(22.0, 'crouch', x=-200, face=-1, ease='io').key(22.3, 'dive', x=-222, alt=140, ease='out').key(22.42, 'cross', x=-214, alt=0, ease='in')
Z.key(22.32, 'swguard', face=1, ease='back').key(22.42, 'swhigh', ease='back'); clang(22.42, A, 'rhand', 1.6)
A.key(22.5, 'guard2', ease='io'); strike(A, 22.6, 'jab'); Z.key(22.6, 'swguard', ease='back'); clang(22.6, A, 'fhand')
A.key(22.68, 'chamber', ease='io').key(22.77, 'kick', ease='back'); Z.key(22.77, 'swhigh', ease='back'); clang(22.77, A, 'ftoe', 1.5)
Z.key(22.86, 'swback', ease='io').key(22.96, 'swfwd', x=-244, ease='back')
hit(22.96, at(A, 22.96, 'chest'), col=ACC_H, stop=0.1, shake=14, iframe=True, slash=dict(r=105, a0=200, a1=340, w=32, squash=0.5), sound='cut')
A.key(22.86, 'guard', ease='io').key(22.96, 'guard').key(23.0, 'flyback', alt=30, ease='back') \
 .key(23.36, 'flyback', x=-40, alt=40, arc=60, rot=-90, ease='lin').key(23.46, 'lying', x=-20, alt=0, rot=-90, ease='in')
ground_hit(23.46, -20, 0.8)

# ---------------- finale: both charge, one draw-cut through both
Z.key(23.5, 'swguard', ease='io').key(23.95, 'iai', face=1, ease='io').hold(24.76)
B.key(23.6, 'lying').key(24.1, 'kneel', rot=-360, face=-1, ease='io').key(24.25, 'run', x=-132, ease='in') \
 .key(24.6, 'run', x=-176, ease='lin').key(24.8, 'dive', x=-196, alt=55, ease='out')
A.key(23.6, 'lying').key(24.1, 'kneel', rot=0, face=-1, ease='io').key(24.22, 'run', x=-36, ease='in') \
 .key(24.62, 'run', x=-128, ease='lin').key(24.82, 'airkick', x=-170, alt=50, ease='out')
sfx(24.3, 'whoosh', 0.6)
WARP.slow(24.78, 0.5, 0.3)
Z.key(24.8, 'swback', x=-232, sw=-150, ease='in').key(24.9, 'swfwd', x=60, ease='back')
fx('speedlines', 24.8, 0.3, mode='horiz'); post('dark', 24.8, 0.7, 0.8)
hit(24.88, at(B, 24.88, 'chest'), col=ACC_H, size=1.4, slash=dict(r=110, a0=200, a1=340, w=34, squash=0.45), sound='cut')
hit(24.88, at(A, 24.88, 'chest'), col=ACC_H, stop=0.4, shake=20, iframe=True, size=1.4, slash=dict(r=110, a0=200, a1=340, w=34, squash=0.45))
post('flash', 24.88, 0.3)
A.key(24.9, 'flyback', x=-180, alt=50).key(25.45, 'lying', x=-290, alt=0, arc=60, rot=-90, ease='lin')
B.key(24.9, 'flyback', x=-205, alt=55).key(25.5, 'lying', x=-335, alt=0, arc=60, rot=-90, ease='lin')
ground_hit(25.45, -290, 0.8); ground_hit(25.5, -335, 0.8)
Z.hold(25.9).key(26.1, 'swguard', ease='io').key(26.24, 'swfwd', ease='back').key(26.8, 'iai', ease='io')
sfx(26.24, 'whoosh', 0.5); sfx(26.8, 'chin', 1.0)
WARP.stop(26.8, 0.45)
A.hold(25.9).key(26.6, 'kneel', rot=0, face=1, ease='io').hold(26.82).key(26.9, 'hurt', ease='back').key(27.35, 'facedown', rot=90, ease='in')
B.hold(25.9).key(26.6, 'kneel', rot=0, face=1, ease='io').hold(26.82).key(26.9, 'hurt', ease='back').key(27.4, 'facedown', rot=90, ease='in')
for F in (A, B):
    c = at(F, 26.82, 'chest')
    fx('slash', 26.84, 0.45, x=c[0], y=c[1], r=110, a0=200, a1=330, w=36, col=ACC_H)
    fx('slash', 26.88, 0.45, x=c[0], y=c[1], r=110, a0=-30, a1=110, w=36, col=ACC_H)
    fx('impact', 26.88, 0.5, x=c[0], y=c[1], col=ACC_H, size=1.4)
post('flash', 26.86, 0.5); post('iframe', 26.86, 0.1); post('shake', 26.86, 0.8, 22); post('chroma', 26.86, 0.6, 9)
sfx(26.86, 'cut', 1.0); sfx(26.9, 'boom', 1.0)
ground_hit(27.35, -290, 0.6); ground_hit(27.4, -335, 0.6)
Z.hold(27.3).key(28.2, 'stand', ease='io')
TEXT.append(('fin', 29.0, 2.6)); post('fade', 30.6, 1.0)

# ================================================================= camera (cuts, close-ups, tracking)
def cut(t, a, until=None, to=None):
    CAM.key(t, a[0], a[1], a[2], 'hold', a[3] if len(a) > 3 else 0)
    if until:
        b = to or a; CAM.key(until, b[0], b[1], b[2], 'io', b[3] if len(b) > 3 else 0)

def center(Fs, t):
    xs, ys = [], []
    for F in Fs:
        Wd, _ = F.world(F.anim(t)); xs.append(Wd['hip'][0]); ys.append(Wd['hip'][1])
    return sum(xs)/len(xs), sum(ys)/len(ys)

def follow(t0, t1, Fs, z, dy=-30, rot=0, rot1=None, z1=None, step=0.08):
    n = max(2, int((t1 - t0)/step)); rot1 = rot if rot1 is None else rot1; z1 = z if z1 is None else z1
    for i in range(n + 1):
        t = t0 + (t1 - t0)*i/n
        pts = [center(Fs, t + o) for o in (-0.12, -0.06, 0, 0.06, 0.12)]
        cx = sum(p[0] for p in pts)/5; cy = sum(p[1] for p in pts)/5 + dy
        CAM.key(t, cx, cy, lerp(z, z1, i/n), 'hold' if i == 0 else 'lin', lerp(rot, rot1, i/n))

def close(t, F, joint, z, until, z1=None, dx=0, dy=0, rot=0):
    x, y = at(F, (t + until)/2, joint)
    cut(t, (x + dx, y + dy, z, rot), until, (x + dx, y + dy, z1 or z*1.08, rot))

cut(0, (0, -150, 1.05), 2.59, (0, -135, 1.6))
close(2.6, Z, 'head', 6.5, 3.24, 7.3, dx=4)
cut(3.25, (0, -210, 0.95), 3.73, (-80, -180, 1.05))
cut(3.76, (-230, -110, 2.6, -4), 4.39, (-226, -118, 3.0, -2))
cut(4.4, (60, -210, 1.0), 4.73, (90, -180, 1.05))
cut(4.76, (230, -110, 2.6, 4), 5.39, (226, -118, 3.0, 2))
cut(5.4, (0, -80, 1.35), 5.99, (0, -95, 1.55))
follow(6.0, 6.99, [A, Z], 2.2, rot=-3, z1=2.5)
follow(7.0, 7.84, [Z, B], 2.3, rot=3, z1=2.6)
follow(7.85, 8.77, [Z, B], 2.8, rot=-2, rot1=2)
follow(8.78, 9.69, [B, Z], 1.6, z1=1.4)
follow(9.7, 10.23, [A, Z], 2.4, rot=-4)
cut(10.24, (-75, -128, 3.0, -5), 11.44, (-75, -128, 3.5, 5))
cut(11.45, (-74, -122, 2.4), 11.99, (-74, -120, 1.6))
follow(12.0, 12.89, [Z, B], 1.5, z1=1.7)
cut(12.9, (-40, -150, 2.0, -6), 13.31, (-62, -390, 1.6, -3))
cut(13.32, (-72, -480, 2.6, 6), 13.62, (-60, -300, 1.5))
cut(13.64, (-56, -95, 1.15), 14.49, (-56, -110, 1.35))
cut(14.5, (-56, -60, 2.5, 8), 15.19, (-56, -70, 2.9, 6))
close(15.2, Z, 'fhand', 5.5, 15.9, 6.2)
cut(15.91, (-40, -70, 1.6, -4), 16.39, (-40, -80, 1.8, -2))
follow(16.4, 17.09, [Z], 2.6, dy=-40)
close(17.1, Z, 'head', 5.5, 17.69, 6.3)
cut(17.7, (-56, -150, 1.35), 18.59, (-56, -160, 1.15))
close(18.6, Z, 'fhand', 5.0, 19.54, 5.8, dy=-20)
cut(19.55, (-150, -120, 1.3), 19.7, (-262, -120, 1.45))
cut(19.72, (-288, -120, 2.4, -4), 20.14, (-280, -120, 2.6, -2))
follow(20.15, 20.81, [Z, B], 2.6, rot=4, rot1=-2)
follow(20.82, 21.14, [Z, B], 1.6)
cut(21.15, (-232, -420, 2.0, -5), 21.96, (-222, -450, 2.4, 5))
cut(21.98, (-180, -110, 1.35), 22.0, (-180, -110, 1.35))
follow(22.01, 22.95, [Z, A], 2.6, rot=-3, rot1=2)
cut(22.97, (-140, -120, 1.3), 23.49, (-140, -120, 1.3))
cut(23.5, (-150, -110, 1.25), 23.89, (-150, -110, 1.3))
close(23.9, Z, 'head', 3.0, 24.6, 3.5, dy=40, rot=-6)
cut(24.62, (-140, -110, 1.25), 24.86, (-140, -110, 1.3))
cut(24.9, (40, -120, 2.2, 5), 25.89, (30, -120, 2.4, 3))
cut(25.9, (-130, -120, 1.15), 26.77, (-125, -125, 1.2))
close(26.78, Z, 'fhand', 4.5, 26.84, 4.6)
cut(26.85, (-130, -130, 1.1), 27.99, (-110, -150, 1.0))
cut(28.0, (-60, -200, 0.95), 31.6, (-60, -280, 0.8))

# ================================================================= finalize timing
ANIM_END = 31.6
FXR = [FX(kind, WARP.R(ta), d, layer, **kw) for ta, kind, d, layer, kw in _FX]
POSTR = [(kind, WARP.R(ta), d, amt) for kind, ta, d, amt in POST]
for kind, tr, d, amt in POSTR:
    if kind == 'shake': CAM.shake(tr, amt, d)
TEXTR = [(e[0], WARP.R(e[1]), e[2]) + tuple(e[3:]) for e in TEXT]
FIGHTERS = {'hero': HERO, 'oni': ONI, 'kage': KAGE}

# ================================================================= background
_cache = {}
def sky():
    if 'sky' in _cache: return _cache['sky']
    w, h = int(W*SS*1.3), int(H*SS*1.5)
    y = np.linspace(0, 1, h)[:, None]
    stops = [(0, (8, 8, 30)), (0.2, (24, 16, 56)), (0.34, (70, 30, 92)), (0.43, (190, 74, 98)), (0.5, (255, 148, 108)), (1, (255, 182, 132))]
    img = np.zeros((h, w, 3))
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        m = ((y >= a) & (y <= b)).astype(float); s = np.clip((y-a)/(b-a), 0, 1)
        for c in range(3): img[:, :, c] += m[:, 0:1] * (ca[c] + (cb[c]-ca[c])*s)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA')
    d = ImageDraw.Draw(im); r = random.Random(3)
    for i in range(260):
        x, yy = r.uniform(0, w), r.uniform(0, h*0.45); s = r.uniform(0.6, 2.2)*SS
        d.ellipse([x-s/2, yy-s/2, x+s/2, yy+s/2], fill=(255, 245, 255, int(r.uniform(80, 230)*(1-yy/(h*0.45)))))
    # moon + glow
    mx, my, mr = w*0.66, h*0.27, 140*SS
    glow = Image.new('RGBA', im.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    for i in range(14, 0, -1):
        rr = mr*(1 + i*0.22); gd.ellipse([mx-rr, my-rr, mx+rr, my+rr], fill=(255, 210, 190, int(14 + 2*(14-i))))
    glow = glow.filter(ImageFilter.GaussianBlur(30*SS)); im.alpha_composite(glow)
    d = ImageDraw.Draw(im)
    d.ellipse([mx-mr, my-mr, mx+mr, my+mr], fill=(255, 238, 222))
    for cx, cy, cr in ((-40, -30, 28), (35, 40, 22), (60, -55, 14), (-55, 60, 16)):
        d.ellipse([mx+cx*SS-cr*SS, my+cy*SS-cr*SS, mx+cx*SS+cr*SS, my+cy*SS+cr*SS], fill=(246, 222, 210))
    # cloud streaks
    cl = Image.new('RGBA', im.size, (0, 0, 0, 0)); cd = ImageDraw.Draw(cl)
    for i in range(16):
        cx, cy = r.uniform(0, w), r.uniform(h*0.25, h*0.62); cw, ch = r.uniform(200, 600)*SS, r.uniform(10, 26)*SS
        cd.ellipse([cx-cw, cy-ch, cx+cw, cy+ch], fill=(60, 30, 80, 120) if cy < h*0.45 else (255, 140, 120, 70))
    cl = cl.filter(ImageFilter.GaussianBlur(8*SS)); im.alpha_composite(cl)
    _cache['sky'] = im
    return im

def ridge(seed, n, span, hmin, hmax, jag):
    r = random.Random(seed); pts = []; x = -span
    while x < span:
        pts.append((x, -r.uniform(hmin, hmax))); x += r.uniform(*jag)
    return pts
LAYERS = [(0.10, ridge(1, 0, 3500, 120, 420, (60, 180)), (58, 30, 86)),
          (0.28, ridge(2, 0, 3200, 60, 230, (40, 120)), (36, 18, 60)),
          (0.55, ridge(3, 0, 3000, 20, 120, (20, 70)), (22, 12, 40))]
SPIRES = [(random.Random(i).uniform(-2500, 2500), random.Random(i+50).uniform(140, 300)) for i in range(14)]
STONES = [(random.Random(i*3).uniform(-2500, 2500), random.Random(i*3+1).uniform(-18, 260), random.Random(i*3+2).uniform(4, 16)) for i in range(160)]

def draw_world(base, v):
    s = sky(); sw, sh = s.size
    ox = int(sw/2 - W*SS/2 - v.cx*0.02*SS); oy = int(sh*0.30 - H*SS*0.30 + v.cy*0.06*SS)
    ox = max(0, min(sw - W*SS, ox)); oy = max(0, min(sh - H*SS, oy))
    base.paste(s.crop((ox, oy, ox + W*SS, oy + H*SS)), (0, 0))
    d = ImageDraw.Draw(base)
    for p, pts, col in LAYERS:
        poly = [v.ws(x, y - 30, p) for x, y in pts]
        poly = [(poly[0][0], H*SS*3), *poly, (poly[-1][0], H*SS*3)]
        d.polygon(poly, fill=col)
        if p == 0.55:
            for x, hh in SPIRES:
                b0, b1, tp = v.ws(x-16, -20, p), v.ws(x+16, -20, p), v.ws(x+3, -20-hh, p)
                d.polygon([b0, (b0[0]+(tp[0]-b0[0])*0.6-4*SS, b0[1]+(tp[1]-b0[1])*0.6), tp, b1], fill=col)
    # ground plateau
    gx0, gx1 = v.cx - 3000, v.cx + 3000
    bands = [(-26, (28, 16, 38)), (0, (22, 12, 32)), (60, (16, 9, 25)), (180, (10, 6, 17)), (400, (6, 4, 11))]
    for (y0, c0), (y1, _) in zip(bands, bands[1:] + [(3000, None)]):
        d.polygon([v.ws(gx0, y0), v.ws(gx1, y0), v.ws(gx1, y1), v.ws(gx0, y1)], fill=c0)
    a, b = v.ws(gx0, -26), v.ws(gx1, -26)
    d.line([a, b], fill=(255, 150, 120), width=max(1, int(2.2*v.k)))
    for x, y, s_ in STONES:
        if abs(x - v.cx) > 900/v.z: continue
        p = v.ws(x, y); r = s_*v.k*(0.6 + y/400)
        d.polygon([(p[0]-r, p[1]), (p[0]-r*0.3, p[1]-r*0.7), (p[0]+r*0.6, p[1]-r*0.5), (p[0]+r, p[1])], fill=(34, 20, 46))
        d.line([(p[0]-r*0.3, p[1]-r*0.7), (p[0]+r*0.6, p[1]-r*0.5)], fill=(120, 70, 100), width=max(1, int(v.k)))

EMBERS = [(random.Random(i).random(), random.Random(i+99).random(), random.Random(i+7).uniform(0.4, 1.0)) for i in range(38)]
def draw_embers(L, v, tr):
    for x0, y0, dpt in EMBERS:
        x = ((x0*W*1.4 + tr*40*dpt - v.cx*v.z*dpt*0.6) % (W*1.4) - W*0.2) * SS
        y = ((y0*H - tr*55*dpt + v.cy*v.z*dpt*0.3) % H) * SS
        x += math.sin(tr*2 + x0*30)*12*SS
        r = (0.8 + 1.4*dpt)*SS
        dot(L['front'], (x, y), r, (255, 220, 180, int(160*dpt)))
        dot(L['glow'], (x, y), r*2.5, (int(90*dpt), int(45*dpt), int(25*dpt)))

_vig = {}
def vignette():
    if 'v' not in _vig:
        y, x = np.mgrid[0:H, 0:W]; d = np.sqrt(((x-W/2)/(W*0.75))**2 + ((y-H*0.52)/(H*0.62))**2)
        _vig['v'] = np.clip(1.15 - d*0.65, 0.35, 1.0)[:, :, None]
    return _vig['v']

# ================================================================= text
def draw_text(img, tr):
    d = ImageDraw.Draw(img, 'RGBA')
    for e in TEXTR:
        kind, t0, dur = e[:3]; age = tr - t0
        if not 0 <= age < dur: continue
        u = age/dur; a = clamp(age/0.15) * clamp((dur-age)/0.3)
        if kind in ('title', 'fin'):
            txt = 'ONE  vs  TWO' if kind == 'title' else 'F I N'
            sz = 92 if kind == 'title' else 80
            f = font(sz); sc = 1.0 + 0.06*(1-u)
            tw = d.textlength(txt, font=f); x, y = W/2 - tw/2, H*0.22
            gl = Image.new('RGBA', img.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
            gd.text((x, y), txt, font=f, fill=(63, 227, 255, int(220*a)))
            gl = gl.filter(ImageFilter.GaussianBlur(14)); img.alpha_composite(gl)
            d = ImageDraw.Draw(img, 'RGBA')
            d.text((x+4, y+4), txt, font=f, fill=(0, 0, 0, int(160*a)))
            d.text((x, y), txt, font=f, fill=(255, 255, 255, int(255*a)))
            if kind == 'title':
                sub = 'A  ONE-SWORD  DUEL'; fs = font(26); sw = d.textlength(sub, font=fs)
                d.text((W/2 - sw/2, y + 118), sub, font=fs, fill=(255, 210, 190, int(230*a)))
        elif kind == 'card':
            name, lk = e[3], e[4]
            slide = EASE['snap'](clamp(age/0.25)); out = EASE['in'](clamp((age - dur + 0.25)/0.25))
            y = H*0.70 if lk['kind'] != 'hero' else H*0.18
            off = (1 - slide)*W - out*W
            if lk['kind'] == 'shade': off = -off
            band = [(off - 40, y), (off + W + 40, y - 60), (off + W + 40, y + 40), (off - 40, y + 100)]
            d.polygon(band, fill=hexc(lk['acc']) + (int(225*a),))
            d.polygon([(off - 40, y + 86), (off + W + 40, y + 26), (off + W + 40, y + 40), (off - 40, y + 100)], fill=(255, 255, 255, int(200*a)))
            f = font(64); tw = d.textlength(name, font=f)
            d.text((W/2 - tw/2 + off + 3, y - 16 + 3), name, font=f, fill=(0, 0, 0, int(170*a)))
            d.text((W/2 - tw/2 + off, y - 16), name, font=f, fill=(255, 255, 255, int(255*a)))
    return img

# ================================================================= frame
def frame(fi):
    tr = fi / FPS
    ta = min(WARP.A(tr), ANIM_END)
    v = View(CAM.at(ta, tr))
    HERO.look['eyeglow'] = ta >= 17.3
    base = Image.new('RGBA', (W*SS, H*SS)); draw_world(base, v)
    back = Image.new('RGBA', base.size, (0, 0, 0, 0)); front = Image.new('RGBA', base.size, (0, 0, 0, 0))
    glow = Image.new('RGB', base.size, (0, 0, 0))
    L = dict(back=ImageDraw.Draw(back), front=ImageDraw.Draw(front), glow=ImageDraw.Draw(glow))
    for kind, t0, dd, amt in POSTR:   # darken background for dramatic beats
        if kind == 'dark' and 0 <= tr - t0 < dd:
            a = amt * clamp((tr - t0)/0.08) * clamp((dd - (tr - t0))/0.15)
            base = Image.blend(base, Image.new('RGBA', base.size, (6, 4, 14, 255)), a)
    states = {n: F.anim(ta) for n, F in FIGHTERS.items()}
    prev = {n: F.anim(ta - 0.04) for n, F in FIGHTERS.items()}
    for n, st in states.items():   # contact shadows
        c = v.ws(st['x'], 2); s = max(0.2, 1 - st['alt']/500)
        rx, ry = 46*v.k*s, 9*v.k*s
        L['back'].ellipse([c[0]-rx, c[1]-ry, c[0]+rx, c[1]+ry], fill=(0, 0, 0, int(120*s)))
    for e in FXR:
        age = tr - e.tr
        if 0 <= age < e.d:
            if e.kind == 'aura':
                e.kw['fighter'] = FIGHTERS[e.kw['fighter']] if isinstance(e.kw['fighter'], str) else e.kw['fighter']
                e.kw['state'] = e.kw['fighter'].anim(ta)
            draw_fx(e, age, L, v, fi)
    vels = {}
    for n, F in FIGHTERS.items():
        st, pv = states[n], prev[n]
        vel = ((st['x'] - pv['x'])/0.04, -(st['alt'] - pv['alt'])/0.04); vels[n] = vel
        sp = math.hypot(*vel)
        if sp > 700:   # coloured afterimages on dashes
            acc = hexc(F.look['acc'])
            for j in (3, 2):
                gs = F.anim(ta - j*0.03)
                draw_parts(L['back'], L['glow'], fighter_parts(F, gs, v, ta, vel),
                           ghost=mix(acc, (255, 255, 255), 0.3) + (int(min(1, sp/1500)*(110 - j*25)),))
        # motion-blur smear: sub-frame copies when limbs move fast
        Wn, _ = F.world(st); Wp, _ = F.world(F.anim(ta - 1/30))
        rel = lambda Wd, j: (Wd[j][0] - Wd['hip'][0], Wd[j][1] - Wd['hip'][1])
        disp = max(math.dist(rel(Wn, j), rel(Wp, j)) for j in ('fhand', 'rhand', 'ftoe', 'rtoe', 'head')) * v.k
        if sp > 700: disp = 0
        if disp > 14*SS:
            col = shade(hexc(F.look['top']), 0.9)
            for j, a in ((3, 45), (2, 70), (1, 95)):
                gs = F.anim(ta - j/90)
                draw_parts(L['back'], L['glow'], fighter_parts(F, gs, v, ta, vel),
                           ghost=col + (int(a*min(1, disp/(40*SS))),))
    base.alpha_composite(back)
    d = ImageDraw.Draw(base)
    for n in ('oni', 'kage', 'hero'):
        draw_parts(d, L['glow'], fighter_parts(FIGHTERS[n], states[n], v, ta, vels[n]))
    blade_trail(HERO, v, ta, L)
    draw_embers(L, v, tr)
    base.alpha_composite(front)
    img = base.convert('RGB').reduce(SS); g = glow.reduce(SS)
    arr = np.asarray(img, dtype=np.float32)
    ga = np.asarray(g, dtype=np.float32)
    arr += ga*0.55 + np.asarray(g.filter(ImageFilter.GaussianBlur(4)), np.float32)*0.9 \
               + np.asarray(g.filter(ImageFilter.GaussianBlur(16)), np.float32)*1.3
    arr *= vignette()
    for kind, t0, dd, amt in POSTR:
        age = tr - t0
        if not 0 <= age < dd: continue
        u = age/dd
        if kind == 'flash': arr += (255 - arr) * (1-u)**2
        elif kind == 'chroma':
            s = int(amt*(1-u)**2)
            if s: arr[:, :, 0] = np.roll(arr[:, :, 0], s, 1); arr[:, :, 2] = np.roll(arr[:, :, 2], -s, 1)
    for kind, t0, dd, amt in POSTR:
        if kind == 'iframe' and 0 <= tr - t0 < dd:
            lum = arr.clip(0, 255) @ np.array([0.3, 0.59, 0.11], np.float32)
            m = lum > np.percentile(lum, 78)
            if int((tr - t0)*FPS) % 2: m = ~m
            arr = np.where(m[:, :, None], np.array([250, 244, 236], np.float32), np.array([14, 8, 24], np.float32))
    rng = np.random.default_rng(fi)
    arr += rng.normal(0, 3.5, (H, W, 1)).astype(np.float32)
    for kind, t0, dd, amt in POSTR:
        if kind == 'fade' and tr >= t0: arr *= 1 - clamp((tr - t0)/dd)
    if tr < 0.6: arr *= tr/0.6
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert('RGBA')
    img = draw_text(img, tr)
    return img.convert('RGB')

def _bytes(fi): return frame(fi).tobytes()

def main():
    cmd = sys.argv[1]
    if cmd == 'still':
        out = sys.argv[2]; os.makedirs(out, exist_ok=True)
        for s in sys.argv[3:]:
            frame(int(round(float(s)*FPS))).save(os.path.join(out, f'f_{s}.png'))
        return
    if cmd == 'video':
        out = sys.argv[2]
        t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
        t1 = float(sys.argv[4]) if len(sys.argv) > 4 else DUR
        import audio
        wav = os.path.splitext(out)[0] + '.wav'
        audio.write(wav, CUES, WARP, DUR, t0, t1)
        from multiprocessing import Pool
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                               '-r', str(FPS), '-i', '-', '-i', wav, '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
                               '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out],
                              stdin=subprocess.PIPE)
        frames = range(int(t0*FPS), int(t1*FPS))
        with Pool(os.cpu_count()) as pool:
            for i, b in enumerate(pool.imap(_bytes, frames, chunksize=2)):
                ff.stdin.write(b)
                if i % 60 == 0: print(f'frame {i}/{len(frames)}', flush=True)
        ff.stdin.close(); sys.exit(ff.wait())

if __name__ == '__main__':
    print(f'real duration of animation: {WARP.R(ANIM_END):.2f}s (DUR={DUR})', file=sys.stderr)
    main()
