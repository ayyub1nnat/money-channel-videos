# One-off: replace an already-scheduled main video with a rebuilt version (same date/slot).
# Set OLD_ID, SHORT_ID, SRC (raw base where video.mp4/thumbnail.jpg live) and DATE. Uploads the new video
# with the same publish time, thumbnail, captions and translations; points the Short's description to the
# new video; swaps the playlist entry; and turns the old video back into a plain private video (unscheduled,
# title prefixed "[old]") so the owner can delete it in Studio. Prints REPLACE {...}.
import requests, json, datetime
DATE = "YYYY-MM-DD"; OLD_ID = ""; SHORT_ID = ""; SRC = ""; MEDIA = ""   # SRC: raw base of main (days/...), MEDIA: raw base holding video.mp4 + thumbnail.jpg
REPO = "ayyub1nnat/money-channel-videos"; RAW = f"https://raw.githubusercontent.com/{REPO}"
exec(requests.get(f"{RAW}/main/yt_lib.py", timeout=60).text)
seo = requests.get(f"{SRC}/days/{DATE}/seo.json", timeout=60).json()
loc = requests.get(f"{SRC}/days/{DATE}/localizations.json", timeout=60).json()
out = {}
old = yt("GET", "videos", {"part": "snippet,status", "id": OLD_ID})["items"][0]
st = {k: old["status"][k] for k in ("privacyStatus", "publishAt", "selfDeclaredMadeForKids", "embeddable", "publicStatsViewable", "license") if k in old["status"]}
vid = yt_upload_video(yt_download(f"{MEDIA}/video.mp4", "/home/user/v2.mp4"),
                      {"title": seo["title"][:100], "description": seo["description"][:4900], "tags": seo["tags"],
                       "categoryId": seo.get("categoryId", "27"), "defaultLanguage": "en", "defaultAudioLanguage": "en"}, st)
out["new_id"] = vid; out["status"] = st
for name, fn in [("thumbnail", lambda: yt_set_thumbnail(vid, yt_download(f"{MEDIA}/thumbnail.jpg", "/home/user/t2.jpg"))),
                 ("captions", lambda: yt_insert_caption(vid, yt_download(f"{SRC}/days/{DATE}/subtitles.srt", "/home/user/s2.srt")))]:
    try: fn(); out[name] = "ok"
    except Exception as ex: out[name] = str(ex)[:300]
def relocalize(v_id, locs, fix=None):
    v = yt("GET", "videos", {"part": "snippet,localizations", "id": v_id})["items"][0]; sn = v["snippet"]
    desc = sn.get("description", ""); L = dict(v.get("localizations", {}), **locs)
    if fix:
        desc = desc.replace(*fix); L = {k: {"title": x["title"], "description": x["description"].replace(*fix)} for k, x in L.items()}
    yt("PUT", "videos", {"part": "snippet,localizations"}, {"id": v_id, "snippet": {"title": sn["title"], "description": desc,
       "categoryId": sn["categoryId"], "tags": sn.get("tags", []), "defaultLanguage": "en"}, "localizations": L})
try:
    relocalize(vid, {k: {"title": x["title"][:100], "description": x["description"][:4900]} for k, x in loc.items() if not k.startswith("_")}); out["localized"] = "ok"
except Exception as ex: out["localized"] = str(ex)[:300]
try:
    relocalize(SHORT_ID, {}, (OLD_ID, vid)); out["short_link"] = "ok"
except Exception as ex: out["short_link"] = str(ex)[:300]
try:
    pls = yt("GET", "playlists", {"part": "id", "mine": "true", "maxResults": "50"})["items"]
    for p in pls:
        for it in yt("GET", "playlistItems", {"part": "snippet", "playlistId": p["id"], "maxResults": "50"}).get("items", []):
            if it["snippet"]["resourceId"]["videoId"] == OLD_ID:
                yt("POST", "playlistItems", {"part": "snippet"}, {"snippet": {"playlistId": p["id"], "resourceId": {"kind": "youtube#video", "videoId": vid}}})
                yt("DELETE", "playlistItems", {"id": it["id"]})
                out["playlist"] = p["id"]
except Exception as ex: out["playlist"] = str(ex)[:300]
try:
    sn = old["snippet"]
    yt("PUT", "videos", {"part": "snippet,status"}, {"id": OLD_ID, "snippet": {"title": ("[old] " + sn["title"])[:100], "description": sn.get("description", ""),
       "categoryId": sn["categoryId"], "tags": sn.get("tags", [])}, "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False}})
    out["old"] = "unscheduled, private"
except Exception as ex: out["old"] = str(ex)[:300]
print("REPLACE", json.dumps(out, ensure_ascii=False))
