# Daily run — Simple Money Life  (rules rewritten by the owner on 2026-10-30; everything older is cancelled)

Runs every day at **04:31 Asia/Baku** (00:31 UTC, right after the Cloudflare image quota resets).
Let **X** = today's date in Asia/Baku (`TZ=Asia/Baku date +%F`). Each run BUILDS and UPLOADS the content for **X itself**:
- **1 Short** → public at **21:00 Baku** on X
- **1 main video** → public at **23:00 Baku** on X
That's all: no second Short anymore.

All YouTube API calls go through `yt_lib.py` (owner's own Google Cloud project; creds in the Composio workbench file
/mnt/files/sml/yt_creds.json). Never use Composio's YOUTUBE_* tools.

## The owner's content rules (2026-10-30) — apply to every script
1. **Sam is the main character** (brand/hero_ref.jpg, `{HERO}` in prompts). He must be in MOST scenes (≥ 75% of the
   image prompts contain `{HERO}`), main video and Short. Mia/Jake only as short contrast scenes. Never copy another channel's character.
2. **Topics = practical "save money" scripts that teach something**: concrete tips, real true numbers (cite the source in
   the description), what to do step by step. Tie to the date when there's an obvious event (holidays, Black Friday, tax season…).
3. **No text/title over the video.** No hook headline on Shorts (`hook` is not rendered). Only subtitles + small number tags.
4. **No background music, no transition sounds.** Voice only (build_pov.py default: `"music": false, "sfx": false`).
5. **Clear subtitles that don't hide the picture** (white text, black outline, no dark box — pov.py does this).
6. **Voice:** only `"voice": "am_michael"`. Emotional, warm, NOT rushed: `"speed": 0.95`, main `"lead": 0.2, "gap": 0.3, "scene_gap": 0.5`,
   Short `"lead": 0.1, "gap": 0.3, "scene_gap": 0.35, "tail": 0.8`. Short sentences, questions, pauses ("..."), contractions.
7. **Titles: more clickbait** (curiosity gap, shocking but TRUE number, "YOU"/"ONCE" in caps, "…"), every title starts with
   "POV:" (fr "POV : "). Short title ends with one emoji. Never promise something the video doesn't deliver.
