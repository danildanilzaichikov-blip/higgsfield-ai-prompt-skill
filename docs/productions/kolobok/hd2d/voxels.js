// Voxel characters: the same 3D primitives as the pixel sprites, filled into a voxel grid.
// Each voxel takes a stepped colour from its material ramp (baked light, like pixel art);
// the scene's lights then add real form and real cast shadows on top.
import * as THREE from 'three';
import V from './voxels.json' with { type: 'json' };

const L = new THREE.Vector3(-.55, -.68, .48).normalize();       // sprite space: y points down
const RIM = new THREE.Vector3(.85, -.35, .15).normalize();
const hsh = (x, y, z) => { const v = Math.sin(x * 12.9898 + y * 78.233 + z * 37.719) * 43758.5453; return v - Math.floor(v); };
const _box = new THREE.BoxGeometry(1, 1, 1);

export function buildVoxel(name, hM, o = {}) {
  const d = V.chars[name], P = d.prims, vs = o.vs ?? 1.5;
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9, z0 = 1e9, z1 = -1e9;
  for (const p of P) {
    if (p[0] === 'ell') { const [, cx, cy, cz, rx, ry, rz] = p; x0 = Math.min(x0, cx - rx); x1 = Math.max(x1, cx + rx); y0 = Math.min(y0, cy - ry); y1 = Math.max(y1, cy + ry); z0 = Math.min(z0, cz - rz); z1 = Math.max(z1, cz + rz); }
    else { const [, ax, ay, az, bx, by, bz, r] = p; x0 = Math.min(x0, ax - r, bx - r); x1 = Math.max(x1, ax + r, bx + r); y0 = Math.min(y0, ay - r, by - r); y1 = Math.max(y1, ay + r, by + r); z0 = Math.min(z0, az - r, bz - r); z1 = Math.max(z1, az + r, bz + r); }
  }
  const nx = Math.ceil((x1 - x0) / vs) + 1, ny = Math.ceil((y1 - y0) / vs) + 1, nz = Math.ceil((z1 - z0) / vs) + 1;
  const id = new Int16Array(nx * ny * nz).fill(-1), nrm = new Float32Array(nx * ny * nz * 3);
  const I = (i, j, k) => (k * ny + j) * nx + i;
  P.forEach((p, pi) => {
    let bx0, bx1, by0, by1, bz0, bz1;
    if (p[0] === 'ell') { const [, cx, cy, cz, rx, ry, rz] = p; [bx0, bx1, by0, by1, bz0, bz1] = [cx - rx, cx + rx, cy - ry, cy + ry, cz - rz, cz + rz]; }
    else { const [, ax, ay, az, bx, by, bz, r] = p; [bx0, bx1, by0, by1, bz0, bz1] = [Math.min(ax, bx) - r, Math.max(ax, bx) + r, Math.min(ay, by) - r, Math.max(ay, by) + r, Math.min(az, bz) - r, Math.max(az, bz) + r]; }
    const i0 = Math.max(0, Math.floor((bx0 - x0) / vs)), i1 = Math.min(nx - 1, Math.ceil((bx1 - x0) / vs)), j0 = Math.max(0, Math.floor((by0 - y0) / vs)), j1 = Math.min(ny - 1, Math.ceil((by1 - y0) / vs)), k0 = Math.max(0, Math.floor((bz0 - z0) / vs)), k1 = Math.min(nz - 1, Math.ceil((bz1 - z0) / vs));
    for (let k = k0; k <= k1; k++) for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
      const X = x0 + (i + .5) * vs, Y = y0 + (j + .5) * vs, Z = z0 + (k + .5) * vs;
      let inside = false, n0, n1, n2;
      if (p[0] === 'ell') { const [, cx, cy, cz, rx, ry, rz] = p; const u = (X - cx) / rx, v = (Y - cy) / ry, w = (Z - cz) / rz; inside = u * u + v * v + w * w <= 1; n0 = u / rx; n1 = v / ry; n2 = w / rz; }
      else { const [, ax, ay, az, bx, by, bz, r] = p; const dx = bx - ax, dy = by - ay, dz = bz - az, ll = dx * dx + dy * dy + dz * dz + 1e-9; const t = Math.max(0, Math.min(1, ((X - ax) * dx + (Y - ay) * dy + (Z - az) * dz) / ll)); n0 = X - (ax + t * dx); n1 = Y - (ay + t * dy); n2 = Z - (az + t * dz); inside = n0 * n0 + n1 * n1 + n2 * n2 <= r * r; }
      if (inside) { const q = I(i, j, k); id[q] = pi; const nl = Math.hypot(n0, n1, n2) || 1; nrm[q * 3] = n0 / nl; nrm[q * 3 + 1] = n1 / nl; nrm[q * 3 + 2] = n2 / nl; }
    }
  });
  // decals (eyes, mouths, embroidery): paint the front-most voxel of each column
  const deco = new Map();
  for (const [x, y, c] of d.decals) {
    const i = Math.floor((x + .5 - x0) / vs), j = Math.floor((y + .5 - y0) / vs); if (i < 0 || j < 0 || i >= nx || j >= ny) continue;
    for (let k = nz - 1; k >= 0; k--) if (id[I(i, j, k)] >= 0) { deco.set(I(i, j, k), c); break; }
  }
  const filled = (i, j, k) => i >= 0 && j >= 0 && k >= 0 && i < nx && j < ny && k < nz && id[I(i, j, k)] >= 0;
  const list = [];
  for (let k = 0; k < nz; k++) for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
    if (!filled(i, j, k)) continue;
    if (filled(i + 1, j, k) && filled(i - 1, j, k) && filled(i, j + 1, k) && filled(i, j - 1, k) && filled(i, j, k + 1) && filled(i, j, k - 1)) continue;
    list.push([i, j, k]);
  }
  const s = hM / (y1 - y0), cx0 = (x0 + x1) / 2, cz0 = (z0 + z1) / 2, cyC = (y0 + y1) / 2;
  const mesh = new THREE.InstancedMesh(_box, new THREE.MeshLambertMaterial({ color: '#ffffff' }), list.length);
  const m4 = new THREE.Matrix4(), col = new THREE.Color(), n = new THREE.Vector3();
  list.forEach(([i, j, k], idx) => {
    const X = x0 + (i + .5) * vs, Y = y0 + (j + .5) * vs, Z = z0 + (k + .5) * vs, q = I(i, j, k);
    const yM = o.center ? (cyC - Y) * s : (y1 - Y) * s;
    m4.makeScale(vs * s, vs * s, vs * s).setPosition((X - cx0) * s, yM, (Z - cz0) * s); mesh.setMatrixAt(idx, m4);
    let rgb = deco.get(q);
    if (!rgb) {
      const M = V.mats[P[id[q]][P[id[q]][0] === 'ell' ? 7 : 8]], R = M.ramp; n.set(nrm[q * 3], nrm[q * 3 + 1], nrm[q * 3 + 2]);
      let v = .42 + .58 * Math.max(0, n.dot(L)); if (M.noise) v += (hsh(i, j, k) - .5) * M.noise * 1.4;
      let ix = Math.max(0, Math.min(R.length - 1, Math.floor(v * (R.length - 1) + .35)));
      if (n.dot(RIM) > .72 && n.z < .55) ix = Math.min(R.length - 1, ix + 1);
      // a dark selout on the silhouette edge seen from the front
      if (!filled(i, j, k + 1) && (!filled(i - 1, j, k) || !filled(i + 1, j, k) || !filled(i, j - 1, k) || !filled(i, j + 1, k)) && n.z < .25) ix = Math.max(0, ix - 1);
      rgb = R[ix];
    }
    col.setRGB(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, THREE.SRGBColorSpace); mesh.setColorAt(idx, col);
  });
  mesh.instanceMatrix.needsUpdate = true; mesh.instanceColor.needsUpdate = true;
  mesh.castShadow = true; mesh.receiveShadow = true;
  const g = new THREE.Group(); g.add(mesh); g.userData.char = name; return g;
}
