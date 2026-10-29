"""Sound effects track for POV videos: a soft "whoosh" on every scene change and a "pop" when a tag appears.
Usage: python3 sfx.py <wd>  → <wd>/sfx.wav (same length as the voice). All sounds are synthesized here (no samples)."""
import json, sys, os, numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from povlib import shots
from scipy.signal import butter, sosfilt
wd = sys.argv[1]; SR = 44100
S = json.load(open(f"{wd}/script.json")); TL = json.load(open(f"{wd}/timeline.json"))
D = TL["duration"]; out = np.zeros(int((D + 1) * SR), np.float32); rng = np.random.default_rng(7)

def whoosh(dur=0.42):
    n = int(dur * SR); x = rng.standard_normal(n).astype(np.float32); y = np.zeros(n, np.float32)
    # sweep a band-pass filter up then down in small blocks
    blocks = 24; L = n // blocks
    for b in range(blocks):
        u = b / (blocks - 1); f = 300 + 3200 * np.sin(np.pi * u) ** 1.5
        sos = butter(2, [max(80, f * 0.6), min(SR / 2 - 100, f * 1.6)], "bandpass", fs=SR, output="sos")
        y[b * L:(b + 1) * L] = sosfilt(sos, x[b * L:(b + 1) * L])
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    return y * env / (np.abs(y).max() + 1e-6)

def pop(dur=0.09):
    t = np.arange(int(dur * SR)) / SR; f = 900 * np.exp(-t * 25) + 300
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 45)).astype(np.float32)

def add(sig, at, gain):
    i = int(max(0, at) * SR); j = min(len(out), i + len(sig)); out[i:j] += sig[:j - i] * gain

W = whoosh(); P = pop()
for k, s in enumerate(TL["scenes"]):
    if k: add(W, s["start"] - 0.3, 0.55)
    for x in shots(s, bool(S.get("vertical")))[1:]: add(W, x - 0.2, 0.32)      # quieter whoosh on in-scene cuts
    if S["scenes"][k].get("tag"): add(P, s["start"] + 0.25, 0.6)
sf.write(f"{wd}/sfx.wav", out[:int(D * SR)], SR); print("sfx ok", len(TL["scenes"]), "scenes")
