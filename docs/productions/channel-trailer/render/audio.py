"""Soundtrack for the trailer: music bed (plucks + soft beat) and SFX synced to render.py events."""
import sys, numpy as np
from scipy.signal import lfilter, butter
SR = 44100; DUR = 60.5; N = int(SR * DUR)
rng = np.random.default_rng(7)
mus = np.zeros(N); fx = np.zeros(N)

def put(buf, t, x, g=1.0):
    i = int(t * SR); j = min(N, i + len(x))
    if j > i: buf[i:j] += x[:j - i] * g
def env(n, a=.005, r=None):
    e = np.ones(n); ai = max(1, int(a * SR)); e[:ai] = np.linspace(0, 1, ai)
    if r: e *= np.exp(-np.arange(n) / (r * SR))
    return e
def bp(x, lo, hi, o=2):
    b, a = butter(o, [lo / (SR / 2), hi / (SR / 2)], "band"); return lfilter(b, a, x)
def lp(x, f, o=2):
    b, a = butter(o, f / (SR / 2)); return lfilter(b, a, x)
def hz(m): return 440 * 2 ** ((m - 69) / 12)

_ks = {}
def pluck(m, dur=1.6, bright=.5):
    key = (m, dur)
    if key in _ks: return _ks[key]
    f = hz(m); P = int(SR / f); n = int(dur * SR); y = np.zeros(n)
    buf = rng.uniform(-1, 1, P); buf = lp(buf, 2000 + 4000 * bright) if P > 20 else buf
    pos = 0
    while pos < n:
        k = min(P, n - pos); y[pos:pos + k] = buf[:k]
        buf = .996 * .5 * (buf + np.roll(buf, -1)); pos += P
    y *= env(n, .002); _ks[key] = y; return y

def sq(f, dur, duty=.5):
    t = np.arange(int(dur * SR)) / SR; return np.where((t * f) % 1 < duty, 1.0, -1.0)

# ------------------------------------------------ music: Am F C G, 100 BPM
BPM = 100; beat = 60 / BPM; bar = 4 * beat
chords = [[57, 60, 64, 69], [53, 57, 60, 65], [55, 60, 64, 67], [55, 59, 62, 67]]
lead = [76, 74, 72, 74, 76, 79, 76, 74, 72, 69, 72, 74, 76, 72, 69, 67]
t = 0.0; b = 0
while t < 58.4:
    ch = chords[b % 4]; calm = t >= 45.0
    pattern = [(0, 1, .9), (1.5, -1, .45), (2, 1, .7), (3, 1, .5), (3.5, -1, .35)] if not calm else [(0, 1, .55), (2, 1, .35)]
    for off, d, g in pattern:
        st = t + off * beat; notes = ch if d > 0 else ch[::-1]
        for i, m in enumerate(notes): put(mus, st + i * .012, pluck(m + 12, 1.4 if not calm else 2.4, .4), g * .12)
    # bass
    put(mus, t, np.sin(2 * np.pi * hz(ch[0] - 12) * np.arange(int(bar * SR)) / SR) * env(int(bar * SR), .01, .9), .22 if not calm else .14)
    if 1.5 < t < 45.0:                       # soft lo-fi beat
        for k in range(4):
            kt = t + k * beat; n = int(.18 * SR); tt = np.arange(n) / SR
            if k in (0, 2): put(mus, kt, np.sin(2 * np.pi * (50 + 90 * np.exp(-tt * 30)) * tt) * env(n, .001, .07), .55)
            if k in (1, 3): put(mus, kt, bp(rng.uniform(-1, 1, n), 1500, 6000) * env(n, .001, .05), .22)
            for h in (0, .5): put(mus, kt + h * beat, bp(rng.uniform(-1, 1, int(.04 * SR)), 7000, 15000) * env(int(.04 * SR), .001, .01), .12)
    if 15 <= t < 30:                          # 8-bit lead in the adventure section
        for i in range(8):
            m = lead[(b * 8 + i) % 16]; n = int(beat / 2 * SR * .9)
            put(mus, t + i * beat / 2, lp(sq(hz(m), beat / 2 * .9, .25), 3500) * env(n, .003, .15), .05)
    if 30 <= t < 45:                          # bell lead in the discoveries section
        for i in range(4):
            m = lead[(b * 4 + i) % 16]; n = int(beat * SR); tt = np.arange(n) / SR
            put(mus, t + i * beat, (np.sin(2 * np.pi * hz(m) * tt) + .3 * np.sin(2 * np.pi * hz(m) * 2.76 * tt)) * env(n, .002, .25), .07)
    t += bar; b += 1
# final chord
for i, m in enumerate([57, 60, 64, 69, 72]): put(mus, 58.4 + i * .03, pluck(m + 12, 2.0, .5), .16)

# ------------------------------------------------ sfx
def noise(d): return rng.uniform(-1, 1, int(d * SR))
def scratch(t0, t1, g=.10):
    n = int((t1 - t0) * SR); x = bp(noise(t1 - t0), 2500, 9000); tt = np.arange(n) / SR
    am = np.clip(np.sin(2 * np.pi * 5.5 * tt + np.sin(tt * 3)) * .7 + .4, 0, 1) * (.7 + .3 * rng.random(n))
    put(fx, t0, x * am * env(n, .02), g)
def pop(t, g=.35, f0=900):
    n = int(.12 * SR); tt = np.arange(n) / SR
    put(fx, t, np.sin(2 * np.pi * (f0 * np.exp(-tt * 18) + 180) * tt) * env(n, .001, .04), g)
