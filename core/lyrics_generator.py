"""
LYRICS GENERATOR — Desi Trap / Hinglish Rap
============================================
Style: Divine, Seedhe Maut, Emiway Bantai, Kr$na, Prabh Deep vibes
Language: Hinglish (Hindi + English mixed naturally)
Beat: Hard desi trap, 808s, dhol samples, dark atmospheric
"""
import json
import random
import re
import logging
import requests
from core.gemini_client import gemini as _gemini
from config import MUSIC_STYLE

logger = logging.getLogger(__name__)

# Hinglish wordbanks for variety
HINGLISH_WORDBANKS = {
    "street": ["gully", "bhai", "yaar", "chacha", "dada", "basti", "mohalla", "chawl"],
    "hustle": ["paisa", "izzat", "mehnat", "struggle", "grind", "sach", "real talk", "no cap"],
    "emotion": ["dard", "khushi", "akela", "yaadein", "teri maa", "dil", "junoon", "aag"],
    "slang": ["ek dum", "arey bhai", "sahi bola", "kya scene hai", "chill maar", "bindaas", "jhakaas"],
    "places": ["Mumbai", "Delhi", "Bombay", "gully", "station", "local train", "tea stall", "chai tapri"],
}


def _safe_json_parse(raw: str) -> dict:
    """Parse JSON with auto-repair for truncated responses."""
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strip trailing commas before closing brackets/braces (common truncation artifact)
    repaired = re.sub(r",\s*([\]\}])", r"\1", raw)

    open_braces   = repaired.count("{") - repaired.count("}")
    open_brackets = repaired.count("[") - repaired.count("]")

    if repaired.count('"') % 2 != 0:
        repaired += '"'

    repaired += "]" * max(0, open_brackets)
    repaired += "}" * max(0, open_braces)

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    logger.warning("JSON fully broken — extracting fields via regex")
    result = {}
    for field in ["title", "hook", "verse1", "verse2", "bridge",
                  "full_lyrics", "suno_prompt", "youtube_title",
                  "instagram_caption", "tagline"]:
        match = re.search(rf'"{field}"\s*:\s*"(.*?)(?<!\\)"', raw, re.DOTALL)
        if match:
            result[field] = match.group(1).replace('\\"', '"')

    # Fallback defaults
    result.setdefault("title", "Gully Ka Sach")
    result.setdefault("hook", "Gully se aaya hoon main, koi nahi roka mujhe\nPaisa kama liya bhai, khud hi toh joda mujhe")
    result.setdefault("verse1", "Arey bhai sun le meri baat, no fake no cap\nMehnat ki hai maine, ab dekh mera map")
    result.setdefault("verse2", "Dil mein aag hai yaar, aankh mein sapna\nKoi rok nahi sakta, yeh mera apna")
    result.setdefault("bridge", "Ek dum sahi bola, real talk bhai\nGully ka yeh beta, udd gaya aasman mein")
    result.setdefault("full_lyrics", result["hook"])
    result.setdefault("suno_prompt", "desi trap hip hop, 85 bpm, hard 808s, dark atmospheric, hindi rap, street vibe")
    result.setdefault("youtube_title", f"{result['title']} - Desi Trap Rap")
    result.setdefault("instagram_caption", "Gully ka sach 🔥 #desitrap #hindi #rap")
    result.setdefault("mood_tags", ["desi", "trap", "hinglish", "street", "real"])
    result.setdefault("short_hook_moments", ["Hook drop", "Verse 1 bars", "Bridge moment", "Final hook"])
    return result


