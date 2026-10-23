"""Animated explainer renderer. Scenes are param-driven templates (see RUNBOOK.md).
Usage: python3 engine.py <workdir> <t0> <t1> <out.mp4|out.png>
Reads <workdir>/timeline.json (made by tts.py)."""
import json, math, sys, subprocess, random, hashlib
import numpy as np
import skia

W, H, FPS = 1920, 1080, 24
FONT_DIR = "/usr/share/fonts/truetype/google-fonts/"
def _tf(name, fallback="DejaVu Sans"):
    tf = skia.Typeface.MakeFromFile(FONT_DIR + name)
    return tf if tf else skia.Typeface(fallback)
TF_BOLD = _tf("Poppins-Bold.ttf")
TF_SEMI = _tf("Poppins-Medium.ttf")

def C(h, a=255):
    h = h.lstrip("#")
    return skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

INK, CREAM, WHITE = "#1F2A44", "#FFF6E9", "#FFFFFF"
TEAL, ORANGE, CORAL, PURPLE = "#2EC4B6", "#FF9F1C", "#FF6B6B", "#7B61FF"
GREEN, YELLOW, SKY, PINK = "#3BB273", "#FFD23F", "#5DA9E9", "#FF8FAB"
SKIN, HAIR = "#F2C29B", "#3A2A20"
ACCENTS = [SKY, ORANGE, GREEN, PURPLE, CORAL, TEAL]
NAMED = {"teal": TEAL, "orange": ORANGE, "coral": CORAL, "red": CORAL, "purple": PURPLE, "green": GREEN,
         "yellow": YELLOW, "sky": SKY, "blue": SKY, "pink": PINK}
BG_PAIRS = [("#FFE8D6", "#FFD1B3"), ("#E3F6F5", "#BDEBE7"), ("#EAE6FF", "#D3CCFF"), ("#FFF3D6", "#FFE2A8"),
            ("#FFE3E3", "#FFC9C9"), ("#E6F7EC", "#C5EDD3"), ("#E4F1FB", "#C3DFF5"), ("#F1ECFF", "#DCD2FF"),
            ("#FFF6E9", "#FFE6C4"), ("#FFF0F5", "#FFD6E4")]

def col(x, default=SKY):
    if not x: return default
    return NAMED.get(str(x).lower(), x if str(x).startswith("#") else default)

# ---------- easing ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def eo_cubic(x): x = clamp(x); return 1 - (1 - x) ** 3
def eo_back(x, s=1.7):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1
def prog(lt, t0, d=0.5): return clamp((lt - t0) / d)

# ---------- primitives ----------
def paint(c_, style="fill", sw=0):
    p = skia.Paint(AntiAlias=True, Color=C(c_) if isinstance(c_, str) else c_)
    if style == "stroke":
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(sw)
        p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    return p

def rrect(c, x, y, w, h, r, fill, outline=None, ow=6):
    rect = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r)
    c.drawRRect(rect, paint(fill))
    if outline: c.drawRRect(rect, paint(outline, "stroke", ow))

def circle(c, x, y, r, fill, outline=None, ow=6):
    c.drawCircle(x, y, r, paint(fill))
    if outline: c.drawCircle(x, y, r, paint(outline, "stroke", ow))

def line(c, x1, y1, x2, y2, c_, w): c.drawLine(x1, y1, x2, y2, paint(c_, "stroke", w))

def shadow(c, x, y, w, h, r=30, a=40):
    p = skia.Paint(AntiAlias=True, Color=skia.Color(31, 42, 68, a),
                   MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y + 14, w, h), r, r), p)

def font(sz, tf=TF_BOLD):
    f = skia.Font(tf, sz); f.setEdging(skia.Font.Edging.kAntiAlias); f.setSubpixel(True); return f

def fit(s, sz, maxw, tf=TF_BOLD, minsz=18):
    while sz > minsz and font(sz, tf).measureText(s) > maxw: sz -= 2
    return sz

def text(c, s, x, y, sz, c_=INK, tf=TF_BOLD, align="center", alpha=255, maxw=None):
    s = str(s)
    if maxw: sz = fit(s, sz, maxw, tf)
    f = font(sz, tf); w = f.measureText(s)
    if align == "center": x -= w / 2
    elif align == "right": x -= w
    p = paint(c_); p.setAlpha(int(alpha)); c.drawString(s, x, y, f, p)
    return w

def wrap(s, f, maxw):
    lines = [""]
    for w in str(s).split():
        t = (lines[-1] + " " + w).strip()
        if f.measureText(t) <= maxw or not lines[-1]: lines[-1] = t
        else: lines.append(w)
    return lines

def text_block(c, s, x, y, sz, maxw, c_=INK, tf=TF_BOLD, align="center", maxlines=3, alpha=255, lh=1.25):
    while True:
        f = font(sz, tf); ls = wrap(s, f, maxw)
        if len(ls) <= maxlines or sz < 22: break
        sz -= 3
    tot = len(ls) * sz * lh
    for i, l in enumerate(ls):
        text(c, l, x, y - tot / 2 + sz * lh * (i + 0.8), sz, c_, tf, align, alpha)
    return tot

def coin(c, x, y, r=34, rot=0.0):
    sx = abs(math.cos(rot)) * 0.85 + 0.15
    c.save(); c.translate(x, y); c.scale(sx, 1)
    circle(c, 0, 0, r, YELLOW, INK, 5); circle(c, 0, 0, r * 0.68, "#FFE680")
    text(c, "$", 0, r * 0.38, r * 1.0, "#C98B00"); c.restore()

def bill(c, x, y, w=150, h=80, rot=0):
    c.save(); c.translate(x, y); c.rotate(rot)
    rrect(c, -w / 2, -h / 2, w, h, 12, "#8FD694", INK, 5)
    circle(c, 0, 0, h * 0.28, "#5DBB63", INK, 4); text(c, "$", 0, h * 0.13, h * 0.38, INK)
    c.restore()

def check_mark(c, x, y, s, c_=GREEN, p=1.0, w=12):
    if p <= 0: return
    pts = [(x - s * 0.5, y), (x - s * 0.15, y + s * 0.35), (x + s * 0.55, y - s * 0.4)]
    path = skia.Path(); path.moveTo(*pts[0])
    l1 = math.dist(pts[0], pts[1]); l2 = math.dist(pts[1], pts[2]); L = (l1 + l2) * p
    if L <= l1:
        f = L / l1; path.lineTo(pts[0][0] + (pts[1][0] - pts[0][0]) * f, pts[0][1] + (pts[1][1] - pts[0][1]) * f)
    else:
        path.lineTo(*pts[1]); f = (L - l1) / l2
        path.lineTo(pts[1][0] + (pts[2][0] - pts[1][0]) * f, pts[1][1] + (pts[2][1] - pts[1][1]) * f)
    c.drawPath(path, paint(c_, "stroke", w))

