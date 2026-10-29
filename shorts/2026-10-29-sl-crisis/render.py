"""Custom documentary-style Short: S&L crisis. Usage: python3 render.py <dir> <t0> <t1> <out.mp4>  (video only)
Data: FRED FEDFUNDS (monthly), FDIC Banking Review 2000 (Curry & Shibut), largest-bankruptcies list (FCA 9/9/1988 $33.864B)."""
import sys, json, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
wd, T0, T1, OUT = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
W, H, FPS = 1080, 1920, 30
FB = "/home/claude/money-channel-videos/fonts/Poppins-Bold.ttf"
TL = json.load(open(f"{wd}/timeline.json")); SC = TL["scenes"]; DUR = TL["duration"]
RED, GRN, YEL, WHT, GRY = (235, 59, 59), (40, 200, 110), (255, 205, 60), (255, 255, 255), (150, 160, 175)
BG = (12, 16, 28)
_f = {}
def F(s):
    if s not in _f: _f[s] = ImageFont.truetype(FB, s)
    return _f[s]
def ease(u): u = max(0, min(1, u)); return u * u * (3 - 2 * u)
def back(u):  # overshoot pop
    u = max(0, min(1, u)); c = 1.7; return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2
IMG = {}
def img(i):
    if i not in IMG:
        im = Image.open(f"{wd}/img/{i:03d}.jpg").convert("RGB").resize((W, H), Image.LANCZOS); IMG[i] = im
    return IMG[i]
def kb(i, u, z0=1.0, z1=1.12, dark=0.0, blur=0):
    im = img(i); z = z0 + (z1 - z0) * u
    w, h = int(W / z), int(H / z); x, y = (W - w) // 2, int((H - h) * 0.4)
    f = im.crop((x, y, x + w, y + h)).resize((W, H), Image.BILINEAR)
    if blur: f = f.filter(ImageFilter.GaussianBlur(blur))
    if dark: f = Image.blend(f, Image.new("RGB", (W, H), BG), dark)
    return f
def grad(f, top=0.75, bottom=0.85):
    a = np.linspace(0, 1, H)[:, None]
    m = np.clip(np.maximum((0.35 - a) / 0.35 * top, (a - 0.55) / 0.45 * bottom), 0, 1)
    arr = np.array(f).astype(np.float32); bg = np.array(BG, np.float32)
    arr = arr * (1 - m[..., None]) + bg * m[..., None]
    return Image.fromarray(arr.astype(np.uint8))
def text_c(d, y, s, size, fill=WHT, stroke=8, sc=1.0, alpha=1.0, xc=W / 2):
    f = F(max(8, int(size * sc)))
    bb = d.textbbox((0, 0), s, font=f, stroke_width=stroke); tw, th = bb[2] - bb[0], bb[3] - bb[1]
    col = tuple(int(c) for c in fill) + (int(255 * alpha),)
    d.text((xc - tw / 2, y - th / 2), s, font=f, fill=col, stroke_width=stroke, stroke_fill=(0, 0, 0, int(255 * alpha)))
    return tw, th
def fit(s, size, maxw, stroke=8):
    while size > 20:
        bb = F(size).getbbox(s, stroke_width=stroke)
        if bb[2] - bb[0] <= maxw: return size
        size -= 4
    return size
def label(d, y, s, size, bgc, fg=WHT, sc=1.0, alpha=1.0):
    size = fit(s, int(size * sc), W - 140, 0); f = F(size)
    bb = d.textbbox((0, 0), s, font=f); tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = 26; x0 = (W - tw) / 2 - pad
    d.rounded_rectangle((x0, y - th / 2 - pad * 0.8, x0 + tw + 2 * pad, y + th / 2 + pad * 0.9), 22,
                        fill=tuple(bgc) + (int(235 * alpha),))
    d.text(((W - tw) / 2, y - th / 2 - bb[1]), s, font=f, fill=tuple(fg) + (int(255 * alpha),))