def generate_song_concept() -> dict:
    """Generate Hinglish desi trap song concept."""
    theme = random.choice(MUSIC_STYLE["themes"])
    slang1 = random.choice(HINGLISH_WORDBANKS["street"])
    slang2 = random.choice(HINGLISH_WORDBANKS["hustle"])
    place  = random.choice(HINGLISH_WORDBANKS["places"])

    prompt = f"""You are a desi trap rap songwriter in the style of Divine, Seedhe Maut, Emiway Bantai, and Kr$na.
Generate a complete original HINGLISH rap song — mix of Hindi and English naturally, like real Indian street rap.

THEME: {theme}
VIBE: Desi trap, hard 808s, dark and real
SETTING: {place}, street life, real talk
KEY WORDS TO USE: "{slang1}", "{slang2}"

LANGUAGE RULES:
- Mix Hindi and English in same line, very naturally (Hinglish)
- Use Hindi slang: "bhai", "yaar", "arey", "sahi", "ek dum", "teri", "meri", "kya", "nahi", "hoon"
- English bars mixed in: "no cap", "real talk", "grind", "hustle", "on my grind", "level up"
- Lines should RHYME and have FLOW — think actual rap cadence
- Ad-libs in parentheses: (arey), (bhai), (sahi bola), (haan), (ek dum)
- NOT robotic — sound human, authentic Indian rap

Return ONLY a valid JSON object, no markdown, no extra text:
{{
  "title": "Song title in Hinglish (2-4 words, catchy)",
  "tagline": "One catchy Hinglish line describing the vibe",
  "hook": "Full hook lyrics 4-8 lines, Hinglish rhyming flow",
  "verse1": "16-20 lines verse 1, Hinglish, hard bars",
  "verse2": "16-20 lines verse 2, Hinglish, storytelling",
  "bridge": "4-8 lines bridge, more introspective",
  "full_lyrics": "Complete assembled song with section labels [Hook] [Verse 1] etc",
  "suno_prompt": "120-word music prompt: desi trap beat, 85 BPM, hard 808 bass, dhol samples, dark atmospheric pads, Hindi rap style, voice like Divine or Kr$na, dark moody",
  "youtube_title": "SEO YouTube title with desi trap keywords",
  "youtube_description": "300 word description with story and hashtags",
  "short_hook_moments": ["4 best 30-60 second moment descriptions"],
  "instagram_caption": "Hinglish Instagram caption under 150 chars with fire emojis",
  "mood_tags": ["desi", "trap", "hinglish", "street", "real"]
}}"""

    last_err = None
    for attempt in range(3):
        try:
            raw = _gemini(prompt, max_tokens=2000)
            concept = _safe_json_parse(raw)
            concept["theme"] = theme
            logger.info(f"Generated song concept: '{concept['title']}'")
            return concept
        except Exception as e:
            last_err = e
            logger.warning(f"Attempt {attempt+1} failed: {e} — retrying...")

    logger.error(f"All 3 attempts failed: {last_err} — using fallback")
    return {
        "title": "Gully Ka Sach",
        "theme": theme,
        "tagline": "Bhai, yeh life real hai",
        "hook": (
            "Gully se aaya hoon main, no cap no lie (arey)\n"
            "Mehnat ki apni, kisi ne nahi dekhi (bhai)\n"
            "Paisa aayega, izzat bhi milegi\n"
            "Seedha raasta, bas yehi meri niti (haan)"
        ),
        "verse1": (
            "Subah uthke chai piya, tapri pe khada tha\n"
            "Dreams bade the yaar, account mein zero pada tha (sahi bola)\n"
            "Local train mein tha, rush hour ki bheed mein\n"
            "Sochta tha bhai, kab niklunga is grind se\n"
            "But teri maa kasam, tune nahi roka mujhe\n"
            "Hustle karta raha, koi rok nahi saka mujhe (ek dum)\n"
            "Mumbai ki gully ne sikha diya real talk\n"
            "Fake log aaye gaye, main karta raha my walk\n"
        ),
        "verse2": (
            "Dil mein tha sapna, aankh mein tha determination\n"
            "Gully boy se uthke, kar diya transformation (haan bhai)\n"
            "Log haste the yaar, ab dekhte hain mujhe\n"
            "Real grind dikhai, ab samjhe hain mujhe\n"
            "Teri yaadein bhai, rakhti hain motivated\n"
            "Ek dum sahi tha, kabhi nahi deflated\n"
        ),
        "bridge": (
            "Yeh jo dard hai, yeh jo struggle hai bhai\n"
            "Teri maa ki kasam, yeh sabse bada sahi\n"
            "Real talk karta hoon, no filter no cap\n"
            "Gully ka yeh beta, never looking back\n"
        ),
        "full_lyrics": "Gully Ka Sach\n\n[Hook]\nGully se aaya hoon main...\n",
        "suno_prompt": (
            "desi trap hip hop beat, 85 BPM, hard 808 bass lines, "
            "dark atmospheric synth pads, dhol tabla samples, minor key, "
            "deep reverb on vocals, rap style like Divine or Kr$na, "
            "Mumbai street vibe, dark moody production, "
            "occasional Hindi vocal chops, bass-heavy mix"
        ),
        "youtube_title": "Gully Ka Sach — Desi Trap Rap 🔥 Hindi Rap 2025",
        "youtube_description": "Real desi trap from the gully. No cap, pure real talk.",
        "short_hook_moments": ["Hook drop bhai", "Verse 1 bars", "Bridge real talk", "Final hook"],
        "instagram_caption": "Gully ka sach 🔥 Real talk bhai #desitrap #hindirap #rap",
        "mood_tags": ["desi", "trap", "hinglish", "street", "real"],
    }


def generate_suno_music_prompt(concept: dict) -> str:
    base = concept.get("suno_prompt", "")
    # Always add desi trap tags to ensure correct style
    style_tags = "[desi trap] [hindi rap] [808 bass] [dark atmospheric]"
    return f"{style_tags} {base}"


def get_best_short_clips(concept: dict) -> list:
    moments = concept.get("short_hook_moments", [])
    clips = []
    for i, moment in enumerate(moments[:4]):
        clips.append({
            "index": i + 1,
            "description": moment,
            "type": "hook" if i == 0 else "verse" if i < 3 else "bridge",
        })
    return clips


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    concept = generate_song_concept()
    print(json.dumps(concept, indent=2))
