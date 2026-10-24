"""Vertical teaser Short (1080x1920, ~35-50 s) cut from a finished day's video.
Usage: python3 short.py <workdir>
Needs in <workdir>: video.mp4, voice.wav, timeline.json, script.json (i.e. run after build.py).
Optional in script.json:
  "short": {"hook": "Big text on top (<= 40 chars)",
            "clips": [[scene, first_line, last_line], ...]}   # lines inclusive, 0-based
Default clips: the hook scene's first 3 lines + the first 2 lines of three evenly spaced middle scenes.
Output: short.mp4 (clean voice from the clips + energetic original music, big captions, end card)."""
import json, os, subprocess, sys, hashlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
wd = os.path.abspath(sys.argv[1])
S = json.load(open(f"{wd}/script.json")); TL = json.load(open(f"{wd}/timeline.json"))
SC = TL["scenes"]; T = S.get("thumbnail", {}); SH = S.get("short", {})
W, H = 1080, 1920
VY = 560                     # top of the video strip
CROP_H = 840                 # keep the top 840 px of each 1920x1080 frame (drops the burned-in subtitle strip)
VH = round(CROP_H * W / 1920)  # 506 px tall on the Short
FB = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
FX = "/usr/share/fonts/truetype/google-fonts/Poppins-ExtraBold.ttf"
if not os.path.exists(FX): FX = FB
tmp = f"{wd}/short_tmp"; os.makedirs(tmp, exist_ok=True)

def run(cmd):
    print("+", " ".join(cmd)[:200], flush=True); subprocess.run(cmd, check=True)

# ---- pick clips --------------------------------------------------------------
def default_clips():
    n = len(SC); mids = [i for i in range(1, n - 2)]
    pick = [mids[round(k * (len(mids) - 1) / 2)] for k in range(3)] if len(mids) >= 3 else mids
    return [[0, 0, min(2, len(SC[0]["line_starts"]) - 1)]] + [[i, 0, min(1, len(SC[i]["line_starts"]) - 1)] for i in sorted(set(pick))]

clips = SH.get("clips") or default_clips()
def span(si, a, b):
    s = SC[si]; ls = s["line_starts"]
    t0 = max(0.0, ls[a] - 0.12)
    # end of line b = start of last sub chunk that ends before the next line starts
    nxt = ls[b + 1] if b + 1 < len(ls) else s["end"]
    end = max(x["end"] for x in s["subs"] if x["start"] < nxt - 0.05)
    return t0, end + 0.25
spans = [span(*c) for c in clips]
total = sum(b - a for a, b in spans)
while total > 50 and len(spans) > 2:          # keep it short
    spans.pop(); clips.pop(); total = sum(b - a for a, b in spans)
END = 3.2                                       # end card seconds
print("clips", clips, "speech", round(total, 1))

# ---- static overlays (PIL) -----------------------------------------------------
def font(p, sz): return ImageFont.truetype(p, sz)
def fit(d, txt, p, sz, maxw):
    while sz > 30 and d.textlength(txt, font=font(p, sz)) > maxw: sz -= 4
    return font(p, sz)
