# YouTube Data API helper using the channel owner's OWN Google Cloud project (own quota: 100 uploads/day,
# 10,000 API units/day, not shared). Credentials live ONLY in the Composio workbench's private storage:
# /mnt/files/sml/yt_creds.json  {client_id, client_secret, refresh_token}  — never commit them.
# Load in COMPOSIO_REMOTE_WORKBENCH with:
#   import requests; exec(requests.get("https://raw.githubusercontent.com/ayyub1nnat/money-channel-videos/main/yt_lib.py", timeout=60).text)
import json, os, time, requests

_CREDS = "/mnt/files/sml/yt_creds.json"
_tok = {"v": None, "exp": 0}
API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3"

def yt_token():
    if _tok["v"] and time.time() < _tok["exp"] - 60:
        return _tok["v"]
    c = json.load(open(_CREDS))
    r = requests.post("https://oauth2.googleapis.com/token", timeout=60, data={
        "client_id": c["client_id"], "client_secret": c["client_secret"],
        "refresh_token": c["refresh_token"], "grant_type": "refresh_token"})
    if r.status_code != 200:
        raise RuntimeError(f"token refresh failed {r.status_code}: {r.text[:300]} — the owner may need to re-authorize (see OWN_API_SETUP.md)")
    j = r.json(); _tok["v"] = j["access_token"]; _tok["exp"] = time.time() + j.get("expires_in", 3600)
    return _tok["v"]

def yt(method, path, params=None, body=None, base=API, **kw):
    """Call the YouTube API; returns parsed JSON (or {} for empty bodies). Raises on HTTP errors."""
    h = {"Authorization": f"Bearer {yt_token()}"}
    r = requests.request(method, f"{base}/{path}", params=params or {}, json=body, headers={**h, **kw.pop("headers", {})},
                         timeout=kw.pop("timeout", 120), **kw)
    if r.status_code >= 400:
        raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:400]}")
    return r.json() if r.text.strip() else {}

def yt_upload_video(path, snippet, status, mime="video/mp4"):
    """Resumable upload. snippet: {title, description, tags, categoryId, defaultLanguage?}; status: {privacyStatus, publishAt?, ...}. Returns video id."""
    size = os.path.getsize(path)
    init = requests.post(f"{UPLOAD}/videos", params={"uploadType": "resumable", "part": "snippet,status"},
                         headers={"Authorization": f"Bearer {yt_token()}", "Content-Type": "application/json; charset=UTF-8",
                                  "X-Upload-Content-Type": mime, "X-Upload-Content-Length": str(size)},
                         json={"snippet": snippet, "status": status}, timeout=60)
    if init.status_code >= 400:
        raise RuntimeError(f"upload init -> {init.status_code}: {init.text[:400]}")
    loc = init.headers["Location"]
    with open(path, "rb") as f:
        r = requests.put(loc, data=f, headers={"Content-Type": mime, "Content-Length": str(size)}, timeout=900)
    if r.status_code >= 400:
        raise RuntimeError(f"upload -> {r.status_code}: {r.text[:400]}")
    return r.json()["id"]

def yt_set_thumbnail(video_id, path):
    with open(path, "rb") as f:
        data = f.read()
    mime = "image/png" if path.endswith(".png") else "image/jpeg"
    return yt("POST", "thumbnails/set", {"videoId": video_id, "uploadType": "media"}, base=UPLOAD,
              data=data, headers={"Content-Type": mime})

def yt_insert_caption(video_id, srt_path, lang="en", name="English"):
    boundary = "smlcaptionboundary"
    meta = json.dumps({"snippet": {"videoId": video_id, "language": lang, "name": name, "isDraft": False}})
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n"
            f"--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n").encode() + open(srt_path, "rb").read() + f"\r\n--{boundary}--".encode()
    return yt("POST", "captions", {"part": "snippet", "uploadType": "multipart"}, base=UPLOAD,
              data=body, headers={"Content-Type": f"multipart/related; boundary={boundary}"})

def yt_download(url, path):
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for ch in r.iter_content(1 << 20): f.write(ch)
    return path
