"""Thumbnail 1280x720 from script.json "thumbnail": {line1, line2, badge, sub, mood, bg:[c1,c2], props}"""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skia
import engine as E
from PIL import Image

wd = sys.argv[1]
S = json.load(open(f"{wd}/script.json")); T = S.get("thumbnail", {})
W, H = 1280, 720
info = skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
surf = skia.Surface.MakeRaster(info); c = surf.getCanvas()
bg = T.get("bg") or ["#FFD23F", "#FF9F1C"]
c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=skia.GradientShader.MakeLinear([(0, 0), (W, H)], [E.C(bg[0]), E.C(bg[1])])))
for bx, by, br in [(1150, 90, 150), (80, 650, 130)]:
    c.drawCircle(bx, by, br, E.paint(skia.Color(255, 255, 255, 70)))
mood = T.get("mood", "happy")
c.save(); c.translate(1010, 760); c.scale(0.95, 0.95)
E.person(c, 0, 0, 1.0, 0.5, mood, E.col(T.get("shirt"), E.GREEN if mood == "happy" else E.CORAL),
         {"happy": "up", "sad": "head", "surprised": "head"}.get(mood, "point"), long_hair=T.get("long_hair", False))
c.restore()
props = T.get("props", ["coins"])
if "coins" in props:
    for x, y, rot in [(800, 150, 0.3), (1220, 300, 1.2), (850, 470, 2.0)]: E.coin(c, x, y, 44, rot)
    E.bill(c, 1200, 560, 150, 80, -20)
if "question" in props:
    for x, y in [(820, 180), (1230, 200)]: E.text(c, "?", x, y, 150, E.PURPLE)
def outlined(s, x, y, sz, fill):
    sz = E.fit(s, sz, 600); f = E.font(sz)
    c.drawString(s, x, y, f, E.paint(E.INK, "stroke", 16)); c.drawString(s, x, y, f, E.paint(fill))
outlined(T.get("line1", "").upper(), 60, 190, 120, "#FFFFFF")
outlined(T.get("line2", "").upper(), 60, 330, 150, "#FFFFFF")
if T.get("badge"):
    E.rrect(c, 55, 380, 580, 150, 30, E.INK); E.text(c, T["badge"].upper(), 345, 485, 96, "#FFD23F", maxw=540)
if T.get("sub"):
    E.rrect(c, 60, 575, 560, 90, 45, E.CORAL, E.INK, 6); E.text(c, T["sub"], 340, 636, 44, "#FFFFFF", maxw=520)
surf.makeImageSnapshot().save(f"{wd}/thumbnail.png", skia.kPNG)
Image.open(f"{wd}/thumbnail.png").convert("RGB").save(f"{wd}/thumbnail.jpg", quality=90)
print("thumbnail ok")
