"""Score + foley for «Колобок», read from timeline.json. Chamber-fairy palette: harp, celesta,
strings, recorder; a music box at night. 84 BPM, D minor; the score stops dead on «Ам!».
usage: .venv/bin/python films/kolobok/mix.py  → films/kolobok/out/mix.wav"""
import json, os, wave
import numpy as np
from scipy.signal import butter, lfilter, fftconvolve

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(HERE, "timeline.json")))
SR = 48000; DUR = TL["dur"]; N = int(SR * DUR); rng = np.random.default_rng(11)
BEAT = 60 / TL["bpm"]; BAR = 4 * BEAT
mus = np.zeros((N, 2)); fx = np.zeros((N, 2))

def put(buf, t, x, g=1., pan=0.):
    i = int(t * SR)
    if i >= N: return
    x = x[: N - max(i, 0)]
    if i < 0: x = x[-i:]; i = 0
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(x), 0] += x * g * l * 1.41; buf[i:i + len(x), 1] += x * g * r * 1.41
def env(n, a=.005, r=None):
    e = np.ones(n); ai = max(1, int(a * SR)); e[:ai] = np.linspace(0, 1, ai)
    if r: e *= np.exp(-np.arange(n) / (r * SR))
    return e
def lp(x, f): b, a = butter(2, min(f, SR / 2 - 100) / (SR / 2)); return lfilter(b, a, x)
def bp(x, lo, hi): b, a = butter(2, [lo / (SR / 2), hi / (SR / 2)], "band"); return lfilter(b, a, x)
def hz(m): return 440 * 2 ** ((m - 69) / 12)
def noise(d): return rng.uniform(-1, 1, int(d * SR))

_c = {}
def harp(m, d=2.6, bright=.5):
    if (m, d) in _c: return _c[(m, d)]
    P = int(SR / hz(m)); n = int(d * SR); y = np.zeros(n); buf = lp(rng.uniform(-1, 1, P), 2500 + 3000 * bright) if P > 24 else rng.uniform(-1, 1, P); pos = 0
    while pos < n: k = min(P, n - pos); y[pos:pos + k] = buf[:k]; buf = .9975 * .5 * (buf + np.roll(buf, -1)); pos += P
    y *= env(n, .002); _c[(m, d)] = y; return y
def celesta(m, d=1.8):
    t = np.arange(int(d * SR)) / SR; f = hz(m)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 2.4) + .45 * np.sin(2 * np.pi * f * 4.0 * t) * np.exp(-t * 7) + .2 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t * 4)) * env(len(t), .002)
def musicbox(m, d=2.2):
    t = np.arange(int(d * SR)) / SR; f = hz(m)
    return (np.sin(2 * np.pi * f * t) + .6 * np.sin(2 * np.pi * f * 3.0 * t) * np.exp(-t * 3) + .3 * np.sin(2 * np.pi * f * 5.03 * t) * np.exp(-t * 6)) * np.exp(-t * 1.8) * env(len(t), .001)
def strings(ms, d, g=1.):
    t = np.arange(int(d * SR)) / SR; x = np.zeros(len(t))
    for m in ms:
        for det in (-.16, 0, .16):
            vib = 1 + .0035 * np.sin(2 * np.pi * 5.2 * t + m)
            ph = 2 * np.pi * hz(m) * (1 + det / 100) * np.cumsum(vib) / SR; x += (ph / np.pi) % 2 - 1
    x = lp(x, 1800); e = np.minimum(1, t / .7) * np.minimum(1, (d - t) / .7); return x * e * g / len(ms) / 3
def recorder(m, d):
    t = np.arange(int(d * SR)) / SR; f = hz(m) * (1 + .004 * np.sin(2 * np.pi * 5 * t))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) + .08 * np.sin(4 * np.pi * np.cumsum(f) / SR) + .05 * bp(rng.uniform(-1, 1, len(t)), 1500, 5000)
    return x * np.minimum(1, t / .05) * np.minimum(1, (d - t) / .08)

# —— harmony per bar (21 bars) ——
Dm, Bb, F, A, Gm, C, D = [50, 53, 57], [46, 50, 53], [53, 57, 60], [45, 49, 52], [43, 46, 50], [48, 52, 55], [50, 54, 57]
BARS = [Dm, Bb, F, A,  Dm, Gm, A,  Dm, Bb,  F, C,  Dm, A,  Gm, Dm,  Gm, A, None, D, D, D]
MEL = {0: [74, 77, 76, 74], 1: [72, 69, 70, 72], 2: [74, 72, 70, 69], 3: [67, 69, 64, 69],
       8: [77, 76, 74, 72], 9: [74, 72, 69, 72], 10: [76, 74, 72, 74], 11: [77, 74, 72, 69], 12: [73, 72, 69, 73]}
