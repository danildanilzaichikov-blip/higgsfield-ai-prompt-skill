"""«Колобок» — 60-second storybook retelling.

Eight painted locations with a slow camera drift, characters as static sticker pictures
that pop in, pop-up captions describing what they do, speech bubbles, soft cross-dissolve
transitions with fairy dust. Frames are piped to ffmpeg.

usage: python3 render.py OUT.mp4 [--preview T1,T2,...]
"""
import math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, DUR = 1920, 1080, 24, 60.0
BW, BH, K = 2112, 1188, 1.5          # background canvas (bg coords) and its supersampling
INK = (44, 30, 26)
F_TITLE = os.path.join(HERE, "Ruslan.ttf")
F_TEXT = os.path.join(HERE, "Philosopher-Bold.ttf")

def clamp(v, a=0.0, b=1.0): return a if v < a else b if v > b else v
def seg(t, a, b): return clamp((t - a) / (b - a)) if b > a else float(t >= a)
def ss(x): x = clamp(x); return x * x * (3 - 2 * x)
def lerp(a, b, k): return a + (b - a) * k
def back(x, s=2.2):
    x = clamp(x); x -= 1; return x * x * ((s + 1) * x + s) + 1
def hsh(i, s):
    v = math.sin(i * 127.1 + s * 311.7) * 43758.5453; return v - math.floor(v)

# ============================================================ painter
class Pn:
    def __init__(s, w, h, k, bg=(0, 0, 0, 0), mode="RGBA"):
        s.k = k; s.im = Image.new(mode, (int(w * k), int(h * k)), bg); s.d = ImageDraw.Draw(s.im)
    def P(s, pts): return [(x * s.k, y * s.k) for x, y in pts]
    def poly(s, pts, fill, ol=INK, w=5):
        s.d.polygon(s.P(pts), fill=fill)
        if ol and w: s.d.line(s.P(pts + [pts[0]]), fill=ol, width=max(1, int(w * s.k)), joint="curve")
    def ell(s, cx, cy, rx, ry, fill, ol=INK, w=5):
        k = s.k; s.d.ellipse([(cx - rx) * k, (cy - ry) * k, (cx + rx) * k, (cy + ry) * k], fill=fill,
                             outline=ol if w else None, width=max(1, int(w * k)) if w else 0)
    def rect(s, x0, y0, x1, y1, fill, ol=INK, w=5, r=0):
        k = s.k
        if r: s.d.rounded_rectangle([x0 * k, y0 * k, x1 * k, y1 * k], r * k, fill=fill, outline=ol if w else None, width=max(1, int(w * k)) if w else 0)
        else: s.d.rectangle([x0 * k, y0 * k, x1 * k, y1 * k], fill=fill, outline=ol if w else None, width=max(1, int(w * k)) if w else 0)
    def line(s, pts, col=INK, w=5): s.d.line(s.P(pts), fill=col, width=max(1, int(w * s.k)), joint="curve")
    def rot_ell(s, cx, cy, rx, ry, ang, fill, ol=INK, w=5, n=40):
        a = math.radians(ang)
        pts = [(cx + rx * math.cos(t) * math.cos(a) - ry * math.sin(t) * math.sin(a),
                cy + rx * math.cos(t) * math.sin(a) + ry * math.sin(t) * math.cos(a)) for t in np.linspace(0, 2 * math.pi, n, endpoint=False)]
        s.poly(pts, fill, ol, w)

def wavy(x0, x1, y, amp, seed, step=40, f=.004):
    return [(x, y + amp * math.sin(x * f + seed) + amp * .4 * math.sin(x * f * 2.7 + seed * 2)) for x in range(int(x0), int(x1) + step, step)]

# ============================================================ characters (static pictures)
def finish_sprite(p, height, anchors, mirror=False):
    im = p.im; bb = im.getbbox(); im = im.crop(bb)
    ox, oy = bb[0] / p.k, bb[1] / p.k
    sc = height / (im.height / p.k) / p.k
    im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
    an = {k: ((x - ox) * p.k * sc, (y - oy) * p.k * sc) for k, (x, y) in anchors.items()}
    if mirror:
        im = ImageOps.mirror(im); an = {k: (im.width - x, y) for k, (x, y) in an.items()}
    pad = 16; a = im.getchannel("A")
    big = Image.new("L", (im.width + pad * 2, im.height + pad * 2), 0); big.paste(a, (pad, pad))
    border = big.filter(ImageFilter.MaxFilter(15))
    out = Image.new("RGBA", big.size, (0, 0, 0, 0))
    sh = Image.new("RGBA", big.size, (30, 20, 10, 0)); sh.putalpha(border.filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * .45)))
    out.alpha_composite(sh, (5, 10)) if False else out.alpha_composite(sh)
    wh = Image.new("RGBA", big.size, (255, 252, 244, 0)); wh.putalpha(border); out.alpha_composite(wh)
    out.alpha_composite(im, (pad, pad))
    an = {k: (x + pad, y + pad) for k, (x, y) in an.items()}
    an["foot"] = (out.width / 2, out.height - pad)
    return out, an

SKIN = (247, 206, 172); CHEEK = (240, 140, 120)
def spr_ded():
    p = Pn(400, 780, 3)
    p.ell(170, 752, 34, 16, (200, 160, 100)); p.ell(232, 752, 34, 16, (200, 160, 100))
    p.rect(158, 560, 196, 748, (100, 112, 145)); p.rect(206, 560, 244, 748, (100, 112, 145))
    p.poly([(96, 360), (60, 500), (88, 512), (136, 392)], (246, 242, 230)); p.ell(72, 512, 22, 22, SKIN)
    p.poly([(304, 360), (340, 500), (312, 512), (264, 392)], (246, 242, 230)); p.ell(328, 512, 22, 22, SKIN)
    p.poly([(124, 330), (276, 330), (306, 600), (94, 600)], (246, 242, 230))
    p.rect(100, 570, 300, 598, (205, 50, 48), w=0)
    for i in range(9): p.ell(112 + i * 22, 584, 5, 5, (250, 220, 120), w=0)
    p.rect(110, 466, 290, 486, (205, 50, 48), w=4)
    p.ell(200, 236, 80, 84, SKIN)
    p.ell(124, 236, 18, 34, (200, 200, 205)); p.ell(276, 236, 18, 34, (200, 200, 205))
    beard = [(128, 262)] + [(128 + i * 9, 262 + 150 * math.sin(math.pi * i / 16) + (10 if i % 2 else 0)) for i in range(1, 16)] + [(272, 262), (240, 290), (200, 300), (160, 290)]
    p.poly(beard, (250, 250, 248), w=4)
    p.ell(176, 284, 26, 12, (250, 250, 248), w=3); p.ell(224, 284, 26, 12, (250, 250, 248), w=3)
    p.ell(200, 262, 15, 13, (238, 160, 140), w=4)
    p.ell(172, 226, 7, 8, INK, w=0); p.ell(228, 226, 7, 8, INK, w=0)
    p.line([(158, 206), (186, 200)], (170, 170, 175), 6); p.line([(214, 200), (242, 206)], (170, 170, 175), 6)
    p.ell(150, 254, 14, 9, CHEEK, w=0); p.ell(250, 254, 14, 9, CHEEK, w=0)
    return finish_sprite(p, 560, {"head": (200, 150)})

