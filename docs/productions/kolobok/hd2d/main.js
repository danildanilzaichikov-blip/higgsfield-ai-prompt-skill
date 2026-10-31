// «Колобок» — hd-2d style film: page contract, shot routing, tilt-shift, overlay
import * as THREE from 'three';
import { makePost } from './post_ts.js';
import { TL, loadSprites } from './cast.js';
import { drawOverlay, overlayReady, introReady, texts } from './ui.js';
import { seg, ss } from '/core/lib.js';

const W = 1920, H = 1080, Q = new URLSearchParams(location.search), SS = +(Q.get('ss') ?? 2);
await loadSprites();
const { buildWorld } = await import('./world.js');
const { buildInside } = await import('./inside.js');
const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(W, H);
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.getElementById('stage').appendChild(renderer.domElement);
const camera = new THREE.PerspectiveCamera(30, W / H, .3, 2000);
const sets = { world: buildWorld(), inside: buildInside() };
const SET_OF = id => (id === 'inside' ? 'inside' : 'world');
const post = makePost(renderer, sets.world.scene, camera, W, H, { ssaa: SS });
post.bloom.strength = .55; post.bloom.radius = .75; post.bloom.threshold = .85;
const V = post.vig.uniforms; V.amt.value = .55; V.warm.value = .1; V.contrast.value = .22; V.sat.value = 1.08;
await overlayReady(); await introReady();

const shotAt = t => TL.shots.find(s => t >= s.a && t < s.b) ?? TL.shots[TL.shots.length - 1];
const _v = new THREE.Vector3();
const toScreen = p => { _v.copy(p).project(camera); return [(_v.x * .5 + .5) * W, (-_v.y * .5 + .5) * H]; };
// fades: to black only into and out of the izba (a set change), and at both ends of the film
function fadeK(t) {
  let k = Math.min(ss(seg(t, 0, .8)), 1 - ss(seg(t, 59.0, 60)));
  for (const b of [8.57, 17.14]) k = Math.min(k, ss(Math.abs(t - b) / .35));
  for (const b of [22.86, 28.57, 34.29, 40.0]) k = Math.min(k, .35 + .65 * ss(Math.abs(t - b) / .3));
  return k;
}

window.DUR = TL.dur;
window.render = t => {
  const shot = shotAt(t), S = sets[SET_OF(shot.id)];
  post.dof.scene = S.scene; if (post.dof.ao) post.dof.ao.scene = S.scene;
  post.vig.uniforms.fade.value = 1; post.bloom.strength = .55; post.bloom.threshold = .85; V.warm.value = .1; V.sat.value = 1.08;
  const r = S.update(t, shot, camera, post, renderer);
  // tilt-shift band follows the subject's screen height
  camera.updateMatrixWorld(); _v.copy(r.subject).project(camera);
  post.dof.tiltAmt = 16; post.dof.tiltC = Math.min(.8, Math.max(.2, _v.y * .5 + .5)); post.dof.tiltW = .08; post.dof.tiltF = .3; post.dof.maxCoc = Math.max(post.dof.maxCoc, 22);
  if (shot.id === 'map' || (shot.id === 'night' && t > 55)) { post.dof.tiltC = .42; post.dof.tiltW = .1; }
  V.sat.value *= 1.12; V.contrast.value = .26;
  post.composer.render();
  const heads = S.heads(t), anchors = {};
  for (const k in heads) anchors[k] = toScreen(heads[k]);
  drawOverlay(t, anchors, fadeK(t));
};
window.TEXTS = t => { window.render(t); return texts(t); };
window.EV = [];
window.READY = true;
