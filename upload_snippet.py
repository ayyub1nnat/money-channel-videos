# Paste into COMPOSIO_REMOTE_WORKBENCH as-is. Uses the channel's OWN Google Cloud project via yt_lib.py
# (own quota, not shared). Uploads the video waiting on the `media` branch (date in media/meta.json):
#   main video  → private, publishAt 06:00 Asia/Baku on that date (public now if that time passed)
#   thumbnail, English CC track (days/<date>/subtitles.srt), translated titles/descriptions (localizations.json)
#   Short (media/short.mp4, if present) → publishAt 06:00 Asia/Baku too, description links to the main video
# Prints RESULT {...}. Safe to re-run only if RESULT was not ok (otherwise it would upload a duplicate).
import requests, json, datetime
from zoneinfo import ZoneInfo
REPO = "ayyub1nnat/money-channel-videos"
RAW = f"https://raw.githubusercontent.com/{REPO}"
exec(requests.get(f"{RAW}/main/yt_lib.py", timeout=60).text)

meta = requests.get(f"{RAW}/media/meta.json", timeout=60).json()
DATE = meta["date"]
seo = requests.get(f"{RAW}/main/days/{DATE}/seo.json", timeout=60).json()
lr = requests.get(f"{RAW}/main/days/{DATE}/localizations.json", timeout=60)
loc = lr.json() if lr.status_code == 200 else {}

LA = ZoneInfo("Asia/Baku")   # owner's choice (2026-10-26): video AND its Short public at 06:00 Baku (= evening in the US); standalone Short 19:00
y, m, d = map(int, DATE.split("-"))
now = datetime.datetime.now(datetime.timezone.utc)
def status_for(hour):
    t = datetime.datetime(y, m, d, hour, 0, tzinfo=LA)
    base = {"selfDeclaredMadeForKids": False, "embeddable": True, "publicStatsViewable": True, "license": "youtube"}
    if t > now + datetime.timedelta(minutes=15):
        return dict(base, privacyStatus="private", publishAt=t.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    return dict(base, privacyStatus="public")

def localize(vid, locs):
    if not locs: return None
    v = yt("GET", "videos", {"part": "snippet,localizations", "id": vid})["items"][0]; sn = v["snippet"]
    yt("PUT", "videos", {"part": "snippet,localizations"}, {"id": vid,
       "snippet": {"title": sn["title"], "description": sn.get("description", ""), "categoryId": sn["categoryId"],
                   "tags": sn.get("tags", []), "defaultLanguage": "en"},
       "localizations": dict(v.get("localizations", {}), **locs)})

out = {"date": DATE}
try:
    p = yt_download(f"{RAW}/media/video.mp4", "/home/user/video.mp4")
    st = status_for(6)
    vid = yt_upload_video(p, {"title": seo["title"][:100], "description": seo["description"][:4900], "tags": seo["tags"],
                              "categoryId": seo.get("categoryId", "27"), "defaultLanguage": "en", "defaultAudioLanguage": "en"}, st)
    out.update(ok=True, video_id=vid, status_set=st)
    for name, fn in [("thumbnail", lambda: yt_set_thumbnail(vid, yt_download(f"{RAW}/media/thumbnail.jpg", "/home/user/thumb.jpg"))),
                     ("captions", lambda: yt_insert_caption(vid, yt_download(f"{RAW}/main/days/{DATE}/subtitles.srt", "/home/user/sub.srt"))),
                     ("localized", lambda: localize(vid, {k: {"title": v["title"][:100], "description": v["description"][:4900]}
                                                          for k, v in loc.items() if not k.startswith("_")}))]:
        try: fn(); out[name] = "ok"
        except Exception as ex: out[name] = str(ex)[:300]
    # teaser Short
    if requests.head(f"{RAW}/media/short.mp4", timeout=60, allow_redirects=True).status_code == 200:
        try:
            sh = seo.get("short", {}); link = f"https://youtu.be/{vid}"
            stitle = (sh.get("title") or seo["title"])[:90]
            if "#shorts" not in stitle.lower(): stitle = (stitle + " #shorts")[:100]
            sdesc = (f"▶️ Watch the full video: {link}\n\n" + sh.get("description", seo["description"].split("\n\n")[0])
                     + "\n\nThis video is for educational purposes only and is not financial advice.\n\n#shorts #personalfinance #money")
            sid = yt_upload_video(yt_download(f"{RAW}/media/short.mp4", "/home/user/short.mp4"),
                                  {"title": stitle, "description": sdesc[:4900], "tags": sh.get("tags", seo["tags"][:10]) + ["shorts"],
                                   "categoryId": seo.get("categoryId", "27"), "defaultLanguage": "en", "defaultAudioLanguage": "en"}, status_for(6))
            out["short_id"] = sid
            try:
                localize(sid, {k: {"title": v["title"][:100], "description": f"▶️ {link}\n\n" + v["description"]}
                               for k, v in loc.get("_short", {}).items()})
                out["short_localized"] = "ok"
            except Exception as ex: out["short_localized"] = str(ex)[:300]
        except Exception as ex:
            out["short_error"] = str(ex)[:300]
    # standalone Short (media/short2.mp4, own topic, no link to the main video) → public 19:00 Baku
    if requests.head(f"{RAW}/media/short2.mp4", timeout=60, allow_redirects=True).status_code == 200:
        try:
            s2 = seo.get("short2", {})
            t2 = s2["title"][:90]
            if "#shorts" not in t2.lower(): t2 = (t2 + " #shorts")[:100]
            d2 = (s2.get("description", "") + "\n\n▶️ More simple money moves every day: https://www.youtube.com/@simplemoneylifeez"
                  + "\n\nThis video is for educational purposes only and is not financial advice.\n\n#shorts #personalfinance #money")
            sid2 = yt_upload_video(yt_download(f"{RAW}/media/short2.mp4", "/home/user/short2.mp4"),
                                   {"title": t2, "description": d2[:4900], "tags": s2.get("tags", []) + ["shorts"],
                                    "categoryId": "27", "defaultLanguage": "en", "defaultAudioLanguage": "en"}, status_for(19))
            out["short2_id"] = sid2
            try:
                yt_insert_caption(sid2, yt_download(f"{RAW}/main/days/{DATE}/short2/subtitles.srt", "/home/user/s2.srt")); out["short2_captions"] = "ok"
            except Exception as ex: out["short2_captions"] = str(ex)[:300]
            try:
                localize(sid2, loc.get("_short2", {})); out["short2_localized"] = "ok"
            except Exception as ex: out["short2_localized"] = str(ex)[:300]
        except Exception as ex:
            out["short2_error"] = str(ex)[:300]
except Exception as ex:
    out.update(ok=False, error=str(ex)[:400])
print("RESULT", json.dumps(out, ensure_ascii=False))
