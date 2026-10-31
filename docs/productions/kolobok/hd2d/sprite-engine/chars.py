"""Character sprites built from 3D primitives (facing right; animals are flipped to face left)."""
import math
from pix import render, decal, flip_prims, flip_ops

EYE = (24, 16, 26); WH = (255, 255, 255); RED = (200, 40, 50); PINK = (230, 130, 140)

def finish(prims, ops, w, h, flip=False, **kw):
    if flip: prims, ops = flip_prims(prims, w), flip_ops(ops, w)
    im = render(prims, w, h, **kw)
    from PIL import Image
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); decal(lay, ops)
    mask = im.getchannel("A"); lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", im.size, 0), mask))
    im.alpha_composite(lay)
    return im.crop(im.getbbox())

def ded():
    w, h, c = 60, 100, 30
    P = [("ell", c - 7, 95, 4, 6, 3, 5, "bast"), ("ell", c + 7, 95, 4, 6, 3, 5, "bast"),
         ("cap", c - 6, 78, 2, c - 7, 92, 3, 4.2, "white"), ("cap", c + 6, 78, 2, c + 7, 92, 3, 4.2, "white"),
         ("cap", c - 6, 66, 1, c - 6, 80, 1, 4.6, "trous"), ("cap", c + 6, 66, 1, c + 6, 80, 1, 4.6, "trous"),
         ("ell", c, 52, 0, 15, 22, 11, "linen"), ("ell", c, 66, 0, 16, 9, 10, "linen"),
         ("cap", c - 13, 36, 2, c - 17, 52, 5, 4.2, "linen"), ("cap", c - 17, 52, 5, c - 12, 63, 9, 4.0, "linen"),
         ("cap", c + 13, 36, 2, c + 17, 52, 5, 4.2, "linen"), ("cap", c + 17, 52, 5, c + 12, 63, 9, 4.0, "linen"),
         ("ell", c - 11, 65, 10, 4, 4, 4, "skin"), ("ell", c + 11, 65, 10, 4, 4, 4, "skin"),
         ("ell", c, 19, -2, 11.5, 11, 9, "beard"), ("ell", c, 20, 1, 10, 11, 10, "skin"),
         ("ell", c, 33, 6, 9, 12, 6, "beard"), ("ell", c - 3, 28, 10, 4, 2.4, 3, "beard"), ("ell", c + 3, 28, 10, 4, 2.4, 3, "beard"),
         ("ell", c, 24, 11, 2.6, 2.6, 2, "skin")]
    ops = [("rect", (c - 9, 58, c + 9, 60), RED), ("px", [(c - 11 + i * 3, 73) for i in range(8)], RED),
           ("px", [(c - 4, 20), (c + 4, 20), (c - 4, 21), (c + 4, 21)], EYE), ("line", [(c - 6, 17), (c - 3, 16)], (150, 150, 165)),
           ("line", [(c + 3, 16), (c + 6, 17)], (150, 150, 165)), ("px", [(c - 7, 24), (c + 7, 24)], (240, 140, 130)),
           ("line", [(c - 4, 42), (c, 44), (c + 4, 42)], RED)]
    return finish(P, ops, w, h)