def cross(c, x, y, s, c_=CORAL, p=1.0, w=16):
    if p <= 0: return
    a = clamp(p * 2); b = clamp(p * 2 - 1)
    line(c, x - s, y - s, x - s + 2 * s * a, y - s + 2 * s * a, c_, w)
    if b > 0: line(c, x + s, y - s, x + s - 2 * s * b, y - s + 2 * s * b, c_, w)

def pop(c, x, y, a):
    c.save(); c.translate(x, y); c.scale(a, a)

def person(c, x, y, s=1.0, t=0.0, mood="neutral", shirt=SKY, arms="down", hair=HAIR, skin=SKIN, long_hair=False):
    bob = math.sin(t * 2.2) * 6
    c.save(); c.translate(x, y + bob * 0.3); c.scale(s, s)
    line(c, -38, -150, -42, -10, INK, 30); line(c, 38, -150, 42, -10, INK, 30)
    rrect(c, -72, -22, 60, 24, 12, INK); rrect(c, 12, -22, 60, 24, 12, INK)
    if long_hair:
        rrect(c, -110, -560, 220, 230, 90, hair, INK, 7)
    rrect(c, -95, -400, 190, 270, 70, shirt, INK, 7)
    def arm(x1, y1, x2, y2):
        line(c, x1, y1, x2, y2, INK, 34); line(c, x1, y1, x2, y2, skin, 22)
    if arms == "up":
        wv = math.sin(t * 6) * 10
        arm(-85, -360, -170, -480 + wv); arm(85, -360, 170, -480 - wv)
    elif arms == "head":
        arm(-85, -360, -150, -470); arm(-150, -470, -95, -540); arm(85, -360, 150, -470); arm(150, -470, 95, -540)
    elif arms == "point":
        arm(-88, -360, -125, -200); arm(88, -360, 220, -420 + math.sin(t * 3) * 8)
    elif arms == "think":
        arm(-88, -360, -125, -200); arm(88, -360, 120, -330); arm(120, -330, 40, -440)
    else:
        sw = math.sin(t * 2.2) * 6
        arm(-88, -360, -125, -200 + sw); arm(88, -360, 125, -200 - sw)
    rrect(c, -22, -430, 44, 40, 10, skin)
    circle(c, 0, -520, 100, skin, INK, 7)
    p = skia.Path(); p.addArc(skia.Rect.MakeXYWH(-104, -624, 208, 208), 180, 180)
    p.lineTo(80, -560); p.quadTo(0, -600, -80, -560); p.close()
    c.drawPath(p, paint(hair)); c.drawPath(p, paint(INK, "stroke", 7))
    blink = (t % 3.7) < 0.12
    for ex in (-36, 36):
        if blink: line(c, ex - 10, -515, ex + 10, -515, INK, 6)
        else: circle(c, ex, -515, 10, INK)
    circle(c, -62, -480, 14, "#F7A1A1"); circle(c, 62, -480, 14, "#F7A1A1")
    mp = skia.Path()
    if mood == "happy": mp.addArc(skia.Rect.MakeXYWH(-34, -500, 68, 50), 10, 160)
    elif mood == "sad":
        mp.addArc(skia.Rect.MakeXYWH(-30, -468, 60, 40), 200, 140)
        line(c, -52, -548, -20, -540, INK, 6); line(c, 52, -548, 20, -540, INK, 6)
    elif mood == "surprised": c.drawOval(skia.Rect.MakeXYWH(-14, -480, 28, 34), paint(INK))
    else: mp.moveTo(-20, -465); mp.lineTo(20, -465)
    c.drawPath(mp, paint(INK, "stroke", 7))
    c.restore()

def bubble(c, x, y, s, a, w=520, fill=WHITE):
    if a <= 0: return
    pop(c, x, y, eo_back(a))
    f = font(44); ls = wrap(s, f, w - 70); h = 62 * len(ls) + 50
    shadow(c, -w / 2, -h / 2, w, h, 36)
    rrect(c, -w / 2, -h / 2, w, h, 36, fill, INK, 6)
    p = skia.Path(); p.moveTo(-w / 2 + 60, h / 2 - 3); p.lineTo(-w / 2 + 30, h / 2 + 50); p.lineTo(-w / 2 + 120, h / 2 - 3); p.close()
    c.drawPath(p, paint(fill)); c.drawPath(p, paint(INK, "stroke", 6))
    line(c, -w / 2 + 64, h / 2 - 3, -w / 2 + 116, h / 2 - 3, fill, 10)
    for i, l in enumerate(ls): text(c, l, 0, -h / 2 + 25 + 62 * (i + 0.8), 44, INK, TF_SEMI)
    c.restore()

def pill(c, x, y, w, h, label, fill, a=1.0, tc=WHITE, sz=44, outline=INK):
    if a <= 0: return
    pop(c, x, y, eo_back(a))
    shadow(c, -w / 2, -h / 2, w, h, h / 2)
    rrect(c, -w / 2, -h / 2, w, h, h / 2, fill, outline, 5)
    text(c, label, 0, sz * 0.36, sz, tc, maxw=w - 40)
    c.restore()

# ---------- timing helpers ----------
def reveals(sc, n, d, lo=0.12, hi=0.72):
    """When each of n items appears (scene-local seconds)."""
    p = sc.get("params", {})
    ls = sc.get("line_starts", [])
    if isinstance(p.get("at"), list) and len(p["at"]) >= n:
        return [ls[min(k, len(ls) - 1)] - sc["start"] + 0.15 if ls else d * 0.2 for k in p["at"][:n]]
    if len(ls) >= n + 1:
        return [ls[i + 1] - sc["start"] + 0.15 for i in range(n)]
    return [d * (lo + (hi - lo) * i / max(1, n - 1)) for i in range(n)] if n > 1 else [d * lo]

