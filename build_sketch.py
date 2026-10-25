"""Build a whiteboard-style video (script.json "style": "sketch"), horizontal (main video) or vertical (Short).
Usage: python3 build_sketch.py <workdir> [--preview]
Steps: voice + timeline (tts.py) → preview grid → pencil sound → frames (sketch.py, 2 in parallel) →
mix (voice + pencil + ducked music) → video.mp4 (or short.mp4 if "vertical": true) + subtitles.srt + chapters.txt
(+ thumbnail via thumb.py for horizontal videos)."""
import json, os, subprocess, sys, math, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
wd = os.path.abspath(sys.argv[1]); preview = "--preview" in sys.argv
def run(cmd): print("+", " ".join(cmd)[:200], flush=True); subprocess.run(cmd, check=True)

S = json.load(open(f"{wd}/script.json")); V = bool(S.get("vertical"))
if not os.path.exists(f"{wd}/timeline.json") or os.path.getmtime(f"{wd}/timeline.json") < os.path.getmtime(f"{wd}/script.json"):
    run(["python3", f"{HERE}/tts.py", wd, os.environ.get("MODELS_DIR", os.path.join(HERE, "models"))])
TL = json.load(open(f"{wd}/timeline.json")); D = TL["duration"]

# preview grid (one still per scene, max 24)
os.makedirs(f"{wd}/prev", exist_ok=True)
scs = TL["scenes"]; step = max(1, math.ceil(len(scs) / 24)); idx = list(range(0, len(scs), step))
tw, th = (240, 427) if V else (480, 270); cols = 6 if V else 4
for i in idx:
    s = scs[i]
    subprocess.run(["python3", f"{HERE}/sketch.py", wd, str(s["start"] + (s["end"] - s["start"]) * 0.85), "0", f"{wd}/prev/s{i:03d}.png"],
                   stderr=subprocess.DEVNULL, check=True)
from PIL import Image
rows = math.ceil(len(idx) / cols); g = Image.new("RGB", (tw * cols, th * rows), "white")
for k, i in enumerate(idx):
    g.paste(Image.open(f"{wd}/prev/s{i:03d}.png").convert("RGB").resize((tw, th)), ((k % cols) * tw, (k // cols) * th))
g.save(f"{wd}/preview_grid.jpg", quality=80); print("preview:", f"{wd}/preview_grid.jpg")
if preview: sys.exit(0)

seed = str(int(hashlib.md5(S["title"].encode()).hexdigest()[:8], 16))
if not os.path.exists(f"{wd}/music.wav"):
    run(["python3", f"{HERE}/music.py", str(D + 2), f"{wd}/music.wav", seed] + (["energetic"] if V else []))
run(["python3", f"{HERE}/sketch.py", wd, "--pencil"])
half = round(D / 2 * 24) / 24
p1 = subprocess.Popen(["python3", f"{HERE}/sketch.py", wd, "0", str(half), f"{wd}/part1.mp4"], stderr=subprocess.DEVNULL)
p2 = subprocess.Popen(["python3", f"{HERE}/sketch.py", wd, str(half), str(D), f"{wd}/part2.mp4"], stderr=subprocess.DEVNULL)
assert p1.wait() == 0 and p2.wait() == 0, "render failed"
mv = float(S.get("music_volume", 0.34 if V else 0.30)); pv = float(S.get("pencil_volume", 0.16)); lufs = -13 if V else -14
run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{wd}/voice.wav", "-stream_loop", "-1", "-i", f"{wd}/music.wav", "-i", f"{wd}/pencil.wav",
     "-filter_complex",
     f"[0:a]aresample=44100,pan=stereo|c0=c0|c1=c0,asplit=2[v][vsc];[1:a]aresample=44100,volume={mv}[m];"
     "[m][vsc]sidechaincompress=threshold=0.02:ratio=9:attack=15:release=400:makeup=1[md];"
     f"[2:a]aresample=44100,pan=stereo|c0=c0|c1=c0,volume={pv}[pc];"
     f"[v][md][pc]amix=inputs=3:duration=first:normalize=0,afade=t=out:st={max(0, D - 2)}:d=2,loudnorm=I={lufs}:TP=-1.5:LRA=11[a]",
     "-map", "[a]", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", f"{wd}/mix.m4a"])
open(f"{wd}/list.txt", "w").write(f"file '{wd}/part1.mp4'\nfile '{wd}/part2.mp4'\n")
out = f"{wd}/{'short' if V else 'video'}.mp4"
run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{wd}/list.txt", "-i", f"{wd}/mix.m4a",
     "-map", "0:v", "-map", "1:a", "-c", "copy", "-shortest", "-movflags", "+faststart", out])

# subtitles
def ts(t):
    ms = int(round(t * 1000)); return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"
srt, n = [], 1
for s in scs:
    for x in s["subs"]:
        srt.append(f"{n}\n{ts(x['start'])} --> {ts(x['end'] + 0.1)}\n{x['text']}\n"); n += 1
open(f"{wd}/subtitles.srt", "w").write("\n".join(srt))
# chapters: scenes that carry "chapter" (fallback: every heading), first at 0:00, ≥ 10 s apart
spec = S["scenes"]; marks = [(0 if i == 0 else int(s["start"]), (spec[i].get("chapter") or "")) for i, s in enumerate(scs)]
if not any(c for _, c in marks): marks = [(0 if i == 0 else int(s["start"]), s.get("heading", "")) for i, s in enumerate(scs)]
ch, last = [], -99
for t, c in marks:
    if c and (t - last >= 10 or not ch):
        ch.append(f"{t//60}:{t%60:02d} {c}"); last = t
if ch: ch[0] = "0:00 " + ch[0].split(" ", 1)[1]
open(f"{wd}/chapters.txt", "w").write("\n".join(ch) + "\n")
if not V and S.get("thumbnail"):
    run(["python3", f"{HERE}/thumb.py", wd])
print(f"DONE sketch {os.path.basename(out)} {D:.1f}s | chapters:\n" + "\n".join(ch))
