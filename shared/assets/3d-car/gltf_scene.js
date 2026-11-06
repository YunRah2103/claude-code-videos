// Scene module for export_gltf.mjs: the coupe with plain standard materials (ids -> base colours), exported as glTF JSON.
import * as THREE from 'three';
import { GLTFExporter } from '../vendor/jsm/exporters/GLTFExporter.js';
import { buildCoupe } from './coupe.js';
import { stdMat } from './toon.js';
export async function build() {
  const car = buildCoupe(THREE, (id) => stdMat(id)); car.pose({ xray: true });
  const gltf = await new GLTFExporter().parseAsync(car.group, { binary: false });
  return { gltf: JSON.stringify(gltf), frame: () => ({}) };
}