def spr_baba():
    p = Pn(420, 780, 3)
    p.ell(176, 760, 30, 14, (120, 70, 40)); p.ell(244, 760, 30, 14, (120, 70, 40))
    p.poly([(104, 370), (64, 520), (92, 530), (140, 400)], (246, 242, 230)); p.ell(76, 534, 22, 22, SKIN)
    p.poly([(316, 370), (356, 520), (328, 530), (280, 400)], (246, 242, 230)); p.ell(344, 534, 22, 22, SKIN)
    p.poly([(140, 330), (280, 330), (330, 752), (90, 752)], (196, 44, 52))
    p.line([(210, 340), (210, 750)], (250, 200, 90), 8)
    p.rect(120, 690, 300, 718, (250, 200, 90), w=0)
    p.poly([(150, 420), (270, 420), (296, 690), (124, 690)], (250, 248, 240), w=4)
    for i in range(6): p.ell(146 + i * 26, 676, 6, 6, (196, 44, 52), w=0)
    p.ell(210, 220, 98, 104, (245, 190, 60))
    for (dx, dy) in ((-70, -40), (-40, -80), (10, -92), (60, -70), (80, -20), (-82, 10), (76, 30)): p.ell(210 + dx, 220 + dy, 8, 8, (205, 50, 48), w=0)
    p.poly([(176, 300), (210, 352), (244, 300)], (245, 190, 60), w=4)
    p.ell(210, 238, 64, 70, SKIN)
    p.ell(186, 228, 7, 8, INK, w=0); p.ell(234, 228, 7, 8, INK, w=0)
    p.line([(188, 262), (210, 272), (232, 262)], INK, 5)
    p.ell(170, 252, 14, 9, CHEEK, w=0); p.ell(250, 252, 14, 9, CHEEK, w=0)
    return finish_sprite(p, 540, {"head": (210, 130)})

def spr_kolobok(r=95):
    p = Pn(240, 240, 3)
    p.ell(120, 120, 100, 100, (246, 190, 56), w=6)
    p.ell(98, 92, 52, 42, (252, 214, 110), w=0)
    for i in range(14):
        a = i / 14 * 2 * math.pi; p.line([(120 + 78 * math.cos(a), 120 + 78 * math.sin(a)), (120 + 86 * math.cos(a + .12), 120 + 86 * math.sin(a + .12))], (214, 150, 40), 6)
    p.ell(96, 106, 9, 12, INK, w=0); p.ell(144, 106, 9, 12, INK, w=0)
    p.ell(99, 101, 3, 3, (255, 255, 255), w=0); p.ell(147, 101, 3, 3, (255, 255, 255), w=0)
    p.ell(76, 136, 14, 10, CHEEK, w=0); p.ell(164, 136, 14, 10, CHEEK, w=0)
    p.d.arc([(92) * 3, (112) * 3, (148) * 3, (156) * 3], 20, 160, fill=INK, width=15)
    return finish_sprite(p, r * 2, {})

def spr_hare():
    p = Pn(380, 740, 3)
    p.ell(150, 708, 50, 20, (225, 225, 220)); p.ell(240, 708, 50, 20, (225, 225, 220))
    p.ell(195, 530, 92, 172, (214, 214, 208)); p.ell(210, 560, 52, 120, (250, 250, 246), w=0)
    p.rot_ell(120, 470, 22, 58, 30, (214, 214, 208)); p.rot_ell(272, 470, 22, 58, -30, (214, 214, 208))
    p.rot_ell(160, 140, 30, 112, -10, (214, 214, 208)); p.rot_ell(160, 146, 13, 84, -10, (240, 170, 180), w=0)
    p.rot_ell(240, 136, 30, 112, 14, (214, 214, 208)); p.rot_ell(240, 142, 13, 84, 14, (240, 170, 180), w=0)
    p.ell(205, 300, 86, 80, (214, 214, 208)); p.ell(240, 330, 40, 30, (250, 250, 246), w=0)
    p.ell(232, 284, 10, 13, INK, w=0); p.ell(176, 284, 10, 13, INK, w=0)
    p.ell(208, 318, 12, 9, (230, 120, 140), w=0)
    for dy in (-6, 6): p.line([(232, 322 + dy), (296, 314 + dy * 2)], INK, 3); p.line([(184, 322 + dy), (120, 314 + dy * 2)], INK, 3)
    p.line([(196, 336), (208, 346), (220, 336)], INK, 4)
    return finish_sprite(p, 520, {"head": (205, 60)})

def spr_wolf():
    p = Pn(560, 720, 3)
    p.poly([(150, 600), (40, 500), (20, 560), (60, 650), (150, 690)], (120, 128, 140))
    p.ell(240, 520, 140, 180, (132, 140, 152)); p.ell(300, 500, 58, 120, (236, 236, 236), w=0)
    p.rect(250, 560, 290, 700, (132, 140, 152)); p.rect(320, 560, 360, 700, (132, 140, 152))
    p.ell(270, 700, 30, 14, (132, 140, 152)); p.ell(340, 700, 30, 14, (132, 140, 152))
    p.poly([(250, 190), (270, 70), (330, 160)], (132, 140, 152)); p.poly([(330, 160), (370, 66), (400, 176)], (132, 140, 152))
    p.ell(330, 240, 100, 92, (132, 140, 152))
    p.poly([(390, 210), (520, 250), (500, 296), (390, 300)], (132, 140, 152))
    p.poly([(400, 290), (500, 296), (470, 312), (410, 312)], (236, 236, 236), w=4)
    for i in range(4): p.poly([(420 + i * 18, 298), (428 + i * 18, 312), (436 + i * 18, 298)], (255, 255, 255), w=2)
    p.ell(512, 254, 16, 14, INK, w=0)
    p.ell(388, 220, 11, 11, (250, 220, 90)); p.ell(390, 220, 5, 7, INK, w=0)
    p.line([(362, 196), (412, 206)], INK, 7)
    return finish_sprite(p, 520, {"head": (330, 60)}, mirror=True)

