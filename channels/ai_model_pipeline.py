"""
AI MODEL PIPELINE — Consistent AI Girl Video Reels
====================================================
Flow:
  1. Generate content concept (Gemini/Groq)
  2. Generate base model image via kie.ai Flux (consistent seed = same girl)
  3. Animate image into video via kie.ai Seedance (real moving video)
  4. Add quote overlay + voiceover via FFmpeg
  5. Return reel-ready MP4

Same girl every video = locked character seed + consistent prompt.
"""

import asyncio
import json
import logging
import os
import random
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests

from core.gemini_client import gemini
from config import BASE_DIR

logger    = logging.getLogger("AI_MODEL")
MODEL_DIR = Path(BASE_DIR) / "output" / "ai_model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

KIE_API_KEY = os.getenv("KIE_API_KEY", "")

# kie.ai API endpoints
KIE_IMAGE_URL    = "https://api.kie.ai/api/v1/image/flux/generate"
KIE_VIDEO_URL    = "https://api.kie.ai/api/v1/video/seedance/generate"
KIE_TASK_IMG_URL = "https://api.kie.ai/api/v1/image/get"
KIE_TASK_VID_URL = "https://api.kie.ai/api/v1/video/get"

MAX_WAIT = 300
POLL_INT = 10

# LOCKED CHARACTER — same girl every video
LOCKED_CHARACTER = (
    "beautiful indian woman, 24 years old, long dark hair, sharp facial features, "
    "light brown skin, confident expression, photorealistic, 8k, professional photography"
)

LIFESTYLE_THEMES = [
    {"theme": "morning routine aesthetic", "vibe": "soft golden hour, luxury apartment, coffee, minimal white outfit"},
    {"theme": "fashion outfit of the day",  "vibe": "street style, confident pose, urban background, stylish"},
    {"theme": "gym motivation",             "vibe": "athletic wear, gym mirror, strong confident look"},
    {"theme": "travel aesthetic",           "vibe": "exotic beach location, golden sunset, wanderlust"},
    {"theme": "self care sunday",           "vibe": "cozy robe, candles, skincare, peaceful bedroom"},
    {"theme": "night out glam",             "vibe": "elegant dress, city lights at night, glamorous look"},
    {"theme": "beach summer vibes",         "vibe": "sunset beach, summer dress, golden hour light"},
    {"theme": "boss energy",                "vibe": "business casual, city skyline, confident smile"},
]


def _kie_headers():
    if not KIE_API_KEY:
        raise ValueError(
            "KIE_API_KEY not set!\n"
            "Get free key (5000 credits, no card): https://kie.ai"
        )
    return {"Authorization": f"Bearer {KIE_API_KEY}", "Content-Type": "application/json"}


def _poll_image(task_id: str) -> str:
    """Poll until image task done. Returns image URL."""
    waited = 0
    while waited < MAX_WAIT:
        time.sleep(POLL_INT)
        waited += POLL_INT
        try:
            r = requests.get(KIE_TASK_IMG_URL, params={"taskId": task_id},
                             headers=_kie_headers(), timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"  Image poll error (retry): {e}")
            continue
        data   = r.json().get("data") or {}
        status = data.get("status", "PENDING")
        logger.info(f"  Image [{task_id}]: {status} ({waited}s)")
        if status == "SUCCESS":
            resp = data.get("response") or {}
            url  = resp.get("imageUrl") or resp.get("url") or ""
            if not url:
                raise RuntimeError(f"SUCCESS but no imageUrl: {data}")
            return url
        if status in ("ERROR", "FAILED"):
            raise RuntimeError(f"Image generation failed: {data.get('error', data)}")
    raise TimeoutError("Image task timed out")


def _poll_video(task_id: str) -> str:
    """Poll until video task done. Returns video URL."""
    waited = 0
    while waited < MAX_WAIT:
        time.sleep(POLL_INT)
        waited += POLL_INT
        try:
            r = requests.get(KIE_TASK_VID_URL, params={"taskId": task_id},
                             headers=_kie_headers(), timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"  Video poll error (retry): {e}")
            continue
        data   = r.json().get("data") or {}
        status = data.get("status", "PENDING")
        logger.info(f"  Video [{task_id}]: {status} ({waited}s)")
        if status == "SUCCESS":
            resp = data.get("response") or {}
            url  = resp.get("videoUrl") or resp.get("url") or ""
            if not url:
                raise RuntimeError(f"SUCCESS but no videoUrl: {data}")
            return url
        if status in ("ERROR", "FAILED"):
            raise RuntimeError(f"Video generation failed: {data.get('error', data)}")
    raise TimeoutError("Video task timed out")


