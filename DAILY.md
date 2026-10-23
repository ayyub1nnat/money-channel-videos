# Daily run — Simple Money Life

Runs every day at **00:02 America/Los_Angeles** (right after Composio's shared YouTube upload quota resets).
Let **X** = today's date in America/Los_Angeles (`TZ=America/Los_Angeles date +%F`).

The pipeline works one day ahead: the video for date X was built yesterday and waits on the `media` branch;
today's run uploads it (scheduled to go public at 18:00 Los Angeles time on X), then builds the video for X+1.

## 1. Setup
- `add_repo` owner `ayyub1nnat`, repo `money-channel-videos`, access `push`; clone to `/home/claude/money-channel-videos`; `register_repo_root`.
- `cd /home/claude/money-channel-videos && bash setup.sh` (≈2–3 min; downloads the voice model).
- Load the Composio tools (ToolSearch `select:mcp__Composio__COMPOSIO_REMOTE_WORKBENCH,mcp__Composio__COMPOSIO_MULTI_EXECUTE_TOOL,mcp__Composio__COMPOSIO_SEARCH_TOOLS`). Call COMPOSIO_SEARCH_TOOLS once for "upload a video to youtube" to get a session id; YouTube account must show active.

## 2. Upload the waiting video (do this FIRST — quota runs out fast)
- `curl -s https://raw.githubusercontent.com/ayyub1nnat/money-channel-videos/media/meta.json` → its `date` should be X (or earlier if a previous upload failed).
- Check `topics.json`: if that date's topic already has a `video_id` (or status says uploaded), skip to step 3.
- Run the contents of `upload_snippet.py` unchanged in COMPOSIO_REMOTE_WORKBENCH. Read the `RESULT` line.
  - ok → record `video_id` and `status: "scheduled"` on that topic in topics.json.
  - quota error → retry at most 3 more times, ~3 minutes apart (wait with a background `sleep 180` Bash command). Still failing → don't block; continue to step 3 and, in the final report, send the owner the video + title/description so they can upload by hand in YouTube Studio (and mark the topic `status: "manual upload needed"`).
  - any other error → read it, fix the cause if it's in our inputs (e.g. title/description length, tags), retry once.

## 3. Build tomorrow's video (date X+1)
Follow RUNBOOK.md sections 1–4 for date X+1: pick the next unused topic, write `days/<X+1>/script.json`, preview, look at `preview_grid.jpg`, fix issues, full build (run it in the background, ≈15–20 min), check frames, write `seo.json`.

## 4. Save
- On `main`: commit `days/<X+1>/{script.json,seo.json,thumbnail.jpg,subtitles.srt,chapters.txt}` and topics.json (topic → `used: true`, `date: X+1`, `status: "built, waiting for upload"`), push.
- Media branch (holds ONLY the next video, force-pushed):
  ```bash
  rm -rf /home/claude/media && mkdir /home/claude/media && cd /home/claude/media && git init -q -b media
  cp ../money-channel-videos/days/<X+1>/{video.mp4,thumbnail.jpg} .
  echo '{"date": "<X+1>", "title": "<title>"}' > meta.json
  git add . && git -c user.name=Claude -c user.email=noreply@anthropic.com commit -qm "media <X+1>"
  git remote add origin https://github.com/ayyub1nnat/money-channel-videos && git push -qf origin media
  ```
  Only do this after step 2 succeeded or was handed to the owner — never overwrite a video that still needs uploading without delivering it first.

## 5. Report to the owner (in Azerbaijani, short)
Send with SendUserMessage (and SendUserFile for files):
- Today's video: title + `https://studio.youtube.com/video/<id>/edit`, goes public 18:00 Los Angeles time (Baku: 05:00 next day until Nov 1, 06:00 after).
- Tomorrow's video is ready: title + thumbnail file.
- Any problem, plainly, with what they need to do (e.g. manual upload: attach video.mp4 + title + description).
