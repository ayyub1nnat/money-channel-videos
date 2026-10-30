"""Illustrated "POV" video renderer: one AI illustration per scene with slow camera moves (Ken Burns),
soft crossfades, optional pop-in tag (big number / short label) and burned-in subtitles.
Usage: python3 pov.py <wd> <t0> <t1> <out.mp4|.png>
Needs <wd>/timeline.json (tts.py) and <wd>/img/NNN.jpg (scene index, 3 digits). script.json "vertical": true → 1080x1920."""
import json, sys, os, math, subprocess, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from povlib import shots, shot_params
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
wd = sys.argv[1]; t0 = float(sys.argv[2]); t1 = float(sys.argv[3]); out = sys.argv[4]
S = json.load(open(f"{wd}/script.json")); TL = json.load(open(f"{wd}/timeline.json"))
V = bool(S.get("vertical")); W, H = (1080, 1920) if V else (1920, 1080); FPS = 24; XF = 0.2 if V else 0.3
SC = TL["scenes"]; SPEC = S["scenes"]
FONT = os.path.join(HERE, "fonts", "Poppins-Bold.ttf")
if not os.path.exists(FONT): FONT = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"

_img = {}
def base(i):
    if i not in _img:
        p = f"{wd}/img/{i:03d}.jpg"
        im = Image.open(p).convert("RGB") if os.path.exists(p) else Image.new("RGB", (W, H), (235, 230, 220))
        # cover-fit into a canvas 12% larger than the frame so the camera can move
        cw, ch = int(W * 1.12), int(H * 1.12); s = max(cw / im.width, ch / im.height)
        im = im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.LANCZOS)
        x, y = (im.width - cw) // 2, (im.height - ch) // 2
        _img[i] = im.crop((x, y, x + cw, y + ch))
        if len(_img) > 4: _img.pop(next(iter(_img)))
    return _img[i]

def ease(u): return u * u * (3 - 2 * u)
def scene_frame(i, t):
    s = SC[i]; st = shots(s, V); j = max(0, sum(1 for x in st if x <= t) - 1)
    a = st[j]; b = st[j + 1] if j + 1 < len(st) else s["end"] + XF
    u = ease(min(1, max(0, (t - a) / max(0.1, b - a))))
    im = base(i); cw, ch = im.size; p = shot_params(i, j)
    if p["punch"]:                               # punch-in on part of the picture, slow push
        z = p["z"] + 0.05 * u; vw, vh = W / z, H / z
        cx = min(max(cw * p["fx"], vw / 2), cw - vw / 2); cy = min(max(ch * p["fy"], vh / 2), ch - vh / 2)
    else:
        mode = p["mode"]; z0, z1 = {"in": (1.0, 1.10), "out": (1.10, 1.0)}.get(mode, (1.06, 1.06))
        z = z0 + (z1 - z0) * u; vw, vh = min(W / z, cw), min(H / z, ch); cx, cy = cw / 2, ch / 2
        if mode == "left": cx = cw / 2 + (cw - vw) / 2 * (0.9 - 1.8 * u)
        if mode == "right": cx = cw / 2 - (cw - vw) / 2 * (0.9 - 1.8 * u)
    box = (cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2)
    return im.resize((W, H), Image.BILINEAR, box=box)

# ---- overlays
_txt = {}
def font(sz): return ImageFont.truetype(FONT, sz)
def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        nxt = (cur + " " + w).strip()
        if d.textlength(nxt, font=f) <= maxw: cur = nxt
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines
def sub_img(text):
    # owner 2026-10-30: clear subtitles that don't cover the picture: no dark box, white text with a thin black outline
    if text in _txt: return _txt[text]
    f = font(50 if V else 46); d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines = wrap(d, text, f, W * (0.84 if V else 0.72)); lh = int(f.size * 1.25)
    tw = int(max(d.textlength(l, font=f) for l in lines)); pw, ph = tw + 40, lh * len(lines) + 24
    im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
    for k, l in enumerate(lines):
        lw = dd.textlength(l, font=f)
        dd.text(((pw - lw) / 2, 10 + k * lh), l, font=f, fill="white", stroke_width=5, stroke_fill=(0, 0, 0))
    _txt[text] = im; return im