def _download(url: str, path: str) -> str:
    r = requests.get(url, timeout=180, stream=True)
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(65536):
            f.write(chunk)
    size_kb = Path(path).stat().st_size // 1024
    logger.info(f"  ✅ Downloaded: {path} ({size_kb}KB)")
    if size_kb < 5:
        raise RuntimeError(f"Downloaded file too small ({size_kb}KB)")
    return path


def generate_content_concept() -> dict:
    td     = random.choice(LIFESTYLE_THEMES)
    prompt = f"""Create Instagram content for an AI lifestyle model account.
Theme: {td['theme']}, Vibe: {td['vibe']}
Return ONLY valid JSON, no markdown:
{{
    "quote": "short motivational quote max 8 words no special characters",
    "caption": "Instagram caption with emojis 150 chars max",
    "hashtags": ["#lifestyle","#fashion","#aimodel","#aesthetic","#motivation","#viral","#fyp"],
    "video_motion_prompt": "describe subtle motion: slow camera push in gentle wind soft lighting 8 words max"
}}"""
    raw  = re.sub(r"```json|```", "", gemini(prompt)).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("JSON parse failed for concept, using defaults")
        data = {
            "quote": "Stay focused and keep going",
            "caption": "Living my best life ✨",
            "hashtags": ["#lifestyle", "#aimodel", "#viral", "#fyp"],
            "video_motion_prompt": "slow cinematic push in soft light",
        }
    data["theme"] = td["theme"]
    data["vibe"]  = td["vibe"]
    return data


def generate_model_image(content: dict, session: str) -> str:
    """Generate base model image via kie.ai Flux with locked character seed."""
    image_prompt = (
        f"{LOCKED_CHARACTER}, {content['vibe']}, "
        "fully clothed, tasteful, high fashion, instagram aesthetic, "
        "natural lighting, ultra detailed, sharp focus"
    )

    logger.info("🖼️  Generating model image via kie.ai Flux...")
    resp = requests.post(
        KIE_IMAGE_URL,
        headers=_kie_headers(),
        json={
            "prompt":      image_prompt[:500],
            "model":       "flux-kontext-pro",
            "width":       1080,
            "height":      1350,
            "seed":        42,
            "callBackUrl": "https://example.com/callback",
        },
        timeout=60,
    )
    if resp.status_code == 402:
        raise RuntimeError("kie.ai credits exhausted — top up at https://kie.ai/pricing")
    if resp.status_code == 422:
        logger.warning("flux-kontext-pro unavailable, trying flux-dev...")
        resp = requests.post(
            KIE_IMAGE_URL,
            headers=_kie_headers(),
            json={
                "prompt":      image_prompt[:500],
                "model":       "flux-dev",
                "width":       1080,
                "height":      1350,
                "seed":        42,
                "callBackUrl": "https://example.com/callback",
            },
            timeout=60,
        )
    resp.raise_for_status()

    resp_data = resp.json()
    task_id   = (resp_data.get("data") or {}).get("taskId", "")
    if not task_id:
        raise RuntimeError(f"No taskId from image API: {resp_data}")

    image_url = _poll_image(task_id)
    out_path  = str(MODEL_DIR / f"model_{session}.jpg")
    return _download(image_url, out_path)


def generate_model_video(image_path: str, content: dict, session: str) -> str:
    """Animate the model image into a short video via kie.ai Seedance."""
    motion      = content.get("video_motion_prompt", "slow cinematic push in, soft light, natural movement")
    full_prompt = (
        f"{LOCKED_CHARACTER}, {content['vibe']}, "
        f"{motion}, cinematic, smooth motion, 4k quality"
    )

    logger.info("🎬 Animating model image via kie.ai Seedance...")

    import base64
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    for model_name in ["seedance-2.0-fast", "seedance-1.0-fast", "seedance"]:
        resp = requests.post(
            KIE_VIDEO_URL,
            headers=_kie_headers(),
            json={
                "prompt":      full_prompt[:500],
                "image":       f"data:image/jpeg;base64,{img_b64}",
                "model":       model_name,
                "duration":    6,
                "ratio":       "9:16",
                "callBackUrl": "https://example.com/callback",
            },
            timeout=60,
        )
        if resp.status_code == 402:
            raise RuntimeError("kie.ai credits exhausted")
        if resp.status_code == 422:
            logger.warning(f"  Model '{model_name}' not available, trying next...")
            continue
        if resp.status_code == 200:
            resp_data = resp.json()
            task_id   = (resp_data.get("data") or {}).get("taskId", "")
            if task_id:
                logger.info(f"  Using model: {model_name}")
                video_url = _poll_video(task_id)
                raw_path  = str(MODEL_DIR / f"raw_video_{session}.mp4")
                return _download(video_url, raw_path)
        logger.warning(f"  Seedance {model_name} HTTP {resp.status_code}")

    logger.warning("  All Seedance models failed — using FFmpeg Ken Burns fallback (free)")
    return _ken_burns_fallback(image_path, content, session)


