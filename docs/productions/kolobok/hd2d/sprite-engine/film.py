"""«Колобок» in modern volumetric pixel art — 60 s, 1080p/24.

World is drawn at 480x270 and scaled x4 with nearest neighbour; bloom, light and UI are
composited at full resolution so text and boxes move smoothly while staying pixel-crisp.

usage: python3 film.py OUT.mp4 [--preview T1,T2,...]
"""
import math, os, sys, subprocess
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pix import render, decal, MATS
import chars

HERE = os.path.dirname(os.path.abspath(__file__))
LW, LH, SC = 480, 270, 4
W, H, FPS, DUR = LW * SC, LH * SC, 24, 60.0
WW = 560; GY = 238
FONT = os.path.join(HERE, "Pixelify-Bold.ttf"); FONTM = os.path.join(HERE, "Pixelify-Medium.ttf")
OUTL = (28, 18, 30)

def clamp(v, a=0.0, b=1.0): return a if v < a else b if v > b else v
def seg(t, a, b): return clamp((t - a) / (b - a)) if b > a else float(t >= a)
def ss(x): x = clamp(x); return x * x * (3 - 2 * x)
def lerp(a, b, k): return a + (b - a) * k
def eout(x): x = clamp(x); return 1 - (1 - x) ** 3
def back(x, s=1.8):
    x = clamp(x); x -= 1; return x * x * ((s + 1) * x + s) + 1
def hsh(i, s):
    v = math.sin(i * 127.1 + s * 311.7) * 43758.5453; return v - math.floor(v)
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0

# ============================================================ background helpers
def sky(top, bot, w=WW, h=LH, bands=9, end=1.0):
    y = np.clip(np.linspace(0, 1, h) / end, 0, 1)[:, None] * np.ones((1, w))
    v = y * (bands - 1); lo = np.floor(v); fr = v - lo
    thr = np.tile(BAYER, (h // 4 + 1, w // 4 + 1))[:h, :w]
    q = (lo + (fr > thr)) / (bands - 1)
    a, b = np.array(top, float), np.array(bot, float)
    return Image.fromarray((a + (b - a) * q[..., None]).astype(np.uint8)).convert("RGBA")

def ridge(d, w, y, amp, col, top, seed, f=.018, step=2):
    pts = [(x, y + amp * math.sin(x * f + seed) + amp * .5 * math.sin(x * f * 2.3 + seed * 3)) for x in range(0, w + step, step)]
    d.polygon(pts + [(w, LH), (0, LH)], fill=col)
    for i in range(len(pts) - 1):
        x, yy = pts[i]; d.point((x, round(yy)), fill=top); d.point((x + 1, round(yy)), fill=top)

def paste(base, im, x, y, anchor="bottom"):
    if anchor == "bottom": base.alpha_composite(im, (int(x - im.width / 2), int(y - im.height)))
    else: base.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))

def obj(prims, w, h, **kw):
    im = render(prims, w, h, **kw); bb = im.getbbox(); return im.crop(bb) if bb else im

def cloud(seed, s=1.0, mat="cloud"):
    P = []
    for i in range(6):
        P.append(("ell", 30 + (i - 2.5) * 9 * s + hsh(i, seed) * 6, 20 + hsh(i + 3, seed) * 4 - (i in (2, 3)) * 5 * s, 0, (10 + 6 * hsh(i, seed + 1)) * s, (7 + 4 * hsh(i, seed + 2)) * s, 8, mat))
    return obj(P, 90, 40, amb=.55, outline=False, inner=False)

def round_tree(seed, s=1.0, mat="leaf"):
    w, h = int(70 * s), int(100 * s); c = w / 2
    P = [("cap", c, h - 2, 0, c, h * .45, 0, 4.5 * s, "trunk")]
    for i in range(9):
        a = i / 9 * 6.283 + hsh(i, seed); r = (12 + 6 * hsh(i, seed + 1)) * s
        P.append(("ell", c + math.cos(a) * 15 * s, h * .36 + math.sin(a) * 12 * s, 6 + 6 * hsh(i, seed + 2), r, r * .9, r, mat))
    P.append(("ell", c, h * .3, 14, 16 * s, 14 * s, 12, mat))
    return obj(P, w, h, seed=seed)

def birch_tree(seed, s=1.0):
    w, h = int(60 * s), int(150 * s); c = w / 2
    P = [("cap", c, h - 1, 0, c + 2 * s, h * .3, 0, 3.6 * s, "birch")]
    for i in range(10):
        a = i / 10 * 6.283 + hsh(i, seed); r = (8 + 5 * hsh(i, seed + 1)) * s
        P.append(("ell", c + math.cos(a) * 13 * s, h * .25 + math.sin(a) * 16 * s, 8 * hsh(i, seed + 2), r, r * .85, r, "leaf"))
    im = render(P, w, h, seed=seed); d = ImageDraw.Draw(im)
    for i in range(int(h * .7 / 9)):
        y = int(h - 6 - i * 9 - 4 * hsh(i, seed)); x = int(c - 3 * s + 3 * s * hsh(i, seed + 5))
        if im.getpixel((x, y))[3] and im.getpixel((x, y))[0] > 150: d.line([(x, y), (x + max(1, int(2 * s)), y)], fill=(30, 26, 34))
    return im.crop(im.getbbox())

def spruce_tree(seed, s=1.0, mat="spruce"):
    w, h = int(56 * s), int(130 * s); c = w / 2
    P = [("cap", c, h - 1, 0, c, h - 14 * s, 0, 3 * s, "trunk")]
    for i in range(6):
        y = h - 18 * s - i * 17 * s; r = (24 - i * 3.6) * s
        P.append(("ell", c, y, i * 2, r, 9 * s, 8, mat))
    P.append(("ell", c, h - 18 * s - 6 * 17 * s + 4 * s, 13, 4 * s, 7 * s, 5, mat))
    return obj(P, w, h, seed=seed)

