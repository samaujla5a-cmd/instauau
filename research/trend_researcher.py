"""
TREND RESEARCHER — Instagram Only
Generates trending hashtags and captions using Claude AI
No YouTube API needed
"""
import os, random, logging, anthropic, json, re
logger = logging.getLogger("RESEARCH")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY","")

BASE_HASHTAGS = [
    "#rap","#hiphop","#trap","#trippyvibes","#lofi",
    "#chillvibes","#undergroundhiphop","#rapmusic","#newmusic",
    "#reels","#viral","#fyp","#explore","#trending",
    "#hiphophead","#bars","#freestyle","#rapgod","#newartist",
]

def get_trending_tags(genre="rap"):
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role":"user","content":
                f'Give me 20 trending Instagram hashtags for {genre} music in 2025. '
                f'Return ONLY a JSON array of strings like ["#tag1","#tag2"]. No other text.'}]
        )
        text = resp.content[0].text.strip()
        text = re.sub(r"```json|```","",text).strip()
        tags = json.loads(text)
        return {"instagram_tags": tags}
    except Exception as e:
        logger.warning(f"Trend research failed: {e} — using defaults")
        return {"instagram_tags": BASE_HASHTAGS}

def build_instagram_metadata(concept, clip=None, trend_data=None):
    tags = trend_data.get("instagram_tags", BASE_HASHTAGS) if trend_data else BASE_HASHTAGS
    title = concept.get("title","")
    mood  = concept.get("mood_tags",["chill"])[0] if concept.get("mood_tags") else "chill"
    caption = f"🎵 {title}\n\n{mood} vibes only 🔥\n\n"
    caption += " ".join(tags[:25])
    return {"caption": caption, "hashtags": tags}

def get_optimal_post_times():
    return ["08:00","14:00","20:00"]
