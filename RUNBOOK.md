# Daily YouTube Video — Runbook

Channel niche: **personal finance & getting your life together** (budgeting, saving, debt, habits, side income, productivity), English, US audience.
Style: friendly, practical, calm female narrator (Kokoro voice `af_heart`), flat cartoon animation, burned-in subtitles, soft background music ducked under the voice.
Publish time: **19:00 America/Los_Angeles every day** (upload earlier as private with `publishAt`).

---

## 0. Setup (fresh machine)
```bash
git clone https://github.com/<owner>/money-channel-videos.git /home/claude/repo   # after add_repo
cd /home/claude/repo && bash setup.sh
```

## 1. Pick today's topic
Open `topics.json`, take the first topic with `"used": false`. If fewer than 10 remain, append ~15 new, non-overlapping topics in the same niche (mix formats: step-by-step plans, "N habits/mistakes", myths, challenges, explainers, "what I'd do if...").

## 2. Write `days/YYYY-MM-DD/script.json`
Target **4–6 minutes**: 9–12 scenes, 3–6 lines per scene, each line one or two short spoken sentences (~8–22 words).
Writing rules:
- Hook in the first 2 lines (a relatable pain + the promise of the video). No "Hey guys, welcome back".
- Concrete and useful: real numbers, examples, steps. Plain words, short sentences, written for the ear. Numbers as words when spoken naturally ("forty eight hours", "fifty, thirty, twenty").
- Facts must be correct and general; no specific stock/crypto picks, no guaranteed returns, no tax/legal claims that vary by state.
- Use **at least 6 different templates** per video, and don't open with the same template as yesterday's video.
- Last scene: `person` with `{"mood":"happy","props":["confetti"],"subscribe":true}` + ask a comment question.
- `heading` ≤ 40 chars. Thumbnail text: line1 + line2 + badge, 2–5 words total feel, big & emotional.

```json
{
  "title": "…YouTube title, ≤ 70 chars…",
  "voice": "af_heart",
  "thumbnail": {"line1": "Stop Living", "line2": "Paycheck to", "badge": "Paycheck", "sub": "Simple 5-step plan",
                "mood": "happy|sad|surprised|neutral", "props": ["coins"|"question"], "bg": ["#FFD23F", "#FF9F1C"]},
  "scenes": [ {"visual": "<template>", "heading": "…", "params": {…}, "lines": ["…", "…"]} ]
}
```
Items in list-like templates appear in sync with the narration: item *i* appears when line *i+1* starts (line 0 is the intro line). Override with `"at": [lineIndex, …]`.

### Templates (`visual` → `params`)
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
- Title ≤ 100 chars (aim 50–70), main keyword first, curiosity + clarity.
- Description: 2-sentence hook with keyword → 2–4 sentence summary → `⏱️ CHAPTERS` from `chapters.txt` (first must be 0:00) → comment question → like/subscribe line → disclaimer "This video is for educational purposes only and is not financial advice." → music credit (see below) → 3 hashtags. Keep under 4,500 bytes.
- Tags: 12–20 search phrases, total < 450 chars.
- Music credit: default track is original/royalty-free → "Music: original background track". If `script.json` has `music_file` (an NCS track), use the exact NCS credit text.

## 5. Publish
See DAILY.md: videos are built one day ahead, kept on the `media` branch, and uploaded by `upload_snippet.py` (Composio workbench) right after the YouTube quota resets at midnight Pacific, scheduled to go public at 19:00 America/Los_Angeles.

## 6. Report
Send the owner a short message **in Azerbaijani**: today's title, the YouTube Studio link `https://studio.youtube.com/video/<id>/edit`, publish time (19:00 Los Angeles), and the thumbnail. If anything failed, say exactly what, and leave the video private.
