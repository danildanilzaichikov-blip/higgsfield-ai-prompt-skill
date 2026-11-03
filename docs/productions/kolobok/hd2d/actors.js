// Where every creature walks: piecewise paths with eased segments; gait phase comes from the
// distance actually travelled, so feet never slide. Heading follows the motion, then a rest facing.
import * as THREE from 'three';
import { seg, ss, lerp } from '/core/lib.js';

export function path(keys, o = {}) {
  // keys: [[t, x, z], ...]; between consecutive keys the actor moves (eased), otherwise holds
  const segs = []; let acc = 0;
  for (let i = 0; i + 1 < keys.length; i++) { const [ta, xa, za] = keys[i], [tb, xb, zb] = keys[i + 1]; const len = Math.hypot(xb - xa, zb - za); segs.push({ ta, tb, xa, za, xb, zb, len, d0: acc }); acc += len; }
  function at(t) {
    if (t <= keys[0][0]) return { x: keys[0][1], z: keys[0][2], d: 0, v: 0, dir: segs[0] ? Math.atan2(segs[0].zb - segs[0].za, segs[0].xb - segs[0].xa) : 0 };
    let last = null;
    for (const s of segs) {
      if (t < s.ta) break;
      if (t <= s.tb && s.len > .01) { const k = s.tb > s.ta ? seg(t, s.ta, s.tb) : 1, e = o.linear ? k : ss(k), v = s.len > .01 ? (o.linear ? 1 : 6 * k * (1 - k)) : 0;
        return { x: lerp(s.xa, s.xb, e), z: lerp(s.za, s.zb, e), d: s.d0 + s.len * e, v: Math.min(1, v * 1.5), dir: Math.atan2(s.zb - s.za, s.xb - s.xa), moving: s.len > .01 }; }
      last = s;
    }
    let lastMoving = null, next = null; for (const s of segs) { if (s.tb <= t && s.len > .01) lastMoving = s; if (!next && s.ta >= t && s.len > .01) next = s; }
    let hold = keys[0]; for (const kk of keys) if (kk[0] <= t) hold = kk;
    const dd = lastMoving ? lastMoving.d0 + lastMoving.len : 0;
    return { x: hold[1], z: hold[2], d: dd, v: 0, dir: lastMoving ? Math.atan2(lastMoving.zb - lastMoving.za, lastMoving.xb - lastMoving.xa) : null,
      tStop: lastMoving ? lastMoving.tb : -9, nextDir: next ? Math.atan2(next.zb - next.za, next.xb - next.xa) : null, tNext: next ? next.ta : 1e9 };
  }
  return at;
}
// heading for a model that faces +x (quadrupeds) or +z (people): blend to a rest facing when still
export function yawOf(dir, faceX) { return faceX ? -dir : Math.PI / 2 - dir; }
export function blendAngle(a, b, k) { let d = ((b - a + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI; return a + d * k; }