def izba(lit=False):
    w, h = 150, 140; P = []
    for i in range(9): P.append(("cap", 12, 132 - i * 10.5, 0, 138, 132 - i * 10.5, 0, 5.6, "log"))
    for side in (8, 142):
        for i in range(9): P.append(("ell", side, 132 - i * 10.5, 4, 5.5, 5.5, 5, "log"))
    im = render(P, w, h, seed=3); d = ImageDraw.Draw(im)
    roof = MATS["roof"]["ramp"]
    d.polygon([(0, 50), (75, 0), (75, 52)], fill=roof[3]); d.polygon([(75, 0), (150, 50), (75, 52)], fill=roof[1])
    for i in range(1, 8): d.line([(75 - i * 10, i * 6.7), (75, i * 6.9)], fill=roof[2])
    for i in range(1, 8): d.line([(75 + i * 10, i * 6.7), (75, i * 6.9)], fill=roof[0])
    d.line([(0, 50), (75, 0), (150, 50)], fill=OUTL, width=2)
    d.rectangle([108, 2, 118, 30], fill=roof[2], outline=OUTL)
    wc = (255, 214, 120) if lit else (150, 200, 235)
    d.rectangle([57, 70, 93, 104], fill=wc, outline=OUTL)
    if not lit:
        d.rectangle([58, 71, 92, 78], fill=(195, 228, 248))
    d.line([(75, 70), (75, 104)], fill=(250, 248, 240), width=2); d.line([(57, 86), (93, 86)], fill=(250, 248, 240), width=2)
    d.rectangle([47, 68, 56, 106], fill=(58, 92, 176), outline=OUTL); d.rectangle([94, 68, 103, 106], fill=(58, 92, 176), outline=OUTL)
    d.polygon([(52, 68), (75, 56), (98, 68)], fill=(250, 248, 240), outline=OUTL)
    d.rectangle([52, 104, 98, 108], fill=(250, 248, 240), outline=OUTL)
    d.rectangle([20, 92, 40, 132], fill=(110, 64, 40), outline=OUTL)
    return im

def flowers(d, x0, x1, y0, y1, n, seed, petal=(255, 255, 255), mid=(250, 200, 40)):
    for i in range(n):
        x = int(lerp(x0, x1, hsh(i, seed))); y = int(lerp(y0, y1, hsh(i, seed + 3)))
        d.point([(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)], fill=petal); d.point((x, y), fill=mid)

def grass(d, x0, x1, y0, y1, n, seed, col, top):
    for i in range(n):
        x = int(lerp(x0, x1, hsh(i, seed))); y = int(lerp(y0, y1, hsh(i, seed + 1))); hh = 2 + int(4 * hsh(i, seed + 2))
        d.line([(x, y), (x, y - hh)], fill=col); d.point((x, y - hh), fill=top)

def mushroom():
    P = [("cap", 8, 22, 0, 8, 12, 0, 3, "white"), ("ell", 8, 11, 2, 8, 5, 6, "mush")]
    im = render(P, 18, 26); decal(im, [("px", [(5, 9), (10, 8), (12, 11), (7, 12)], (255, 255, 255))]); return im.crop(im.getbbox())

def bush(seed, berries=False):
    P = [("ell", 22 + (i - 3) * 6 + hsh(i, seed) * 3, 18 - hsh(i, seed + 1) * 6, i % 3, 9, 8, 7, "leafdark") for i in range(7)]
    im = render(P, 46, 30, seed=seed)
    if berries:
        d = ImageDraw.Draw(im)
        for k in range(12):
            x, y = int(6 + hsh(k, seed) * 34), int(6 + hsh(k, seed + 2) * 16)
            if im.getpixel((x, y))[3]: d.point([(x, y), (x + 1, y)], fill=(220, 40, 60)); d.point((x, y - 1), fill=(255, 140, 140))
    return im.crop(im.getbbox())

# ============================================================ locations (static layers)
def loc_village():
    far = sky((88, 150, 222), (214, 236, 246), bands=10, end=.75); d = ImageDraw.Draw(far)
    d.ellipse([470, 18, 500, 48], fill=(255, 238, 160)); d.ellipse([475, 23, 495, 43], fill=(255, 250, 220))
    for x, y, s_ in ((60, 30, 1.0), (250, 18, .8), (380, 50, .7)): paste(far, cloud(int(x), s_), x, y, "center")
    ridge(d, WW, 168, 6, (120, 160, 150), (160, 196, 180), 1); ridge(d, WW, 186, 5, (96, 150, 92), (140, 190, 110), 4)
    for i in range(6): paste(far, round_tree(10 + i, .45, "leafdark"), 30 + i * 95, 192)
    main = Image.new("RGBA", (WW, LH), (0, 0, 0, 0)); d = ImageDraw.Draw(main)
    ridge(d, WW, 206, 3, (110, 172, 74), (160, 210, 96), 7)
    d.polygon([(190, LH), (230, 210), (262, 210), (300, LH)], fill=(210, 184, 130)); d.line([(230, 210), (190, LH)], fill=(176, 148, 100))
    paste(main, izba(), 420, 216)
    for i in range(16): paste(main, obj([("cap", 4, 30, 0, 4, 4, 0, 2.6, "log")], 9, 34), 20 + i * 7, 222)
    for x in (30, 52, 78):
        im = obj([("cap", 6, 60, 0, 6, 16, 0, 1.6, "leaf"), ("ell", 6, 12, 3, 7, 7, 3, "sunflower"), ("ell", 6, 12, 7, 3, 3, 2, "trunk")], 14, 64)
        paste(main, im, x, 214)
    grass(d, 0, WW, 214, 268, 160, 2, (80, 140, 60), (150, 200, 90)); flowers(d, 0, WW, 222, 266, 40, 3)
    return far, main, (0, 40), "day"