# ---------- templates ----------
def t_person(c, lt, d, sc, P):
    mood = P.get("mood", "neutral"); arms = P.get("arms", {"sad": "head", "happy": "up"}.get(mood, "down"))
    props = P.get("props", [])
    side = P.get("side", "left")
    px = 640 if side == "left" else 1280
    a = eo_back(prog(lt, 0.2, 0.7))
    if "confetti" in props:
        random.seed(7)
        for i in range(40):
            sx = random.uniform(200, 1800); sp = random.uniform(80, 160)
            y = ((lt * sp + random.uniform(0, 1100)) % 1200) - 100
            c.save(); c.translate(sx + math.sin(lt * 2 + i) * 20, y); c.rotate(lt * random.uniform(60, 200))
            rrect(c, -9, -5, 18, 10, 3, random.choice([CORAL, ORANGE, YELLOW, TEAL, PURPLE, SKY])); c.restore()
    pop(c, px, 850, a)
    person(c, 0, 0, 0.88, lt, mood, col(P.get("shirt"), {"sad": CORAL, "happy": GREEN}.get(mood, SKY)), arms,
           long_hair=P.get("long_hair", False))
    c.restore()
    ox = 1220 if side == "left" else 640
    if "sweat" in props and lt > 1:
        yy = 300 + ((lt * 60) % 60); sx = px + 95
        p = skia.Path(); p.moveTo(sx, yy); p.quadTo(sx + 15, yy + 30, sx, yy + 40); p.quadTo(sx - 15, yy + 30, sx, yy)
        c.drawPath(p, paint(SKY)); c.drawPath(p, paint(INK, "stroke", 4))
    if "question" in props:
        for i, (qx, qy) in enumerate([(px - 170, 280), (px + 160, 230), (px + 270, 340)]):
            qa = prog(lt, 1.5 + i * 0.4, 0.4)
            if qa > 0: text(c, "?", qx, qy + math.sin(lt * 3 + i) * 12, 110, PURPLE, alpha=255 * qa)
    if "wallet" in props:
        wa = eo_back(prog(lt, 0.8, 0.6)); pop(c, ox - 40, 700, wa)
        rrect(c, -130, -80, 260, 170, 30, "#8B5E3C", INK, 7); rrect(c, 40, -30, 110, 70, 20, "#A47148", INK, 6)
        circle(c, 95, 5, 12, YELLOW, INK, 4); c.restore()
        if "bills" in props:
            for i in range(7):
                q = (lt - 1.5 - i * 0.9) / 3.2
                if 0 < q < 1:
                    bill(c, ox - 40 + q * (500 + i * 30) * (1 if side == "left" else -1),
                         640 - q * (420 + i * 25) + math.sin(q * 8 + i) * 30, 130, 70, q * 160 * (1 if i % 2 else -1))
    elif "bills" in props or "coins" in props:
        for k in range(5):
            ph = (lt * 0.5 + k / 5) % 1
            coin(c, ox - 200 + k * 100, 150 + ph * 700, 30, ph * 8)
    if P.get("sign"):
        bubble(c, ox, 380, P["sign"], prog(lt, P.get("sign_at", d * 0.25), 0.5), 560)
    if P.get("subscribe"):
        ba = eo_back(prog(lt, d * 0.45, 0.6))
        if ba > 0:
            pul = 1 + 0.04 * math.sin(lt * 5)
            pop(c, ox, 500, ba * pul); shadow(c, -260, -75, 520, 150, 40)
            rrect(c, -260, -75, 520, 150, 40, "#FF0033", INK, 6); text(c, "SUBSCRIBE", 0, 24, 66, WHITE); c.restore()
            la = eo_back(prog(lt, d * 0.45 + 0.5, 0.5)); pop(c, ox, 720, la)
            circle(c, 0, 0, 80, WHITE, INK, 6); rrect(c, -40, -10, 22, 60, 6, SKY, INK, 4)
            p = skia.Path(); p.moveTo(-12, -10); p.lineTo(5, -55); p.quadTo(25, -60, 22, -35); p.lineTo(18, -15)
            p.lineTo(45, -15); p.quadTo(58, -12, 52, 5); p.lineTo(42, 45); p.quadTo(38, 52, 28, 52); p.lineTo(-12, 52); p.close()
            c.drawPath(p, paint(SKY)); c.drawPath(p, paint(INK, "stroke", 5)); c.restore()

def t_leak(c, lt, d, sc, P):
    labels = (P.get("labels") or ["Coffee", "Delivery", "Subscriptions"])[:3]
    a = eo_back(prog(lt, 0.2, 0.7))
    pop(c, 760, 500, a)
    p = skia.Path(); p.moveTo(-230, -200); p.lineTo(230, -200); p.lineTo(180, 230); p.lineTo(-180, 230); p.close()
    c.drawPath(p, paint(col(P.get("color"), SKY))); c.drawPath(p, paint(INK, "stroke", 8))
    rrect(c, -250, -225, 500, 50, 25, "#7FBDEB", INK, 7)
    text(c, P.get("center", "$"), 0, 80, 200 if len(P.get("center", "$")) < 3 else 90, WHITE, maxw=360)
    holes = [(-120, 120), (40, 170), (130, 60)]
    for hx, hy in holes: circle(c, hx, hy, 16, INK)
    c.restore()
    ts = reveals(sc, len(labels), d, 0.2, 0.55)
    for i, (hx, hy) in enumerate(holes[:len(labels)]):
        if lt > ts[i]:
            for k in range(4):
                ph = (lt * 0.9 + k * 0.25 + i * 0.13) % 1.0
                coin(c, 760 + hx + ph * 40 * (1 if hx > 0 else -1), 500 + hy + ph * 300, 20, ph * 6)
        pill(c, [1250, 1370, 1250][i], [320, 470, 620][i], 380, 100, labels[i], WHITE, prog(lt, ts[i], 0.5), INK, 42)
    if P.get("counter"):
        ca = prog(lt, d * 0.6, 0.5)
        pill(c, 1310, 790, 480, 110, P["counter"], CORAL, ca, WHITE, 54)

def t_phone(c, lt, d, sc, P):
    items = (P.get("items") or [])[:6]; tags = (P.get("tags") or [])[:4]
    a = eo_back(prog(lt, 0.2, 0.7))
    cx = 820 if tags else 960
    c.save(); c.translate(cx, 520); c.scale(a * 0.85, a * 0.85)
    shadow(c, -230, -400, 460, 800, 60); rrect(c, -230, -400, 460, 800, 60, INK)
    rrect(c, -205, -370, 410, 740, 40, WHITE); rrect(c, -60, -390, 120, 26, 13, INK)
    text(c, P.get("title", "My App"), 0, -300, 40, INK, maxw=360)
    ts = reveals(sc, len(items), d, 0.1, 0.55)
    for i, it in enumerate(items):
        n, v = (it + [""])[:2] if isinstance(it, list) else (it, "")
        ia = eo_cubic(prog(lt, ts[i], 0.45))
        if ia <= 0: continue
        y = -230 + i * 95
        c.save(); c.translate((1 - ia) * 120, 0)
        rrect(c, -180, y, 360, 78, 20, "#F4F2FF"); circle(c, -135, y + 39, 22, ACCENTS[i % 6])
        text(c, n, -100, y + 50, 30, INK, TF_SEMI, "left", 255 * ia, maxw=190 if v else 270)
        if v: text(c, v, 165, y + 50, 30, INK, TF_BOLD, "right", 255 * ia, maxw=110)
        c.restore()
    c.restore()
    for i, n in enumerate(tags):
        pill(c, 1340, 330 + i * 140, 360, 100, n, ACCENTS[(i + 1) % 6], prog(lt, d * 0.62 + i * 0.5, 0.5))

