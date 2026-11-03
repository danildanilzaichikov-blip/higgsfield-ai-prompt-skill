"""Volumetric pixel-art engine: 3D primitives -> per-pixel normals -> quantized palette ramps."""
import math
import numpy as np
from PIL import Image, ImageDraw

L = np.array([-0.55, -0.68, 0.48]); L = L / np.linalg.norm(L)
RIM = np.array([0.85, -0.35, 0.15]); RIM = RIM / np.linalg.norm(RIM)
OUT = (28, 18, 30)

def hexr(*cs): return [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in cs]

MATS = {  # dark -> light, shadows hue-shifted toward purple/blue
    "skin": dict(ramp=hexr("#7a3f45", "#b8665a", "#e39a7c", "#f6c7a0", "#ffe3c4")),
    "linen": dict(ramp=hexr("#5b5873", "#9a97ad", "#cfcbd3", "#efeae4", "#fffaf2")),
    "white": dict(ramp=hexr("#6c6f8c", "#a8acc2", "#d9dbe4", "#f3f3f5", "#ffffff")),
    "beard": dict(ramp=hexr("#6a6a80", "#a6a8b8", "#d2d4dc", "#eeeff2", "#ffffff"), noise=.12),
    "grey": dict(ramp=hexr("#3c3f58", "#5f647d", "#8a8fa3", "#b3b7c3", "#d7d9df")),
    "trous": dict(ramp=hexr("#2a2c4a", "#3f4670", "#5b6696", "#7d89b4", "#a3aecb")),
    "bast": dict(ramp=hexr("#5a3a22", "#8a5c32", "#b98a4e", "#dcb675", "#f1d9a0"), noise=.15),
    "red": dict(ramp=hexr("#4a1530", "#7d1d36", "#b3283a", "#e04a43", "#ff8a6a")),
    "scarf": dict(ramp=hexr("#5a2a10", "#9a4e14", "#d18a1e", "#f2bd3c", "#ffe17a")),
    "bread": dict(ramp=hexr("#4a2410", "#86451a", "#c27a2a", "#e9ae48", "#ffd98a", "#fff1c8"), noise=.16, spec=True),
    "hare": dict(ramp=hexr("#3f3540", "#6e5d5a", "#9c8a7c", "#c4b4a0", "#e6dcc8"), noise=.14),
    "harebelly": dict(ramp=hexr("#8a8496", "#bdb8c2", "#e3e0e2", "#f7f5f2", "#ffffff"), noise=.08),
    "wolf": dict(ramp=hexr("#262a3e", "#454b63", "#6c7389", "#9aa0ae", "#c9ccd3"), noise=.16),
    "wolflight": dict(ramp=hexr("#5d5a6e", "#8e8b98", "#bdbac0", "#dedbd8", "#f4f2ee"), noise=.12),
    "bear": dict(ramp=hexr("#2a1418", "#4e2a22", "#774330", "#a0623f", "#c78a58"), noise=.18),
    "bearlight": dict(ramp=hexr("#5a3428", "#8c5a3c", "#b98458", "#ddb07c", "#f2d2a0"), noise=.1),
    "fox": dict(ramp=hexr("#4a1a1e", "#8a3018", "#c95a1c", "#ef8a2c", "#ffbe5c"), noise=.14),
    "foxwhite": dict(ramp=hexr("#8a7f96", "#c0b8c6", "#e8e2e2", "#fbf7f0", "#ffffff"), noise=.08),
    "dark": dict(ramp=hexr("#140d16", "#24182a", "#3a2a3e", "#58475a", "#7a6a78")),
    "log": dict(ramp=hexr("#3a1e18", "#6a3a22", "#9a5a30", "#c58448", "#e6b070"), noise=.2),
    "roof": dict(ramp=hexr("#2e1a22", "#4f2c2a", "#734236", "#985a42", "#b97a56"), noise=.15),
    "leaf": dict(ramp=hexr("#163a2e", "#22603a", "#3d8a3e", "#6db34a", "#a6d65c", "#d9f08a"), noise=.18),
    "leafdark": dict(ramp=hexr("#0e2626", "#173f36", "#22603e", "#3a8444", "#5ea64c"), noise=.18),
    "spruce": dict(ramp=hexr("#0c2228", "#123a36", "#1d5640", "#2f744a", "#4f9656"), noise=.2),
    "birch": dict(ramp=hexr("#6a6878", "#a8a6b2", "#d8d6da", "#f2f0ea", "#ffffff"), noise=.1),
    "trunk": dict(ramp=hexr("#24141a", "#40241e", "#603a28", "#845436", "#a8744a"), noise=.2),
    "cloud": dict(ramp=hexr("#9a8fb8", "#c0b8d8", "#e2dcef", "#f6f3fa", "#ffffff")),
    "cloudwarm": dict(ramp=hexr("#b0708a", "#d898a0", "#f2bfae", "#ffdcc0", "#fff0dc")),
    "stove": dict(ramp=hexr("#7a7088", "#a8a0b0", "#d4cdd2", "#ece6e2", "#fbf8f2"), noise=.06),
    "clay": dict(ramp=hexr("#4a2018", "#7a3a22", "#a85a30", "#cf8448", "#eaaa6a")),
    "blue": dict(ramp=hexr("#1a2050", "#283a80", "#3a5cb0", "#5a86d8", "#8ab4f0")),
    "berry": dict(ramp=hexr("#3a0a1e", "#6a1028", "#a01c34", "#d83848", "#ff7a7a")),
    "mush": dict(ramp=hexr("#4a0a14", "#8a1420", "#c82a2a", "#f05040", "#ff8a6a")),
    "stone": dict(ramp=hexr("#2c2a3a", "#4a4858", "#6e6c7a", "#9694a0", "#bdbac2"), noise=.15),
    "sunflower": dict(ramp=hexr("#6a3a08", "#b06a10", "#e8a418", "#ffd23c", "#fff08a")),
    "honey": dict(ramp=hexr("#5a3008", "#9a5a10", "#d89420", "#f6c440", "#fff08a")),
}