def loc_kitchen():
    far = Image.new("RGBA", (WW, LH), (0, 0, 0, 255))
    P = [("cap", -10, 10 + i * 11, 0, WW + 10, 10 + i * 11, 0, 5.8, "log") for i in range(22)]
    wall = render(P, WW, LH, amb=.35, outline=False, seed=4); far.alpha_composite(wall)
    d = ImageDraw.Draw(far)
    d.rectangle([40, 40, 100, 90], fill=(170, 210, 240), outline=OUTL); d.line([(70, 40), (70, 90)], fill=(250, 248, 240), width=2); d.line([(40, 65), (100, 65)], fill=(250, 248, 240), width=2)
    d.rectangle([150, 70, 260, 74], fill=(110, 64, 40), outline=OUTL)
    for i, m in enumerate(("clay", "blue", "clay")): paste(far, obj([("ell", 8, 8, 0, 8, 7, 6, m)], 18, 18), 168 + i * 34, 70)
    d.rectangle([0, 214, WW, LH], fill=(112, 70, 44)); [d.line([(i * 40, 214), (i * 40 - 30, LH)], fill=(90, 54, 34)) for i in range(16)]
    d.line([(0, 214), (WW, 214)], fill=OUTL)
    st = MATS["stove"]["ramp"]
    d.polygon([(330, 230), (330, 90), (470, 90), (470, 230)], fill=st[3], outline=OUTL)
    d.polygon([(470, 230), (470, 90), (500, 76), (500, 216)], fill=st[1], outline=OUTL)
    d.polygon([(330, 90), (360, 76), (500, 76), (470, 90)], fill=st[4], outline=OUTL)
    d.rectangle([420, 10, 450, 90], fill=st[3], outline=OUTL); d.polygon([(450, 10), (462, 4), (462, 84), (450, 90)], fill=st[1], outline=OUTL)
    for y in range(100, 230, 14): d.line([(331, y), (469, y)], fill=st[2])
    d.pieslice([368, 166, 432, 230], 180, 360, fill=(46, 26, 30), outline=OUTL); d.rectangle([368, 198, 432, 230], fill=(46, 26, 30), outline=OUTL)
    d.rectangle([369, 199, 431, 229], fill=(46, 26, 30))
    d.rectangle([140, 176, 270, 182], fill=(130, 80, 48), outline=OUTL); d.rectangle([148, 182, 154, 222], fill=(110, 64, 40), outline=OUTL); d.rectangle([256, 182, 262, 222], fill=(110, 64, 40), outline=OUTL)
    paste(far, obj([("ell", 14, 10, 0, 14, 8, 8, "blue"), ("ell", 14, 5, 6, 10, 3, 3, "linen")], 30, 20), 180, 177)
    paste(far, obj([("ell", 10, 14, 0, 10, 14, 8, "linen")], 22, 30), 236, 177)
    d.rectangle([10, 110, 26, 170], fill=(250, 248, 240), outline=OUTL); [d.line([(10, 158 + i * 3), (26, 158 + i * 3)], fill=(200, 40, 50)) for i in range(3)]
    return far, Image.new("RGBA", (WW, LH), (0, 0, 0, 0)), (20, 50), "warm"

def loc_window():
    far = Image.new("RGBA", (WW, LH), (0, 0, 0, 255))
    out = sky((96, 160, 228), (220, 240, 248), w=200, h=150, bands=7)
    od = ImageDraw.Draw(out); ridge(od, 200, 100, 4, (110, 170, 90), (160, 210, 110), 2)
    for x in (30, 90, 160): paste(out, birch_tree(x, .55), x, 140)
    far.alpha_composite(out, (180, 50))
    P = [("cap", -10, 6 + i * 11, 0, WW + 10, 6 + i * 11, 0, 5.8, "log") for i in range(25)]
    wall = render(P, WW, LH, amb=.35, outline=False, seed=5)
    hole = Image.new("L", (WW, LH), 255); ImageDraw.Draw(hole).rectangle([180, 50, 379, 199], fill=0)
    wall.putalpha(Image.composite(wall.getchannel("A"), Image.new("L", (WW, LH), 0), hole)); far.alpha_composite(wall)
    frame = [("cap", 178, 48, 0, 382, 48, 0, 4, "white"), ("cap", 178, 48, 0, 178, 202, 0, 4, "white"), ("cap", 382, 48, 0, 382, 202, 0, 4, "white"),
             ("cap", 280, 50, 0, 280, 200, 0, 2.6, "white"), ("cap", 180, 125, 0, 380, 125, 0, 2.6, "white"),
             ("cap", 160, 210, 4, 400, 210, 4, 6, "linen")]
    far.alpha_composite(render(frame, WW, LH, seed=6))
    d = ImageDraw.Draw(far)
    d.polygon([(165, 44), (205, 22), (280, 12), (355, 22), (395, 44)], fill=(250, 248, 240), outline=OUTL)
    for i in range(7): d.ellipse([196 + i * 25 - 3, 26 - 3, 196 + i * 25 + 3, 26 + 3], fill=(58, 92, 176))
    for x0 in (128, 392):
        d.rectangle([x0, 40, x0 + 38, 206], fill=(196, 44, 52), outline=OUTL)
        for k in range(7): d.line([(x0 + 1, 52 + k * 22), (x0 + 37, 52 + k * 22)], fill=(250, 220, 220), width=2)
        for k in range(3): d.line([(x0 + 10 + k * 10, 41), (x0 + 10 + k * 10, 205)], fill=(250, 220, 220))
    paste(far, obj([("cap", 8, 22, 0, 8, 12, 0, 6, "clay"), ("ell", 8, 8, 4, 9, 7, 6, "leaf"), ("ell", 8, 5, 10, 2.5, 2.5, 2, "berry")], 20, 30), 210, 205)
    return far, Image.new("RGBA", (WW, LH), (0, 0, 0, 0)), (40, 40), "day"

