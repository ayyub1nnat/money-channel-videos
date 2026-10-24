# Daily run — Simple Money Life

Runs every day at **00:02 America/Los_Angeles** (right after Composio's shared YouTube upload quota resets).
Let **X** = today's date in America/Los_Angeles (`TZ=America/Los_Angeles date +%F`).

The pipeline works one day ahead: the video for date X was built yesterday and waits on the `media` branch;
today's run uploads it (scheduled to go public at 19:00 Los Angeles time on X), then builds the video for X+1.

## 1. Setup
- `add_repo` owner `ayyub1nnat`, repo `money-channel-videos`, access `push`; clone to `/home/claude/money-channel-videos`; `register_repo_root`.
- `cd /home/claude/money-channel-videos && bash setup.sh` (≈2–3 min; downloads the voice model).
- Load the Composio tools (ToolSearch `select:mcp__Composio__COMPOSIO_REMOTE_WORKBENCH,mcp__Composio__COMPOSIO_MULTI_EXECUTE_TOOL,mcp__Composio__COMPOSIO_SEARCH_TOOLS`). Call COMPOSIO_SEARCH_TOOLS once for "upload a video to youtube" to get a session id; YouTube account must show active.

## 2. Upload the waiting video (do this FIRST — quota runs out fast)
- `curl -s https://raw.githubusercontent.com/ayyub1nnat/money-channel-videos/media/meta.json` → its `date` should be X (or earlier if a previous upload failed).
- Check `topics.json`: if that date's topic already has a `video_id` (or status says uploaded), skip to step 3.
- Run the contents of `upload_snippet.py` unchanged in COMPOSIO_REMOTE_WORKBENCH. Read the `RESULT` line.
  - ok → check `captions_error` is null (English CC track added); if not, retry the caption upload alone with YOUTUBE_UPLOAD_CAPTION_TRACK. Record `video_id` and `status: "scheduled"` on that topic in topics.json.
  - Teaser Short: the same run also uploads `media/short.mp4` (same 19:00 publish time, description links to the main video). Record `short_id` on the topic. If `short_error` is a quota error, retry just the Short upload (same code block as in upload_snippet.py, with `vid` = the main video id) at most 3 more times ~3 min apart; still failing → in the report send the owner `short.mp4` + Short title/description from seo.json `short` (with the main video link) so they can upload it in YouTube Studio, scheduled 19:00 Los Angeles.
  - quota error → retry at most 3 more times, ~3 minutes apart (wait with a background `sleep 180` Bash command). Still failing → don't block; continue to step 3 and, in the final report, send the owner the video + title/description so they can upload by hand in YouTube Studio (and mark the topic `status: "manual upload needed"`).
  - any other error → read it, fix the cause if it's in our inputs (e.g. title/description length, tags), retry once.

- Pending Shorts from earlier days: after the step above (main video + its Short handled), look in topics.json for a topic with `short_status: "pending upload"`. Its Short waits on the branch named in `short_branch` (file `short.mp4`). Upload it with the Short code block from upload_snippet.py (video from that branch, `vid` = that topic's `video_id`, title/description from that day's seo.json `short`) and make it public right away (its main video is already public). ok → set `short_id`, `short_status: "uploaded"`, delete the branch if possible. Quota error → leave it pending for the next run; don't retry in a loop.

## 3. Build tomorrow's video (date X+1)
Follow RUNBOOK.md sections 1–4 for date X+1: pick the next unused topic, write `days/<X+1>/script.json`, preview, look at `preview_grid.jpg`, fix issues, full build (run it in the background, ≈15–20 min), check frames, write `seo.json`.
Then the teaser Short: add `"short": {"hook": "<= 40 chars, punchy", "clips": [[scene, first_line, last_line], ...]}` to script.json (3–4 clips: the hook + the most striking/visual moments, 35–50 s total; avoid `timeline` scenes, their bottom labels get cropped), keep timeline.json newer than script.json (`touch -r days/<X+1>/timeline.json days/<X+1>/script.json`), run `python3 short.py days/<X+1>` (≈1 min), look at 3–4 frames (no overlapping captions, nothing cut off), and add `"short": {"title", "description", "tags"}` to seo.json (title ≤ 90 chars; `#shorts` and the link are added at upload).

## 4. Save
- On `main`: commit `days/<X+1>/{script.json,seo.json,thumbnail.jpg,subtitles.srt,chapters.txt}` and topics.json (topic → `used: true`, `date: X+1`, `status: "built, waiting for upload"`), push.
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
- Today's video: title + `https://studio.youtube.com/video/<id>/edit`, goes public 19:00 Los Angeles time (Baku: 06:00 next day until Nov 1, 07:00 after).
- Today's teaser Short: `https://studio.youtube.com/video/<short_id>/edit` (or the file for manual upload if quota ran out).
- Tomorrow's video is ready: title + thumbnail file.
- Any problem, plainly, with what they need to do (e.g. manual upload: attach video.mp4 + title + description).
