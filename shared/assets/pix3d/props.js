// Voxel props: handshake icon (the deal), key (unlock package), padlock (shackle pops open).
import { P } from './palette.js';
import { voxelSprite } from './voxel.js';
import * as THREE from 'three';

export function handshake(size = 1.6) {
  return voxelSprite([
    '.oooo.....ooo.........oooo.',
    'osssso...okkko.......occcco',
    'ossssoooookkkooooooooocccco',
    'osssssokkkkkkkkkkkkkokcccco',
    'osssssokdkkdkkdkkdkkkkcccco',
    'osssssokdkkdkkdkkdkkkkcccco',
    'osssssokdkkdkkdkkdkkkocccco',
    'osssso.okkkkkkkkkkkkooocccco',
    '.oooo...ooooooooooooo..oooo.',
  ], { o: P.navy, s: P.sleeve, c: P.carBlue, k: P.skin, d: 0xb07a52 }, { size, depth: 2 });
}

export function key(size = 1.2) {
  return voxelSprite([
    '.ggg...............',
    'gGGGg..............',
    'gG.GgggggggggggggggG',
    'gG.GGGGGGGGGGGGGGGGG',
    'gGGGg........G.G.G..',
    '.ggg.........G.G....',
  ], { g: [P.goldSh, false], G: [P.gold, true] }, { size, depth: 2 });
}

export function padlock(size = 1.5) {
  const g = new THREE.Group();
  const body = voxelSprite(['GGGGGGGG', 'GGGGGGGG', 'GGGnnGGG', 'GGGnnGGG', 'GGGGGGGG', 'gggggggg'],
                           { G: P.gold, g: P.goldSh, n: P.navy }, { size, depth: 2 });
  const shackle = voxelSprite(['..ssss..', '.s....s.', '.s....s.', '.s....s.'], { s: P.silverHi }, { size, depth: 1 });
  shackle.position.y = 6 * size; g.add(body); g.add(shackle);
  g.userData = { shackle, size };
  return g;
}
