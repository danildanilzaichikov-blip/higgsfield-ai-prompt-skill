// Articulated voxel creatures. Every part is a set of 3D primitives (ellipsoids, tapered capsules)
// filled into a voxel grid with stepped, baked pixel-art shading; parts hang on pivots so legs,
// heads and tails move. Units in the definitions: centimetres, y up. Quadrupeds face +x, people face +z.
import * as THREE from 'three';
import V from './voxels.json' with { type: 'json' };

const MATS = { ...V.mats,
  eye: { ramp: [[30, 18, 10], [120, 70, 20], [220, 150, 40], [250, 200, 80]], noise: 0 },
  pink: { ramp: [[120, 50, 70], [190, 100, 120], [235, 150, 165], [250, 195, 205]], noise: 0 },
  black: { ramp: [[10, 8, 14], [24, 18, 28], [40, 32, 46], [64, 56, 70]], noise: 0 },
  spines: { ramp: [[30, 20, 16], [60, 42, 30], [96, 70, 50], [140, 110, 80], [190, 165, 130]], noise: .5 },
  antler: { ramp: [[60, 40, 26], [110, 80, 54], [170, 140, 100], [220, 200, 160]], noise: .1 },
  feather: { ramp: [[40, 30, 40], [80, 60, 60], [130, 100, 80], [180, 150, 110], [220, 200, 160]], noise: .25 },
  wingB: { ramp: [[20, 30, 90], [40, 80, 180], [80, 140, 230], [160, 200, 255]], noise: 0 },
  wingY: { ramp: [[120, 60, 0], [210, 130, 10], [250, 200, 50], [255, 240, 150]], noise: 0 },
  deer: { ramp: [[60, 30, 20], [110, 60, 34], [160, 96, 54], [200, 136, 80], [228, 176, 120]], noise: .14 },
  squir: { ramp: [[70, 24, 10], [130, 50, 18], [190, 88, 32], [230, 130, 60], [250, 180, 110]], noise: .16 },
};
const L = new THREE.Vector3(-.5, .72, .48).normalize(), RIM = new THREE.Vector3(.75, .4, -.3).normalize();
const hsh = (x, y, z) => { const v = Math.sin(x * 12.9898 + y * 78.233 + z * 37.719) * 43758.5453; return v - Math.floor(v); };
const BOX = new THREE.BoxGeometry(1, 1, 1);

