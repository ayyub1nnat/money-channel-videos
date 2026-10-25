"""Build a whiteboard-style video (script.json "style": "sketch").
Usage: python3 build_sketch.py <workdir> [--preview]
Reuses build.py for voice/timeline/music/subtitles/thumbnail, then renders frames with sketch.py and mixes
voice + pencil scribbles + ducked music into video.mp4."""
import json, os, subprocess, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
wd = os.path.abspath(sys.argv[1]); preview = "--preview" in sys.argv
def run(cmd): print("+", " ".join(cmd), flush=True); subprocess.run(cmd, check=True)

S = json.load(open(f"{wd}/script.json"))
if not os.path.exists(f"{wd}/timeline.json") or os.path.getmtime(f"{wd}/timeline.json") < os.path.getmtime(f"{wd}/script.json"):
    run(["python3", f"{HERE}/tts.py", wd, os.environ.get("MODELS_DIR", os.path.join(HERE, "models"))])
TL = json.load(open(f"{wd}/timeline.json")); D = TL["duration"]

os.makedirs(f"{wd}/prev", exist_ok=True)
times = [s["start"] + (s["end"] - s["start"]) * 0.85 for s in TL["scenes"]]
for i, t in enumerate(times):
    subprocess.run(["python3", f"{HERE}/sketch.py", wd, str(t), "0", f"{wd}/prev/s{i:02d}.png"], stderr=subprocess.DEVNULL, check=True)
from PIL import Image
rows = math.ceil(len(times) / 3); g = Image.new("RGB", (1920, 360 * rows), "white")
for i in range(len(times)):
    g.paste(Image.open(f"{wd}/prev/s{i:02d}.png").convert("RGB").resize((640, 360)), ((i % 3) * 640, (i // 3) * 360))
g.save(f"{wd}/preview_grid.jpg", quality=80); print("preview:", f"{wd}/preview_grid.jpg")
if preview: sys.exit(0)

if not os.path.exists(f"{wd}/music.wav"):
    import hashlib
    run(["python3", f"{HERE}/music.py", str(D + 2), f"{wd}/music.wav", str(int(hashlib.md5(S["title"].encode()).hexdigest()[:8], 16))])
run(["python3", f"{HERE}/sketch.py", wd, "--pencil"])
half = round(D / 2 * 24) / 24
p1 = subprocess.Popen(["python3", f"{HERE}/sketch.py", wd, "0", str(half), f"{wd}/part1.mp4"], stderr=subprocess.DEVNULL)
p2 = subprocess.Popen(["python3", f"{HERE}/sketch.py", wd, str(half), str(D), f"{wd}/part2.mp4"], stderr=subprocess.DEVNULL)
assert p1.wait() == 0 and p2.wait() == 0, "render failed"
mv = float(S.get("music_volume", 0.30)); pv = float(S.get("pencil_volume", 0.16))
run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{wd}/voice.wav", "-stream_loop", "-1", "-i", f"{wd}/music.wav", "-i", f"{wd}/pencil.wav",
     "-filter_complex",
     f"[0:a]aresample=44100,pan=stereo|c0=c0|c1=c0,asplit=2[v][vsc];[1:a]aresample=44100,volume={mv}[m];"
     "[m][vsc]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=450:makeup=1[md];"
     f"[2:a]aresample=44100,pan=stereo|c0=c0|c1=c0,volume={pv}[pc];"
     f"[v][md][pc]amix=inputs=3:duration=first:normalize=0,afade=t=out:st={max(0, D - 2.5)}:d=2.5,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
     "-map", "[a]", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", f"{wd}/mix.m4a"])
open(f"{wd}/list.txt", "w").write(f"file '{wd}/part1.mp4'\nfile '{wd}/part2.mp4'\n")
run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{wd}/list.txt", "-i", f"{wd}/mix.m4a",
     "-map", "0:v", "-map", "1:a", "-c", "copy", "-shortest", "-movflags", "+faststart", f"{wd}/video.mp4"])
print("DONE sketch video.mp4")
