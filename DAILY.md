# Daily run — Simple Money Life

Runs every day at **09:30 Asia/Baku**. Main video AND its Short go public at **11:00 Asia/Baku**; a second, standalone Short at **19:00 Asia/Baku** (owner's choice, 2026-10-25). All YouTube API calls go through `yt_lib.py`, which uses the channel owner's OWN Google Cloud project (credentials in the Composio workbench's private file /mnt/files/sml/yt_creds.json; own quota: 100 uploads + 10,000 units per day, not shared).
Let **X** = today's date in Asia/Baku (`TZ=Asia/Baku date +%F`).

The pipeline works one day ahead: the video for date X was built yesterday and waits on the `media` branch;
today's run uploads it (main video and Short both public at 11:00 Baku time on X), then builds the video for X+1.

## 1. Setup
- `add_repo` owner `ayyub1nnat`, repo `money-channel-videos`, access `push`; clone to `/home/claude/money-channel-videos`; `register_repo_root`.
- `cd /home/claude/money-channel-videos && bash setup.sh` (≈2–3 min; downloads the voice model).
- Load the Composio tools (ToolSearch `select:mcp__Composio__COMPOSIO_REMOTE_WORKBENCH,mcp__Composio__COMPOSIO_SEARCH_TOOLS`). Call COMPOSIO_SEARCH_TOOLS once (any youtube use case) to get a session id for the workbench. Do NOT use Composio's own YouTube tools (YOUTUBE_*) or proxy_execute for YouTube: their quota is shared and runs out; always use yt_lib.py.
- Check the credentials work: in the workbench run `exec(requests.get(RAW+'/main/yt_lib.py').text); print(yt('GET','channels',{'part':'id','mine':'true'}))`. If the token refresh fails, nothing can be uploaded: build tomorrow's video anyway and tell the owner to redo the short re-authorization in OWN_API_SETUP.md (step 4–5).

## 2. Upload the waiting video
- `curl -s https://raw.githubusercontent.com/ayyub1nnat/money-channel-videos/media/meta.json` → its `date` should be X (or earlier if a previous upload failed).
- Check `topics.json`: if that date's topic already has a `video_id` (or status says uploaded), skip to step 3.
- Run the contents of `upload_snippet.py` unchanged in COMPOSIO_REMOTE_WORKBENCH (load it from the raw URL at the current commit SHA to avoid GitHub's 5-min raw cache, e.g. `RAW/<sha>/upload_snippet.py`). It uploads the main video and the Short (both scheduled 11:00 Baku), thumbnail, English captions and translations. Read the `RESULT` line.
  - ok → record on that topic in topics.json: `video_id`, `short_id`, `status: "scheduled"`, `short_status: "scheduled"`, `short2_id`, `localized: true` (if `localized`/`short_localized` are "ok"). Any sub-step that isn't "ok" (thumbnail/captions/localized) → fix and redo just that sub-step with yt_lib (don't re-upload).
  - ok:false → read the error. Never re-run the whole snippet if a video id was already created (check the channel's recent uploads first) — that would duplicate. Fix the cause and retry once; still failing → send the owner the files + title/description/tags for a manual upload and mark `status: "manual upload needed"`.

- Translations for older videos: any topic with a `video_id` and `localized: false` → run `localize_snippet.py` with DATE/MAIN_ID/SHORT_ID set. ok → `localized: true`.

- Channel SEO: run `channel_seo_snippet.py` unchanged (idempotent): channel keywords/translations, adds new long videos to their playlist (ids in playlists.json), posts one question comment under each public long video (scheduled ones get theirs on a later run).

## 3. Build tomorrow's video (date X+1)
Use the ★ "fast whiteboard" format from RUNBOOK.md (one line + one drawing per scene, emotional voice, `big_headings`, chapters):
pick the next unused topic, write `days/<X+1>/script.json` (+ `"thumbnail"`), run `python3 build_sketch.py days/<X+1> --preview`, look at `preview_grid.jpg`,
fix issues, then `python3 build_sketch.py days/<X+1>` in the background (≈15-20 min) → video.mp4, subtitles.srt, chapters.txt, thumbnail.
Then the Short: write its OWN script `days/<X+1>/short_v/script.json` (vertical, 8-10 scenes, see RUNBOOK), `python3 build_sketch.py days/<X+1>/short_v`,
`cp days/<X+1>/short_v/short.mp4 days/<X+1>/short.mp4`.
Then the SECOND, standalone Short (owner's choice 2026-10-25: 2 Shorts a day): a different, self-contained topic (not about the main video,
no "full video" call — end with "follow for one simple money move every day"), same vertical fast format, 8-10 scenes, truthful hook
(example: shorts/2026-10-25-subscriptions/script.json). Write `days/<X+1>/short2/script.json`, `python3 build_sketch.py days/<X+1>/short2`,
`cp days/<X+1>/short2/short.mp4 days/<X+1>/short2.mp4`. It goes public at 19:00 Baku.
Check 3-4 frames of each. Write seo.json (with chapters from chapters.txt, the `short` title/description/tags and the `short2`
title/description/tags) and localizations.json (incl. `_short` and `_short2`).

## 4. Save
- On `main`: commit `days/<X+1>/{script.json,seo.json,localizations.json,thumbnail.jpg,subtitles.srt,chapters.txt,timeline.json}` and `days/<X+1>/short_v/{script.json,timeline.json}` and `days/<X+1>/short2/{script.json,timeline.json,subtitles.srt}` and topics.json (topic → `used: true`, `date: X+1`, `status: "built, waiting for upload"`, `localized: false`), push.
- Media branch (holds ONLY the next video, force-pushed):
  ```bash
  rm -rf /home/claude/media && mkdir /home/claude/media && cd /home/claude/media && git init -q -b media
  cp ../money-channel-videos/days/<X+1>/{video.mp4,thumbnail.jpg,short.mp4,short2.mp4} .
  echo '{"date": "<X+1>", "title": "<title>"}' > meta.json
  git add . && git -c user.name=Claude -c user.email=noreply@anthropic.com commit -qm "media <X+1>"
  git remote add origin https://github.com/ayyub1nnat/money-channel-videos && git push -qf origin media
  ```
  Only do this after step 2 succeeded or was handed to the owner — never overwrite a video that still needs uploading without delivering it first.

## 5. Report to the owner (in Azerbaijani, short)
Send with SendUserMessage (and SendUserFile for files):
- Today's video and Short: titles + `https://studio.youtube.com/video/<id>/edit` links, both go public at 11:00 Baku time.
- Today's standalone Short (`short2_id`, 19:00 Baku) and teaser Short: `https://studio.youtube.com/video/<short_id>/edit` (or the file for manual upload if quota ran out).
- Tomorrow's video is ready: title + thumbnail file.
- Any problem, plainly, with what they need to do (e.g. manual upload: attach video.mp4 + title + description).
