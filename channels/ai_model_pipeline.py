"""
AI MODEL PIPELINE — Indian AI Influencer (Naina-style)
=======================================================
Reference: @naina_avtr, @_nainasharma______ style
- Consistent beautiful Indian girl character
- Traditional + modern fashion mix
- Lifestyle, fashion, motivation content
- Professional photorealistic aesthetic

FIXES vs original:
1. Ken Burns bug fixed: zoompan d= must equal total frames (fps * duration)
   Original used d=180 but that's only 6s at 30fps = correct, BUT scale
   must produce the exact resolution zoompan outputs. Fixed pipeline below.
2. Character updated to Indian AI influencer (Naina-style)
3. Themes updated to Indian lifestyle/fashion
4. Image prompt improved for consistency
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
from config import BASE_DIR, AI_MODEL_CHARACTER

logger    = logging.getLogger("AI_MODEL")
MODEL_DIR = Path(BASE_DIR) / "output" / "ai_model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

KIE_API_KEY = os.getenv("KIE_API_KEY", "")

KIE_IMAGE_ENDPOINTS = [
    "https://api.kie.ai/api/v1/flux-kontext/generate",
    "https://api.kie.ai/api/v1/flux/generate",
    "https://api.kie.ai/api/v1/image/flux/generate",
]
KIE_TASK_URL = "https://api.kie.ai/api/v1/jobs/recordInfo"

MAX_WAIT = 300
POLL_INT = 10

# Locked character — consistent Indian AI girl every video
LOCKED_CHARACTER = AI_MODEL_CHARACTER["description"]
LIFESTYLE_THEMES = AI_MODEL_CHARACTER["vibes"]


def _kie_headers():
    if not KIE_API_KEY:
        raise ValueError(
            "KIE_API_KEY not set!\n"
            "Get free key (5000 credits, no card): https://kie.ai"
        )
    return {"Authorization": f"Bearer {KIE_API_KEY}", "Content-Type": "application/json"}


def _poll_image(task_id: str) -> str:
    waited = 0
    while waited < MAX_WAIT:
        time.sleep(POLL_INT)
        waited += POLL_INT
        try:
            r = requests.get(KIE_TASK_URL, params={"taskId": task_id},
                             headers=_kie_headers(), timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"  Image poll error (retry): {e}")
            continue
        data   = r.json().get("data") or {}
        status = data.get("state") or data.get("status", "PENDING")
        logger.info(f"  Image [{task_id}]: {status} ({waited}s)")
        if status in ("success", "SUCCESS"):
            result_json = data.get("resultJson") or ""
            if result_json:
                try:
                    result = json.loads(result_json)
                    urls = result.get("resultUrls") or []
                    if urls:
                        return urls[0]
                except Exception:
                    pass
            resp = data.get("response") or {}
            url  = resp.get("imageUrl") or resp.get("url") or ""
            if not url:
                raise RuntimeError(f"SUCCESS but no imageUrl: {data}")
            return url
        if status in ("error", "ERROR", "failed", "FAILED"):
            raise RuntimeError(f"Image generation failed: {data.get('failMsg', data)}")
    raise TimeoutError("Image task timed out")


def _poll_video(task_id: str) -> str:
    waited = 0
    while waited < MAX_WAIT:
        time.sleep(POLL_INT)
        waited += POLL_INT
        try:
            r = requests.get(KIE_TASK_URL, params={"taskId": task_id},
                             headers=_kie_headers(), timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"  Video poll error (retry): {e}")
            continue
        data   = r.json().get("data") or {}
        status = data.get("state") or data.get("status", "PENDING")
        logger.info(f"  Video [{task_id}]: {status} ({waited}s)")
        if status in ("success", "SUCCESS"):
            result_json = data.get("resultJson") or ""
            if result_json:
                try:
                    result = json.loads(result_json)
                    urls = result.get("resultUrls") or []
                    if urls:
                        return urls[0]
                except Exception:
                    pass
            resp = data.get("response") or {}
            url  = resp.get("videoUrl") or resp.get("url") or ""
            if not url:
                raise RuntimeError(f"SUCCESS but no videoUrl: {data}")
            return url
        if status in ("error", "ERROR", "failed", "FAILED"):
            raise RuntimeError(f"Video generation failed: {data.get('failMsg', data)}")
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
    prompt = f"""Create Instagram content for an Indian AI lifestyle model account (like @naina_avtr).