def wrap(d, txt, p, sz, maxw, maxlines=2):
    words = txt.split()
    for s_ in range(sz, 40, -4):
        f = font(p, s_); lines, cur = [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if d.textlength(t, font=f) <= maxw: cur = t
            else: lines.append(cur); cur = w
        lines.append(cur)
        if len(lines) <= maxlines: return f, lines
    return f, lines

ink = (31, 42, 68); yellow = (255, 210, 63); coral = (255, 107, 107)
hook = SH.get("hook") or " ".join(x for x in [T.get("line1"), T.get("line2"), T.get("badge")] if x)
ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
f, lines = wrap(d, hook.upper(), FX, 104, W - 120, 2)
if f.size < 76: f, lines = wrap(d, hook.upper(), FX, 104, W - 120, 3)
lh = f.size * 1.12; y = 290 - lh * len(lines) / 2
for ln in lines:
    d.text((W / 2, y + lh / 2), ln, font=f, fill="white", anchor="mm", stroke_width=12, stroke_fill=ink); y += lh
# video frame border + CTA pill under captions
d.rounded_rectangle([0, VY - 8, W, VY + VH + 8], 0, outline=ink, width=8)
cta = "FULL VIDEO ON THE CHANNEL"
fc = fit(d, cta, FB, 50, 820); tw = d.textlength(cta, font=fc) + 150
d.rounded_rectangle([(W - tw) / 2, 1300, (W + tw) / 2, 1410], 55, fill=coral, outline=ink, width=6)
d.text((W / 2 - 40, 1355), cta, font=fc, fill="white", anchor="mm")
cx = (W + tw) / 2 - 62; d.polygon([(cx - 16, 1330), (cx - 16, 1380), (cx + 26, 1355)], fill="white")
ov.save(f"{tmp}/overlay.png")

# end card: gradient + thumbnail + text
bg = T.get("bg") or ["#FFD23F", "#FF9F1C"]
def hx(c): c = c.lstrip("#"); return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
c1, c2 = hx(bg[0]), hx(bg[1])
ec = Image.new("RGB", (W, H)); px = ec.load()
for yy in range(H):
    k = yy / H; col = tuple(int(c1[i] + (c2[i] - c1[i]) * k) for i in range(3))
    for xx in range(W): px[xx, yy] = col
de = ImageDraw.Draw(ec)
f1, l1 = wrap(de, "WATCH THE FULL VIDEO", FX, 110, W - 120, 2); y = 420
for ln in l1:
    de.text((W / 2, y), ln, font=f1, fill="white", anchor="mm", stroke_width=12, stroke_fill=ink); y += f1.size * 1.15
th = Image.open(f"{wd}/thumbnail.png").convert("RGB").resize((960, 540))
ec.paste(Image.new("RGB", (976, 556), ink), (52, 712)); ec.paste(th, (60, 720))
f2, l2 = wrap(de, S["title"], FB, 54, W - 140, 3); y = 1380
for ln in l2:
    de.text((W / 2, y), ln, font=f2, fill=ink, anchor="mm"); y += f2.size * 1.25
de.text((W / 2, y + 90), "Link in the description", font=font(FB, 46), fill="white", anchor="mm", stroke_width=6, stroke_fill=ink)
ec.save(f"{tmp}/endcard.png")

# ---- captions (ASS, big & centered under the video) ----------------------------
def at(t): t = max(0, t); return f"{int(t // 3600)}:{int(t // 60 % 60):02d}:{t % 60:05.2f}"
ev = []; off = 0.0
for (si, a, b), (t0, t1) in zip(clips, spans):
    for x in SC[si]["subs"]:
        if x["end"] <= t0 or x["start"] >= t1: continue
        s0 = max(x["start"], t0) - t0 + off; s1 = min(x["end"] + 0.08, t1) - t0 + off
        txt = x["text"].replace("{", "(").replace("}", ")")
        ev.append([s0, s1, txt])
    off += t1 - t0
ev.sort()
for i in range(len(ev) - 1): ev[i][1] = min(ev[i][1], ev[i + 1][0] - 0.01)   # never two captions at once
ev = [f"Dialogue: 0,{at(a)},{at(b)},Cap,,0,0,0,,{t}" for a, b, t in ev]
ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Poppins,80,&H00FFFFFF,&H00FFFFFF,&H00442A1F,&H64000000,-1,0,0,0,100,100,0,0,1,7,2,5,70,70,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(e.replace(",Cap,,0,0,0,,", ",Cap,,0,0,0,,{\\pos(540,1175)}") for e in ev) + "\n"
open(f"{tmp}/caps.ass", "w").write(ass)

# ---- cut video + voice ---------------------------------------------------------
parts = []
for i, (t0, t1) in enumerate(spans):
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", f"{wd}/video.mp4",
         "-an", "-vf", "fps=30,setsar=1", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", f"{tmp}/v{i}.mp4"])
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", f"{wd}/voice.wav",
         "-af", "aresample=44100,afade=t=in:d=0.04,areverse,afade=t=in:d=0.08,areverse", "-ac", "1", f"{tmp}/a{i}.wav"])
    parts.append(i)
open(f"{tmp}/vl.txt", "w").write("".join(f"file '{tmp}/v{i}.mp4'\n" for i in parts))
open(f"{tmp}/al.txt", "w").write("".join(f"file '{tmp}/a{i}.wav'\n" for i in parts))
run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{tmp}/vl.txt", "-c", "copy", f"{tmp}/clips.mp4"])
run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{tmp}/al.txt", f"{tmp}/voice.wav"])
D = total + END

# ---- compose vertical video ------------------------------------------------------
fc = (f"[0:v]split=2[a][b];"
      f"[a]crop=1920:{CROP_H}:0:0,scale=-2:{H},crop={W}:{H},gblur=sigma=40,eq=brightness=-0.12:saturation=1.2[bg];"
      f"[b]crop=1920:{CROP_H}:0:0,scale={W}:{VH}[fg];"
      f"[bg][fg]overlay=0:{VY}[m];[m][1:v]overlay=0:0[o];[o]ass={tmp}/caps.ass,fps=30,format=yuv420p,setsar=1[main];"
      f"[2:v]scale={W}:{H},fps=30,format=yuv420p,trim=duration={END},setpts=PTS-STARTPTS,fade=t=in:d=0.35,setsar=1[end];"
      f"[main][end]concat=n=2:v=1:a=0[v]")
run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{tmp}/clips.mp4", "-i", f"{tmp}/overlay.png",
     "-loop", "1", "-t", f"{END}", "-i", f"{tmp}/endcard.png", "-filter_complex", fc, "-map", "[v]",
     "-c:v", "libx264", "-preset", "medium", "-crf", "19", f"{tmp}/video_v.mp4"])

# ---- energetic music + mix ----------------------------------------------------------
seed = int(hashlib.md5((S["title"] + "short").encode()).hexdigest()[:8], 16)
run(["python3", f"{HERE}/music.py", str(D + 1), f"{tmp}/music.wav", str(seed), "energetic"])
run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{tmp}/voice.wav", "-i", f"{tmp}/music.wav", "-filter_complex",
     f"[0:a]apad=whole_dur={D},pan=stereo|c0=c0|c1=c0,asplit=2[v][sc];[1:a]aresample=44100,volume=0.55[m];"
     "[m][sc]sidechaincompress=threshold=0.03:ratio=5:attack=10:release=300:makeup=1[md];"
     f"[v][md]amix=inputs=2:duration=first:normalize=0,atrim=duration={D},afade=t=out:st={D - 1.2}:d=1.2,"
     "loudnorm=I=-13:TP=-1.5:LRA=9[a]", "-map", "[a]", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", f"{tmp}/mix.m4a"])
run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{tmp}/video_v.mp4", "-i", f"{tmp}/mix.m4a", "-map", "0:v", "-map", "1:a",
     "-c", "copy", "-shortest", "-movflags", "+faststart", f"{wd}/short.mp4"])
dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{wd}/short.mp4"],
                     capture_output=True, text=True).stdout.strip()
print(f"DONE short.mp4 {dur}s clips={clips}")