def loc_birches():
    far = sky((110, 176, 236), (232, 244, 236), bands=9, end=.8); d = ImageDraw.Draw(far)
    for x, y, s_ in ((80, 26, .9), (330, 18, .7)): paste(far, cloud(int(x) + 7, s_), x, y, "center")
    ridge(d, WW, 176, 5, (140, 190, 120), (180, 220, 150), 2)
    for i in range(9): paste(far, birch_tree(20 + i, .6), 20 + i * 64 + 10 * hsh(i, 2), 196)
    main = Image.new("RGBA", (WW, LH), (0, 0, 0, 0)); d = ImageDraw.Draw(main)
    ridge(d, WW, 200, 3, (104, 170, 70), (160, 214, 100), 5)
    d.polygon([(0, 236), (180, 226), (400, 226), (WW, 234), (WW, 250), (0, 256)], fill=(214, 190, 140))
    d.line([(0, 236), (180, 226), (400, 226), (WW, 234)], fill=(240, 220, 170))
    grass(d, 0, WW, 206, 226, 120, 4, (80, 140, 60), (160, 210, 100)); flowers(d, 0, WW, 206, 224, 34, 5)
    grass(d, 0, WW, 252, 270, 100, 6, (70, 130, 50), (150, 200, 90)); flowers(d, 0, WW, 254, 268, 20, 7)
    paste(main, birch_tree(3, 1.25), 18, 262); paste(main, birch_tree(4, 1.1), 540, 262)
    return far, main, (0, 60), "day"

def loc_spruce():
    far = sky((150, 196, 206), (214, 230, 222), bands=8, end=.7); d = ImageDraw.Draw(far)
    for i in range(12): paste(far, spruce_tree(30 + i, .7, "leafdark"), i * 50 + 10 * hsh(i, 1), 186)
    main = Image.new("RGBA", (WW, LH), (0, 0, 0, 0)); d = ImageDraw.Draw(main)
    for i in range(8): paste(main, spruce_tree(50 + i, 1.0), 20 + i * 72 + 14 * hsh(i, 3), 210)
    ridge(d, WW, 206, 3, (60, 110, 70), (100, 150, 90), 6)
    d.polygon([(0, 238), (200, 228), (380, 228), (WW, 236), (WW, 252), (0, 258)], fill=(150, 120, 90)); d.line([(0, 238), (200, 228), (380, 228), (WW, 236)], fill=(190, 160, 120))
    for x in (130, 300, 470): paste(main, mushroom(), x, 250)
    grass(d, 0, WW, 252, 270, 100, 8, (40, 90, 50), (90, 140, 80))
    paste(main, spruce_tree(9, 1.9), 20, 270); paste(main, spruce_tree(8, 1.7), 548, 270)
    return far, main, (60, 10), "cool"

def loc_thicket():
    far = sky((86, 120, 96), (160, 176, 130), bands=7, end=.8); d = ImageDraw.Draw(far)
    for i in range(10): paste(far, round_tree(70 + i, 1.1, "leafdark"), i * 60, 200)
    main = Image.new("RGBA", (WW, LH), (0, 0, 0, 0)); d = ImageDraw.Draw(main)
    ridge(d, WW, 204, 3, (70, 96, 50), (110, 140, 70), 8)
    d.polygon([(0, 240), (200, 230), (380, 230), (WW, 238), (WW, 254), (0, 260)], fill=(128, 98, 70)); d.line([(0, 240), (200, 230), (380, 230), (WW, 238)], fill=(160, 128, 90))
    oak = obj([("cap", 20, 270, 0, 22, 0, 0, 16, "trunk"), ("cap", 22, 80, 2, 60, 40, 2, 7, "trunk")], 70, 272)
    paste(main, oak, 20, 272); paste(main, oak.transpose(Image.FLIP_LEFT_RIGHT), 540, 272)
    hive = obj([("ell", 10, 14, 0, 9, 12, 8, "honey")], 22, 30); d.line([(528, 60), (528, 72)], fill=OUTL); paste(main, hive, 528, 96)
    for x in (110, 440): paste(main, bush(int(x), True), x, 230)
    paste(main, obj([("cap", 10, 10, 0, 90, 14, 0, 7, "log")], 100, 24), 250, 266)
    grass(d, 0, WW, 254, 270, 90, 9, (50, 80, 40), (100, 130, 60))
    return far, main, (40, 20), "deep"

def loc_glade():
    far = sky((236, 132, 110), (255, 214, 150), bands=10, end=.85); d = ImageDraw.Draw(far)
    d.ellipse([250, 150, 310, 210], fill=(255, 226, 160)); d.ellipse([260, 160, 300, 200], fill=(255, 246, 210))
    for x, y, s_ in ((70, 40, 1.0), (420, 30, .8)): paste(far, cloud(int(x) + 11, s_, "cloudwarm"), x, y, "center")
    ridge(d, WW, 186, 5, (178, 120, 96), (220, 160, 120), 3)
    for x in (30, 90, 470, 530): paste(far, birch_tree(int(x), .6), x, 200)
    main = Image.new("RGBA", (WW, LH), (0, 0, 0, 0)); d = ImageDraw.Draw(main)
    ridge(d, WW, 204, 3, (170, 150, 70), (230, 200, 110), 5)
    for i in range(260):
        x = hsh(i, 4) * WW; y = 206 + hsh(i, 5) * 64; hh = 4 + 9 * hsh(i, 6)
        d.line([(x, y), (x + 3 * (hsh(i, 7) - .5), y - hh)], fill=(150, 130, 50) if i % 3 else (200, 170, 70))
    flowers(d, 0, WW, 210, 266, 30, 11, (250, 130, 170), (255, 230, 120))
    paste(main, obj([("cap", 20, 20, 0, 20, 4, 0, 14, "log")], 40, 40), 520, 244)
    return far, main, (20, 70), "sunset"

