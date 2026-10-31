"""Stick & Kalyaka — 60 s channel trailer, rendered procedurally.

2.5D notebook cartoon: ink characters standing up off a perspective page (paper-cutout
edges + contact shadows), multiplane foreground with parallax, line boil on twos,
8-bit accents, pop-up subtitles. Frames are piped to ffmpeg.

usage: python3 render.py OUT.mp4 [--preview T1,T2,...] [--fast]
"""
import math, os, sys, subprocess
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, DUR = 1920, 1080, 24, 60.0
G = 820                                  # ground line (world y)
INK = (28, 28, 36); PAPER = (250, 247, 238); EDGE = (196, 190, 178)
RED = (222, 46, 46); BLUE = (40, 86, 205); YEL = (246, 200, 42)
WOOD = (232, 192, 140); GRAPH = (70, 70, 78)
FONT = os.path.join(HERE, "Rubik-Black.ttf")
FONT2 = os.path.join(HERE, "Rubik-XB.ttf")

# ---------------------------------------------------------------- helpers
def clamp(v, a=0.0, b=1.0): return a if v < a else b if v > b else v
def seg(t, a, b): return clamp((t - a) / (b - a)) if b > a else float(t >= a)
def ss(x): x = clamp(x); return x * x * (3 - 2 * x)
def lerp(a, b, k): return a + (b - a) * k
def back(x, s=1.9):
    x = clamp(x); x -= 1; return x * x * ((s + 1) * x + s) + 1
def crash(x): x = clamp(x); return 1 - (1 - x) ** 4
def hsh(i, s):
    v = math.sin(i * 127.1 + s * 311.7) * 43758.5453; return v - math.floor(v)

def ik(a, t, l1, l2, prefer):
    """two-bone IK; prefer(j1, j2) -> chosen joint"""
    dx, dy = t[0] - a[0], t[1] - a[1]; d = math.hypot(dx, dy)
    d = max(1e-3, min(d, l1 + l2 - 0.5)); ang = math.atan2(dy, dx)
    c = clamp((l1 * l1 + d * d - l2 * l2) / (2 * l1 * d), -1, 1); th = math.acos(c)
    j1 = (a[0] + l1 * math.cos(ang + th), a[1] + l1 * math.sin(ang + th))
    j2 = (a[0] + l1 * math.cos(ang - th), a[1] + l1 * math.sin(ang - th))
    j = prefer(j1, j2)
    e = (j[0] + l2 * math.cos(math.atan2(t[1] - j[1], t[0] - j[0])),
         j[1] + l2 * math.sin(math.atan2(t[1] - j[1], t[0] - j[0])))
    return j, e

def circle(cx, cy, r, n=28, a0=0, a1=2 * math.pi, ry=None):
    ry = r if ry is None else ry
    return [(cx + r * math.cos(lerp(a0, a1, i / n)), cy + ry * math.sin(lerp(a0, a1, i / n)))
            for i in range(n + 1)]

def S(pts, col=INK, w=7, cut=True, fill=None, dot=False):
    return {"pts": pts, "col": col, "w": w, "cut": cut, "fill": fill, "dot": dot}

def plen(p): return sum(math.hypot(p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1]) for i in range(len(p) - 1))

def reveal(strokes, frac):
    """truncate strokes to a drawn fraction; return (strokes, tip)"""
    if frac >= 1: return strokes, None
    tot = sum(max(plen(s["pts"]), 8) for s in strokes); left = tot * clamp(frac); out = []; tip = None
    for s in strokes:
        L = max(plen(s["pts"]), 8)
        if left >= L: out.append(s); left -= L; tip = s["pts"][-1]; continue
        if left <= 0: break
        p = s["pts"]; acc = 0; q = [p[0]]
        for i in range(len(p) - 1):
            sl = math.hypot(p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1])
            if acc + sl >= left:
                k = (left - acc) / max(sl, 1e-6)
                q.append((lerp(p[i][0], p[i + 1][0], k), lerp(p[i][1], p[i + 1][1], k))); break
            q.append(p[i + 1]); acc += sl
        s2 = dict(s); s2["fill"] = None; s2["pts"] = q; out.append(s2); tip = q[-1]; break
    return out, tip

def peel(strokes, k, ground=G):
    """k=0 lies flat on the page, 1 stands up"""
    if k >= 0.999: return strokes
    kk = 0.12 + 0.88 * k
    return [dict(s, pts=[(x, ground - (ground - y) * kk) for x, y in s["pts"]]) for s in strokes]

def shift(strokes, dx, dy):
    return [dict(s, pts=[(x + dx, y + dy) for x, y in s["pts"]]) for s in strokes]

# ---------------------------------------------------------------- camera / draw
class Cam:
    def __init__(s, cx, cy, z): s.cx, s.cy, s.z = cx, cy, z
    def T(s, x, y, par=1.0):
        return ((x - s.cx) * s.z * par + W / 2, (y - s.cy) * s.z * par + H / 2)

def draw_strokes(d, cam, strokes, seed, boil=1.4):
    if not strokes: return
    z = cam.z
    def sp(s):
        return [cam.T(x + (hsh(i, seed + j) - .5) * 2 * boil, y + (hsh(i + 7, seed + j) - .5) * 2 * boil)
                for j, (i, (x, y)) in [(0, (i, p)) for i, p in enumerate(s["pts"])]]
    pts = [sp(s) for s in strokes]
    for s, p in zip(strokes, pts):           # paper-cutout thickness sliver
        if s["cut"] and len(p) > 1:
            off = [(x + 3 * z, y + 5 * z) for x, y in p]
            d.line(off, fill=EDGE, width=int((s["w"] + 9) * z), joint="curve")
    for s, p in zip(strokes, pts):
        if s["cut"] and len(p) > 1:
            d.line(p, fill=PAPER, width=int((s["w"] + 9) * z), joint="curve")
    for s, p in zip(strokes, pts):
        if s["fill"] and len(p) > 2: d.polygon(p, fill=s["fill"])
    for s, p in zip(strokes, pts):
        if s["dot"]:
            (x, y), r = p[0], s["w"] * z
            d.ellipse([x - r, y - r, x + r, y + r], fill=s["col"])
        elif len(p) > 1:
            wd = max(1, int(s["w"] * z)); d.line(p, fill=s["col"], width=wd, joint="curve")
            r = wd / 2.2
            for x, y in (p[0], p[-1]): d.ellipse([x - r, y - r, x + r, y + r], fill=s["col"])

def shadow(sd, cam, x, w, a=70, y=G + 4):
    (sx, sy), z = cam.T(x, y), cam.z
    sd.ellipse([sx - w * z, sy - w * 0.16 * z, sx + w * z, sy + w * 0.16 * z], fill=(70, 55, 40, a))