def headline(d, lines, t, y0=250, colors=None):
    for k, s in enumerate(lines):
        u = (t - 0.12 * k) / 0.35
        if u <= 0: continue
        c = (colors or [RED, (30, 40, 60)] * 3)[k]
        label(d, y0 + k * 135, s, 78 if k == 0 else 60, c, sc=0.6 + 0.4 * back(u), alpha=min(1, u * 2))
def source(d, s): d.text((40, H - 70), s, font=F(26), fill=(200, 205, 215, 200))

# ---------- subtitles (karaoke-style chunks) ----------
DISP = ["$33.86 billion in assets... and it still went bankrupt!",
"America, 1988. The savings and loan industry is falling apart.",
"It started with interest rates. They exploded to almost 20%!",
"Their old mortgages paid low, fixed rates. But savers now wanted much more. Every month, they lost money.",
"So many gambled. Risky loans. Empty office towers. And they lost even more.",
"September 9, 1988. The owner of American Savings and Loan goes bankrupt. $33.86 billion in assets!",
"And that was just one. From 1986 to 1995, over 1,000 thrifts failed.",
"And the bill landed on taxpayers. About $124 billion!",
"Could this have been prevented? Tell me in the comments!"]
SUBS = []
for sc, txt in zip(SC, DISP):
    ws = txt.split(); a0, a1 = sc["subs"][0]["start"], sc["subs"][-1]["end"]
    chunks = []; cur = []
    for w in ws:
        cur.append(w)
        if len(cur) >= 4 or w[-1] in ".!?": chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    tot = sum(sum(len(w) + 2 for w in c) for c in chunks); t = a0
    for c in chunks:
        dt = (a1 - a0) * sum(len(w) + 2 for w in c) / tot
        SUBS.append({"start": t, "end": t + dt, "text": " ".join(c)}); t += dt
def subs(d, t):
    for s in SUBS:
        if s["start"] <= t < s["end"]:
            ln = s["text"].upper(); u = (t - s["start"]) / 0.12; sc = 0.85 + 0.15 * ease(u)
            text_c(d, 1560, ln, fit(ln, 84, W - 100, 10), YEL, stroke=10, sc=sc)
            return

# ---------- data ----------
FF = [4.61,4.68,4.69,4.73,5.35,5.39,5.42,5.90,6.14,6.47,6.51,6.56,6.70,6.78,6.79,6.89,7.36,7.60,7.81,8.04,8.45,8.96,9.76,10.03,
10.07,10.06,10.09,10.01,10.24,10.29,10.47,10.94,11.43,13.77,13.18,13.78,13.82,14.13,17.19,17.61,10.98,9.47,9.03,9.61,10.87,12.81,15.85,18.90,
19.08,15.93,14.70,15.72,18.52,19.10,19.04,17.82,15.87,15.08,13.31,12.37,13.22,14.78,14.68,14.94,14.45,14.15,12.59,10.12,10.31,9.71,9.20,8.95,
8.68,8.51,8.77,8.80,8.63,8.98,9.37,9.56,9.45,9.48,9.34,9.47,9.56,9.59,9.91,10.29,10.32,11.06,11.23,11.64,11.30,9.99,9.43,8.38,
8.35,8.50,8.58,8.27,7.97,7.53,7.88,7.90,7.92,7.99,8.05,8.27,8.14,7.86,7.48,6.99,6.85,6.92,6.56,6.17,5.89,5.85,6.04,6.91,
6.43,6.10,6.13,6.37,6.85,6.73,6.58,6.73,7.22,7.29,6.69,6.77,6.83,6.58,6.58,6.87,7.09,7.51,7.75,8.01,8.19,8.30,8.35,8.76,
9.12,9.36,9.85,9.84,9.81,9.53,9.24,8.99,9.02,8.84,8.55,8.45]   # 1977-01 .. 1989-12

def panel(d, box, alpha=215):
    d.rounded_rectangle(box, 34, fill=(18, 24, 40, alpha), outline=(70, 85, 115, 255), width=3)