def loc_night():
    far = sky((10, 14, 40), (52, 58, 110), bands=8, end=.9); d = ImageDraw.Draw(far)
    for i in range(140): d.point((int(hsh(i, 1) * WW), int(hsh(i, 2) * 170)), fill=(255, 250, 220) if i % 4 else (200, 210, 255))
    moon = obj([("ell", 20, 20, 0, 18, 18, 18, "stove")], 42, 42, light=np.array([.8, -.3, .5]) / np.linalg.norm([.8, -.3, .5]), amb=.05, rim_on=False)
    paste(far, moon, 440, 30, "center")
    ridge(d, WW, 186, 6, (24, 34, 60), (40, 54, 90), 2)
    main = Image.new("RGBA", (WW, LH), (0, 0, 0, 0)); d = ImageDraw.Draw(main)
    hut = izba(lit=True)
    a = np.asarray(hut).astype(float); lit = (a[..., 0] > 240) & (a[..., 1] > 200) & (a[..., 2] < 140)
    a[..., :3] *= np.array([.28, .3, .5]); a[lit, :3] = (255, 214, 120); hut = Image.fromarray(a.astype(np.uint8))
    paste(main, hut, 230, 220)
    for x in (60, 120, 380, 450, 520):
        sp = spruce_tree(int(x), 1.0); b = np.asarray(sp).astype(float); b[..., :3] *= np.array([.25, .3, .45]); paste(main, Image.fromarray(b.astype(np.uint8)), x, 222)
    ridge(d, WW, 214, 3, (18, 28, 44), (34, 48, 74), 7)
    return far, main, (40, 40), "night"

LOCS = {"village": loc_village, "kitchen": loc_kitchen, "window": loc_window, "birches": loc_birches,
        "spruce": loc_spruce, "thicket": loc_thicket, "glade": loc_glade, "night": loc_night}
GRADE = {"day": (1.0, 1.0, 1.0), "warm": (1.05, .96, .86), "cool": (.92, 1.0, 1.04), "deep": (.86, .92, .86),
         "sunset": (1.08, .95, .86), "night": (1.0, 1.0, 1.0)}

# ============================================================ script (same timing as the score)
SCENES = [("village", 0.0, 7.5), ("kitchen", 7.5, 15.0), ("window", 15.0, 21.5), ("birches", 21.5, 28.0),
          ("spruce", 28.0, 34.5), ("thicket", 34.5, 41.0), ("glade", 41.0, 53.0), ("night", 53.0, 60.0)]
XF = .45
CAST = [  # scene, sprite, x, ground_y, t_in, t_out
    ("village", "ded", 150, GY - 6, 2.4, 9), ("village", "baba", 205, GY - 6, 2.8, 9),
    ("kitchen", "baba", 92, GY, 8.0, 16), ("birches", "hare", 380, GY - 6, 22.8, 29),
    ("spruce", "wolf", 380, GY - 4, 29.3, 35), ("thicket", "bear", 384, GY - 2, 35.8, 42), ("glade", "fox", 362, GY - 4, 42.4, 54),
]
KOLO = {  # scene: path(t) -> (x, y_center, angle_rad, visible)
    "kitchen": lambda t: (400, 212, 0.0, t >= 12.3),
    "window": lambda t: _hop(t, (280, 194), (440, 330), 18.8, 20.0, 15.5),
    "birches": lambda t: _roll2(t, -30, 190, 21.8, 23.0, 660, 26.6, 27.8),
    "spruce": lambda t: _roll2(t, -30, 190, 28.3, 29.5, 660, 33.0, 34.2),
    "thicket": lambda t: _roll2(t, -30, 196, 34.8, 36.0, 660, 39.5, 40.7),
    "glade": lambda t: _fox(t),
}
def _hop(t, a, b, ta, tb, tin):
    k = seg(t, ta, tb); x = lerp(a[0], b[0], k); y = lerp(a[1], b[1], k) - 70 * math.sin(math.pi * min(1, k * 1.6)) * (k < .62)
    return x, y, -k * 9, t >= tin
def _roll2(t, x0, x1, ta, tb, x2, tc, td):
    x = lerp(x0, x1, ss(seg(t, ta, tb))) if t < tc else lerp(x1, x2, seg(t, tc, td) ** 1.5)
    return x, GY - 14, (x - x0) / 14.0, t >= ta - .05
def _fox(t):
    x = lerp(-30, 200, ss(seg(t, 41.3, 42.6))); y = GY - 14; ang = (x + 30) / 14.0
    if t > 47.3:
        k = seg(t, 47.3, 48.3); x = lerp(200, 330, k); y = lerp(GY - 14, 196, k) - 60 * math.sin(math.pi * k); ang += k * 6
    return x, y, ang, 41.2 <= t < 48.95

