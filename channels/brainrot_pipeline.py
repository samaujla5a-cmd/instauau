"""
BRAINROT PIPELINE
Subway Surfers + Minecraft split screen
Auto trending audio + AI viral text via Gemini Flash (free)
"""
import asyncio
import os
import re
import json
import random
import logging
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

from core.gemini_client import gemini as _gemini

logger = logging.getLogger("BRAINROT")

BASE_DIR   = Path(__file__).parent.parent
BRAIN_DIR  = BASE_DIR / "output" / "brainrot"
BRAIN_DIR.mkdir(parents=True, exist_ok=True)

# Local bundled fallback clips (commit short loops to assets/ to avoid yt-dlp on Railway)
ASSETS_DIR = BASE_DIR / "assets"
LOCAL_CLIPS = {
    "subway":    ASSETS_DIR / "subway.mp4",
    "minecraft": ASSETS_DIR / "minecraft.mp4",
}

BRAINROT_COLORS = {"subway": "#FF6B35", "minecraft": "#5D8A3C"}

VIRAL_TOPICS = [
    "sigma male rules nobody talks about",
    "things that hit different at 3am",
    "facts that sound fake but are real",
    "things gen z will never understand",
    "unwritten rules of life",
    "things that are lowkey illegal",
    "mind blowing facts about space",
    "dark psychology tricks that actually work",
    "things you didn't know about your brain",
    "life hacks that actually work",
    "facts about money nobody teaches you",
    "things that will make you question reality",
]


def generate_viral_text() -> dict:
    topic = random.choice(VIRAL_TOPICS)
    prompt = f"""Generate viral brainrot-style content for Instagram Reels about: "{topic}"

Return ONLY a valid JSON object, no markdown, no extra text:
{{
    "hook": "SHORT punchy hook text (max 8 words, ALL CAPS, no punctuation)",
    "points": ["point 1 (max 10 words)", "point 2 (max 10 words)", "point 3 (max 10 words)", "point 4 (max 10 words)", "point 5 (max 10 words)"],
    "caption": "Instagram caption with emojis and hashtags (200 chars max)",
    "hashtags": ["#brainrot", "#viral", "#fyp", "#facts", "#mindblown"]
}}

Make it genuinely interesting and shareable. No asterisks, no markdown."""

    text = _gemini(prompt)
    text = re.sub(r"```json|```", "", text).strip()
    data = json.loads(text)
    data["topic"] = topic
    logger.info(f"Generated brainrot topic: {topic}")
    return data


async def _make_tts_voice(text: str, out_path: str) -> None:
    """Generate TTS voiceover using edge-tts."""
    import edge_tts
    communicate = edge_tts.Communicate(text, "en-US-GuyNeural", rate="+15%")
    await communicate.save(out_path)


def generate_voiceover(hook: str, points: list, session: str) -> str | None:
    """Create a TTS voiceover mp3. Returns path or None if edge-tts unavailable."""
    try:
        voice_text = hook + ". " + ". ".join(points[:5])
        voice_path = str(BRAIN_DIR / f"voice_{session}.mp3")
        asyncio.run(_make_tts_voice(voice_text, voice_path))
        logger.info(f"✅ Voiceover generated: {voice_path}")
        return voice_path
    except Exception as e:
        logger.warning(f"TTS voiceover failed ({e}) — video will have no audio")
        return None


def get_background_clip(clip_type: str, duration: int = 30) -> str:
    out_path = BRAIN_DIR / f"{clip_type}_{datetime.now().strftime('%H%M%S')}.mp4"

    # FIX: Try local bundled clip first (Railway IPs are blocked by YouTube)
    local = LOCAL_CLIPS.get(clip_type)
    if local and local.exists():
        logger.info(f"Using local bundled {clip_type} clip")
        return str(local)

    # Try yt-dlp (works locally, usually fails on Railway)
    search_term = (
        "subway surfers gameplay no commentary"
        if clip_type == "subway"
        else "minecraft parkour gameplay no commentary"
    )
    try:
        result = subprocess.run([
            "yt-dlp", f"ytsearch1:{search_term}",
            "--match-filter", "duration < 600",
            "-f", "worst[ext=mp4]/worst",
            "-o", str(out_path),
            "--no-playlist", "--quiet",
        ], capture_output=True, timeout=60)
        if out_path.exists():
            logger.info(f"Downloaded {clip_type} clip via yt-dlp")
            return str(out_path)
    except Exception as e:
        logger.warning(f"yt-dlp failed: {e} — using solid color fallback")

    # Last resort: solid color background
    color = BRAINROT_COLORS.get(clip_type, "#111111")
    logger.info(f"Generating solid color fallback for {clip_type}")
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={color}:size=1080x960:rate=30",
        "-t", str(duration),
        "-c:v", "libx264", str(out_path)
    ], capture_output=True)
    return str(out_path)


