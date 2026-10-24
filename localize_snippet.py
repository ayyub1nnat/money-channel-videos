# Paste into COMPOSIO_REMOTE_WORKBENCH; set DATE (and MAIN_ID / SHORT_ID if known, else they're looked up
# in the channel's recent uploads by title). Adds translated titles/descriptions (YouTube "localizations")
# from days/<DATE>/localizations.json to the main video and its Short, so viewers in those languages see
# the title/description in their own language. Uses API units only (no upload quota); still needs the
# daily API quota, so run it right after the quota reset. Prints LOCALIZE {...}.
import requests, json

DATE = "YYYY-MM-DD"
MAIN_ID = None
SHORT_ID = None
REPO = "ayyub1nnat/money-channel-videos"
RAW = f"https://raw.githubusercontent.com/{REPO}"
API = "https://www.googleapis.com/youtube/v3"

seo = requests.get(f"{RAW}/main/days/{DATE}/seo.json", timeout=60).json()
loc = requests.get(f"{RAW}/main/days/{DATE}/localizations.json", timeout=60).json()

def get(path, **q):
    r, e = proxy_execute("GET", f"{API}/{path}", "youtube", query_params=q)
    if e: raise RuntimeError(str(e)[:300])
    return r.get("data", r) if isinstance(r, dict) else r

def find_upload(pred):
    ch = get("channels", part="contentDetails", mine="true")
    up = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    items = get("playlistItems", part="snippet", playlistId=up, maxResults="50")["items"]
    for it in items:
        if pred(it["snippet"]["title"]): return it["snippet"]["resourceId"]["videoId"]
    return None

def localize(vid, locs):
    v = get("videos", part="snippet,localizations", id=vid)["items"][0]
    sn = v["snippet"]
    body = {"id": vid,
            "snippet": {"title": sn["title"], "description": sn.get("description", ""), "categoryId": sn["categoryId"],
                        "tags": sn.get("tags", []), "defaultLanguage": sn.get("defaultLanguage") or "en"},
            "localizations": dict(v.get("localizations", {}), **locs)}
    r, e = proxy_execute("PUT", f"{API}/videos", "youtube", query_params={"part": "snippet,localizations"}, body=body)
    return str(e)[:300] if e else "ok"

out = {"date": DATE}
try:
    main_title = seo["title"]
    if not MAIN_ID: MAIN_ID = find_upload(lambda t: t.strip() == main_title.strip())
    main_locs = {k: {"title": v["title"][:100], "description": v["description"][:4900]} for k, v in loc.items() if not k.startswith("_")}
    out["main"] = (MAIN_ID, localize(MAIN_ID, main_locs) if MAIN_ID else "main video not found")
    sh = seo.get("short", {}); sl = loc.get("_short", {})
    if sh and sl:
        if not SHORT_ID:
            st = sh["title"].lower()[:40]
            SHORT_ID = find_upload(lambda t: t.lower().startswith(st) or (st[:25] in t.lower() and "#shorts" in t.lower()))
        link = f"▶️ https://youtu.be/{MAIN_ID}\n\n" if MAIN_ID else ""
        short_locs = {k: {"title": v["title"][:100], "description": link + v["description"]} for k, v in sl.items()}
        out["short"] = (SHORT_ID, localize(SHORT_ID, short_locs) if SHORT_ID else "short not found")
except Exception as ex:
    out["error"] = str(ex)[:300]
print("LOCALIZE", json.dumps(out, ensure_ascii=False))
