// The road diorama: yard with the izba → birch grove → spruce wood → thicket → sunset glade, one table.
import * as THREE from 'three';
import { PX, ramp, h2, fbm, ground, woodPlanks, shingles, billboard, glow, blob, texOf } from './px.js';
import { mat, mesh, box, mats, house } from './kit.js';
import { sky, stars, particles, beamCard, flick } from './fx.js';
import { track, seg, ss, lerp, clamp } from '/core/lib.js';
import { TL, sprite, voxKolobok, popScale, kolobokPath, FOXNOSE } from './cast.js';
import * as RIG from './rigs.js';
import { path, yawOf, blendAngle } from './actors.js';

const C = c => new THREE.Color(c);

// lighting moods; each shot picks one, the road crossfades between neighbours
const MOOD = {
  morning: { sun: '#fff0d4', si: 2.3, sd: [-.55, .8, .55], hs: '#bcd6ff', hg: '#5f6d3a', hi: 1.0, fog: '#d4e4ef', fd: .010, top: '#4f86d6', mid: '#93bdee', hor: '#e6f0f2', exp: 1.0, st: 0 },
  noon: { sun: '#fffbe8', si: 2.6, sd: [-.3, .9, .4], hs: '#c4e0ff', hg: '#5d7a3a', hi: 1.05, fog: '#dcecd6', fd: .012, top: '#4a8ae0', mid: '#a0cdf2', hor: '#eef6ea', exp: 1.0, st: 0 },
  spruce: { sun: '#e2f0ff', si: 1.5, sd: [-.4, .85, .3], hs: '#9cc6cc', hg: '#2d4630', hi: .95, fog: '#a8c8c2', fd: .032, top: '#6a9ab8', mid: '#a8c8cc', hor: '#cfe0da', exp: 1.08, st: 0 },
  thicket: { sun: '#c8dca8', si: 1.0, sd: [-.2, .9, .2], hs: '#6f9478', hg: '#1c2a1c', hi: .85, fog: '#4c6c5a', fd: .045, top: '#2c4a44', mid: '#4f7464', hor: '#7a9a80', exp: 1.18, st: 0 },
  sunset: { sun: '#ffa868', si: 2.6, sd: [.85, .28, -.55], hs: '#ffb8a2', hg: '#4a3434', hi: .9, fog: '#e8a07c', fd: .018, top: '#3c4a9c', mid: '#e08878', hor: '#ffcf8a', exp: 1.05, st: 0 },
  night: { sun: '#a8bcff', si: 1.6, sd: [-.3, .8, .4], hs: '#4a5c9c', hg: '#141428', hi: 1.6, fog: '#1c2848', fd: .016, top: '#070c22', mid: '#16224a', hor: '#33466a', exp: 1.6, st: 1 },
};
function mood(t) {
  const K = [[0, 'morning'], [21.5, 'morning'], [22.9, 'noon'], [28.5, 'noon'], [28.6, 'spruce'], [34.2, 'spruce'], [34.3, 'thicket'], [39.9, 'thicket'], [40.0, 'sunset'], [51.4, 'sunset'], [53.5, 'night']];
  let i = 0; while (i < K.length - 1 && t >= K[i + 1][0]) i++;
  const a = MOOD[K[i][1]], b = MOOD[K[Math.min(i + 1, K.length - 1)][1]], k = i < K.length - 1 ? ss(seg(t, K[i][0], K[i + 1][0])) : 0;
  const o = {};
  for (const key in a) {
    if (typeof a[key] === 'string') o[key] = C(a[key]).lerp(C(b[key]), k);
    else if (Array.isArray(a[key])) o[key] = new THREE.Vector3(...a[key]).lerp(new THREE.Vector3(...b[key]), k).normalize();
    else o[key] = lerp(a[key], b[key], k);
  }
  return o;
}

function groundTex(seed, grass, dirt, maskF) { return ground(192, 192, { seed, grass, dirt, mask: maskF }); }