REC = {3: [69, 72, 74, 72], 4: [74, 72, 69, 67], 5: [69, 70, 69, 67]}       # recorder in the izba
AM = TL["events"]["am"]
for b, ch in enumerate(BARS):
    t = b * BAR
    if ch is None: continue
    night = b >= 18; fox = b in (15, 16)
    put(mus, t, strings([m + 12 for m in ch], BAR + .8, .9 if not night else .6), .09, -.2)
    if not night:
        arp = ch + [c + 12 for c in ch] + [ch[1] + 24]
        order = [0, 1, 2, 3, 4, 5, 6, 5] if not fox else [0, 2, 4, 6, 4, 2, 0, 2]
        for i, k in enumerate(order): put(mus, t + i * BEAT / 2, harp(arp[k] + 12), .13 if not fox else .1, .25)
        if 6 <= b <= 14:
            for k in (0, 2): put(mus, t + k * BEAT, harp(ch[0] - 12, .6) * env(int(.6 * SR), .002, .14), .3, -.1)
        if b in MEL:
            for i, m in enumerate(MEL[b]): put(mus, t + i * BEAT, celesta(m), .08, .15)
        if b in REC:
            for i, m in enumerate(REC[b]): put(mus, t + i * BEAT, recorder(m, BEAT * .95), .045, -.3)
    else:
        for i, m in enumerate([62, 66, 69, 74, 69, 66, 69, 74] if b < 20 else [62, 66, 69, 74, 78, 81, 78, 74]):
            put(mus, t + i * BEAT / 2, musicbox(m + 12), .07, .1)
put(mus, 20 * BAR, strings([62, 66, 69, 74], 2.8, .9), .1)
# the score dies on «Ам!»: hard cut, only the reverb tail survives
cut = int(AM * SR); n_rel = int(.04 * SR); mus[cut:cut + n_rel] *= np.linspace(1, 0, n_rel)[:, None]; mus[cut + n_rel:int(18 * BAR * SR)] = 0
# hall reverb on the music bus
ir_n = int(2.4 * SR); ir = rng.standard_normal((ir_n, 2)) * np.exp(-np.arange(ir_n) / (.55 * SR))[:, None]; ir[:, 0] = lp(ir[:, 0], 6000); ir[:, 1] = lp(ir[:, 1], 6000)
dry = mus.copy(); wet = np.stack([fftconvolve(dry[:, i], ir[:, i])[:N] for i in range(2)], 1); wet /= np.abs(wet).max() + 1e-9
mus = dry + wet * np.abs(dry).max() * .35

# —— foley ——
def chime(t, g=.06, pan=0):
    for i, m in enumerate((88, 91, 95, 98, 100)): put(fx, t + i * .04, celesta(m, .6), g, pan)
def pop(t, g=.15): n = int(.12 * SR); tt = np.arange(n) / SR; put(fx, t, np.sin(2 * np.pi * (900 * np.exp(-tt * 18) + 200) * tt) * env(n, .001, .04), g)
def whoosh(t, d=.8, g=.1):
    n = int(d * SR); put(fx, t, bp(noise(d), 500, 3500) * np.sin(np.pi * np.arange(n) / n) ** 2, g)
def roll(t0, t1, g=.12):
    d = t1 - t0; n = int(d * SR); tt = np.arange(n) / SR
    put(fx, t0, lp(noise(d), 380) * (1 + .5 * np.sin(2 * np.pi * 9 * tt)) * np.sin(np.pi * tt / d) * 3, g)
def boing(t, g=.12): n = int(.42 * SR); tt = np.arange(n) / SR; f = 260 + 320 * tt / .42; put(fx, t, np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .003, .16), g)
def crackle(t0, t1, g=.05):
    t = t0
    while t < t1: n = int(.02 * SR); put(fx, t, bp(noise(.02), 1500, 6000) * env(n, .001, .005), g * (.4 + rng.random()), rng.uniform(-.4, .6)); t += .04 + .18 * rng.random()
