# Daily YouTube Video — Runbook

> ## ★★★★ OWNER'S RULES OF 2026-10-30 — THEY OVERRIDE EVERYTHING BELOW
> See DAILY.md ("The owner's content rules"). In short: Sam in most scenes; informative save-money scripts; **1 Short (21:00 Baku) +
> 1 main video (23:00 Baku) per day, built and uploaded the same day**; no title/hook text over the video; **no music, no transition
> sounds**; clear outlined subtitles; am_michael at speed 0.95 (calm, emotional, not rushed); clickbait "POV:" titles; split
> comparison thumbnails (thumb_pov.py `"layout": "split"`). The retention section (hook headline, speed 1.15, SFX) and the
> 3-uploads/18:00 rules below are CANCELLED. Older sections are kept only as technical reference.

Channel niche: **personal finance & getting your life together** (budgeting, saving, debt, habits, side income, productivity), English, US audience.
Style: friendly, practical, emotional MALE narrator (Kokoro voice `am_michael`, owner's choice 2026-10-28; was af_heart), flat cartoon animation, burned-in subtitles, soft background music ducked under the voice.
Publish time: **18:00 Asia/Baku every day for the main video and both Shorts** (owner's choice 2026-10-28) (upload earlier as private with `publishAt`).

---

## 0. Setup (fresh machine)
```bash
git clone https://github.com/<owner>/money-channel-videos.git /home/claude/repo   # after add_repo
cd /home/claude/repo && bash setup.sh
```

## 1. Pick today's topic
Open `topics.json`, take the first topic with `"used": false`. If fewer than 10 remain, append ~15 new, non-overlapping topics in the same niche (mix formats: step-by-step plans, "N habits/mistakes", myths, challenges, explainers, "what I'd do if...").

## ★★★ RETENTION RULES SINCE 2026-10-29 (owner's decision after analytics: Shorts "stayed to watch" was only 26.9%)
Goal: stop the swipe in the first second and keep people focused. Applies to every new script.
- **Shorts** (`pov_short`, `pov_short2`): `"hook": ["LINE 1", "LINE 2"]` = big headline shown from frame 0 to the end (pov.py draws it,
  numbers turn yellow; ≤ 22 chars per line, no emoji). The hook states the shocking concrete number/situation ("$14 GONE" / "BEFORE 9 AM").
  `"speed": 1.15, "lead": 0.0, "gap": 0.15, "scene_gap": 0.15, "tail": 0.6`; 8 scenes, ONE short line per scene (≤ 12 words),
  total 22-30 s. Line 1 = the shock itself, no setup. Last line loops back into the first (e.g. "...because Jake's still spending
  fourteen dollars before nine A M." → hook), teaser still mentions "full routine/story on my channel".
  Reference: `days/2026-10-30/pov_short`, `pov_short2` (script_v1.json = the old, slower version).
- **Main video**: `"speed": 1.05, "lead": 0.1, "gap": 0.18, "scene_gap": 0.28`. Long scenes are automatically cut into ~4.6 s shots
  (odd shots = punch-in on part of the illustration) so the picture changes every few seconds — no extra images needed.
- **Sound design** (automatic in build_pov.py via sfx.py): whoosh on every scene change and in-scene cut, pop when a tag appears.
  Tune with `"sfx_volume"` (default 0.45 Shorts / 0.30 main).
- Voice energy: short punchy sentences, questions, "Wait.", "Here's the thing.", exclamation marks where a person would raise their voice.

## ★★ FORMAT SINCE 2026-10-26 (owner's decision): illustrated "POV" stories — this WINS over the whiteboard section below
Inspired by big finance channels that use AI-illustrated POV stories (we use OUR OWN hero, never copy another channel's character).
- Hero: **Sam** (owner confirmed 2026-10-28: Sam is the main character of EVERY video, also on the channel avatar/banner in brand/) — reference image `brand/hero_ref.jpg` (early 30s, dark brown wavy hair, round glasses, stubble, mustard-yellow
  sweater, white collar, dark jeans). Write `{HERO}` in an image prompt wherever Sam appears; images_snippet.py sends the reference.
  Recurring side characters: Jake (young man, blue shirt, impulsive spender), Mia (woman with a ponytail, credit-card spender).
- Narration in 2nd person ("You..."), Sam is "you" on screen. Contrast: calm, prepared you vs. stressed people around you. Emotional,
  concrete, true numbers (say "not guaranteed" for any investment growth).
- **EVERY title starts with "POV:"** (owner's rule 2026-10-26): main video, teaser Short AND standalone Short, in English and in every
  translation (fr: "POV : "). Clickbait in tone (curiosity gap, "…", a shocking but TRUE number, "YOU" in caps once, 1 emoji on Shorts),
  never in substance. Shorts: e.g. "POV: Your Friend Earns $2,000 More Than You… and Asks YOU for Money 😳",
  "POV: You Think You Pay $86 for Subscriptions… It's Really $219 😱". Before picking a Short topic, check the channel's existing
  uploads so it isn't a repeat (2026-10-27 short2 repeated the subscriptions topic of YAlE1_vk2NQ).
- Title patterns: "POV: You <did the smart thing> — <others> Still <are stuck>" / "POV: You Earn $X and Still Save $Y — ...". Thumbnail:
  `"thumbnail": {"img": "<prompt: {HERO} calm in front, stressed people behind>", "image": "thumb", "text": ["2-3 WORDS", "2-3 WORDS"], "color": "#5BE37D", "pos": "right"}`.
- **VOICE + LENGTH SINCE 2026-10-28 (owner's decision):** every script (main + both Shorts) uses `"voice": "am_michael"` (male).
  Write for a real, emotional human narrator: short sentences, questions, pauses with "...", exclamation marks where a person
  would raise their voice, contractions ("you're", "it's"), no robotic lists. The main video must be **9-10 minutes**
  (check `timeline.json` duration: 540-600 s; add or trim lines if outside). To stay within ≤ 70 images/day, the main video has
  **50-53 scenes with 2-4 lines each (≈ 10-11 s per image, ≈ 1,250-1,350 spoken words at am_michael speed 1.0 ≈ 2.5 words/s)**; Shorts stay at 8 scenes.
- Main video `days/<date>/pov/script.json`: `"style": "pov"`, speed 1.0, 50-53 scenes (9-10 min, see above), each scene 2-4 short sentences
  + one `"img"` prompt (concrete scene, setting, emotion; no text in images) + optional `"tag"` (big number/label, ≤ 22 chars,
  `"tag_color"` red #E23B3B loss / green #1B9E4B win / orange #E88A1A / blue #2C7BE5) + `"chapter"` at section starts.
- Shorts (vertical, 8 scenes, speed 1.08, voice am_michael, prompts end with "vertical composition"): `pov_short` = teaser of the main story ending
  "The full story is on my channel"; `pov_short2` = standalone money tip story ending "Follow for one simple money move every day!".
- Image budget: Cloudflare free tier ≈ 10,000 neurons/day (resets 00:00 UTC) ≈ 85 images at 1024x576 → keep total scenes
  (main + 2 Shorts + thumb) ≤ 70. If an image is "flagged" (false positive), reword the prompt and regenerate that one.
- Pipeline: commit scripts → in the workbench set `SHA`, `JOBS` and exec `images_snippet.py` (background; poll `IMG_STATUS`)
  → `./fetch_imgs.sh <dirs>` → `python3 build_pov.py <dir> --preview` (look at preview_grid.jpg) → `python3 build_pov.py <dir>`.
- Reference: `days/2026-10-26/pov`, `pov_short`, `pov_short2`.

## ★ (older) FORMAT SINCE 2026-10-25 (owner's decision, based on results): "fast whiteboard"
The emotional, fast Short ("This $5 Habit Is Stealing $1,825...") got 43 views vs 11 for the calmer video. EVERY main video and EVERY Short now uses this format:
- `"style": "sketch"`, `"speed": 1.08` (main) / `1.1` (Short), `"lead": 0.3`, `"scene_gap": 0.35` (Short 0.3), `"tail": 1.5`, main also `"big_headings": true`; Short `"vertical": true`.
- **One line per scene, one drawing per scene** → a new page with a new doodle every ~4 s. Each scene: `{"heading": "2-4 punchy words", "lines": ["one spoken sentence or two short ones"], "draws": [{...}]}`.
- Main video: 40-60 scenes (≈3-4.5 min). Mark section starts with `"chapter": "Step 1: ..."` (≥ 10 s apart) → YouTube chapters.
- Voice: emotional, direct, second person. Short sentences. Questions ("Be honest."), surprise ("Wait."), stakes ("And that's how the debt trap starts."), relief ("No panic. Just paid."). Exclamation marks where a real person would raise their voice.
- Hook (first 2-3 scenes): a shocking but TRUE number or scenario + "you" + what they'll get. Titles/thumbnails may be clickbait in tone, never in substance: everything promised must be in the video, every number correct.
- Numbers on screen as `big` draws, colored (red = loss/danger, green = savings/win, yellow = math).
- Short (separate script in `days/<date>/short_v/script.json`, NOT cut from the main video): 8-10 scenes, 35-45 s, same topic, self-contained value, ends with "the full step-by-step plan is in the full video on my channel" (`play` icon). Build it with `python3 build_sketch.py days/<date>/short_v` → `short_v/short.mp4`; copy it to `days/<date>/short.mp4`.
- Reference scripts: `days/2026-10-25/fast/script.json` (main) and `shorts/2026-10-25-five-dollars/script.json` (Short).

## 2. Write `days/YYYY-MM-DD/script.json` (older notes; the ★ format above wins where they differ)
Target **4–6 minutes**: 9–12 scenes, 3–6 lines per scene, each line one or two short spoken sentences (~8–22 words).
Writing rules:
- Hook in the first 2 lines (a relatable pain + the promise of the video). No "Hey guys, welcome back".
- Concrete and useful: real numbers, examples, steps. Plain words, short sentences, written for the ear. Numbers as words when spoken naturally ("forty eight hours", "fifty, thirty, twenty").
- Facts must be correct and general; no specific stock/crypto picks, no guaranteed returns, no tax/legal claims that vary by state.
- Use **at least 6 different templates** per video, and don't open with the same template as yesterday's video.
- Last scene: `person` with `{"mood":"happy","props":["confetti"],"subscribe":true}` + ask a comment question.
- **Pace (data, 2026-10-25: first video kept viewers ~0:57 of 3:01 ≈ 31%):** set `"speed": 1.06` in script.json; first scene ≤ 12 s (2–3 lines max), get to the first useful point by 0:20; every scene ≤ 25 s — split longer ones; no scene where the picture stays the same for more than ~6 s (use list/timeline/checklist templates whose items appear line by line).
- **Retention (what makes YouTube push a video):** the first 15 seconds decide most of it. Line 1 = the viewer's pain or a surprising fact/number; line 2 = the concrete payoff ("by the end you'll have a 4-step plan"). No intro, no channel name, no "in this video I will". Every 30–45 s give a small new payoff (a number, a mini-example, "here's the trick"). Use open loops ("the third one surprised me", "stay for step 5, it's the one most people skip"). Never pad: if a line doesn't teach or move the story, cut it.
- **Topic choice:** prefer topics people actually search (how to…, best way to…, N mistakes/habits, X vs Y, "on a low income", "for beginners") and topics that fit the next video in the same series (playlist), so viewers binge.
- **Mention the series:** in the outro, one line pointing to a related earlier video ("if you haven't built your emergency fund yet, watch that one next").
- `heading` ≤ 40 chars.
- **Thumbnail (biggest lever for clicks):** max 3–5 big words that ADD to the title (don't repeat it), one emotion (character mood matches it), high contrast background different from the last 3 videos, a number or money symbol when possible. It must read clearly at phone size (~160 px wide): check `thumbnail.png` scaled down.

```json
{
  "title": "…YouTube title, ≤ 70 chars…",
  "voice": "am_michael",
  "thumbnail": {"line1": "Stop Living", "line2": "Paycheck to", "badge": "Paycheck", "sub": "Simple 5-step plan",
                "mood": "happy|sad|surprised|neutral", "props": ["coins"|"question"], "bg": ["#FFD23F", "#FF9F1C"]},
  "scenes": [ {"visual": "<template>", "heading": "…", "params": {…}, "lines": ["…", "…"]} ]
}
```
Items in list-like templates appear in sync with the narration: item *i* appears when line *i+1* starts (line 0 is the intro line). Override with `"at": [lineIndex, …]`.

### Default style: whiteboard / hand-drawn (`"style": "sketch"`) — USE THIS FOR EVERY NEW VIDEO
Owner's request (2026-10-25): animations must change with every sentence, look hand-drawn by a person, with a pencil sound.
Set `"style": "sketch"` at the top of script.json and give every scene a `"draws"` list with **exactly one item per line**:
- `{"icon": "<name>", "label": "2-4 words"}` → a doodle traced by the drawing hand + a handwritten label
- `{"big": "$500", "label": "Starter goal"}` → a big handwritten number/word circled in color (use for every number the narrator says)
- `null` → nothing new on that line (use rarely; the picture must keep changing)
- optional `"color": "#hex"`; scene-level `"flow": true` draws arrows between the doodles (processes, steps, money flows)
Icons (sketch_icons.py; add new ones there as SVG paths in a 100×100 box if a topic needs them): coin, coins, bill, piggy, wallet, card, bank, house, car,
phone, calendar, clock, chart_up, chart_down, bars, arrow, check, cross, bulb, target, shield, moneybag, cart, gift, person, person_sad, people, family,
heart, star, lock, scale, hourglass, rocket, trophy, seedling, umbrella, magnifier, receipt, warning, question, gears, snowball, mail, fire, bell, play,
thumbsup, scissors, list, battery, globe, handshake, plane, pizza, coffee, brain, book, key, percent, dollar, pencil.
Rules: max 6 lines per scene (layout: 1-3 in a row, 4 in a 2×2, 5-6 in two rows); labels ≤ 22 characters; vary icons — don't repeat the same icon
within a scene; the first scene's first draw should be the most visual one (it's the hook). `visual`/`params` are ignored in sketch style.
Build with `python3 build_sketch.py days/<date> --preview` (look at preview_grid.jpg), then `python3 build_sketch.py days/<date>`
(≈20 min), then `python3 short.py days/<date>` as usual. Thumbnails still use thumb.py.

### Templates (`visual` → `params`) — classic style only
| visual | params | good for |
|---|---|---|
| `person` | `mood` happy/sad/neutral/surprised, `arms` up/head/point/think/down, `props` [wallet, bills, coins, question, sweat, confetti], `sign` speech-bubble text, `sign_at` sec, `subscribe` bool, `shirt` color, `long_hair` bool, `side` left/right | hook, emotion, outro |
| `list` | `items` [≤5 short strings], `mood`, `shirt` | numbered key points |
| `checklist` | `items` [[tag, text], …≤5] | recap, steps |
| `stat` | `value`, `prefix`, `suffix`, `decimals`, `caption`, `color` | one striking number |
| `compare` | `left_title`, `right_title`, `left` [≤4], `right` [≤4] | bad vs good habit, myth vs fact |
| `quote` | `text`, `author` | rule of thumb, famous quote (only real, correctly attributed quotes) |
| `timeline` | `steps` [[label, desc], …≤5] | step-by-step process, weeks/months |
| `calendar` | `title`, `days` (≤35), `badge`, `shirt` | challenges, streaks, habits |
| `balance` | `left`, `right`, `heavy` left/right, `caption` | income vs spending, trade-offs |
| `clock` | `items` [[time, text], …≤4] | routines, schedules, "today/this week" |
| `pie` | `parts` [[number, name], …≤4], `center`, `unit` | budgets, splits |
| `phone` | `title`, `items` [[name, value], …≤6], `tags` [≤4] | tracking, apps, shopping carts |
| `cards` | `items` [[name, keep_bool], …≤6], `price`, `result` | subscriptions/expenses to cut |
| `leak` | `labels` [3], `center`, `counter` | hidden costs, money leaks |
| `jar` | `label`, `goal`, `prefix`, `suffix` | savings goal, emergency fund |
| `snowball` | `items` [[name, value], 3] | debt payoff, momentum |
| `flow` | `source`, `targets` [3] | automation, where money goes |
| `growth` | `bars` [numbers], `bar_labels`, `items` [≤3] | income growth, compound interest |
Colors: teal, orange, coral, purple, green, yellow, sky, pink or `#hex`. Keep text short — long text auto-shrinks.

## 3. Build
```bash
cd /home/claude/repo
python3 build.py days/YYYY-MM-DD --preview     # ~2 min: voice + stills → preview_grid.jpg
```
**Look at `preview_grid.jpg`** (Read tool). Fix overlaps/overflow/odd wording in script.json, re-run preview if changed. Then:
```bash
python3 build.py days/YYYY-MM-DD               # ~15–20 min (run in background, wait for it)
```
Outputs: `video.mp4`, `thumbnail.png/.jpg`, `subtitles.srt`, `chapters.txt`. Check: duration 3.5–7 min, sample 3 frames with ffmpeg and look at them.

### Teaser Short
`python3 short.py days/YYYY-MM-DD` (after the full build) → `short.mp4`: 1080x1920, 35–50 s, the clips listed in script.json `short.clips` (hook text on top, video strip with the burned-in subtitle strip cropped off, big captions, "FULL VIDEO ON THE CHANNEL" call, end card with the thumbnail), clean voice + an energetic original track (`music.py … energetic`). Uploaded together with the main video, same publish time, description links to it.

## 4. SEO → `days/YYYY-MM-DD/seo.json`
`{"title": "...", "description": "...", "tags": [...]}`
- Title ≤ 100 chars (aim 45–65), the exact phrase people search near the start, plus a benefit or curiosity hook ("…(Step by Step)", "…That Keep You Broke", "…Nobody Tells You"). No clickbait that the video doesn't deliver. Write 3 options, pick the best.
- First 150 characters of the description = what shows in search: main keyword + promise, no links or emojis there.
- Description: 2-sentence hook with keyword → 2–4 sentence summary → `⏱️ CHAPTERS` from `chapters.txt` (first must be 0:00) → comment question → like/subscribe line → disclaimer "This video is for educational purposes only and is not financial advice." → music credit (see below) → 3 hashtags. Keep under 4,500 bytes.
- Tags: 12–20 search phrases, total < 450 chars.
- Music credit: default track is original/royalty-free → "Music: original background track". If `script.json` has `music_file` (an NCS track), use the exact NCS credit text.

- Pick the playlist key (budgeting / saving / debt / habits / income, see playlists.json) and add `"playlist": "<key>"` to seo.json.

## 4b. Translations → `days/YYYY-MM-DD/localizations.json`
Translate the final title and full description (chapters included, same timestamps) into **es, pt, hi, de, fr**: natural, native-sounding, not word-for-word; titles ≤ 100 chars (keep them catchy and searchable in that language); descriptions < 4,900 bytes; keep emojis, the disclaimer, and the channel name "Simple Money Life" untranslated; hashtags can be localized. Also `"_short"`: {lang: {title (end with " #shorts"), description}} for the Short. Format: see days/2026-10-25/localizations.json. Applied after upload by `localize_snippet.py`.

## 5. Publish
See DAILY.md: videos are built one day ahead, kept on the `media` branch, and uploaded by `upload_snippet.py` (Composio workbench) right after the YouTube quota resets at midnight Pacific, scheduled to go public at 12:00 America/Los_Angeles (Short 16:00).

## 6. Report
Send the owner a short message **in Azerbaijani**: today's title, the YouTube Studio link `https://studio.youtube.com/video/<id>/edit`, publish time (12:00 Los Angeles; Short 16:00), and the thumbnail. If anything failed, say exactly what, and leave the video private.
