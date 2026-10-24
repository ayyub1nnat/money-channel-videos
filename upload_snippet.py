# Paste into COMPOSIO_REMOTE_WORKBENCH as-is. Uploads the video waiting on the `media` branch
# (date in media/meta.json) to YouTube as private and schedules it for 12:00 America/Los_Angeles (= 15:00 New York)
# on that date; if that time has passed, publishes immediately. Prints RESULT {...} at the end.
# Composio's YouTube upload quota is shared and resets at midnight America/Los_Angeles,
# Also adds the English CC track from days/<date>/subtitles.srt, and uploads the teaser Short
# (media/short.mp4, if present) scheduled for the same time, with a link to the main video.
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
    pub = datetime.datetime(y, m, dd, 12, 0, tzinfo=et)            # main video: 12:00 LA = 15:00 NY
    spub = datetime.datetime(y, m, dd, 16, 0, tzinfo=et)           # Short: 16:00 LA = 19:00 NY (evening Shorts peak)
    now = datetime.datetime.now(datetime.timezone.utc)
    if pub > now + datetime.timedelta(minutes=15):
        status = {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "embeddable": True, "publicStatsViewable": True, "license": "youtube",
                  "publishAt": pub.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    else:
        status = {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "embeddable": True, "publicStatsViewable": True, "license": "youtube"}
    r2, e2 = proxy_execute("PUT", "https://www.googleapis.com/youtube/v3/videos", "youtube", query_params={"part": "status"},
                           body={"id": vid, "status": status})
    r3, e3 = run_composio_tool("YOUTUBE_UPDATE_THUMBNAIL", {"videoId": vid, "thumbnailUrl": f"{RAW}/media/thumbnail.jpg"})
    e5 = None
    try:
        sr = requests.get(f"{RAW}/main/days/{DATE}/subtitles.srt", timeout=60); sr.raise_for_status()
        open("/home/user/subtitles.srt", "w").write(sr.text)
        cup, e5 = upload_local_file("/home/user/subtitles.srt")
        if not e5:
            r5, e5 = run_composio_tool("YOUTUBE_UPLOAD_CAPTION_TRACK", {"videoId": vid, "language": "en", "name": "English",
                "isDraft": False, "file": {"name": "subtitles.srt", "mimetype": "application/octet-stream", "s3key": cup["s3key"]}})
    except Exception as ex:
        e5 = ex
    if spub > now + datetime.timedelta(minutes=15):
        sstatus = dict(status, privacyStatus="private", publishAt=spub.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    else:
        sstatus = {k: v for k, v in status.items() if k != "publishAt"}; sstatus["privacyStatus"] = "public"
    # teaser Short (media/short.mp4, built by short.py): published 16:00 LA (19:00 NY), links to the main video
    short_id, e6 = None, None
    try:
        hs = requests.head(f"{RAW}/media/short.mp4", timeout=60, allow_redirects=True)
        if hs.status_code == 200:
            sp = "/home/user/short.mp4"
            with requests.get(f"{RAW}/media/short.mp4", stream=True, timeout=300) as r:
                r.raise_for_status()
                with open(sp, "wb") as f:
                    for ch in r.iter_content(1 << 20): f.write(ch)
            sup, e6 = upload_local_file(sp)
            if not e6:
                sh = seo.get("short", {})
                link = f"https://youtu.be/{vid}"
                stitle = (sh.get("title") or seo["title"])[:90]
                if "#shorts" not in stitle.lower(): stitle = (stitle + " #shorts")[:100]
                sdesc = (f"▶️ Watch the full video: {link}\n\n" + sh.get("description", seo["description"].split("\n\n")[0])
                         + "\n\nThis video is for educational purposes only and is not financial advice.\n\n#shorts #personalfinance #money")
                rs, e6 = run_composio_tool("YOUTUBE_MULTIPART_UPLOAD_VIDEO", {
                    "title": stitle, "description": sdesc[:4900], "tags": sh.get("tags", seo["tags"][:10]) + ["shorts"],
                    "categoryId": seo.get("categoryId", "27"), "privacyStatus": "private",
                    "videoFile": {"name": "short.mp4", "mimetype": "video/mp4", "s3key": sup["s3key"]}})
                if not e6:
                    dsh = rs.get("data", rs); short_id = (dsh.get("video") or dsh.get("response_data") or dsh).get("id")
                    _, e6 = proxy_execute("PUT", "https://www.googleapis.com/youtube/v3/videos", "youtube",
                                          query_params={"part": "status"}, body={"id": short_id, "status": sstatus})
    except Exception as ex:
        e6 = ex
    r4, e4 = run_composio_tool("YOUTUBE_GET_VIDEO_DETAILS_BATCH", {"id": [vid], "parts": ["status"]})
    print("RESULT", json.dumps({"ok": True, "date": DATE, "video_id": vid, "status_set": status,
                                "status_error": str(e2)[:300] if e2 else None,
                                "thumbnail_error": str(e3)[:300] if e3 else None,
                                "captions_error": str(e5)[:300] if e5 else None,
                                "short_id": short_id, "short_error": str(e6)[:300] if e6 else None,
                                "status_now": json.dumps(r4, default=str)[:600]}))