def spr_bear():
    p = Pn(580, 840, 3)
    p.rect(170, 640, 262, 812, (130, 82, 50), r=30); p.rect(318, 640, 410, 812, (130, 82, 50), r=30)
    p.ell(290, 510, 175, 220, (140, 90, 56)); p.ell(290, 540, 100, 150, (205, 160, 115), w=0)
    p.rot_ell(120, 470, 50, 120, 20, (140, 90, 56)); p.rot_ell(460, 470, 50, 120, -20, (140, 90, 56))
    p.ell(185, 120, 46, 46, (140, 90, 56)); p.ell(185, 120, 22, 22, (205, 160, 115), w=0)
    p.ell(395, 120, 46, 46, (140, 90, 56)); p.ell(395, 120, 22, 22, (205, 160, 115), w=0)
    p.ell(290, 220, 128, 118, (140, 90, 56))
    p.ell(290, 262, 56, 44, (215, 172, 128))
    p.ell(290, 240, 22, 15, INK, w=0)
    p.ell(244, 200, 10, 11, INK, w=0); p.ell(336, 200, 10, 11, INK, w=0)
    p.line([(270, 280), (290, 292), (310, 280)], INK, 5)
    return finish_sprite(p, 560, {"head": (290, 80)})

def spr_fox():
    p = Pn(560, 660, 3)
    p.ell(170, 590, 150, 58, (232, 118, 44)); p.ell(60, 590, 50, 42, (250, 248, 240))
    p.ell(250, 470, 110, 168, (232, 118, 44)); p.ell(300, 470, 50, 120, (250, 248, 240), w=0)
    p.line([(280, 560), (280, 640)], (70, 40, 30), 14); p.line([(330, 560), (330, 640)], (70, 40, 30), 14)
    p.poly([(270, 140), (284, 20), (340, 120)], (232, 118, 44)); p.poly([(276, 64), (284, 20), (300, 70)], (60, 40, 30), w=0)
    p.poly([(340, 120), (390, 22), (410, 140)], (232, 118, 44)); p.poly([(380, 50), (390, 22), (398, 56)], (60, 40, 30), w=0)
    p.poly([(250, 140), (420, 140), (520, 224), (430, 270), (270, 280)], (232, 118, 44))
    p.poly([(330, 230), (520, 224), (430, 270), (300, 270)], (250, 248, 240), w=4)
    p.ell(518, 224, 14, 12, INK, w=0)
    p.line([(372, 186), (392, 178), (412, 186)], INK, 6); p.line([(366, 168), (410, 162)], INK, 4)
    return finish_sprite(p, 470, {"head": (330, 30), "nose": (518, 224)}, mirror=True)

# ============================================================ backgrounds
def sky(top, bot, horizon=1.0):
    y = np.linspace(0, 1, BH)[:, None, None]; y = np.clip(y / horizon, 0, 1)
    a = np.array(top, np.float32); b = np.array(bot, np.float32)
    arr = (a + (b - a) * y) * np.ones((1, BW, 1), np.float32)
    return Image.fromarray(arr.astype(np.uint8)).resize((int(BW * K), int(BH * K)), Image.BILINEAR).convert("RGBA")

def painter_on(img): p = Pn(BW, BH, K); p.im = img; p.d = ImageDraw.Draw(img); return p

def cloud(p, x, y, s=1.0, col=(255, 255, 255)):
    for dx, dy, r in ((0, 0, 60), (60, -24, 70), (130, 0, 56), (60, 18, 60)): p.ell(x + dx * s, y + dy * s, r * s, r * .8 * s, col, w=0)

def spruce(p, x, y, h, col, w=4, ol=INK):
    tw = h * .42
    p.rect(x - h * .04, y - h * .12, x + h * .04, y, (90, 60, 40), ol, w)
    for i in range(4):
        yy = y - h * .1 - i * h * .2; ww = tw * (1 - i * .2)
        p.poly([(x - ww, yy), (x, yy - h * .38), (x + ww, yy)], col, ol, w)

def birch(p, x, y, h, s=1.0, ol=INK):
    p.rect(x - 14 * s, y - h, x + 14 * s, y, (246, 244, 236), ol, 4 * s)
    for i in range(int(h / 60)):
        yy = y - h + 30 + i * 60 + hsh(i, x) * 20; p.rect(x - 14 * s, yy, x - 14 * s + 16 * s * (.4 + hsh(i, x + 1)), yy + 8 * s, (40, 40, 40), None, 0)
    for j in range(7):
        a = j / 7 * 2 * math.pi; p.ell(x + math.cos(a) * 80 * s, y - h - 10 + math.sin(a) * 60 * s, 70 * s, 56 * s, (150, 205, 100), None, 0)
    p.ell(x, y - h - 20, 90 * s, 70 * s, (170, 215, 110), None, 0)

def leafy(p, x, y, h, col=(70, 120, 60), trunk=(110, 75, 45)):
    p.poly([(x - 30, y), (x - 18, y - h * .6), (x + 18, y - h * .6), (x + 30, y)], trunk)
    for j in range(8):
        a = j / 8 * 2 * math.pi; p.ell(x + math.cos(a) * h * .3, y - h * .75 + math.sin(a) * h * .2, h * .24, h * .2, col)
    p.ell(x, y - h * .78, h * .3, h * .24, col, None, 0)

def flowers(p, x0, x1, y0, y1, n, seed, col=(255, 255, 255), mid=(250, 200, 40)):
    for i in range(n):
        x = lerp(x0, x1, hsh(i, seed)); y = lerp(y0, y1, hsh(i, seed + 3))
        for a in range(6): p.ell(x + math.cos(a) * 9, y + math.sin(a) * 9, 7, 7, col, None, 0)
        p.ell(x, y, 6, 6, mid, None, 0)

def izba(p, x, y, s=1.0, lit=False, dark=False):
    wall = (60, 45, 50) if dark else (168, 112, 66); roof = (40, 32, 40) if dark else (120, 68, 44)
    p.poly([(x - 260 * s, y), (x - 260 * s, y - 300 * s), (x + 260 * s, y - 300 * s), (x + 260 * s, y)], wall)
    if not dark:
        for i in range(7): p.line([(x - 260 * s, y - 20 * s - i * 42 * s), (x + 260 * s, y - 20 * s - i * 42 * s)], (130, 82, 48), 4 * s)
    p.poly([(x - 310 * s, y - 290 * s), (x, y - 520 * s), (x + 310 * s, y - 290 * s)], roof)
    p.rect(x + 120 * s, y - 560 * s, x + 180 * s, y - 420 * s, wall)
    win = (255, 214, 120) if lit else (170, 210, 240)
    p.rect(x - 80 * s, y - 230 * s, x + 80 * s, y - 100 * s, win)
    if not dark:
        p.poly([(x - 110 * s, y - 236 * s), (x, y - 300 * s), (x + 110 * s, y - 236 * s)], (250, 248, 240))
        p.rect(x - 118 * s, y - 236 * s, x - 82 * s, y - 94 * s, (60, 110, 190)); p.rect(x + 82 * s, y - 236 * s, x + 118 * s, y - 94 * s, (60, 110, 190))
        p.rect(x - 110 * s, y - 100 * s, x + 110 * s, y - 84 * s, (250, 248, 240))
    p.line([(x, y - 230 * s), (x, y - 100 * s)], INK, 5); p.line([(x - 80 * s, y - 165 * s), (x + 80 * s, y - 165 * s)], INK, 5)

