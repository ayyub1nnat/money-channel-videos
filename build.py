"""One-command video build.
Usage: python3 build.py <workdir> [--preview]
<workdir>/script.json must exist (see RUNBOOK.md). Produces in <workdir>:
  video.mp4, thumbnail.png (+ thumbnail.jpg <2MB), subtitles.srt, preview_grid.jpg
--preview renders only stills (preview_grid.jpg) for a quick layout check."""
import json, os, subprocess, sys, hashlib, math
HERE = os.path.dirname(os.path.abspath(__file__))
wd = os.path.abspath(sys.argv[1]); preview = "--preview" in sys.argv
MD = os.environ.get("MODELS_DIR", os.path.join(HERE, "models"))
def run(cmd, **kw):
    print("+", " ".join(cmd) if isinstance(cmd, list) else cmd, flush=True)
    subprocess.run(cmd, check=True, **kw)

S = json.load(open(f"{wd}/script.json"))
if not os.path.exists(f"{wd}/timeline.json") or os.path.getmtime(f"{wd}/timeline.json") < os.path.getmtime(f"{wd}/script.json"):
    run(["python3", f"{HERE}/tts.py", wd, MD])
TL = json.load(open(f"{wd}/timeline.json")); D = TL["duration"]

# preview stills (always) -------------------------------------------------
os.makedirs(f"{wd}/prev", exist_ok=True)
procs = []
for i, s in enumerate(TL["scenes"]):
    t = s["start"] + (s["end"] - s["start"]) * 0.8
    procs.append(subprocess.Popen(["python3", f"{HERE}/engine.py", wd, str(t), "0", f"{wd}/prev/{i:02d}.png"],
                                  stderr=subprocess.DEVNULL))
    if len(procs) >= 2: procs.pop(0).wait()
for p in procs: p.wait()
from PIL import Image
fs = sorted(f for f in os.listdir(f"{wd}/prev") if f.endswith(".png"))
rows = math.ceil(len(fs) / 3); g = Image.new("RGB", (1920, 360 * rows), "white")
for i, f in enumerate(fs): g.paste(Image.open(f"{wd}/prev/{f}").convert("RGB").resize((640, 360)), ((i % 3) * 640, (i // 3) * 360))
g.save(f"{wd}/preview_grid.jpg", quality=80)
print("preview:", f"{wd}/preview_grid.jpg")
if preview: sys.exit(0)

# music ---------------------------------------------------------------------
seed = int(hashlib.md5(S["title"].encode()).hexdigest()[:8], 16)
music = S.get("music_file") or f"{wd}/music.wav"
if not S.get("music_file"):
    run(["python3", f"{HERE}/music.py", str(D + 2), music, str(seed)])

# render video in 2 parallel halves -------------------------------------------
half = round(D / 2 * 24) / 24
p1 = subprocess.Popen(["python3", f"{HERE}/engine.py", wd, "0", str(half), f"{wd}/part1.mp4"], stderr=subprocess.DEVNULL)
p2 = subprocess.Popen(["python3", f"{HERE}/engine.py", wd, str(half), str(D), f"{wd}/part2.mp4"], stderr=subprocess.DEVNULL)
assert p1.wait() == 0 and p2.wait() == 0, "render failed"

# audio mix: voice on top, music ducked under speech -----------------------------
mv = float(S.get("music_volume", 0.36))
run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{wd}/voice.wav", "-stream_loop", "-1", "-i", music, "-filter_complex",
     f"[0:a]aresample=44100,pan=stereo|c0=c0|c1=c0,asplit=2[v][vsc];[1:a]aresample=44100,volume={mv}[m];"
     "[m][vsc]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=450:makeup=1[md];"
     f"[v][md]amix=inputs=2:duration=first:normalize=0,afade=t=out:st={max(0, D - 2.5)}:d=2.5,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
     "-map", "[a]", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", f"{wd}/mix.m4a"])
open(f"{wd}/list.txt", "w").write(f"file '{wd}/part1.mp4'\nfile '{wd}/part2.mp4'\n")
run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{wd}/list.txt", "-i", f"{wd}/mix.m4a",
     "-map", "0:v", "-map", "1:a", "-c", "copy", "-shortest", "-movflags", "+faststart", f"{wd}/video.mp4"])

# subtitles ----------------------------------------------------------------------
def ts(t):
    ms = int(round(t * 1000)); return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"
out, i = [], 1
for s in TL["scenes"]:
    for x in s["subs"]:
        out.append(f"{i}\n{ts(x['start'])} --> {ts(x['end'] + 0.1)}\n{x['text']}\n"); i += 1
open(f"{wd}/subtitles.srt", "w").write("\n".join(out))

# chapters --------------------------------------------------------------------
ch = []
for i, s in enumerate(TL["scenes"]):
    if s.get("heading"):
        t = 0 if i == 0 else int(s["start"]); ch.append(f"{t//60}:{t%60:02d} {s['heading']}")
open(f"{wd}/chapters.txt", "w").write("\n".join(ch) + "\n")

# thumbnail ---------------------------------------------------------------------
run(["python3", f"{HERE}/thumb.py", wd])
dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{wd}/video.mp4"],
                     capture_output=True, text=True).stdout.strip()
print(f"DONE video.mp4 {dur}s | chapters:\n" + "\n".join(ch))