// ['e', cx,cy,cz, rx,ry,rz, mat]  |  ['c', ax,ay,az, bx,by,bz, r0, r1, mat]
export function vox(prims, vs = 2) {
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9, z0 = 1e9, z1 = -1e9;
  for (const p of prims) {
    if (p[0] === 'e') { x0 = Math.min(x0, p[1] - p[4]); x1 = Math.max(x1, p[1] + p[4]); y0 = Math.min(y0, p[2] - p[5]); y1 = Math.max(y1, p[2] + p[5]); z0 = Math.min(z0, p[3] - p[6]); z1 = Math.max(z1, p[3] + p[6]); }
    else { const r = Math.max(p[7], p[8]); x0 = Math.min(x0, p[1] - r, p[4] - r); x1 = Math.max(x1, p[1] + r, p[4] + r); y0 = Math.min(y0, p[2] - r, p[5] - r); y1 = Math.max(y1, p[2] + r, p[5] + r); z0 = Math.min(z0, p[3] - r, p[6] - r); z1 = Math.max(z1, p[3] + r, p[6] + r); }
  }
  x0 = Math.floor(x0 / vs) * vs; y0 = Math.floor(y0 / vs) * vs; z0 = Math.floor(z0 / vs) * vs;
  const nx = Math.ceil((x1 - x0) / vs) + 1, ny = Math.ceil((y1 - y0) / vs) + 1, nz = Math.ceil((z1 - z0) / vs) + 1;
  const id = new Int16Array(nx * ny * nz).fill(-1), N = new Float32Array(nx * ny * nz * 3), I = (i, j, k) => (k * ny + j) * nx + i;
  prims.forEach((p, pi) => {
    let bx0, bx1, by0, by1, bz0, bz1;
    if (p[0] === 'e') [bx0, bx1, by0, by1, bz0, bz1] = [p[1] - p[4], p[1] + p[4], p[2] - p[5], p[2] + p[5], p[3] - p[6], p[3] + p[6]];
    else { const r = Math.max(p[7], p[8]); [bx0, bx1, by0, by1, bz0, bz1] = [Math.min(p[1], p[4]) - r, Math.max(p[1], p[4]) + r, Math.min(p[2], p[5]) - r, Math.max(p[2], p[5]) + r, Math.min(p[3], p[6]) - r, Math.max(p[3], p[6]) + r]; }
    const i0 = Math.max(0, Math.floor((bx0 - x0) / vs)), i1 = Math.min(nx - 1, Math.ceil((bx1 - x0) / vs)), j0 = Math.max(0, Math.floor((by0 - y0) / vs)), j1 = Math.min(ny - 1, Math.ceil((by1 - y0) / vs)), k0 = Math.max(0, Math.floor((bz0 - z0) / vs)), k1 = Math.min(nz - 1, Math.ceil((bz1 - z0) / vs));
    for (let k = k0; k <= k1; k++) for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
      const X = x0 + (i + .5) * vs, Y = y0 + (j + .5) * vs, Z = z0 + (k + .5) * vs; let ins, n0, n1, n2;
      if (p[0] === 'e') { const u = (X - p[1]) / p[4], v = (Y - p[2]) / p[5], w = (Z - p[3]) / p[6]; ins = u * u + v * v + w * w <= 1; n0 = u / p[4]; n1 = v / p[5]; n2 = w / p[6]; }
      else { const dx = p[4] - p[1], dy = p[5] - p[2], dz = p[6] - p[3], ll = dx * dx + dy * dy + dz * dz + 1e-9, t = Math.max(0, Math.min(1, ((X - p[1]) * dx + (Y - p[2]) * dy + (Z - p[3]) * dz) / ll)), r = p[7] + (p[8] - p[7]) * t;
        n0 = X - (p[1] + t * dx); n1 = Y - (p[2] + t * dy); n2 = Z - (p[3] + t * dz); ins = n0 * n0 + n1 * n1 + n2 * n2 <= r * r; }
      if (ins) { const q = I(i, j, k); id[q] = pi; const nl = Math.hypot(n0, n1, n2) || 1; N[q * 3] = n0 / nl; N[q * 3 + 1] = n1 / nl; N[q * 3 + 2] = n2 / nl; }
    }
  });
  const F = (i, j, k) => i >= 0 && j >= 0 && k >= 0 && i < nx && j < ny && k < nz && id[I(i, j, k)] >= 0, list = [];
  for (let k = 0; k < nz; k++) for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) if (F(i, j, k) && !(F(i + 1, j, k) && F(i - 1, j, k) && F(i, j + 1, k) && F(i, j - 1, k) && F(i, j, k + 1) && F(i, j, k - 1))) list.push([i, j, k]);
  const mesh = new THREE.InstancedMesh(BOX, new THREE.MeshLambertMaterial({ color: '#ffffff' }), Math.max(1, list.length));
  const m4 = new THREE.Matrix4(), col = new THREE.Color(), n = new THREE.Vector3(), s = vs / 100;
  list.forEach(([i, j, k], idx) => {
    const q = I(i, j, k), p = prims[id[q]], M = MATS[p[p.length - 1]] ?? MATS.dark, R = M.ramp;
    m4.makeScale(s, s, s).setPosition((x0 + (i + .5) * vs) / 100, (y0 + (j + .5) * vs) / 100, (z0 + (k + .5) * vs) / 100); mesh.setMatrixAt(idx, m4);
    n.set(N[q * 3], N[q * 3 + 1], N[q * 3 + 2]);
    let v = .4 + .6 * Math.max(0, n.dot(L)); if (M.noise) v += (hsh(i, j, k) - .5) * M.noise * 1.5;
    let ix = Math.max(0, Math.min(R.length - 1, Math.floor(v * (R.length - 1) + .35)));
    if (n.dot(RIM) > .7) ix = Math.min(R.length - 1, ix + 1);
    if ((!F(i - 1, j, k) || !F(i + 1, j, k) || !F(i, j - 1, k)) && Math.abs(n.z) < .3) ix = Math.max(0, ix - 1);
    const c = R[ix]; col.setRGB(c[0] / 255, c[1] / 255, c[2] / 255, THREE.SRGBColorSpace); mesh.setColorAt(idx, col);
  });
  mesh.instanceMatrix.needsUpdate = true; if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  mesh.castShadow = true; mesh.receiveShadow = true; return mesh;
}
function part(prims, pivot = [0, 0, 0], vs = 2) { const g = new THREE.Group(); g.position.set(pivot[0] / 100, pivot[1] / 100, pivot[2] / 100); if (prims.length) g.add(vox(prims, vs)); return g; }
const mir = (prims, sz) => prims.map(p => { const q = [...p]; q[3] *= sz; if (q[0] === 'c') q[6] *= sz; return q; });