8. **Thumbnails like big POV finance channels** (owner's screenshot 2026-10-30): bold, simple, two-panel comparison:
   left = the expensive/bad choice (gloomy), right = Sam's smart choice (bright), a white label box on top of each panel
   ("MIA: $410" red / "YOU: $42" green), yellow arrow between. Use `"thumbnail": {"layout": "split", "left": {"img", "label", "color"},
   "right": {"img", "label", "color"}}` — images_snippet.py makes thumb_l.jpg/thumb_r.jpg, thumb_pov.py renders it.
   Single-image layout (`"image": "thumb", "text": [...], "label"`) only when a comparison doesn't fit.
9. **Length:** main video 9-10 min (timeline.json duration 540-600 s; ≈ 42-50 scenes of 3-4 lines, ≈ 1,450-1,550 words at speed 0.95).
   Short: 8 scenes, one line each (~12-18 words), 40-55 s, ends pointing to the full video on the channel.
10. Image budget ≤ 70/day (Cloudflare free quota ≈ 85 images, resets 00:00 UTC). Main ≤ 50 + Short 8 + 2 thumb images.

## 1. Setup
- `add_repo` owner `ayyub1nnat`, repo `money-channel-videos`, access `push`; clone to `/home/claude/money-channel-videos`; `register_repo_root`.
- `bash setup.sh` (≈2–3 min, voice model).
- Composio: ToolSearch `select:mcp__Composio__COMPOSIO_REMOTE_WORKBENCH,mcp__Composio__COMPOSIO_SEARCH_TOOLS`, call COMPOSIO_SEARCH_TOOLS once
  for a session id, write the creds files (task prompt), check `yt('GET','channels',{'part':'id','mine':'true'})`.

## 2. Already done?
- topics.json: if the topic with `date == X` already has a `video_id` → nothing to build; only report. Never re-run an upload that created an id.
- If `days/X/pov/script.json` and `days/X/pov_short/script.json` already exist (prepared earlier), don't rewrite them — go to step 4.

## 3. Write the scripts for X
- Pick the topic (date event first, else the first `"used": false` topic in topics.json) as a save-money POV story with Sam.
- Check the channel's uploads (playlistItems of the uploads playlist) so the topic isn't a repeat.
- `days/X/pov/script.json` (main, with the split `thumbnail`), `days/X/pov_short/script.json` (`"vertical": true`, prompts end with "vertical composition").
- Commit + push to main; note the SHA.

## 4. Images
- In the workbench: `SHA="<sha>"; JOBS=["days/X/pov","days/X/pov_short"]; exec(requests.get(f"{RAW}/{SHA}/images_snippet.py").text)`.
- IMPORTANT (learned 2026-10-30): the background thread stalls between workbench calls. Keep a cell running while it works:
  call `time.sleep(170); print(IMG_STATUS)` repeatedly until `running` is False. If it stops progressing, generate the missing
  images synchronously inside cells (cf_image + gh_put from the snippet, ThreadPoolExecutor(4), one lock around gh_put to avoid 409s,
  ~140 s per cell). Flagged image → reword that prompt, commit, regenerate. 429 "daily free allocation" → quota is gone until 00:00 UTC:
  tell the owner and finish the rest when it resets (do not switch to paid services without asking).
- `./fetch_imgs.sh days/X/pov days/X/pov_short`

## 5. Build
- `python3 build_pov.py days/X/pov --preview` and the same for pov_short; look at preview_grid.jpg (Sam consistent? faces/hands ok? tags not covering faces?).
  Duration check: main 540-600 s (add/trim lines and re-run if outside).
- `python3 build_pov.py days/X/pov` and `.../pov_short` (≈ 25 min for the main video on 2 cores; run in background, poll).
- Look at thumbnail.jpg (labels readable at phone size, faces not covered).
- `cp days/X/pov/{video.mp4,thumbnail.jpg,subtitles.srt,chapters.txt} days/X/`; `cp days/X/pov_short/short.mp4 days/X/short.mp4`;
  `mkdir -p days/X/short && cp days/X/pov_short/subtitles.srt days/X/short/`.
- `days/X/seo.json`: title, description (hook sentence with keyword → summary with the numbers → ⏱️ CHAPTERS from chapters.txt →
  comment question → subscribe line → sources/"numbers are an example" → "⚠️ This video is for educational purposes only and is not
  financial advice." → hashtags; NO music credit), tags (12-18), `categoryId` "27", `playlist` key (playlists.json), and `short`: {title, description, tags}.
- `days/X/localizations.json`: es, pt, hi, de, fr {title, description (same chapters)} + `_short` {lang: {title ending " #shorts", description}}.

## 6. Save + upload
- Commit on main: `days/X/{seo.json,localizations.json,thumbnail.jpg,subtitles.srt,chapters.txt}`, `days/X/short/subtitles.srt`,
  `days/X/pov*/{script.json,timeline.json,subtitles.srt,chapters.txt}`, topics.json (`used: true, date: X, status: "built"`). Push.
- Media branch (force-push, holds only today's files):
  ```bash
  rm -rf /home/claude/media && mkdir /home/claude/media && cd /home/claude/media && git init -q -b media
  cp ../money-channel-videos/days/X/{video.mp4,thumbnail.jpg,short.mp4} .
  echo '{"date": "X", "title": "<title>"}' > meta.json
  git add . && git -c user.name=Claude -c user.email=noreply@anthropic.com commit -qm "media X"
  git remote add origin https://github.com/ayyub1nnat/money-channel-videos && git push -qf origin media
  ```
- Check `curl -s https://raw.githubusercontent.com/ayyub1nnat/money-channel-videos/media/meta.json` shows date X (raw cache ≈ 5 min).
- Run `upload_snippet.py` from the raw URL at the current main SHA in the workbench (Short → 21:00 Baku, video → 23:00 Baku).
  Long uploads: run it in a thread and keep a cell sleeping/polling (see step 4). Read the RESULT line.
  ok → topics.json: `video_id`, `short_id`, `status: "scheduled"`, `localized: true`, `publish: "X 21:00 Short / 23:00 video (Baku)"`; commit + push.
  Sub-step not ok (thumbnail/captions/localized) → redo only that sub-step with yt_lib. ok:false → check recent uploads before any retry.
- Run `channel_seo_snippet.py` unchanged (playlists, channel keywords, comments).

## 7. Report (Azerbaijani, short) with SendUserMessage + SendUserFile(thumbnail.jpg) + PushNotification
- Short (21:00) and video (23:00) titles with `https://studio.youtube.com/video/<id>/edit` links.
- Any problem and what the owner must do.