def texture(img, vign=.28):
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    h, w = a.shape[:2]; rng = np.random.default_rng(5)
    a += rng.normal(0, 3.2, (h, w, 1)).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = 1 - vign * np.clip(((xx / w - .5) ** 2 + (yy / h - .5) ** 2) * 2.2, 0, 1)
    a *= v[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

GY = 1000
def bg_village():
    im = sky((120, 180, 236), (232, 244, 248), .8); p = painter_on(im)
    p.ell(1780, 170, 80, 80, (255, 230, 120), None, 0)
    cloud(p, 300, 170); cloud(p, 1100, 120, .8); cloud(p, 1500, 240, .6)
    p.poly([(0, BH)] + wavy(0, BW, 720, 40, 1) + [(BW, BH)], (150, 190, 160), None, 0)
    p.poly([(0, BH)] + wavy(0, BW, 820, 30, 3) + [(BW, BH)], (130, 180, 92), None, 0)
    p.poly([(0, BH)] + wavy(0, BW, 900, 14, 5) + [(BW, BH)], (150, 200, 96), None, 0)
    p.poly([(700, BH), (980, 930), (1120, 930), (1300, BH)], (226, 204, 156), None, 0)
    izba(p, 1560, 1010)
    for i in range(14): p.rect(60 + i * 34, 860, 84 + i * 34, 1000, (180, 140, 90), INK, 3)
    p.line([(50, 900), (540, 900)], INK, 5); p.line([(50, 950), (540, 950)], INK, 5)
    for x in (120, 260, 410):
        p.line([(x, 1000), (x, 760)], (60, 120, 50), 8); p.ell(x, 750, 40, 40, (250, 200, 40)); p.ell(x, 750, 18, 18, (120, 80, 40), None, 0)
    flowers(p, 0, BW, 1040, 1170, 40, 2)
    return texture(im.resize((BW, BH), Image.LANCZOS))

def bg_kitchen():
    im = Image.new("RGBA", (int(BW * K), int(BH * K)), (176, 120, 72, 255)); p = painter_on(im)
    for i in range(12): p.rect(0, i * 80, BW, i * 80 + 76, (182 - (i % 2) * 14, 124 - (i % 2) * 10, 74), (120, 76, 44), 3)
    p.rect(0, 900, BW, BH, (140, 96, 60), None, 0)
    for i in range(12): p.line([(i * 190, 900), (i * 190 - 120, BH)], (110, 72, 44), 4)
    p.rect(160, 160, 520, 420, (190, 225, 245)); p.line([(340, 160), (340, 420)]); p.line([(160, 290), (520, 290)])
    p.rect(120, 150, 560, 172, (250, 248, 240))
    p.rect(620, 300, 1060, 320, (130, 82, 50))
    for i, c in enumerate(((60, 110, 190), (205, 70, 50), (240, 200, 90))): p.ell(680 + i * 140, 260, 50, 44, c)
    p.rect(1240, 340, 1900, 1010, (238, 232, 220))
    p.rect(1600, 60, 1720, 340, (238, 232, 220))
    p.poly([(1400, 1010), (1400, 760)] + [(1570 + 170 * math.cos(a), 760 - 130 * math.sin(a)) for a in np.linspace(math.pi, 0, 20)] + [(1740, 760), (1740, 1010)], (70, 40, 32))
    p.ell(1570, 900, 140, 70, (255, 140, 50), None, 0); p.ell(1570, 920, 90, 40, (255, 210, 110), None, 0)
    for i in range(5): p.line([(1240, 420 + i * 120), (1900, 420 + i * 120)], (210, 200, 185), 3)
    p.rect(560, 760, 1100, 790, (150, 100, 60)); p.rect(600, 790, 630, 1000, (130, 82, 50)); p.rect(1030, 790, 1060, 1000, (130, 82, 50))
    p.poly([(700, 760), (900, 760), (870, 690), (730, 690)], (60, 110, 190)); p.ell(800, 690, 70, 18, (250, 240, 210))
    p.rect(950, 640, 1040, 760, (230, 220, 190), r=20)
    p.rect(120, 470, 200, 760, (250, 248, 240)); [p.line([(120, 700 + i * 14), (200, 700 + i * 14)], (205, 50, 48), 6) for i in range(3)]
    return texture(im.resize((BW, BH), Image.LANCZOS))

def bg_window():
    im = Image.new("RGBA", (int(BW * K), int(BH * K)), (170, 114, 68, 255)); p = painter_on(im)
    for i in range(16): p.rect(0, i * 76, BW, i * 76 + 72, (176 - (i % 2) * 12, 118 - (i % 2) * 8, 70), (120, 76, 44), 3)
    glass = sky((120, 185, 240), (220, 240, 250)).crop((0, 0, int(900 * K), int(640 * K)))
    gp = painter_on(glass); gp.k = K
    gp.poly([(0, 640)] + [(x, 460 + 30 * math.sin(x / 90)) for x in range(0, 900, 30)] + [(900, 640)], (130, 185, 95), None, 0)
    for x in (120, 320, 640): birch(gp, x, 600, 300, .7)
    cloud(gp, 380, 110, .8)
    im.paste(glass, (int(606 * K), int(200 * K)))
    p.rect(606, 200, 1506, 840, None, INK, 8)
    p.line([(1056, 200), (1056, 840)], (250, 248, 240), 26); p.line([(606, 520), (1506, 520)], (250, 248, 240), 26)
    p.rect(540, 150, 606, 900, (250, 248, 240)); p.rect(1506, 150, 1572, 900, (250, 248, 240))
    p.poly([(520, 160), (700, 60), (1056, 10), (1412, 60), (1592, 160)], (250, 248, 240))
    for i in range(7): p.ell(640 + i * 138, 112 - 40 * math.sin(i / 6 * math.pi), 22, 22, (60, 110, 190))
    p.rect(500, 880, 1612, 940, (250, 248, 240))
    p.rect(470, 940, 1642, 980, (200, 150, 100))
    for side in (0, 1):
        x0 = 380 if side == 0 else 1600
        p.poly([(x0, 150), (x0 + 130, 150), (x0 + 110 if side == 0 else x0 + 20, 900), (x0 + 10 if side == 0 else x0 + 130, 900)], (205, 60, 60))
        for j in range(8): p.line([(x0 + 10, 200 + j * 90), (x0 + 120, 200 + j * 90)], (250, 230, 230), 8)
    p.poly([(680, 880), (700, 800), (780, 800), (800, 880)], (205, 100, 60)); p.ell(740, 760, 50, 40, (90, 160, 70)); p.ell(740, 740, 18, 18, (240, 80, 90))
    return texture(im.resize((BW, BH), Image.LANCZOS))

def bg_birches():
    im = sky((150, 205, 245), (240, 248, 236), .75); p = painter_on(im)
    cloud(p, 400, 160, .9); cloud(p, 1400, 110, .7)
    p.poly([(0, BH)] + wavy(0, BW, 780, 30, 2) + [(BW, BH)], (160, 205, 120), None, 0)
    for x in (100, 330, 520, 1320, 1560, 1800, 2000): birch(p, x, 840, 420, .6)
    p.poly([(0, BH)] + wavy(0, BW, 880, 20, 4) + [(BW, BH)], (130, 195, 90), None, 0)
    p.poly([(0, 1080), (600, 990), (1500, 990), (BW, 1060), (BW, 1110), (0, 1140)], (226, 204, 156), None, 0)
    for x in (60, 1900): birch(p, x, 1060, 820, 1.1)
    flowers(p, 0, BW, 900, 980, 30, 7); flowers(p, 0, BW, 1120, 1180, 24, 9)
    return texture(im.resize((BW, BH), Image.LANCZOS))

def bg_spruce():
    im = sky((170, 210, 215), (225, 238, 230), .7); p = painter_on(im)
    for i in range(16): spruce(p, i * 150 + 40, 760, 360 + 60 * hsh(i, 1), (120, 160, 140), 0)
    for i in range(12): spruce(p, i * 200 + 100, 860, 520 + 80 * hsh(i, 2), (70, 125, 95), 3)
    p.poly([(0, BH)] + wavy(0, BW, 900, 14, 6) + [(BW, BH)], (90, 140, 80), None, 0)
    p.poly([(0, 1060), (700, 990), (1400, 990), (BW, 1050), (BW, 1110), (0, 1140)], (180, 150, 110), None, 0)
    for x in (90, 1960): spruce(p, x, 1090, 900, (40, 95, 60), 5)
    for x, y in ((520, 1130), (1500, 1120), (1640, 1150)):
        p.rect(x - 10, y - 40, x + 10, y, (250, 248, 240)); p.poly([(x - 40, y - 36)] + [(x + 40 * math.cos(a), y - 36 - 34 * math.sin(a)) for a in np.linspace(0, math.pi, 12)][::-1] + [(x + 40, y - 36)], (220, 50, 50))
        for k in range(3): p.ell(x - 18 + k * 18, y - 52 - (k % 2) * 8, 5, 5, (255, 255, 255), None, 0)
    return texture(im.resize((BW, BH), Image.LANCZOS))

def bg_thicket():
    im = sky((120, 150, 120), (190, 200, 160), .7); p = painter_on(im)
    for i in range(9): leafy(p, i * 260 + 60, 860, 640 + 100 * hsh(i, 3), (60, 100, 62))
    p.poly([(0, BH)] + wavy(0, BW, 900, 12, 8) + [(BW, BH)], (90, 120, 60), None, 0)
    p.rect(-40, 80, 160, 1100, (110, 75, 45)); p.rect(1960, 60, 2160, 1100, (110, 75, 45))
    p.poly([(0, 1070), (700, 1000), (1400, 1000), (BW, 1060), (BW, 1120), (0, 1150)], (150, 120, 85), None, 0)
    p.line([(2010, 300), (2010, 380)], INK, 4); p.ell(2010, 440, 60, 70, (240, 190, 60)); [p.line([(1955, 410 + i * 26), (2065, 410 + i * 26)], (160, 110, 40), 4) for i in range(4)]
    for x in (300, 1650):
        p.ell(x, 970, 160, 90, (60, 120, 60))
        for k in range(10): p.ell(x - 120 + hsh(k, x) * 240, 930 + hsh(k, x + 1) * 80, 9, 9, (210, 40, 60), None, 0)
    p.rect(560, 1100, 980, 1150, (120, 80, 50), r=20)
    return texture(im.resize((BW, BH), Image.LANCZOS), .34)

def bg_glade():
    im = sky((250, 170, 120), (255, 226, 170), .75); p = painter_on(im)
    p.ell(1060, 760, 170, 170, (255, 240, 190), None, 0); p.ell(1060, 760, 120, 120, (255, 250, 220), None, 0)
    cloud(p, 300, 200, 1.0, (255, 214, 190)); cloud(p, 1600, 150, .8, (255, 214, 190))
    p.poly([(0, BH)] + wavy(0, BW, 800, 30, 9) + [(BW, BH)], (200, 170, 100), None, 0)
    for x in (150, 380, 1720, 1950): birch(p, x, 840, 420, .6)
    p.poly([(0, BH)] + wavy(0, BW, 900, 16, 3) + [(BW, BH)], (190, 180, 90), None, 0)
    for i in range(120):
        x = hsh(i, 4) * BW; y = 940 + hsh(i, 5) * 240; p.line([(x, y), (x + 10 * (hsh(i, 6) - .5), y - 40 - 30 * hsh(i, 7))], (150, 150, 60), 4)
    p.ell(1880, 1020, 110, 30, (150, 100, 60)); p.rect(1770, 900, 1990, 1020, (140, 90, 55)); p.ell(1880, 900, 110, 30, (220, 180, 120))
    flowers(p, 0, BW, 960, 1170, 30, 11, (250, 120, 160), (255, 230, 120))
    return texture(im.resize((BW, BH), Image.LANCZOS))

def bg_night():
    im = sky((20, 28, 70), (70, 80, 140), .9); p = painter_on(im)
    for i in range(120):
        x = hsh(i, 1) * BW; y = hsh(i, 2) * 700; r = 1.5 + 2.5 * hsh(i, 3); p.ell(x, y, r, r, (255, 250, 220), None, 0)
    p.ell(1650, 230, 110, 110, (255, 244, 200), None, 0); p.ell(1600, 200, 100, 100, (30, 40, 85), None, 0)
    p.poly([(0, BH)] + wavy(0, BW, 820, 40, 2) + [(BW, BH)], (30, 50, 70), None, 0)
    izba(p, 760, 1000, 1.0, lit=True, dark=True)
    p.poly([(0, BH)] + wavy(0, BW, 980, 16, 7) + [(BW, BH)], (24, 40, 55), None, 0)
    for x in (1400, 1700, 1980, 200): spruce(p, x, 1000, 520, (22, 38, 50), 0)
    im = im.resize((BW, BH), Image.LANCZOS)
    glow = Image.new("RGBA", (BW, BH), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow); gd.ellipse([1500, 80, 1800, 380], fill=(255, 240, 180, 60))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(40)))
    return texture(im, .2)

