"""ONE vs TWO — original anime-style fight: one swordsman against two attackers.

Usage:
  python render.py still OUTDIR t1 t2 ...      # preview PNGs (real seconds)
  python render.py video OUT.mp4 [start end]  # render (start/end in real seconds)
"""
import math, os, sys, random, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from engine import *

DUR = 34.0

LOOK_H = dict(kind='hero', top='#eef1fb', pants='#25304d', skin='#f4dac8', hair='#171a33',
              hair_hl='#5fe9ff', acc='#3fe3ff', eye='#7ff7ff')
LOOK_A = dict(kind='oni', top='#c0263a', pants='#1c0e15', skin='#2a0c14', hair='#efe3d0',
              acc='#ff5a36', eye='#ffd23a')
LOOK_B = dict(kind='shade', top='#6a3fa6', pants='#160e25', skin='#e9d2c8', hair='#2e1a52',
              acc='#c77dff', eye='#ff6fe0')

HERO, ONI, KAGE = Fighter('hero', LOOK_H), Fighter('oni', LOOK_A), Fighter('kage', LOOK_B)
HERO.sheath_from = 0.0; HERO.glow_from = 17.8
CAM, WARP = Camera(), Warp()
_FX, CUES, POST, TEXT = [], [], [], []   # anim-timed; converted after the warp is final

def fx(kind, ta, d, layer='front', **kw): _FX.append((ta, kind, d, layer, kw))
def sfx(ta, name, vol=1.0): CUES.append((ta, name, vol))
def post(kind, ta, d, amt=1.0): POST.append((kind, ta, d, amt))
def at(F, ta, joint):
    Wd, _ = F.world(F.state(ta)); return Wd[joint]

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
# --- S0 intro / S1 enemies drop in
Z.key(0, 'stand', x=0, face=1).key(2.4, 'stand', ease='io').key(3.1, 'look', ease='io')
A.key(0, 'dive', x=-215, alt=2400, face=1).key(3.5, 'dive', alt=1500, ease='lin') \
 .key(3.95, 'land', alt=0, ease='in').key(4.7, 'guard', ease='io')
B.key(0, 'dive', x=215, alt=2400, face=-1).key(4.3, 'dive', alt=1500, ease='lin') \
 .key(4.75, 'land', alt=0, ease='in').key(5.5, 'guard', ease='io')
ground_hit(3.95, -215); ground_hit(4.75, 215)
sfx(3.55, 'fall', 0.6); sfx(4.35, 'fall', 0.6)
Z.key(4.1, 'look', face=-1, ease='snap').key(4.9, 'look', face=1, ease='snap').key(5.9, 'guard', ease='out')
TEXT += [('title', 0.7, 2.6), ('card', 4.0, 1.25, 'AKA ONI', LOOK_A), ('card', 4.85, 1.25, 'KAGE', LOOK_B),
         ('card', 6.05, 0.75, 'KAZE', LOOK_H)]
fx('glint', 6.35, 0.35, x=8, y=-140, col='#7ff7ff', size=34); sfx(6.35, 'shing', 0.5)

# --- S3 Aka Oni rushes from behind
A.key(6.75, 'guard', x=-215).key(7.05, 'dash', x=-120, ease='in').key(7.18, 'cross', x=-66, ease='out')
Z.key(6.95, 'guard', face=-1, ease='snap').key(7.15, 'block', ease='snap')
sfx(6.9, 'whoosh', 0.6)
hit(7.18, at(A, 7.18, 'rhand'), big=False, col=LOOK_A['acc'], stop=0.05)
Z.key(7.3, 'guard2').key(7.42, 'elbow', x=-12, ease='snap')
A.key(7.3, 'cross').key(7.45, 'hurt', x=-92, ease='snap').key(7.9, 'hurt', x=-170, ease='out').key(8.4, 'guard', x=-195, ease='io')
hit(7.42, at(Z, 7.42, 'fel'), col=LOOK_H['acc'], stop=0.08, shake=10)
Z.key(7.75, 'guard', ease='io')