# ---------------------------------------------------------------- background
BX0, BY0, BX1, BY1 = -1500, -2700, 3500, 1750
def build_bg():
    w, h = BX1 - BX0, BY1 - BY0
    rng = np.random.default_rng(3)
    n = Image.fromarray(rng.normal(0, 1, (h // 3, w // 3)).astype(np.float32), "F").resize((w, h), Image.BILINEAR)
    n2 = rng.normal(0, 1, (h, w)).astype(np.float32)
    base = np.empty((h, w, 3), np.float32); base[:] = PAPER
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lamp = 1.025 - 0.07 * np.clip(np.hypot(xx + BX0 + 300, yy + BY0 + 600) / 3200, 0, 1)
    base *= lamp[..., None]; base += (np.asarray(n) * 2.2 + n2 * 1.6)[..., None]
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(img)
    y = BY0
    while y < BY1:                                # ruled lines, wider toward the viewer
        d.line([(0, y - BY0), (w, y - BY0)], fill=(158, 190, 228), width=3)
        y += 40 + max(0, y - 200) * 0.05
    for x0 in (170,):                             # red margin, slight perspective slant
        d.line([(x0 - BX0 + (BY0 - 0) * 0.05, 0), (x0 - BX0 + (BY1 - 0) * 0.05 - 0, h)], fill=(226, 112, 112), width=4)
    return img

NIGHT = (34, 44, 92)

# ---------------------------------------------------------------- characters
UL = LL = 64; TOR = 104; R = 34; UA = LA = 54

def stick(s):
    x = s.get("x", 900); f = s.get("face", 0); dirs = f if f else 1
    cr = s.get("crouch", 0); lean = s.get("lean", 0); ph = s.get("phase")
    hipy = G - (UL + LL) * 0.985 + cr * 58
    if ph is not None:
        St = s.get("stride", 92); feet = []
        for p in (ph % 1, (ph + .5) % 1):
            if p < .5: ox, lift = St * (.25 - p), 0
            else:
                t = (p - .5) / .5; ox, lift = St * (-.25 + .5 * ss(t)), 24 * math.sin(math.pi * t)
            feet.append((x + ox * dirs, G - lift))
        hipy += 6 * math.cos(4 * math.pi * ph); sw = 30 * math.sin(2 * math.pi * ph)
    else:
        sp = 24 if f == 0 else 13; feet = s.get("feet") or [(x - sp, G), (x + sp, G)]; sw = 0
    hipy -= s.get("jump", 0)
    hip = (x, hipy); neck = (x + lean * 34, hipy - TOR); sh = (neck[0] - lean * 4, neck[1] + 14)
    head = (neck[0] + lean * 10, neck[1] - R - 3)
    out = [S(circle(*head, R), fill=PAPER), S([hip, neck])]
    def knee(j1, j2):
        if f == 0: return j1 if abs(j1[0] - x) > abs(j2[0] - x) else j2
        return j1 if j1[0] * dirs > j2[0] * dirs else j2
    legs = []
    for ft in feet:
        tgt = (ft[0], ft[1] - s.get("jump", 0) * 0.3)
        k, e = ik(hip, tgt, UL, LL, knee); legs.append(S([hip, k, e]))
    elb = lambda j1, j2: j1 if j1[1] > j2[1] else j2
    arms = []
    for side, key in ((1, "hR"), (-1, "hL")):
        t = s.get(key)
        if t is None:
            if f == 0: t = (sh[0] + side * 34, sh[1] + 96)
            else: t = (sh[0] + dirs * side * sw - dirs * 4, sh[1] + 98)
        el, e = ik(sh, t, UA, LA, elb); arms.append(S([sh, el, e]))
    # face
    ex = [(-12, 0), (12, 0)] if f == 0 else [(dirs * 6, 0), (dirs * 20, 0)]
    hx, hy = head; eyes = []
    for dx, _ in ex:
        if s.get("big"): eyes += [S(circle(hx + dx * 1.3, hy - 6, 10), w=4), S([(hx + dx * 1.3, hy - 6)], w=3.5, dot=True, cut=False)]
        elif s.get("closed"): eyes.append(S([(hx + dx - 6, hy - 6), (hx + dx, hy - 3), (hx + dx + 6, hy - 6)], w=4, cut=False))
        else: eyes.append(S([(hx + dx, hy - 6)], w=4.6, dot=True, cut=False))
    sm = s.get("smile", 0.4); mx = hx + (0 if f == 0 else dirs * 13)
    mouth = S([(mx - 11 + i * 2.2, hy + 13 + sm * 6 * (1 - ((i - 5) / 5) ** 2)) for i in range(11)], w=4, cut=False)
    if s.get("open_mouth"): mouth = S(circle(mx, hy + 15, 6, 14), w=4, cut=False)
    # scarf with lagging tails (follow-through)
    v = s.get("v", 0); bk = -1 if v > 0 else 1; vv = clamp(abs(v) / 260)
    if abs(v) < 5: bk = -dirs if f else 1
    knot = (neck[0], neck[1] + 6); fl = s.get("flutter", 0)
    tails = []
    for k2, o in ((0, 0), (1, 1.2)):
        pts = [knot]
        for i in range(1, 5):
            pts.append((knot[0] + bk * i * (4 + 11 * vv) + o * 3,
                        knot[1] + i * (8 - 6 * vv) + o * 4 + math.sin(fl * 9 + i * 1.3 + o) * (2 + 5 * vv)))
        tails.append(S(pts, RED, 7))
    band = S([(neck[0] - 17, neck[1] + 3), (neck[0], neck[1] + 8), (neck[0] + 17, neck[1] + 3)], RED, 9)
    order = [out[0]] + eyes + [mouth, out[1]] + arms + legs + [band] + tails
    return order, {"head": head, "sh": sh, "hip": hip}

def kalyaka(k):
    x = k.get("x", 1100); f = k.get("face", -1); hop = k.get("hop", 0); sq = k.get("squash", 0)
    curl = k.get("curl", 0); nod = k.get("nod", 0)
    rx = 58 * (1 + .14 * sq) * (1 - .12 * curl); ry = 34 * (1 - .14 * sq) * (1 + .15 * curl)
    legh = 30 * (1 - curl); cy = G - legh - ry - hop + nod * 8
    rng = np.random.default_rng(11); jit = rng.uniform(.62, 1.0, 120)
    pts = []
    for i in range(120):
        a = i / 120 * 2 * math.pi * 3.3
        pts.append((x + rx * jit[i] * math.cos(a) + 10 * math.cos(a * 6.3),
                    cy + ry * jit[i] * math.sin(a) + 9 * math.sin(a * 6.3)))
    body = S(pts, BLUE, 4)
    legs = []
    ph = k.get("phase")
    for i, (ox, pair) in enumerate(((-34, 0), (-16, .5), (18, .5), (36, 0))):
        if legh < 3: break
        ax, ay = x + ox * (f or 1), cy + ry * .62
        if ph is not None:
            p = (ph + pair) % 1; fx = ax + (f or 1) * 14 * math.sin(2 * math.pi * p); fy = G - hop - max(0, 13 * math.sin(2 * math.pi * p))
        else: fx, fy = ax + (k.get("splay", 0) * (1 if ox > 0 else -1)), G - hop
        fy = min(fy, G - hop); fy = max(fy, ay + 4)
        mid = ((ax + fx) / 2 + (f or 1) * 4, (ay + fy) / 2)
        legs.append(S([(ax, ay), mid, (fx, fy)], BLUE, 5))
    fx_ = f if f else 1
    eyes = []
    for dx in ((fx_ * 22, fx_ * 40) if f else (-12, 12)):
        ey = cy - 10 - nod * 3
        if k.get("closed"): eyes.append(S([(x + dx - 6, ey), (x + dx, ey + 3), (x + dx + 6, ey)], INK, 3.5, cut=False))
        else: eyes.append(S([(x + dx, ey)], INK, 5.5, cut=False, dot=True))
    if k.get("yawn"): eyes.append(S(circle(x + fx_ * 44, cy + 10, 6 + 4 * k["yawn"], 14), INK, 3.5, cut=False))
    wag = k.get("wag", 0); tb = (x - fx_ * rx * .9, cy - 4); tail = [tb]
    ang = math.pi * (1 if fx_ > 0 else 0) - fx_ * (.6 + .5 * math.sin(wag)) * (1 - .6 * curl)
    for i in range(1, 6):
        r = i * 11; zz = (7 if i % 2 else -7)
        tail.append((tb[0] + math.cos(ang) * r - math.sin(ang) * zz, tb[1] + math.sin(ang) * r + math.cos(ang) * zz))
    return [body] + eyes + legs + [S(tail, BLUE, 4.5)], (x, cy)

def pencil(tip, u, L=170, w=22):
    ux, uy = u; n = math.hypot(ux, uy) or 1; ux, uy = ux / n, uy / n; px, py = -uy, ux
    tx, ty = tip; cone = 34
    b0 = (tx + ux * cone, ty + uy * cone); b1 = (tx + ux * L, ty + uy * L)
    body = [(b0[0] + px * w / 2, b0[1] + py * w / 2), (b1[0] + px * w / 2, b1[1] + py * w / 2),
            (b1[0] - px * w / 2, b1[1] - py * w / 2), (b0[0] - px * w / 2, b0[1] - py * w / 2)]
    cn = [(tx, ty), (b0[0] + px * w / 2, b0[1] + py * w / 2), (b0[0] - px * w / 2, b0[1] - py * w / 2), (tx, ty)]
    gr = [(tx, ty), (tx + ux * 11 + px * 4, ty + uy * 11 + py * 4), (tx + ux * 11 - px * 4, ty + uy * 11 - py * 4), (tx, ty)]
    return [S(body + [body[0]], INK, 4, fill=YEL), S(cn, INK, 4, fill=WOOD), S(gr, INK, 3, cut=False, fill=GRAPH)]

def held_pencil(tip, sh, grip=140):
    ux, uy = sh[0] - tip[0], sh[1] - tip[1]; d = math.hypot(ux, uy) or 1
    ux, uy = ux / d, uy / d; g = min(grip, max(40, d - 50))
    return pencil(tip, (ux, uy)), (tip[0] + ux * g, tip[1] + uy * g)

# ---------------------------------------------------------------- props
def rocket(x, base, filled=1.0, faces=False, squash=0.0):
    hgt = 300 * (1 - .12 * squash); wd = 78 * (1 + .1 * squash)
    top = base - hgt; body = []
    for i in range(25):
        a = i / 24
        yy = lerp(base - 30, top + 70, a); ww = wd * (1 - .25 * a * a)
        body.append((x + ww, yy))
    body += [(x + wd * .55, top + 40), (x, top), (x - wd * .55, top + 40)]
    for i in range(24, -1, -1):
        a = i / 24; yy = lerp(base - 30, top + 70, a); ww = wd * (1 - .25 * a * a); body.append((x - ww, yy))
    body.append(body[0])
    nose = [(x + wd * .76, top + 70), (x + wd * .55, top + 40), (x, top), (x - wd * .55, top + 40), (x - wd * .76, top + 70), (x + wd * .76, top + 70)]
    finL = [(x - wd, base - 110), (x - wd - 50, base + 6), (x - wd + 6, base - 32)]
    finR = [(x + wd, base - 110), (x + wd + 50, base + 6), (x + wd - 6, base - 32)]
    win = circle(x, top + 130, 38, 30)
    fr = lambda c: c if filled >= 1 else None
    out = [S(body, INK, 6, fill=fr(RED)), S(nose, INK, 5, fill=fr(YEL)),
           S(finL + [finL[0]], INK, 6, fill=fr(YEL)), S(finR + [finR[0]], INK, 6, fill=fr(YEL)),
           S(win, INK, 6, fill=fr((235, 245, 255))), S([(x - 30, base - 40), (x - 30, base - 110), (x + 30, base - 110), (x + 30, base - 40)], INK, 5, cut=False)]
    if faces:
        wy = top + 130
        out += [S(circle(x - 15, wy - 2, 13, 16), INK, 4, cut=False), S([(x - 20, wy - 5)], INK, 2.6, dot=True, cut=False),
                S([(x - 11, wy - 5)], INK, 2.6, dot=True, cut=False),
                S([(x - 22 + i * 1.4, wy + 4 + 3 * (1 - ((i - 5) / 5) ** 2)) for i in range(11)], INK, 3, cut=False),
                S([(x - 26, wy + 13), (x - 4, wy + 13)], RED, 5, cut=False),
                S(circle(x + 18, wy + 6, 14, 18, ry=10), BLUE, 3.5, cut=False),
                S([(x + 22, wy + 2)], INK, 2.8, dot=True, cut=False), S([(x + 30, wy + 2)], INK, 2.8, dot=True, cut=False)]
    return out

def balloon(x, y, col):
    b = circle(x, y, 46, 30, ry=56)
    knot = [(x - 7, y + 62), (x + 7, y + 62), (x, y + 54), (x - 7, y + 62)]
    string = [(x + 6 * math.sin(i * .6), y + 62 + i * 14) for i in range(12)]
    return [S(b, INK, 5, fill=col), S(knot, INK, 3, fill=col), S(string, INK, 3, cut=False)]

def moon(x, y, r=70):
    o = circle(x, y, r, 30, math.radians(-110), math.radians(110))
    i_ = circle(x - r * .45, y, r * .82, 30, math.radians(80), math.radians(-80))
    return [S(o + i_ + [o[0]], INK, 5, fill=(255, 236, 150))]

# ---------------------------------------------------------------- 8-bit sprites
COIN = ["..XX..", ".XYYX.", "XYWYYX", "XYWYYX", ".XYYX.", "..XX.."]
STAR = ["..X..", ".XYX.", "XYYYX", ".XYX.", "..X.."]
CLOUD = ["....XXXX....", "..XXWWWWXX..", ".XWWWWWWWWX.", "XWWWWWWWWWWX", ".XXXXXXXXXX."]
SUN = ["..XXXX..", ".XYYYYX.", "XYYOYYYX", "XYYYYYYX", "XYYYYOYX", "XYYYYYYX", ".XYYYYX.", "..XXXX.."]
PAL = {"X": (40, 40, 60), "Y": (250, 205, 40), "W": (200, 225, 255), "O": (245, 150, 40), "G": (70, 180, 80), "B": (150, 95, 60)}
def sprite(d, rows, sx, sy, px, pal=PAL, override=None):
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            if c == ".": continue
            col = (override or pal)[c] if c in (override or pal) else pal[c]
            d.rectangle([sx + i * px, sy + j * px, sx + (i + 1) * px - 1, sy + (j + 1) * px - 1], fill=col)
def sprite_c(d, rows, cx, cy, px, **kw): sprite(d, rows, cx - len(rows[0]) * px / 2, cy - len(rows) * px / 2, px, **kw)

# ---------------------------------------------------------------- foreground (near layer)
FG = [(-200, 1010, 0), (520, 1060, 1), (1300, 1030, 0), (1900, 1075, 1), (2500, 1020, 0), (3100, 1060, 1)]
def foreground(d, cam, night=0):
    for wx, wy, kind in FG:
        x, y = cam.T(wx, wy, 1.55); z = cam.z * 1.55
        if x < -300 or x > W + 300: continue
        if kind == 0:   # curled pencil shaving
            pts = [(x + 60 * z * math.cos(a) * (1 - a / 9), y + 26 * z * math.sin(a) * (1 - a / 9)) for a in np.linspace(0, 6.5, 30)]
            d.line(pts, fill=(214, 178, 128), width=int(16 * z), joint="curve")
            d.line(pts[:8], fill=(232, 196, 70), width=int(9 * z), joint="curve")
        else:           # eraser crumbs
            for i in range(5):
                rx = x + (hsh(i, wx) - .5) * 120 * z; ry = y + (hsh(i + 3, wx) - .5) * 40 * z; r = (8 + 10 * hsh(i, 9)) * z
                d.ellipse([rx - r, ry - r * .7, rx + r, ry + r * .7], fill=(214, 196, 196))

# ---------------------------------------------------------------- timeline
def walkx(t, t0, t1, x0, x1):
    k = ss(seg(t, t0, t1)); x = lerp(x0, x1, k)
    St = abs(x1 - x0) / max(1, round(abs(x1 - x0) / 92)) if x1 != x0 else 92
    v = (x1 - x0) / (t1 - t0) * 6 * k * (1 - k) * 1.0 if t0 < t < t1 else 0
    walking = t0 < t < t1
    return x, (abs(x - x0) / St if walking else None), St, v

def cam_path(t, keys):
    for (ta, a), (tb, b) in zip(keys, keys[1:]):
        if ta <= t <= tb:
            k = seg(t, ta, tb); e = crash(k) if b[3] == "crash" else ss(k)
            return Cam(lerp(a[0], b[0], e), lerp(a[1], b[1], e), lerp(a[2], b[2], e))
    a = keys[-1][1] if t > keys[-1][0] else keys[0][1]
    return Cam(a[0], a[1], a[2])

class Frame:
    def __init__(s, cam): s.cam = cam; s.layers = []; s.shadows = []; s.night = 0; s.pix = []; s.post = []
    def add(s, strokes, seed): s.layers.append((strokes, seed))

def draw_held(fr, tip, st):
    ps, grip = held_pencil(tip, (st["x"], G - 300)); return ps, grip

def scene(t):
    """global time -> Frame"""
    ta = math.floor(t * 12) / 12                      # character animation on twos
    seed = int(t * 12)
    if t < 15: return clip1(t, ta, seed)
    if t < 30: return clip2(t, t - 15, ta - 15, seed)
    if t < 45: return clip3(t, t - 30, ta - 30, seed)
    return clip4(t, t - 45, ta - 45, seed)

def stick_with_pencil(fr, st, tip, seed, extra_reach=None):
    """stick holding the pencil whose tip is at `tip` (right hand)"""
    _, rig = stick(st)
    ps, grip = held_pencil(tip, rig["sh"]); st = dict(st, hR=grip)
    sk, rig = stick(st); fr.add(sk, seed); fr.add(ps, seed + 50); return rig

def clip1(t, lt, seed):
    cam = cam_path(t, [(0, (900, 640, 1.0, "")), (4.2, (880, 655, 1.22, "")), (5.2, (900, 660, 1.22, "")),
                       (9.8, (1000, 660, 1.42, "")), (10.2, (1000, 660, 1.42, "")), (10.6, (1000, 640, 1.85, "crash")),
                       (15, (1000, 640, 1.9, ""))])
    fr = Frame(cam); sx = 880; kx = 1090
    # STICK
    if lt < 1.0:
        hop = abs(math.sin(lt * math.pi * 2)) * 30
        fr.add(pencil((sx + 60, G - hop), (0.15, -1)), seed); fr.shadows.append((sx + 60, 30, 50))
        return fr
    st = dict(x=sx, face=0, smile=.5)
    if lt < 3.6:
        sk, _ = stick(st); sk, tip = reveal(sk, seg(lt, 1.0, 3.5)); sk = peel(sk, 0)
        fr.add(sk, seed)
        if tip:
            tip = (tip[0], G - (G - tip[1]) * .12)
            fr.add(pencil(tip, (0.35, -1)), seed + 1)
        return fr
    pk = back(seg(lt, 3.6, 4.4))
    if lt < 5.0:
        sk, _ = stick(dict(st, crouch=.25 * (1 - pk), smile=.6)); fr.add(peel(sk, pk), seed)
        fr.shadows.append((sx, 60 * pk + 10, int(70 * pk)))
        fr.add(pencil((sx + 110, G), (0.15, -1)), seed + 1); fr.shadows.append((sx + 110, 25, 50)); return fr
    fr.shadows.append((sx, 70, 70))
    if lt < 5.9:   # bend at the knees and pick the pencil up
        k = seg(lt, 5.0, 5.9); cr = math.sin(k * math.pi) * .7
        tip = (lerp(sx + 110, kx - 40, ss(seg(k, .5, 1))), lerp(G, G - 30, ss(seg(k, .5, 1))))
        stick_with_pencil(fr, dict(st, face=1, crouch=cr, lean=.25 * math.sin(k * math.pi)), tip, seed)
        return fr
    # draw KALYAKA
    kal, _ = kalyaka(dict(x=kx, face=-1))
    if lt < 8.6:
        k = seg(lt, 5.9, 8.5); ks, tip = reveal(kal, k); ks = peel(ks, 0); fr.add(ks, seed + 3)
        tip = (tip[0], G - (G - tip[1]) * .12) if tip else (kx, G)
        stick_with_pencil(fr, dict(st, face=1, crouch=.62, lean=.35, smile=.6), tip, seed); return fr
    kp = back(seg(lt, 8.6, 9.3)); shake = math.sin(lt * 40) * 10 * seg(lt, 9.3, 9.5) * (1 - seg(lt, 9.8, 10))
    if lt < 10:
        kal, _ = kalyaka(dict(x=kx + shake, face=-1, closed=9.85 < lt < 9.95, squash=.3 * math.sin(lt * 40) * (shake != 0)))
        fr.add(peel(kal, kp), seed + 3); fr.shadows.append((kx, 70 * kp + 10, int(70 * kp)))
        stick_with_pencil(fr, dict(st, face=1, crouch=.62 * (1 - seg(lt, 8.6, 9.6)), lean=.35 * (1 - seg(lt, 8.6, 9.6)), smile=.8),
                          (kx - 60, G - 40 + 50 * seg(lt, 8.6, 9.6)), seed)
        return fr
    # wave + bounce
    w = seg(lt, 10.2, 10.6); ws = math.sin((lt - 10.2) * 7.5)
    bounce = abs(math.sin((lt - 10) * 5.2)); hop = bounce * 26
    kal, _ = kalyaka(dict(x=kx, face=0, hop=hop, squash=(.6 if hop < 5 else -.4) * (1 if lt > 10.05 else 0), wag=lt * 14))
    fr.add(kal, seed + 3); fr.shadows.append((kx, 70 - hop * .6, 70))
    sh = (sx, G - 248)
    hr = (sx + 70 + 22 * ws * w, sh[1] - 70 * w + 96 * (1 - w))
    sk, rig = stick(dict(st, face=0, smile=1, hR=hr, flutter=lt))
    fr.add(sk, seed)
    fr.add(pencil((sx - 190, G - 2), (1, -.04)), seed + 4)        # pencil lying on the page
    fr.post.append(("plaque", "Стик и Каракуля", seg(t, 10, 10.4) * (1 - seg(t, 14.2, 14.6))))
    return fr

def clip2(t, lt0, lt, seed):
    fr = None; sx0 = 930; rx = 1180
    if lt < 10:
        keys = [(0, (950, 640, 1.0, "")), (4, (1000, 640, 1.18, "")), (8.4, (980, 620, 1.05, "")),
                (10, (rx, -400, 1.0, ""))]
        cam = cam_path(lt0, keys); fr = Frame(cam)
        # rocket
        rk = rocket(rx, G, filled=1.0 if lt > 3.9 else 0)
        base = G; sq = 0
        if lt > 8.0:
            sq = math.sin(seg(lt, 8.0, 8.6) * math.pi) * .8 if lt < 8.6 else 0
            base = G - (ss(seg(lt, 8.6, 10)) ** 1.6) * 1500
        if lt < 3.9:
            rs, tip = reveal(rk, seg(lt, .4, 3.8)); fr.add(rs, seed + 5)
        else:
            fr.add(rocket(rx, base, faces=lt > 8.0, squash=sq), seed + 5)
            fr.shadows.append((rx, 140 * (1 - seg(base, G, G - 500) * 0 - clamp((G - base) / 500)) + 1, int(70 * (1 - clamp((G - base) / 400)))))
            if base < G - 5:                     # smoke puffs
                for i in range(6):
                    py = base + 30 + i * 45; r = 18 + i * 8
                    fr.add([S(circle(rx + (hsh(i, 3) - .5) * 60, py, r, 18), (120, 120, 130), 4, cut=False, fill=(235, 232, 225))], seed + 70 + i)
        # kalyaka
        if lt < 6.0:
            if lt < 4.5: kx, ph, fc, hop = 640, None, 1, 0
            else:
                kx, ph, St, v = walkx(lt, 4.5, 5.6, 640, rx - 110); ph = (ph or 0) * 1.0; fc = 1
                hop = 0
                if lt > 5.6:
                    k = seg(lt, 5.6, 6.0); kx = lerp(rx - 110, rx, k); hop = math.sin(k * math.pi) * 120; ph = None
            if not (lt > 5.85):
                kal, _ = kalyaka(dict(x=kx, face=fc, phase=ph, hop=hop, wag=lt * 12, squash=.4 if 5.55 < lt < 5.65 else 0))
                fr.add(kal, seed + 3); fr.shadows.append((kx, 70 - hop * .3, 60))
        # stick
        if lt < 4.2:
            tip = tip if lt < 3.9 and tip else (rx - 70, G - 80)
            stick_with_pencil(fr, dict(x=sx0, face=1, lean=.2, smile=.6, crouch=.2), tip if lt < 3.9 else (sx0 + 70, G - 60), seed)
            fr.shadows.append((sx0, 70, 70))
        elif lt < 8.0:
            if lt < 6.0:
                sk, _ = stick(dict(x=sx0, face=1, smile=.9)); fr.add(sk, seed); fr.shadows.append((sx0, 70, 70))
            else:
                x, ph, St, v = walkx(lt, 6.0, 7.4, sx0, rx - 120)
                jump = 0; feet = None
                if lt > 7.4:
                    k = seg(lt, 7.4, 8.0); x = lerp(rx - 120, rx - 20, k); jump = math.sin(k * math.pi) * 110
                    ph = None
                if lt < 7.9:
                    hl = (rx - 70, G - 150) if lt > 7.3 else None
                    sk, _ = stick(dict(x=x, face=1, phase=ph, stride=St, v=v, smile=.9, jump=jump, hL=hl, flutter=lt,
                                       crouch=.5 * seg(lt, 7.2, 7.4) * (1 - seg(lt, 7.4, 7.6))))
                    fr.add(sk, seed); fr.shadows.append((x, 70 - jump * .3, 70))
        if lt < 4.6: fr.post.append(("plaque", "Приключения", seg(lt0, .6, 1.0) * (1 - seg(lt0, 4.2, 4.6))))
        return fr
    # 8-bit world flight
    k = seg(lt0, 10, 15); rxw = lerp(-300, 2300, k); ryw = 560 + math.sin(lt0 * 2.4) * 40
    cam = Cam(lerp(200, 1900, ss(k)), 560, 1.0); fr = Frame(cam)
    fr.pix.append(("world", cam, lt0))
    for i, cxw in enumerate((600, 1200, 1800)):
        if lt0 < 10 + 1 + i * 1.3: fr.pix.append(("coin", cxw, 560 + math.sin(i) * 30, lt0))
        elif lt0 < 10 + 1.5 + i * 1.3: fr.pix.append(("sparkle", cxw, 560, lt0 - (10 + 1 + i * 1.3)))
    rk = rocket(0, 0, faces=True)
    rk = [dict(s, pts=[(rxw + y * .25 * 0 + (y - (-150)) * 0 + x * math.cos(1.25) - (y + 150) * math.sin(1.25) * 1,
                        ryw + x * math.sin(1.25) + (y + 150) * math.cos(1.25)) for x, y in s["pts"]]) for s in rk]
    fr.add(rk, seed + 5)
    for i in range(5):
        px_ = rxw - 200 - i * 70; fr.add([S(circle(px_, ryw + math.sin(i + lt0 * 3) * 10, 16 + i * 6, 16), (120, 120, 130), 4, cut=False, fill=(235, 232, 225))], seed + 80 + i)
    return fr

def clip3(t, lt0, lt, seed):
    cam = cam_path(lt0, [(0, (900, 560, 1.0, "")), (5, (1080, 560, 1.0, "")), (6, (1080, 520, 1.0, "")),
                          (10, (1060, 470, 1.0, "")), (15, (1100, 480, 1.22, ""))])
    fr = Frame(cam); sx = 560; kx0 = 1300
    cols = [(232, 60, 60), (246, 146, 40), (246, 210, 50), (80, 186, 90), (60, 120, 225), (150, 90, 200)]
    cx, cy = 1250, G; tip = None
    arcs = []
    for i, c in enumerate(cols):
        r = 520 - i * 30
        arcs.append(S(circle(cx, cy, r, 40, math.pi, 2 * math.pi), c, 26, cut=False))
    if lt < 4.8:
        n = seg(lt, .4, 4.6) * 6; shown = []
        for i in range(6):
            if n >= i + 1: shown.append(arcs[i])
            elif n > i:
                s2, tip = reveal([arcs[i]], n - i); shown += s2
        fr.add(shown, seed + 9)
    else: fr.add(arcs, seed + 9)
    # balloons
    bx = [1110, 1250, 1390]; bc = [(232, 60, 60), (246, 210, 50), (60, 120, 225)]
    for i in range(3):
        t0 = 5.2 + i * 1.4
        if lt < t0: break
        fl = ss(seg(lt, t0 + 1.0, t0 + 1.9)); by = lerp(G - 160, G - 400, fl) + math.sin(lt * 2 + i) * 6 * fl
        bl = balloon(bx[i], by, bc[i])
        if lt < t0 + 1.0:
            bl, tp = reveal(bl, seg(lt, t0, t0 + 1.0)); tip = tp or tip
        fr.add(bl, seed + 20 + i)
        if 13.0 <= lt and i == 2: fr.pix.append(("burst", cam, bx[2], by, lt - 13.0))
    # pencil: draws by itself (magic) — stick conducts it
    if lt < 9.4 and tip is not None:
        ptip = tip
    else:
        ptip = None
    # stick
    if lt < 10:
        if ptip is not None:
            fr.add(pencil(ptip, (.45, -1)), seed + 40)
            rig = stick(dict(x=sx, face=1))[1]
            dx, dy = ptip[0] - rig["sh"][0], ptip[1] - rig["sh"][1]; d = math.hypot(dx, dy) or 1
            hr = (rig["sh"][0] + dx / d * 104, rig["sh"][1] + dy / d * 104)
            sk, _ = stick(dict(x=sx, face=1, hR=hr, smile=.8, lean=.08)); fr.add(sk, seed)
        else:
            sk, _ = stick(dict(x=sx, face=1, smile=.8)); fr.add(sk, seed)
            fr.add(pencil((sx - 50, G - 40), (-.3, -1)), seed + 40)
    else:
        idx = 0 if lt < 11.5 else 1 if lt < 13.0 else 2
        k = seg(lt, [10.0, 11.5, 13.0][idx], [10.0, 11.5, 13.0][idx] + .35)
        by = G - 400
        rig = stick(dict(x=sx + 100, face=1))[1]
        tx, ty = bx[idx], by
        dx, dy = tx - rig["sh"][0], ty - rig["sh"][1]; d = math.hypot(dx, dy) or 1
        hr = (rig["sh"][0] + dx / d * 100 * k + 30 * (1 - k), rig["sh"][1] + dy / d * 100 * k + 90 * (1 - k))
        x, ph, St, v = walkx(lt, 10.0, 10.9, sx, sx + 100)
        sk, _ = stick(dict(x=x, face=1, phase=ph, stride=St, v=v, hR=hr, smile=1, lean=.06)); fr.add(sk, seed)
        fr.add(pencil((sx - 50, G - 40), (-.3, -1)), seed + 40)
    fr.shadows.append((sx if lt < 10 else sx + 100, 70, 70))
    # kalyaka hops under each new balloon, then nods
    kx = kx0; hop = 0; nod = 0
    for i in range(3):
        t0 = 5.2 + i * 1.4 + 1.0
        if lt > t0:
            k = seg(lt, t0, t0 + .5); kx = lerp(kx if i else kx0 + 120, bx[i] + 40, ss(k)); hop = math.sin(k * math.pi) * 60
    if lt < 6.2: kx = kx0 + 120
    if lt > 10:
        kx = bx[2] + 40; hop = 0
        for tt in (10.0, 11.5, 13.0):
            nod = max(nod, math.sin(clamp((lt - tt - .25) / .4) * math.pi))
    kal, _ = kalyaka(dict(x=kx, face=-1, hop=hop, nod=nod, wag=lt * 9)); fr.add(kal, seed + 3)
    fr.shadows.append((kx, 70 - hop * .4, 60))
    if lt0 < 4.6: fr.post.append(("plaque", "Открытия", seg(lt0, .4, .8) * (1 - seg(lt0, 4.2, 4.6))))
    return fr

def clip4(t, lt0, lt, seed):
    cam = cam_path(lt0, [(0, (900, 600, 1.0, "")), (5, (860, 610, 1.08, "")), (10, (720, 690, 1.38, "")),
                          (15, (980, 560, .95, ""))])
    fr = Frame(cam); fr.night = .62 * ss(seg(lt0, .4, 4.6)); sx = 600; kx = 800
    mn = moon(330, 230)
    if lt < 3.2:
        ms, tip = reveal(mn, seg(lt, .5, 3.0)); fr.add(ms, seed + 9)
        tip = tip or (330, 230)
        fr.add(pencil(tip, (.5, -1)), seed + 40)
    else: fr.add(mn, seed + 9)
    if lt0 > 3.0: fr.pix.append(("stars", cam, lt0))
    # kalyaka: yawn, turn twice, curl up
    face = -1; curl = 0; closed = False; yawn = 0
    if 5.0 < lt < 6.0: yawn = math.sin(seg(lt, 5.0, 6.0) * math.pi)
    if 6.0 <= lt < 7.0: face = -1 if int((lt - 6.0) * 4) % 2 == 0 else 1
    if lt >= 7.0: curl = ss(seg(lt, 7.0, 7.5)); closed = lt > 7.3; face = -1
    kal, kc = kalyaka(dict(x=kx, face=face, curl=curl, closed=closed, yawn=yawn, wag=lt * (6 * (1 - curl)), nod=.5 * seg(lt, 9.2, 9.5) * (1 - seg(lt, 9.6, 9.9))))
    fr.add(kal, seed + 3); fr.shadows.append((kx, 70, 60))
    blanket = [S([(kx - 12, G - 4), (kx - 6, G - 60), (kx + 40, G - 76), (kx + 78, G - 50), (kx + 92, G - 6), (kx - 12, G - 4)], INK, 5, fill=(250, 214, 120)),
               S([(kx + 8, G - 44), (kx + 74, G - 40)], (200, 150, 70), 4, cut=False), S([(kx + 4, G - 22), (kx + 84, G - 22)], (200, 150, 70), 4, cut=False)]
    if lt > 7.7:
        bs, btip = reveal(blanket, seg(lt, 7.7, 9.0)) if lt < 9.0 else (blanket, None); fr.add(bs, seed + 60)
    else: btip = None
    # stick
    if lt < 7.2:
        sk, _ = stick(dict(x=sx, face=1, smile=.6, hR=(sx + 120, 300) if lt < 3.0 else None)); fr.add(sk, seed)
    elif lt < 10.0:
        cr = .9 * ss(seg(lt, 7.2, 7.7)) * (1 - ss(seg(lt, 9.85, 10.0)))
        feet = [(sx - 30, G), (sx + 40, G - 2)]
        if lt < 9.0 and btip:
            stick_with_pencil(fr, dict(x=sx, face=1, crouch=cr, lean=.35, smile=.6, feet=feet), btip, seed)
        else:
            hr = (kx - 30 + 15 * math.sin(lt * 6), kc[1] - 30) if 9.1 < lt < 9.9 else None
            sk, _ = stick(dict(x=sx, face=1, crouch=cr, lean=.3 * (1 if hr else .4), smile=.8, feet=feet, hR=hr)); fr.add(sk, seed)
    else:
        x, ph, St, v = walkx(lt, 12.6, 13.6, sx, sx - 130)
        f = 0 if lt < 12.5 or lt > 13.7 else -1
        w = seg(lt, 10.5, 10.9) * (1 - seg(lt, 12.3, 12.6)) + seg(lt, 13.8, 14.1); ws = math.sin((lt - 10.5) * 4.5)
        sh = (x, G - 248)
        hr = (x + 70 + 22 * ws * w, sh[1] - 70 * w + 96 * (1 - w)) if w > 0 else None
        sk, _ = stick(dict(x=x, face=f, phase=ph if f else None, stride=St, v=v, smile=1, hR=hr, flutter=lt)); fr.add(sk, seed)
    fr.shadows.append((sx if lt < 12.6 else sx - 130 * ss(seg(lt, 12.6, 13.6)), 70, 70))
    if lt0 < 4.6: fr.post.append(("plaque", "Вечерние истории", seg(lt0, .4, .8) * (1 - seg(lt0, 4.2, 4.6))))
    return fr

# ---------------------------------------------------------------- subtitles
SUBS = []
def load_subs():
    p = os.path.join(HERE, "subtitles.srt")
    blocks = open(p, encoding="utf-8").read().strip().split("\n\n")
    def ts(s):
        h, m, r = s.split(":"); sec, ms = r.split(","); return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000
    for b in blocks:
        ln = b.strip().split("\n"); a, c = ln[1].split(" --> "); SUBS.append((ts(a), ts(c), " ".join(ln[2:])))
HOT = {"Каракуля.", "оживает.", "Раз.", "Два.", "Три!", "Подписывайтесь", "встречи!", "Приключения…", "открытия"}

# pop-up text: each phrase pops in word by word, in free space near the action
POS = {1: (.50, .17), 2: (.50, .17), 3: (.30, .20), 4: (.62, .22), 5: (.50, .11), 6: (.74, .17),
       7: (.32, .16), 8: (.66, .16), 9: (.50, .27), 10: (.50, .20), 11: (.34, .16), 12: (.62, .26),
       13: (.30, .30), 14: (.50, .26), 15: (.72, .30), 16: (.68, .17), 17: (.68, .30), 18: (.27, .13),
       19: (.27, .25), 20: (.27, .16)}
TINTS = [(255, 255, 255), (255, 214, 40), (120, 210, 255), (255, 150, 190), (150, 235, 140)]
_cache = {}
def word_img(word, col, size):
    key = (word, col, size)
    if key in _cache: return _cache[key]
    f = ImageFont.truetype(FONT, size); tw = int(f.getlength(word)) + 50
    im = Image.new("RGBA", (tw, int(size * 1.6)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.text((29, 19), word, font=f, fill=(20, 20, 50, 150), stroke_width=12, stroke_fill=(20, 20, 50, 150))
    d.text((24, 12), word, font=f, fill=col, stroke_width=11, stroke_fill=(32, 30, 70))
    _cache[key] = im; return im

def draw_subs(img, t):
    for n, (a, b, txt) in enumerate(SUBS, 1):
        if not (a <= t < b + .2): continue
        words = txt.split(" "); hot = any(w in HOT for w in words)
        size = 118 if hot else 96
        base = TINTS[n % len(TINTS)] if not hot else (255, 214, 40)
        ims = [word_img(w, (255, 214, 40) if w in HOT else base, size) for w in words]
        gap = int(size * .36) - 50; total = sum(i.width for i in ims) + gap * (len(ims) - 1)
        px, py = POS.get(n, (.5, .2)); cx, cy = W * px, H * py
        fit = min(1.0, W * .86 / max(total, 1)); total *= fit
        cx = min(max(cx, total / 2 + 50), W - total / 2 - 50)
        x = cx - total / 2
        out = seg(t, b - .05, b + .2)                     # pop-out: shrink away
        for i, (w, im) in enumerate(zip(words, ims)):
            k = t - (a + i * .13)
            if k < 0: x += (im.width + gap) * fit; continue
            sc = back(seg(k, 0, .32), 3.2) * (1 - out) * fit
            if sc <= .02: x += (im.width + gap) * fit; continue
            wob = math.sin(t * 3 + n + i) * 2.5
            rot = ((hsh(i, n) - .5) * 12) * (1 - seg(k, 0, .32) * .5) + wob * .3
            s2 = im.resize((max(2, int(im.width * sc)), max(2, int(im.height * sc))), Image.BILINEAR).rotate(rot, expand=True, resample=Image.BILINEAR)
            yb = cy + math.sin(t * 4 + i) * 4 - (1 - seg(k, 0, .2)) * 30
            img.alpha_composite(s2, (int(x + im.width * fit / 2 - s2.width / 2), int(yb - s2.height / 2)))
            x += (im.width + gap) * fit

def draw_plaque(img, text, k):
    if k <= 0: return
    f = ImageFont.truetype(FONT2, 54); tw = int(f.getlength(text)) + 110
    im = Image.new("RGBA", (tw + 20, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([10, 14, tw + 10, 104], 26, fill=(32, 30, 70, 90))
    d.rounded_rectangle([4, 6, tw + 4, 96], 26, fill=(255, 255, 255), outline=INK, width=5)
    d.ellipse([28, 34, 62, 68], fill=RED); d.text((80, 18), text, font=f, fill=INK)
    x = int(-tw - 40 + (tw + 100) * back(k, 1.6)); img.alpha_composite(im, (x, H - 150))

# ---------------------------------------------------------------- 8-bit layer
def draw_pix(d, item, cam):
    kind = item[0]
    if kind == "world":
        _, c, lt0 = item
        for i in range(-2, 10):                            # far clouds (slow)
            x = (i * 520 - c.cx * .35) % 5200 - 600
            sprite_c(d, CLOUD, x, 170 + (i % 3) * 90, 14)
        sx = W - 260 - (c.cx - 200) * .08; sprite_c(d, SUN, sx, 180, 18)
        px = 30; off = -(c.cx * 1.25) % (px * 2)            # 8-bit ground (fast)
        for j in range(4):
            for i in range(-2, W // px + 3):
                col = PAL["G"] if j == 0 else PAL["B"] if (i + j) % 2 else (125, 80, 50)
                x = i * px + off; y = H - 4 * px + j * px
                d.rectangle([x, y, x + px - 1, y + px - 1], fill=col)
        for i in range(-1, 8):                             # pipes / blocks mid layer
            x = (i * 640 - c.cx * .9) % 5000 - 400
            for b in range(3):
                d.rectangle([x + b * 40, H - 4 * px - 40, x + b * 40 + 39, H - 4 * px - 1], fill=(240, 170, 60), outline=(40, 40, 60), width=4)
    elif kind == "coin":
        _, x, y, lt0 = item; sx, sy = cam.T(x, y)
        sq = abs(math.cos(lt0 * 6)); px = 10
        rows = [r[:] for r in COIN]
        sprite_c(d, rows, sx, sy, px)
    elif kind == "sparkle":
        _, x, y, k = item; sx, sy = cam.T(x, y)
        for a in range(8):
            r = 20 + 140 * k; ang = a * math.pi / 4
            s_ = 14 * (1 - k) + 2
            d.rectangle([sx + math.cos(ang) * r - s_, sy + math.sin(ang) * r - s_, sx + math.cos(ang) * r + s_, sy + math.sin(ang) * r + s_], fill=(255, 220, 60))
    elif kind == "burst":
        _, c, x, y, k = item
        if k > 1.6: return
        sx, sy = c.T(x, y); kk = clamp(k / 1.2)
        for a in range(10):
            ang = a * math.pi / 5 + .3; r = (40 + 220 * crash(kk)) * c.z
            px = max(3, int(9 * (1 - clamp((k - .9) / .7)) * c.z))
            sprite_c(d, STAR, sx + math.cos(ang) * r, sy + math.sin(ang) * r, px)
    elif kind == "stars":
        _, c, lt0 = item
        for i, (wx, wy) in enumerate(((180, 120), (480, 90), (560, 300), (120, 330), (700, 170), (260, 420))):
            if lt0 < 3.0 + i * .25: continue
            sx, sy = c.T(wx, wy); tw = (int(lt0 * 4 + i) % 3)
            sprite_c(d, STAR, sx, sy, [5, 8, 11][tw] * c.z, override={"X": (255, 240, 170), "Y": (255, 250, 220)})

# ---------------------------------------------------------------- page flip
FLIPS = [30.0]
def page_flip(img, t, bg):
    for b in FLIPS:
        if b - .28 <= t < b + .28:
            k = (t - (b - .28)) / .56; d = ImageDraw.Draw(img)
            sheet = Image.new("RGB", (W, H), PAPER); sd = ImageDraw.Draw(sheet)
            y = 60
            while y < H: sd.line([(0, y), (W, y)], fill=(158, 190, 228), width=3); y += 46
            sd.line([(170, 0), (150, H)], fill=(226, 112, 112), width=4)
            mask = Image.new("L", (W, H), 0); md = ImageDraw.Draw(mask)
            if k < .5:
                e = W * (1 - ss(k * 2)); md.polygon([(e, 0), (W, 0), (W, H), (e - 120, H)], fill=255)
                img.paste(sheet, (0, 0), mask)
                d.line([(e, 0), (e - 120, H)], fill=(170, 165, 150), width=10)
            else:
                e = W * (1 - ss((k - .5) * 2)); md.polygon([(0, 0), (e, 0), (e - 120, H), (0, H)], fill=255)
                img.paste(sheet, (0, 0), mask)
                d.line([(e, 0), (e - 120, H)], fill=(170, 165, 150), width=10)


# ---------------------------------------------------------------- stickers (pop-up pictures)
def _star(d, c, r, col):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5; rr = r if i % 2 == 0 else r * .45
        pts.append((c + rr * math.cos(a), c + rr * math.sin(a)))
    d.polygon(pts, fill=col, outline=INK, width=9)
def make_sticker(kind, size=260):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = size / 2; r = size * .34
    if kind == "star": _star(d, c, r * 1.15, YEL)
    elif kind == "bolt":
        pts = [(c + .1 * r, c - 1.2 * r), (c - .7 * r, c + .15 * r), (c - .05 * r, c + .15 * r), (c - .25 * r, c + 1.2 * r), (c + .75 * r, c - .2 * r), (c + .08 * r, c - .2 * r)]
        d.polygon(pts, fill=YEL, outline=INK, width=9)
    elif kind == "bulb":
        d.ellipse([c - r * .85, c - r * 1.15, c + r * .85, c + r * .5], fill=(255, 236, 120), outline=INK, width=9)
        d.rectangle([c - r * .4, c + r * .45, c + r * .4, c + r * 1.0], fill=(170, 170, 180), outline=INK, width=8)
        d.line([(c - r * .3, c - r * .2), (c, c + r * .3), (c + r * .3, c - r * .2)], fill=INK, width=7)
    elif kind == "clock":
        d.rectangle([c - r * .18, c - r * 1.25, c + r * .18, c - r * .9], fill=RED, outline=INK, width=7)
        d.ellipse([c - r, c - r * .95, c + r, c + r * 1.05], fill=PAPER, outline=INK, width=10)
        d.line([(c, c + .05 * r), (c + r * .55, c - r * .45)], fill=RED, width=10); d.line([(c, c + .05 * r), (c, c - r * .6)], fill=INK, width=8)
    elif kind == "bell":
        d.chord([c - r, c - r * 1.1, c + r, c + r * .9], 180, 360, fill=YEL, outline=INK, width=9)
        d.rectangle([c - r, c - r * .2, c + r, c + r * .55], fill=YEL); d.line([(c - r, c - r * .2), (c - r * 1.1, c + r * .6)], fill=INK, width=9)
        d.line([(c + r, c - r * .2), (c + r * 1.1, c + r * .6)], fill=INK, width=9)
        d.rounded_rectangle([c - r * 1.25, c + r * .5, c + r * 1.25, c + r * .78], 8, fill=YEL, outline=INK, width=8)
        d.ellipse([c - r * .25, c + r * .75, c + r * .25, c + r * 1.15], fill=(230, 150, 40), outline=INK, width=7)
    elif kind == "play":
        d.ellipse([c - r, c - r, c + r, c + r], fill=BLUE, outline=INK, width=10)
        d.polygon([(c - r * .3, c - r * .5), (c - r * .3, c + r * .5), (c + r * .55, c)], fill=PAPER)
    elif kind == "heart":
        d.ellipse([c - r, c - r * .8, c + r * .05, c + r * .25], fill=RED, outline=INK, width=9)
        d.ellipse([c - r * .05, c - r * .8, c + r, c + r * .25], fill=RED, outline=INK, width=9)
        d.polygon([(c - r * .97, c - r * .1), (c, c + r * 1.05), (c + r * .97, c - r * .1)], fill=RED)
        d.line([(c - r * .97, c - r * .1), (c, c + r * 1.05), (c + r * .97, c - r * .1)], fill=INK, width=9)
        d.rectangle([c - r * .5, c - r * .35, c + r * .5, c + r * .1], fill=RED)
    elif kind == "excl":
        d.ellipse([c - r, c - r, c + r, c + r], fill=RED, outline=INK, width=10)
        d.rounded_rectangle([c - r * .16, c - r * .62, c + r * .16, c + r * .25], 10, fill=PAPER)
        d.ellipse([c - r * .17, c + r * .38, c + r * .17, c + r * .72], fill=PAPER)
    elif kind == "zzz":
        f = ImageFont.truetype(FONT, int(r * .9))
        for i, (dx, dy, sc) in enumerate(((-.5, .5, 1), (.15, -.05, .8), (.65, -.55, .6))):
            ff = ImageFont.truetype(FONT, int(r * .9 * sc))
            d.text((c + dx * r, c + dy * r), "Z", font=ff, fill=(140, 200, 255), anchor="mm", stroke_width=7, stroke_fill=INK)
    elif kind == "coin":
        sprite_c(d, COIN, c, c, int(r * .33))
    elif kind == "pencil":
        d.polygon([(c - r * 1.2, c + r * .9), (c - r * .75, c + r * .45), (c + r * .9, c - r * 1.2), (c + r * 1.25, c - r * .85), (c - r * .35, c + r * .85)], fill=YEL, outline=INK, width=8)
        d.polygon([(c - r * 1.2, c + r * .9), (c - r * .75, c + r * .45), (c - r * .35, c + r * .85)], fill=WOOD, outline=INK, width=7)
    elif kind == "balloon":
        d.ellipse([c - r * .75, c - r * 1.1, c + r * .75, c + r * .6], fill=(60, 120, 225), outline=INK, width=9)
        d.line([(c, c + r * .62), (c + 10, c + r * 1.25)], fill=INK, width=5)
    elif kind == "moon":
        d.ellipse([c - r, c - r, c + r, c + r], fill=(255, 236, 150), outline=INK, width=9)
        d.ellipse([c - r * .35, c - r * 1.15, c + r * 1.35, c + r * .55], fill=(0, 0, 0, 0))
        im2 = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(im2).ellipse([c - r * .35, c - r * 1.15, c + r * 1.35, c + r * .55], fill=(255, 255, 255, 255))
        a = im.getchannel("A"); a.paste(0, mask=im2.getchannel("A")); im.putalpha(a)
        d.arc([c - r * .35, c - r * 1.15, c + r * 1.35, c + r * .55], 120, 250, fill=INK, width=9)
    a = im.getchannel("A")
    border = a.filter(ImageFilter.MaxFilter(17))
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sh = Image.new("RGBA", (size, size), (30, 25, 50, 0)); sh.putalpha(border.point(lambda v: int(v * .35)))
    out.alpha_composite(sh, (6, 9)); wh = Image.new("RGBA", (size, size), (255, 255, 255, 0)); wh.putalpha(border)
    out.alpha_composite(wh); out.alpha_composite(im); return out
_st = {}
def sticker(kind):
    if kind not in _st: _st[kind] = make_sticker(kind)
    return _st[kind]

# (start, duration, kind, x, y, size_px, base_rotation)
POPS = [(3.75, 1.5, "excl", .64, .38, 170, 12), (9.3, 1.6, "heart", .70, .46, 150, -10), (9.5, 1.4, "star", .78, .34, 120, 15),
        (11.6, 2.4, "star", .16, .30, 150, -12), (11.8, 2.2, "pencil", .86, .62, 190, 8),
        (17.6, 2.6, "clock", .82, .30, 210, 10), (21.0, 2.0, "bolt", .18, .40, 190, -14), (24.0, 1.0, "star", .80, .40, 150, 10),
        (26.0, 3.0, "coin", .12, .22, 140, 0), (31.2, 2.6, "bulb", .14, .30, 210, -10), (34.0, 2.0, "balloon", .86, .24, 170, 12),
        (43.0, 1.6, "excl", .86, .56, 150, 10), (46.2, 3.5, "zzz", .58, .55, 200, 0), (47.0, 3.0, "moon", .88, .58, 170, -8),
        (52.0, 4.5, "bell", .70, .40, 230, 12), (52.4, 4.1, "play", .86, .62, 200, -8), (55.0, 2.0, "heart", .62, .66, 140, 0)]

def draw_pops(img, t):
    for t0, dur, kind, px, py, size, rot in POPS:
        k = t - t0
        if k < 0 or k > dur: continue
        sc = back(seg(k, 0, .3), 3.0) * (1 - back(seg(k, dur - .22, dur), 2.0) if k > dur - .22 else 1)
        sc *= size / 260 * (1 + .04 * math.sin(k * 6))
        if sc < .03: continue
        im = sticker(kind); ang = rot + math.sin(k * 3.2) * 6 + (1 - seg(k, 0, .3)) * 40
        s2 = im.resize((max(2, int(260 * sc)), max(2, int(260 * sc))), Image.BILINEAR).rotate(ang, expand=True, resample=Image.BILINEAR)
        img.alpha_composite(s2, (int(W * px - s2.width / 2), int(H * py - s2.height / 2 - math.sin(k * 2.5) * 6)))

# ---------------------------------------------------------------- comic effects
BURSTS = [(10.55, .9, .47, .52), (43.0, .9, .72, .30), (3.6, .6, .50, .55)]
def draw_bursts(img, t):
    for t0, dur, px, py in BURSTS:
        k = t - t0
        if not (0 <= k < dur): continue
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); cx, cy = W * px, H * py
        a = int(150 * (1 - k / dur))
        for i in range(28):
            ang = i * 2 * math.pi / 28 + hsh(i, int(t * 12)) * .1
            r0 = 260 + 120 * hsh(i, 3) + 300 * k; r1 = r0 + 260 + 200 * hsh(i, 5)
            wd = 6 + 10 * hsh(i, 8)
            p0 = (cx + math.cos(ang) * r0, cy + math.sin(ang) * r0); p1 = (cx + math.cos(ang) * r1, cy + math.sin(ang) * r1)
            pa = (cx + math.cos(ang + .02) * r1, cy + math.sin(ang + .02) * r1)
            d.polygon([p0, p1, pa], fill=(30, 30, 40, a)); d.line([p0, p1], fill=(30, 30, 40, a), width=int(wd))
        img.alpha_composite(ov)

def speed_lines(img, t):
    if 25.2 < t < 30.0:            # horizontal streaks in the 8-bit flight
        d = ImageDraw.Draw(img)
        for i in range(14):
            y = 120 + (i * 61) % 760; L = 160 + 220 * hsh(i, 2); x = (W - ((t * 2600 + i * 377) % (W + 800))) + 200
            d.line([(x, y), (x + L, y)], fill=(120, 140, 170), width=4)
    if 23.6 < t < 25.0:            # vertical streaks during launch
        d = ImageDraw.Draw(img)
        for i in range(16):
            x = 80 + (i * 113) % (W - 160); L = 140 + 200 * hsh(i, 4); y = ((t * 3000 + i * 271) % (H + 600)) - 300
            d.line([(x, y), (x, y + L)], fill=(150, 150, 165), width=4)

FLASH = [(3.6, .12), (10.55, .1), (24.6, .1), (43.0, .1)]
def flash(img, t):
    for t0, dur in FLASH:
        if t0 <= t < t0 + dur: return Image.blend(img, Image.new("RGB", (W, H), (255, 255, 255)), .65 * (1 - (t - t0) / dur))
    return img

def shake(t):
    a = 0
    if 23.6 < t < 24.8: a = 9 * (1 - seg(t, 24.2, 24.8))
    if 10.55 < t < 10.95: a = 14 * (1 - seg(t, 10.55, 10.95))
    if 43.0 < t < 43.35: a = 8
    return (math.sin(t * 91) * a, math.cos(t * 77) * a)

# ---------------------------------------------------------------- transitions
def sticker_burst(img, t, b, col, kinds):
    k = (t - (b - .45)) / .9
    if not (0 <= k <= 1): return img
    cover = math.sin(k * math.pi)                       # 0 -> 1 (at the cut) -> 0
    rr = cover * math.hypot(W, H) * .56
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    d.ellipse([W / 2 - rr, H / 2 - rr, W / 2 + rr, H / 2 + rr], fill=col + (255,))
    for i in range(9):                                  # comic rays inside the iris
        ang = i * 2 * math.pi / 9 + t * .8; r1 = rr * 1.2
        d.polygon([(W / 2, H / 2), (W / 2 + math.cos(ang) * r1, H / 2 + math.sin(ang) * r1),
                   (W / 2 + math.cos(ang + .18) * r1, H / 2 + math.sin(ang + .18) * r1)], fill=tuple(min(255, v + 25) for v in col) + (255,))
    m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).ellipse([W / 2 - rr, H / 2 - rr, W / 2 + rr, H / 2 + rr], fill=255)
    rays = Image.new("RGBA", (W, H), (0, 0, 0, 0)); rays.paste(ov, (0, 0), m)
    img = img.convert("RGBA"); img.alpha_composite(rays)
    for i, kind in enumerate(kinds):                     # pictures pop in from the centre
        kk = clamp(cover * 1.4 - i * .05)
        if kk <= 0: continue
        ang = i * 2 * math.pi / len(kinds) + .4; dist = 380 * kk
        sz = int(260 * back(kk, 2.4) * 1.05)
        if sz < 4: continue
        s2 = sticker(kind).resize((sz, sz), Image.BILINEAR).rotate((hsh(i, b) - .5) * 50 + t * 40 * (1 if i % 2 else -1), expand=True)
        img.alpha_composite(s2, (int(W / 2 + math.cos(ang) * dist - s2.width / 2), int(H / 2 + math.sin(ang) * dist * .62 - s2.height / 2)))
    return img.convert("RGB")

def pixel_dissolve(img, t, b):
    k = (t - (b - .4)) / .8
    if not (0 <= k <= 1): return img
    cover = math.sin(k * math.pi); px = 80; d = ImageDraw.Draw(img)
    cols = [(250, 205, 40), (70, 180, 80), (60, 120, 225), (232, 60, 60), (40, 40, 60)]
    for j in range(H // px + 1):
        for i in range(W // px + 1):
            if hsh(i * 31 + j, 5) < cover:
                d.rectangle([i * px, j * px, i * px + px - 1, j * px + px - 1], fill=cols[int(hsh(i, j) * 5)])
    return img

# ---------------------------------------------------------------- frame render
BG = None
def init():
    global BG
    if BG is None: BG = build_bg(); load_subs()

def render(t):
    init(); fr = scene(t); c = fr.cam
    sx_, sy_ = shake(t); c.cx += sx_ / c.z; c.cy += sy_ / c.z
    x0 = c.cx - W / 2 / c.z - BX0; y0 = c.cy - H / 2 / c.z - BY0
    img = BG.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + W / c.z, y0 + H / c.z))
    if fr.night > 0: img = Image.blend(img, Image.new("RGB", (W, H), NIGHT), fr.night)
    img = img.convert("RGBA")
    d = ImageDraw.Draw(img)
    for it in fr.pix:
        if it[0] == "world": draw_pix(d, it, c)
    sl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sl)
    for x, w_, a in fr.shadows: shadow(sd, c, x, w_, a)
    img.alpha_composite(sl); d = ImageDraw.Draw(img)
    for strokes, seed in fr.layers: draw_strokes(d, c, strokes, seed)
    for it in fr.pix:
        if it[0] != "world": draw_pix(d, it, c)
    if not any(it[0] == "world" for it in fr.pix): foreground(d, c)
    speed_lines(img, t); draw_bursts(img, t); draw_pops(img, t)
    for p in fr.post:
        if p[0] == "plaque": draw_plaque(img, p[1], p[2])
    draw_subs(img, t)
    out = img.convert("RGB"); page_flip(out, t, BG); out = flash(out, t)
    out = sticker_burst(out, t, 15.0, (250, 200, 40), ["star", "pencil", "heart", "bolt", "coin", "excl"])
    out = pixel_dissolve(out, t, 25.0)
    out = sticker_burst(out, t, 45.0, (40, 52, 110), ["moon", "zzz", "star", "bulb", "balloon", "heart"])
    if t > DUR - .5: out = Image.blend(out, Image.new("RGB", (W, H), (255, 255, 255)), 0)  # hold
    return out

def render_bytes(i): return render(i / FPS).tobytes()

if __name__ == "__main__":
    out = sys.argv[1]
    if "--preview" in sys.argv:
        ts = [float(v) for v in sys.argv[sys.argv.index("--preview") + 1].split(",")]
        for tt in ts: render(tt).save(f"{out}_{tt:05.1f}.png")
        sys.exit()
    n = int(DUR * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                           "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    with Pool(4, initializer=init) as pool:
        for i, b in enumerate(pool.imap(render_bytes, range(n), chunksize=4)):
            ff.stdin.write(b)
            if i % 120 == 0: print(f"frame {i}/{n}", flush=True)
    ff.stdin.close(); ff.wait()
