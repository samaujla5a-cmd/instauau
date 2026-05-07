"""
AI MODEL PIPELINE — AI image + voiceover reel
"""
import asyncio, os, re, json, random, logging, requests, subprocess
from pathlib import Path
from datetime import datetime
from core.gemini_client import gemini

logger    = logging.getLogger("AI_MODEL")
BASE_DIR  = Path(__file__).parent.parent
MODEL_DIR = BASE_DIR / "output" / "ai_model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

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


def generate_content_concept() -> dict:
    td = random.choice(LIFESTYLE_THEMES)
    prompt = f"""Create Instagram content for an AI lifestyle model account.
Theme: {td['theme']}, Vibe: {td['vibe']}
Return ONLY valid JSON, no markdown:
{{
    "image_prompt": "photorealistic beautiful model, {td['vibe']}, professional photography, high fashion, Instagram aesthetic, 8k. Fully clothed, tasteful.",
    "quote": "short motivational quote max 8 words no special characters",
    "caption": "Instagram caption with emojis 150 chars max",
    "hashtags": ["#lifestyle","#fashion","#aimodel","#aesthetic","#motivation","#viral","#fyp"]
}}"""
    raw  = re.sub(r"```json|```", "", gemini(prompt)).strip()
    data = json.loads(raw)
    data["theme"] = td["theme"]
    logger.info(f"Generated concept: {td['theme']}")
    return data


def generate_ai_image(prompt: str) -> str:
    import urllib.parse
    session  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = str(MODEL_DIR / f"model_{session}.jpg")
    encoded  = urllib.parse.quote(prompt[:500])
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1080&height=1350&nologo=true&enhance=true&model=flux"
    )
    logger.info("Generating AI model image via Pollinations.ai...")
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=90)
            if resp.status_code == 200 and len(resp.content) > 10_000:
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                logger.info(f"AI image saved: {out_path}")
                return out_path
        except Exception as e:
            logger.warning(f"Image attempt {attempt + 1} failed: {e}")
    # Fallback: solid colour placeholder image
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "color=c=#1a1a2e:size=1080x1350:rate=1",
        "-frames:v", "1", out_path,
    ], capture_output=True)
    return out_path


async def _tts(text: str, path: str) -> None:
    import edge_tts
    await edge_tts.Communicate(text, "en-US-JennyNeural", rate="+5%").save(path)


def generate_voiceover(quote: str, session: str) -> str | None:
    if not quote:
        return None
    try:
        path = str(MODEL_DIR / f"voice_{session}.mp3")
        asyncio.run(_tts(quote, path))
        logger.info(f"✅ Voiceover: {path}")
        return path
    except Exception as e:
        logger.warning(f"TTS failed: {e}")
        return None


def _safe_text(t: str) -> str:
    return re.sub(r"[^A-Za-z0-9 ]", "", t)[:50]


def _probe_ok(path: str) -> bool:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name",
         "-of", "default=noprint_wrappers=1", path],
        capture_output=True, timeout=20,
    )
    return r.returncode == 0


def _ffmpeg(cmd: list, timeout: int = 120) -> str:
    r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    return r.stderr.decode(errors="replace")


def create_reel_from_image(image_path: str, content: dict, duration: int = 15) -> str:
    session    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path   = str(MODEL_DIR / f"reel_{session}.mp4")
    tmp_path   = out_path + ".tmp.mp4"
    quote_safe = _safe_text(content.get("quote", ""))
    voice_path = generate_voiceover(quote_safe, session)

    logger.info("Creating Reel from AI image...")

    vf_base = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    vf_text = (
        f",drawtext=text='{quote_safe}'"
        f":fontfile={FONT}:fontsize=52:fontcolor=white"
        f":bordercolor=black:borderw=3"
        f":x=(w-text_w)/2:y=h*0.78"
        f":box=1:boxcolor=black@0.45:boxborderw=14"
    ) if quote_safe else ""

    def _base_cmd(vf: str, preset: str, output: str) -> list:
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", image_path]
        if voice_path:
            cmd += ["-i", voice_path, "-map", "0:v", "-map", "1:a",
                    "-c:a", "aac", "-b:a", "128k"]
        else:
            cmd += ["-map", "0:v", "-an"]
        cmd += [
            "-vf", vf,
            "-t", str(duration),
            "-c:v", "libx264", "-preset", preset,
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-shortest",
            output,
        ]
        return cmd

    # Attempt 1: with text overlay
    err = _ffmpeg(_base_cmd(vf_base + vf_text, "fast", tmp_path), timeout=120)
    sz  = Path(tmp_path).stat().st_size if Path(tmp_path).exists() else 0
    if sz >= 50_000 and _probe_ok(tmp_path):
        os.replace(tmp_path, out_path)
        logger.info(f"✅ AI Model reel: {out_path}")
        return out_path

    logger.error(f"Attempt 1 produced {sz}b stderr: {err[-300:]}")
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    # Attempt 2: no drawtext
    err = _ffmpeg(_base_cmd(vf_base, "fast", tmp_path), timeout=120)
    sz  = Path(tmp_path).stat().st_size if Path(tmp_path).exists() else 0
    if sz >= 50_000 and _probe_ok(tmp_path):
        os.replace(tmp_path, out_path)
        logger.info(f"✅ Reel (no text): {out_path}")
        return out_path

    logger.error(f"Attempt 2 produced {sz}b stderr: {err[-300:]}")
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    # Attempt 3: ultrafast, no audio fallback
    err = _ffmpeg(_base_cmd(vf_base, "ultrafast", out_path), timeout=120)
    sz  = Path(out_path).stat().st_size if Path(out_path).exists() else 0
    if sz < 50_000:
        raise RuntimeError(
            f"All 3 AI Model FFmpeg attempts failed. Last stderr: {err[-300:]}"
        )
    logger.info(f"✅ Reel (ultrafast): {out_path} ({sz // 1024}KB)")
    return out_path


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
        content            = generate_content_concept()
        result["theme"]    = content.get("theme")
        result["title"]    = content.get("theme", "AI Model Post")
        result["caption"]  = content.get("caption")
        result["hashtags"] = content.get("hashtags", [])
        image_path = generate_ai_image(
            content.get("image_prompt", "beautiful woman lifestyle photo"))
        result["image_path"] = image_path
        result["video_path"] = create_reel_from_image(image_path, content)
        logger.info(f"AI Model reel ready: {result['video_path']}")
    except Exception as e:
        logger.error(f"AI Model pipeline failed: {e}", exc_info=True)
        result["errors"].append(str(e))
    result["completed_at"] = datetime.now().isoformat()
    return result