# ---------- scenes ----------
def s_hook(t, dur):
    f = kb(1, t / dur, 1.25, 1.1, dark=0.55, blur=6)
    if t < 0.5:  # flash + shake intro
        f = Image.blend(f, Image.new("RGB", (W, H), (255, 255, 255)), max(0, 0.6 - t * 1.2))
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(o)
    v = 33.86 * ease(t / 1.1)
    sh = (math.sin(t * 90) * 14 * max(0, 1 - abs(t - 1.15) / 0.35)) if t > 0.8 else 0
    text_c(d, 760, f"${v:,.2f}", 230, YEL, stroke=14, sc=1.0 + 0.08 * max(0, 1 - abs(t - 1.15) / 0.3), xc=W / 2 + sh)
    if t > 1.1:
        u = (t - 1.1) / 0.3
        text_c(d, 1000, "BILLION!", 190, RED, stroke=14, sc=2.2 - 1.2 * back(u), alpha=min(1, u * 3), xc=W / 2 + sh)
    if t > 2.4:
        u = (t - 2.4) / 0.35; label(d, 260, "...AND IT STILL WENT BANKRUPT", 66, RED, sc=0.6 + 0.4 * back(u), alpha=min(1, u * 2))
    return f, o

def s_year(t, dur):
    f = grad(kb(0, t / dur, 1.05, 1.2)); o = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(o)
    headline(d, ["AMERICA — 1988", "A FINANCIAL GIANT COLLAPSES"], t)
    return f, o

def chart_bg():
    f = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(f)
    for y in range(0, H, 60): d.line((0, y, W, y), fill=(18, 24, 38))
    for x in range(0, W, 60): d.line((x, 0, x, H), fill=(18, 24, 38))
    return f

def s_rates(t, dur):
    f = chart_bg(); o = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(o)
    headline(d, ["RISING INTEREST RATES", "U.S. FEDERAL FUNDS RATE"], t, colors=[RED, (30, 40, 60)])
    x0, x1, y0, y1 = 120, 1000, 1240, 560
    panel(d, (60, 480, W - 60, 1330))
    for p in (5, 10, 15, 20):
        y = y0 - (y0 - y1) * p / 20; d.line((x0, y, x1, y), fill=(60, 72, 98, 255), width=2)
        d.text((x0 - 80, y - 20), f"{p}%", font=F(32), fill=GRY)
    for yr in (1977, 1981, 1985, 1989):
        x = x0 + (x1 - x0) * (yr - 1977) / 13; d.text((x - 40, y0 + 18), str(yr), font=F(32), fill=GRY)
    n = len(FF); k = int(n * ease(t / (dur * 0.7)))
    pts = [(x0 + (x1 - x0) * i / (n - 1), y0 - (y0 - y1) * FF[i] / 20) for i in range(max(2, k))]
    d.line(pts, fill=RED, width=9, joint="curve")
    lx, ly = pts[-1]; d.ellipse((lx - 14, ly - 14, lx + 14, ly + 14), fill=YEL)
    if k > 54:  # peak June 1981
        px, py = x0 + (x1 - x0) * 53 / (n - 1), y0 - (y0 - y1) * 19.10 / 20
        u = min(1, (k - 54) / 8)
        d.ellipse((px - 20, py - 20, px + 20, py + 20), outline=YEL, width=6)
        text_c(d, py - 70, "19.1% (1981)", 64, YEL, stroke=8, sc=0.6 + 0.4 * back(u))
    source(d, "Source: FRED, Federal Reserve Bank of St. Louis (FEDFUNDS, monthly)")
    return f, o

def arrow(d, x0, y, x1, col, w):
    d.line((x0, y, x1 - 40 * (1 if x1 > x0 else -1), y), fill=col, width=w)
    s = 1 if x1 > x0 else -1
    d.polygon([(x1, y), (x1 - 60 * s, y - w * 1.4), (x1 - 60 * s, y + w * 1.4)], fill=col)