// —— quadruped: body hangs on the hips so it can rear or sit; legs have a knee; head and tail on pivots ——
function quad(o) {
  const root = new THREE.Group(), body = part(o.body, o.hip, o.vs), head = part(o.head, o.neck, o.vs), tail = part(o.tail, o.tailP, o.vs);
  root.add(body); body.add(head); body.add(tail);
  const legs = [];
  for (const [front, sz] of [[1, 1], [1, -1], [0, 1], [0, -1]]) {
    const L0 = front ? o.fl : o.hl, onBody = front || o.hop;
    const pv = (!front && o.hop) ? [L0.p[0] - o.hip[0], L0.p[1] - o.hip[1], L0.p[2] * sz] : [L0.p[0], L0.p[1], L0.p[2] * sz];
    const up = part(mir(L0.up, sz), pv, o.vs), lo = part(mir(L0.lo, sz), L0.knee, o.vs);
    up.add(lo); (onBody ? body : root).add(up); legs.push({ up, lo, front, ph: (front ? 0 : .5) + (sz > 0 ? 0 : .5) * (o.gallop ? 0 : 1) });
  }
  const nose = new THREE.Object3D(); nose.position.set(o.noseP[0] / 100, o.noseP[1] / 100, 0); head.add(nose);
  root.userData = { head, nose };
  // state: { phase, moving (0..1), rear (0..1), sit (0..1), look, wag, t }
  function pose(S) {
    const sw = o.swing * S.moving;
    legs.forEach(l => {
      const a = Math.sin((S.phase + l.ph) * Math.PI * 2);
      l.up.rotation.z = a * sw; l.lo.rotation.z = (l.front ? -1 : 1) * Math.max(0, -Math.cos((S.phase + l.ph) * Math.PI * 2)) * sw * 1.1;
    });
    if (o.hop) { const hp = Math.abs(Math.sin(S.phase * Math.PI)); body.position.y = o.hip[1] / 100 + hp * (o.hopH ?? .18) * S.moving; legs.forEach(l => { l.up.rotation.z = (l.front ? -.6 : .9) * hp * S.moving; }); }
    else body.position.y = o.hip[1] / 100 + Math.abs(Math.cos(S.phase * Math.PI * 2)) * .012 * S.moving - (S.sit || 0) * (o.sitDrop ?? 0);
    body.rotation.z = (S.rear || 0) * 1.05 + (S.sit || 0) * .55;
    legs.forEach(l => { if (!l.front && S.sit) { l.up.rotation.z += S.sit * .9; l.lo.rotation.z -= S.sit * 1.5; } if (l.front && (S.rear || S.sit)) { l.up.rotation.z -= (S.rear || 0) * .9 + (S.sit || 0) * .55; l.lo.rotation.z += (S.rear || 0) * .9; } });
    head.rotation.z = -(S.rear || 0) * .7 - (S.sit || 0) * .45 + Math.sin(S.t * 1.7) * .04 + (S.nod || 0) * .25;
    head.rotation.y = (S.look || 0);
    tail.rotation.y = Math.sin(S.t * (o.wagF ?? 3)) * (S.wag ?? .25); tail.rotation.z = Math.sin(S.phase * Math.PI * 4) * .12 * S.moving;
  }
  return { root, pose, stride: o.stride };
}