# ============================================================ script
SCENES = [  # name, t0, t1, bg builder, cam (cx0,cy0,z0) -> (cx1,cy1,z1)
    ("village", 0.0, 7.5, bg_village, (1056, 594, 1.0), (1000, 580, 1.06)),
    ("kitchen", 7.5, 15.0, bg_kitchen, (1000, 594, 1.0), (1100, 580, 1.05)),
    ("window", 15.0, 21.5, bg_window, (1056, 560, 1.0), (1056, 600, 1.07)),
    ("birches", 21.5, 28.0, bg_birches, (1020, 594, 1.02), (1090, 594, 1.0)),
    ("spruce", 28.0, 34.5, bg_spruce, (1090, 594, 1.0), (1020, 590, 1.05)),
    ("thicket", 34.5, 41.0, bg_thicket, (1056, 600, 1.05), (1056, 580, 1.0)),
    ("glade", 41.0, 53.0, bg_glade, (1000, 594, 1.0), (1100, 610, 1.08)),
    ("night", 53.0, 60.0, bg_night, (1056, 594, 1.06), (1056, 594, 1.0)),
]
XF = .55  # half-length of each cross-dissolve

# characters: (scene, sprite, x, y_ground_or_center, t_in, t_out, path or None)
def roll(x0, x1, ta, tb):
    return ("roll", x0, x1, ta, tb)