def t_pie(c, lt, d, sc, P):
    parts = (P.get("parts") or [[50, "Needs"], [30, "Wants"], [20, "Future"]])[:4]
    cols = [TEAL, ORANGE, PURPLE, CORAL]
    ts = reveals(sc, len(parts), d, 0.2, 0.6)
    x0, y0, R = 700, 540, 290
    a = eo_back(prog(lt, 0.2, 0.6)); pop(c, x0, y0, a)
    shadow(c, -R, -R, 2 * R, 2 * R, R); circle(c, 0, 0, R, WHITE, INK, 7)
    tot = sum(float(p[0]) for p in parts); start = -90
    for i, (pc, name) in enumerate(parts):
        sweep = 360 * float(pc) / tot * eo_cubic(prog(lt, ts[i], 1.0))
        if sweep > 0:
            path = skia.Path(); path.moveTo(0, 0)
            path.arcTo(skia.Rect.MakeXYWH(-R + 10, -R + 10, 2 * R - 20, 2 * R - 20), start, sweep, False); path.close()
            c.drawPath(path, paint(cols[i])); c.drawPath(path, paint(INK, "stroke", 6))
        start += 360 * float(pc) / tot
    circle(c, 0, 0, R * 0.45, CREAM, INK, 6); text(c, P.get("center", "100%"), 0, 22, 60, INK, maxw=R * 0.8)
    c.restore()
    for i, (pc, name) in enumerate(parts):
        la = eo_back(prog(lt, ts[i] + 0.3, 0.5))
        if la <= 0: continue
        y = 540 + (i - (len(parts) - 1) / 2) * 175
        pop(c, 1360, y, la); shadow(c, -280, -70, 560, 140)
        rrect(c, -280, -70, 560, 140, 40, WHITE, INK, 5); rrect(c, -250, -45, 160, 90, 25, cols[i], INK, 4)
        lab = P.get("unit", "%"); text(c, f"{pc}{lab}", -170, 22, 50, WHITE, maxw=140)
        text(c, name, 50, 22, 52, INK, maxw=330); c.restore()

def t_cards(c, lt, d, sc, P):
    items = (P.get("items") or [])[:6]
    price = P.get("price", "")
    n = len(items); cols_ = 3 if n > 4 else 2 if n > 1 else 1
    rows = math.ceil(n / cols_)
    ts = reveals(sc, 1, d, 0.5, 0.5)[0] if not P.get("cut_at") else P["cut_at"]
    for i, it in enumerate(items):
        name, keep = (it if isinstance(it, list) else [it, True])[:2]
        r, k = divmod(i, cols_)
        x = 960 + (k - (cols_ - 1) / 2) * 440; y = 470 + (r - (rows - 1) / 2) * 290
        a = eo_back(prog(lt, 0.3 + i * 0.25, 0.5))
        if a <= 0: continue
        cutp = 0 if keep else prog(lt, d * 0.55 + i * 0.4, 0.5)
        cc = ACCENTS[i % 6]
        pop(c, x, y, a); shadow(c, -180, -120, 360, 240, 36)
        rrect(c, -180, -120, 360, 240, 36, cc, INK, 6)
        circle(c, -110, -50, 36, WHITE, INK, 4); text(c, str(name)[0].upper(), -110, -36, 40, cc)
        text(c, name, 0, 60, 42, WHITE, maxw=320)
        if price: text(c, price, 70, -38, 30, WHITE, TF_SEMI, maxw=180)
        if cutp > 0.5:
            rrect(c, -180, -120, 360, 240, 36, skia.Color(255, 255, 255, int(120 * clamp((cutp - 0.5) * 2))))
        cross(c, 0, 0, 80, CORAL, cutp, 22)
        if keep and P.get("check_keep"): check_mark(c, 120, 60, 50, WHITE, prog(lt, d * 0.55, 0.4), 12)
        c.restore()
    if P.get("result"):
        pill(c, 960, 840, 560, 100, P["result"], GREEN, prog(lt, d * 0.8, 0.5), WHITE, 48)

def t_jar(c, lt, d, sc, P):
    """Piggy bank filling toward a goal."""
    a = eo_back(prog(lt, 0.2, 0.7)); pop(c, 720, 580, a)
    shadow(c, -250, -180, 500, 360, 180)
    for f_, s_ in ((paint(PINK if P.get("color") is None else col(P.get("color"))), None),):
        pass
    pc = "#FFB3C6"
    c.drawOval(skia.Rect.MakeXYWH(-250, -190, 500, 380), paint(pc)); c.drawOval(skia.Rect.MakeXYWH(-250, -190, 500, 380), paint(INK, "stroke", 8))
    for lx in (-150, -60, 60, 150): rrect(c, lx - 28, 150, 56, 90, 20, pc, INK, 6)
    c.drawOval(skia.Rect.MakeXYWH(-310, -50, 110, 90), paint(PINK)); c.drawOval(skia.Rect.MakeXYWH(-310, -50, 110, 90), paint(INK, "stroke", 6))
    circle(c, -272, -5, 9, INK); circle(c, -238, -5, 9, INK); circle(c, -160, -80, 13, INK)
    p = skia.Path(); p.moveTo(-120, -175); p.lineTo(-170, -260); p.lineTo(-60, -195); p.close()
    c.drawPath(p, paint(PINK)); c.drawPath(p, paint(INK, "stroke", 6)); rrect(c, -50, -195, 120, 22, 11, INK)
    c.restore()
    if lt > 1.2:
        for k in range(3):
            ph = ((lt - 1.2) * 0.8 + k / 3) % 1; coin(c, 730, 140 + ph * 260, 38, ph * 9)
    goal = float(P.get("goal", 1000)); pre = P.get("prefix", "$"); suf = P.get("suffix", "")
    if prog(lt, 2.5, 0.5) > 0:
        fill = clamp((lt - 3) / (d * 0.7)); x, y, w = 1150, 480, 580
        text(c, P.get("label", "Savings"), x + w / 2, y - 40, 48, INK, maxw=w)
        rrect(c, x, y, w, 80, 40, WHITE, INK, 6)
        if fill > 0.04: rrect(c, x + 8, y + 8, (w - 16) * fill, 64, 32, GREEN)
        text(c, f"{pre}{int(fill * goal):,}{suf} / {pre}{int(goal):,}{suf}", x + w / 2, y + 160, 54, INK, maxw=w)
    sa = eo_back(prog(lt, d * 0.8, 0.5))
    if sa > 0:
        pop(c, 1440, 800, sa)
        p = skia.Path(); p.moveTo(0, -90); p.lineTo(80, -60); p.quadTo(80, 50, 0, 100); p.quadTo(-80, 50, -80, -60); p.close()
        c.drawPath(p, paint(TEAL)); c.drawPath(p, paint(INK, "stroke", 7)); check_mark(c, 0, 5, 70, WHITE, 1, 14); c.restore()