export function buildWorld() {
  const scene = new THREE.Scene(); scene.fog = new THREE.FogExp2('#d4e4ef', .01);
  const SK = sky({ top: '#4f86d6', mid: '#93bdee', hor: '#e6f0f2', moonI: 0 }); scene.add(SK.mesh);
  const ST = stars(500, 7); scene.add(ST);
  const sun = new THREE.DirectionalLight('#fff0d4', 2.3); sun.castShadow = true; sun.shadow.mapSize.set(4096, 4096);
  Object.assign(sun.shadow.camera, { left: -16, right: 16, top: 16, bottom: -16, near: 1, far: 120 }); sun.shadow.bias = -.0006; sun.shadow.normalBias = .02;
  scene.add(sun, sun.target);
  const hemi = new THREE.HemisphereLight('#bcd6ff', '#5f6d3a', 1); scene.add(hemi);
  const fill = new THREE.PointLight('#dfe8ff', 1.2, 9, 2); scene.add(fill);   // front fill: billboards only have a front normal

  // —— ground: one long table, grass tone per biome, a dirt road along z≈0 ——
  const G = {
    yard: groundTex(13, ['#2a4a22', '#3c6a2e', '#55893a', '#76a84a', '#9cc860'], ['#4a3624', '#6a4e32', '#8a6a44', '#a8885a']),
    birch: groundTex(14, ['#2e5224', '#457a30', '#62a03c', '#86c050', '#b2dc6a'], ['#4a3624', '#6a4e32', '#8a6a44', '#a8885a']),
    spruce: groundTex(15, ['#13261c', '#1d3a26', '#2a5032', '#3c6a3e', '#55864c'], ['#2a2018', '#3e3024', '#5a4632', '#745c42']),
    thicket: groundTex(16, ['#0f1c14', '#18291c', '#243c26', '#355232', '#4a6a40'], ['#22180f', '#34261a', '#4a3826', '#604a34']),
    glade: groundTex(17, ['#4a4a1c', '#6a6a26', '#8e8a34', '#b4a846', '#d8c860'], ['#4a3624', '#6a4e32', '#8a6a44', '#a8885a']),
  };
  const strips = [['yard', -60, 9], ['birch', 9, 26], ['spruce', 26, 42], ['thicket', 42, 58], ['glade', 58, 130]];
  for (const [k, x0, x1] of strips) {
    const m = mat(G[k]); const g = new THREE.BoxGeometry(x1 - x0, .4, 120); g.translate((x0 + x1) / 2, -.2, -20);
    const me = mesh(g, m, { cast: false }); scene.add(me);
  }
  const roadC = ground(96, 96, { seed: 21, mask: () => -.4, dirt: ['#5a4430', '#7a6044', '#9a7c58', '#b89a70'] });
  const road = mesh(new THREE.BoxGeometry(100, .02, 2.2).translate(36, .011, .2), mat(roadC), { cast: false }); scene.add(road);

  // —— izba (log walls, plank roof, white carved frames, blue shutters) ——
  const MM = mats();
  if (!MM.log) {
    MM.log = mat(woodPlanks(96, 96, { pw: 8, len: 96, nails: false, seed: 31, cols: ['#3a2014', '#5e3820', '#84542e', '#a8743e', '#c89656'] }));
    MM.white = mat(woodPlanks(24, 24, { pw: 24, len: 96, nails: false, seed: 2, cols: ['#a8a4a0', '#d8d4cc', '#f2eee6', '#ffffff'] }));
    MM.shutter = mat(woodPlanks(24, 24, { pw: 4, len: 96, nails: false, seed: 3, cols: ['#1a2a5a', '#2a4488', '#3e62b4', '#5a84d4'] }));
  }
  const IZ = { x: 0, z: -4.5, w: 6, d: 4, h: 2.6 };
  const hut = house({ x: IZ.x, z: IZ.z, w: IZ.w, d: IZ.d, h: IZ.h, wall: 'log', roof: 'roof3', windows: [[-1.5, 1.4], [1.5, 1.4]], door: .001 });
  scene.add(hut);
  for (const wx of [-1.5, 1.5]) {
    const fz = IZ.z + IZ.d / 2;
    const top = box(1.3, .14, .12, MM.white); top.position.set(wx, 2.0, fz + .08); hut.parent ? 0 : 0; scene.add(top);
    const crown = new THREE.Mesh(new THREE.ConeGeometry(.55, .32, 3), MM.white); crown.rotation.z = 0; crown.position.set(wx, 2.25, fz + .1); crown.scale.z = .2; scene.add(crown);
    for (const s of [-1, 1]) { const sh = box(.32, 1.15, .06, MM.shutter); sh.position.set(wx + s * .62, .83, fz + .08); scene.add(sh); }
    const sill = box(1.2, .1, .4, MM.white); sill.position.set(wx, .76, fz + .16); scene.add(sill);
  }
  const winLight = new THREE.PointLight('#ffc070', 0, 9, 2); winLight.position.set(0, 1.4, IZ.z + IZ.d / 2 + 1.2); scene.add(winLight);
  const winGlow = [-1.5, 1.5].map(wx => { const g = glow('#ffb860', 2.2, 0); g.position.set(wx, 1.4, IZ.z + IZ.d / 2 + .1); scene.add(g); return g; });
  // fence, porch steps, sunflowers
  for (let i = 0; i < 14; i++) { const p = box(.14, 1.0 + (i % 2) * .1, .08, MM.plank); p.position.set(-9 + i * .32, 0, -1.6); scene.add(p); }
  const rail = box(4.6, .1, .06, MM.plank); rail.position.set(-6.9, .7, -1.58); scene.add(rail);

  // —— forest: tree rows at several depths, understory along the road ——
  const BB = [];
  const put = (name, x, z, hM, o = {}) => { const b = sprite(name, hM, o); b.position.set(x, o.y ?? 0, z); scene.add(b); BB.push(b); if (!o.noBlob) { const s = blob(hM * .18, .35); s.position.set(x, .02, z + .05); scene.add(s); } return b; };
  const H = (i, s) => h2(i, s, 9);
  const AVOID = [16.75, 32.75, 48.75, 64.75];
  const rows = (kind, n, x0, x1, z0, z1, h0, h1, seed, o = {}) => { for (let i = 0; i < n; i++) if (!(z0 > 2 && AVOID.some(c => Math.abs(x0 + (x1 - x0) * (i + H(i, seed)) / n - c) < 4.2))) put(kind + (i % (o.v ?? 4)), x0 + (x1 - x0) * (i + H(i, seed)) / n, z0 + (z1 - z0) * H(i, seed + 1), h0 + (h1 - h0) * H(i, seed + 2), o); };
  // yard
  [[-11, -6], [-8.5, -8], [6.5, -7], [8.8, -5.5], [-13, -10], [4.5, -11]].forEach(([x, z], i) => put('birch' + (i % 4), x, z, 6.2));
  rows('tree', 6, -16, 8, -16, -12, 5, 7, 3, { v: 2 });
  [[-5.2, -1.3], [-4.6, -1.4], [-4.0, -1.3], [3.6, -2.0], [4.2, -2.1]].forEach(([x, z]) => put('sunflower', x, z, 1.5));
  // birch grove
  rows('birch', 18, 9.5, 26, -9, -3, 5.6, 7.6, 11); rows('birch', 14, 9.5, 26, -17, -10, 6, 8, 12); rows('birch', 5, 10, 25.5, 4.3, 5.2, 7, 8, 13);
  // spruce wood
  rows('spruce', 18, 26.2, 42, -9, -2.8, 5.5, 8.5, 21); rows('spruce', 16, 26.2, 42, -18, -10, 7, 9.5, 22); rows('spruce', 5, 27, 41, 4.0, 5.0, 8, 9.5, 23);
  [[29.5, -1.6], [36.5, -1.4], [38.2, 1.6], [27.8, 1.9], [40.5, -1.8]].forEach(([x, z]) => put('mushroom', x, z, .45));
  // thicket
  rows('oak', 16, 42.2, 58, -9, -3, 6.5, 8.8, 31, { v: 3 }); rows('oak', 12, 42.2, 58, -17, -10, 7, 9.5, 32, { v: 3 }); [43.2, 54.5].forEach((x, i) => put('oak' + i, x, 4.6, 8));
  [[45, -1.6], [55.5, -1.5], [52, 2.2]].forEach(([x, z]) => put('berrybush', x, z, 1.1));
  put('hive', 52.6, -2.4, .9, { y: 2.2, noBlob: 1 });
  // glade ring
  rows('birch', 9, 58.5, 82, -9, -4.5, 6, 7.5, 41); rows('tree', 8, 58.5, 82, -16, -10, 6, 8, 42, { v: 2 }); [[60, 3.8], [72.5, 4.2]].forEach(([x, z]) => put('tree' + (x > 70 ? 1 : 0), x, z, 7));
  // understory scattered along both road edges
  const under = ['fern0', 'fern1', 'fern2', 'tuft0', 'tuft1', 'tuft2', 'flowers0', 'flowers1', 'flowers2', 'flowers3', 'rock0', 'rock1', 'rock2'];
  for (let i = 0; i < 260; i++) {
    const x = -10 + i * .33 + H(i, 50) * .3, side = i % 2 ? 1 : -1, z = side > 0 ? 1.5 + H(i, 51) * 2.6 : -1.45 - H(i, 51) * 4.5;
    if (x > -3 && x < 3 && z < 0) continue;                                     // keep the izba yard clear
    const biome = x < 9 ? 0 : x < 26 ? 1 : x < 42 ? 2 : x < 58 ? 3 : 4;
    const pool = [[6, 7, 8, 9, 3, 4], [6, 8, 9, 3, 4, 5, 0], [0, 1, 2, 3, 10, 11], [0, 1, 2, 11, 12, 5], [6, 7, 8, 9, 3, 4, 5]][biome];
    const name = under[pool[Math.floor(H(i, 52) * pool.length)]];
    put(name, x, z, name.startsWith('rock') ? .4 + H(i, 53) * .3 : name.startsWith('fern') ? .7 + H(i, 53) * .4 : .35 + H(i, 53) * .25, { noBlob: 1, shadow: false });
  }
  const stump = new THREE.Mesh(new THREE.CylinderGeometry(.45, .55, .55, 10).translate(0, .27, 0), MM.log); stump.position.set(69.5, 0, -1.6); stump.castShadow = true; scene.add(stump);
  const log = new THREE.Mesh(new THREE.CylinderGeometry(.3, .3, 3.2, 10), MM.log); log.rotation.z = Math.PI / 2; log.position.set(47.5, .3, -2.2); log.castShadow = true; scene.add(log);
  const log2 = new THREE.Mesh(new THREE.CylinderGeometry(.25, .25, 2.4, 10), MM.log); log2.rotation.z = Math.PI / 2; log2.rotation.y = .3; log2.position.set(31.2, .25, -1.9); log2.castShadow = true; scene.add(log2);

  // —— cast: articulated voxel creatures that walk in and out ——
  const E = TL.enc;
  const A = {
    ded: { rig: RIG.ded(), quad: false, rest: 0, vis: [2.9, 9], p: path([[3.0, 0, -2.3], [4.2, -1.9, -.7]]) },
    baba: { rig: RIG.baba(), quad: false, rest: 0, vis: [3.3, 9], p: path([[3.4, .3, -2.3], [4.6, -.6, -.5]]) },
    hare: { rig: RIG.hare(), quad: true, rest: Math.PI, vis: [22, 28.6], p: path([[22.4, E.hare[0] + 1.6, -7.5], [23.7, E.hare[0], .3], [27.3, E.hare[0], .3], [28.6, E.hare[0] + 1.8, -7]]) },
    wolf: { rig: RIG.wolf(), quad: true, rest: Math.PI, vis: [28, 34.3], p: path([[28.0, E.wolf[0] + 2.6, -8], [29.6, E.wolf[0], .3], [33.0, E.wolf[0], .3], [34.3, E.wolf[0] + 3, -7.5]]) },
    bear: { rig: RIG.bear(), quad: true, rest: Math.PI, vis: [33.6, 40], p: path([[33.6, E.bear[0] + 3, -8], [35.3, E.bear[0], .2], [38.5, E.bear[0], .2], [40.0, E.bear[0] + 3, -7.5]]) },
    fox: { rig: RIG.fox(), quad: true, rest: Math.PI, vis: [39.9, 56], p: path([[39.9, E.fox[0] + 3, -6], [41.7, E.fox[0], .35], [51.7, E.fox[0], .35], [54.6, E.fox[0] + 3.2, -7.5]]) },
    deer: { rig: RIG.deer(), quad: true, rest: Math.PI * .85, vis: [40, 60], p: path([[40, 75, -7.2], [44, 75, -7.2], [47, 73.5, -6.8]]) },
    squir: { rig: RIG.squirrel(), quad: true, rest: Math.PI * .6, vis: [28.5, 32], p: path([[28.5, 31.4, -1.9], [30.6, 31.4, -1.9], [31.8, 32.6, -6.5]]), y: .48 },
    hedge: { rig: RIG.hedgehog(), quad: true, rest: 0, vis: [34.2, 40.1], p: path([[34.2, 45.6, -3.4], [40.0, 46.6, -.9]], { linear: 1 }) },
    owl: { rig: RIG.owl(), quad: false, rest: 0, vis: [34.2, 40.1], p: path([[34, 47.2, -2.2]]), y: .58 },
  };
  for (const k in A) { const a = A[k]; scene.add(a.rig.root); a.blob = blob(k === 'bear' ? .9 : k === 'wolf' || k === 'deer' ? .7 : .4, .4); scene.add(a.blob); }
  const birds = []; for (let i = 0; i < 14; i++) { const b = RIG.bird(i % 3 ? 'feather' : 'bear'); scene.add(b.root); birds.push(b); }
  const flies2 = []; for (let i = 0; i < 8; i++) { const b = RIG.butterfly(['wingB', 'wingY', 'petalR'][i % 3] === 'petalR' ? 'red' : ['wingB', 'wingY', 'wingY'][i % 3]); scene.add(b.root); flies2.push(b); }
  const K = voxKolobok(.55); scene.add(K.mesh); const kShadow = blob(.3, .45); scene.add(kShadow);
  const sparks = particles(60, (i, t, o) => {
    // pop sparkles around whoever just appeared (set by update)
    const p = sparkState; const k = clamp((t - p.t0) / .9); const a = i / 60 * 6.283 + h2(i, 1, 1) * .4;
    const r = .2 + k * (1.2 + h2(i, 2, 1) * .8); o.x = p.x + Math.cos(a) * r * .8; o.y = p.y + Math.sin(a) * r * .6 + k * .3; o.z = p.z + .2;
    o.a = (k > 0 && k < 1) ? (1 - k) * 1.4 : 0; o.s = .05 + .04 * h2(i, 3, 1); o.r = 1; o.g = .9; o.b = .55;
  }, { soft: 1 });
  const sparkState = { t0: -9, x: 0, y: 0, z: 0 }; scene.add(sparks);

  // —— atmosphere ——
  const leaves = particles(70, (i, t, o) => { const ph = (t * .12 + h2(i, 1, 4)) % 1; o.x = 9 + h2(i, 2, 4) * 18 + Math.sin(t * 1.3 + i) * .6; o.y = 6 * (1 - ph); o.z = -4 + h2(i, 3, 4) * 7; o.a = .9; o.s = .045; o.r = .85; o.g = .85; o.b = .3; });
  const flies = particles(90, (i, t, o) => { o.x = 42 + h2(i, 1, 5) * 16 + Math.sin(t * .6 + i) * .5; o.y = .4 + h2(i, 2, 5) * 2.2 + Math.sin(t * 1.1 + i * 2) * .2; o.z = -4 + h2(i, 3, 5) * 7; o.a = .6 + .6 * Math.sin(t * 3 + i * 1.7); o.s = .05; o.r = .8; o.g = 1; o.b = .45; }, { soft: 1 });
  const seeds = particles(60, (i, t, o) => { const ph = (t * .05 + h2(i, 1, 6)) % 1; o.x = 58 + h2(i, 2, 6) * 18 + ph * 4; o.y = .3 + ph * 4 + Math.sin(t * 2 + i) * .1; o.z = -3 + h2(i, 3, 6) * 6; o.a = .9; o.s = .04; o.r = 1; o.g = .95; o.b = .85; }, { soft: 1 });
  const nightFlies = particles(70, (i, t, o) => { o.x = -8 + h2(i, 1, 7) * 80; o.y = .3 + h2(i, 2, 7) * 1.8 + Math.sin(t * 1.3 + i) * .15; o.z = -5 + h2(i, 3, 7) * 9; o.a = .5 + .6 * Math.sin(t * 2.6 + i * 1.3); o.s = .06; o.r = .85; o.g = 1; o.b = .5; }, { soft: 1 });
  scene.add(leaves, flies, seeds, nightFlies);
  const sunGlow = glow('#ffcc88', 26, .0); scene.add(sunGlow);
  const rays = [0, 1, 2].map(i => { const b = beamCard(16, 1.2, 4, '#ffd8a0', { k: 0 }); scene.add(b); return b; });

  const _v = new THREE.Vector3();
  function update(t, shot, cam, post, renderer) {
    const M = mood(t);
    sun.color.copy(M.sun); sun.intensity = M.si; hemi.color.copy(M.hs); hemi.groundColor.copy(M.hg); hemi.intensity = M.hi;
    scene.fog.color.copy(M.fog); scene.fog.density = M.fd; SK.u.top.value.copy(M.top); SK.u.mid.value.copy(M.mid); SK.u.hor.value.copy(M.hor);
    SK.u.moonI.value = M.st; SK.u.moonDir.value.set(.5, .5, -1).normalize(); ST.material.uniforms.t.value = t; ST.material.uniforms.k.value = M.st; ST.visible = M.st > .02;
    renderer.toneMappingExposure = M.exp;

    // —— kolobok ——
    const kp = kolobokPath(t); K.mesh.visible = kp.vis; kShadow.visible = kp.vis && kp.y < .3;
    if (kp.vis) { K.set(kp.ang); K.mesh.position.set(kp.x, kp.y, kp.z); kShadow.position.set(kp.x, .02, kp.z + .03); kShadow.scale.setScalar(1 - Math.min(.6, kp.y * .4)); }

    // —— creatures ——
    for (const k in A) {
      const a = A[k], on = t >= a.vis[0] && t <= a.vis[1]; a.rig.root.visible = on; a.blob.visible = on; if (!on) continue;
      const p = a.p(t), moving = p.v > .02;
      let yaw;
      if (moving) yaw = yawOf(p.dir, a.quad);
      else { const restYaw = a.rest, prev = p.dir == null ? restYaw : yawOf(p.dir, a.quad);
        yaw = t > p.tNext - .45 && p.nextDir != null ? blendAngle(restYaw, yawOf(p.nextDir, a.quad), ss(seg(t, p.tNext - .45, p.tNext))) : blendAngle(prev, restYaw, ss(seg(t, p.tStop, p.tStop + .5))); }
      a.rig.root.position.set(p.x, a.y ?? 0, p.z); a.rig.root.rotation.y = yaw;
      const S = { t, phase: p.d / (a.rig.stride ?? 1), moving: moving ? Math.min(1, p.v * 1.4 + .3) : 0, look: 0 };
      if (k === 'bear') S.rear = ss(seg(t, 35.5, 36.2)) * (1 - ss(seg(t, 37.8, 38.4)));
      if (k === 'fox') S.sit = ss(seg(t, 42.0, 42.6)) * (1 - ss(seg(t, 51.0, 51.6)));
      if (k === 'deer') S.nod = t < 43 || t > 45.5 ? 1 : 0;
      if (k === 'hare' && !moving) S.look = Math.sin(t * 2) * .15;
      if (k === 'ded' && t > 5.0 && t < 8.4) S.wave = ss(seg(t, 5.0, 5.4)) * (1 - ss(seg(t, 7.8, 8.4)));
      a.rig.pose(S);
      a.blob.position.set(p.x, .02, p.z + .03);
    }
    A.fox.rig.root.updateMatrixWorld(true); if (t < 47.6) { A.fox.rig.root.userData.nose.getWorldPosition(_v); FOXNOSE.x = _v.x; FOXNOSE.y = _v.y; FOXNOSE.z = _v.z; }
    // birds: flocks crossing the sky in the yard, the birches and the sunset glade
    const flock = t < 8.6 ? [-14, 7, -8, 2.6] : t > 22.8 && t < 28.6 ? [8, 7.5, -9, 2.8] : t > 40 && t < 48.6 ? [56, 6.5, -10, 2.4] : null;
    birds.forEach((b, i) => { b.root.visible = !!flock; if (!flock) return; const t0 = t < 8.6 ? 0 : t < 30 ? 22.8 : 40;
      b.root.position.set(flock[0] + (t - t0) * flock[3] + (i % 5) * -.9, flock[1] + Math.sin(t * 2 + i) * .25 + (i % 3) * .5, flock[2] + (i % 4) * 1.2); b.root.rotation.y = 0; b.pose({ t, seed: i }); });
    flies2.forEach((b, i) => { const yardB = i < 4, on = yardB ? t < 8.6 : t > 40 && t < 51.5; b.root.visible = on; if (!on) return;
      const c = yardB ? [-4.6 + (i % 2) * 8, 1.0, -1.0] : [61 + i * 1.2, .8, 1.2];
      b.root.position.set(c[0] + Math.sin(t * 1.3 + i * 2) * 1.1, c[1] + Math.sin(t * 2.3 + i) * .35, c[2] + Math.cos(t * 1.1 + i) * .7); b.root.rotation.y = Math.atan2(-Math.cos(t * 1.3 + i * 2), -Math.sin(t * 1.1 + i)) ; b.pose({ t, seed: i }); });
    if (t >= 20.0 && t < 21) { sparkState.t0 = 20.0; sparkState.x = 1.5; sparkState.y = 1.1; sparkState.z = -2.2; }
    sparks.userData.update(t);
    // —— camera ——
    const cp = camPath(t, shot); cam.fov = cp.fov; cam.updateProjectionMatrix(); cam.position.copy(cp.p); cam.lookAt(cp.l);
    fill.position.copy(cp.l).add(new THREE.Vector3(.3, 1.6, 2.4)); fill.intensity = shot.id === 'night' ? .5 : 1.1;
    sun.position.copy(cp.l).addScaledVector(M.sd, 40); sun.target.position.copy(cp.l); sun.target.updateMatrixWorld();

    // —— practicals ——
    const nightK = M.st; winLight.intensity = nightK * 4 * flick(t, 2); winGlow.forEach(g => g.material.color.set('#ffb860').multiplyScalar(nightK * 1.4));
    hut.userData.windows.forEach(w => { w.material.emissiveIntensity = .15 + nightK * 2.4; });
    sunGlow.visible = shot.id === 'glade'; sunGlow.position.set(cp.l.x + 34, 6, -40); sunGlow.material.color.set('#ffb070').multiplyScalar(.9);
    rays.forEach((r, i) => { const on = shot.id === 'glade' ? 1 : 0; r.material.uniforms.k.value = .12 * on; r.material.uniforms.t.value = t; r.userData.aim(new THREE.Vector3(cp.l.x + 12 + i * 2.5, 8, -10), new THREE.Vector3(-.75, -.5, .45), cam); r.visible = on > 0; });
    leaves.visible = t < 28.6 && t > 21; flies.visible = shot.id === 'bear'; seeds.visible = shot.id === 'glade'; nightFlies.visible = nightK > .3;
    for (const p of [leaves, flies, seeds, nightFlies]) if (p.visible) p.userData.update(t);

    // —— focus: on kolobok or the speaker, tilt band follows ——
    const subj = cp.focus; post.dof.focus = cam.position.distanceTo(subj); post.dof.aper = cp.aper ?? 260; post.dof.maxCoc = 18;
    post.vig.uniforms.warm.value = shot.id === 'glade' ? .3 : .1;
    return { subject: subj };
  }

  // anchors for speech bubbles (world positions of heads)
  function heads(t) {
    const kp = kolobokPath(t), o = {};
    for (const k of ['ded', 'baba', 'hare', 'wolf', 'bear', 'fox']) { A[k].rig.root.updateMatrixWorld(true); const v = new THREE.Vector3(); A[k].rig.root.userData.head.getWorldPosition(v); v.y += k === 'bear' ? .55 : k === 'hare' ? .45 : .35; o[k] = v; }
    o.kolobok = new THREE.Vector3(kp.x, kp.y + .65, kp.z); return o;
  }
  return { scene, update, heads };
}

