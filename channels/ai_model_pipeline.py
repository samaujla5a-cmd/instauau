"""
AI LIFESTYLE MODEL PIPELINE
AI generated fashion/lifestyle content
Motivational quotes + trending aesthetic via Gemini Flash (free)
"""
import asyncio
import os
import re
import json
import random
import logging
import requests
import subprocess
from pathlib import Path
from datetime import datetime

from core.gemini_client import gemini as _gemini

logger = logging.getLogger("AI_MODEL")

BASE_DIR   = Path(__file__).parent.parent
MODEL_DIR  = BASE_DIR / "output" / "ai_model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


LIFESTYLE_THEMES = [
    {"theme": "morning routine aesthetic", "vibe": "soft golden hour, luxury apartment, coffee, minimal"},
    {"theme": "fashion outfit of the day",  "vibe": "street style, confident pose, urban background"},
    {"theme": "gym motivation",             "vibe": "athletic wear, gym aesthetic, strong and confident"},
    {"theme": "travel aesthetic",           "vibe": "exotic location, golden light, wanderlust vibes"},
    {"theme": "self care sunday",           "vibe": "cozy, skincare, candles, peaceful bedroom"},
    {"theme": "boss babe energy",           "vibe": "business casual, city skyline, confident smile"},
    {"theme": "night out glam",             "vibe": "elegant dress, city lights, glamorous makeup"},
    {"theme": "beach summer vibes",         "vibe": "sunset beach, golden skin, summer aesthetic"},
]

QUOTE_STYLES = [
    "short powerful motivational quote",
    "aesthetic self love quote",
    "boss mindset quote",
    "glow up reminder quote",
    "confidence affirmation",
]


def generate_content_concept() -> dict:
    theme_data  = random.choice(LIFESTYLE_THEMES)
    quote_style = random.choice(QUOTE_STYLES)

    prompt = f"""Create Instagram content for an AI lifestyle/fashion model account.

Theme: {theme_data['theme']}
Vibe: {theme_data['vibe']}

Return ONLY a valid JSON object, no markdown, no extra text:
{{
    "image_prompt": "detailed prompt for a beautiful AI model photo. Include: photorealistic, {theme_data['vibe']}, professional photography, soft lighting, high fashion, Instagram aesthetic, 8k quality. NO nudity, fully clothed, tasteful.",
    "quote": "a {quote_style} (max 12 words, impactful)",
    "caption": "Instagram caption with personality, emojis, call to action (150 chars max)",
    "hashtags": ["#lifestyle", "#fashion", "#aimodel", "#aesthetic", "#motivation", "#glow", "#selfcare", "#model", "#viral", "#fyp", "#explore", "#instagram"]
}}

Make it feel authentic and aspirational. No asterisks."""

    text = _gemini(prompt)
    text = re.sub(r"```json|```", "", text).strip()
    data = json.loads(text)
    data["theme"] = theme_data["theme"]
    logger.info(f"Generated concept: {theme_data['theme']}")
    return data


def generate_ai_image(image_prompt: str) -> str:
    import urllib.parse
    session  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = MODEL_DIR / f"model_{session}.jpg"

    encoded = urllib.parse.quote(image_prompt[:500])
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1350&nologo=true&enhance=true&model=flux"

    logger.info("Generating AI model image via Pollinations.ai...")
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=90)
            if resp.status_code == 200 and len(resp.content) > 10000:
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                logger.info(f"AI image saved: {out_path}")
                return str(out_path)
            logger.warning(f"Pollinations attempt {attempt+1} returned {resp.status_code}")
        except Exception as e:
            logger.warning(f"Image attempt {attempt+1} failed: {e}")

    # Fallback: solid color image
    logger.info("Using solid color fallback image")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "color=c=#1a1a2e:size=1080x1350:rate=1",
        "-frames:v", "1", str(out_path)
    ], capture_output=True)
    return str(out_path)


async def _make_tts_voice(text: str, out_path: str) -> None:
    """Generate TTS voiceover using edge-tts."""
    import edge_tts
    communicate = edge_tts.Communicate(text, "en-US-JennyNeural", rate="+5%")
    await communicate.save(out_path)


def generate_voiceover(quote: str, session: str) -> str | None:
    """Create a TTS voiceover for the quote. Returns path or None on failure."""
    if not quote:
        return None
    try:
        voice_path = str(MODEL_DIR / f"voice_{session}.mp3")
        asyncio.run(_make_tts_voice(quote, voice_path))
        logger.info(f"✅ Voiceover generated: {voice_path}")
        return voice_path
    except Exception as e:
        logger.warning(f"TTS voiceover failed ({e}) — reel will have no audio")
        return None


def create_reel_from_image(image_path: str, content: dict, duration: int = 15) -> str:
    session   = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path  = MODEL_DIR / f"reel_{session}.mp4"
    quote_raw = content.get("quote", "")
    quote     = quote_raw.replace("'", "\\'").replace(":", "\\:")

    # FIX: generate TTS voiceover so the reel has audio
    voice_path = generate_voiceover(quote_raw, session)

    base_cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
    ]
    if voice_path:
        base_cmd += ["-i", voice_path]

    filter_complex = (
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,"
        f"drawtext=text='{quote}'"
        f":fontsize=56:fontcolor=white:bordercolor=black@0.8:borderw=3"
        f":x=(w-text_w)/2:y=h*0.75"
        f":box=1:boxcolor=black@0.4:boxborderw=15"
        f":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf[out]"
    )

    cmd = base_cmd + ["-filter_complex", filter_complex, "-map", "[out]"]
    if voice_path:
        cmd += ["-map", "1:a", "-c:a", "aac", "-b:a", "128k", "-shortest"]

    cmd += [
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast",
        "-b:v", "3500k", "-maxrate", "3500k", "-bufsize", "7000k",
        "-r", "30", "-g", "60",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_path)
    ]

    logger.info("Creating Reel from AI image...")
    result = subprocess.run(cmd, capture_output=True, timeout=120)

    if not out_path.exists():
        logger.error(f"FFmpeg error: {result.stderr.decode()[-300:]}")
        fallback_cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_path,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            "-t", str(duration), "-c:v", "libx264",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)
        ]
        if voice_path:
            fallback_cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", image_path,
                "-i", voice_path,
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-shortest",
                "-t", str(duration), "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)
            ]
        subprocess.run(fallback_cmd, capture_output=True, timeout=60)

    return str(out_path)


def run_ai_model_pipeline() -> dict:
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"AI MODEL PIPELINE START | {session_id}")
    result = {
        "session_id": session_id, "channel": "ai_model",
        "started_at": datetime.now().isoformat(),
        "image_path": None, "video_path": None,
        "caption": None, "hashtags": [], "errors": [],
    }
    try:
        content = generate_content_concept()
        result["theme"]    = content.get("theme")
        result["title"]    = content.get("theme", "AI Model Post")  # for Telegram
        result["caption"]  = content.get("caption")
        result["hashtags"] = content.get("hashtags", [])
        image_path = generate_ai_image(content.get("image_prompt", "beautiful woman lifestyle photo"))
        result["image_path"] = image_path
        video_path = create_reel_from_image(image_path, content)
        result["video_path"] = video_path
        logger.info(f"AI Model reel ready: {video_path}")
    except Exception as e:
        logger.error(f"AI Model pipeline failed: {e}", exc_info=True)
        result["errors"].append(str(e))
    result["completed_at"] = datetime.now().isoformat()
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_ai_model_pipeline()
    print(json.dumps(result, indent=2))