CAPS = [
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
BUBS = [  # t0, t1, speaker, text, anchor (scene-relative world x, y)
    (4.9, 7.25, "Старик", "Испеки мне, старая, колобок!", "ded"),
    (23.3, 25.2, "Заяц", "Колобок, колобок! Я тебя съем!", "hare"),
    (25.2, 26.6, "Колобок", "Я от дедушки ушёл, я от бабушки ушёл, а от тебя, заяц, не хитро уйти!", "kolo"),
    (29.8, 31.6, "Волк", "Колобок, колобок! Я тебя съем!", "wolf"),
    (31.6, 33.0, "Колобок", "Я от зайца ушёл, а от тебя, волк, не хитро уйти!", "kolo"),
    (36.3, 38.1, "Медведь", "Колобок, колобок! Я тебя съем!", "bear"),
    (38.1, 39.5, "Колобок", "Я от волка ушёл, а от тебя, медведь, не хитро уйти!", "kolo"),
    (43.3, 46.7, "Лиса", "Колобок, колобок! Сядь ко мне на язычок да пропой ещё разок.", "fox"),
]
TITLES = [(0.3, 3.0, "Колобок", .5, .30, 30), (48.95, 50.6, "Ам!", .66, .40, 30), (54.8, 59.3, "Конец", .5, .40, 30)]

# ============================================================ caches
_loc = {}; _spr = {}; _kolo = {}
def loc(name):
    if name not in _loc: _loc[name] = LOCS[name]()
    return _loc[name]
def spr(name):
    if name not in _spr: _spr[name] = chars.SPRITES[name]()
    return _spr[name]
def kolo(ang):
    k = int(round((ang % (2 * math.pi)) / (2 * math.pi) * 24)) % 24
    if k not in _kolo: _kolo[k] = chars.kolobok(k / 24 * 2 * math.pi)
    return _kolo[k]

def scene_of(name): return next(s for s in SCENES if s[0] == name)
def camx(name, t):
    _, t0, t1 = scene_of(name); a, b = loc(name)[2]; return int(round(lerp(a, b, ss(seg(t, t0 - XF, t1 + XF)))))

# ============================================================ per-frame effects (low-res)
def fx(name, img, t, cx):
    d = ImageDraw.Draw(img, "RGBA")
    if name == "village":
        for i in range(7):
            k = ((t * .25 + i / 7) % 1); x = 420 + 33 - cx + 18 * k + 5 * math.sin(t + i); y = 64 - 90 * k; r = 3 + 9 * k
            d.ellipse([x - r, y - r, x + r, y + r], fill=(235, 235, 240, int(150 * (1 - k))))
    if name == "kitchen":
        mx = 400 - cx
        for i in range(26):
            k = (t * 1.6 + hsh(i, 1)) % 1; x = mx + (hsh(i, 2) - .5) * 44 * (1 - k) + 3 * math.sin(t * 9 + i); y = 228 - 34 * k
            col = (255, 240, 160) if k < .3 else (255, 170, 60) if k < .65 else (220, 70, 40); r = 4 * (1 - k) + 1
            d.rectangle([x - r, y - r, x + r, y + r], fill=col + (230,))
        for i in range(6):
            k = (t * .6 + i / 6) % 1; d.point((60 - cx + 40 * hsh(i, 3) + 50 * k, 70 + 120 * k), fill=(255, 240, 200, 160))
    if name == "birches":
        for i in range(14):
            k = (t * .12 + hsh(i, 3)) % 1; x = (hsh(i, 4) * 520 + 30 * math.sin(t * 1.3 + i) - cx * .5) % 480; y = -10 + 260 * k
            d.rectangle([x, y, x + 1, y], fill=(200, 210, 80, 230) if i % 2 else (240, 200, 60, 230))
    if name == "spruce":
        for j, (y, a) in enumerate(((200, 60), (214, 80), (226, 50))):
            off = (t * (8 + 4 * j)) % 120
            for x in range(-120, 480, 120): d.ellipse([x + off - 70, y - 8, x + off + 70, y + 8], fill=(220, 236, 236, a))
    if name == "thicket":
        for i in range(18):
            x = (hsh(i, 5) * 480 + 10 * math.sin(t * .7 + i)) % 480; y = 60 + hsh(i, 6) * 150 + 8 * math.sin(t + i * 2)
            if math.sin(t * 2.3 + i) > .2: d.point((x, y), fill=(255, 250, 200, 200))
    if name == "glade":
        for i in range(5):
            a0 = -2.2 + i * .25 + .05 * math.sin(t * .5 + i); x0, y0 = 280 - cx * .5, 180
            d.polygon([(x0, y0), (x0 + 400 * math.cos(a0), y0 + 400 * math.sin(a0)), (x0 + 400 * math.cos(a0 + .07), y0 + 400 * math.sin(a0 + .07))], fill=(255, 230, 170, 26))
        for i in range(16):
            k = (t * .07 + hsh(i, 7)) % 1; x = (hsh(i, 8) * 480 + 120 * k) % 480; y = 230 - 180 * k + 6 * math.sin(t * 2 + i)
            d.point([(x, y), (x + 1, y)], fill=(255, 250, 230, 220))
    if name == "night":
        for i in range(14):
            x = (hsh(i, 9) * 480 + 20 * math.sin(t * .5 + i)) % 480; y = 170 + hsh(i, 10) * 80 + 6 * math.sin(t * 1.3 + i)
            a = .5 + .5 * math.sin(t * 3 + i * 1.7)
            d.point((x, y), fill=(220, 255, 140, int(255 * a)))
            if a > .8: d.point([(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)], fill=(220, 255, 140, 90))

def glow_layer(name, t, cx):
    """additive light, low-res RGB float"""
    g = Image.new("RGB", (LW, LH), (0, 0, 0)); d = ImageDraw.Draw(g)
    if name == "kitchen":
        a = .8 + .2 * math.sin(t * 11) + .1 * math.sin(t * 23); x = 400 - cx
        d.ellipse([x - 60, 170, x + 60, 250], fill=(int(160 * a), int(70 * a), int(20 * a)))
    if name == "glade": d.ellipse([280 - 20 * 0 - cx * .5 - 70, 110, 280 - cx * .5 + 70, 250], fill=(150, 90, 40))
    if name == "night":
        x = 230 - cx; d.ellipse([x - 40, 120, x + 40, 200], fill=(120, 80, 20)); d.ellipse([440 - cx * .5 - 40, -10, 440 - cx * .5 + 40, 70], fill=(60, 60, 80))
    if name == "village": d.ellipse([485 - cx * .5 - 40, -7, 485 - cx * .5 + 40, 73], fill=(90, 80, 40))
    return g.filter(ImageFilter.GaussianBlur(14))

# ============================================================ compose one scene (low-res RGBA) + anchors
def pop_in(t, ti, to):
    if t < ti or t > to: return None
    k = seg(t, ti, ti + .5); out = 1 - ss(seg(t, to - .35, to))
    return back(k, 2.0), ss(seg(t, ti, ti + .25)) * out

def scene_img(name, t):
    far, main, _, grade = loc(name); cx = camx(name, t)
    img = Image.new("RGBA", (LW, LH), (0, 0, 0, 255))
    fx_ = int(round(cx * .5)); img.alpha_composite(far.crop((fx_, 0, fx_ + LW, LH)))
    img.alpha_composite(main.crop((cx, 0, cx + LW, LH)))
    anchors = {}
    for scn, s_, x, gy, ti, to in CAST:
        if scn != name: continue
        p = pop_in(t, ti, to)
        if not p: continue
        rise, alpha = p; im = spr(s_)
        if alpha < 1:
            im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
        sway = int(round(math.sin(t * 2.2 + x) * .6))
        y = gy + int(round((1 - rise) * 14))
        sh = Image.new("RGBA", (im.width + 8, 6), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse([0, 0, im.width + 7, 5], fill=(20, 10, 30, int(90 * alpha)))
        img.alpha_composite(sh, (int(x - cx - sh.width / 2), gy - 3))
        img.alpha_composite(im, (int(x - cx - im.width / 2) + sway, int(y - im.height)))
        anchors[s_] = (x - cx, gy - im.height - 4)
    if name in KOLO:
        kx, ky, ang, vis = KOLO[name](t)
        if vis:
            im = kolo(ang)
            if name == "kitchen":
                k = seg(t, 12.3, 12.8); s_ = back(k, 2.4)
                if s_ < .99: im = im.resize((max(1, int(im.width * s_)), max(1, int(im.height * s_))), Image.NEAREST)
            if ky > GY - 20:
                sh = Image.new("RGBA", (30, 5), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse([0, 0, 29, 4], fill=(20, 10, 30, 90)); img.alpha_composite(sh, (int(kx - cx - 15), GY - 3))
            img.alpha_composite(im, (int(kx - cx - im.width / 2), int(ky - im.height / 2)))
            anchors["kolo"] = (kx - cx, ky - 18)
    fx(name, img, t, cx)
    gr = GRADE[grade]
    if gr != (1.0, 1.0, 1.0):
        a = np.asarray(img).astype(np.float32); a[..., :3] *= np.array(gr); img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return img, glow_layer(name, t, cx), anchors

# ============================================================ UI at full resolution (pixel font, smooth motion)
@lru_cache(maxsize=256)
def word_img(word, size, col, font=FONT):
    f = ImageFont.truetype(font, size); w = int(f.getlength(word)) + 4
    im = Image.new("RGBA", (w, size + 6), (0, 0, 0, 0)); d = ImageDraw.Draw(im); d.fontmode = "1"
    d.text((2, 2), word, font=f, fill=(20, 12, 30, 255)); d.text((1, 1), word, font=f, fill=col + (255,))
    return im.resize((im.width * SC, im.height * SC), Image.NEAREST)

@lru_cache(maxsize=64)
def box_img(wl, hl, style):
    im = Image.new("RGBA", (wl, hl), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if style == "narr":
        d.rectangle([0, 1, wl - 1, hl - 2], fill=(20, 14, 40, 235)); d.rectangle([1, 0, wl - 2, hl - 1], fill=(20, 14, 40, 235))
        d.rectangle([2, 2, wl - 3, hl - 3], outline=(240, 200, 110)); d.rectangle([3, 3, wl - 4, hl - 4], outline=(120, 80, 60))
        for x, y in ((2, 2), (wl - 3, 2), (2, hl - 3), (wl - 3, hl - 3)): d.point((x, y), fill=(255, 240, 180))
    else:
        d.rectangle([0, 1, wl - 1, hl - 7], fill=(252, 248, 236)); d.rectangle([1, 0, wl - 2, hl - 6], fill=(252, 248, 236))
        d.rectangle([1, 1, wl - 2, hl - 7], outline=(28, 18, 30))
        d.polygon([(wl // 2 - 4, hl - 7), (wl // 2 + 4, hl - 7), (wl // 2, hl - 1)], fill=(252, 248, 236), outline=(28, 18, 30))
        d.line([(wl // 2 - 3, hl - 7), (wl // 2 + 3, hl - 7)], fill=(252, 248, 236))
    return im.resize((wl * SC, hl * SC), Image.NEAREST)

def wrap(words, size, maxw):
    f = ImageFont.truetype(FONT, size); sp = f.getlength(" "); lines, cur, w = [], [], 0
    for wd in words:
        ww = f.getlength(wd)
        if cur and w + sp + ww > maxw: lines.append(cur); cur, w = [wd], ww
        else: cur.append(wd); w += (sp if cur[:-1] else 0) + ww
    return lines + [cur], sp

def fade(im, a):
    if a >= .999: return im
    im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a))); return im

def text_block(img, t, t0, t1, text, cx_px, top_px, size, col, maxw_l, style, name=None, anchor=None):
    """box + words that drift up and fade in one after another (smooth, sub-pixel at 1080p)"""
    if not (t0 <= t < t1 + .3): return
    words = text.split(" "); lines, sp = wrap(words, size, maxw_l)
    lh = size + 4; wl = int(max(sum(ImageFont.truetype(FONT, size).getlength(w) for w in ln) + sp * (len(ln) - 1) for ln in lines)) + 16
    hl = len(lines) * lh + 10 + (6 if style == "bubble" else 0)
    kin = eout(seg(t, t0, t0 + .35)); kout = ss(seg(t, t1, t1 + .3)); a = kin * (1 - kout)
    if a <= .01: return
    bx = box_img(wl, hl, style)
    bw, bh = bx.width, bx.height
    x0 = cx_px - bw / 2; y0 = top_px - (bh if style == "bubble" else 0)
    x0 = min(max(x0, 24), W - bw - 24); y0 += (1 - kin) * 22 - kout * 18
    img.alpha_composite(fade(bx, a), (int(x0), int(y0)))
    if name:
        tag = word_img(name, 9, (255, 236, 160), FONT)
        pad = Image.new("RGBA", (tag.width + 16, tag.height + 4), (90, 40, 70, 255)); pad.alpha_composite(tag, (8, 2))
        img.alpha_composite(fade(pad, a), (int(x0 + 16), int(y0 - pad.height + 8)))
    i = 0; f = ImageFont.truetype(FONT, size)
    for li, ln in enumerate(lines):
        lw_ = sum(f.getlength(w) for w in ln) + sp * (len(ln) - 1); x = x0 + (bw - lw_ * SC) / 2; y = y0 + (5 + li * lh) * SC
        for wd in ln:
            k = eout(seg(t, t0 + .2 + i * .06, t0 + .55 + i * .06)); wa = k * (1 - kout)
            wi = word_img(wd, size, col)
            if wa > .01: img.alpha_composite(fade(wi, wa), (int(x), int(y + (1 - k) * 18)))
            x += (f.getlength(wd) + sp) * SC; i += 1

def title(img, t, t0, t1, txt, px, py, size):
    if not (t0 <= t < t1): return
    k = seg(t, t0, t0 + .6); out = ss(seg(t, t1 - .4, t1)); a = ss(k * 2) * (1 - out)
    f = ImageFont.truetype(FONT, size); w = int(f.getlength(txt)) + 8
    im = Image.new("RGBA", (w, size + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im); d.fontmode = "1"
    for dx in (-1, 0, 1, 2):
        for dy in (-1, 0, 1, 2): d.text((3 + dx, 3 + dy), txt, font=f, fill=(28, 18, 30))
    m = Image.new("L", im.size, 0); md = ImageDraw.Draw(m); md.fontmode = "1"; md.text((3, 3), txt, font=f, fill=255)
    grad = Image.new("RGBA", im.size); gd = ImageDraw.Draw(grad)
    for y in range(im.height):
        c = (255, 244, 170) if y < size * .45 else (250, 196, 60) if y < size * .75 else (214, 120, 40); gd.line([(0, y), (im.width, y)], fill=c)
    im.paste(grad, (0, 0), m)
    big = im.resize((im.width * SC, im.height * SC), Image.NEAREST)
    s = .85 + .15 * back(k, 2.0); bw, bh = int(big.width * s), int(big.height * s)
    big = big.resize((bw, bh), Image.NEAREST)
    y = H * py - bh / 2 + math.sin(t * 2) * 6 + (1 - ss(k)) * 30
    img.alpha_composite(fade(big, a), (int(W * px - bw / 2), int(y)))

# ============================================================ frame
def frame(t):
    cur = [s for s in SCENES if s[1] - XF <= t < s[2] + XF]
    a_img, a_glow, anc = scene_img(cur[0][0], t); name = cur[0][0]
    if len(cur) > 1:   # pixel dissolve (ordered Bayer threshold, 2x2 blocks)
        b_img, b_glow, banc = scene_img(cur[1][0], t); k = ss(seg(t, cur[1][1] - XF, cur[1][1] + XF))
        thr = np.kron(np.tile(BAYER, (LH // 8 + 1, LW // 8 + 1)), np.ones((2, 2)))[:LH, :LW]
        m = Image.fromarray(((thr < k) * 255).astype(np.uint8))
        a_img = Image.composite(b_img, a_img, m); a_glow = Image.blend(a_glow, b_glow, k)
        if k > .5: anc, name = banc, cur[1][0]
    low = a_img.convert("RGB")
    # bloom: bright pass of the low-res frame + scene light, blurred, added at full res
    arr = np.asarray(low).astype(np.float32)
    lum = arr @ np.array([.3, .59, .11]); bp = arr * (np.clip((lum - 170) / 85, 0, 1)[..., None])
    bloom = Image.fromarray(np.clip(bp, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5))
    add = np.asarray(bloom).astype(np.float32) * .55 + np.asarray(a_glow).astype(np.float32) * .6
    up = np.asarray(low.resize((W, H), Image.NEAREST)).astype(np.float32)
    addu = np.asarray(Image.fromarray(np.clip(add, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32)
    out = np.clip(up + addu, 0, 255)
    out *= VIGN
    img = Image.fromarray(out.astype(np.uint8)).convert("RGBA")
    for t0, t1, txt in CAPS:
        text_block(img, t, t0, t1, txt, W / 2, 26, 12, (255, 246, 222), 400, "narr")
    for t0, t1, who, txt, key in BUBS:
        if t0 - .1 <= t < t1 + .35:
            ax, ay = anc.get(key, (LW / 2, 120))
            text_block(img, t, t0, t1, txt, ax * SC, (ay - 2) * SC, 10, (40, 26, 40), 180, "bubble", who)
    for tt in TITLES: title(img, t, *tt)
    o = img.convert("RGB")
    if t < .7: o = Image.blend(Image.new("RGB", (W, H)), o, ss(t / .7))
    if t > DUR - 1.2: o = Image.blend(o, Image.new("RGB", (W, H)), ss((t - DUR + 1.2) / 1.2))
    return o

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGN = (1 - .32 * np.clip(((xx / W - .5) ** 2 + (yy / H - .5) ** 2) * 2.4, 0, 1))[..., None]

def init():
    for n in LOCS: loc(n)
    for n in chars.SPRITES: spr(n)
    for k in range(24): kolo(k / 24 * 2 * math.pi)

def rb(i): return frame(i / FPS).tobytes()

if __name__ == "__main__":
    out = sys.argv[1]
    if "--preview" in sys.argv:
        for tt in [float(v) for v in sys.argv[sys.argv.index("--preview") + 1].split(",")]: frame(tt).save(f"{out}_{tt:05.1f}.png")
        sys.exit()
    n = int(DUR * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    with Pool(4, initializer=init) as pool:
        for i, b in enumerate(pool.imap(rb, range(n), chunksize=4)):
            ff.stdin.write(b)
            if i % 240 == 0: print(f"frame {i}/{n}", flush=True)
    ff.stdin.close(); ff.wait()
