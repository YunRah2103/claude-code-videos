"""Render one episode. Usage: EPDIR=../tesla python render.py video VOICE.wav MUSIC.mp3 OUT.mp4
| clip VOICE MUSIC OUT T0 T1 | still T OUT.png | sheet OUT.png t1,t2,... | thumb T OUT.png | meta OUT.json"""
import engine, scenes
engine.main(scenes)
