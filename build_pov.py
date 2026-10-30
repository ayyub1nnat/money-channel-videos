"""Build an illustrated POV video (script.json "style": "pov"), horizontal (main) or vertical (Short).
Usage: python3 build_pov.py <workdir> [--preview]
Needs images in <wd>/img/NNN.jpg (one per scene; get them with images.py) and, for the thumbnail, <wd>/img/thumb.jpg.
Steps: voice + timeline (tts.py) → preview grid → music → frames (pov.py, 2 in parallel) → mix (voice + ducked music)
→ video.mp4 (or short.mp4 if vertical) + subtitles.srt + chapters.txt + thumbnail.jpg (horizontal)."""
import json, os, subprocess, sys, math, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
wd = os.path.abspath(sys.argv[1]); preview = "--preview" in sys.argv
def run(cmd): print("+", " ".join(cmd)[:200], flush=True); subprocess.run(cmd, check=True)

S = json.load(open(f"{wd}/script.json")); V = bool(S.get("vertical"))
if not os.path.exists(f"{wd}/timeline.json") or os.path.getmtime(f"{wd}/timeline.json") < os.path.getmtime(f"{wd}/script.json"):
    run(["python3", f"{HERE}/tts.py", wd, os.environ.get("MODELS_DIR", os.path.join(HERE, "models"))])
TL = json.load(open(f"{wd}/timeline.json")); D = TL["duration"]; scs = TL["scenes"]
missing = [i for i in range(len(scs)) if not os.path.exists(f"{wd}/img/{i:03d}.jpg")]
if missing: print("WARNING missing images for scenes:", missing)

os.makedirs(f"{wd}/prev", exist_ok=True)
step = max(1, math.ceil(len(scs) / 24)); idx = list(range(0, len(scs), step))
tw, th = (240, 427) if V else (480, 270); cols = 6 if V else 4
for i in idx:
    s = scs[i]
    subprocess.run(["python3", f"{HERE}/pov.py", wd, str(s["start"] + (s["end"] - s["start"]) * 0.6), "0", f"{wd}/prev/s{i:03d}.png"], check=True)
from PIL import Image
rows = math.ceil(len(idx) / cols); g = Image.new("RGB", (tw * cols, th * rows), "white")
for k, i in enumerate(idx):
    g.paste(Image.open(f"{wd}/prev/s{i:03d}.png").convert("RGB").resize((tw, th)), ((k % cols) * tw, (k // cols) * th))
g.save(f"{wd}/preview_grid.jpg", quality=80); print("preview:", f"{wd}/preview_grid.jpg", f"{D:.1f}s")
if preview: sys.exit(0)

# owner 2026-10-30: NO background music and NO transition sounds by default (voice only, so viewers can focus).
# Old behaviour only if script.json sets "music": true / "sfx": true.
MUSIC, SFX = bool(S.get("music", False)), bool(S.get("sfx", False))
seed = str(int(hashlib.md5(S["title"].encode()).hexdigest()[:8], 16))
if MUSIC and not os.path.exists(f"{wd}/music.wav"):
    run(["python3", f"{HERE}/music.py", str(D + 2), f"{wd}/music.wav", seed] + (["energetic"] if V else []))
half = round(D / 2 * 24) / 24
p1 = subprocess.Popen(["python3", f"{HERE}/pov.py", wd, "0", str(half), f"{wd}/part1.mp4"])
p2 = subprocess.Popen(["python3", f"{HERE}/pov.py", wd, str(half), str(D), f"{wd}/part2.mp4"])
assert p1.wait() == 0 and p2.wait() == 0, "render failed"
mv = float(S.get("music_volume", 0.30 if V else 0.26)); lufs = -14
xv = float(S.get("sfx_volume", 0.45 if V else 0.30))
if MUSIC or SFX:
    if SFX: run(["python3", f"{HERE}/sfx.py", wd])
    ins = ["-i", f"{wd}/voice.wav"] + (["-stream_loop", "-1", "-i", f"{wd}/music.wav"] if MUSIC else []) + (["-i", f"{wd}/sfx.wav"] if SFX else [])
    fc = "[0:a]aresample=44100,pan=stereo|c0=c0|c1=c0,asplit=2[v][vsc];"; mix = "[v]"; n = 1; k = 1
    if MUSIC:
        fc += f"[{k}:a]aresample=44100,volume={mv}[m];[m][vsc]sidechaincompress=threshold=0.02:ratio=9:attack=15:release=400:makeup=1[md];"; mix += "[md]"; n += 1; k += 1
    else: fc += "[vsc]anullsink;"
    if SFX: fc += f"[{k}:a]aresample=44100,pan=stereo|c0=c0|c1=c0,volume={xv}[fx];"; mix += "[fx]"; n += 1
    fc += f"{mix}amix=inputs={n}:duration=first:normalize=0,afade=t=out:st={max(0, D - 2)}:d=2,loudnorm=I={lufs}:TP=-1.5:LRA=11[a]"
    run(["ffmpeg", "-y", "-loglevel", "error"] + ins + ["-filter_complex", fc, "-map", "[a]", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", f"{wd}/mix.m4a"])
else:
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{wd}/voice.wav", "-af",
         f"aresample=44100,pan=stereo|c0=c0|c1=c0,afade=t=out:st={max(0, D - 1)}:d=1,loudnorm=I={lufs}:TP=-1.5:LRA=11",
         "-ar", "48000", "-c:a", "aac", "-b:a", "192k", f"{wd}/mix.m4a"])
open(f"{wd}/list.txt", "w").write(f"file '{wd}/part1.mp4'\nfile '{wd}/part2.mp4'\n")
out = f"{wd}/{'short' if V else 'video'}.mp4"
run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{wd}/list.txt", "-i", f"{wd}/mix.m4a",
     "-map", "0:v", "-map", "1:a", "-c", "copy", "-shortest", "-movflags", "+faststart", out])
if os.path.getsize(out) > 90e6:          # GitHub's 100 MB file limit (media branch): squeeze until it fits
    for crf in (26, 28, 30):
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", out, "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
             "-c:a", "copy", "-movflags", "+faststart", f"{wd}/small.mp4"]); os.replace(f"{wd}/small.mp4", out)
        if os.path.getsize(out) <= 90e6: break

def ts(t):
    ms = int(round(t * 1000)); return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"
srt, n = [], 1
for s in scs:
    for x in s["subs"]:
        srt.append(f"{n}\n{ts(x['start'])} --> {ts(x['end'] + 0.1)}\n{x['text']}\n"); n += 1
open(f"{wd}/subtitles.srt", "w").write("\n".join(srt))
spec = S["scenes"]; ch, last = [], -99
for i, s in enumerate(scs):
    c = spec[i].get("chapter"); t = 0 if i == 0 else int(s["start"])
    if c and (t - last >= 10 or not ch): ch.append(f"{t//60}:{t%60:02d} {c}"); last = t
if ch: ch[0] = "0:00 " + ch[0].split(" ", 1)[1]
open(f"{wd}/chapters.txt", "w").write("\n".join(ch) + "\n")
if not V and S.get("thumbnail"):
    run(["python3", f"{HERE}/thumb_pov.py", wd])
print(f"DONE pov {os.path.basename(out)} {D:.1f}s | chapters:\n" + "\n".join(ch))
