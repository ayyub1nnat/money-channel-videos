# Paste into COMPOSIO_REMOTE_WORKBENCH AFTER images_snippet.py has finished (images are more important for the
# Cloudflare quota). Needs /mnt/files/sml/cf_creds.json and the GitHub connection in Composio.
# For each script in JOBS whose "voice" is "aura2:<speaker>" (owner's choice 2026-10-28: male voice "aura2:orpheus"),
# generates one FLAC per spoken line with Cloudflare Workers AI Deepgram Aura-2 and commits them to the `assets`
# branch as <dir>/voice/SSS_L.flac (scene, line). Background thread: poll `print(VOICE_STATUS)` until running is False.
# Then locally: ./fetch_imgs.sh <dirs> (also fetches voice/) and tts.py uses these files; any missing line falls back
# to Kokoro "am_michael" (tell the owner if that happened: Aura-2 needs the Workers Paid plan beyond the free quota).
import requests, base64, json, threading, time, contextlib, io, os
from concurrent.futures import ThreadPoolExecutor
try:
    import soundfile as sf
except ImportError:
    import subprocess; subprocess.run("pip install -q soundfile", shell=True); import soundfile as sf
REPO = "ayyub1nnat/money-channel-videos"; RAW = f"https://raw.githubusercontent.com/{REPO}"
SHA = globals().get("SHA", "main"); JOBS = globals().get("JOBS", [])
CF = json.load(open("/mnt/files/sml/cf_creds.json"))
VOICE_STATUS = globals().get("VOICE_STATUS") or {"done": 0, "skipped": 0, "errors": [], "running": False}

def aura(text, speaker):
    last = ""
    for a in range(3):
        r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{CF['account_id']}/ai/run/@cf/deepgram/aura-2-en",
                          headers={"Authorization": f"Bearer {CF['api_token']}"},
                          json={"text": text, "speaker": speaker, "encoding": "linear16", "container": "wav", "sample_rate": 24000},
                          timeout=150)
        if r.status_code == 200 and r.content[:4] == b"RIFF":
            x, sr = sf.read(io.BytesIO(r.content)); b = io.BytesIO(); sf.write(b, x, sr, format="FLAC"); return b.getvalue()
        last = f"{r.status_code} {r.text[:200]}"
        if r.status_code in (400, 401, 403, 429): break
        time.sleep(5 * (a + 1))
    raise RuntimeError(last)

def _gh(method, path, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return proxy_execute(method, f"/repos/{REPO}/contents/{path}", "github", **kw)

def gh_put_voice(path, data):
    res, err = _gh("GET", path, query_params={"ref": "assets"})
    body = {"message": f"voice {path}", "content": base64.b64encode(data).decode(), "branch": "assets"}
    if not err and isinstance(res, dict) and res.get("sha"): body["sha"] = res["sha"]
    for a in range(4):   # parallel PUTs on one branch can conflict (409) -> retry
        res, err = _gh("PUT", path, body=body)
        if not err: return
        time.sleep(2 + 2 * a)
    raise RuntimeError(str(err)[:200])

def run_voice():
    VOICE_STATUS["running"] = True
    try:
        for d in JOBS:
            S = requests.get(f"{RAW}/{SHA}/{d}/script.json", timeout=60).json()
            v = S.get("voice", "")
            if not v.startswith("aura2:"): continue
            spk = v.split(":", 1)[1]
            items = [(f"{d}/voice/{i:03d}_{j}.flac", ln) for i, sc in enumerate(S["scenes"]) for j, ln in enumerate(sc["lines"])]
            def one(it):
                path, ln = it
                try:
                    gh_put_voice(path, aura(ln, spk)); VOICE_STATUS["done"] += 1
                except Exception as ex:
                    VOICE_STATUS["errors"].append((path, str(ex)[:200]))
            with ThreadPoolExecutor(3) as ex:
                list(ex.map(one, items))
            if any(("429" in e or "401" in e or "403" in e) for _, e in VOICE_STATUS["errors"]): return
    finally:
        VOICE_STATUS["running"] = False

if not VOICE_STATUS["running"]:
    threading.Thread(target=run_voice, daemon=True).start()
time.sleep(5); print("VOICE", VOICE_STATUS)
