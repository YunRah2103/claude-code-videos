// Toon "ID buffer" materials for the 3D pixel look. Nothing is coloured in WebGL: every fragment writes
//   info pass  (uMode 0): R = material id, G = light level (0..1, /1.25 headroom), B = cool rim amount
//   depth pass (uMode 1): R,G = linear depth (16 bit, uNear..uFar), B = 0
// and pixpost.py maps id + light to a fixed <=40-colour palette with Bayer dither and navy outlines.
// Ids must match pixpost.py RAMPS.
import * as THREE from 'three';

export const ID = { BODY: 1, GLASS: 2, TYRE: 3, RIM: 4, DARK: 5, HEAD: 6, TAIL: 7, METAL: 8, GLOW: 9, SAND: 10,
  BACK: 11, ARROW: 12, HOT: 13, SKIN: 14, HAIR: 15, SHIRT: 16, JEANS: 17, SAND_LINE: 18, SKID: 19, BACK_LAMP: 20,
  SPECS: 21, EYE: 22 };   // face details: never outlined (they are 1-2 px at 135x240)

export const U = {                                   // shared uniforms (one object: set once per frame)
  uMode: { value: 0 }, uNear: { value: 0.1 }, uFar: { value: 60 },
  uKey: { value: new THREE.Vector3(0.55, 0.75, 0.45).normalize() },      // warm key: front-left, high
  uRim: { value: new THREE.Vector3(-0.7, 0.35, -0.6).normalize() },      // cool rim from behind
  uPool: { value: new THREE.Vector3(0, 0, 0) },                          // floor light pool centre (x, z) + unused
  uFloorOff: { value: new THREE.Vector2(0, 0) },                         // floor joints scroll (car driving)
  uShadow: { value: new THREE.Vector4(0, 0, 0, 0) },                     // car contact shadow: x, z, yaw, strength
  uTime: { value: 0 },
};

const VERT = `
varying vec3 vN; varying vec3 vW; varying float vD;
void main(){
  mat4 m = modelMatrix;
#ifdef USE_INSTANCING
  m = modelMatrix * instanceMatrix;
#endif
  vec4 w = m * vec4(position, 1.0); vW = w.xyz;
  vN = normalize(mat3(m) * normal);
  vec4 mv = viewMatrix * w; vD = -mv.z; gl_Position = projectionMatrix * mv;
}`;

const FRAG = `
uniform float uMode, uNear, uFar, uId, uKind, uSpec, uGlow, uTime, uLevel;
uniform vec3 uKey, uRim, uPool; uniform vec2 uFloorOff; uniform vec4 uShadow;
varying vec3 vN; varying vec3 vW; varying float vD;
void main(){
  if (uMode > 0.5) {                                   // depth pass
    float d = clamp((vD - uNear) / (uFar - uNear), 0.0, 1.0) * 65535.0;
    gl_FragColor = vec4(floor(d / 256.0) / 255.0, mod(d, 256.0) / 255.0, 0.0, 1.0); return;
  }
  vec3 N = normalize(vN); if (!gl_FrontFacing) N = -N;
  vec3 V = normalize(cameraPosition - vW);
  float id = uId, lit, rim = 0.0;
  if (uKind < 0.5) {                                   // lit solid: ambient + warm key + glossy highlight
    float k = max(dot(N, uKey), 0.0);
    float sky = 0.5 + 0.5 * N.y;
    lit = 0.07 + 0.2 * sky + 0.74 * k + uSpec * pow(max(dot(N, normalize(uKey + V)), 0.0), 36.0);
    rim = pow(1.0 - max(dot(N, V), 0.0), 2.5) * smoothstep(-0.1, 0.6, dot(N, uRim) + 0.3);
    lit = lit * uLevel + uGlow;
  } else if (uKind < 1.5) {                            // sand floor: light pool, joints, contact shadow
    vec2 p = vW.xz - uPool.xz; float r = length(p);
    lit = 0.95 - 0.045 * r;
    vec2 g = fract((vW.xz + uFloorOff) / vec2(1.6, 1.6));
    vec2 gd = min(g, 1.0 - g) * 1.6;
    if (min(gd.x, gd.y) < 0.022) id = ${ID.SAND_LINE}.0;
    vec2 q = vW.xz - uShadow.xy; float c = cos(uShadow.z), s = sin(uShadow.z);
    q = vec2(c * q.x - s * q.y, s * q.x + c * q.y);
    vec2 e = abs(q) - vec2(1.95, 0.72);
    float sd = length(max(e, 0.0)) + min(max(e.x, e.y), 0.0);
    lit -= uShadow.w * (1.0 - smoothstep(-0.25, 0.45, sd));
  } else if (uKind < 2.5) {                            // backdrop: slatted roller doors, pillars, lamps
    float a = atan(vW.z, vW.x) * 14.0 / 3.14159;      // 28 bays around
    float f = fract(a), slat = fract(vW.y / 0.22);
    lit = 0.55 - 0.05 * vW.y + 0.25 * (slat < 0.18 ? -1.0 : 0.0);
    if (f < 0.07) lit = 0.85;                          // pillar
    if (vW.y > 3.6 && vW.y < 3.9 && f > 0.35 && f < 0.65) { id = ${ID.BACK_LAMP}.0; lit = 0.9; }
    lit *= 0.9 + 0.1 * sin(a * 0.5 + uTime * 0.0);
  } else { lit = uLevel; }                             // flat (emissive panels, skid marks)
  gl_FragColor = vec4(id / 255.0, clamp(lit / 1.25, 0.0, 1.0), clamp(rim, 0.0, 1.0), 1.0);
}`;

// kind: 0 lit, 1 floor, 2 backdrop, 3 flat. spec: glossiness (body ~0.5). glow: added light (engine pulse).
export function mat(id, { kind = 0, spec = 0.0, glow = 0, level = 1, side = THREE.FrontSide } = {}) {
  return new THREE.ShaderMaterial({
    vertexShader: VERT, fragmentShader: FRAG, side,
    uniforms: { ...U, uId: { value: id }, uKind: { value: kind }, uSpec: { value: spec }, uGlow: { value: glow }, uLevel: { value: level } },
  });
}

// Standard-material stand-in (for glTF export / normal previews): same ids -> flat base colours.
export const BASE = { 1: 0xefd5aa, 2: 0x3f8a8e, 3: 0x262636, 4: 0xb9b4bf, 5: 0x14141f, 6: 0xd8e6ff, 7: 0xb02446, 8: 0x7d7888,
  9: 0xf07a2a, 12: 0xb02446, 13: 0xf07a2a, 14: 0xb8966c, 15: 0x14141f, 16: 0xfff0d0, 17: 0x1f2342 };
export function stdMat(id) { return new THREE.MeshStandardMaterial({ color: BASE[id] ?? 0x888888, roughness: id === 2 ? 0.1 : 0.5, metalness: [4, 8].includes(id) ? 0.6 : 0 }); }