def t_snowball(c, lt, d, sc, P):
    items = (P.get("items") or [["Card", "$400"], ["Loan", "$1,200"], ["Car", "$3,500"]])[:3]
    GY = 840
    p = skia.Path(); p.moveTo(0, 330); p.quadTo(650, 360, 1150, GY); p.lineTo(1920, GY); p.lineTo(1920, 1080); p.lineTo(0, 1080); p.close()
    c.drawPath(p, paint(WHITE)); c.drawPath(p, paint(INK, "stroke", 6))
    t1, t2, t3 = 1.0, d * 0.35, d * 0.85
    if lt < t2:
        u = clamp((lt - t1) / (t2 - t1))
        x = (1 - u) ** 2 * 60 + 2 * (1 - u) * u * 650 + u * u * 1150
        y = (1 - u) ** 2 * 330 + 2 * (1 - u) * u * 360 + u * u * GY; grow = u * 0.45
    else:
        u = clamp((lt - t2) / (t3 - t2)); x = 1150 + u * 650; y = GY; grow = 0.45 + 0.55 * u
    r = 40 + 100 * grow
    for i, it in enumerate(items):
        n, v = (it + [""])[:2] if isinstance(it, list) else (it, "")
        a = eo_back(prog(lt, 0.5 + i * 0.4, 0.5))
        if a <= 0: continue
        bx = 1330 + i * 190; hgt = 190 + i * 80
        th = t2 + (t3 - t2) * clamp((bx - 70 - 1150) / 650)
        sh = 1 - eo_cubic(prog(lt, th, 0.35))
        if sh > 0:
            c.save(); c.translate(bx, GY); c.scale(a * sh, a * sh)
            rrect(c, -70, -hgt, 140, hgt, 20, [CORAL, ORANGE, PURPLE][i], INK, 6)
            text(c, n, 0, -hgt + 60, 36, WHITE, maxw=125); text(c, v, 0, -hgt + 110, 32, WHITE, TF_SEMI, maxw=125); c.restore()
        cp = prog(lt, th + 0.3, 0.4)
        if cp > 0: circle(c, bx, GY - 110, 60 * eo_back(cp), WHITE, GREEN, 8); check_mark(c, bx, GY - 110, 55, GREEN, cp, 12)
    circle(c, x, y - r + 6, r, "#F4FAFF", INK, 7)
    for k in range(3):
        ang = lt * 4 + k * 2.1
        circle(c, x + math.cos(ang) * r * 0.5, y - r + 6 + math.sin(ang) * r * 0.5, r * 0.12, "#CFE6F7")

def gear(c, x, y, r, teeth, rot, c_):
    c.save(); c.translate(x, y); c.rotate(rot); p = skia.Path()
    for i in range(teeth * 2):
        ang = math.pi * i / teeth; rr = r if i % 2 == 0 else r * 0.8
        a1 = ang - math.pi / teeth / 2; a2 = ang + math.pi / teeth / 2
        (p.moveTo if i == 0 else p.lineTo)(math.cos(a1) * rr, math.sin(a1) * rr); p.lineTo(math.cos(a2) * rr, math.sin(a2) * rr)
    p.close(); c.drawPath(p, paint(c_)); c.drawPath(p, paint(INK, "stroke", 6)); circle(c, 0, 0, r * 0.32, CREAM, INK, 6); c.restore()

def t_flow(c, lt, d, sc, P):
    src = P.get("source", "PAYDAY"); targets = (P.get("targets") or ["Savings", "Debt", "Bills"])[:3]
    a = eo_back(prog(lt, 0.2, 0.6)); pop(c, 380, 540, a); shadow(c, -150, -110, 300, 220, 40)
    rrect(c, -150, -110, 300, 220, 40, YELLOW, INK, 7); text(c, src, 0, -20, 48, INK, maxw=260)
    text(c, P.get("source_icon", "$"), 0, 70, 80, "#C98B00"); c.restore()
    ga = eo_back(prog(lt, 0.8, 0.6))
    if ga > 0: pop(c, 860, 540, ga); gear(c, -50, -40, 110, 10, lt * 40, PURPLE); gear(c, 110, 90, 75, 8, -lt * 58 + 10, TEAL); c.restore()
    ts = reveals(sc, len(targets), d, 0.25, 0.55)
    ys = [280, 540, 800][:len(targets)] if len(targets) == 3 else [380, 700][:len(targets)]
    for i, n in enumerate(targets):
        if lt < ts[i]: continue
        y = ys[i]; line(c, 1010, 540, 1300, y, skia.Color(31, 42, 68, 70), 10)
        ph = (lt * 0.6 + i * 0.33) % 1; coin(c, 1010 + 290 * ph, 540 + (y - 540) * ph, 22, ph * 8)
        pill(c, 1520, y, 420, 150, n, [GREEN, CORAL, SKY][i], prog(lt, ts[i], 0.5), WHITE, 54)
    if lt > 1.0:
        line(c, 540, 540, 740, 540, skia.Color(31, 42, 68, 70), 10); ph = (lt * 0.7) % 1; coin(c, 540 + 200 * ph, 540, 24, ph * 8)

def t_growth(c, lt, d, sc, P):
    vals = P.get("bars") or [0.25, 0.38, 0.5, 0.7, 0.95]; items = (P.get("items") or [])[:3]
    mx = max(vals); vals = [v / mx * 0.95 for v in vals]
    labels = P.get("bar_labels") or []
    nb = len(vals); base = 860; x0 = 330 if items else 560; sp = min(165, 800 / nb)
    line(c, x0 - 40, base, x0 + sp * nb + 20, base, INK, 8)
    for i, v in enumerate(vals):
        h = 520 * v * eo_cubic(prog(lt, 0.6 + i * 0.5, 0.8))
        if h > 2: rrect(c, x0 + i * sp, base - h, sp * 0.73, h, 18, ACCENTS[i % 6], INK, 6)
        if i < len(labels): text(c, labels[i], x0 + i * sp + sp * 0.36, base + 50, 30, INK, TF_SEMI, maxw=sp)
    ap = eo_cubic(prog(lt, 0.6 + nb * 0.5, 1.2))
    if ap > 0 and P.get("arrow", True):
        pts = [(x0 + sp * 0.36 + i * sp, base - 520 * v - 50) for i, v in enumerate(vals)]
        path = skia.Path(); path.moveTo(*pts[0]); n = ap * (len(pts) - 1)
        for i in range(1, len(pts)):
            if i <= n: path.lineTo(*pts[i])
            else:
                f = n - (i - 1); px, py = pts[i - 1]; qx, qy = pts[i]; path.lineTo(px + (qx - px) * f, py + (qy - py) * f); break
        c.drawPath(path, paint(CORAL, "stroke", 14))
        if ap >= 1:
            ex, ey = pts[-1]; hp = skia.Path(); hp.moveTo(ex + 40, ey - 40); hp.lineTo(ex - 15, ey - 35); hp.lineTo(ex + 35, ey + 15); hp.close()
            c.drawPath(hp, paint(CORAL))
    ts = reveals(sc, len(items), d, 0.35, 0.7)
    for i, s in enumerate(items):
        ia = eo_back(prog(lt, ts[i], 0.5))
        if ia <= 0: continue
        pop(c, 1500, 380 + i * 180, ia); shadow(c, -260, -60, 520, 120)
        rrect(c, -260, -60, 520, 120, 60, WHITE, INK, 5); circle(c, -200, 0, 34, [ORANGE, PURPLE, TEAL][i])
        text(c, str(i + 1), -200, 15, 40, WHITE); text(c, s, 30, 15, 40, INK, TF_SEMI, maxw=380); c.restore()