# --- S4 Kage jump-kicks; up-kick, aerial spin kick, slam
B.key(7.9, 'guard', x=215).key(8.08, 'crouch', x=200, ease='io').key(8.62, 'airkick', x=6, alt=95, arc=70, ease='lin')
sfx(8.1, 'whoosh', 0.7)
Z.key(8.25, 'guard').key(8.36, 'crouch', ease='snap').key(8.5, 'crouch').key(8.62, 'upkick', face=1, ease='snap')
hit(8.62, at(Z, 8.62, 'ftoe'), col=LOOK_H['acc'], stop=0.1, shake=12, iframe=True)
B.key(8.66, 'flyback', alt=110, rot=-30, ease='snap').key(9.15, 'flyback', x=60, alt=380, rot=-200, ease='out')
Z.key(8.8, 'upkick').key(8.92, 'crouch', ease='io').key(9.12, 'tuck', x=-30, alt=320, ease='out') \
 .key(9.22, 'tuck', alt=350, rot=200, ease='lin').key(9.3, 'airkick', alt=372, rot=360, ease='out')
sfx(8.95, 'whoosh', 0.8); sfx(9.15, 'whoosh', 0.9)
WARP.slow(8.98, 0.32, 0.35)
B.key(9.3, 'flyback', x=60, alt=380, rot=-205)
hit(9.3, at(Z, 9.3, 'ftoe'), col=LOOK_H['acc'], stop=0.12, shake=16, iframe=True, size=1.3)
B.key(9.34, 'flyback', rot=-250, ease='snap').key(9.58, 'lying', x=210, alt=0, rot=-90, ease='in') \
 .key(9.74, 'lying', alt=26, rot=-80, ease='out').key(9.9, 'lying', alt=0, rot=-90, ease='in') \
 .hold(11.2).key(11.6, 'kneel', rot=0, ease='io').key(12.2, 'guard', x=195, ease='io')
ground_hit(9.58, 210, 1.3); WARP.stop(9.58, 0.06)
Z.key(9.45, 'airkick', alt=330, ease='out').key(9.82, 'land', x=40, alt=0, ease='in').key(10.15, 'guard', ease='io')
fx('dust', 9.82, 0.8, layer='back', x=40, n=10, size=0.7); sfx(9.82, 'land', 0.7)

