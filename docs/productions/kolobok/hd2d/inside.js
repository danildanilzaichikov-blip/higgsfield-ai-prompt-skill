// Inside the izba, dollhouse cut: log walls, plank floor, whitewashed Russian stove with a live fire.
import * as THREE from 'three';
import { woodPlanks, plaster, glow, blob } from './px.js';
import { mat, mesh, box, mats, fire, windowQuad } from './kit.js';
import { particles, beamCard, flick } from './fx.js';
import { seg, ss, lerp, back } from '/core/lib.js';
import { sprite, voxKolobok, popScale } from './cast.js';
import * as RIG from './rigs.js';
import { path, yawOf, blendAngle } from './actors.js';

export function buildInside() {
  const scene = new THREE.Scene(); scene.fog = new THREE.FogExp2('#2a1a14', .02); scene.background = new THREE.Color('#120a08');
  const MM = mats();
  const logs = MM.log ?? mat(woodPlanks(96, 96, { pw: 8, len: 96, nails: false, seed: 31, cols: ['#3a2014', '#5e3820', '#84542e', '#a8743e', '#c89656'] }));
  const floor = mesh(new THREE.BoxGeometry(9, .2, 6).translate(0, -.1, -.5), MM.plank, { cast: false }); scene.add(floor);
  const back_ = mesh(new THREE.BoxGeometry(9, 4, .3).translate(0, 2, -3.4), logs); scene.add(back_);
  const left = mesh(new THREE.BoxGeometry(.3, 4, 6).translate(-4.4, 2, -.5), logs); scene.add(left);
  const win = windowQuad(1.0, 1.1); win.position.set(-1.8, 2.1, -3.23); scene.add(win);
  win.material = win.material.clone(); win.material.emissive.set('#cfe6ff'); win.material.emissiveIntensity = 1.6;
  // Russian stove: whitewashed block, step, chimney, arched mouth
  const white = mat(plaster(96, 96, { seed: 5, wall: ['#a8a29a', '#c8c2b8', '#e2ddd2', '#f4f0e6'], beams: [] }));
  const stove = new THREE.Group(); scene.add(stove); stove.position.set(1.9, 0, -1.6);
  stove.add(box(2.4, 2.0, 2.2, white)); const step = box(1.0, 1.2, 2.2, white); step.position.set(-1.6, 0, 0); stove.add(step);
  const chim = box(.8, 2.2, .8, white); chim.position.set(.5, 2.0, -.6); stove.add(chim);
  const mouth = new THREE.Mesh(new THREE.PlaneGeometry(.9, .7), new THREE.MeshBasicMaterial({ color: '#1a0c08' })); mouth.position.set(1.9, .75, -.48); scene.add(mouth);
  const arch = new THREE.Mesh(new THREE.CircleGeometry(.45, 16, 0, Math.PI), new THREE.MeshBasicMaterial({ color: '#1a0c08' })); arch.position.set(1.9, 1.1, -.48); scene.add(arch);
  const fl = fire(.7, { seed: 2, i: 3.4 }); fl.position.set(1.9, .42, -.55); scene.add(fl);
  const fireL = new THREE.PointLight('#ff9a40', 6, 9, 1.8); fireL.castShadow = true; fireL.shadow.mapSize.set(1024, 1024); fireL.shadow.bias = -.004; fireL.position.set(1.9, .9, .2); scene.add(fireL);
  const fGlow = glow('#ff9a40', 2.6, 1.2); fGlow.position.set(1.9, .8, -.3); scene.add(fGlow);
  const sparks = particles(40, (i, t, o) => { const ph = (t * .7 + i / 40) % 1; o.x = 1.9 + Math.sin(i * 3.1 + t * 2) * .25; o.y = .5 + ph * 1.2; o.z = -.35; o.a = (1 - ph) * 1.2; o.s = .04; o.r = 1; o.g = .7; o.b = .3; }, { soft: 1 });
  scene.add(sparks);
  // table, bowl, flour sack
  const table = box(1.8, .08, 1.0, MM.plank); table.position.set(-1.7, .8, -1.2); scene.add(table);
  for (const [x, z] of [[-2.5, -1.6], [-.9, -1.6], [-2.5, -.8], [-.9, -.8]]) { const l = box(.08, .8, .08, MM.beam); l.position.set(x, 0, z); scene.add(l); }
  const bowl = sprite('bowl', .32); bowl.position.set(-1.9, .88, -1.05); scene.add(bowl);
  const sack = sprite('sack', .55); sack.position.set(-1.2, .88, -1.3); scene.add(sack);
  // light: daylight through the window + warm hemisphere + front fill
  const day = new THREE.DirectionalLight('#dfeaff', 1.4); day.position.set(-3, 5, -6); day.castShadow = true; day.shadow.mapSize.set(2048, 2048); Object.assign(day.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6 }); scene.add(day);
  scene.add(new THREE.HemisphereLight('#f0d8b8', '#3a2418', .75));
  const fill = new THREE.PointLight('#ffe6c8', 1.4, 8, 2); fill.position.set(-.5, 2, 2.6); scene.add(fill);
  const beam = beamCard(5, .5, 1.6, '#e8f0ff', { k: .18 }); scene.add(beam);
  const dust = particles(60, (i, t, o) => { o.x = -1.8 + Math.sin(i + t * .3) * .6 + (i % 7) * .1; o.y = .6 + ((i * .37 + t * .05) % 1) * 1.6; o.z = -2.5 + (i % 5) * .45; o.a = .4 + .3 * Math.sin(t * 2 + i); o.s = .025; o.r = 1; o.g = .95; o.b = .85; }, { soft: 1 });
  scene.add(dust);
  // cast
  const BR = RIG.baba(), baba = BR.root, bp = path([[8.57, -4.4, .6], [10.1, -.6, -.2]]); scene.add(baba); const bs = blob(.45, .5); bs.position.set(-.6, .02, -.15); scene.add(bs);
  const K = voxKolobok(.55); scene.add(K.mesh); const ks = blob(.3, .5); scene.add(ks);

  function update(t, shot, cam, post, renderer) {
    const lt = t - shot.a, k = ss(seg(t, shot.a, shot.b));
    cam.fov = 30; cam.updateProjectionMatrix();
    cam.position.set(lerp(.6, 1.0, k), lerp(4.2, 3.0, k), lerp(7.2, 5.4, k)); cam.lookAt(lerp(.2, .9, k), 1.0, -1.0);
    // the flare: when kolobok bakes the fire swells and every shadow jumps
    const flare = Math.exp(-Math.max(0, t - 13.6) / .5) * (t >= 13.6 ? 1 : 0);
    const lvl = (1 + flare * 1.8) * flick(t, 1);
    fireL.intensity = 5.5 * Math.pow(lvl, 1.3); fGlow.material.color.set('#ff9a40').multiplyScalar(1.1 * lvl); fl.userData.update(t, cam, .9 + flare * .7);
    fireL.position.set(1.9 + Math.sin(t * 7) * .04, .9, .2);
    sparks.userData.update(t); dust.userData.update(t);
    beam.material.uniforms.t.value = t; beam.userData.aim(new THREE.Vector3(-1.8, 2.1, -3.1), new THREE.Vector3(.3, -.6, .75), cam);
    const P = bp(t), mv = P.v > .02; baba.position.set(P.x, 0, P.z); bs.position.set(P.x, .02, P.z + .05);
    baba.rotation.y = mv ? yawOf(P.dir, false) : blendAngle(yawOf(P.dir ?? Math.PI / 2, false), .35, ss(seg(t, P.tStop, P.tStop + .5)));
    BR.pose({ t, phase: P.d / BR.stride, moving: mv ? Math.min(1, P.v * 1.4 + .3) : 0, nod: t > 13.6 && t < 15 ? .6 : 0 });
    const kv = t >= 13.6; K.mesh.visible = kv; ks.visible = kv;
    if (kv) { const s = back(seg(t, 13.6, 14.2), 2.6); K.mesh.scale.setScalar(Math.max(.01, s)); const x = lerp(1.9, 1.2, ss(seg(t, 14.4, 15.4))), y = .55 + Math.sin(Math.PI * seg(t, 14.4, 15.4)) * .5 - ss(seg(t, 14.4, 15.4)) * .27; K.mesh.position.set(x, y, -.2); K.set(-ss(seg(t, 14.4, 15.4)) * 5); ks.position.set(x, .02, -.15); }
    post.dof.focus = cam.position.distanceTo(new THREE.Vector3(.6, 1, -.6)); post.dof.aper = 300; post.dof.maxCoc = 18;
    post.vig.uniforms.warm.value = .32; renderer.toneMappingExposure = 1.15;
    return { subject: new THREE.Vector3(.6, 1, -.6) };
  }
  function heads(t) { return { baba: new THREE.Vector3(-.6, 1.85, -.2), kolobok: new THREE.Vector3(1.4, 1.1, -.2) }; }
  return { scene, update, heads };
}