def baba():
    w, h, c = 62, 100, 31
    P = [("ell", c - 6, 96, 3, 5, 2.5, 4, "dark"), ("ell", c + 6, 96, 3, 5, 2.5, 4, "dark"),
         ("ell", c, 64, 0, 17, 32, 11, "red"), ("ell", c, 50, 2, 12, 14, 10, "red"),
         ("ell", c, 70, 8, 9, 22, 3, "linen"),
         ("cap", c - 12, 38, 2, c - 16, 52, 5, 4.8, "linen"), ("cap", c - 16, 52, 5, c - 8, 58, 11, 4.2, "linen"),
         ("cap", c + 12, 38, 2, c + 16, 52, 5, 4.8, "linen"), ("cap", c + 16, 52, 5, c + 8, 58, 11, 4.2, "linen"),
         ("ell", c, 56, 14, 9, 4, 4, "clay"), ("ell", c, 53, 16, 6, 2, 2, "bread"),
         ("ell", c, 19, -1, 13, 13, 11, "scarf"), ("ell", c, 31, 4, 4, 3, 3, "scarf"),
         ("ell", c, 21, 3, 8.5, 9.5, 9, "skin"), ("ell", c, 23, 11, 2.2, 2.2, 2, "skin")]
    dots = [(c - 9, 12), (c - 4, 9), (c + 2, 8), (c + 8, 11), (c + 11, 17), (c - 11, 19), (c + 10, 23), (c - 10, 25)]
    ops = [("px", dots, RED), ("px", [(c - 3, 20), (c + 3, 20), (c - 3, 21), (c + 3, 21)], EYE),
           ("px", [(c - 6, 24), (c + 6, 24)], (240, 140, 130)), ("line", [(c - 2, 27), (c, 28), (c + 2, 27)], (140, 60, 60)),
           ("rect", (c - 16, 88, c + 16, 89), (240, 190, 60))]
    return finish(P, ops, w, h)

def kolobok(rot=0.0):
    w, h, c = 34, 34, 17
    P = [("ell", c, c, 0, 14, 14, 14, "bread", rot)]
    ca, sa = math.cos(rot), math.sin(rot)
    def R(x, y): return (round(c + x * ca - y * sa), round(c + x * sa + y * ca))
    face = math.cos(rot) > -0.2   # the face turns away as he rolls
    ops = []
    if face:
        ops = [("px", [R(-4, -3), R(-4, -2), R(4, -3), R(4, -2)], EYE), ("px", [R(-6, 2), R(6, 2)], (240, 120, 90)),
               ("px", [R(-3, 3), R(-2, 4), R(-1, 5), R(0, 5), R(1, 5), R(2, 4), R(3, 3)], (90, 30, 20))]
    return finish(P, ops, w, h)

def hare():
    w, h, c = 50, 92, 24
    P = [("ell", c - 8, 88, 3, 9, 3.5, 6, "hare"), ("ell", c + 6, 88, 3, 9, 3.5, 6, "hare"),
         ("ell", c, 66, 0, 14, 20, 12, "hare"), ("ell", c + 4, 68, 7, 8, 14, 6, "harebelly"),
         ("cap", c + 6, 56, 9, c + 10, 64, 11, 3, "hare"),
         ("cap", c - 1, 30, -2, c - 4, 4, -3, 3.6, "hare"), ("cap", c + 5, 30, 0, c + 8, 3, -1, 3.6, "hare"),
         ("ell", c + 3, 38, 2, 10, 9, 9, "hare"), ("ell", c + 9, 41, 8, 5, 4, 4, "harebelly"),
         ("ell", c - 12, 72, -4, 5, 5, 4, "harebelly")]
    ops = [("line", [(c + 8, 6), (c + 8, 26)], PINK), ("line", [(c - 3, 7), (c - 2, 27)], PINK),
           ("px", [(c + 7, 36), (c + 7, 37), (c + 8, 36)], EYE), ("px", [(c + 8, 35)], WH),
           ("px", [(c + 13, 40), (c + 14, 40)], PINK), ("line", [(c + 12, 43), (c + 19, 41)], (90, 80, 90)),
           ("line", [(c + 12, 44), (c + 19, 46)], (90, 80, 90)), ("px", [(c - 4, 3), (c + 8, 2)], (40, 30, 40))]
    return finish(P, ops, w, h, flip=True)

