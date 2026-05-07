"""
LYRICS GENERATOR — Gemini Flash (Free)
Trippy Weed Rap | Human-like Flow
"""
import json
import random
import re
import logging
import requests
from core.gemini_client import gemini as _gemini
from config import MUSIC_STYLE

logger = logging.getLogger(__name__)

TRIPPY_WORDBANKS = {
    "cosmic": ["cosmos","nebula","stardust","galaxy","orbit","infinite void","third eye","dimension"],
    "weed":   ["chronic","OG","Mary Jane","kush","green","blunt","smoke","elevated","high as clouds"],
    "vibes":  ["frequencies","wavelength","energy","aura","vibrations","resonance","flow state"],
    "philosophical": ["consciousness","existence","perception","illusion","awakening","truth","purpose"],
}


def _safe_json_parse(raw: str) -> dict:
    """Parse JSON with auto-repair for truncated responses."""
    raw = re.sub(r"```json|```", "", raw).strip()

    # Attempt 1: direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Attempt 2: truncation repair — close any open strings/arrays/objects
    repaired = raw
    # Count open vs closed braces/brackets
    open_braces   = repaired.count("{") - repaired.count("}")
    open_brackets = repaired.count("[") - repaired.count("]")

    # If ends mid-string, close the string first
    if repaired.count('"') % 2 != 0:
        repaired += '"'

    # Close open arrays then objects
    repaired += "]" * max(0, open_brackets)
    repaired += "}" * max(0, open_braces)

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Attempt 3: extract just the fields we need via regex fallback
    logger.warning("JSON fully broken — extracting fields via regex")
    result = {}
    for field in ["title", "hook", "verse1", "verse2", "bridge",
                  "full_lyrics", "suno_prompt", "youtube_title",
                  "instagram_caption", "tagline"]:
        match = re.search(rf'"{field}"\s*:\s*"(.*?)(?<!\\)"', raw, re.DOTALL)
        if match:
            result[field] = match.group(1).replace('\\"', '"')

    # Fallback defaults for required fields
    result.setdefault("title", "Elevated State")
    result.setdefault("hook", "Floating through the cosmos, elevated mind")
    result.setdefault("verse1", "Living in the moment, third eye open wide")
    result.setdefault("verse2", "Consciousness expanding, universe inside")
    result.setdefault("bridge", "Feel the vibrations, let it all go")
    result.setdefault("full_lyrics", result["hook"])
    result.setdefault("suno_prompt", "trippy hip hop, 85 bpm, deep bass, atmospheric")
    result.setdefault("youtube_title", f"{result['title']} - Trippy Rap")
    result.setdefault("instagram_caption", "Elevated state of mind 🌿✨")
    result.setdefault("mood_tags", ["trippy", "chill", "elevated", "cosmic", "deep"])
    result.setdefault("short_hook_moments", ["Hook drop at start", "Verse 1 peak", "Bridge moment", "Final hook"])
    return result


def generate_song_concept() -> dict:
    """Generate a unique song concept with Groq→Gemini, with JSON repair on truncation."""
    theme = random.choice(MUSIC_STYLE["themes"])
    word1 = random.choice(TRIPPY_WORDBANKS["cosmic"])
    word2 = random.choice(TRIPPY_WORDBANKS["philosophical"])

    prompt = f"""You are a creative hip-hop songwriter specializing in trippy, weed-culture rap music.
Generate a complete original rap song concept and full lyrics.

THEME: {theme}
VIBE: {MUSIC_STYLE['vibe']}
MOOD: {MUSIC_STYLE['mood']}

Requirements:
- Write lyrics that sound HUMAN and authentic - not robotic or forced
- Use slang, pauses, ad-libs naturally (in parentheses like (ayy), (yeah), (smoke))
- Flow should vary - some fast bars, some slow and drawn out
- Include introspective/philosophical lines mixed with street wisdom
- Use internal rhyme schemes, not just end-rhymes
- Add trippy imagery: "{word1}", "{word2}", visual metaphors
- Structure: Hook → Verse 1 → Hook → Verse 2 → Bridge → Hook
- Length: Full song ~2.5-3 minutes when performed (350-450 words)

Return ONLY a valid JSON object with EXACTLY this structure, no markdown, no extra text:
{{
  "title": "Song title (creative, 2-5 words)",
  "tagline": "One catchy line that describes the vibe",
  "hook": "Full hook lyrics (4-8 lines, repeated 3x)",
  "verse1": "Full verse 1 lyrics (16-20 lines)",
  "verse2": "Full verse 2 lyrics (16-20 lines)",
  "bridge": "Bridge lyrics (4-8 lines)",
  "full_lyrics": "Complete assembled song with section labels",
  "suno_prompt": "A 120-word music generation prompt describing beat, instruments, mood, tempo, voice style",
  "youtube_title": "SEO-optimized YouTube title with relevant keywords",
  "youtube_description": "Full YouTube description (300 words) with timestamps, story, call to action",
  "short_hook_moments": ["4 best 30-60 second moment descriptions for shorts/reels"],
  "instagram_caption": "Engaging Instagram caption under 150 chars",
  "mood_tags": ["list","of","5","mood","descriptors"]
}}"""

    # Retry up to 3 times on JSON failure
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

    logger.error(f"All 3 attempts failed: {last_err} — using safe fallback concept")
    return {
        "title": "Elevated State",
        "theme": theme,
        "tagline": "High above the noise",
        "hook": "Elevated state of mind, floating through the cosmos\nThird eye open wide, seeing past the locus",
        "verse1": "Living in the moment, consciousness expanding\nUniverse inside me, too deep for understanding",
        "verse2": "Frequencies aligning, vibrations never lying\nSmoke rising to the stars, my spirit keeps on flying",
        "bridge": "Let it all go, feel the flow\nElevated high, watch me grow",
        "full_lyrics": "Elevated State\n\n[Hook]\nElevated state of mind...",
        "suno_prompt": "trippy hip hop, 85 bpm, deep bass, 808s, atmospheric pads, smooth flow, weed culture",
        "youtube_title": "Elevated State — Trippy Weed Rap 🌿",
        "youtube_description": "New trippy rap track. Elevated vibes only.",
        "short_hook_moments": ["Opening hook", "Verse 1 bars", "Bridge", "Final hook"],
        "instagram_caption": "Elevated state of mind 🌿✨ #rap #trippy",
        "mood_tags": ["trippy", "chill", "elevated", "cosmic", "deep"],
    }


def generate_suno_music_prompt(concept: dict) -> str:
    base = concept.get("suno_prompt", "")
    style_tags = f"[{MUSIC_STYLE['vibe']}] [{MUSIC_STYLE['genre']}]"
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