def t_checklist(c, lt, d, sc, P):
    items = (P.get("items") or [])[:5]; n = len(items)
    ts = reveals(sc, n, d, 0.15, 0.75)
    hgt = 165 if n <= 4 else 140
    y0 = 520 - (n - 1) * hgt / 2
    for i, it in enumerate(items):
        tag, desc = (it + [""])[:2] if isinstance(it, list) else ("", it)
        y = y0 + i * hgt
        a = eo_cubic(prog(lt, 0.3 + i * 0.2, 0.5))
        if a <= 0: continue
        c.save(); c.translate((1 - a) * -200, 0)
        shadow(c, 340, y - 60, 1240, 120, 34); rrect(c, 340, y - 60, 1240, 120, 34, WHITE, INK, 5)
        rrect(c, 375, y - 40, 80, 80, 20, WHITE, INK, 6)
        tx = 490
        if tag:
            rrect(c, 490, y - 38, 210, 76, 38, ACCENTS[i % 6]); text(c, tag, 595, y + 14, 36, WHITE, maxw=190); tx = 730
        text(c, desc, tx, y + 16, 44, INK, TF_SEMI, "left", maxw=1560 - tx)
        check_mark(c, 415, y, 60, GREEN, prog(lt, ts[i] + 0.4, 0.5), 14)
        c.restore()

def t_list(c, lt, d, sc, P):
    """Numbered key points with a character pointing at them."""
    items = (P.get("items") or [])[:5]; n = len(items)
    ts = reveals(sc, n, d, 0.12, 0.7)
    a = eo_back(prog(lt, 0.2, 0.6))
    pop(c, 370, 860, a); person(c, 0, 0, 0.78, lt, P.get("mood", "happy"), col(P.get("shirt"), PURPLE), "point",
                               long_hair=P.get("long_hair", True)); c.restore()
    hgt = 160 if n <= 4 else 132
    y0 = 520 - (n - 1) * hgt / 2
    for i, s in enumerate(items):
        ia = eo_back(prog(lt, ts[i], 0.5))
        if ia <= 0: continue
        y = y0 + i * hgt; cc = ACCENTS[i % 6]
        c.save(); c.translate(1180, y); c.scale(ia, ia)
        shadow(c, -500, -hgt * 0.4, 1000, hgt * 0.8, 40)
        rrect(c, -500, -hgt * 0.4, 1000, hgt * 0.8, 40, WHITE, INK, 5)
        circle(c, -430, 0, hgt * 0.27, cc, INK, 4); text(c, str(i + 1), -430, hgt * 0.1, hgt * 0.3, WHITE)
        text(c, s, -360, 15, 44, INK, TF_SEMI, "left", maxw=830)
        c.restore()

def t_stat(c, lt, d, sc, P):
    val = float(P.get("value", 100)); pre = P.get("prefix", ""); suf = P.get("suffix", "")
    dec = int(P.get("decimals", 0)); cap = P.get("caption", "")
    a = eo_back(prog(lt, 0.2, 0.6))
    cur = val * eo_cubic(prog(lt, 0.4, max(1.5, d * 0.3)))
    s = f"{pre}{cur:,.{dec}f}{suf}"
    rays = col(P.get("color"), ORANGE)
    c.save(); c.translate(960, 470); c.rotate(lt * 8)
    for k in range(12):
        c.save(); c.rotate(k * 30)
        p = skia.Path(); p.moveTo(0, 0); p.lineTo(-60, -900); p.lineTo(60, -900); p.close()
        pp = paint(rays); pp.setAlpha(40); c.drawPath(p, pp); c.restore()
    c.restore()
    pop(c, 960, 470, a)
    shadow(c, -560, -190, 1120, 380, 60)
    rrect(c, -560, -190, 1120, 380, 60, WHITE, INK, 8)
    text(c, s, 0, 75, 210, rays, maxw=1000)
    c.restore()
    if cap:
        ca = prog(lt, 1.0, 0.5)
        text_block(c, cap, 960, 790, 54, 1400, INK, TF_BOLD, alpha=255 * ca, maxlines=2)

def t_compare(c, lt, d, sc, P):
    L = (P.get("left") or [])[:4]; R = (P.get("right") or [])[:4]
    lt_t = P.get("left_title", "Instead of"); rt_t = P.get("right_title", "Do this")
    tl = reveals(sc, len(L) + len(R), d, 0.12, 0.75)
    for side, (title, items, cc, x) in enumerate([(lt_t, L, CORAL, 520), (rt_t, R, GREEN, 1400)]):
        a = eo_back(prog(lt, 0.2 + side * 0.3, 0.6))
        if a <= 0: continue
        pop(c, x, 520, a)
        shadow(c, -400, -360, 800, 720, 50); rrect(c, -400, -360, 800, 720, 50, WHITE, INK, 6)
        rrect(c, -400, -360, 800, 130, 50, cc, INK, 6); rrect(c, -397, -280, 794, 50, 0, cc)
        line(c, -400, -230, 400, -230, INK, 6)
        text(c, title, 0, -270, 56, WHITE, maxw=720)
        n = len(items); hh = 540 / max(n, 1)
        for i, s in enumerate(items):
            idx = i if side == 0 else len(L) + i
            ia = prog(lt, tl[idx] if P.get("interleave") is None else tl[idx], 0.4)
            if ia <= 0: continue
            y = -230 + hh * (i + 0.5)
            if side == 0: cross(c, -330, y, 22, CORAL, ia, 10)
            else: check_mark(c, -330, y, 50, GREEN, ia, 10)
            text(c, s, -280, y + 15, 42, INK, TF_SEMI, "left", 255 * ia, maxw=640)
        c.restore()
    va = eo_back(prog(lt, 0.6, 0.5))
    if va > 0: pop(c, 960, 520, va); circle(c, 0, 0, 70, YELLOW, INK, 6); text(c, "VS", 0, 20, 52, INK); c.restore()