def wolf():
    w, h, c = 104, 80, 50
    P = [("cap", c - 30, 40, -6, c - 46, 62, -6, 5.5, "wolf"),
         ("cap", c - 20, 50, -4, c - 22, 76, -4, 4, "wolf"), ("cap", c + 18, 50, -4, c + 20, 76, -4, 4, "wolf"),
         ("ell", c - 2, 44, 0, 30, 14, 12, "wolf"), ("ell", c + 22, 38, 3, 12, 14, 11, "wolf"), ("ell", c + 22, 46, 9, 8, 9, 5, "wolflight"),
         ("cap", c - 14, 50, 6, c - 13, 77, 6, 4, "wolf"), ("cap", c + 24, 50, 6, c + 26, 77, 6, 4, "wolf"),
         ("cap", c + 28, 18, 2, c + 26, 6, 1, 3, "wolf"), ("cap", c + 36, 18, 4, c + 37, 6, 3, 3, "wolf"),
         ("ell", c + 33, 25, 6, 11, 9, 9, "wolf"), ("cap", c + 38, 28, 8, c + 51, 31, 8, 4.6, "wolf"),
         ("cap", c + 40, 32, 8, c + 50, 34, 8, 2.6, "wolflight")]
    ops = [("px", [(c + 52, 30), (c + 53, 30), (c + 52, 31), (c + 53, 31)], EYE),
           ("px", [(c + 37, 22), (c + 38, 22)], (250, 210, 80)), ("px", [(c + 38, 22)], EYE),
           ("line", [(c + 34, 19), (c + 40, 21)], EYE), ("px", [(c + 44, 34), (c + 46, 34), (c + 48, 34)], WH),
           ("px", [(c + 26, 6), (c + 37, 6)], EYE)]
    return finish(P, ops, w, h, flip=True)

def bear():
    w, h, c = 80, 112, 40
    P = [("cap", c - 11, 82, 0, c - 12, 104, 1, 8, "bear"), ("cap", c + 11, 82, 0, c + 12, 104, 1, 8, "bear"),
         ("ell", c, 66, 0, 24, 30, 18, "bear"), ("ell", c, 70, 12, 14, 20, 6, "bearlight"),
         ("cap", c - 20, 48, 4, c - 28, 70, 10, 7, "bear"), ("cap", c + 20, 48, 4, c + 28, 70, 10, 7, "bear"),
         ("ell", c - 12, 18, -2, 6, 6, 5, "bear"), ("ell", c + 12, 18, -2, 6, 6, 5, "bear"),
         ("ell", c, 30, 0, 15, 14, 13, "bear"), ("ell", c, 35, 11, 7, 5.5, 5, "bearlight"), ("ell", c, 32, 15, 3, 2.2, 2, "dark")]
    ops = [("px", [(c - 6, 27), (c + 6, 27), (c - 6, 28), (c + 6, 28)], EYE), ("px", [(c - 6, 26)], WH), ("px", [(c + 6, 26)], WH),
           ("line", [(c - 2, 39), (c, 40), (c + 2, 39)], EYE), ("px", [(c - 12, 18), (c + 12, 18)], (90, 50, 40))]
    return finish(P, ops, w, h)

def fox():
    w, h, c = 80, 84, 36
    P = [("ell", c - 16, 74, -4, 18, 8, 8, "fox"), ("ell", c - 30, 74, -2, 7, 6, 6, "foxwhite"),
         ("ell", c, 56, 0, 13, 21, 11, "fox"), ("ell", c + 5, 56, 8, 7, 14, 4, "foxwhite"),
         ("cap", c + 6, 64, 8, c + 7, 80, 8, 2.4, "dark"), ("cap", c + 12, 64, 6, c + 13, 80, 6, 2.4, "dark"),
         ("cap", c + 2, 22, 0, c, 8, -1, 3.4, "fox"), ("cap", c + 11, 22, 1, c + 13, 8, 0, 3.4, "fox"),
         ("ell", c + 6, 28, 2, 10, 9, 9, "fox"), ("cap", c + 10, 31, 6, c + 24, 34, 6, 4, "fox"),
         ("cap", c + 12, 35, 7, c + 23, 36, 7, 2.6, "foxwhite")]
    ops = [("px", [(c + 25, 33), (c + 26, 33), (c + 25, 34)], EYE),
           ("line", [(c + 10, 26), (c + 14, 25), (c + 16, 27)], EYE), ("px", [(c + 0, 8), (c + 13, 8), (c + 0, 9), (c + 13, 9)], EYE)]
    return finish(P, ops, w, h, flip=True)

SPRITES = {"ded": ded, "baba": baba, "hare": hare, "wolf": wolf, "bear": bear, "fox": fox}
