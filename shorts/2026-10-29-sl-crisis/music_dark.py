"""Original documentary underscore: mysterious, tense but not horror. D minor, ~72 BPM.
Low drone pad + soft heartbeat pulse + ticking clock + sparse reverbed piano notes + gentle risers at scene changes.
Usage: python3 music_dark.py <dur> <out.wav> [timeline.json]"""
import sys, json, numpy as np, soundfile as sf
SR = 44100; DUR = float(sys.argv[1]); OUT = sys.argv[2]
N = int(DUR * SR); t = np.arange(N) / SR
rng = np.random.default_rng(7)
L = np.zeros(N); R = np.zeros(N)
def mtof(m): return 440 * 2 ** ((m - 69) / 12)
def lp(x, a):  # one-pole lowpass (vectorised via filtfilt-free recursion in blocks)
    from scipy.signal import lfilter
    return lfilter([a], [1, a - 1], x)
# 1) drone pad: D2 + A2 + F3 (minor), detuned saw-ish, slow filter swell, chord moves Dm -> Bb -> Gm -> A every 8 s
prog = [(38, 45, 53), (34, 41, 50), (31, 38, 46), (33, 40, 49)]
pad = np.zeros(N)
for k in range(int(DUR // 8) + 1):
    a0, a1 = int(k * 8 * SR), min(N, int((k * 8 + 8.6) * SR))
    if a0 >= N: break
    tt = np.arange(a1 - a0) / SR; seg = np.zeros(a1 - a0)
    for m in prog[k % 4]:
        for det in (-0.12, 0.0, 0.11):
            f = mtof(m + det); ph = (f * tt) % 1
            seg += (2 * ph - 1) * 0.5 + np.sin(2 * np.pi * f * tt) * 0.6
    e = np.minimum(1, tt / 1.2) * np.minimum(1, (tt[-1] - tt + 1e-3) / 0.8)
    pad[a0:a1] += seg * e
pad = lp(pad, 0.035) * (0.75 + 0.25 * np.sin(2 * np.pi * t / 9))
pad /= np.abs(pad).max() + 1e-9
L += pad * 0.42; R += pad * 0.42
# sub drone
sub = np.sin(2 * np.pi * mtof(26) * t) * 0.22 * (0.8 + 0.2 * np.sin(2 * np.pi * t / 5)); L += sub; R += sub
# 2) heartbeat pulse (soft low thump, lub-dub) every 2 beats at 72 BPM
beat = 60 / 72
def thump(at, g):
    n = int(0.35 * SR); tt = np.arange(n) / SR
    x = np.sin(2 * np.pi * (70 * np.exp(-tt * 9) + 38) * tt) * np.exp(-tt * 13) * g
    i = int(at * SR); j = min(N, i + n)
    if i < N: L[i:j] += x[: j - i]; R[i:j] += x[: j - i]
bt = 1.0
while bt < DUR - 1:
    thump(bt, 0.55); thump(bt + 0.24, 0.32); bt += 2 * beat
# 3) clock tick (very quiet, high, alternating pan)
k = 0; tk = 0.5
while tk < DUR - 0.5:
    n = int(0.02 * SR); x = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 400)
    x = np.diff(np.concatenate([[0], x])) * 0.06; i = int(tk * SR)
    (L if k % 2 else R)[i:i + n] += x[: max(0, min(n, N - i))]
    k += 1; tk += beat
# 4) sparse piano-like notes (D minor), with simple echo/reverb
notes = [74, 77, 81, 76, 74, 72, 77, 69]
pn = np.zeros(N)
for idx, at in enumerate(np.arange(2.0, DUR - 2, beat * 4)):
    m = notes[idx % len(notes)]; n = int(2.5 * SR); tt = np.arange(n) / SR
    f = mtof(m); x = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) + 0.12 * np.sin(6 * np.pi * f * tt)) * np.exp(-tt * 2.2)
    x *= np.minimum(1, tt / 0.005) * 0.16; i = int(at * SR); j = min(N, i + n); pn[i:j] += x[: j - i]
for d, g in ((0.37, 0.45), (0.74, 0.25), (1.11, 0.14)):
    s = int(d * SR); pn[s:] += pn[:-s] * g
L += pn * 0.9; R += np.roll(pn, int(0.012 * SR)) * 0.9
# 5) gentle risers (filtered noise swell) into scene changes
if len(sys.argv) > 3:
    tl = json.load(open(sys.argv[3]))
    for s in tl["scenes"][1:]:
        at = s["start"]; n = int(1.2 * SR); i = int((at - 1.2) * SR)
        if i < 0: continue
        x = lp(rng.standard_normal(n), 0.08) * np.linspace(0, 1, n) ** 2 * 0.25
        j = min(N, i + n); L[i:j] += x[: j - i]; R[i:j] += x[: j - i]
fade = np.minimum(1, np.minimum(t / 0.8, (DUR - t) / 1.5))
mix = np.stack([L * fade, R * fade], 1); mix /= np.abs(mix).max() + 1e-9
sf.write(OUT, (mix * 0.9).astype(np.float32), SR); print("music ok", OUT)
