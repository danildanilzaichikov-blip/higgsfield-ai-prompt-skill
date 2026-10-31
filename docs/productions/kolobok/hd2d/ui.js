// Overlay: pixel font drawn at 1/4 resolution with a hard alpha threshold, scaled ×4 without smoothing.
// Glyphs stay pixel-crisp; boxes and words still move smoothly (sub-pixel position + alpha every frame).
import { TL } from './cast.js';
import { seg, ss, eo, back, clamp } from '/core/lib.js';

const cv = document.getElementById('ov'), g = cv.getContext('2d'); g.imageSmoothingEnabled = false;
const W = 1920, H = 1080, S = 4;
const FONT = 'PixB', SIZE = 8, NAME = 8;
export async function overlayReady() { await document.fonts.load(`${SIZE}px ${FONT}`); await document.fonts.load(`24px ${FONT}`); }

const cache = new Map();
function pixText(text, size, col, shadow = '#140c1c') {
  const key = text + '|' + size + '|' + col; if (cache.has(key)) return cache.get(key);
  const c = document.createElement('canvas'), x = c.getContext('2d'); x.font = `${size}px ${FONT}`;
  const w = Math.ceil(x.measureText(text).width) + 4, h = Math.ceil(size * 1.5) + 2; c.width = w; c.height = h;
  x.font = `${size}px ${FONT}`; x.textBaseline = 'top';
  x.fillStyle = col; x.fillText(text, 1, 1);
  const d = x.getImageData(0, 0, w, h); for (let i = 3; i < d.data.length; i += 4) d.data[i] = d.data[i] > 110 ? 255 : 0; x.putImageData(d, 0, 0);
  const r = { c, w, h }; cache.set(key, r); return r;
}
const measure = (() => { const c = document.createElement('canvas').getContext('2d'); return (t, s) => { c.font = `${s}px ${FONT}`; return c.measureText(t).width; }; })();

function frame(wl, hl, style) {
  const key = 'F' + wl + 'x' + hl + style; if (cache.has(key)) return cache.get(key);
  const c = document.createElement('canvas'); c.width = wl; c.height = hl; const x = c.getContext('2d');
  if (style === 'narr') {
    x.fillStyle = 'rgba(16,10,30,.86)'; x.fillRect(1, 0, wl - 2, hl); x.fillRect(0, 1, wl, hl - 2);
    x.fillStyle = '#e8c070'; x.fillRect(2, 2, wl - 4, 1); x.fillRect(2, hl - 3, wl - 4, 1); x.fillRect(2, 2, 1, hl - 4); x.fillRect(wl - 3, 2, 1, hl - 4);
    x.fillStyle = '#7a5434'; x.fillRect(3, 3, wl - 6, 1); x.fillRect(3, hl - 4, wl - 6, 1);
    x.fillStyle = '#fff2c0'; for (const [a, b] of [[2, 2], [wl - 3, 2], [2, hl - 3], [wl - 3, hl - 3]]) x.fillRect(a, b, 1, 1);
  } else {
    const hb = hl - 5; x.fillStyle = '#fbf6ea'; x.fillRect(1, 0, wl - 2, hb); x.fillRect(0, 1, wl, hb - 2);
    x.fillStyle = '#1c1224'; x.fillRect(1, 0, wl - 2, 1); x.fillRect(1, hb - 1, wl - 2, 1); x.fillRect(0, 1, 1, hb - 2); x.fillRect(wl - 1, 1, 1, hb - 2);
    const m = wl >> 1; x.fillStyle = '#fbf6ea'; x.fillRect(m - 3, hb - 1, 7, 1); x.fillRect(m - 2, hb, 5, 1); x.fillRect(m - 1, hb + 1, 3, 2); x.fillRect(m, hb + 3, 1, 1);
    x.fillStyle = '#1c1224'; x.fillRect(m - 4, hb - 1, 1, 1); x.fillRect(m + 4, hb - 1, 1, 1); x.fillRect(m - 3, hb, 1, 1); x.fillRect(m + 3, hb, 1, 1); x.fillRect(m - 2, hb + 1, 1, 2); x.fillRect(m + 2, hb + 1, 1, 2); x.fillRect(m - 1, hb + 3, 1, 1); x.fillRect(m + 1, hb + 3, 1, 1); x.fillRect(m, hb + 4, 1, 1);
  }
  cache.set(key, c); return c;
}
function wrap(text, size, maxw) {
  const words = text.split(' '), sp = measure(' ', size) * .6, lines = []; let cur = [], w = 0;
  for (const wd of words) { const ww = measure(wd, size); if (cur.length && w + sp + ww > maxw) { lines.push(cur); cur = [wd]; w = ww; } else { w += (cur.length ? sp : 0) + ww; cur.push(wd); } }
  lines.push(cur); return { lines, sp };
}

