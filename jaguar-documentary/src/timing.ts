// Global timeline (seconds). Narration clips are placed back to back with short gaps.
export const FPS = 30;
export const NAR = [
  {file: 'audio/n1.mp3', at: 0.6, dur: 65.352},
  {file: 'audio/n2.mp3', at: 66.4, dur: 58.2},
  {file: 'audio/n3.mp3', at: 125.1, dur: 64.752},
  {file: 'audio/n4.mp3', at: 190.4, dur: 58.464},
  {file: 'audio/n5.mp3', at: 249.4, dur: 50.16},
];
export const TOTAL = 304.5;
export const TOTAL_FRAMES = Math.round(TOTAL * FPS);
