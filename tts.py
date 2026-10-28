"""Voiceover + timeline. Usage: python3 tts.py <workdir> <models_dir>"""
import json, re, sys
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

wd, md = sys.argv[1], sys.argv[2]
S = json.load(open(f"{wd}/script.json"))
k = Kokoro(f"{md}/kokoro-v1.0.onnx", f"{md}/voices-v1.0.bin")
SR = 24000
VOICE = S.get("voice", "am_michael"); SPEED = float(S.get("speed", 1.0))
LEAD, GAP, SCENE_GAP, TAIL = float(S.get("lead", 0.6)), float(S.get("gap", 0.38)), float(S.get("scene_gap", 0.9)), float(S.get("tail", 1.5))

def chunks(line, maxw=7):
    out, cur = [], []
    for w in line.split():
        cur.append(w)
        if len(cur) >= maxw or (len(cur) >= 4 and re.search(r"[,.;:?!]$", w)):
            out.append(" ".join(cur)); cur = []
    if cur:
        if out and len(cur) <= 2: out[-1] += " " + " ".join(cur)
        else: out.append(" ".join(cur))
    return out

audio = [np.zeros(int(LEAD * SR), np.float32)]; t = LEAD; timeline = []
for sc in S["scenes"]:
    st = t; subs = []; ls = []
    for li, ln in enumerate(sc["lines"]):
        s, sr = k.create(ln, voice=VOICE, speed=SPEED, lang="en-us")
        nz = np.where(np.abs(s) > 0.01)[0]
        if len(nz): s = s[max(0, nz[0] - 600): nz[-1] + 1200]
        dur = len(s) / SR; ls.append(round(t, 3))
        cs = chunks(ln); tot = sum(len(x) for x in cs); ct = t
        for x in cs:
            cd = dur * len(x) / tot; subs.append({"start": round(ct, 3), "end": round(ct + cd, 3), "text": x}); ct += cd
        audio.append(s.astype(np.float32)); t += dur
        g = GAP if li < len(sc["lines"]) - 1 else SCENE_GAP
        audio.append(np.zeros(int(g * SR), np.float32)); t += g
    timeline.append({"id": sc.get("id", f"s{len(timeline)}"), "visual": sc.get("visual", "sketch"), "params": sc.get("params", {}),
                     "heading": sc.get("heading", ""), "start": round(st, 3), "end": round(t, 3),
                     "line_starts": ls, "subs": subs})
audio.append(np.zeros(int(TAIL * SR), np.float32)); t += TAIL
timeline[-1]["end"] = round(t, 3)
sf.write(f"{wd}/voice.wav", np.concatenate(audio), SR)
json.dump({"title": S["title"], "duration": round(t, 3), "scenes": timeline}, open(f"{wd}/timeline.json", "w"), indent=1)
print("voice ok", round(t, 1), "s")