def s_squeeze(t, dur):
    f = chart_bg(); o = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(o)
    headline(d, ["THE SQUEEZE", "HOW SAVINGS & LOANS LOST MONEY"], t)
    u1, u2, u3 = ease((t - 0.2) / 0.5), ease((t - 2.4) / 0.5), ease((t - 4.6) / 0.5)
    def box(y, a, l1, l2, c):
        panel(d, (150, y - 85, W - 150, y + 85), int(215 * a))
        text_c(d, y - 28, l1, 54, c, 0, alpha=a); text_c(d, y + 38, l2, 40, WHT, 0, alpha=a)
    def varrow(y0, y1, c, w, a, txt):
        if a <= 0: return
        ye = y0 + (y1 - y0) * a
        d.line((W / 2, y0, W / 2, ye - 30), fill=c, width=w)
        d.polygon([(W / 2, ye + 10), (W / 2 - w * 1.6, ye - 40), (W / 2 + w * 1.6, ye - 40)], fill=c)
        d.text((W / 2 + w * 1.6 + 20, (y0 + y1) / 2 - 22), txt, font=F(40), fill=c)
    box(560, max(u1, 0.001), "OLD MORTGAGES", "pay the S&L low, fixed rates", GRN)
    varrow(650, 760, GRN, 12, u1, "small money IN")
    box(850, 1, "SAVINGS & LOAN", "stuck in the middle", YEL)
    varrow(940, 1080, RED, 34, u2, "big money OUT")
    if u2 > 0: box(1170, u2, "SAVERS' DEPOSITS", "now demand high new rates", RED)
    if u3 > 0: label(d, 1350, "= LOSSES EVERY MONTH", 70, RED, sc=0.6 + 0.4 * back((t - 4.6) / 0.35), alpha=u3)
    return f, o

def stamp(d, y, s, t0, t, col=RED, size=96, rot=0):
    u = (t - t0) / 0.25
    if u <= 0: return
    text_c(d, y, s, size, col, stroke=10, sc=2.0 - 1.0 * back(u), alpha=min(1, u * 3))

def s_risky(t, dur):
    f = grad(kb(2, t / dur, 1.08, 1.22)); o = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(o)
    headline(d, ["RISKY INVESTMENTS"], t)
    stamp(d, 1120, "BAD LOANS", 1.0, t, YEL, 96); stamp(d, 1260, "MASSIVE LOSSES", 2.4, t, RED, 100)
    return f, o

def s_date(t, dur):
    f = kb(1, t / dur, 1.1, 1.2, dark=0.6, blur=3); o = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(o)
    u = back(t / 0.4)
    # calendar card
    cx, cy, cw, ch = W / 2, 620, 480 * u, 430 * u
    if u > 0.05:
        d.rounded_rectangle((cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2), 40, fill=(245, 245, 245, 255))
        d.rounded_rectangle((cx - cw / 2, cy - ch / 2, cx + cw / 2, cy - ch / 2 + 130 * u), 40, fill=RED + (255,))
        text_c(d, cy - ch / 2 + 65 * u, "SEPT 1988", 64, WHT, 0, sc=u)
        text_c(d, cy + 70 * u, "9", 250, (25, 25, 35), 0, sc=u)
    if t > 1.5:
        v = (t - 1.5) / 0.4
        text_c(d, 920, "FINANCIAL CORP. OF AMERICA", fit("FINANCIAL CORP. OF AMERICA", 66, W - 100), WHT, 8, alpha=min(1, v * 2))
        text_c(d, 990, "owner of American Savings & Loan", 44, GRY, 6, alpha=min(1, v * 2))
    stamp(d, 1140, "BANKRUPT", 3.0, t, RED, 150)
    if t > 4.6:
        v = (t - 4.6) / 0.5; val = 33.864 * ease(v)
        text_c(d, 1300, f"${val:.2f} BILLION IN ASSETS", fit("$33.86 BILLION IN ASSETS", 78, W - 80), YEL, 10)
    source(d, "Bankruptcy filing 9/9/1988, assets $33.864B (BankruptcyData)")
    return f, o