// —— the cast ——
export function wolf() {
  const F = 'wolf', Lt = 'wolflight';
  return quad({ vs: 2, swing: .5, stride: 1.25, hip: [-30, 60, 0], neck: [72, 18, 0], tailP: [-18, 4, 0], noseP: [26, -1],
    body: [['e', 30, 2, 0, 44, 17, 15, F], ['e', 62, 2, 0, 20, 21, 16, F], ['e', 4, 2, 0, 18, 18, 15, F], ['e', 34, -8, 0, 30, 9, 11, Lt], ['e', 64, 8, 0, 13, 15, 15, Lt], ['c', 66, 8, 0, 78, 22, 0, 12, 10, F]],
    head: [['e', 6, 6, 0, 11, 10, 10, F], ['c', 12, 2, 0, 26, -1, 0, 5.5, 3.6, F], ['c', 12, -2, 0, 24, -4, 0, 3.8, 2.6, Lt], ['e', 27, -1, 0, 2.4, 2.2, 2.4, 'black'],
      ['e', 15, 9, 5.6, 1.8, 1.3, 1.2, 'eye'], ['e', 15, 9, -5.6, 1.8, 1.3, 1.2, 'eye'], ['e', 16, 9, 6.4, .9, .9, .8, 'black'], ['e', 16, 9, -6.4, .9, .9, .8, 'black'],
      ['c', 3, 14, 5, 1, 26, 4, 3.8, 1, F], ['c', 3, 14, -5, 1, 26, -4, 3.8, 1, F], ['e', 9, -6, 0, 7, 3, 6, Lt]],
    tail: [['c', 0, 0, 0, -16, -20, 0, 6, 5, F], ['c', -16, -20, 0, -22, -34, 0, 5, 2.2, Lt]],
    fl: { p: [64, -6, 8], up: [['c', 0, 0, 0, 1, -24, 0, 5.5, 4.4, F]], knee: [1, -24, 0], lo: [['c', 0, 0, 0, -1, -27, 0, 4, 3, F], ['e', 2, -29, 0, 5.5, 2.6, 4, F]] },
    hl: { p: [-34, 60, 8], up: [['e', 0, -6, 0, 9, 13, 7, F], ['c', 0, -10, 0, -6, -30, 0, 5, 3.8, F]], knee: [-6, -30, 0], lo: [['c', 0, 0, 0, 4, -27, 0, 3.4, 3, F], ['e', 6, -29, 0, 5.5, 2.6, 4, F]] },
  });
}
export function fox() {
  const F = 'fox', W = 'foxwhite', D = 'black';
  return quad({ vs: 1.6, swing: .5, stride: .8, hip: [-18, 38, 0], neck: [44, 12, 0], tailP: [-12, 2, 0], noseP: [20, -1], sitDrop: .1, wagF: 2,
    body: [['e', 18, 2, 0, 27, 11, 10, F], ['e', 38, 4, 0, 13, 13, 10, F], ['e', 40, 0, 6, 9, 11, 5, W], ['e', 40, 0, -6, 9, 11, 5, W], ['e', 2, 2, 0, 12, 12, 10, F], ['c', 42, 6, 0, 48, 14, 0, 7.5, 6.5, F]],
    head: [['e', 4, 5, 0, 8, 7, 7.5, F], ['c', 8, 2, 0, 20, -1, 0, 4, 2, F], ['c', 8, -1, 0, 18, -3, 0, 3, 1.6, W], ['e', 7, 0, 5.5, 4, 3, 2, W], ['e', 7, 0, -5.5, 4, 3, 2, W], ['e', 20.5, -1, 0, 1.6, 1.5, 1.6, D],
      ['e', 11, 6, 4.2, 1.4, .8, 1, 'black'], ['e', 11, 6, -4.2, 1.4, .8, 1, 'black'],
      ['c', 1, 10, 4.5, -1, 22, 5, 4, .8, F], ['c', 1, 10, -4.5, -1, 22, -5, 4, .8, F], ['c', -.5, 18, 5, -1, 22, 5, 1.4, .6, D], ['c', -.5, 18, -5, -1, 22, -5, 1.4, .6, D]],
    tail: [['c', 0, 0, 0, -14, -10, 0, 6, 8, F], ['c', -14, -10, 0, -26, -16, 0, 8, 6.5, F], ['c', -26, -16, 0, -32, -18, 0, 6, 2, W]],
    fl: { p: [40, -4, 5], up: [['c', 0, 0, 0, 1, -16, 0, 3, 2.4, F]], knee: [1, -16, 0], lo: [['c', 0, 0, 0, 0, -17, 0, 2.2, 1.8, D], ['e', 2, -18, 0, 3.2, 1.6, 2.4, D]] },
    hl: { p: [-20, 38, 5], up: [['e', 0, -4, 0, 6, 9, 5, F], ['c', 0, -6, 0, -4, -19, 0, 3.2, 2.4, F]], knee: [-4, -19, 0], lo: [['c', 0, 0, 0, 3, -17, 0, 2.1, 1.8, D], ['e', 4.5, -18, 0, 3.2, 1.6, 2.4, D]] },
  });
}
export function bear() {
  const F = 'bear', Lt = 'bearlight';
  return quad({ vs: 2.4, swing: .38, stride: 1.4, hip: [-40, 74, 0], neck: [86, 6, 0], tailP: [-26, 4, 0], noseP: [34, -6],
    body: [['e', 38, 0, 0, 52, 33, 31, F], ['e', 64, 14, 0, 24, 20, 24, F], ['e', 4, 2, 0, 26, 30, 28, F], ['e', 40, -18, 0, 36, 12, 22, Lt], ['c', 76, 4, 0, 90, 4, 0, 18, 16, F]],
    head: [['e', 8, 2, 0, 19, 18, 18, F], ['c', 16, -3, 0, 30, -6, 0, 9, 7.5, Lt], ['e', 33, -4, 0, 3.6, 3, 4.5, 'black'], ['c', 22, -11, 0, 30, -11, 0, 3, 2.4, Lt],
      ['e', 18, 7, 8, 2, 2, 1.6, 'black'], ['e', 18, 7, -8, 2, 2, 1.6, 'black'], ['e', 2, 18, 11, 6, 6, 4, F], ['e', 2, 18, -11, 6, 6, 4, F], ['e', 3, 18, 12, 3, 3, 3, Lt], ['e', 3, 18, -12, 3, 3, 3, Lt]],
    tail: [['e', -3, 0, 0, 6, 6, 6, F]],
    fl: { p: [70, -14, 15], up: [['c', 0, 0, 0, 2, -30, 0, 12, 10, F]], knee: [2, -30, 0], lo: [['c', 0, 0, 0, 0, -26, 0, 9.5, 9, F], ['e', 4, -30, 0, 11, 5, 9, F], ['c', 12, -31, 4, 15, -32, 4, 1.4, .8, 'beard'], ['c', 12, -31, -1, 15, -32, -1, 1.4, .8, 'beard'], ['c', 12, -31, -6, 15, -32, -6, 1.4, .8, 'beard']] },
    hl: { p: [-44, 74, 15], up: [['e', 0, -8, 0, 15, 22, 13, F], ['c', 0, -14, 0, -4, -40, 0, 10, 9, F]], knee: [-4, -40, 0], lo: [['c', 0, 0, 0, 2, -28, 0, 9, 9, F], ['e', 6, -33, 0, 13, 5, 9, F]] },
  });
}
export function hare() {
  const F = 'hare', W = 'harebelly';
  return quad({ vs: 1.4, swing: .3, stride: .9, hop: true, gallop: true, hip: [-6, 18, 0], neck: [20, 16, 0], tailP: [-16, 6, 0], noseP: [15, -2],
    body: [['e', 6, 6, 0, 18, 13, 11, F], ['e', 14, 6, 6, 9, 9, 4, W], ['e', -6, 4, 0, 12, 13, 11, F], ['e', 14, 4, 0, 10, 12, 9, W]],
    head: [['e', 4, 4, 0, 8, 7.5, 7, F], ['e', 11, 1, 0, 4.4, 4, 4.5, W], ['e', 15, 1, 0, 1.3, 1.1, 1.3, 'pink'], ['e', 7, 6, 5, 1.8, 2, 1.4, 'black'], ['e', 7, 6, -5, 1.8, 2, 1.4, 'black'], ['e', 7.6, 6.8, 5.8, .6, .6, .5, 'white'],
      ['c', 0, 10, 3, -6, 33, 4, 3.2, 2.3, F], ['c', 0, 10, -3, -2, 33, -4, 3.2, 2.3, F], ['c', -.5, 14, 4.8, -5.5, 31, 5.6, 1.7, 1.2, 'pink'], ['c', 0, 14, -4.8, -2, 31, -5.6, 1.7, 1.2, 'pink'], ['c', -5.5, 31, 4, -6, 34, 4, 2.3, 1.5, 'black'], ['c', -2, 31, -4, -2, 34, -4, 2.3, 1.5, 'black']],
    tail: [['e', -1, 0, 0, 4, 4, 4, 'white']],
    fl: { p: [14, -4, 5], up: [['c', 0, 0, 0, 1, -9, 0, 2.4, 2, F]], knee: [1, -9, 0], lo: [['c', 0, 0, 0, 1, -8, 0, 2, 1.8, F], ['e', 3, -9, 0, 3, 1.4, 2, W]] },
    hl: { p: [-10, 18, 6], up: [['e', 0, -4, 0, 8, 9, 5, F]], knee: [-4, -10, 0], lo: [['c', 0, 0, 0, 2, -7, 0, 2.6, 2.2, F], ['e', 6, -8.5, 0, 9, 1.8, 3, F]] },
  });
}
export function deer() {
  const F = 'deer', W = 'foxwhite';
  return quad({ vs: 2.2, swing: .45, stride: 1.3, hip: [-34, 92, 0], neck: [56, 28, 0], tailP: [-22, 8, 0], noseP: [26, -10],
    body: [['e', 22, 4, 0, 44, 18, 16, F], ['e', 0, 6, 0, 18, 18, 15, F], ['e', 24, -8, 0, 30, 8, 11, W], ['c', 50, 10, 0, 60, 34, 0, 9, 7, F]],
    head: [['e', 4, 2, 0, 8, 8, 7.5, F], ['c', 6, -2, 0, 20, -10, 0, 5, 3.2, F], ['e', 21, -10, 0, 2, 1.8, 2, 'black'], ['e', 8, 3, 5.6, 1.6, 1.6, 1.2, 'black'], ['e', 8, 3, -5.6, 1.6, 1.6, 1.2, 'black'],
      ['c', -2, 8, 6, -8, 16, 12, 2.6, 1.5, F], ['c', -2, 8, -6, -8, 16, -12, 2.6, 1.5, F],
      ['c', 0, 9, 3, -4, 30, 6, 1.3, 1, 'antler'], ['c', -2, 18, 4, 6, 26, 6, 1, .8, 'antler'], ['c', 0, 9, -3, -4, 30, -6, 1.3, 1, 'antler'], ['c', -2, 18, -4, 6, 26, -6, 1, .8, 'antler']],
    tail: [['e', -2, 0, 0, 3, 5, 3, W]],
    fl: { p: [36, -8, 8], up: [['c', 0, 0, 0, 1, -40, 0, 4, 3, F]], knee: [1, -40, 0], lo: [['c', 0, 0, 0, 0, -42, 0, 2.6, 2.2, F], ['e', 1, -44, 0, 2.6, 2, 2.4, 'black']] },
    hl: { p: [-38, 92, 8], up: [['e', 0, -10, 0, 10, 16, 7, F], ['c', 0, -14, 0, -6, -44, 0, 4.5, 3, F]], knee: [-6, -44, 0], lo: [['c', 0, 0, 0, 3, -42, 0, 2.6, 2.2, F], ['e', 4, -44, 0, 2.6, 2, 2.4, 'black']] },
  });
}
export function squirrel() {
  const F = 'squir';
  return quad({ vs: 1, swing: .45, stride: .45, hop: true, gallop: true, hip: [-4, 10, 0], neck: [11, 8, 0], tailP: [-9, 2, 0], noseP: [8, -1],
    body: [['e', 3, 3, 0, 9, 7, 5.5, F], ['e', 7, 2, 3, 4, 5, 2, 'foxwhite']],
    head: [['e', 2, 3, 0, 5, 4.5, 4.5, F], ['e', 7, 2, 0, .9, .8, .9, 'black'], ['e', 4, 4, 3.3, 1.1, 1.3, .8, 'black'], ['e', 4, 4, -3.3, 1.1, 1.3, .8, 'black'], ['c', 0, 6, 2.5, -1, 11, 2.5, 1.4, .6, F], ['c', 0, 6, -2.5, -1, 11, -2.5, 1.4, .6, F]],
    tail: [['c', 0, 0, 0, -6, 10, 0, 3.5, 5, F], ['c', -6, 10, 0, -2, 20, 0, 5, 4, F], ['c', -2, 20, 0, 4, 22, 0, 4, 2, F]],
    fl: { p: [8, -2, 3], up: [['c', 0, 0, 0, 1, -5, 0, 1.4, 1.2, F]], knee: [1, -5, 0], lo: [['e', 1, -2, 0, 1.8, 1, 1.2, F]] },
    hl: { p: [-6, 10, 3.5], up: [['e', 0, -3, 0, 4, 5, 3, F]], knee: [-2, -6, 0], lo: [['e', 2, -3.5, 0, 4, 1, 1.6, F]] },
  });
}
export function hedgehog() {
  const S = 'spines', F = 'bearlight';
  return quad({ vs: 1, swing: .5, stride: .22, hip: [-6, 8, 0], neck: [9, 1, 0], tailP: [-11, 0, 0], noseP: [9, -2],
    body: [['e', 1, 2, 0, 11, 7, 8, S], ['e', 4, -2, 0, 8, 4, 6, F]],
    head: [['e', 2, 0, 0, 4, 3.5, 3.5, F], ['c', 3, -1, 0, 8, -2, 0, 2, 1, F], ['e', 9, -2, 0, .9, .9, .9, 'black'], ['e', 4, 1, 2.6, .8, .8, .6, 'black'], ['e', 4, 1, -2.6, .8, .8, .6, 'black']],
    tail: [],
    fl: { p: [6, -3, 4], up: [['c', 0, 0, 0, 0, -3, 0, 1.2, 1, F]], knee: [0, -3, 0], lo: [['e', .5, -2, 0, 1.3, .8, 1, F]] },
    hl: { p: [-6, 8, 4], up: [['c', 0, 0, 0, 0, -5, 0, 1.4, 1.1, F]], knee: [0, -5, 0], lo: [['e', .5, -2.6, 0, 1.4, .8, 1, F]] },
  });
}