def t_quote(c, lt, d, sc, P):
    q = P.get("text", ""); au = P.get("author", "")
    a = eo_back(prog(lt, 0.2, 0.6)); pop(c, 960, 500, a)
    shadow(c, -720, -280, 1440, 560, 50); rrect(c, -720, -280, 1440, 560, 50, WHITE, INK, 7)
    text(c, "“", -620, -80, 300, col(P.get("color"), ORANGE))
    c.restore()
    if a > 0.9:
        n = int(len(q) * clamp((lt - 0.6) / max(1.5, min(d * 0.5, len(q) * 0.05))))
        text_block(c, q[:n], 990, 480, 64, 1180, INK, TF_BOLD, maxlines=4)
        if au: text(c, "— " + au, 1580, 730, 44, "#5A6478", TF_SEMI, "right", 255 * prog(lt, d * 0.5, 0.5), maxw=900)

def t_timeline(c, lt, d, sc, P):
    steps = (P.get("steps") or [])[:5]; n = len(steps)
    ts = reveals(sc, n, d, 0.12, 0.75)
    x0, x1, y = 260, 1660, 520
    sp = (x1 - x0) / max(1, n - 1)
    pr = clamp((lt - 0.4) / max(1, ts[-1] - 0.4 + 0.5)) if n else 0
    line(c, x0, y, x1, y, skia.Color(31, 42, 68, 50), 18)
    line(c, x0, y, x0 + (x1 - x0) * pr, y, CORAL, 18)
    for i, st in enumerate(steps):
        lab, desc = (st + [""])[:2] if isinstance(st, list) else (st, "")
        x = x0 + sp * i; a = eo_back(prog(lt, ts[i], 0.5))
        circle(c, x, y, 34, WHITE, INK, 6)
        if a <= 0: continue
        pop(c, x, y, a); circle(c, 0, 0, 52, ACCENTS[i % 6], INK, 6); text(c, str(i + 1), 0, 20, 52, WHITE); c.restore()
        up = i % 2 == 0; cy = y - 210 if up else y + 210
        w = min(380, sp * 1.8)
        pop(c, x, cy, a); shadow(c, -w / 2, -95, w, 190, 30); rrect(c, -w / 2, -95, w, 190, 30, WHITE, INK, 5)
        text(c, lab, 0, -30, 40, ACCENTS[i % 6], maxw=w - 30)
        if desc: text_block(c, desc, 0, 35, 32, w - 40, INK, TF_SEMI, maxlines=2)
        c.restore()
        line(c, x, y + (-52 if up else 52), x, cy + (95 if up else -95), INK, 5)

def t_calendar(c, lt, d, sc, P):
    days = int(P.get("days", 30)); title = P.get("title", "30-Day Challenge")
    a = eo_back(prog(lt, 0.2, 0.6)); pop(c, 760, 520, a)
    cols_ = 7; rows = math.ceil(days / cols_); cs = 88
    w = cols_ * cs + 80; h = rows * cs + 200
    shadow(c, -w / 2, -h / 2, w, h, 40); rrect(c, -w / 2, -h / 2, w, h, 40, WHITE, INK, 7)
    rrect(c, -w / 2, -h / 2, w, 120, 40, CORAL, INK, 7); rrect(c, -w / 2 + 3, -h / 2 + 60, w - 6, 57, 0, CORAL)
    line(c, -w / 2, -h / 2 + 120, w / 2, -h / 2 + 120, INK, 7)
    text(c, title, 0, -h / 2 + 80, 48, WHITE, maxw=w - 60)
    filled = int(days * clamp((lt - 1) / (d * 0.7)))
    for i in range(days):
        r, k = divmod(i, cols_); x = -w / 2 + 40 + k * cs + cs / 2; y = -h / 2 + 160 + r * cs + cs / 2
        rrect(c, x - 36, y - 36, 72, 72, 16, "#F4F2FF")
        if i < filled: rrect(c, x - 36, y - 36, 72, 72, 16, GREEN); check_mark(c, x, y, 40, WHITE, 1, 8)
        else: text(c, str(i + 1), x, y + 11, 30, "#8A93A8", TF_SEMI)
    c.restore()
    pa = eo_back(prog(lt, 0.8, 0.6)); pop(c, 1480, 860, pa)
    person(c, 0, 0, 0.7, lt, "happy", col(P.get("shirt"), TEAL), "up" if filled > days * 0.6 else "down"); c.restore()
    if P.get("badge"):
        pill(c, 1480, 230, 520, 110, P["badge"], ORANGE, prog(lt, d * 0.6, 0.5), WHITE, 46)

