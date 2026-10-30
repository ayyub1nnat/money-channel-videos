"""Shared shot timing for pov.py and sfx.py: long scenes are split into shots of ~SHOT seconds
(odd shots are a punch-in on part of the same illustration), so the picture changes every few seconds."""
import random
def shots(s, vertical):
    SHOT = 4.0 if vertical else 6.0   # calmer cuts (owner 2026-10-30)
    d = s["end"] - s["start"]; n = max(1, round(d / SHOT))
    return [s["start"] + d * j / n for j in range(n)]          # shot start times
def shot_params(i, j):
    r = random.Random(i * 101 + j * 7 + 3)
    if j % 2 == 0: return {"punch": False, "mode": r.choice(["in", "out", "left", "right"]) if (i or j) else "in"}
    return {"punch": True, "z": r.uniform(1.28, 1.42), "fx": r.uniform(0.35, 0.65), "fy": r.uniform(0.35, 0.55)}
