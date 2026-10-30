"""Thumbnail for POV videos (owner's style since 2026-10-30, like big finance POV channels: bold, simple, clickable).
Usage: python3 thumb_pov.py <wd>
script.json "thumbnail":
  split layout (default for comparisons):
    {"layout": "split", "left": {"img": <prompt>, "label": "MIA: $410", "color": "#E23B3B"},
                        "right": {"img": <prompt>, "label": "YOU: $42", "color": "#1B9E4B"}, "arrow": true}
    images: <wd>/img/thumb_l.jpg and thumb_r.jpg (images_snippet.py makes them from the prompts)
  single layout:
    {"image": "thumb" | <scene index>, "text": ["LINE 1", "LINE 2"], "label": "$1,000 SAVED", "color": "#1B9E4B", "pos": "left"|"right"}"""
import json, sys, os, math
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); wd = sys.argv[1]
S = json.load(open(f"{wd}/script.json")); T = S["thumbnail"]
W, H = 1280, 720
FONT = os.path.join(HERE, "fonts", "Poppins-Bold.ttf")
if not os.path.exists(FONT): FONT = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
def F(sz): return ImageFont.truetype(FONT, sz)
def cover(p, w, h):
    im = Image.open(p).convert("RGB"); s = max(w / im.width, h / im.height)
    im = im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))
def label(d, cx, y, text, color, maxw, sz=66):
    f = F(sz)
    while d.textlength(text, font=f) > maxw - 50 and sz > 34: sz -= 2; f = F(sz)
    tw = d.textlength(text, font=f); bw, bh = tw + 44, int(sz * 1.32)
    x0 = cx - bw / 2
    d.rounded_rectangle((x0 + 6, y + 7, x0 + bw + 6, y + bh + 7), 14, fill=(0, 0, 0))
    d.rounded_rectangle((x0, y, x0 + bw, y + bh), 14, fill="white", outline=(0, 0, 0), width=5)
    d.text((x0 + 22, y + (bh - sz * 1.22) / 2), text, font=f, fill=color)

if T.get("layout") == "split":
    L, R = T["left"], T["right"]; half = W // 2
    li = cover(f"{wd}/img/thumb_l.jpg", half, H); ri = cover(f"{wd}/img/thumb_r.jpg", half, H)
    li = ImageEnhance.Brightness(ImageEnhance.Color(li).enhance(0.8)).enhance(0.78)          # gloomy side
    li = Image.blend(li, Image.new("RGB", li.size, (25, 40, 80)), 0.18)
    ri = ImageEnhance.Contrast(ImageEnhance.Color(ri).enhance(1.3)).enhance(1.08)          # bright side
    im = Image.new("RGB", (W, H)); im.paste(li, (0, 0)); im.paste(ri, (half, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((half - 5, 0, half + 5, H), fill=(15, 15, 15))
    label(d, half / 2, 26, L.get("label", ""), L.get("color", "#E23B3B"), half)
    label(d, half + half / 2, 26, R.get("label", ""), R.get("color", "#1B9E4B"), half)
    if T.get("arrow", True):                                   # yellow arrow bad → good
        y = H - 110; x0, x1 = half - 120, half + 110
        d.line((x0, y, x1 - 40, y), fill=(0, 0, 0), width=40); d.line((x0, y, x1 - 40, y), fill="#FFD23F", width=26)
        d.polygon([(x1 + 8, y), (x1 - 52, y - 46), (x1 - 52, y + 46)], fill="#FFD23F", outline=(0, 0, 0), width=6)
else:
    src = T.get("image", "thumb"); p = f"{wd}/img/{src}.jpg" if isinstance(src, str) else f"{wd}/img/{int(src):03d}.jpg"
    im = cover(p, W, H); im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.25)).enhance(1.08)
    d = ImageDraw.Draw(im)
    lines = T.get("text", []); lines = [lines] if isinstance(lines, str) else lines
    right = T.get("pos", "left") == "right"; y = 30
    for k, ln in enumerate(lines):
        sz = 104; f = F(sz)
        while d.textlength(ln, font=f) > W * 0.5 and sz > 50: sz -= 4; f = F(sz)
        x = W - 40 - d.textlength(ln, font=f) if right else 40
        d.text((x, y), ln, font=f, fill="white", stroke_width=12, stroke_fill="black"); y += int(sz * 1.08)
    if T.get("label"):
        f = F(60); tw = d.textlength(T["label"], font=f)
        label(d, (W - 40 - (tw + 44) / 2) if not right else (40 + (tw + 44) / 2), y + 10, T["label"], T.get("color", "#1B9E4B"), W * 0.45, 60)
im.save(f"{wd}/thumbnail.jpg", quality=90); print("thumbnail ok")
