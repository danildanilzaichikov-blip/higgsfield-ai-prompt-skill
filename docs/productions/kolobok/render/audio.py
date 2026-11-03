"""Fairy-tale score for «Колобок»: harp arpeggios, music-box melody, soft strings; SFX on the beats."""
import sys, wave, numpy as np
from scipy.signal import lfilter, butter
SR = 44100; DUR = 60.0; N = int(SR * DUR); rng = np.random.default_rng(3)
mus = np.zeros(N); fx = np.zeros(N)
def put(b, t, x, g=1.):
    i = int(t * SR); j = min(N, i + len(x))
    if j > i and i >= 0: b[i:j] += x[:j - i] * g
def env(n, a=.005, r=None):
    e = np.ones(n); ai = max(1, int(a * SR)); e[:ai] = np.linspace(0, 1, ai)
    if r: e *= np.exp(-np.arange(n) / (r * SR))
    return e
def lp(x, f): b, a = butter(2, f / (SR / 2)); return lfilter(b, a, x)
def bp(x, lo, hi): b, a = butter(2, [lo / (SR / 2), hi / (SR / 2)], "band"); return lfilter(b, a, x)
def hz(m): return 440 * 2 ** ((m - 69) / 12)
_c = {}
def harp(m, d=2.4):
    if (m, d) in _c: return _c[(m, d)]
    P = int(SR / hz(m)); n = int(d * SR); y = np.zeros(n); buf = lp(rng.uniform(-1, 1, P), 3000) if P > 20 else rng.uniform(-1, 1, P); pos = 0
    while pos < n: k = min(P, n - pos); y[pos:pos + k] = buf[:k]; buf = .997 * .5 * (buf + np.roll(buf, -1)); pos += P
    y *= env(n, .002); _c[(m, d)] = y; return y
def bell(m, d=1.6):
    t = np.arange(int(d * SR)) / SR; f = hz(m)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 2.2) + .5 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t * 5) + .25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 9)) * env(len(t), .002)
def pad(ms, d, g=1.):
    t = np.arange(int(d * SR)) / SR; x = np.zeros(len(t))
    for m in ms:
        for det in (-.12, .12): ph = 2 * np.pi * hz(m) * (1 + det / 100) * t; x += ((ph / np.pi) % 2 - 1)
    x = lp(x, 1400); e = np.minimum(1, t / .6) * np.minimum(1, (d - t) / .6); return x * e * g / len(ms)

BPM = 84; beat = 60 / BPM; bar = 4 * beat
# section map (start time, chord list per bar, mode)
prog_a = [[50, 53, 57], [46, 50, 53], [53, 57, 60], [45, 49, 52]]        # Dm Bb F A
prog_fox = [[43, 46, 50], [45, 49, 52]]                                  # Gm A (sly)
melody = [74, 77, 76, 74, 72, 69, 70, 72, 74, 72, 70, 69, 67, 69, 64, 69]   # D minor tune, 2 bars per line
t = 0.6; b = 0
while t < 57.5:
    fox = 41.5 <= t < 49.0
    ch = (prog_fox if fox else prog_a)[b % (2 if fox else 4)]
    put(mus, t, pad([m + 12 for m in ch], bar + .6, .5 if t < 53 else .7), .10)
    arp = ch + [c + 12 for c in ch] + [ch[1] + 24]
    order = [0, 1, 2, 3, 4, 5, 6, 5] if not fox else [0, 2, 4, 6, 4, 2, 0, 2]
    for i, k in enumerate(order):
        put(mus, t + i * beat / 2, harp(arp[k] + 12), .16 if not fox else .12)
    if 7 < t < 41.5:   # light pizzicato bass on the road
        for k in (0, 2): put(mus, t + k * beat, harp(ch[0] - 12, .5) * env(int(.5 * SR), .002, .12), .35)
    if not fox and t < 53:
        for i in range(4):
            m = melody[(b * 4 + i) % 16]; put(mus, t + i * beat + (beat / 2 if i == 3 and b % 2 else 0), bell(m), .09)
    t += bar; b += 1
