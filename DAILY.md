# Daily run — Simple Money Life

Runs every day at **00:02 America/Los_Angeles**. All YouTube API calls go through `yt_lib.py`, which uses the channel owner's OWN Google Cloud project (credentials in the Composio workbench's private file /mnt/files/sml/yt_creds.json; own quota: 100 uploads + 10,000 units per day, not shared).
Let **X** = today's date in America/Los_Angeles (`TZ=America/Los_Angeles date +%F`).

The pipeline works one day ahead: the video for date X was built yesterday and waits on the `media` branch;
today's run uploads it (main video public at 12:00 Los Angeles = 15:00 New York on X; its teaser Short at 16:00 Los Angeles = 19:00 New York), then builds the video for X+1.

## 1. Setup
- `add_repo` owner `ayyub1nnat`, repo `money-channel-videos`, access `push`; clone to `/home/claude/money-channel-videos`; `register_repo_root`.
- `cd /home/claude/money-channel-videos && bash setup.sh` (≈2–3 min; downloads the voice model).
- Load the Composio tools (ToolSearch `select:mcp__Composio__COMPOSIO_REMOTE_WORKBENCH,mcp__Composio__COMPOSIO_SEARCH_TOOLS`). Call COMPOSIO_SEARCH_TOOLS once (any youtube use case) to get a session id for the workbench. Do NOT use Composio's own YouTube tools (YOUTUBE_*) or proxy_execute for YouTube: their quota is shared and runs out; always use yt_lib.py.
- Check the credentials work: in the workbench run `exec(requests.get(RAW+'/main/yt_lib.py').text); print(yt('GET','channels',{'part':'id','mine':'true'}))`. If the token refresh fails, nothing can be uploaded: build tomorrow's video anyway and tell the owner to redo the short re-authorization in OWN_API_SETUP.md (step 4–5).

## 2. Upload the waiting video
- `curl -s https://raw.githubusercontent.com/ayyub1nnat/money-channel-videos/media/meta.json` → its `date` should be X (or earlier if a previous upload failed).
- Check `topics.json`: if that date's topic already has a `video_id` (or status says uploaded), skip to step 3.
- Run the contents of `upload_snippet.py` unchanged in COMPOSIO_REMOTE_WORKBENCH (load it from the raw URL at the current commit SHA to avoid GitHub's 5-min raw cache, e.g. `RAW/<sha>/upload_snippet.py`). It uploads the main video (scheduled 12:00 LA), thumbnail, English captions, translations, and the teaser Short (16:00 LA). Read the `RESULT` line.
  - ok → record on that topic in topics.json: `video_id`, `short_id`, `status: "scheduled"`, `short_status: "scheduled"`, `localized: true` (if `localized`/`short_localized` are "ok"). Any sub-step that isn't "ok" (thumbnail/captions/localized) → fix and redo just that sub-step with yt_lib (don't re-upload).
  - ok:false → read the error. Never re-run the whole snippet if a video id was already created (check the channel's recent uploads first) — that would duplicate. Fix the cause and retry once; still failing → send the owner the files + title/description/tags for a manual upload and mark `status: "manual upload needed"`.

- Translations for older videos: any topic with a `video_id` and `localized: false` → run `localize_snippet.py` with DATE/MAIN_ID/SHORT_ID set. ok → `localized: true`.

- Channel SEO: run `channel_seo_snippet.py` unchanged (idempotent): channel keywords/translations, adds new long videos to their playlist (ids in playlists.json), posts one question comment under each public long video (scheduled ones get theirs on a later run).

## 3. Build tomorrow's video (date X+1)
Follow RUNBOOK.md sections 1–4 for date X+1 **in the whiteboard style** (`"style": "sketch"` + a `draws` item per line, build with `build_sketch.py`, see RUNBOOK): pick the next unused topic, write `days/<X+1>/script.json`, preview, look at `preview_grid.jpg`, fix issues, full build with `build_sketch.py` (run it in the background, ≈20 min), check frames, write `seo.json`.
Then the teaser Short: add `"short": {"hook": "<= 40 chars, punchy", "clips": [[scene, first_line, last_line], ...]}` to script.json (3–4 clips: the hook + the most striking/visual moments, 35–50 s total; avoid `timeline` scenes, their bottom labels get cropped), keep timeline.json newer than script.json (`touch -r days/<X+1>/timeline.json days/<X+1>/script.json`), run `python3 short.py days/<X+1>` (≈1 min), look at 3–4 frames (no overlapping captions, nothing cut off), and add `"short": {"title", "description", "tags"}` to seo.json (title ≤ 90 chars; `#shorts` and the link are added at upload).

## 4. Save
- On `main`: commit `days/<X+1>/{script.json,seo.json,localizations.json,thumbnail.jpg,subtitles.srt,chapters.txt}` and topics.json (topic → `used: true`, `date: X+1`, `status: "built, waiting for upload"`, `localized: false`), push.
- Media branch (holds ONLY the next video, force-pushed):
  ```bash
  rm -rf /home/claude/media && mkdir /home/claude/media && cd /home/claude/media && git init -q -b media
  cp ../money-channel-videos/days/<X+1>/{video.mp4,thumbnail.jpg,short.mp4} .
  echo '{"date": "<X+1>", "title": "<title>"}' > meta.json
  git add . && git -c user.name=Claude -c user.email=noreply@anthropic.com commit -qm "media <X+1>"
  git remote add origin https://github.com/ayyub1nnat/money-channel-videos && git push -qf origin media
  ```
  Only do this after step 2 succeeded or was handed to the owner — never overwrite a video that still needs uploading without delivering it first.

## 5. Report to the owner (in Azerbaijani, short)
Send with SendUserMessage (and SendUserFile for files):
- Today's video: title + `https://studio.youtube.com/video/<id>/edit`, goes public 12:00 Los Angeles time (Baku: 23:00 the same day until Nov 1, 00:00 next day after). Short: 16:00 Los Angeles (Baku: 03:00 next day until Nov 1, 04:00 after).
- Today's teaser Short: `https://studio.youtube.com/video/<short_id>/edit` (or the file for manual upload if quota ran out).
- Tomorrow's video is ready: title + thumbnail file.
- Any problem, plainly, with what they need to do (e.g. manual upload: attach video.mp4 + title + description).