// —— people: built facing +z; legs and arms swing on hips and shoulders ——
function person(o) {
  const root = new THREE.Group(), torso = part(o.torso, [0, 0, 0], 2), head = part(o.head, o.neck, 2);
  root.add(torso); torso.add(head);
  const limbs = [];
  for (const sx of [1, -1]) {
    const leg = part(o.leg.map(p => { const q = [...p]; q[1] *= sx; if (q[0] === 'c') q[4] *= sx; return q; }), [o.hipX * sx, o.hipY, 0]); root.add(leg); limbs.push({ g: leg, k: sx, leg: 1 });
    const arm = part(o.arm.map(p => { const q = [...p]; q[1] *= sx; if (q[0] === 'c') q[4] *= sx; return q; }), [o.shX * sx, o.shY, 0]); torso.add(arm); limbs.push({ g: arm, k: sx, leg: 0 });
  }
  root.userData = { head };
  function pose(S) {
    const a = Math.sin(S.phase * Math.PI * 2) * S.moving;
    limbs.forEach(l => { l.g.rotation.x = (l.leg ? -.45 : .4) * a * l.k; });
    torso.position.y = Math.abs(Math.cos(S.phase * Math.PI * 2)) * .02 * S.moving;
    head.rotation.y = (S.look || 0) + Math.sin(S.t * .9) * .05; head.rotation.x = Math.sin(S.t * 1.3) * .03 + (S.nod || 0) * .2;
    limbs.forEach(l => { if (!l.leg && S.wave && l.k > 0) { l.g.rotation.z = -S.wave * 2.4; l.g.rotation.x = Math.sin(S.t * 9) * .25 * S.wave; } });
  }
  return { root, pose, stride: .9 };
}
export function ded() {
  return person({ hipX: 9, hipY: 80, shX: 22, shY: 140, neck: [0, 148, 0],
    torso: [['e', 0, 116, 0, 21, 34, 14, 'linen'], ['e', 0, 88, 0, 24, 12, 15, 'linen'], ['e', 0, 100, 0, 22.5, 3, 15, 'red'], ['e', 0, 80, 0, 24.5, 2.4, 15.5, 'red'], ['e', 0, 145, 6, 9, 3, 7, 'red']],
    head: [['e', 0, 22, -3, 16.5, 15, 13, 'grey'], ['e', 0, 22, 0, 14.5, 16.5, 14, 'skin'], ['e', 0, 3, 8, 13, 17, 8, 'beard'], ['e', -4.5, 13, 13, 6, 2.8, 3, 'beard'], ['e', 4.5, 13, 13, 6, 2.8, 3, 'beard'],
      ['e', 0, 17, 14.5, 3.6, 3.6, 3, 'skin'], ['e', -5.5, 24, 12.5, 1.9, 1.9, 1.5, 'black'], ['e', 5.5, 24, 12.5, 1.9, 1.9, 1.5, 'black'], ['e', -6, 28, 12, 4, 1.2, 1.5, 'grey'], ['e', 6, 28, 12, 4, 1.2, 1.5, 'grey'], ['e', -9, 18, 11, 3, 2, 2, 'pink'], ['e', 9, 18, 11, 3, 2, 2, 'pink']],
    leg: [['c', 0, 0, 0, 0, -38, 0, 7, 6.5, 'trous'], ['c', 0, -38, 0, 0, -72, 0, 6.5, 6, 'white'], ['e', 0, -76, 4, 7.5, 4.5, 11, 'bast']],
    arm: [['c', 0, 0, 0, 3, -28, 0, 6.5, 6, 'linen'], ['c', 3, -28, 0, 4, -50, 2, 5.5, 5, 'linen'], ['e', 4, -55, 2, 5, 5, 5, 'skin']],
  });
}
export function baba() {
  return person({ hipX: 8, hipY: 40, shX: 21, shY: 136, neck: [0, 146, 0],
    torso: [['e', 0, 100, 0, 23, 46, 16, 'red'], ['e', 0, 50, 0, 29, 34, 19, 'red'], ['e', 0, 80, 13, 14, 34, 5, 'linen'], ['e', 0, 18, 0, 30, 2.4, 19.5, 'scarf'], ['e', 0, 140, 3, 14, 6, 12, 'linen']],
    head: [['e', 0, 21, -2, 18, 19, 16, 'scarf'], ['e', 0, 19, 4, 12.5, 14, 13, 'skin'], ['e', 0, 3, 9, 6, 4, 4, 'scarf'], ['e', 0, 16, 16.5, 2.8, 2.8, 2.4, 'skin'],
      ['e', -5, 22, 15, 1.8, 1.8, 1.4, 'black'], ['e', 5, 22, 15, 1.8, 1.8, 1.4, 'black'], ['e', -7.5, 15, 14, 3, 2, 1.5, 'pink'], ['e', 7.5, 15, 14, 3, 2, 1.5, 'pink'],
      ['e', -12, 30, 11, 2, 2, 2, 'red'], ['e', 10, 34, 10, 2, 2, 2, 'red'], ['e', 0, 38, 6, 2, 2, 2, 'red'], ['e', 14, 22, 6, 2, 2, 2, 'red'], ['e', -15, 20, 5, 2, 2, 2, 'red']],
    leg: [['c', 0, 0, 0, 0, -32, 0, 5, 4.5, 'dark'], ['e', 0, -37, 4, 6, 3.5, 9, 'dark']],
    arm: [['c', 0, 0, 0, 3, -26, 3, 7, 6, 'linen'], ['c', 3, -26, 3, 0, -46, 10, 5.5, 5, 'linen'], ['e', 0, -51, 12, 5, 5, 5, 'skin']],
  });
}