def create_split_screen_video(content: dict, duration: int = 45) -> str:
    session     = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path    = BRAIN_DIR / f"brainrot_{session}.mp4"
    top_clip    = get_background_clip("subway", duration)
    bottom_clip = get_background_clip("minecraft", duration)

    hook   = content.get("hook", "MIND BLOWING FACTS")
    points = content.get("points", [])

    # FIX: generate TTS voiceover so the video has audio
    voice_path = generate_voiceover(hook, points, session)

    def _esc(text):
        # Remove quotes entirely, escape special ffmpeg drawtext chars
        return (text.replace("'", "")
                    .replace('"', '')
                    .replace(":", "\\:")
                    .replace("%", "\\%")
                    .replace("[", "")
                    .replace("]", "")
                    .replace(",", " "))

    hook_safe = _esc(hook)
    drawtext_filters = [
        f"drawtext=text='{hook_safe}'"
        f":fontsize=52:fontcolor=yellow:bordercolor=black:borderw=3"
        f":x=(w-text_w)/2:y=80"
        f":box=1:boxcolor=black@0.5:boxborderw=10"
        f":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]

    for i, point in enumerate(points[:5]):
        start_time = 3 + (i * 7)
        end_time   = start_time + 6
        safe_point = _esc(point)
        y_pos = 900 + (i * 80)
        drawtext_filters.append(
            f"drawtext=text='{safe_point}'"
            f":fontsize=38:fontcolor=white:bordercolor=black:borderw=2"
            f":x=(w-text_w)/2:y={y_pos}"
            f":box=1:boxcolor=black@0.6:boxborderw=8"
            f":enable='between(t\\,{start_time}\\,{end_time})'"
            f":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        )

    drawtext_str = ",".join(drawtext_filters)

    # Build ffmpeg command — include audio if voiceover was generated
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", top_clip,
        "-stream_loop", "-1", "-i", bottom_clip,
    ]
    if voice_path:
        cmd += ["-i", voice_path]

    filter_complex = (
        f"[0:v]scale=1080:960,trim=duration={duration}[top];"
        f"[1:v]scale=1080:960,trim=duration={duration}[bot];"
        f"[top][bot]vstack=inputs=2[stacked];"
        f"[stacked]{drawtext_str}[out]"
    )
    cmd += ["-filter_complex", filter_complex, "-map", "[out]"]

    if voice_path:
        # map audio from the 3rd input (index 2), trim to video duration
        cmd += ["-map", "2:a", "-c:a", "aac", "-shortest"]

    cmd += [
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast",
        "-b:v", "3500k", "-maxrate", "3500k", "-bufsize", "7000k",
        "-r", "30", "-g", "60",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_path)
    ]

    logger.info("Creating split screen video...")
    result = subprocess.run(cmd, capture_output=True, timeout=300)

    if not out_path.exists():
        logger.error(f"FFmpeg failed: {result.stderr.decode()[-500:]}")
        # Simple fallback without text overlay
        fallback_cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", top_clip,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
            "-t", str(duration), "-c:v", "libx264",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)
        ]
        if voice_path:
            fallback_cmd = [
                "ffmpeg", "-y",
                "-stream_loop", "-1", "-i", top_clip,
                "-i", voice_path,
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
                "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-shortest",
                "-t", str(duration), "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)
            ]
        subprocess.run(fallback_cmd, capture_output=True, timeout=120)

    logger.info(f"Split screen video created: {out_path}")
    return str(out_path)


def run_brainrot_pipeline() -> dict:
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"BRAINROT PIPELINE START | {session_id}")
    result = {
        "session_id": session_id, "channel": "brainrot",
        "started_at": datetime.now().isoformat(),
        "video_path": None, "caption": None, "hashtags": [], "errors": [],
    }
    try:
        content = generate_viral_text()
        result["topic"]    = content.get("topic")
        result["caption"]  = content.get("caption")
        result["hashtags"] = content.get("hashtags", [])
        video_path = create_split_screen_video(content)
        result["video_path"] = video_path
        logger.info(f"Brainrot video ready: {video_path}")
    except Exception as e:
        logger.error(f"Brainrot pipeline failed: {e}", exc_info=True)
        result["errors"].append(str(e))
    result["completed_at"] = datetime.now().isoformat()
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_brainrot_pipeline()
    print(json.dumps(result, indent=2))
