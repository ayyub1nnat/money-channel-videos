"""Whiteboard / hand-drawn explainer renderer ("style": "sketch" in script.json).
Every narration line draws a new doodle (icon + handwritten label, or a big handwritten number) traced
by a drawing hand, with line-boil wobble, a gently following camera and page flips between scenes.
Usage: python3 sketch.py <workdir> <t0> <t1> <out.mp4|out.png>   (needs timeline.json from tts.py)
       python3 sketch.py <workdir> --pencil   → writes pencil.wav (scribble sound under each drawing)"""
import json, math, sys, os, re, random, subprocess
import numpy as np
import skia
from svg.path import parse_path, Move, Line, CubicBezier, QuadraticBezier, Arc, Close
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sketch_icons import ICONS, KEYWORDS

W, H, FPS = 1920, 1080, 24
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIRS = [os.path.join(HERE, "fonts"), "/home/claude/fonts"]
def _font_file(name):
    for d in FONT_DIRS:
        if os.path.exists(os.path.join(d, name)): return os.path.join(d, name)
    raise FileNotFoundError(name)
TF_HAND = skia.Typeface.MakeFromFile(_font_file("Kalam-Bold.ttf"))
TF_SUB = skia.Typeface.MakeFromFile("/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf") or TF_HAND
INK = skia.Color(34, 34, 40)
ACC = ["#FF6B6B", "#2EC4B6", "#FFB627", "#5DA9E9", "#9B5DE5", "#3BB273"]

def C(h, a=255):
    h = h.lstrip("#"); return skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3

def stroke_paint(color=INK, w=6.0, alpha=255):
    p = skia.Paint(AntiAlias=True, Color=color, Style=skia.Paint.kStroke_Style, StrokeWidth=w,
                   StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)
    p.setAlpha(int(alpha)); return p
def fill_paint(color, alpha=255):
    p = skia.Paint(AntiAlias=True, Color=color); p.setAlpha(int(alpha)); return p

# ---------- geometry ----------
def svg_to_paths(d, scale, ox, oy, jitter=0.0, rnd=None):
    """SVG d → list of skia.Path contours (one per subpath), placed at (ox, oy), scaled from the 100-box."""
    out, cur = [], None
    def P(z):
        x, y = z.real, z.imag
        if jitter and rnd: x += rnd.uniform(-jitter, jitter); y += rnd.uniform(-jitter, jitter)
        return ox + x * scale, oy + y * scale
    for seg in parse_path(d):
        if isinstance(seg, Move):
            if cur is not None and cur.countPoints() > 1: out.append(cur)
            cur = skia.Path(); cur.moveTo(*P(seg.end))
        elif isinstance(seg, Line): cur.lineTo(*P(seg.end))
        elif isinstance(seg, CubicBezier): cur.cubicTo(*P(seg.control1), *P(seg.control2), *P(seg.end))
        elif isinstance(seg, QuadraticBezier): cur.quadTo(*P(seg.control), *P(seg.end))
        elif isinstance(seg, Arc):
            for i in range(1, 25): cur.lineTo(*P(seg.point(i / 24)))
        elif isinstance(seg, Close): cur.close()
    if cur is not None and cur.countPoints() > 1: out.append(cur)
    return out

def text_paths(text, size, x, y, align="center", maxw=None):
    """Handwritten text as glyph outline contours (traced) + one fill path. Returns (contours, fill, width)."""
    while True:
        f = skia.Font(TF_HAND, size)
        w = f.measureText(text)
        if not maxw or w <= maxw or size <= 22: break
        size -= 3
    if align == "center": x -= w / 2
    elif align == "right": x -= w
    glyphs = f.textToGlyphs(text); pos = f.getPos(glyphs)
    fill = skia.Path(); contours = []
    for g, p in zip(glyphs, pos):
        gp = f.getPath(g)
        if gp is None or gp.countPoints() == 0: continue
        gp = skia.Path(gp); gp.transform(skia.Matrix.Translate(x + p.x(), y))
        fill.addPath(gp)
        it = skia.PathMeasure(gp, False)
        while True:
            seg = skia.Path()
            if it.getLength() > 0.5 and it.getSegment(0, it.getLength(), seg, True): contours.append(seg)
            if not it.nextContour(): break
    return contours, fill, w, size