# --- S5 flurry with Aka Oni
A.key(10.2, 'guard', x=-195).key(10.45, 'dash', x=-115, ease='in').key(10.56, 'jab', x=-80, ease='out')
Z.key(10.3, 'guard', face=-1, ease='snap').key(10.48, 'dash', x=5, ease='in').key(10.58, 'block', x=-6)
sfx(10.35, 'whoosh', 0.7)
fx('speedlines', 10.56, 1.45, focus=(-40, -120))
t = 10.62
for i in range(9):
    atk, dfn = (A, Z) if i % 2 == 0 else (Z, A)
    pose = ('jab', 'cross')[(i//2) % 2]
    atk.key(t, pose, ease='snap'); dfn.key(t, 'block', ease='snap')
    hand = 'fhand' if pose == 'jab' else 'rhand'
    hit(t, at(atk, t, hand), big=False, col=(LOOK_A if atk is A else LOOK_H)['acc'], shake=4)
    atk.key(t + 0.09, 'guard', ease='io'); dfn.key(t + 0.09, 'guard', ease='io')
    t += 0.15
Z.key(11.95, 'chamber', ease='snap').key(12.05, 'kick', ease='snap')
hit(12.05, at(Z, 12.05, 'ftoe'), col=LOOK_H['acc'], stop=0.1, shake=14, iframe=True)
A.key(12.05, 'guard').key(12.09, 'flyback', alt=20, ease='snap').key(12.5, 'flyback', x=-300, alt=40, arc=50, rot=-40, ease='lin') \
 .key(12.7, 'land', x=-325, alt=0, rot=0, ease='in').key(13.0, 'guard', x=-300, ease='io')
fx('dust', 12.62, 0.9, layer='back', x=-320, n=12, dir=-1); sfx(12.65, 'land', 0.6)

# --- S6 both attack at once
A.key(13.0, 'guard', x=-300).key(13.15, 'dash', x=-160, ease='in').key(13.25, 'cross', x=-96, ease='out')
B.key(12.95, 'guard', x=195).key(13.12, 'crouch', x=175, ease='io').key(13.25, 'kick', x=66, ease='snap')
Z.key(12.4, 'guard', ease='io').key(13.05, 'guard', x=-15, face=1, ease='out').key(13.24, 'horse', ease='snap')
sfx(13.1, 'whoosh', 0.8)
hit(13.25, at(A, 13.25, 'rhand'), big=False, col=LOOK_A['acc'], size=1.8)
hit(13.25, at(B, 13.25, 'ftoe'), big=False, col=LOOK_B['acc'], size=1.8, stop=0.32, shake=8, iframe=True)
post('chroma', 13.25, 0.5, 7)
Z.key(13.45, 'horse').key(13.58, 'push', ease='snap').key(14.1, 'guard', ease='io')
A.key(13.45, 'cross').key(13.58, 'hurt', x=-125, ease='snap').key(14.05, 'guard', x=-240, ease='out')
B.key(13.45, 'kick').key(13.58, 'hurt', x=95, ease='snap').key(14.05, 'guard', x=170, ease='out')
fx('ring', 13.58, 0.6, layer='back', x=-15, r=420, col=LOOK_H['acc']); fx('impact', 13.58, 0.4, x=-15, y=-110, col=LOOK_H['acc'], size=0.8)
post('shake', 13.58, 0.4, 10); sfx(13.58, 'boom', 0.8)

# --- S7 coordinated: sweep low, kick high -> Kaze is knocked away
A.key(14.35, 'guard', x=-240).key(14.6, 'dash', x=-130, ease='in').key(14.78, 'sweep', x=-62, ease='out') \
 .key(15.1, 'crouch', x=-62, ease='io').key(15.6, 'guard', ease='io')
Z.key(14.5, 'guard', x=-15).key(14.66, 'crouch', ease='snap').key(14.86, 'tuck', alt=110, ease='out')
B.key(14.45, 'guard', x=170).key(14.6, 'crouch', x=160, ease='io').key(14.94, 'airkick', x=30, alt=115, arc=40, ease='lin')
sfx(14.62, 'whoosh', 0.7); sfx(14.75, 'whoosh', 0.8)
Z.key(14.94, 'tuck', alt=118, ease='lin')
hit(14.94, at(B, 14.94, 'ftoe'), col=LOOK_B['acc'], stop=0.16, shake=24, iframe=True, size=1.4)
post('chroma', 14.94, 0.6, 9)
Z.key(14.98, 'flyback', alt=128, ease='snap').key(15.4, 'flyback', x=-340, alt=10, arc=50, rot=-50, ease='lin') \
 .key(15.5, 'hurt', x=-365, alt=0, rot=0, ease='out').key(15.95, 'kneel', x=-400, ease='out')
fx('dust', 15.42, 1.0, layer='back', x=-360, n=18, dir=-1, spread=0.6); sfx(15.45, 'skid', 0.8)
B.key(15.2, 'land', x=-5, alt=0, ease='in').key(15.6, 'guard', x=-5, ease='io')

# --- S8 the approach, power awakening
A.key(16.0, 'guard', x=-62).key(17.6, 'guard2', x=-200, ease='io').key(18.15, 'guard', x=-205)
B.key(16.0, 'guard', x=-5).key(17.6, 'guard2', x=-110, ease='io').key(18.15, 'guard', x=-112)
for tt in (16.3, 16.9, 17.5): sfx(tt, 'heart', 0.9)
Z.hold(17.45)
fx('glint', 17.35, 0.35, x=-392, y=-128, col='#7ff7ff', size=40); sfx(17.35, 'shing', 0.4)
Z.key(18.0, 'power', ease='io')
fx('aura', 17.8, 7.1, layer='front', fighter='hero', col=LOOK_H['acc']); sfx(17.6, 'rumble', 0.9)
fx('crack', 17.95, 7.0, layer='back', x=-400, n=11, hot=True, col=LOOK_H['acc'])
fx('ring', 18.15, 0.7, layer='back', x=-400, r=520, col=LOOK_H['acc'])
fx('impact', 18.15, 0.5, x=-400, y=-100, col=LOOK_H['acc'], size=1.5)
post('flash', 18.15, 0.35); post('shake', 18.15, 0.8, 20); post('iframe', 18.15, 0.07); WARP.stop(18.15, 0.1)
sfx(18.15, 'boom', 1.0)
A.key(18.3, 'hurt', x=-185, ease='snap').key(18.8, 'guard', x=-190, ease='io')
B.key(18.3, 'hurt', x=-95, ease='snap').key(18.8, 'guard', x=-98, ease='io')
Z.key(18.7, 'iai', ease='io').hold(19.5)
fx('glint', 19.25, 0.3, x=-414, y=-58, col='#ffffff', size=26); sfx(19.2, 'shing', 0.35)

# --- S10 flash step draw-cut through Aka Oni, parry & cut Kage
Z.key(19.58, 'swback', x=-330, sw=-150, ease='in').key(19.68, 'swfwd', x=-150, ease='snap')
fx('speedlines', 19.56, 0.25, mode='horiz'); sfx(19.58, 'shing', 0.9)
hit(19.66, (-195, -105), col=LOOK_H['acc'], stop=0.12, shake=14, iframe=True,
    slash=dict(r=95, a0=200, a1=340, w=30, squash=0.45), sound='cut')
A.key(19.66, 'guard', x=-192).key(19.7, 'hurt', x=-215, ease='snap').key(20.3, 'hurt', x=-240).key(20.7, 'kneel', x=-250, face=1, ease='io')
B.key(19.9, 'guard', x=-98).key(20.05, 'cross', x=-92, ease='snap')
Z.key(19.9, 'swguard', x=-150, ease='io').key(20.04, 'swguard', ease='snap')
sfx(19.95, 'whoosh', 0.6)
hit(20.05, at(B, 20.05, 'rhand'), big=False, col='#ffffff', stop=0.05, sound='clang', size=1.3)
Z.key(20.18, 'swup', ease='snap').key(20.28, 'swdown', ease='snap')
hit(20.28, (-100, -115), col=LOOK_H['acc'], stop=0.1, shake=12, slash=dict(r=110, a0=-110, a1=60, w=32, squash=0.9), sound='cut')
B.key(20.28, 'cross').key(20.32, 'flyback', alt=30, ease='snap').key(20.8, 'flyback', x=40, alt=60, arc=70, rot=-50, ease='lin') \
 .key(21.0, 'land', x=60, alt=0, rot=0, ease='in').key(21.3, 'crouch', x=60, ease='io')
fx('dust', 20.98, 0.8, layer='back', x=60, n=10); sfx(21.0, 'land', 0.6)
Z.key(20.6, 'swguard', x=-140, ease='io')

# --- S11 both leap for a dual dive; mid-air triple cut in slow motion
A.key(21.2, 'crouch', x=-250, face=1, ease='io').key(21.9, 'tuck', x=-215, alt=470, ease='out').key(22.18, 'dive', x=-160, alt=395, ease='in')
B.key(21.3, 'crouch', x=60).key(21.9, 'tuck', x=20, alt=470, ease='out').key(22.46, 'dive', x=-48, alt=392, ease='in')
sfx(21.45, 'whoosh', 0.8)
Z.key(21.3, 'swguard', x=-100, ease='io').key(21.75, 'crouch', sw=150, ease='io') \
 .key(22.12, 'tuck', alt=380, sw=200, face=-1, ease='out').key(22.2, 'swdown', alt=390, ease='snap') \
 .key(22.26, 'swfwd', alt=392, ease='io').key(22.36, 'swfwd', alt=394, rot=360, ease='lin') \
 .key(22.42, 'swup', alt=394, rot=360, face=1, ease='snap').key(22.48, 'swdown', alt=392, ease='snap')
sfx(21.95, 'whoosh', 0.9)
WARP.slow(22.05, 0.7, 0.3)
fx('speedlines', 22.12, 0.5, focus=(-100, -440))
hit(22.2, at(A, 22.2, 'chest'), col=LOOK_H['acc'], stop=0.08, shake=12, iframe=True,
    slash=dict(r=100, a0=-80, a1=110, w=30), sound='cut')
fx('slash', 22.3, 0.35, x=-100, y=-440, r=120, a0=0, a1=340, w=24, col=LOOK_H['acc']); sfx(22.29, 'shing', 0.7)
hit(22.48, at(B, 22.48, 'chest'), col=LOOK_H['acc'], stop=0.1, shake=14, iframe=True,
    slash=dict(r=105, a0=250, a1=60, w=32), sound='cut')
A.key(22.24, 'flyback', x=-170, alt=395, ease='snap').key(22.8, 'flyback', x=-330, alt=0, rot=-70, ease='in') \
 .key(22.9, 'lying', rot=-90, ease='out').hold(23.9).key(24.45, 'kneel', rot=0, face=1, ease='io').hold(24.72) \
 .key(24.8, 'hurt', ease='snap').key(25.25, 'facedown', rot=90, ease='in')
B.key(22.52, 'flyback', x=-30, alt=390, ease='snap').key(23.05, 'flyback', x=150, alt=0, rot=-70, ease='in') \
 .key(23.15, 'lying', rot=-90, ease='out').hold(23.9).key(24.45, 'kneel', rot=0, face=-1, ease='io').hold(24.72) \
 .key(24.8, 'hurt', ease='snap').key(25.3, 'facedown', rot=90, ease='in')
ground_hit(22.8, -330); ground_hit(23.05, 150)
Z.key(22.6, 'swdown', alt=360).key(23.2, 'swlow', x=-100, alt=0, rot=0, ease='in')
fx('ring', 23.2, 0.6, layer='back', x=-100, r=260, col=LOOK_H['acc']); fx('dust', 23.2, 0.9, layer='back', x=-100, n=14)
sfx(23.2, 'land', 0.9); post('shake', 23.2, 0.4, 8)

# --- S12 the sheathe; delayed cuts land
Z.hold(23.85).key(24.1, 'swguard', ease='io').key(24.2, 'swfwd', ease='snap').key(24.68, 'iai', ease='io')
sfx(24.2, 'whoosh', 0.5); sfx(24.7, 'chin', 1.0)
WARP.stop(24.7, 0.45)
for F, x in ((A, -330), (B, 150)):
    fx('slash', 24.74, 0.45, x=x, y=-80, r=110, a0=200, a1=330, w=34, col=LOOK_H['acc'])
    fx('slash', 24.78, 0.45, x=x, y=-80, r=110, a0=-30, a1=110, w=34, col=LOOK_H['acc'])
    fx('impact', 24.78, 0.5, x=x, y=-80, col=LOOK_H['acc'], size=1.4)
post('flash', 24.76, 0.5); post('iframe', 24.76, 0.1); post('shake', 24.76, 0.8, 22); post('chroma', 24.76, 0.6, 9)
sfx(24.76, 'cut', 1.0); sfx(24.8, 'boom', 1.0)
ground_hit(25.25, -330, 0.6); ground_hit(25.3, 150, 0.6)
Z.hold(25.2).key(26.1, 'stand', ease='io')

# --- S13 outro
TEXT += [('fin', 27.2, 3.0)]
post('fade', 28.6, 1.0)

# ================================================================= camera
for k in [(0, 0, -170, 0.85), (2.9, 0, -130, 1.5, 'io'), (3.45, 0, -280, 0.72, 'out'), (4.95, 0, -140, 1.0),
          (5.5, 0, -140, 1.25), (5.62, 4, -138, 3.3, 'snap'), (6.7, 4, -138, 3.5), (6.8, -40, -110, 1.9, 'snap'),
          (7.8, -60, -110, 2.0), (8.15, 0, -150, 1.45), (8.62, 0, -190, 1.7), (9.25, 30, -420, 1.45),
          (9.62, 110, -150, 1.25), (10.2, 40, -115, 1.55), (10.6, -40, -118, 2.4, 'snap'), (11.9, -40, -118, 2.7, 'lin'),
          (12.3, -150, -110, 1.6), (12.9, -50, -110, 1.25), (13.25, -15, -118, 2.0, 'snap'), (13.65, -15, -110, 1.35),
          (14.4, -40, -125, 1.3), (14.95, -40, -210, 1.75, 'out'), (15.5, -260, -125, 1.35),
          (16.15, -398, -95, 2.8), (17.45, -398, -100, 3.2, 'lin'), (17.75, -330, -150, 1.6, 'out'),
          (18.3, -300, -170, 1.25), (18.75, -385, -110, 2.2), (19.5, -385, -110, 2.45, 'lin'),
          (19.64, -230, -120, 1.5, 'snap'), (20.0, -140, -120, 1.9), (20.45, -100, -130, 1.6), (21.25, -100, -160, 1.15),
          (21.95, -110, -420, 1.3), (22.25, -100, -460, 1.85), (22.65, -100, -430, 1.7), (23.25, -100, -130, 1.35),
          (23.95, -100, -120, 2.2), (24.7, -100, -118, 2.45, 'lin'), (24.76, -90, -130, 1.05, 'snap'),
          (26.2, -90, -160, 0.95), (29.6, -90, -260, 0.78, 'lin')]:
    CAM.key(k[0], k[1], k[2] + 12, k[3]*1.15, k[4] if len(k) > 4 else 'io')

# ================================================================= finalize timing
ANIM_END = 29.7
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
    states = {n: F.state(ta) for n, F in FIGHTERS.items()}
    prev = {n: F.state(ta - 0.04) for n, F in FIGHTERS.items()}
    for n, st in states.items():   # contact shadows
        c = v.ws(st['x'], 2); s = max(0.2, 1 - st['alt']/500)
        rx, ry = 46*v.k*s, 9*v.k*s
        L['back'].ellipse([c[0]-rx, c[1]-ry, c[0]+rx, c[1]+ry], fill=(0, 0, 0, int(120*s)))
    for e in FXR:
        age = tr - e.tr
        if 0 <= age < e.d:
            if e.kind == 'aura':
                e.kw['fighter'] = FIGHTERS[e.kw['fighter']] if isinstance(e.kw['fighter'], str) else e.kw['fighter']
                e.kw['state'] = e.kw['fighter'].state(ta)
            draw_fx(e, age, L, v, fi)
    vels = {}
    for n, F in FIGHTERS.items():
        st, pv = states[n], prev[n]
        vel = ((st['x'] - pv['x'])/0.04, -(st['alt'] - pv['alt'])/0.04); vels[n] = vel
        sp = math.hypot(*vel)
        if sp > 650:   # afterimages
            acc = hexc(F.look['acc'])
            for j in (2, 1):
                gs = F.state(ta - j*0.03)
                parts = fighter_parts(F, gs, v, ta, vel)
                draw_parts(L['back'], L['glow'], parts, ghost=mix(acc, (255, 255, 255), 0.3) + (int(min(1, sp/1500)*(105 - j*35)),))
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