# ending: warm D major chord and music-box run
for i, m in enumerate([62, 66, 69, 74, 78, 81]): put(mus, 57.5 + i * .09, bell(m, 2.4), .08)
put(mus, 57.5, pad([62, 66, 69, 74], 2.5, .8), .12)

def noise(d): return rng.uniform(-1, 1, int(d * SR))
def chime(t, g=.10):
    for i, m in enumerate((88, 91, 95, 98, 100, 103)): put(fx, t + i * .045, bell(m, .6), g)
def whoosh(t, d=1.1, g=.12):
    n = int(d * SR); x = bp(noise(d), 600, 4000); put(fx, t, x * np.sin(np.pi * np.arange(n) / n) ** 2, g)
def roll(t, d, g=.10):
    n = int(d * SR); tt = np.arange(n) / SR; x = lp(noise(d), 400) * (1 + .5 * np.sin(2 * np.pi * 7 * tt)); put(fx, t, x * np.sin(np.pi * tt / d), g * 3)
def boing(t, g=.12):
    n = int(.4 * SR); tt = np.arange(n) / SR; f = 300 + 300 * tt / .4; put(fx, t, np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .003, .15), g)
def crackle(t0, t1, g=.05):
    t = t0
    while t < t1: n = int(.02 * SR); put(fx, t, bp(noise(.02), 1500, 6000) * env(n, .001, .005), g * (.5 + rng.random())); t += .05 + .2 * rng.random()
def bird(t, g=.05):
    n = int(.18 * SR); tt = np.arange(n) / SR; f = 2800 + 900 * np.sin(2 * np.pi * 9 * tt); put(fx, t, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / .18), g)
def growl(t, g=.18):
    n = int(.9 * SR); tt = np.arange(n) / SR; x = np.sin(2 * np.pi * (70 + 8 * np.sin(2 * np.pi * 23 * tt)) * tt) + .4 * lp(noise(.9), 300); put(fx, t, x * np.sin(np.pi * tt / .9), g)
def chomp(t):
    n = int(.25 * SR); tt = np.arange(n) / SR; put(fx, t, (np.sin(2 * np.pi * 90 * tt) + .6 * bp(noise(.25), 200, 2000)) * env(n, .001, .07), .45)
def owl(t, g=.06):
    for k, d in ((0, .25), (.45, .5)): n = int(d * SR); tt = np.arange(n) / SR; put(fx, t + k, np.sin(2 * np.pi * 420 * tt) * np.sin(np.pi * tt / d), g)

for tb in (7.5, 15.0, 21.5, 28.0, 34.5, 41.0, 53.0): whoosh(tb - .55); chime(tb - .1, .05)
chime(.4, .08)
for tp in (2.4, 2.8, 8.0, 12.3, 15.5, 22.8, 29.3, 35.8, 42.4): chime(tp, .06)
crackle(7.8, 14.8); chime(12.3, .1)
boing(18.8); roll(21.8, 1.3); roll(26.6, 1.2); roll(28.3, 1.3); roll(33.0, 1.2); roll(34.8, 1.3); roll(39.5, 1.2); roll(41.3, 1.3)
for i in range(6): bird(22 + i * .9 + rng.random() * .3)
growl(36.3); boing(47.3); chomp(48.95); owl(54.5); owl(57.2)
mix = mus + fx; mix = np.tanh(mix * 1.6) / np.tanh(1.6)
fi = int(.6 * SR); mix[:fi] *= np.linspace(0, 1, fi); fo = int(1.4 * SR); mix[-fo:] *= np.linspace(1, 0, fo)
mix = mix / (np.abs(mix).max() + 1e-9) * .89
st = np.stack([mix, np.roll(mix, 11) * .97], 1)
with wave.open(sys.argv[1], "wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())
print("ok")
