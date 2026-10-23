# Paste into COMPOSIO_REMOTE_WORKBENCH (set DATE first). Uploads today's video from the repo's
# `media` branch to YouTube as private, schedules it for 20:00 America/New_York, sets the thumbnail.
# If 20:00 ET has already passed, it publishes immediately.
import requests, json, datetime
from zoneinfo import ZoneInfo

DATE = "YYYY-MM-DD"
REPO = "ayyub1nnat/money-channel-videos"
RAW = f"https://raw.githubusercontent.com/{REPO}"

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
assert not err, err
d = res.get("data", res); vid = (d.get("video") or d.get("response_data") or d).get("id")
print("video id:", vid)

et = ZoneInfo("America/New_York")
y, m, dd = map(int, DATE.split("-"))
pub = datetime.datetime(y, m, dd, 20, 0, tzinfo=et)
now = datetime.datetime.now(datetime.timezone.utc)
if pub > now + datetime.timedelta(minutes=15):
    status = {"privacyStatus": "private", "publishAt": pub.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "selfDeclaredMadeForKids": False}
else:
    status = {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
r2, err = proxy_execute("PUT", "/youtube/v3/videos", "youtube", query_params={"part": "status"},
                        body={"id": vid, "status": status})
print("status:", err or r2)

r3, err = run_composio_tool("YOUTUBE_UPDATE_THUMBNAIL", {"videoId": vid, "thumbnailUrl": f"{RAW}/media/thumbnail.jpg"})
print("thumbnail:", err or "ok")
r4, err = run_composio_tool("YOUTUBE_GET_VIDEO_DETAILS_BATCH", {"id": [vid], "parts": ["status", "snippet"]})
print(json.dumps(r4, default=str)[:1500])
