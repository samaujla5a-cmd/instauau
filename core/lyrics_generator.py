import json, random, re, logging
from core.gemini_client import gemini
from config import MUSIC_STYLE
logger = logging.getLogger(__name__)
WORDBANKS = {"street":["gully","bhai","yaar","basti"],"hustle":["paisa","izzat","mehnat","grind"],"places":["Mumbai","Delhi","gully","chai tapri"]}

def _safe_parse(raw):
    raw = re.sub(r"```json|```","",raw).strip()
    try: return json.loads(raw)
    except: pass
    result = {"title":"Gully Ka Sach","hook":"Gully se aaya hoon main\nPaisa kama liya bhai","full_lyrics":"Gully se aaya hoon main...","suno_prompt":"desi trap hip hop, 85 bpm, hard 808s, dark atmospheric","youtube_title":"Gully Ka Sach - Desi Trap","instagram_caption":"Gully ka sach 🔥 #desitrap","mood_tags":["desi","trap"],"short_hook_moments":["Hook drop","Verse bars"]}
    return result

def generate_song_concept():
    theme = random.choice(MUSIC_STYLE["themes"]); s1 = random.choice(WORDBANKS["street"]); s2 = random.choice(WORDBANKS["hustle"]); place = random.choice(WORDBANKS["places"])
    prompt = f"""You are a desi street rap songwriter. THEME: {theme}. KEY WORDS: "{s1}", "{s2}", SETTING: {place}.
Return ONLY valid JSON: {{"title":"Hinglish song title 2-4 words","hook":"4-8 line hook","full_lyrics":"Complete song with [Hook] [Verse] labels","suno_prompt":"Indian hiphop: 90 BPM, boom-bap, sitar, dhol, dark, raw","youtube_title":"SEO YouTube title","instagram_caption":"Hinglish caption under 150 chars with emojis","mood_tags":["desi","hiphop"],"short_hook_moments":["4 best moments for reels"]}}"""
    for _ in range(3):
        try:
            raw = gemini(prompt, max_tokens=2000); c = _safe_parse(raw); c["theme"] = theme; return c
        except Exception as e: logger.warning(f"Attempt failed: {e}")
    c = _safe_parse(""); c["theme"] = theme; return c

def generate_suno_music_prompt(concept):
    return f"[indian hiphop] [boom-bap] [sitar sample] [dhol kick] [dark cinematic] {concept.get('suno_prompt','')}"