def tick(t, g=.25): n = int(.03 * SR); put(fx, t, bp(noise(.03), 2000, 8000) * env(n, .0005, .006), g)
def yip(t, g=.18):
    n = int(.16 * SR); tt = np.arange(n) / SR; f = 1000 + 700 * np.sin(np.pi * tt / .16)
    put(fx, t, np.tanh(3 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * env(n, .005, .07), g)
def whoosh(t, d=.7, g=.32, up=True):
    n = int(d * SR); x = noise(d); out = np.zeros(n); seg_ = 2048
    for i in range(0, n, seg_):
        k = i / n; fc = (300 + 5000 * (k if up else 1 - k)); out[i:i + seg_] = lp(x[i:i + seg_], max(200, fc))[:len(out[i:i + seg_])]
    put(fx, t, out * np.sin(np.pi * np.arange(n) / n) ** 1.5, g)
def hit(t, g=.5):
    n = int(.35 * SR); tt = np.arange(n) / SR
    put(fx, t, (np.sin(2 * np.pi * (45 + 120 * np.exp(-tt * 25)) * tt) + .3 * bp(noise(.35), 200, 3000)) * env(n, .001, .12), g)
def boing(t, g=.22):
    n = int(.45 * SR); tt = np.arange(n) / SR; f = 220 + 160 * tt / .45 + 30 * np.sin(2 * np.pi * 14 * tt)
    put(fx, t, np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .003, .2), g)
def step(t, g=.10): n = int(.07 * SR); put(fx, t, bp(noise(.07), 300, 2500) * env(n, .001, .02), g)
def blip(t, g=.13):
    for i, (f, d) in enumerate(((880, .07), (1175, .2))):
        n = int(d * SR); put(fx, t + i * .07, sq(f, d) * env(n, .001, .08), g)
def jingle(t, g=.10):
    for i, m in enumerate((84, 88, 91, 96, 100)):
        n = int(.06 * SR); put(fx, t + i * .05, sq(hz(m), .06) * env(n, .001, .04), g)
def chime(t, m, g=.22):
    n = int(1.2 * SR); tt = np.arange(n) / SR
    put(fx, t, (np.sin(2 * np.pi * hz(m) * tt) + .4 * np.sin(2 * np.pi * hz(m) * 3.01 * tt)) * env(n, .002, .4), g)
def rumble(t0, d, g=.35):
    n = int(d * SR); put(fx, t0, lp(noise(d), 160) * 3 * np.sin(np.pi * np.arange(n) / n), g)
def crickets(t0, t1, g=.035):
    t = t0
    while t < t1:
        for k in range(3):
            n = int(.03 * SR); tt = np.arange(n) / SR; put(fx, t + k * .055, np.sin(2 * np.pi * 4600 * tt) * np.sin(np.pi * tt / .03), g)
        t += .9 + .5 * rng.random()
def yawn(t, g=.12):
    n = int(.6 * SR); tt = np.arange(n) / SR; f = 700 - 320 * tt / .6
    put(fx, t, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / .6), g)
def glitch(t, g=.12):
    for i in range(10): n = int(.04 * SR); put(fx, t + i * .04, sq(hz(60 + int(rng.integers(0, 36))), .04) * env(n, .001, .03), g)

# clip 1
tick(.25); tick(.75); scratch(1.0, 3.5); pop(3.6, .45); hit(3.6, .25)
scratch(5.9, 8.5); pop(8.6, .4); whoosh(9.25, .35, .12); yip(9.9)
whoosh(10.2, .4, .3); hit(10.55, .55); yip(11.1); yip(12.6)
# transition 15
whoosh(14.55, .9, .4); [pop(14.65 + i * .06, .18, 700 + 120 * i) for i in range(6)]
# clip 2
scratch(15.4, 18.8); jingle(18.9, .07)
for i in range(6): step(19.5 + i * .18, .06)
boing(20.6); [step(21.05 + i * .3) for i in range(5)]; boing(22.5)
pop(23.0, .2, 400); rumble(23.6, 1.6); whoosh(23.7, 1.3, .4); hit(24.6, .3)
glitch(24.6); whoosh(24.6, .8, .25, up=False)
for tc in (26.0, 27.3, 28.6): blip(tc); jingle(tc + .12, .05)
whoosh(29.7, .6, .3)
# clip 3
for i in range(6): whoosh(30.45 + i * .7, .6, .10)
for i in range(3): scratch(35.2 + i * 1.4, 36.1 + i * 1.4, .07); pop(36.2 + i * 1.4, .3, 600 + i * 150)
chime(40.0, 79); chime(41.5, 83); chime(43.0, 86, .28); jingle(43.0, .1); hit(43.0, .35)
# transition 45
whoosh(44.55, .9, .4); [pop(44.65 + i * .06, .16, 600 + 100 * i) for i in range(6)]
# clip 4
scratch(45.5, 48.0, .08); crickets(47.0, 60.0); yawn(50.0); whoosh(52.7, 1.2, .08); scratch(52.7, 54.0, .06)
for i in range(4): step(57.65 + i * .27, .07)
# sticker pops (render.POPS)
for t0 in (3.75, 9.3, 9.5, 11.6, 11.8, 17.6, 21.0, 24.0, 26.0, 31.2, 34.0, 43.0, 46.2, 47.0, 52.0, 52.4, 55.0):
    pop(t0, .16, 1300)

mix = mus * .9 + fx
mix = np.tanh(mix * 1.4) / np.tanh(1.4)
fade = np.ones(N); fn = int(1.2 * SR); fade[-fn:] = np.linspace(1, 0, fn); mix *= fade
mix = mix / (np.abs(mix).max() + 1e-9) * .89
st = np.stack([mix, np.roll(mix, 9) * .98], 1)
import wave
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())
print("ok")
