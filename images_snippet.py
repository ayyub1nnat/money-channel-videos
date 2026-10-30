# Paste into COMPOSIO_REMOTE_WORKBENCH (needs the GitHub connection in Composio and the Cloudflare creds file
# /mnt/files/sml/cf_creds.json = {"account_id": ..., "api_token": ...}). Generates one illustration per scene of
# each script in JOBS with Cloudflare Workers AI (FLUX.2 klein 4B, reference image = our hero) and commits them to
# the `assets` branch as <dir>/img/NNN.jpg (+ thumb.jpg). Runs in a background thread: call this cell once, then
# poll `print(IMG_STATUS)` in later cells until running is False. Skips images that already exist on the branch.
import requests, base64, json, threading, time, contextlib, io, os
REPO = "ayyub1nnat/money-channel-videos"; RAW = f"https://raw.githubusercontent.com/{REPO}"
SHA = globals().get("SHA", "main")          # commit of main holding the scripts
JOBS = globals().get("JOBS", [])            # e.g. ["days/2026-10-26/pov", "days/2026-10-26/pov_short"]
CF = json.load(open("/mnt/files/sml/cf_creds.json"))
MODEL = "@cf/black-forest-labs/flux-2-klein-4b"
STYLE = ("Flat 2D cartoon illustration for a YouTube personal finance story, clean bold black outlines, simple cel shading, "
         "bright warm colors, expressive friendly faces, detailed but uncluttered background, webcomic style. No text, no letters, no watermark.")
HERO_TXT = ("Sam, the man from image 0: early 30s, short dark brown wavy hair, round glasses, light stubble, "
            "mustard-yellow crewneck sweater over a white collar, dark jeans")
HERO_REF = requests.get(f"{RAW}/{SHA}/brand/hero_ref.jpg", timeout=60)
HERO_REF = HERO_REF.content if HERO_REF.status_code == 200 else None
IMG_STATUS = globals().get("IMG_STATUS") or {"done": 0, "skipped": 0, "errors": [], "running": False, "neurons_hint": 0}

def cf_image(prompt, w, h, seed, ref=None):
    files = {"prompt": (None, prompt), "width": (None, str(w)), "height": (None, str(h)), "seed": (None, str(seed))}
    if ref: files["input_image_0"] = ("hero.jpg", ref, "image/jpeg")
    for a in range(3):
        r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{CF['account_id']}/ai/run/{MODEL}",
                          headers={"Authorization": f"Bearer {CF['api_token']}"}, files=files, timeout=150)
        if r.status_code == 200:
            j = r.json(); img = (j.get("result") or {}).get("image")
            if img: return base64.b64decode(img)
        last = f"{r.status_code} {r.text[:200]}"
        if r.status_code in (400, 401, 403): break
        time.sleep(5 * (a + 1))
    raise RuntimeError(last)

def gh_exists(path):
    with contextlib.redirect_stdout(io.StringIO()):
        res, err = proxy_execute("GET", f"/repos/{REPO}/contents/{path}", "github", query_params={"ref": "assets"})
    return (not err) and isinstance(res, dict) and res.get("sha")

def gh_put(path, data):
    sha = gh_exists(path)
    body = {"message": f"img {path}", "content": base64.b64encode(data).decode(), "branch": "assets"}
    if sha: body["sha"] = sha
    with contextlib.redirect_stdout(io.StringIO()):
        res, err = proxy_execute("PUT", f"/repos/{REPO}/contents/{path}", "github", body=body)
    if err: raise RuntimeError(str(err)[:200])

def prompt_for(p, hero):
    p = p.replace("{HERO}", "Sam (the man from image 0)" if hero else "a friendly man with round glasses in a mustard-yellow sweater")
    return f"{STYLE} Scene: {p}." + (f" Keep Sam exactly as in image 0: {HERO_TXT}." if hero else "")

def run_jobs():
    IMG_STATUS["running"] = True
    try:
        for d in JOBS:
            S = requests.get(f"{RAW}/{SHA}/{d}/script.json", timeout=60).json(); V = bool(S.get("vertical"))
            w, h = (576, 1024) if V else (1024, 576)
            items = [(f"{i:03d}", sc["img"]) for i, sc in enumerate(S["scenes"])]
            T = S.get("thumbnail", {})
            if T.get("img"): items.append(("thumb", T["img"]))
            for side, key in (("left", "thumb_l"), ("right", "thumb_r")):       # split thumbnail (owner's style 2026-10-30)
                if isinstance(T.get(side), dict) and T[side].get("img"):
                    items.append((key, T[side]["img"] + ", close-up from the chest up, the face in the middle of the image, "
                                  "the top fifth of the image is plain background with nothing important (space for a label)"))
            for k, p in items:
                path = f"{d}/img/{k}.jpg"
                if gh_exists(path): IMG_STATUS["skipped"] += 1; continue
                hero = "{HERO}" in p and HERO_REF is not None
                try:
                    data = cf_image(prompt_for(p, hero), {"thumb": 1024, "thumb_l": 640, "thumb_r": 640}.get(k, w), {"thumb": 576, "thumb_l": 720, "thumb_r": 720}.get(k, h),
                                    seed=abs(hash(d + k)) % 100000, ref=HERO_REF if hero else None)
                    gh_put(path, data); IMG_STATUS["done"] += 1
                except Exception as ex:
                    IMG_STATUS["errors"].append((path, str(ex)[:200]))
                    if "401" in str(ex) or "403" in str(ex) or "429" in str(ex) or "4006" in str(ex): return
    finally:
        IMG_STATUS["running"] = False

if not IMG_STATUS["running"]:
    threading.Thread(target=run_jobs, daemon=True).start()
time.sleep(5); print("IMAGES", IMG_STATUS)