class Stroke:
    def __init__(self, path):
        self.path = path; self.m = skia.PathMeasure(path, False); self.L = max(0.01, self.m.getLength())
    def partial(self, frac):
        seg = skia.Path(); self.m.getSegment(0, self.L * clamp(frac), seg, True); return seg
    def tip(self, frac):
        r = self.m.getPosTan(self.L * clamp(frac))
        pos = r[0] if isinstance(r, tuple) else r
        try: return pos.x(), pos.y()
        except Exception: return pos.fX, pos.fY

class Drawing:
    """An ordered set of strokes drawn over [t0, t1], then optional fills fade in, then text."""
    def __init__(self, strokes, t0, t1, width=6.0, color=INK, fills=None, fill_color=None, center=(960, 540), text_fill=None, text_color=INK):
        self.strokes = [Stroke(p) for p in strokes]; self.t0, self.t1 = t0, t1
        self.w, self.color = width, color; self.fills = fills or []; self.fill_color = fill_color
        self.total = sum(s.L for s in self.strokes) or 1; self.center = center
        self.text_fill, self.text_color = text_fill, text_color
        self.seed = random.random() * 1000
    def progress(self, t): return clamp((t - self.t0) / max(0.05, self.t1 - self.t0))
    def draw(self, c, t, boil):
        p = self.progress(t)
        if p <= 0: return None
        c.save()
        if boil:  # line boil: tiny jitter that changes every 3 frames → hand-drawn life
            k = int(t * FPS / 3); r = random.Random(self.seed + k)
            cx, cy = self.center; c.translate(cx, cy); c.rotate(r.uniform(-0.35, 0.35)); c.translate(-cx + r.uniform(-1.2, 1.2), -cy + r.uniform(-1.2, 1.2))
        fa = clamp((t - self.t1) / 0.35)
        if fa > 0 and self.fills and self.fill_color is not None:
            for fp in self.fills: c.drawPath(fp, fill_paint(self.fill_color, 110 * fa))
        if fa > 0 and self.text_fill is not None:
            c.drawPath(self.text_fill, fill_paint(self.text_color, 255 * fa))
        target = p * self.total; acc = 0; tip = None
        for s in self.strokes:
            if acc >= target: break
            if acc + s.L <= target:
                c.drawPath(s.path, stroke_paint(self.color, self.w, 255 if self.text_fill is None else 255 * (1 - 0.6 * fa)))
            else:
                fr = (target - acc) / s.L
                c.drawPath(s.partial(fr), stroke_paint(self.color, self.w)); tip = s.tip(fr)
            acc += s.L
        c.restore()
        return tip if p < 1 else None

# ---------- hand ----------
def draw_hand(c, x, y, t):
    c.save(); c.translate(x, y); c.scale(1.35, 1.35); c.rotate(-28 + math.sin(t * 9) * 2)
    skin, sleeve = C("#F2C29B"), C("#5DA9E9")
    # pencil (tip at 0,0)
    p = skia.Path(); p.moveTo(0, 0); p.lineTo(-7, 22); p.lineTo(7, 22); p.close(); c.drawPath(p, fill_paint(C("#F5DEB3")))
    p = skia.Path(); p.moveTo(-2.5, 7); p.lineTo(2.5, 7); p.lineTo(0, 0); p.close(); c.drawPath(p, fill_paint(INK))
    c.drawRect(skia.Rect.MakeLTRB(-7, 22, 7, 150), fill_paint(C("#FFC93C")))
    c.drawRect(skia.Rect.MakeLTRB(-7, 22, 7, 150), stroke_paint(INK, 2.5))
    c.drawRect(skia.Rect.MakeLTRB(-7, 150, 7, 168), fill_paint(C("#FF8FAB")))
    # hand
    c.drawOval(skia.Rect.MakeLTRB(-18, 70, 62, 150), fill_paint(skin))
    c.drawOval(skia.Rect.MakeLTRB(-18, 70, 62, 150), stroke_paint(C("#C98F6B"), 3))
    for dx, dy in ((-22, 64), (-14, 80)):
        c.drawOval(skia.Rect.MakeXYWH(dx, dy, 30, 22), fill_paint(skin)); c.drawOval(skia.Rect.MakeXYWH(dx, dy, 30, 22), stroke_paint(C("#C98F6B"), 3))
    c.drawRect(skia.Rect.MakeLTRB(10, 140, 70, 330), fill_paint(sleeve))
    c.drawRect(skia.Rect.MakeLTRB(6, 136, 74, 152), fill_paint(C("#3D7FBF")))
    c.restore()