CAST = [
    ("village", "ded", 640, GY, 2.4, 9, None), ("village", "baba", 900, GY, 2.8, 9, None),
    ("kitchen", "baba", 380, GY + 40, 8.0, 16, None), ("kitchen", "kolobok", 1570, 905, 12.3, 16, None),
    ("window", "kolobok", 1056, 880, 15.5, 20.2, ("hop", 1056, 880, 1500, 1500, 18.8, 20.0)),
    ("birches", "kolobok", -150, 1040, 21.0, 29, ("roll2", -150, 700, 21.8, 23.0, 2400, 26.6, 27.8)),
    ("birches", "hare", 1420, 1040, 22.8, 29, None),
    ("spruce", "kolobok", -150, 1040, 27.5, 35, ("roll2", -150, 700, 28.3, 29.5, 2400, 33.0, 34.2)),
    ("spruce", "wolf", 1420, 1040, 29.3, 35, None),
    ("thicket", "kolobok", -150, 1050, 34.0, 42, ("roll2", -150, 720, 34.8, 36.0, 2400, 39.5, 40.7)),
    ("thicket", "bear", 1440, 1050, 35.8, 42, None),
    ("glade", "fox", 1380, 1040, 42.4, 54, None),
    ("glade", "kolobok", -150, 1040, 40.5, 48.95, ("rollhop", -150, 760, 41.3, 42.6, 47.3, 48.3)),
]
CAPS = [  # canonical text (folk tale, A. N. Tolstoy's telling)
    (3.0, 5.0, "Жили-были старик со старухой."), (5.1, 7.25, "Вот и просит старик: «Испеки мне колобок»."),
    (8.1, 10.9, "Старуха по амбару помела, по сусекам поскребла…"), (11.0, 12.8, "…замесила на сметане, изжарила в масле…"),
    (12.9, 14.75, "…и вышел колобок румяный."),
    (15.6, 17.9, "Положила его старуха на окошечко постудить."), (18.0, 21.2, "Колобок полежал-полежал, да и покатился!"),
    (22.2, 24.2, "Катится колобок, а навстречу ему заяц."), (24.3, 27.7, "Спел колобок песенку — и покатился дальше."),
    (28.6, 31.0, "Катится колобок, а навстречу ему волк."), (31.1, 34.2, "Спел песенку — только волк его и видел!"),
    (35.1, 37.4, "Катится, а навстречу ему медведь."), (37.5, 40.7, "Спел — только медведь его и видел!"),
    (41.6, 43.6, "Катится колобок, а навстречу ему лиса."), (43.8, 46.8, "«Какая славная песенка!» — хвалит лиса."),
    (46.9, 48.8, "Колобок прыг лисе на язык…"), (49.0, 52.7, "…а лиса его — ам! — и съела."),
    (53.6, 56.0, "Тут и сказке конец,"), (56.1, 59.0, "а кто слушал — молодец!"),
]
BUBS = [  # (t0, t1, text, x, y) in bg coords (tail points down at x)
    (4.9, 7.25, "Испеки мне, старая, колобок!", 640, 400),
    (23.3, 25.2, "Колобок, колобок! Я тебя съем!", 1420, 430),
    (25.2, 26.6, "Я от дедушки ушёл, я от бабушки ушёл, а от тебя, заяц, не хитро уйти!", 700, 820),
    (29.8, 31.6, "Колобок, колобок! Я тебя съем!", 1420, 450), (31.6, 33.0, "Я от зайца ушёл, а от тебя, волк, не хитро уйти!", 700, 820),
    (36.3, 38.1, "Колобок, колобок! Я тебя съем!", 1440, 470), (38.1, 39.5, "Я от волка ушёл, а от тебя, медведь, не хитро уйти!", 720, 830),
    (43.3, 46.7, "Колобок, колобок! Сядь ко мне на язычок да пропой ещё разок.", 1380, 500),
]
TITLES = [(0.3, 3.0, "Колобок", 1056, 300, 190), (48.95, 50.6, "Ам!", 1180, 420, 210), (54.8, 59.3, "Конец", 1056, 420, 170)]

# ============================================================ runtime
_bg = {}; _spr = {}
SPR = {"ded": spr_ded, "baba": spr_baba, "kolobok": spr_kolobok, "hare": spr_hare, "wolf": spr_wolf, "bear": spr_bear, "fox": spr_fox}
HEIGHTS = {"ded": 560, "baba": 540, "kolobok": 190, "hare": 520, "wolf": 520, "bear": 560, "fox": 470}

def cut_white(im):
    """alpha from a plain white backdrop: only near-white regions touching the border become transparent"""
    from scipy import ndimage
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    white = (a.min(axis=2) > 232) & (np.ptp(a, axis=2) < 18)
    lab, _ = ndimage.label(white)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bgm = np.isin(lab, list(edge))
    alpha = np.where(bgm, 0, 255).astype(np.uint8)
    alpha = np.asarray(Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(1.2)))
    out = im.convert("RGBA"); out.putalpha(Image.fromarray(alpha)); return out

