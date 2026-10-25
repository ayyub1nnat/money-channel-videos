"""Thumbnail for POV videos. Usage: python3 thumb_pov.py <wd>
script.json "thumbnail": {"image": "thumb" | <scene index>, "text": ["LINE 1", "LINE 2"], "color": "#FFD23F",
                          "pos": "left"|"right", "you": [x, y] (optional point in 1280x720 coords for a "YOU" arrow)}"""
import json, sys, os, math
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
HERE = os.path.dirname(os.path.abspath(__file__)); wd = sys.argv[1]
S = json.load(open(f"{wd}/script.json")); T = S["thumbnail"]
src = T.get("image", "thumb"); p = f"{wd}/img/{src}.jpg" if isinstance(src, str) else f"{wd}/img/{int(src):03d}.jpg"
W, H = 1280, 720
im = Image.open(p).convert("RGB"); s = max(W / im.width, H / im.height)
im = im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.LANCZOS)
im = im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))
im = ImageEnhance.Color(im).enhance(1.25); im = ImageEnhance.Contrast(im).enhance(1.08)
d = ImageDraw.Draw(im); FONT = os.path.join(HERE, "fonts", "Poppins-Bold.ttf")
lines = T.get("text", []); lines = [lines] if isinstance(lines, str) else lines
right = T.get("pos", "left") == "right"; y = 34
for k, ln in enumerate(lines):
    sz = 96 if k == 0 else 84
    f = ImageFont.truetype(FONT, sz)
    while d.textlength(ln, font=f) > W * 0.56 and sz > 50: sz -= 4; f = ImageFont.truetype(FONT, sz)
    x = W - 40 - d.textlength(ln, font=f) if right else 40
    d.text((x, y), ln, font=f, fill=T.get("color", "#FFD23F") if k == 0 else "white", stroke_width=10, stroke_fill="black")
    y += int(sz * 1.12)
if T.get("you"):
    tx, ty = T["you"]; f = ImageFont.truetype(FONT, 70); lx, ly = tx + 150, ty - 120
    d.line((lx - 10, ly + 70, tx + 18, ty - 10), fill="black", width=22); d.line((lx - 10, ly + 70, tx + 18, ty - 10), fill="#E23B3B", width=12)
    d.polygon([(tx, ty), (tx + 46, ty - 14), (tx + 14, ty - 46)], fill="#E23B3B", outline="black")
    d.text((lx - 20, ly - 30), "YOU", font=f, fill="white", stroke_width=9, stroke_fill="black")
im.save(f"{wd}/thumbnail.jpg", quality=90); print("thumbnail ok")