# ---------- scene building ----------
def auto_draw(line):
    m = re.search(r"\$\d[\d,]*|\d+(?:\.\d+)?%", line)
    if m: return {"big": m.group(0)}
    low = line.lower()
    for k, ic in KEYWORDS:
        if k in low: return {"icon": ic}
    return {"icon": "bulb"}

VERTICAL = False
def cells(n):
    if VERTICAL:
        if n <= 1: return [(W / 2, H * 0.42, 640)]
        return [(W / 2, H * (0.30 + 0.28 * i / max(1, n - 1)), 380) for i in range(n)]
    if n <= 1: return [(960, 540, 420)]
    if n == 2: return [(560, 540, 360), (1360, 540, 360)]
    if n == 3: return [(370, 540, 300), (960, 540, 300), (1550, 540, 300)]
    if n == 4: return [(600, 365, 235), (1320, 365, 235), (600, 715, 235), (1320, 715, 235)]
    cols = 3; out = []
    for i in range(n):
        r, k = divmod(i, cols); y = 365 if r == 0 else 715
        inrow = min(cols, n - r * cols); x = 960 + (k - (inrow - 1) / 2) * 600
        out.append((x, y, 225))
    return out

class Scene:
    def __init__(self, sc, spec, idx):
        self.sc, self.idx = sc, idx
        self.start, self.end = sc["start"], sc["end"]
        lines = spec.get("lines", [])
        draws = spec.get("draws") or [auto_draw(l) for l in lines]
        draws = (list(draws) + [None] * len(lines))[:max(1, len(lines))]
        ls = sc.get("line_starts") or [self.start]
        ends = [(ls[i + 1] - 0.38) if i + 1 < len(ls) else self.end - 0.9 for i in range(len(ls))]
        items = [(i, d) for i, d in enumerate(draws) if d]
        rnd = random.Random(idx * 7919)
        self.drawings = []; self.fixed = []
        # heading, written at the top
        head = sc.get("heading") or spec.get("heading") or ""
        if head:
            if VERTICAL:
                cont, fill, w, sz = text_paths(head, 110, W / 2, 330, "center", maxw=W - 120); hx0 = W / 2 - w / 2; uy = 365
            else:
                cont, fill, w, sz = text_paths(head, 64, 90, 128, "left", maxw=1700); hx0 = 90; uy = 150
            self.fixed.append(Drawing(cont, 0.05, 0.05 + min(1.1, 0.25 + 0.035 * len(head)), 2.2 if not VERTICAL else 3.2, INK, center=(hx0 + w / 2, uy - 30), text_fill=fill))
            u = skia.Path(); u.moveTo(hx0, uy); u.cubicTo(hx0 + w * 0.3, uy - 10, hx0 + w * 0.7, uy + 10, hx0 + w, uy - 4)
            self.fixed.append(Drawing([u], 0.1 + min(1.1, 0.25 + 0.035 * len(head)), 0.45 + min(1.1, 0.25 + 0.035 * len(head)), 5, C("#FF6B6B")))
        self.focus = []  # (t0, t1, (x, y))
        cl = cells(len(items))
        flow = spec.get("flow", False)
        prev_xy = None
        for k, ((li, d), (cx, cy, size)) in enumerate(zip(items, cl)):
            t0 = max(0.2, ls[min(li, len(ls) - 1)] - self.start + 0.05) if li > 0 or not head else 0.9
            dur = max(0.6, (ends[min(li, len(ends) - 1)] - self.start) - t0)
            acc = C(d.get("color") or ACC[(idx + k) % len(ACC)]) if not str(d.get("color", "")).startswith("#") else C(d["color"])
            if isinstance(d, str): d = {"icon": d}
            label = d.get("label", "")
            if d.get("big"):
                big = d["big"]; bsz = size * 0.62
                tdur = min(1.4, 0.35 + 0.12 * len(big), dur * 0.55)
                cont, fill, w, bs = text_paths(big, bsz, cx, cy + bsz * 0.32, "center", maxw=min(size * 1.8, W - 200))
                self.drawings.append(Drawing(cont, t0, t0 + tdur, 2.6, INK, center=(cx, cy), text_fill=fill, text_color=acc))
                ring = skia.Path(); rw, rh = w / 2 + 40, bs * 0.62
                ring.moveTo(cx + rw, cy - 6)
                for i in range(1, 40):
                    a = 2 * math.pi * i / 36; ring.lineTo(cx + math.cos(a) * rw * (1 + 0.04 * math.sin(i)), cy - 6 + math.sin(a) * rh)
                self.drawings.append(Drawing([ring], t0 + tdur, t0 + tdur + 0.45, 5, acc, center=(cx, cy)))
                ly = cy + rh + max(60, size * 0.19 * 0.95); lt = t0 + tdur + 0.45
            else:
                ic = ICONS.get(d.get("icon", ""), ICONS["bulb"])
                s = size / 100; ox, oy = cx - size / 2, cy - size / 2 - (24 if label else 0)
                strokes, fills = [], []
                for si, dstr in enumerate(ic["s"]):
                    ps = svg_to_paths(dstr, s, ox, oy, 0.6, rnd); strokes += ps
                    if si in ic.get("f", []): fills += ps
                tdur = min(1.7, max(0.7, dur * 0.5))
                self.drawings.append(Drawing(strokes, t0, t0 + tdur, max(4.5, size / 36), INK, fills, acc, center=(cx, cy)))
                ly = oy + size + 52; lt = t0 + tdur
            if label:
                ldur = min(1.1, 0.3 + 0.04 * len(label))
                cont, fill, w, _ = text_paths(label, max(40, size * 0.19), cx, ly, "center", maxw=min(size * 2.0 if len(cl) <= 3 else 520, W - 140))
                self.drawings.append(Drawing(cont, lt, lt + ldur, 2.0, INK, center=(cx, ly - 16), text_fill=fill))
                lt += ldur
            if flow and prev_xy is not None:
                (px, py) = prev_xy; a = skia.Path()
                sx, ex = px + 0.62 * (cx - px) * 0.35, cx - (cx - px) * 0.35
                if abs(cy - py) < 10:
                    a.moveTo(px + (cx - px) * 0.32, cy - 10); a.cubicTo((px + cx) / 2, cy - 40, (px + cx) / 2, cy + 20, cx - (cx - px) * 0.32, cy - 10)
                    hx, hy = cx - (cx - px) * 0.32, cy - 10
                    a.moveTo(hx - 22, hy - 16); a.lineTo(hx, hy); a.lineTo(hx - 24, hy + 12)
                    self.drawings.append(Drawing([a], t0 - 0.35, t0, 5, C("#9AA0AE"), center=((px + cx) / 2, cy)))
            prev_xy = (cx, cy)
            self.focus.append((t0, lt, (cx, cy)))

    def render(self, c, lt, cam=True):
        # camera: drift gently toward what is being drawn
        CX, CY = W / 2, H / 2
        tx, ty, z = CX, CY, 1.0
        for (a, b, (x, y)) in self.focus:
            if lt >= a - 0.2:
                k = ease((lt - a + 0.2) / 0.6)
                tx, ty = tx + (x - tx) * 0.16 * k, ty + (y - ty) * 0.16 * k; z = 1.0 + 0.05 * k
        if self.focus and lt > self.focus[-1][1] + 0.6:  # zoom back out to show the whole page
            k = ease((lt - self.focus[-1][1] - 0.6) / 0.8); tx += (CX - tx) * k; ty += (CY - ty) * k; z += (1.0 - z) * k
        c.save()
        if cam:
            c.translate(CX, CY); c.scale(z, z); c.translate(-tx, -ty)
        tip = None
        for d in self.drawings:
            r = d.draw(c, lt, boil=lt > d.t1)
            if r is not None: tip = r
        c.restore()
        if tip is not None and cam:
            tip = ((tip[0] - tx) * z + CX, (tip[1] - ty) * z + CY)
        for d in self.fixed:
            r = d.draw(c, lt, boil=lt > d.t1)
            if r is not None: tip = r
        return tip

    def draw_intervals(self):
        return [(self.start + d.t0, self.start + d.t1) for d in self.fixed + self.drawings]

