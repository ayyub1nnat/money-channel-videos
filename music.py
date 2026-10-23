"""Original royalty-free background track: uplifting electronic / lo-fi pop, 112 BPM."""
import numpy as np, soundfile as sf, sys

import random
SR = 44100
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 262
OUT = sys.argv[2] if len(sys.argv) > 2 else "music.wav"
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 1
R = random.Random(SEED)
BPM = R.choice([100, 104, 108, 112, 116, 120])
beat = 60 / BPM
N = int(DUR * SR)
out = np.zeros((N, 2), np.float32)
rng = np.random.default_rng(1)

def mtof(m): return 440 * 2 ** ((m - 69) / 12)

def env(n, a=0.01, d=0.2, s=0.6, r=0.3, hold=None):
    t = np.arange(n) / SR
    hold = hold if hold is not None else n / SR - r
    e = np.where(t < a, t / a, np.where(t < a + d, 1 - (1 - s) * (t - a) / d, s))
    rel = np.clip(1 - (t - hold) / r, 0, 1)
    return e * np.where(t > hold, rel, 1)

def add(sig, start, gain=1.0, pan=0.0):
    i = int(start * SR)
    if i >= N: return
    sig = sig[: N - i]
    l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    out[i:i + len(sig), 0] += sig * gain * l
    out[i:i + len(sig), 1] += sig * gain * r

def saw(f, n, detune=0.0):
    t = np.arange(n) / SR
    s = 0
    for dt in (-detune, 0, detune):
        ph = (t * f * (1 + dt)) % 1
        s = s + (2 * ph - 1)
    return s / 3

def lowpass(x, cut):
    a = np.exp(-2 * np.pi * cut / SR)
    y = np.empty_like(x); acc = 0.0
    # vectorised one-pole via lfilter-like loop in chunks
    from scipy.signal import lfilter
    return lfilter([1 - a], [1, -a], x)

# progression vi-IV-I-V in C  (Am F C G), each 2 bars
PROGS = [([[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]], [45, 41, 48, 43]),   # Am F C G
         ([[48, 52, 55], [55, 59, 62], [57, 60, 64], [53, 57, 60]], [48, 43, 45, 41]),   # C G Am F
         ([[53, 57, 60], [55, 59, 62], [52, 55, 59], [57, 60, 64]], [41, 43, 40, 45]),   # F G Em Am
         ([[50, 53, 57], [55, 59, 62], [48, 52, 55], [57, 60, 64]], [38, 43, 48, 45]),   # Dm G C Am
         ([[48, 52, 55], [57, 60, 64], [53, 57, 60], [55, 59, 62]], [48, 45, 41, 43])]   # C Am F G
chords, bass = R.choice(PROGS)
TR = R.choice([-2, -1, 0, 0, 1, 2])
chords = [[m + TR for m in ch] for ch in chords]; bass = [b + TR for b in bass]
bar = 4 * beat
prog_len = 8 * bar
sections = int(DUR / prog_len) + 1

for s in range(sections):
    base = s * prog_len
    intro = s == 0
    for ci, ch in enumerate(chords):
        t0 = base + ci * 2 * bar
        n = int(2 * bar * SR)
        # warm pad
        pad = sum(saw(mtof(m), n, 0.004) for m in ch) / 3
        pad = lowpass(pad, 900) * env(n, 0.4, 0.5, 0.8, 0.6)
        add(pad.astype(np.float32), t0, 0.22, -0.2)
        add(pad.astype(np.float32), t0, 0.22, 0.2)
        # bass
        if not intro:
            for b in range(8):
                nb = int(beat * 0.9 * SR)
                f = mtof(bass[ci])
                tt = np.arange(nb) / SR
                bs = np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)
                add((bs * env(nb, 0.005, 0.15, 0.7, 0.08)).astype(np.float32), t0 + b * beat, 0.30)
        # pluck arpeggio (16ths)
        arp = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[1] + 12, ch[0] + 24, ch[2] + 12, ch[1] + 12, ch[2] + 12]
        for k in range(32):
            m = arp[k % 8]
            nn = int(beat / 4 * 1.6 * SR)
            tt = np.arange(nn) / SR
            pl = (np.sign(np.sin(2 * np.pi * mtof(m) * tt)) * 0.3 + np.sin(2 * np.pi * mtof(m) * tt)) * np.exp(-tt * 14)
            pl = lowpass(pl, 2600)
            add(pl.astype(np.float32), t0 + k * beat / 4, 0.09 if not intro else 0.06, 0.35 if k % 2 else -0.35)
        # drums
        if not intro:
            for b in range(8):
                tb = t0 + b * beat
                nk = int(0.25 * SR); tt = np.arange(nk) / SR
                kick = np.sin(2 * np.pi * (45 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9)
                add(kick.astype(np.float32), tb, 0.55)
                if b % 2 == 1:
                    ns = int(0.18 * SR); tt = np.arange(ns) / SR
                    clap = rng.standard_normal(ns) * np.exp(-tt * 22)
                    clap = clap - lowpass(clap, 1200)
                    add(clap.astype(np.float32), tb, 0.16)
                for h in (0.5,):
                    nh = int(0.05 * SR); tt = np.arange(nh) / SR
                    hat = rng.standard_normal(nh) * np.exp(-tt * 80)
                    hat = hat - lowpass(hat, 6000)
                    add(hat.astype(np.float32), tb + h * beat, 0.10, 0.3)

# fades + normalise
fi, fo = int(2 * SR), int(4 * SR)
out[:fi] *= np.linspace(0, 1, fi)[:, None]
out[-fo:] *= np.linspace(1, 0, fo)[:, None]
out /= np.max(np.abs(out)) + 1e-9
out *= 0.9
sf.write(OUT, out, SR)
print("ok", DUR)
