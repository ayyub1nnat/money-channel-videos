# Paste into COMPOSIO_REMOTE_WORKBENCH as-is. Uploads the video waiting on the `media` branch
# (date in media/meta.json) to YouTube as private and schedules it for 19:00 America/Los_Angeles
# on that date; if that time has passed, publishes immediately. Prints RESULT {...} at the end.
# Composio's YouTube upload quota is shared and resets at midnight America/Los_Angeles,
# so this should run right after that. On HTTP 429 it prints RESULT {"ok": false, "quota": true}.
import requests, json, datetime
from zoneinfo import ZoneInfo

REPO = "ayyub1nnat/money-channel-videos"
RAW = f"https://raw.githubusercontent.com/{REPO}"
meta = requests.get(f"{RAW}/media/meta.json", timeout=60).json()
DATE = meta["date"]
seo = requests.get(f"{RAW}/main/days/{DATE}/seo.json", timeout=60).json()

p = "/home/user/video.mp4"
with requests.get(f"{RAW}/media/video.mp4", stream=True, timeout=300) as r:
    r.raise_for_status()
    with open(p, "wb") as f:
        for ch in r.iter_content(1 << 20): f.write(ch)
up, err = upload_local_file(p); assert not err, err

res, err = run_composio_tool("YOUTUBE_MULTIPART_UPLOAD_VIDEO", {
    "title": seo["title"][:100], "description": seo["description"], "tags": seo["tags"],
    "categoryId": seo.get("categoryId", "27"), "privacyStatus": "private",
    "videoFile": {"name": "video.mp4", "mimetype": "video/mp4", "s3key": up["s3key"]}})
if err:
    print("RESULT", json.dumps({"ok": False, "date": DATE, "quota": "429" in str(err) or "quota" in str(err).lower(),
                                "error": str(err)[:300]}))
else:
    d = res.get("data", res)
    v = d.get("video") or d.get("response_data") or d
    vid = v.get("id")
    et = ZoneInfo("America/Los_Angeles")
    y, m, dd = map(int, DATE.split("-"))
    pub = datetime.datetime(y, m, dd, 19, 0, tzinfo=et)
    now = datetime.datetime.now(datetime.timezone.utc)
    if pub > now + datetime.timedelta(minutes=15):
        status = {"privacyStatus": "private", "selfDeclaredMadeForKids": False,
                  "publishAt": pub.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    else:
        status = {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    r2, e2 = proxy_execute("PUT", "/youtube/v3/videos", "youtube", query_params={"part": "status"},
                           body={"id": vid, "status": status})
    r3, e3 = run_composio_tool("YOUTUBE_UPDATE_THUMBNAIL", {"videoId": vid, "thumbnailUrl": f"{RAW}/media/thumbnail.jpg"})
    r4, e4 = run_composio_tool("YOUTUBE_GET_VIDEO_DETAILS_BATCH", {"id": [vid], "parts": ["status"]})
    print("RESULT", json.dumps({"ok": True, "date": DATE, "video_id": vid, "status_set": status,
                                "status_error": str(e2)[:300] if e2 else None,
                                "thumbnail_error": str(e3)[:300] if e3 else None,
                                "status_now": json.dumps(r4, default=str)[:600]}))