# ---------- page ----------
_paper = None
def paper(c):
    global _paper
    if _paper is None:
        rng = np.random.default_rng(3)
        base = np.ones((H // 4, W // 4, 4), np.uint8) * 255
        n = rng.normal(0, 3.2, (H // 4, W // 4))
        tone = np.clip(250 + n, 236, 255).astype(np.uint8)
        base[..., 0] = tone; base[..., 1] = tone; base[..., 2] = np.clip(tone.astype(int) - 4, 0, 255).astype(np.uint8)
        img = skia.Image.fromarray(base, colorType=skia.kRGBA_8888_ColorType)
        _paper = img
    c.drawImageRect(_paper, skia.Rect.MakeWH(W, H), skia.SamplingOptions(skia.FilterMode.kLinear))

def wrap(s, f, maxw):
    lines = [""]
    for w in s.split():
        t = (lines[-1] + " " + w).strip()
        if f.measureText(t) <= maxw or not lines[-1]: lines[-1] = t
        else: lines.append(w)
    return lines

def subtitle(c, sub, t):
    if not sub: return
    a = clamp((t - sub["start"]) / 0.1) * clamp((sub["end"] + 0.15 - t) / 0.1)
    if a <= 0: return
    fs = 66 if VERTICAL else 54
    f = skia.Font(TF_SUB, fs); f.setEdging(skia.Font.Edging.kAntiAlias)
    ls = wrap(sub["text"], f, W - 160 if VERTICAL else 1500); lh = int(fs * 1.3)
    bw = max(f.measureText(l) for l in ls) + 80; bh = lh * len(ls) + 34
    x, y = (W - bw) / 2, (H * 0.80 - bh / 2) if VERTICAL else (H - 60 - bh)
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, bw, bh), 24, 24), fill_paint(skia.Color(24, 26, 36), 225 * a))
    for i, l in enumerate(ls):
        c.drawString(l, W / 2 - f.measureText(l) / 2, y + 17 + lh * (i + 1) - fs * 0.3, f, fill_paint(skia.ColorWHITE, 255 * a))

class Video:
    def __init__(self, wd):
        self.TL = json.load(open(f"{wd}/timeline.json"))
        spec = json.load(open(f"{wd}/script.json"))
        global W, H, VERTICAL
        if spec.get("vertical"): W, H, VERTICAL = 1080, 1920, True
        self.scenes = [Scene(sc, sp, i) for i, (sc, sp) in enumerate(zip(self.TL["scenes"], spec["scenes"]))]
        self.hand = (W + 200, H + 200)
    def frame(self, c, t):
        si = 0
        for i, s in enumerate(self.scenes):
            if t >= s.start: si = i
        S = self.scenes[si]; lt = t - S.start
        paper(c)
        flip = 0.5
        if si > 0 and lt < flip:  # page slides away to the left, new page underneath
            k = ease(lt / flip)
            tip = S.render(c, lt)
            c.save(); c.translate(-W * k, 0)
            c.drawRect(skia.Rect.MakeWH(W, H), fill_paint(C("#FBFAF5")))
            P = self.scenes[si - 1]; P.render(c, P.end - P.start)
            c.drawRect(skia.Rect.MakeXYWH(W - 6, 0, 30, H), fill_paint(skia.Color(0, 0, 0), 28))
            c.restore()
        else:
            tip = S.render(c, lt)
        # hand follows the pen tip; glides to the corner when idle
        tx, ty = tip if tip else (W - 120, H + 140)
        hx, hy = self.hand
        k = 0.55 if tip else 0.12
        hx += (tx - hx) * k; hy += (ty - hy) * k; self.hand = (hx, hy)
        if hy < H + 60: draw_hand(c, hx, hy, t)
        cur = None
        for s in self.TL["scenes"][si]["subs"]:
            if s["start"] - 0.05 <= t <= s["end"] + 0.15: cur = s
        subtitle(c, cur, t)
        c.drawRect(skia.Rect.MakeXYWH(0, 0, W * t / self.TL["duration"], 7), fill_paint(C("#FF6B6B")))

    def intervals(self):
        out = []
        for s in self.scenes: out += s.draw_intervals()
        return out

def pencil_wav(wd):
    import soundfile as sf
    from scipy.signal import butter, sosfilt
    V = Video(wd); SR = 44100; D = V.TL["duration"]; N = int(D * SR)
    rng = np.random.default_rng(5); out = np.zeros(N, np.float32)
    sos = butter(4, [1800, 7000], btype="bandpass", fs=SR, output="sos")
    for a, b in V.intervals():
        if b - a < 0.08: continue
        n0, n1 = int(a * SR), min(N, int(b * SR))
        n = n1 - n0
        if n <= 0: continue
        noise = sosfilt(sos, rng.standard_normal(n + 2000))[2000:]
        tt = np.arange(n) / SR
        f = rng.uniform(5, 9)
        env = (0.35 + 0.65 * np.abs(np.sin(2 * np.pi * f * tt + rng.uniform(0, 6)))) * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 1.3 * tt)))
        fade = np.minimum(1, np.minimum(tt / 0.04, (tt[-1] - tt) / 0.06 + 1e-6))
        out[n0:n1] += (noise * env * fade).astype(np.float32)
    m = np.max(np.abs(out)) or 1
    sf.write(f"{wd}/pencil.wav", out / m * 0.5, SR)
    print("pencil ok", len(V.intervals()), "strokes")

