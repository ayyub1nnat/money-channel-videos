# Paste into COMPOSIO_REMOTE_WORKBENCH (after the daily upload). Idempotent channel-SEO pass:
#  1. channel keywords, country (US) and default language (en) + translated channel description (es, pt, hi, de, fr)
#  2. creates the playlists from playlists.json that have no id yet (prints their ids → record them in playlists.json)
#  3. puts every uploaded video that isn't in a playlist yet into its best-matching playlist
#  4. posts a friendly top-level question comment on videos that have no comment from the channel yet
# Uses API units only (no upload quota). Prints SEO {...}.
import requests, json
REPO = "ayyub1nnat/money-channel-videos"
RAW = f"https://raw.githubusercontent.com/{REPO}"
API = "https://www.googleapis.com/youtube/v3"
PL = requests.get(f"{RAW}/main/playlists.json", timeout=60).json()
out = {"errors": []}

exec(requests.get(f"{RAW}/main/yt_lib.py", timeout=60).text)   # own Google project credentials
def call(method, path, q=None, body=None):
    return yt(method, path, q or {}, body)

KEYWORDS = ('"personal finance" budgeting "how to save money" "money tips" "debt free" "emergency fund" "money habits" '
            '"financial freedom" "budget for beginners" "paycheck to paycheck" "side hustle" "self improvement" "simple living"')
CH_LOC = {
 "es": "Simple Money Life te ayuda a tomar el control de tu dinero y de tu vida, paso a paso. Cada día, un nuevo video animado y breve sobre presupuestos, ahorro, fondo de emergencia, salir de deudas, mejores hábitos y cómo ganar más. Sin jerga complicada ni promesas de hacerte rico rápido. Contenido solo educativo, no es asesoramiento financiero.",
 "pt": "O Simple Money Life ajuda você a assumir o controle do seu dinheiro e da sua vida, um passo de cada vez. Todo dia, um novo vídeo animado e curto sobre orçamento, como economizar, reserva de emergência, sair das dívidas, hábitos melhores e como ganhar mais. Sem jargão complicado nem promessas de enriquecer rápido. Conteúdo apenas educativo, não é aconselhamento financeiro.",
 "hi": "Simple Money Life आपको कदम-दर-कदम अपने पैसे और अपनी ज़िंदगी पर काबू पाने में मदद करता है। हर दिन बजट, बचत, इमरजेंसी फंड, कर्ज़ से छुटकारा, अच्छी आदतों और ज़्यादा कमाई पर एक नया छोटा एनिमेटेड वीडियो। न मुश्किल शब्द, न जल्दी अमीर बनने के वादे। केवल शिक्षा के लिए, वित्तीय सलाह नहीं।",
 "de": "Simple Money Life hilft dir, Schritt für Schritt die Kontrolle über dein Geld und dein Leben zu übernehmen. Jeden Tag ein neues kurzes Animationsvideo über Budgetplanung, Sparen, Notgroschen, Schuldenabbau, bessere Gewohnheiten und mehr Einkommen. Kein Fachchinesisch, keine Schnell-reich-Versprechen. Nur zu Bildungszwecken, keine Finanzberatung.",
 "fr": "Simple Money Life vous aide à reprendre le contrôle de votre argent et de votre vie, une étape à la fois. Chaque jour, une nouvelle courte vidéo animée sur le budget, l'épargne, l'épargne de secours, la sortie des dettes, les bonnes habitudes et comment gagner plus. Pas de jargon compliqué, pas de promesses d'enrichissement rapide. Contenu uniquement éducatif, ce n'est pas un conseil financier."}

# 1. channel branding
try:
    ch = call("GET", "channels", {"part": "brandingSettings,localizations,contentDetails,snippet", "mine": "true"})["items"][0]
    cid = ch["id"]; uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    bs = ch.get("brandingSettings", {}); c = bs.get("channel", {})
    c.update({"keywords": KEYWORDS, "country": "US", "defaultLanguage": "en"})
    c.setdefault("description", ch["snippet"].get("description", ""))
    bs["channel"] = c
    locs = ch.get("localizations", {})
    for k, d in CH_LOC.items(): locs[k] = {"title": "Simple Money Life", "description": d}
    call("PUT", "channels", {"part": "brandingSettings"}, {"id": cid, "brandingSettings": bs})
    call("PUT", "channels", {"part": "localizations"}, {"id": cid, "localizations": locs})
    out["channel"] = "ok"
except Exception as ex:
    out["errors"].append(str(ex)); uploads = None; cid = None

# 2. playlists
existing = {}
try:
    for p in call("GET", "playlists", {"part": "snippet", "mine": "true", "maxResults": "50"}).get("items", []):
        existing[p["snippet"]["title"]] = p["id"]
except Exception as ex:
    out["errors"].append(str(ex))
ids = {}
for p in PL["playlists"]:
    pid = p.get("id") or existing.get(p["title"])
    if not pid:
        try:
            pid = call("POST", "playlists", {"part": "snippet,status"}, {"snippet": {"title": p["title"], "description": p["description"],
                       "defaultLanguage": "en"}, "status": {"privacyStatus": "public"}})["id"]
        except Exception as ex:
            out["errors"].append(str(ex))
    ids[p["key"]] = pid
out["playlist_ids"] = ids

# 3. add videos to playlists
def best(title):
    t = title.lower(); score = {p["key"]: sum(m in t for m in p["match"]) for p in PL["playlists"]}
    k = max(score, key=score.get); return k if score[k] > 0 else "habits"
added = []
try:
    vids = call("GET", "playlistItems", {"part": "snippet", "playlistId": uploads, "maxResults": "50"})["items"] if uploads else []
    inpl = set()
    for k, pid in ids.items():
        if pid:
            try: items = call("GET", "playlistItems", {"part": "snippet", "playlistId": pid, "maxResults": "50"}).get("items", [])
            except Exception: items = []   # brand-new playlists can 404 for a few minutes
            for it in items: inpl.add(it["snippet"]["resourceId"]["videoId"])
    for it in vids:
        vid = it["snippet"]["resourceId"]["videoId"]; title = it["snippet"]["title"]
        if vid in inpl or "#shorts" in title.lower(): continue
        pid = ids.get(best(title))
        if pid:
            call("POST", "playlistItems", {"part": "snippet"}, {"snippet": {"playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": vid}}})
            added.append([vid, best(title)])
except Exception as ex:
    out["errors"].append(str(ex))
out["added_to_playlists"] = added

# 4. one question comment per long video from the channel (can't be pinned via API; owner may pin it in Studio)
commented = []
try:
    for it in vids:
        vid = it["snippet"]["resourceId"]["videoId"]; title = it["snippet"]["title"]
        if "#shorts" in title.lower(): continue
        th = call("GET", "commentThreads", {"part": "snippet", "videoId": vid, "maxResults": "50"}).get("items", [])
        if any(x["snippet"]["topLevelComment"]["snippet"].get("authorChannelId", {}).get("value") == cid for x in th): continue
        q = ("Quick question 👇 What's the ONE money change you're going to make this week? "
             "Reply below, I read every comment. And if you want a new simple money tip every day, subscribe. 💚")
        call("POST", "commentThreads", {"part": "snippet"}, {"snippet": {"videoId": vid, "topLevelComment": {"snippet": {"textOriginal": q}}}})
        commented.append(vid)
except Exception as ex:
    out["errors"].append(str(ex))
out["commented"] = commented
print("SEO", json.dumps(out, ensure_ascii=False))