def load_sprite(name):
    path = os.path.join(HERE, "chars", name + ".png")
    if not os.path.exists(path): return None
    im = cut_white(Image.open(path)); im = im.crop(im.getbbox())
    sc = HEIGHTS[name] / im.height; im = im.resize((max(1, int(im.width * sc)), HEIGHTS[name]), Image.LANCZOS)
    p = Pn(im.width, im.height, 1); p.im = im
    return finish_sprite(p, HEIGHTS[name], {"head": (im.width / 2, 0)})

def bgimg(name):
    if name not in _bg:
        path = os.path.join(HERE, "bg", name + ".png")
        if os.path.exists(path): _bg[name] = ImageOps.fit(Image.open(path).convert("RGB"), (BW, BH), Image.LANCZOS)
        else: _bg[name] = next(sc[3] for sc in SCENES if sc[0] == name)().convert("RGB")
    return _bg[name]
def sprite(name):
    if name not in _spr: _spr[name] = load_sprite(name) or SPR[name]()
    return _spr[name]

def cam_of(sc, t):
    _, t0, t1, _, a, b = sc; k = ss(seg(t, t0 - XF, t1 + XF))
    return tuple(lerp(a[i], b[i], k) for i in range(3))
def to_scr(cam, x, y): cx, cy, z = cam; return ((x - cx) * z + W / 2, (y - cy) * z + H / 2)

def kolobok_pos(path, t, x, y):
    """returns (x, y_ground_center, angle_deg, visible_scale)"""
    r = 95
    if path is None: return x, y, 0, 1
    kind = path[0]
    if kind == "hop":
        _, x0, y0, x1, y1, ta, tb = path; k = seg(t, ta, tb)
        return lerp(x0, x1, k), lerp(y0, y1, k * k) - 260 * math.sin(math.pi * min(k, .5) * 2) * (k < .5) - 260 * (k >= .5) * (1 - (k - .5) * 2) ** 2 * 0, -360 * k, 1
    if kind == "roll2":
        _, x0, x1, ta, tb, x2, tc, td = path
        if t < tb: xx = lerp(x0, x1, ss(seg(t, ta, tb)))
        else: xx = lerp(x1, x2, ss(seg(t, tc, td)) ** 1.4)
        return xx, y, -(xx - x0) / r * 57.3, 1
    if kind == "rollhop":
        _, x0, x1, ta, tb, tc, td = path
        xx = lerp(x0, x1, ss(seg(t, ta, tb))); yy = y; ang = -(xx - x0) / r * 57.3
        if t > tc:
            k = seg(t, tc, td); nx, ny = 1380 - 196, 1040 - 360
            xx = lerp(x1, nx, k); yy = lerp(y, ny, k) - 240 * math.sin(math.pi * k); ang -= 200 * k
        return xx, yy, ang, 1
    return x, y, 0, 1

def pop_scale(t, ti, to):
    if t < ti or t > to: return 0
    a = back(seg(t, ti, ti + .45), 2.6)
    b = 1 - ss(seg(t, to - .3, to))
    return a * b

def draw_sprite(img, name, sx, sy, sc, ang=0, anchor="foot", rise=1.0):
    if sc <= .02: return
    spr, an = sprite(name)
    w, h = max(2, int(spr.width * sc)), max(2, int(spr.height * sc * rise))
    im = spr.resize((w, h), Image.BILINEAR)
    if anchor == "center":
        if ang: im = im.rotate(ang, resample=Image.BICUBIC, expand=True)
        img.alpha_composite(im, (int(sx - im.width / 2), int(sy - im.height / 2)))
    else:
        if ang: im = im.rotate(ang, resample=Image.BICUBIC, expand=False, center=(w / 2, h))
        fx, fy = an["foot"]; img.alpha_composite(im, (int(sx - fx * sc), int(sy - fy * sc * rise)))