def main():
    wd = sys.argv[1]
    if sys.argv[2] == "--pencil": return pencil_wav(wd)
    t0, t1, out = float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    V = Video(wd)
    W, H = globals()["W"], globals()["H"]
    info = skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
    surf = skia.Surface.MakeRaster(info)
    if out.endswith(".png"):
        # warm up the hand position, then draw the frame
        for tt in np.arange(max(0, t0 - 1.5), t0, 1 / FPS):
            V.frame(surf.getCanvas(), tt)
        c = surf.getCanvas(); V.frame(c, t0); surf.makeImageSnapshot().save(out, skia.kPNG); return
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    n0, n1 = round(t0 * FPS), round(t1 * FPS)
    buf = np.empty((H, W, 4), np.uint8)
    for tt in np.arange(max(0, t0 - 1.0), t0, 1 / FPS):  # warm-up hand position (not written)
        V.frame(surf.getCanvas(), tt)
    for n in range(n0, n1):
        c = surf.getCanvas(); V.frame(c, n / FPS)
        surf.readPixels(info, buf, W * 4); ff.stdin.write(buf.tobytes())
        if (n - n0) % 480 == 0: print(out, n, "/", n1, flush=True)
    ff.stdin.close(); ff.wait()

if __name__ == "__main__":
    main()