const SHOWN = [];
// a box whose words drift up and fade in one after another
function block(t, t0, t1, text, cx, top, o) {
  if (t < t0 || t > t1 + .35) return;
  const size = o.size, { lines, sp } = wrap(text, size, o.maxw), lh = size + 5;
  const lw = Math.max(...lines.map(l => l.reduce((a, w) => a + measure(w, size), 0) + sp * (l.length - 1)));
  const wl = Math.ceil(lw) + 16, hl = lines.length * lh + 9 + (o.style === 'bubble' ? 5 : 0);
  const kin = eo(seg(t, t0, t0 + .35)), kout = ss(seg(t, t1, t1 + .3)), a = kin * (1 - kout);
  if (a <= .01) return;
  let x0 = cx - wl * S / 2, y0 = (o.style === 'bubble' ? top - hl * S : top) + (1 - kin) * 22 - kout * 18;
  x0 = clamp(x0, 24, W - wl * S - 24); y0 = clamp(y0, 16, H - hl * S - 16);
  g.save(); g.globalAlpha = a; g.imageSmoothingEnabled = false; g.drawImage(frame(wl, hl, o.style), x0, y0, wl * S, hl * S);
  if (o.name) { const n = pixText(o.name, NAME, '#ffe6a0'); g.fillStyle = '#5a2846'; g.fillRect(x0 + 40, y0 - n.h * S + 4, (n.w + 6) * S, n.h * S); g.drawImage(n.c, x0 + 40 + 12, y0 - n.h * S + 6, n.w * S, n.h * S); }
  g.restore();
  let i = 0;
  lines.forEach((ln, li) => {
    const lwi = ln.reduce((a, w) => a + measure(w, size), 0) + sp * (ln.length - 1); let x = x0 + (wl * S - lwi * S) / 2; const y = y0 + (4 + li * lh) * S;
    for (const wd of ln) {
      const k = eo(seg(t, t0 + .18 + i * .06, t0 + .55 + i * .06)), wa = k * (1 - kout);
      if (wa > .01) { const p = pixText(wd, size, o.col); g.save(); g.globalAlpha = wa; g.imageSmoothingEnabled = false; g.drawImage(p.c, Math.round(x), Math.round(y + (1 - k) * 18), p.w * S, p.h * S); g.restore(); }
      x += (measure(wd, size) + sp) * S; i++;
    }
  });
  SHOWN.push({ id: o.id, text, x0: Math.max(0, x0), y0: Math.max(0, y0), x1: Math.min(W, x0 + wl * S), y1: Math.min(H, y0 + hl * S), t0, t1 });
}

const TCACHE = new Map();
function title(t, t0, t1, txt, px, py) {
  if (t < t0 || t > t1) return;
  const k = seg(t, t0, t0 + .6), out = ss(seg(t, t1 - .4, t1)), a = ss(k * 2) * (1 - out);
  let im = TCACHE.get(txt);
  if (!im) {
    const size = 24, c = document.createElement('canvas'), x = c.getContext('2d'); x.font = `${size}px ${FONT}`;
    const w = Math.ceil(x.measureText(txt).width) + 10, h = size + 14; c.width = w; c.height = h; x.font = `${size}px ${FONT}`; x.textBaseline = 'top';
    x.fillStyle = '#1c1224'; for (const dx of [-1, 0, 1, 2]) for (const dy of [-1, 0, 1, 2]) x.fillText(txt, 4 + dx, 4 + dy);
    const gr = x.createLinearGradient(0, 4, 0, 4 + size); gr.addColorStop(0, '#fff4b0'); gr.addColorStop(.45, '#fff4b0'); gr.addColorStop(.46, '#f8c440'); gr.addColorStop(.75, '#f8c440'); gr.addColorStop(.76, '#d8782a'); gr.addColorStop(1, '#d8782a');
    x.fillStyle = gr; x.fillText(txt, 4, 4);
    const d = x.getImageData(0, 0, w, h); for (let i = 3; i < d.data.length; i += 4) d.data[i] = d.data[i] > 110 ? 255 : 0; x.putImageData(d, 0, 0);
    im = c; TCACHE.set(txt, im);
  }
  const s = (.85 + .15 * back(k, 2)) * S, w = im.width * s, h = im.height * s, y = H * py - h / 2 + Math.sin(t * 2) * 6 + (1 - ss(k)) * 30;
  g.save(); g.globalAlpha = a; g.imageSmoothingEnabled = false; g.drawImage(im, W * px - w / 2, y, w, h); g.restore();
  SHOWN.push({ id: 'title', text: txt, x0: W * px - w / 2, y0: y, x1: W * px + w / 2, y1: y + h, t0, t1 });
}

export function drawOverlay(t, anchors, fadeK) {
  SHOWN.length = 0; g.clearRect(0, 0, W, H);
  if (fadeK < 1) { g.fillStyle = `rgba(0,0,0,${1 - fadeK})`; g.fillRect(0, 0, W, H); }
  TL.narr.forEach(([t0, t1, txt], i) => block(t, t0, t1, txt, W / 2, 40, { size: SIZE, maxw: 440, style: 'narr', col: '#fff4dc', id: 'narr' + i }));
  TL.speech.forEach(([t0, t1, who, txt, key], i) => {
    if (t < t0 || t > t1 + .35) return; const p = anchors[key]; if (!p) return;
    const dx = key === 'kolobok' ? -150 : (key === 'ded' || key === 'baba' ? 0 : 130); block(t, t0, t1, txt, p[0] + dx, Math.max(p[1] - 10, 330), { size: 8, maxw: 176, style: 'bubble', col: '#2a1c30', name: who, id: 'sp' + i });
  });
  TL.titles.forEach(([t0, t1, txt, px, py]) => title(t, t0, t1, txt, px, py));
}
export function texts(t) { return SHOWN.filter(s => t >= s.t0 && t <= s.t1).map(s => ({ id: s.id, text: s.text, x0: s.x0, y0: s.y0, x1: s.x1, y1: s.y1 })); }