def fireroar(t0, d=1.6, g=.18): n = int(d * SR); tt = np.arange(n) / SR; put(fx, t0, lp(noise(d), 700) * np.exp(-tt / .5) * np.minimum(1, tt / .03) * 3, g)
def bird(t, g=.035, pan=0):
    n = int(.18 * SR); tt = np.arange(n) / SR; f = 2900 + 900 * np.sin(2 * np.pi * 9 * tt); put(fx, t, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / .18), g, pan)
def growl(t, g=.16): n = int(1.0 * SR); tt = np.arange(n) / SR; put(fx, t, (np.sin(2 * np.pi * (68 + 9 * np.sin(2 * np.pi * 21 * tt)) * tt) + .4 * lp(noise(1.0), 300)) * np.sin(np.pi * tt), g)
def chomp(t): n = int(.3 * SR); tt = np.arange(n) / SR; put(fx, t, (np.sin(2 * np.pi * 85 * tt) + .7 * bp(noise(.3), 200, 2500)) * env(n, .001, .07), .5)
def crickets(t0, t1, g=.02):
    t = t0
    while t < t1:
        for k in range(3): n = int(.03 * SR); tt = np.arange(n) / SR; put(fx, t + k * .055, np.sin(2 * np.pi * 4700 * tt) * np.sin(np.pi * tt / .03), g, rng.uniform(-.7, .7))
        t += .7 + .5 * rng.random()
def owl(t, g=.06):
    for k, d in ((0, .25), (.45, .55)): n = int(d * SR); tt = np.arange(n) / SR; put(fx, t + k, np.sin(2 * np.pi * 410 * tt) * np.sin(np.pi * tt / d), g, -.5)
def wind(t0, t1, g=.03): d = t1 - t0; n = int(d * SR); tt = np.arange(n) / SR; put(fx, t0, lp(noise(d), 500) * (1 + .4 * np.sin(2 * np.pi * .3 * tt)) * np.minimum(1, np.minimum(tt, d - tt) / .5), g * 3)

E = TL["enc"]
for t in (3.6, 3.9, 8.9): pop(t); chime(t, .04)
for t0, *_ in TL["speech"]: chime(t0, .035, .3)
for b in (8.57, 17.14): whoosh(b - .35, .7, .07)
crackle(8.6, 17.1); fireroar(13.6); chime(13.6, .1)
for i in range(10): bird(.8 + i * 1.6 + rng.random() * .4, .03, rng.uniform(-.6, .6))
for i in range(6): bird(23 + i * .9 + rng.random() * .3, .03, rng.uniform(-.6, .6))
boing(20.6); roll(21.2, 22.86)
for name, nxt in (("hare", 28.57), ("wolf", 34.29), ("bear", 40.0)):
    s = E[name][1]; roll(s - .55, s); pop(s - .5, .12); roll(s + 3.6, nxt)
wind(28.6, 34.3); growl(35.1); wind(34.3, 40.0, .025)
roll(40.0, E["fox"][1]); pop(E["fox"][1] - .2, .1); crickets(40.0, 48.5, .012)
boing(47.6); chomp(AM)
crickets(51.4, 60.0); owl(54.6); owl(57.9)
# superhero-comic stings on every first appearance: brass stab + timpani + cymbal swish
def sting(t, root=50):
    d = .9; n = int(d * SR); tt = np.arange(n) / SR; x = np.zeros(n)
    for m in (root, root + 7, root + 12, root + 16):
        ph = 2 * np.pi * hz(m) * tt; x += ((ph / np.pi) % 2 - 1)
    x = lp(x, 2600) * np.exp(-tt / .28) * np.minimum(1, tt / .012)
    tim = np.sin(2 * np.pi * (70 + 40 * np.exp(-tt * 12)) * tt) * np.exp(-tt / .35)
    cym = bp(noise(d), 5000, 14000) * np.exp(-tt / .45)
    put(fx, t, x * .5 + tim * .9 + cym * .25, .35)
    put(fx, t - .25, bp(noise(.3), 800, 6000) * np.linspace(0, 1, int(.3 * SR)) ** 2, .12)
for (t0, t1, key, *_), r in zip(TL["intros"], (50, 53, 55, 57, 45, 43, 52)): sting(t0, r)

mix = mus + fx
peak = np.abs(mix).max() + 1e-9; mix = mix / peak * .9
fo = int(1.2 * SR); mix[-fo:] *= np.linspace(1, 0, fo)[:, None]
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
with wave.open(os.path.join(HERE, "out", "mix.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
print("mix.wav", round(DUR, 2), "s")