Theme: {td['theme']}, Vibe: {td['vibe']}
Style: Mix of modern India and traditional culture. Empowering, aspirational, relatable to Indian audience.

Return ONLY valid JSON, no markdown:
{{
    "quote": "short motivational quote max 8 words, can be Hinglish or English",
    "caption": "Instagram caption with emojis 150 chars max, engaging Indian girl vibe",
    "hashtags": ["#aiinfluencer","#indianmodel","#lifestyle","#desi","#fashion","#aesthetic","#viral","#fyp"],
    "video_motion_prompt": "describe subtle model motion: slight hair movement gentle breathing soft lighting 8 words max"
}}"""
    raw  = re.sub(r"```json|```", "", gemini(prompt)).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("JSON parse failed for concept, using defaults")
        data = {
            "quote": "Stay real stay beautiful",
            "caption": "Living life on my own terms ✨🇮🇳",
            "hashtags": ["#aiinfluencer", "#indianmodel", "#lifestyle", "#desi", "#viral"],
            "video_motion_prompt": "gentle breeze hair movement soft golden light",
        }
    data["theme"] = td["theme"]
    data["vibe"]  = td["vibe"]
    return data


def _try_kie_image_request(payload: dict) -> requests.Response | None:
    """Try each kie.ai image endpoint. Returns first non-404 response or None."""
    for endpoint in KIE_IMAGE_ENDPOINTS:
        try:
            resp = requests.post(endpoint, headers=_kie_headers(),
                                 json=payload, timeout=60)
            if resp.status_code == 404:
                logger.warning(f"  kie.ai endpoint 404: {endpoint} — trying next...")
                continue
            if resp.status_code == 422:
                logger.warning(f"  kie.ai model unavailable at {endpoint} — trying next...")
                continue
            if resp.status_code == 402:
                raise RuntimeError("kie.ai credits exhausted — top up at https://kie.ai/pricing")
            return resp
        except RuntimeError:
            raise
        except requests.RequestException as e:
            logger.warning(f"  kie.ai request error ({endpoint}): {e}")
            continue
    return None


def generate_model_image(content: dict, session: str) -> str:
    """Generate Indian AI model image via kie.ai Flux."""
    image_prompt = (
        f"{LOCKED_CHARACTER}, {content['vibe']}, "
        "fully clothed, tasteful, high fashion, instagram aesthetic, "
        "natural lighting, ultra detailed, sharp focus, "
        "indian beauty standards, warm skin tones"
    )

    logger.info("🖼️  Generating Indian AI model image via kie.ai Flux...")

    for model_name in ["flux-kontext-pro", "flux-kontext-dev", "flux-dev"]:
        if "kontext" in model_name:
            payload = {
                "callBackUrl": "https://example.com/callback",
                "input": {
                    "prompt": image_prompt[:500],
                    "aspect_ratio": "4:5",
                },
            }
        else:
            payload = {
                "prompt": image_prompt[:500],
                "model": model_name,
                "width": 1080,
                "height": 1350,
                "seed": 42,  # Locked seed = same girl every time
                "callBackUrl": "https://example.com/callback",
            }
        resp = _try_kie_image_request(payload)
        if resp is None:
            logger.warning(f"  All endpoints returned 404/error for model {model_name}")
            continue

        if not resp.ok:
            logger.warning(f"  kie.ai {model_name} HTTP {resp.status_code}: {resp.text[:200]}")
            continue

        resp_data = resp.json()
        task_id   = (resp_data.get("data") or {}).get("taskId", "")
        if not task_id:
            logger.warning(f"  No taskId from kie.ai ({model_name}): {resp_data}")
            continue

        try:
            image_url = _poll_image(task_id)
            out_path  = str(MODEL_DIR / f"model_{session}.jpg")
            return _download(image_url, out_path)
        except Exception as e:
            logger.warning(f"  kie.ai image poll/download failed ({model_name}): {e}")
            continue

    # All kie.ai failed — create gradient placeholder
    logger.warning("⚠️  All kie.ai image endpoints failed — creating placeholder")
    return _create_placeholder_image(content, session)


def _create_placeholder_image(content: dict, session: str) -> str:
    """
    Create a warm gradient placeholder image when kie.ai is unavailable.
    Uses warm Indian color palette (saffron/rose/gold) instead of flat color.
    """
    out_path = str(MODEL_DIR / f"model_{session}.jpg")
    theme    = content.get("theme", "lifestyle")
    quote    = re.sub(r"[^A-Za-z0-9 ]", "", content.get("quote", theme))[:40]

    # Warm saffron gradient using two overlapping boxes + text
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "color=c=0x1a0510:size=1080x1350:rate=1",  # Deep rose-purple
        "-vf", (
            # Warm overlay gradient simulation
            "drawbox=x=0:y=0:w=iw:h=ih/2:color=0xff6b1a@0.3:t=fill,"
            "drawbox=x=0:y=ih/2:w=iw:h=ih/2:color=0x8b1a4a@0.25:t=fill,"
            # Gold accent border
            "drawbox=x=0:y=0:w=iw:h=8:color=0xffd700@0.9:t=fill,"
            "drawbox=x=0:y=ih-8:w=iw:h=8:color=0xffd700@0.9:t=fill,"
            "drawbox=x=0:y=0:w=8:h=ih:color=0xffd700@0.9:t=fill,"
            "drawbox=x=iw-8:y=0:w=8:h=ih:color=0xffd700@0.9:t=fill,"
            # Quote text
            f"drawtext=text='{quote}'"
            f":fontfile={FONT}:fontsize=68:fontcolor=white"
            f":x=(w-text_w)/2:y=(h-text_h)/2"
            f":bordercolor=black:borderw=3,"
            # Subtitle
            "drawtext=text='AI MODEL'"
            f":fontfile={FONT}:fontsize=40:fontcolor=0xffd700"
            f":x=(w-text_w)/2:y=(h-text_h)/2+100"
            ":bordercolor=black:borderw=2"
        ),
        "-frames:v", "1",
        "-q:v", "2",
        out_path,
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=30)
    if not Path(out_path).exists() or Path(out_path).stat().st_size < 1000:
        raise RuntimeError(
            f"Placeholder image creation failed: {r.stderr.decode()[-300:]}\n"
            "kie.ai image API is down AND FFmpeg fallback failed."
        )
    logger.info(f"  ✅ Placeholder image created: {out_path}")
    return out_path


def generate_model_video(image_path: str, content: dict, session: str) -> str:
    """Animate model image via kie.ai Seedance, fallback to fixed Ken Burns."""
    motion      = content.get("video_motion_prompt", "slow cinematic push in, soft light")
    full_prompt = (
        f"{LOCKED_CHARACTER}, {content['vibe']}, "
        f"{motion}, cinematic, smooth motion, 4k quality, instagram reel"
    )

    logger.info("🎬 Animating model image via kie.ai Seedance...")

    import base64
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    model_endpoint_map = {
        "seedance-2.0-fast": "https://api.kie.ai/api/v1/market/bytedance/seedance-2-fast",
        "seedance-1.5-pro":  "https://api.kie.ai/api/v1/market/bytedance/seedance-1-5-pro",
        "seedance-2.0":      "https://api.kie.ai/api/v1/market/bytedance/seedance-2",
    }

    for model_name, video_endpoint in model_endpoint_map.items():
        resp = requests.post(
            video_endpoint,
            headers=_kie_headers(),
            json={
                "callBackUrl": "https://example.com/callback",
                "input": {
                    "prompt":       full_prompt[:500],
                    "image":        f"data:image/jpeg;base64,{img_b64}",
                    "duration":     6,
                    "aspect_ratio": "9:16",
                },
            },
            timeout=60,
        )
        if resp.status_code == 402:
            raise RuntimeError("kie.ai credits exhausted")
        if resp.status_code in (404, 422):
            logger.warning(f"  Seedance model '{model_name}' not available (HTTP {resp.status_code}), trying next...")
            continue
        if resp.status_code == 200:
            d = resp.json().get("data") or {}
            task_id = d.get("taskId", "")
            if task_id:
                logger.info(f"  Using Seedance model: {model_name}")
                try:
                    video_url = _poll_video(task_id)
                    raw_path  = str(MODEL_DIR / f"raw_video_{session}.mp4")
                    return _download(video_url, raw_path)
                except Exception as e:
                    logger.warning(f"  Seedance {model_name} poll/download failed: {e}")
                    continue
        logger.warning(f"  Seedance {model_name} HTTP {resp.status_code}")

    logger.warning("  All Seedance models failed — using FFmpeg Ken Burns fallback (free)")
    return _ken_burns_fallback(image_path, content, session)


def _ken_burns_fallback(image_path: str, content: dict, session: str) -> str:
    """
    FIX: Ken Burns zoom effect.
    
    Original bug: zoompan d=180 produced 0 frames because the input image
    was scaled to 1200x1600 but zoompan output size was 1080x1350, causing
    a mismatch. Then the crop to 1080x1920 had no input at that size.
    
    Fix: Use a two-step approach:
    1. zoompan on a correctly sized input, output at final resolution
    2. No extra scale/crop after zoompan (it outputs exactly what you set in s=)
    
    Also: at 30fps for 6 seconds = 180 frames, d=180 is correct.
    The real bug was the intermediate scale producing wrong dimensions.
    """
    logger.info("  Using Ken Burns zoom fallback (FIXED)...")
    out_path = str(MODEL_DIR / f"raw_video_{session}.mp4")

    # Step 1: Get image dimensions and pre-scale to a large canvas
    # zoompan needs input >= output*maxzoom. For zoom up to 1.5x with 1080x1920 out:
    # input must be >= 1080*1.5=1620 wide and 1920*1.5=2880 tall
    # We scale input to 2160x2880 (safe margin), then zoompan outputs 1080x1920
    duration_secs = 8
    fps = 30
    total_frames = duration_secs * fps  # 240

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-vf", (
            # Scale input large enough for zoom
            "scale=2160:2880:force_original_aspect_ratio=increase,"
            "crop=2160:2880,"
            # Ken Burns: slow zoom in from 1.0 to 1.3 over total_frames frames
            # d= total_frames, s= output resolution (exact final size)
            f"zoompan="
            f"z='min(zoom+0.001,1.3)':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:"
            f"s=1080x1920:"
            f"fps={fps},"
            # Ensure correct pixel format
            "format=yuv420p"
        ),
        "-t", str(duration_secs),
        "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        out_path,
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=180)
    sz = Path(out_path).stat().st_size if Path(out_path).exists() else 0

    if sz >= 50_000:
        logger.info(f"  ✅ Ken Burns video: {out_path} ({sz // 1024}KB)")
        return out_path

    # If zoompan still fails, use simple scale + looped frames (ultrafast fallback)
    logger.warning(f"  zoompan failed ({sz}b): {r.stderr.decode()[-200:]} — trying simple loop")
    cmd2 = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-vf", (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "format=yuv420p"
        ),
        "-t", str(duration_secs),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-r", str(fps),
        "-an",
        out_path,
    ]
    r2 = subprocess.run(cmd2, capture_output=True, timeout=120)
    sz = Path(out_path).stat().st_size if Path(out_path).exists() else 0
    if sz < 50_000:
        raise RuntimeError(
            f"Ken Burns fallback failed completely.\n"
            f"zoompan stderr: {r.stderr.decode()[-300:]}\n"
            f"simple loop stderr: {r2.stderr.decode()[-300:]}"
        )
    logger.info(f"  ✅ Simple loop video: {out_path} ({sz // 1024}KB)")
    return out_path


async def _tts(text: str, path: str) -> None:
    import edge_tts
    await edge_tts.Communicate(text, "en-IN-NeerjaNeural", rate="+5%").save(path)


def _add_audio_and_overlay(video_path: str, content: dict, session: str) -> str:
    """Add voiceover quote + elegant text overlay to the model video."""
    quote      = content.get("quote", "")
    out_path   = str(MODEL_DIR / f"reel_{session}.mp4")
    tmp_path   = out_path + ".tmp.mp4"
    # Keep ASCII letters/digits/spaces only (FFmpeg drawtext cannot handle unicode/Devanagari)
    # Hinglish quotes often have no ASCII content - fall back to a safe default
    quote_safe = re.sub(r"[^A-Za-z0-9 '\-]", " ", quote).strip()[:50]
    quote_safe = re.sub(r" {2,}", " ", quote_safe)
    if len(quote_safe) < 3:
        quote_safe = "Stay real stay beautiful"

    voice_path = None
    if quote_safe:
        vp = str(MODEL_DIR / f"voice_{session}.mp3")
        try:
            def _run_tts():
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(_tts(quote_safe, vp))
                finally:
                    loop.close()
            _run_tts()
            if Path(vp).exists() and Path(vp).stat().st_size > 1000:
                voice_path = vp
        except Exception as e:
            logger.warning(f"  TTS failed: {e}")

    # Elegant overlay: thin accent bar + quote + watermark
    vf_base = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    vf_overlay = (
        # Gold accent line above text
        ",drawbox=x=iw*0.1:y=h*0.76:w=iw*0.8:h=3:color=0xffd700@0.9:t=fill"
        # Quote text
        f",drawtext=text='{quote_safe}'"
        f":fontfile={FONT}:fontsize=48:fontcolor=white"
        f":bordercolor=black:borderw=3"
        f":x=(w-text_w)/2:y=h*0.78"
        f":box=1:boxcolor=black@0.55:boxborderw=14"
        # AI Model watermark bottom right
        ",drawtext=text='AI MODEL'"
        f":fontfile={FONT}:fontsize=24:fontcolor=0xffd700"
        ":bordercolor=black:borderw=2"
        ":x=w-text_w-20:y=h-50"
        ":box=1:boxcolor=black@0.4:boxborderw=6"
    ) if quote_safe else (
        ",drawtext=text='AI MODEL'"
        f":fontfile={FONT}:fontsize=24:fontcolor=0xffd700"
        ":bordercolor=black:borderw=2"
        ":x=w-text_w-20:y=h-50"
        ":box=1:boxcolor=black@0.4:boxborderw=6"
    )

    # FIX: Don't use -t and -shortest together — they conflict when voice < video duration.
    # Instead: encode the full video length, audio pads/truncates naturally with -shortest only.
    # Also: vf_base scale must be applied BEFORE overlay drawtext — keep as single -vf chain.
    cmd = ["ffmpeg", "-y", "-i", video_path]
    if voice_path:
        cmd += ["-i", voice_path,
                "-map", "0:v", "-map", "1:a",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest"]   # stop when SHORTER stream ends (voice or video)
    else:
        cmd += ["-map", "0:v", "-an"]

    cmd += [
        "-vf", vf_base + vf_overlay,
        "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        tmp_path,
    ]

    r  = subprocess.run(cmd, capture_output=True, timeout=120)
    sz = Path(tmp_path).stat().st_size if Path(tmp_path).exists() else 0
    if sz >= 50_000:
        os.replace(tmp_path, out_path)
        return out_path

    logger.warning(f"  Overlay encode failed ({sz}b): {r.stderr.decode()[-300:]} — trying no-text fallback")

    # Fallback: no text overlay, no audio
    cmd2 = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", vf_base + ",format=yuv420p",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        out_path,
    ]
    r2 = subprocess.run(cmd2, capture_output=True, timeout=120)
    sz = Path(out_path).stat().st_size if Path(out_path).exists() else 0
    if sz < 50_000:
        raise RuntimeError(
            f"Model video final encode failed.\n"
            f"Overlay attempt: {r.stderr.decode()[-200:]}\n"
            f"Bare fallback: {r2.stderr.decode()[-200:]}"
        )
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