def _ken_burns_fallback(image_path: str, content: dict, session: str) -> str:
    """Free fallback: Ken Burns slow zoom + pan on the image."""
    logger.info("  Using Ken Burns zoom fallback...")
    out_path = str(MODEL_DIR / f"raw_video_{session}.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-vf", (
            "scale=1200:1600,"
            "zoompan=z='min(zoom+0.0008,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            ":d=180:s=1080x1350,"
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920"
        ),
        "-t", "6",
        "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        out_path,
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    if not Path(out_path).exists() or Path(out_path).stat().st_size < 50_000:
        raise RuntimeError(f"Ken Burns fallback failed: {r.stderr.decode()[-300:]}")
    return out_path


async def _tts(text: str, path: str) -> None:
    import edge_tts
    await edge_tts.Communicate(text, "en-US-JennyNeural", rate="+5%").save(path)


def _add_audio_and_overlay(video_path: str, content: dict, session: str) -> str:
    """Add voiceover quote + text overlay to the video."""
    quote      = content.get("quote", "")
    out_path   = str(MODEL_DIR / f"reel_{session}.mp4")
    tmp_path   = out_path + ".tmp.mp4"
    quote_safe = re.sub(r"[^A-Za-z0-9 ]", "", quote)[:50]

    voice_path = None
    if quote_safe:
        vp = str(MODEL_DIR / f"voice_{session}.mp3")
        try:
            asyncio.run(_tts(quote_safe, vp))
            if Path(vp).exists() and Path(vp).stat().st_size > 1000:
                voice_path = vp
        except Exception as e:
            logger.warning(f"  TTS failed: {e}")

    vf_base = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    vf_text = (
        f",drawtext=text='{quote_safe}'"
        f":fontfile={FONT}:fontsize=52:fontcolor=white"
        f":bordercolor=black:borderw=3"
        f":x=(w-text_w)/2:y=h*0.78"
        f":box=1:boxcolor=black@0.5:boxborderw=14"
    ) if quote_safe else ""

    cmd = ["ffmpeg", "-y", "-i", video_path]
    if voice_path:
        cmd += ["-i", voice_path, "-map", "0:v", "-map", "1:a",
                "-c:a", "aac", "-b:a", "128k"]
    else:
        cmd += ["-map", "0:v", "-an"]

    cmd += [
        "-vf", vf_base + vf_text,
        "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-t", "15",
        "-shortest",
        tmp_path,
    ]

    r  = subprocess.run(cmd, capture_output=True, timeout=120)
    sz = Path(tmp_path).stat().st_size if Path(tmp_path).exists() else 0
    if sz >= 50_000:
        os.replace(tmp_path, out_path)
        return out_path

    # Fallback: no text overlay
    cmd2 = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", vf_base,
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an", "-t", "15",
        out_path,
    ]
    subprocess.run(cmd2, capture_output=True, timeout=120)
    sz = Path(out_path).stat().st_size if Path(out_path).exists() else 0
    if sz < 50_000:
        raise RuntimeError(f"Model video final encode failed: {r.stderr.decode()[-300:]}")
    return out_path


def run_ai_model_pipeline() -> dict:
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"AI MODEL PIPELINE START | {session_id}")
    result = {
        "session_id": session_id, "channel": "ai_model",
        "started_at": datetime.now().isoformat(),
        "video_path": None, "caption": None, "hashtags": [], "errors": [],
    }
    try:
        content            = generate_content_concept()
        result["theme"]    = content.get("theme")
        result["title"]    = content.get("theme", "AI Model Post")
        result["caption"]  = content.get("caption")
        result["hashtags"] = content.get("hashtags", [])

        image_path = generate_model_image(content, session_id)
        raw_video  = generate_model_video(image_path, content, session_id)
        final_reel = _add_audio_and_overlay(raw_video, content, session_id)

        result["video_path"] = final_reel
        logger.info(f"AI Model reel ready: {final_reel}")
    except Exception as e:
        logger.error(f"AI Model pipeline failed: {e}", exc_info=True)
        result["errors"].append(str(e))
    result["completed_at"] = datetime.now().isoformat()
    return result
