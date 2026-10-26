# Daily run — Simple Money Life

Runs every day at **09:30 Asia/Baku**. Main video AND its Short go public at **08:00 Asia/Baku** (owner's choice 2026-10-26); the standalone Short at **19:00 Asia/Baku**. All YouTube API calls go through `yt_lib.py`, which uses the channel owner's OWN Google Cloud project (credentials in the Composio workbench's private file /mnt/files/sml/yt_creds.json; own quota: 100 uploads + 10,000 units per day, not shared).
Let **X** = today's date in Asia/Baku (`TZ=Asia/Baku date +%F`).

Because 08:00 is before the run, each run BUILDS the content for date X+1 and UPLOADS it in the same run, scheduled for
08:00 (video + teaser Short) and 19:00 (standalone Short) on X+1. Order: setup → step 2 (catch-up only) → step 3 build X+1 →
step 4 save + media branch → step 2 again for X+1 (upload) → step 5 report.

## 1. Setup
- `add_repo` owner `ayyub1nnat`, repo `money-channel-videos`, access `push`; clone to `/home/claude/money-channel-videos`; `register_repo_root`.
- `cd /home/claude/money-channel-videos && bash setup.sh` (≈2–3 min; downloads the voice model).
- Load the Composio tools (ToolSearch `select:mcp__Composio__COMPOSIO_REMOTE_WORKBENCH,mcp__Composio__COMPOSIO_SEARCH_TOOLS`). Call COMPOSIO_SEARCH_TOOLS once (any youtube use case) to get a session id for the workbench. Do NOT use Composio's own YouTube tools (YOUTUBE_*) or proxy_execute for YouTube: their quota is shared and runs out; always use yt_lib.py.
- Check the credentials work: in the workbench run `exec(requests.get(RAW+'/main/yt_lib.py').text); print(yt('GET','channels',{'part':'id','mine':'true'}))`. If the token refresh fails, nothing can be uploaded: build tomorrow's video anyway and tell the owner to redo the short re-authorization in OWN_API_SETUP.md (step 4–5).

## 2. Upload (catch-up first, then X+1 after step 4)
- `curl -s https://raw.githubusercontent.com/ayyub1nnat/money-channel-videos/media/meta.json` → `date`. At the START of the run it should already be uploaded (it is X, uploaded yesterday); if its topic has no `video_id`, upload it now (catch-up: anything whose time already passed goes public immediately). After step 4 it is X+1 → upload it.
- Check `topics.json`: if that date's topic already has a `video_id` (or status says uploaded), skip to step 3.
- Run the contents of `upload_snippet.py` unchanged in COMPOSIO_REMOTE_WORKBENCH (load it from the raw URL at the current commit SHA to avoid GitHub's 5-min raw cache, e.g. `RAW/<sha>/upload_snippet.py`). It uploads the main video and its Short (scheduled 08:00 Baku on the media date), the standalone Short (19:00 Baku), thumbnail, English captions and translations. Read the `RESULT` line.
  - ok → record on that topic in topics.json: `video_id`, `short_id`, `status: "scheduled"`, `short_status: "scheduled"`, `short2_id`, `localized: true` (if `localized`/`short_localized` are "ok"). Any sub-step that isn't "ok" (thumbnail/captions/localized) → fix and redo just that sub-step with yt_lib (don't re-upload).
  - ok:false → read the error. Never re-run the whole snippet if a video id was already created (check the channel's recent uploads first) — that would duplicate. Fix the cause and retry once; still failing → send the owner the files + title/description/tags for a manual upload and mark `status: "manual upload needed"`.

- Translations for older videos: any topic with a `video_id` and `localized: false` → run `localize_snippet.py` with DATE/MAIN_ID/SHORT_ID set. ok → `localized: true`.

- Channel SEO: run `channel_seo_snippet.py` unchanged (idempotent): channel keywords/translations, adds new long videos to their playlist (ids in playlists.json), posts one question comment under each public long video (scheduled ones get theirs on a later run).

## 3. Build tomorrow's video (date X+1) — ★★ illustrated POV format (RUNBOOK.md)
- Pick the next unused topic and turn it into a POV story. Write `days/<X+1>/pov/script.json` (main, with `thumbnail`),
  `days/<X+1>/pov_short/script.json` (teaser Short) and `days/<X+1>/pov_short2/script.json` (standalone Short, different topic).
  Commit + push them to main and note the commit SHA.
- Images: Cloudflare creds must exist in the workbench → run once:
  `import json,os; os.makedirs("/mnt/files/sml",exist_ok=True); json.dump({"account_id": <from task prompt>, "api_token": <from task prompt>}, open("/mnt/files/sml/cf_creds.json","w"))`
  then `SHA="<sha>"; JOBS=["days/<X+1>/pov","days/<X+1>/pov_short","days/<X+1>/pov_short2"]; exec(requests.get(f"https://raw.githubusercontent.com/ayyub1nnat/money-channel-videos/{SHA}/images_snippet.py").text)`
  and poll `print(IMG_STATUS)` every ~2 min until `running` is False (≈20 min). Flagged images: reword that scene's prompt, commit, re-run (existing images are skipped).
- `./fetch_imgs.sh days/<X+1>/pov days/<X+1>/pov_short days/<X+1>/pov_short2`, then for each dir `python3 build_pov.py <dir> --preview`, look at
  preview_grid.jpg (hero consistent? weird hands/faces? → reword + regenerate), then `python3 build_pov.py <dir>`.
- `cp days/<X+1>/pov/{video.mp4,thumbnail.jpg,subtitles.srt,chapters.txt} days/<X+1>/`, `cp days/<X+1>/pov_short/short.mp4 days/<X+1>/short.mp4`,
  `cp days/<X+1>/pov_short2/short.mp4 days/<X+1>/short2.mp4`, `mkdir -p days/<X+1>/short2 && cp days/<X+1>/pov_short2/subtitles.srt days/<X+1>/short2/`.
- Write `days/<X+1>/seo.json` (title = the POV title, description with chapters from chapters.txt, tags, `short` and `short2` title/description/tags)
  and `localizations.json` (es, pt, hi, de, fr incl. `_short` and `_short2`).
- If Cloudflare fails (quota/token), fall back to the whiteboard format (build_sketch.py) so a video still goes out, and tell the owner.

## 4. Save
- On `main`: commit `days/<X+1>/{script.json,seo.json,localizations.json,thumbnail.jpg,subtitles.srt,chapters.txt,timeline.json}` and `days/<X+1>/short_v/{script.json,timeline.json}` and `days/<X+1>/pov*/{script.json,timeline.json}` and `days/<X+1>/short2/subtitles.srt` and topics.json (topic → `used: true`, `date: X+1`, `status: "built, waiting for upload"`, `localized: false`), push.
- Media branch (holds ONLY the next video, force-pushed):
  ```bash
  rm -rf /home/claude/media && mkdir /home/claude/media && cd /home/claude/media && git init -q -b media
  cp ../money-channel-videos/days/<X+1>/{video.mp4,thumbnail.jpg,short.mp4,short2.mp4} .
  echo '{"date": "<X+1>", "title": "<title>"}' > meta.json
  git add . && git -c user.name=Claude -c user.email=noreply@anthropic.com commit -qm "media <X+1>"
  git remote add origin https://github.com/ayyub1nnat/money-channel-videos && git push -qf origin media
  ```
  Only do this after the previous media date was uploaded (step 2 catch-up) or handed to the owner — never overwrite a video that still needs uploading.
- Then go back to step 2 and upload X+1 (it will be scheduled for 08:00 / 19:00 on X+1).

## 5. Report to the owner (in Azerbaijani, short)
Send with SendUserMessage (and SendUserFile for files):
- Tomorrow's (X+1) uploads: main video + teaser Short (08:00 Baku) and standalone Short (19:00 Baku): titles + `https://studio.youtube.com/video/<id>/edit` links + thumbnail file.
- Any problem, plainly, with what they need to do (e.g. manual upload: attach video.mp4 + title + description).