// —— camera paths (high 3/4 throughout; dives on the window and the fox) ——
const V3 = (x, y, z) => new THREE.Vector3(x, y, z);
function enc(name, t, a, b) {
  const ax = TL.enc[name][0], c = ax - 1.25, k = ss(seg(t, a, b)), f = name === 'bear' ? 1.3 : 1;
  return { p: V3(c + .9 - k * .7, (4.4 - k * .4) * f, (7.6 - k * .6) * f), l: V3(c, .75 * f, 0), fov: 30 };
}
export function camPath(t, shot) {
  const kp = kolobokPath(t);
  let r;
  if (shot.id === 'map') { const k = ss(seg(t, 0, 3.43)); r = { p: V3(lerp(30, 3, k), lerp(40, 10, k), lerp(52, 17, k)), l: V3(lerp(32, 0, k), 0, lerp(-3, -3, k)), fov: 32, focus: V3(lerp(30, 0, k), 0, -3), aper: 60 }; }
  else if (shot.id === 'yard') { const k = ss(seg(t, 3.43, 8.57)); r = { p: V3(lerp(1.0, -.2, k), lerp(5.8, 5.0, k), lerp(10.5, 9.2, k)), l: V3(-.6, 1.0, -1.2), fov: 30, focus: V3(-1.2, 1, -.6) }; }
  else if (shot.id === 'window') {
    if (t < 20.3) { const k = ss(seg(t, 17.14, 20.3)); r = { p: V3(lerp(3.3, 2.7, k), lerp(2.2, 1.7, k), lerp(1.8, 1.0, k)), l: V3(1.5, 1.0, -2.2), fov: 30, focus: V3(1.5, 1.0, -2.2), aper: 420 }; }
    else { const k = ss(seg(t, 20.3, 22.6)); const fx = Math.max(2.6, kp.x); r = { p: V3(lerp(2.7, fx + .9, k), lerp(1.7, 4.8, k), lerp(1.0, 8.2, k)), l: V3(lerp(1.5, fx, k), lerp(1.0, .5, k), lerp(-2.2, 0, k)), fov: 30, focus: V3(kp.x, kp.y + .3, kp.z) }; }
  }
  else if (shot.id === 'hare') r = enc('hare', t, 22.86, 28.57);
  else if (shot.id === 'wolf') r = enc('wolf', t, 28.57, 34.29);
  else if (shot.id === 'bear') r = enc('bear', t, 34.29, 40.0);
  else if (shot.id === 'glade') {
    const fx = TL.enc.fox[0];
    if (t < 46.3) { const k = ss(seg(t, 40, 46.3)); r = { p: V3(fx - 1.2 + .8 - k * .5, 4.2 - k * .7, 7.4 - k * 1.1), l: V3(fx - 1.3, .75, 0), fov: 30 }; }
    else { const k = ss(seg(t, 46.3, 48.4)), k2 = ss(seg(t, 48.6, 51.43)); r = { p: V3(lerp(fx - .9, fx - 1.6, k), lerp(3.5, 1.5, k) + k2 * .2, lerp(6.3, 3.6, k) - k2 * .3), l: V3(lerp(fx - 1.3, fx - .45, k), lerp(.75, .85, k), lerp(0, .3, k)), fov: 30, focus: V3(fx - .4, .85, .35), aper: 380 }; }
  }
  else { const k = ss(seg(t, 51.43, 59.5)); const fx = TL.enc.fox[0]; r = { p: V3(lerp(fx - 1.6, 30, k), lerp(1.7, 36, k), lerp(3.3, 50, k)), l: V3(lerp(fx - .45, 4, k), lerp(.85, 0, k), lerp(.3, -3, k)), fov: 32, focus: k < .5 ? V3(fx - .45, .85, .35) : V3(0, 1.4, -2.4), aper: lerp(380, 60, k) }; }
  if (!r.focus) r.focus = kp.vis ? V3(kp.x, kp.y + .3, kp.z) : r.l;
  return r;
}