def _hash(h, w, seed):
    yy, xx = np.mgrid[0:h, 0:w]
    v = np.sin(xx * 12.9898 + yy * 78.233 + seed * 37.719) * 43758.5453
    return v - np.floor(v)

def render(prims, w, h, light=L, amb=.22, rim=RIM, rim_on=True, outline=True, seed=0, inner=True):
    """prims: ('ell', cx,cy,cz, rx,ry,rz, mat[, uv_rot]) | ('cap', x0,y0,z0, x1,y1,z1, r, mat)"""
    zb = np.full((h, w), -1e9); nb = np.zeros((h, w, 3)); mb = np.full((h, w), -1, int); tb = np.zeros((h, w))
    names = []
    for p in prims:
        kind = p[0]
        if kind == "ell":
            _, cx, cy, cz, rx, ry, rz, mat = p[:8]; rot = p[8] if len(p) > 8 else 0
            x0, x1 = int(max(0, cx - rx - 1)), int(min(w, cx + rx + 2)); y0, y1 = int(max(0, cy - ry - 1)), int(min(h, cy + ry + 2))
            if x1 <= x0 or y1 <= y0: continue
            yy, xx = np.mgrid[y0:y1, x0:x1] + .5
            u = (xx - cx) / rx; v = (yy - cy) / ry; q = 1 - u * u - v * v
            m = q > 0; s = np.sqrt(np.clip(q, 0, 1)); z = cz + rz * s
            n = np.stack([u / rx, v / ry, s / rz], -1)
            # texture coordinate rotates with the object (kolobok roll)
            ca, sa = math.cos(rot), math.sin(rot); tex = (u * ca - v * sa) * 7.3 + (u * sa + v * ca) * 13.1
        else:
            _, ax, ay, az, bx, by, bz, r, mat = p
            x0, x1 = int(max(0, min(ax, bx) - r - 1)), int(min(w, max(ax, bx) + r + 2)); y0, y1 = int(max(0, min(ay, by) - r - 1)), int(min(h, max(ay, by) + r + 2))
            if x1 <= x0 or y1 <= y0: continue
            yy, xx = np.mgrid[y0:y1, x0:x1] + .5
            dx, dy = bx - ax, by - ay; ll = dx * dx + dy * dy + 1e-9
            t = np.clip(((xx - ax) * dx + (yy - ay) * dy) / ll, 0, 1)
            px, py = xx - (ax + t * dx), yy - (ay + t * dy); d2 = px * px + py * py
            m = d2 < r * r; s = np.sqrt(np.clip(r * r - d2, 0, None)); z = az + t * (bz - az) + s
            n = np.stack([px, py, s], -1); tex = t * 9.1 + px * .7
        if mat not in names: names.append(mat)
        mi = names.index(mat)
        sub = zb[y0:y1, x0:x1]; upd = m & (z > sub)
        sub[upd] = z[upd]; nb[y0:y1, x0:x1][upd] = n[upd]; mb[y0:y1, x0:x1][upd] = mi; tb[y0:y1, x0:x1][upd] = tex[upd]
    nb = nb / (np.linalg.norm(nb, axis=-1, keepdims=True) + 1e-9)
    out = np.zeros((h, w, 4), np.uint8)
    noise = _hash(h, w, seed)
    for mi, name in enumerate(names):
        M = MATS[name]; ramp = np.array(M["ramp"]); sel = mb == mi
        if not sel.any(): continue
        n = nb[sel]; dif = np.clip(n @ light, 0, 1)
        val = amb + (1 - amb) * dif
        if M.get("noise"):
            tex = np.sin(tb[sel] * 3.1) * .5 + .5
            val = val + (noise[sel] - .5) * M["noise"] + (tex - .5) * M["noise"] * .6
        idx = np.clip((val * (len(ramp) - 1) + .35).astype(int), 0, len(ramp) - 1)
        if rim_on:
            rr = n @ rim; idx = np.where((rr > .72) & (n[:, 2] < .55), np.minimum(idx + 2, len(ramp) - 1), idx)
        if M.get("spec"):
            hv = light + np.array([0, 0, 1.]); hv /= np.linalg.norm(hv); sp = n @ hv
            idx = np.where(sp > .965, len(ramp) - 1, idx)
        col = ramp[idx]; o = out[sel]; o[:, :3] = col; o[:, 3] = 255; out[sel] = o
    if inner:   # inner contour where depth jumps between different parts
        dz = np.zeros((h, w), bool)
        for sh in ((0, 1), (1, 0)):
            a = zb; b = np.roll(zb, sh, axis=(0, 1))
            ma = mb; mbb = np.roll(mb, sh, axis=(0, 1))
            dz |= (ma >= 0) & (mbb >= 0) & (b - a > 3.0) & (ma != mbb)
        rgb = out[..., :3].astype(int); rgb[dz] = (rgb[dz] * .55).astype(int); out[..., :3] = rgb
    if outline:
        a = mb >= 0; ring = np.zeros_like(a)
        for sh in ((0, 1), (0, -1), (1, 0), (-1, 0)): ring |= np.roll(a, sh, axis=(0, 1))
        ring &= ~a; out[ring] = OUT + (255,)
    return Image.fromarray(out, "RGBA")

def decal(im, ops):
    d = ImageDraw.Draw(im)
    for op in ops:
        k = op[0]
        if k == "px":
            for (x, y) in op[1]: d.point((x, y), fill=op[2])
        elif k == "line": d.line(op[1], fill=op[2], width=op[3] if len(op) > 3 else 1)
        elif k == "rect": d.rectangle(op[1], fill=op[2])
    return im

def flip_prims(prims, w):
    out = []
    for p in prims:
        if p[0] == "ell": q = list(p); q[1] = w - p[1]; out.append(tuple(q))
        else: q = list(p); q[1] = w - p[1]; q[4] = w - p[4]; out.append(tuple(q))
    return out

def flip_ops(ops, w):
    out = []
    for op in ops:
        if op[0] == "px": out.append(("px", [(w - 1 - x, y) for x, y in op[1]], op[2]))
        elif op[0] == "line": out.append(("line", [(w - 1 - x, y) for x, y in op[1]], *op[2:]))
        elif op[0] == "rect": x0, y0, x1, y1 = op[1]; out.append(("rect", (w - 1 - x1, y0, w - 1 - x0, y1), op[2]))
    return out

def mirror_light(): return np.array([L[0], L[1], L[2]])