def t_balance(c, lt, d, sc, P):
    l = P.get("left", "Income"); r = P.get("right", "Expenses"); heavy = P.get("heavy", "right")
    target = (-10 if heavy == "left" else 10) * eo_cubic(prog(lt, d * 0.3, 1.2))
    wob = math.sin(lt * 2) * 1.2
    a = eo_back(prog(lt, 0.2, 0.6)); pop(c, 960, 400, a)
    p = skia.Path(); p.moveTo(-140, 330); p.lineTo(140, 330); p.lineTo(0, 0); p.close()
    c.drawPath(p, paint("#8B5E3C")); c.drawPath(p, paint(INK, "stroke", 7))
    c.save(); c.rotate(target + wob)
    rrect(c, -560, -18, 1120, 36, 18, "#A47148", INK, 6); circle(c, 0, 0, 30, YELLOW, INK, 6)
    for side, lab, cc, big in ((-1, l, GREEN, heavy == "left"), (1, r, CORAL, heavy == "right")):
        x = side * 470
        c.save(); c.translate(x, 0); c.rotate(-(target + wob))
        line(c, -110, 200, 0, 0, INK, 5); line(c, 110, 200, 0, 0, INK, 5)
        pth = skia.Path(); pth.moveTo(-170, 200); pth.lineTo(170, 200); pth.quadTo(150, 270, 0, 270); pth.quadTo(-150, 270, -170, 200); pth.close()
        c.drawPath(pth, paint("#D9D9E3")); c.drawPath(pth, paint(INK, "stroke", 6))
        nco = 6 if big else 3
        for k in range(nco): coin(c, -90 + (k % 3) * 90, 160 - (k // 3) * 55, 34)
        rrect(c, -170, 300, 340, 90, 45, cc, INK, 5); text(c, lab, 0, 362, 44, WHITE, maxw=300)
        c.restore()
    c.restore(); c.restore()
    if P.get("caption"):
        pill(c, 960, 225, 1000, 100, P["caption"], INK, prog(lt, d * 0.55, 0.5), WHITE, 44, None)

def t_clock(c, lt, d, sc, P):
    """Big clock with ticking hands + up to 3 time-blocked items."""
    items = (P.get("items") or [])[:4]
    a = eo_back(prog(lt, 0.2, 0.6)); pop(c, 620, 520, a)
    shadow(c, -300, -300, 600, 600, 300); circle(c, 0, 0, 300, WHITE, INK, 9)
    for k in range(12):
        ang = k * math.pi / 6; line(c, math.sin(ang) * 250, -math.cos(ang) * 250, math.sin(ang) * 275, -math.cos(ang) * 275, INK, 9)
    m = lt * 60; hh = lt * 5
    line(c, 0, 0, math.sin(math.radians(hh)) * 150, -math.cos(math.radians(hh)) * 150, INK, 18)
    line(c, 0, 0, math.sin(math.radians(m)) * 230, -math.cos(math.radians(m)) * 230, CORAL, 12)
    circle(c, 0, 0, 22, YELLOW, INK, 6); c.restore()
    ts = reveals(sc, len(items), d, 0.15, 0.7)
    for i, it in enumerate(items):
        tm, lab = (it + [""])[:2] if isinstance(it, list) else ("", it)
        ia = eo_back(prog(lt, ts[i], 0.5))
        if ia <= 0: continue
        y = 520 + (i - (len(items) - 1) / 2) * 165
        pop(c, 1380, y, ia); shadow(c, -340, -60, 680, 120, 34); rrect(c, -340, -60, 680, 120, 34, WHITE, INK, 5)
        if tm:
            rrect(c, -320, -42, 200, 84, 30, ACCENTS[i % 6]); text(c, tm, -220, 14, 36, WHITE, maxw=180)
        text(c, lab, -90 if tm else -300, 15, 40, INK, TF_SEMI, "left", maxw=410 if tm else 620); c.restore()

TEMPLATES = {"person": t_person, "leak": t_leak, "phone": t_phone, "pie": t_pie, "cards": t_cards, "jar": t_jar,
             "snowball": t_snowball, "flow": t_flow, "growth": t_growth, "checklist": t_checklist, "list": t_list,
             "stat": t_stat, "compare": t_compare, "quote": t_quote, "timeline": t_timeline, "calendar": t_calendar,
             "balance": t_balance, "clock": t_clock}

# ---------- frame composition ----------
class Video:
    def __init__(self, wd):
        self.TL = json.load(open(f"{wd}/timeline.json"))
        seed = int(hashlib.md5(self.TL.get("title", "x").encode()).hexdigest(), 16)
        rnd = random.Random(seed); pairs = BG_PAIRS[:]; rnd.shuffle(pairs)
        for i, s in enumerate(self.TL["scenes"]):
            s["bg"] = pairs[i % len(pairs)]

    def background(self, c, sc, t):
        top, bot = sc["bg"]
        c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=skia.GradientShader.MakeLinear([(0, 0), (0, H)], [C(top), C(bot)])))
        for i, (bx, by, br) in enumerate([(200, 200, 160), (1750, 260, 200), (1650, 950, 140), (150, 900, 120)]):
            c.drawCircle(bx + math.sin(t * 0.4 + i) * 25, by + math.cos(t * 0.35 + i * 2) * 20, br, paint(skia.Color(255, 255, 255, 70)))

    def heading(self, c, s, lt):
        if not s: return
        a = eo_cubic(prog(lt, 0.15, 0.5)); sz = fit(s, 46, 1500)
        w = font(sz).measureText(s) + 80; x = 60 - (1 - a) * (w + 80)
        shadow(c, x, 50, w, 90, 45, 30); rrect(c, x, 50, w, 90, 45, INK)
        text(c, s, x + 40, 111, sz, WHITE, TF_BOLD, "left")

    def subtitle(self, c, sub, t):
        if not sub: return
        a = clamp((t - sub["start"]) / 0.12) * clamp((sub["end"] + 0.15 - t) / 0.12)
        if a <= 0: return
        f = font(58); ls = wrap(sub["text"], f, 1500); lh = 76
        bw = max(f.measureText(l) for l in ls) + 90; bh = lh * len(ls) + 40
        x = (W - bw) / 2; y = H - 70 - bh
        rrect(c, x, y, bw, bh, 28, skia.Color(20, 24, 38, int(215 * a)))
        for i, l in enumerate(ls): text(c, l, W / 2, y + 20 + lh * (i + 1) - 18, 58, WHITE, TF_BOLD, "center", 255 * a)

    def frame(self, c, t):
        S = self.TL["scenes"]
        si = 0
        for i, s in enumerate(S):
            if t >= s["start"]: si = i
        sc = S[si]; lt = t if si == 0 else t - sc["start"]; d = sc["end"] - sc["start"]
        self.background(c, sc, t)
        TEMPLATES.get(sc["visual"], t_list)(c, lt, d, sc, sc.get("params", {}))
        self.heading(c, sc.get("heading", ""), lt)
        cur = None
        for s in sc["subs"]:
            if s["start"] - 0.05 <= t <= s["end"] + 0.15: cur = s
        self.subtitle(c, cur, t)
        c.drawRect(skia.Rect.MakeXYWH(0, 0, W, 8), paint(skia.Color(31, 42, 68, 40)))
        c.drawRect(skia.Rect.MakeXYWH(0, 0, W * t / self.TL["duration"], 8), paint(CORAL))
        if si > 0 and lt < 0.45:
            k = eo_cubic(lt / 0.45)
            c.drawRect(skia.Rect.MakeXYWH(W * k, 0, W, H), paint(C(S[si - 1]["bg"][1])))
            c.drawRect(skia.Rect.MakeXYWH(W * k - 30, 0, 30, H), paint(INK))

def main():
    wd, t0, t1, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    V = Video(wd)
    info = skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
    surf = skia.Surface.MakeRaster(info)
    if out.endswith(".png") or out.endswith(".jpg"):
        c = surf.getCanvas(); c.clear(skia.ColorWHITE); V.frame(c, t0); surf.makeImageSnapshot().save(out, skia.kPNG); return
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                           "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    n0, n1 = round(t0 * FPS), round(t1 * FPS)
    buf = np.empty((H, W, 4), np.uint8)
    for n in range(n0, n1):
        c = surf.getCanvas(); c.clear(skia.ColorWHITE); V.frame(c, n / FPS)
        surf.readPixels(info, buf, W * 4); ff.stdin.write(buf.tobytes())
        if (n - n0) % 480 == 0: print(out, n, "/", n1, flush=True)
    ff.stdin.close(); ff.wait()

if __name__ == "__main__":
    main()