def s_bigger(t, dur):
    f = kb(5, t / dur, 1.05, 1.15, dark=0.72); o = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(o)
    headline(d, ["THE CRISIS WAS MUCH BIGGER"], t)
    panel(d, (90, 440, W - 90, 1200))
    text_c(d, 510, "U.S. federally insured thrifts", 40, GRY, 0)
    base = 1080; mx = 3234; hmax = 480
    for k, (yr, v, col, x) in enumerate([(1986, 3234, (90, 140, 230), 330), (1995, 1645, RED, 750)]):
        u = ease((t - 0.4 - k * 0.9) / 0.8)
        if u <= 0: continue
        h = hmax * v / mx * u
        d.rounded_rectangle((x - 130, base - h, x + 130, base), 18, fill=col + (255,))
        text_c(d, base - h - 50, f"{int(v * u):,}", 70, WHT, 6, xc=x)
        text_c(d, base + 55, str(yr), 50, GRY, 0, xc=x)
    if t > 2.4:
        v = ease((t - 2.4) / 0.8)
        label(d, 1300, f"{int(1043 * v):,} FAILED (1986–1995)", 72, RED)
    source(d, "Source: FDIC Banking Review 2000 (Curry & Shibut)")
    return f, o

def s_bill(t, dur):
    f = kb(3, t / dur, 1.05, 1.18, dark=0.55); o = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(o)
    headline(d, ["BILLIONS IN TAXPAYER COSTS"], t)
    v = 123.8 * ease((t - 0.3) / 1.6)
    if t > 0.3:
        text_c(d, 640, f"${v:,.1f}", 210, YEL, 14, sc=1 + 0.06 * max(0, 1 - abs(t - 2.0) / 0.3))
        text_c(d, 820, "BILLION", 120, RED, 12)
        if t > 2.9: stamp(d, 1250, "UP TO $124 BILLION!", 2.9, t, YEL, 84)
    if t > 2.0:
        u = ease((t - 2.0) / 0.8); x0, x1 = 110, W - 110; tot = 152.9
        xm = x0 + (x1 - x0) * 123.8 / tot
        d.rounded_rectangle((x0, 980, x0 + (xm - x0) * u, 1080), 16, fill=RED + (255,))
        if u > 0.9:
            d.rounded_rectangle((xm + 6, 980, xm + 6 + (x1 - xm - 6) * min(1, (u - 0.9) * 10), 1080), 16, fill=(120, 130, 150, 255))
        d.text((x0, 1100), "Taxpayers $123.8B", font=F(40), fill=RED)
        d.text((x1 - 300, 1100), "Industry $29.1B", font=F(40), fill=(180, 190, 205))
    source(d, "Source: FDIC Banking Review 2000 (Curry & Shibut)")
    return f, o

def s_end(t, dur):
    f = grad(kb(4, t / dur, 1.05, 1.18)); o = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(o)
    headline(d, ["COULD IT HAPPEN AGAIN?", "COMMENT BELOW"], t, colors=[RED, (40, 120, 220)])
    return f, o

FN = [s_hook, s_year, s_rates, s_squeeze, s_risky, s_date, s_bigger, s_bill, s_end]
starts = [0.0] + [s["start"] for s in SC[1:]]; ends = [s["start"] for s in SC[1:]] + [DUR]

def frame(t):
    i = max(k for k in range(len(SC)) if starts[k] <= t)
    st, dur = starts[i], ends[i] - starts[i]; lt = t - st
    f, o = FN[i](lt, dur)
    f = f.convert("RGBA"); f.alpha_composite(o)
    d = ImageDraw.Draw(f); subs(d, t)
    if i > 0 and lt < 0.22:  # punch-in transition
        z = 1.12 - 0.12 * ease(lt / 0.22); w, h = int(W / z), int(H / z)
        f = f.crop(((W - w) // 2, (H - h) // 2, (W - w) // 2 + w, (H - h) // 2 + h)).resize((W, H))
        if lt < 0.06: f = Image.blend(f.convert("RGB"), Image.new("RGB", (W, H), WHT), 0.35).convert("RGBA")
    # progress bar
    d = ImageDraw.Draw(f); d.rectangle((0, H - 12, int(W * t / DUR), H), fill=RED)
    return f.convert("RGB")

if __name__ == "__main__":
    if OUT.endswith(".png"): frame(T0).save(OUT); sys.exit()
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)
    n0, n1 = round(T0 * FPS), round(T1 * FPS)
    for n in range(n0, n1): p.stdin.write(frame(n / FPS).tobytes())
    p.stdin.close(); p.wait()
