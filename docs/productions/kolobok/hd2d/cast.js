// Pixel sprites (rendered offline by the volumetric pixel engine) as lit, shadow-casting billboards.
import * as THREE from 'three';
import { billboard } from './px.js';
import { seg, ss, lerp, clamp, back } from '/core/lib.js';
import TLjson from './timeline.json' with { type: 'json' };
import { buildVoxel } from './voxels.js';
export const TL = TLjson;

const loader = new THREE.TextureLoader(), TEX = {}, META = {};
export async function loadSprites() {
  Object.assign(META, await (await fetch('sprites/meta.json')).json());
  await Promise.all(Object.keys(META).map(n => new Promise((res, rej) => loader.load('sprites/' + n + '.png', t => {
    t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false; t.colorSpace = THREE.SRGBColorSpace; TEX[n] = t; res();
  }, undefined, rej))));
}
export function sprite(name, hM, o = {}) {
  const [w, h] = META[name]; const b = billboard(TEX[name], hM * w / h, hM, o); b.userData.char = name; return b;
}
export function voxChar(name, hM) { return buildVoxel(name, hM, { vs: 1.5 }); }
export function voxKolobok(hM) { const g = buildVoxel('kolobok', hM, { vs: 1, center: true }); return { mesh: g, set(ang) { g.children[0].rotation.z = ang; } }; }
export function kolobokSprite(hM) {
  const [w, h, n] = META.kolobok, t = TEX.kolobok.clone(); t.needsUpdate = true; t.repeat.set(1 / n, 1);
  const b = billboard(t, hM * w / h, hM, { ay: .5 }); b.userData.char = 'kolobok';
  return { mesh: b, set(ang) { const k = ((Math.round(ang / (2 * Math.PI) * n) % n) + n) % n; t.offset.x = k / n; } };
}

// characters rise out of the page: vertical scale with a small overshoot, then sink on exit
export function popScale(t, t0, t1) {
  if (t < t0 || t > t1) return 0;
  return back(seg(t, t0, t0 + .55), 2.2) * (1 - ss(seg(t, t1 - .35, t1)));
}

// kolobok: on the sill, hop, roll in to each animal, roll away, hop onto the fox
const R = .275;
export function kolobokPath(t) {
  const E = TL.enc; let x = 0, y = R, z = .2, vis = false, ang = 0;
  const roll = (x0, x1, a, b) => { const k = ss(seg(t, a, b)); return lerp(x0, x1, k); };
  if (t >= 17.14 && t < 20.6) { x = 1.5; y = .82 + R; z = -2.25; vis = true; ang = 0; }
  else if (t >= 20.6 && t < 21.2) { const k = seg(t, 20.6, 21.2); x = lerp(1.5, 2.8, k); y = lerp(.82 + R, R, k) + Math.sin(Math.PI * k) * .7; z = lerp(-2.25, .2, k); vis = true; ang = -k * 4; }
  else if (t >= 21.2 && t < 22.86) { x = roll(2.8, 10, 21.2, 22.86); vis = true; }
  else if (t >= 22.86 && t < 28.57) { const ax = E.hare[0] - 2.4; x = t < 27.0 ? roll(10.5, ax, 22.86, E.hare[1]) : roll(ax, ax + 9, 27.0, 28.57); vis = true; }
  else if (t >= 28.57 && t < 34.29) { const ax = E.wolf[0] - 2.4; x = t < 32.7 ? roll(26.5, ax, 28.57, E.wolf[1]) : roll(ax, ax + 9, 32.7, 34.29); vis = true; }
  else if (t >= 34.29 && t < 40.0) { const ax = E.bear[0] - 2.6; x = t < 38.4 ? roll(42.5, ax, 34.29, E.bear[1]) : roll(ax, ax + 9, 38.4, 40.0); vis = true; }
  else if (t >= 40.0 && t < 48.57) {
    const ax = E.fox[0] - 2.4; x = roll(58.2, ax, 40.0, E.fox[1]); vis = true;
    if (t >= 47.6) { const k = seg(t, 47.6, 48.45); x = lerp(ax, E.fox[0] - .5, k); y = lerp(R, .78, k) + Math.sin(Math.PI * k) * .6; z = lerp(.2, .42, k); ang = -k * 6; }
  }
  if (vis && ang === 0) ang = -(x / R);
  return { x, y, z, vis, ang };
}