def tag_img(text, color):
    key = ("tag", text, color)
    if key in _txt: return _txt[key]
    f = font(84 if V else 76); d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    tw = int(d.textlength(text, font=f)); pw, ph = tw + 70, int(f.size * 1.5)
    im = Image.new("RGBA", (pw + 16, ph + 16), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
    dd.rounded_rectangle((10, 12, pw + 10, ph + 12), 26, fill=(0, 0, 0, 90))
    dd.rounded_rectangle((2, 2, pw, ph), 26, fill="white", outline=(25, 25, 25), width=5)
    dd.text((35, (ph - f.size * 1.2) / 2), text, font=f, fill=color)
    _txt[key] = im; return im

HOOK = S.get("hook") if (V and S.get("hook_overlay")) else None   # owner 2026-10-30: no title/headline text over the video
if isinstance(HOOK, str): HOOK = [HOOK]
_hook = None
def hook_img():
    global _hook
    if _hook is None:
        sz = 92; f = font(sz); d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        while max(d.textlength(l, font=f) for l in HOOK) > W - 90 and sz > 52: sz -= 4; f = font(sz)
        lh = int(sz * 1.18); im = Image.new("RGBA", (W, lh * len(HOOK) + 60), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
        for k, l in enumerate(HOOK):
            words = l.split(); x = (W - d.textlength(l, font=f)) / 2
            for w in words:
                col = "#FFD23F" if any(c.isdigit() for c in w) or "$" in w else "white"
                dd.text((x, 20 + k * lh), w, font=f, fill=col, stroke_width=11, stroke_fill="black")
                x += d.textlength(w + " ", font=f)
        _hook = im
    return _hook

def frame(t):
    i = next((k for k, s in enumerate(SC) if t < s["end"]), len(SC) - 1)
    fr = scene_frame(i, t)
    if i + 1 < len(SC) and t > SC[i]["end"] - XF:     # crossfade into the next scene
        a = ease((t - (SC[i]["end"] - XF)) / XF); fr = Image.blend(fr, scene_frame(i + 1, t), a)
    fr = fr.convert("RGBA")
    if HOOK:
        fr.alpha_composite(hook_img(), (0, int(H * 0.055)))
    tg = SPEC[i].get("tag")
    if tg:
        dt = t - SC[i]["start"] - 0.25
        if dt > 0:
            im = tag_img(tg, SPEC[i].get("tag_color", "#E23B3B"))
            sc_ = 0.7 + 0.3 * ease(min(1, dt / 0.18))
            im2 = im.resize((max(1, int(im.width * sc_)), max(1, int(im.height * sc_))), Image.BILINEAR)
            x = (W - im2.width) // 2 if V else 56 + (im.width - im2.width) // 2; y = int(H * ((0.27 if HOOK else 0.58) if V else 0.06)) + (im.height - im2.height) // 2
            fr.alpha_composite(im2, (x, y))
    for s in SC[i]["subs"] + (SC[i + 1]["subs"] if i + 1 < len(SC) else []):
        if s["start"] <= t < s["end"] + 0.1:
            im = sub_img(s["text"]); fr.alpha_composite(im, ((W - im.width) // 2, int(H * (0.80 if V else 0.89)) - im.height // 2)); break
    return fr.convert("RGB")

if out.endswith(".png"):
    frame(t0).save(out); sys.exit(0)
n0, n1 = round(t0 * FPS), round(t1 * FPS)
p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "20" if V else "24", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
for n in range(n0, n1):
    p.stdin.write(frame(n / FPS).tobytes())
p.stdin.close(); assert p.wait() == 0