// —— small life ——
export function bird(mat = 'feather') {
  const root = new THREE.Group(), body = part([['e', 0, 0, 0, 7, 4, 4, mat], ['e', 7, 2, 0, 3.5, 3.2, 3.2, mat], ['c', 10, 2, 0, 13, 1.5, 0, 1, .4, 'scarf'], ['c', -6, 0, 0, -13, 1, 0, 2.2, .8, mat], ['e', 8.5, 3, 2.2, .6, .6, .5, 'black'], ['e', 8.5, 3, -2.2, .6, .6, .5, 'black']], [0, 0, 0], 1);
  const wl = part([['e', -1, 0, 6, 5, 1, 7, mat]], [0, 1, 2], 1), wr = part([['e', -1, 0, -6, 5, 1, 7, mat]], [0, 1, -2], 1);
  root.add(body, wl, wr);
  return { root, pose(S) { const f = Math.sin(S.t * 18 + (S.seed || 0)) * .9; wl.rotation.x = f; wr.rotation.x = -f; } };
}
export function butterfly(mat = 'wingB') {
  const root = new THREE.Group(), body = part([['c', -3, 0, 0, 3, 0, 0, .7, .6, 'black']], [0, 0, 0], .5);
  const wl = part([['e', 0, 0, 3, 3, .4, 3.4, mat], ['e', -2, 0, 3, 2, .4, 2, mat]], [0, 0, .6], .5), wr = part([['e', 0, 0, -3, 3, .4, 3.4, mat], ['e', -2, 0, -3, 2, .4, 2, mat]], [0, 0, -.6], .5);
  root.add(body, wl, wr);
  return { root, pose(S) { const f = Math.abs(Math.sin(S.t * 22 + (S.seed || 0))) * 1.3; wl.rotation.x = -f; wr.rotation.x = f; } };
}
export function owl() {
  const root = new THREE.Group(), body = part([['e', 0, 14, 0, 11, 15, 10, 'feather'], ['e', 0, 12, 7, 7, 10, 4, 'linen'], ['c', -4, 0, 2, -5, -3, 4, 1.2, 1, 'scarf'], ['c', 4, 0, 2, 5, -3, 4, 1.2, 1, 'scarf']], [0, 0, 0], 1);
  const head = part([['e', 0, 6, 0, 10, 9, 9, 'feather'], ['e', -4, 6, 6, 4, 4, 3, 'linen'], ['e', 4, 6, 6, 4, 4, 3, 'linen'], ['e', -4, 6, 8.5, 2.2, 2.2, 1, 'eye'], ['e', 4, 6, 8.5, 2.2, 2.2, 1, 'eye'],
    ['e', -4, 6, 9.4, 1, 1, .6, 'black'], ['e', 4, 6, 9.4, 1, 1, .6, 'black'], ['c', 0, 4, 8, 0, 1, 9, 1, .4, 'scarf'], ['c', -6, 12, 2, -8, 18, 0, 2, .6, 'feather'], ['c', 6, 12, 2, 8, 18, 0, 2, .6, 'feather']], [0, 26, 0], 1);
  root.add(body); root.add(head);
  return { root, pose(S) { head.rotation.y = Math.sin(S.t * .7) * .9; } };
}