@lru_cache(maxsize=64)
def text_word(word, size, font, fill, stroke):
    f = ImageFont.truetype(font, size); tw = int(f.getlength(word)) + 30
    im = Image.new("RGBA", (tw, int(size * 1.5)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.text((15, size * .1), word, font=f, fill=fill, stroke_width=stroke, stroke_fill=INK)
    return im

def draw_caption(img, t):
    for t0, t1, txt in CAPS:
        if not (t0 <= t < t1 + .25): continue
        words = txt.split(" "); size = 58; f = ImageFont.truetype(F_TEXT, size); sp = f.getlength(" ")
        ws = [text_word(w, size, F_TEXT, (60, 36, 20), 0) for w in words]
        total = sum(w.width - 30 for w in ws) + sp * (len(ws) - 1)
        out = ss(seg(t, t1 - .05, t1 + .25))
        # parchment ribbon
        rk = back(seg(t, t0, t0 + .35), 1.8) * (1 - out)
        if rk > .02:
            rw, rh = (total + 120) * rk, 110 * min(1, rk * 1.2)
            rib = Image.new("RGBA", (int(rw) + 40, int(rh) + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(rib)
            d.rounded_rectangle([24, 26, rw + 24, rh + 26], 30, fill=(60, 30, 10, 70))
            d.rounded_rectangle([16, 16, rw + 16, rh + 16], 30, fill=(253, 242, 214, 240), outline=(150, 100, 50), width=5)
            d.rounded_rectangle([28, 28, rw + 4, rh + 4], 22, outline=(214, 170, 100), width=2)
            img.alpha_composite(rib, (int(W / 2 - rw / 2 - 16), int(86 - rh / 2 - 16)))
        x = W / 2 - total / 2
        for i, (w, wi) in enumerate(zip(words, ws)):
            k = t - (t0 + .15 + i * .09); adv = wi.width - 30 + sp
            if k < 0 or out > .6: x += adv; continue
            sc = back(seg(k, 0, .3), 3.0)
            s2 = wi.resize((max(2, int(wi.width * sc)), max(2, int(wi.height * sc))), Image.BILINEAR)
            img.alpha_composite(s2, (int(x - 15 + (wi.width - s2.width) / 2), int(86 - s2.height / 2 - (1 - seg(k, 0, .2)) * 20)))
            x += adv

def wrap(text, f, maxw):
    lines, cur = [], ""
    for w in text.split(" "):
        tr = (cur + " " + w).strip()
        if f.getlength(tr) > maxw and cur: lines.append(cur); cur = w
        else: cur = tr
    return lines + [cur]

@lru_cache(maxsize=16)
def bubble_img(text):
    f = ImageFont.truetype(F_TEXT, 46); lines = wrap(text, f, 560)
    tw = max(f.getlength(l) for l in lines); th = len(lines) * 56
    bw, bh = int(tw + 70), int(th + 46); im = Image.new("RGBA", (bw + 20, bh + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([14, 16, bw + 14, bh + 16], 34, fill=(40, 20, 10, 60))
    d.rounded_rectangle([6, 6, bw + 6, bh + 6], 34, fill=(255, 255, 252), outline=INK, width=6)
    cx = bw / 2 + 6; d.polygon([(cx - 26, bh + 2), (cx + 26, bh + 2), (cx, bh + 50)], fill=(255, 255, 252))
    d.line([(cx - 26, bh + 5), (cx, bh + 50), (cx + 26, bh + 5)], fill=INK, width=6)
    for i, l in enumerate(lines): d.text((bw / 2 + 6, 26 + i * 56 + 28), l, font=f, fill=INK, anchor="mm")
    return im

def draw_bubbles(img, t, cam):
    for t0, t1, txt, x, y in BUBS:
        sc = pop_scale(t, t0, t1)
        if sc <= .02: continue
        b = bubble_img(txt); sx, sy = to_scr(cam, x, y)
        s2 = b.resize((max(2, int(b.width * sc)), max(2, int(b.height * sc))), Image.BILINEAR)
        X = min(max(sx - s2.width / 2, 20), W - s2.width - 20)
        img.alpha_composite(s2, (int(X), int(sy - s2.height)))

def draw_titles(img, t):
    for t0, t1, txt, x, y, size in TITLES:
        sc = pop_scale(t, t0, t1)
        if sc <= .02: continue
        im = text_word(txt, size, F_TITLE, (250, 200, 60), 10)
        ang = 4 * math.sin(t * 2)
        s2 = im.resize((max(2, int(im.width * sc)), max(2, int(im.height * sc))), Image.BILINEAR).rotate(ang, expand=True, resample=Image.BICUBIC)
        sx, sy = x / BW * W, y / BH * H
        img.alpha_composite(s2, (int(sx - s2.width / 2), int(sy - s2.height / 2)))

def sparkle(d, x, y, r, a, col=(255, 246, 200)):
    c = col + (int(255 * a),)
    d.polygon([(x, y - r), (x + r * .22, y - r * .22), (x + r, y), (x + r * .22, y + r * .22), (x, y + r), (x - r * .22, y + r * .22), (x - r, y), (x - r * .22, y - r * .22)], fill=c)

def fairy_dust(img, t, amt=1.0, n=26, seed=0):
    if amt <= 0: return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for i in range(n):
        ph = hsh(i, seed) * 6.28; sp = .3 + hsh(i, seed + 1)
        x = (hsh(i, seed + 2) * W + t * 40 * sp) % W; y = (hsh(i, seed + 3) * H - t * 30 * sp) % H
        tw = (.5 + .5 * math.sin(t * 5 * sp + ph)) * amt
        sparkle(d, x, y, 6 + 14 * hsh(i, seed + 4) * tw, tw)
    img.alpha_composite(ov)

def burst(img, t, t0, x, y, cam):
    k = t - t0
    if not (0 <= k < 1.0): return
    sx, sy = to_scr(cam, x, y); d = ImageDraw.Draw(img)
    for i in range(12):
        a = i / 12 * 6.28 + .3; r = 40 + 220 * (1 - (1 - k) ** 3)
        sparkle(d, sx + math.cos(a) * r, sy + math.sin(a) * r * .8, 22 * (1 - k) + 4, 1 - k)

def render_scene(sc, t):
    name = sc[0]; cam = cam_of(sc, t); cx, cy, z = cam
    bg = bgimg(name); vw, vh = W / z, H / z
    img = bg.resize((W, H), Image.BILINEAR, box=(cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2)).convert("RGBA")
    if name == "kitchen":   # flickering stove glow
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl); sx, sy = to_scr(cam, 1570, 900)
        a = int(70 + 40 * math.sin(t * 9) + 25 * math.sin(t * 23)); gd.ellipse([sx - 300, sy - 220, sx + 300, sy + 160], fill=(255, 150, 60, a))
        img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(50)))
    for scn, spr, x, y, ti, to, path in CAST:
        if scn != name: continue
        sc_ = pop_scale(t, ti, to)
        if sc_ <= .02: continue
        if spr == "kolobok":
            xx, yy, ang, _ = kolobok_pos(path, t, x, y)
            sx, sy = to_scr(cam, xx, yy - 95); spr_, an = sprite("kolobok")
            draw_sprite(img, "kolobok", sx, sy, sc_ * z, ang, anchor="center")
        else:
            sway = 1.2 * math.sin(t * 1.7 + x)
            rise = back(seg(t, ti, ti + .55), 1.6) * (1 - ss(seg(t, to - .35, to)))
            sx, sy = to_scr(cam, x, y)
            if rise > .02: draw_sprite(img, spr, sx, sy, z, sway * rise, rise=max(.02, rise))
    if name == "kitchen": burst(img, t, 12.3, 1570, 810, cam)
    if name == "window": burst(img, t, 15.5, 1056, 780, cam)
    if name == "glade": burst(img, t, 48.95, 1184, 680, cam)
    draw_bubbles(img, t, cam)
    if name in ("village", "night"): fairy_dust(img, t, .9 if name == "night" else .5, 30, 3)
    return img

def render(t):
    cur = [sc for sc in SCENES if sc[1] - XF <= t < sc[2] + XF]
    if len(cur) == 1: img = render_scene(cur[0], t)
    else:
        a, b = cur[0], cur[1]; k = ss(seg(t, b[1] - XF, b[1] + XF))
        ia, ib = render_scene(a, t), render_scene(b, t)
        img = Image.blend(ia, ib, k)
        fairy_dust(img, t, math.sin(math.pi * k) * 1.2, 40, int(b[1]))
    draw_titles(img, t); draw_caption(img, t)
    out = img.convert("RGB")
    if t < .6: out = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), out, ss(t / .6))
    if t > DUR - 1.0: out = Image.blend(out, Image.new("RGB", (W, H), (0, 0, 0)), ss((t - (DUR - 1.0)) / 1.0))
    return out

def init():
    for sc in SCENES: bgimg(sc[0])
    for n in SPR: sprite(n)

def rb(i): return render(i / FPS).tobytes()

if __name__ == "__main__":
    out = sys.argv[1]
    if "--preview" in sys.argv:
        for tt in [float(v) for v in sys.argv[sys.argv.index("--preview") + 1].split(",")]: render(tt).save(f"{out}_{tt:05.1f}.png")
        sys.exit()
    n = int(DUR * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    with Pool(4, initializer=init) as pool:
        for i, b in enumerate(pool.imap(rb, range(n), chunksize=4)):
            ff.stdin.write(b)
            if i % 240 == 0: print(f"frame {i}/{n}", flush=True)
    ff.stdin.close(); ff.wait()
