"""
CLIP EXTRACTOR — AI-powered best moment detection for Shorts
"""

import json
import logging
import re

from core.gemini_client import gemini as _ask_ai

logger = logging.getLogger(__name__)

# Typical song structure timing estimates (seconds)
SECTION_TIMES = {
    "hook_1":   (15,  45),
    "verse1":   (45, 100),
    "hook_2":   (100, 130),
    "verse2":   (130, 185),
    "bridge":   (185, 210),
    "hook_3":   (210, 240),
}


def get_clip_timestamps(concept: dict, audio_duration: float) -> list[dict]:
    """
    Use AI (Groq→Gemini fallback) to determine the best 4 clip windows.
    Returns list of {start_sec, end_sec, title, caption_hook, section, energy_level}
    """
    logger.info("🔍 Analyzing song for best short moments...")

    prompt = f"""You are a social media content strategist specializing in viral short-form music content.

Song details:
- Title: {concept['title']}
- Total duration: {audio_duration:.0f} seconds
- Hook: {concept['hook']}
- Verse 1 preview: {concept['verse1'][:200]}
- Bridge: {concept['bridge']}
- Mood tags: {concept['mood_tags']}

Structure estimate (typical for {audio_duration:.0f}s song):
{json.dumps(SECTION_TIMES, indent=2)}

Task: Identify exactly 4 clip windows (each 30-60 seconds) that would perform best as
YouTube Shorts and Instagram Reels. Prioritize:
1. The catchiest hook moment (most likely to go viral)
2. A bar-heavy verse with impressive flow
3. A philosophical/introspective moment (good for engagement comments)
4. The climax/bridge moment with highest energy

Return ONLY a JSON array with exactly 4 objects:
[
  {{
    "clip_number": 1,
    "start_sec": 15.0,
    "end_sec": 58.0,
    "section": "hook",
    "title": "Short punchy title for this clip (5 words max)",
    "caption_hook": "First line of caption that stops the scroll",
    "why_viral": "One sentence on why this moment works",
    "energy_level": "low|medium|high|explosive"
  }}
]

Make start_sec and end_sec realistic based on the song duration {audio_duration:.0f}s.
Each clip must be 30-60 seconds. No overlapping clips.
Return ONLY valid JSON array."""

    raw = _ask_ai(prompt)
    raw = re.sub(r"^```json\s*|^```\s*|```$", "", raw, flags=re.MULTILINE).strip()
    clips = json.loads(raw)

    validated = []
    clip_len  = min(30, audio_duration / 4) if audio_duration < 120 else 45

    for i, clip in enumerate(clips[:4]):
        if audio_duration < 120:
            start = max(0, (audio_duration / 4) * i)
            end   = min(audio_duration, start + clip_len)
        else:
            start = max(0, float(clip["start_sec"]))
            end   = min(audio_duration, float(clip["end_sec"]))

        if end - start < 10:
            end = min(audio_duration, start + clip_len)
        if start >= audio_duration:
            start = max(0, audio_duration - clip_len)
            end   = audio_duration

        clip["start_sec"] = start
        clip["end_sec"]   = end
        clip["duration"]  = end - start
        validated.append(clip)
        logger.info(
            f"  📌 Clip {clip['clip_number']}: {start:.0f}s–{end:.0f}s "
            f"({clip['section']}) - {clip['energy_level']} energy"
        )

    return validated


def trim_audio_clip(audio_path: str, start_sec: float, end_sec: float, out_path: str) -> str:
    """Trim audio file to clip window using pydub."""
    from pydub import AudioSegment
    audio = AudioSegment.from_file(audio_path)
    clip  = audio[int(start_sec * 1000): int(end_sec * 1000)]
    clip  = clip.fade_in(300).fade_out(500)
    clip.export(out_path, format="mp3", bitrate="192k")
    return out_path


def get_clip_metadata(concept: dict, clip: dict, hashtags: list[str]) -> dict:
    """Build upload-ready metadata for each short/reel."""
    base_caption = clip.get("caption_hook", "")
    hashtag_str  = " ".join(hashtags)

    return {
        "yt_title":       f"{clip['title']} 🌿 {concept['title']} #Shorts",
        "yt_description": (
            f"{base_caption}\n\n{concept['title']} — Full song on channel 🔔\n\n{hashtag_str}"
        ),
        "ig_caption":     f"{base_caption} 🎵 {concept['title']}\n\n{hashtag_str}",
        "start_sec":      clip["start_sec"],
        "end_sec":        clip["end_sec"],
        "energy":         clip.get("energy_level", "medium"),
        "section":        clip.get("section", "unknown"),
    }
