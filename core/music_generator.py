"""
MUSIC GENERATOR — kie.ai Suno V4 API
=====================================
Generates real rap songs with actual vocals + beat via kie.ai.
NO TTS. Real AI-generated music.

Setup: Add KIE_API_KEY to Railway env vars.
Get free key (5000 credits, no card): https://kie.ai
"""

import os
import time
import logging
import requests
from pathlib import Path
from config import SONGS_DIR

logger = logging.getLogger(__name__)
os.makedirs(SONGS_DIR, exist_ok=True)

KIE_API_KEY      = os.getenv("KIE_API_KEY", "")
KIE_GENERATE_URL = "https://api.kie.ai/api/v1/generate"
KIE_TASK_URL     = "https://api.kie.ai/api/v1/generate/record-info"
MAX_WAIT_SECS    = 360
POLL_INTERVAL    = 10


def _headers():
    if not KIE_API_KEY:
        raise ValueError(
            "KIE_API_KEY not set!\n"
            "1. Go to https://kie.ai → sign up free (5000 credits, no card)\n"
            "2. Dashboard → API Keys → copy key\n"
            "3. Add KIE_API_KEY=your_key to Railway env vars"
        )
    return {"Authorization": f"Bearer {KIE_API_KEY}", "Content-Type": "application/json"}


def _poll(task_id: str) -> dict:
    """Poll kie.ai until SUCCESS or ERROR. Returns sunoData dict."""
    waited = 0
    while waited < MAX_WAIT_SECS:
        time.sleep(POLL_INTERVAL)
        waited += POLL_INTERVAL
        try:
            resp = requests.get(KIE_TASK_URL, params={"taskId": task_id},
                                headers=_headers(), timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"  Poll request failed (retry): {e}")
            continue

        data   = resp.json()
        d      = data.get("data") or {}
        status = d.get("status", "PENDING")
        logger.info(f"  Suno [{task_id}]: {status} ({waited}s)")

        if status == "SUCCESS":
            response  = d.get("response") or {}
            suno_list = response.get("sunoData") or []
            if suno_list and isinstance(suno_list, list):
                return suno_list[0]
            audio_url = response.get("audioUrl") or d.get("audioUrl") or ""
            if audio_url:
                return response
            raise RuntimeError(f"SUCCESS but no sunoData/audioUrl in response: {data}")

        if status in ("ERROR", "FAILED", "TIMEOUT"):
            raise RuntimeError(f"Suno generation failed: {d.get('error', data)}")

    raise TimeoutError(f"Suno task timed out after {MAX_WAIT_SECS}s")


def _download(url: str, title: str) -> str:
    safe  = "".join(c for c in title if c.isalnum() or c in " _-")[:40]
    path  = str(Path(SONGS_DIR) / f"{safe}.mp3")
    r     = requests.get(url, timeout=180, stream=True)
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(65536):
            f.write(chunk)
    size_kb = Path(path).stat().st_size // 1024
    logger.info(f"  ✅ Audio saved: {path} ({size_kb}KB)")
    if size_kb < 10:
        raise RuntimeError(f"Downloaded audio is too small ({size_kb}KB) — likely corrupt")
    return path


def generate_song(concept: dict, suno_prompt: str = "") -> str:
    """
    Generate full rap song via kie.ai Suno V4.
    Mutates concept to add lyric_timestamps + cover_image_url.
    Returns local MP3 path.
    """
    logger.info(f"🎵 Generating: '{concept.get('title')}' via kie.ai Suno V4...")

    lyrics     = concept.get("full_lyrics", concept.get("hook", ""))
    style_tags = concept.get("suno_prompt", "desi hip hop, trap beat, aggressive male rapper, hindi english mix")[:120]

    payload = {
        "prompt":       lyrics[:2000],
        "style":        style_tags,
        "title":        concept.get("title", "Untitled")[:80],
        "customMode":   True,
        "instrumental": False,
        "model":        "V4",
        "vocalGender":  "m",
        "callBackUrl":  "https://example.com/callback",
        "fetchLyrics":  True,
    }

    resp = requests.post(KIE_GENERATE_URL, headers=_headers(), json=payload, timeout=60)

    if resp.status_code == 401:
        raise ValueError("KIE_API_KEY invalid — check https://kie.ai/dashboard")
    if resp.status_code == 402:
        raise RuntimeError("kie.ai credits exhausted — top up at https://kie.ai/pricing")
    if resp.status_code == 422:
        resp_json = resp.json()
        msg = str(resp_json.get("msg", "")).lower()
        if "callback" in msg:
            logger.warning("  kie.ai rejected callBackUrl, retrying with alternate format...")
            payload["callBackUrl"] = "https://hooks.example.com/kie"
        else:
            logger.warning(f"  kie.ai 422: {resp_json.get('msg')} — retrying without fetchLyrics...")
            payload.pop("fetchLyrics", None)
        resp = requests.post(KIE_GENERATE_URL, headers=_headers(), json=payload, timeout=60)

    # Final fallback: bare minimum payload only
    if resp.status_code == 422:
        logger.warning("  Still 422 — retrying with bare minimum payload...")
        payload = {
            "prompt":       payload["prompt"],
            "style":        payload["style"],
            "title":        payload["title"],
            "customMode":   True,
            "instrumental": False,
            "model":        "V4",
            "callBackUrl":  "https://example.com/callback",
        }
        resp = requests.post(KIE_GENERATE_URL, headers=_headers(), json=payload, timeout=60)

    resp.raise_for_status()

    resp_data = resp.json()
    task_id   = (resp_data.get("data") or {}).get("taskId", "")
    if not task_id:
        raise RuntimeError(f"No taskId in kie.ai response: {resp_data}")
    logger.info(f"  Task submitted: {task_id}")

    suno_data = _poll(task_id)

    lyrics_ts = suno_data.get("lyrics") or suno_data.get("lyricTimestamps") or []
    if lyrics_ts and isinstance(lyrics_ts, list):
        concept["lyric_timestamps"] = lyrics_ts
        logger.info(f"  Got {len(lyrics_ts)} lyric timestamps")
    else:
        logger.info("  No lyric timestamps returned — video will use static lyrics")
        concept.setdefault("lyric_timestamps", [])

    audio_url = (
        suno_data.get("audioUrl")
        or suno_data.get("audio_url")
        or suno_data.get("url")
        or ""
    )
    if not audio_url:
        raise RuntimeError(f"No audioUrl in Suno response: {suno_data}")

    concept["cover_image_url"] = suno_data.get("imageUrl", "")
    return _download(audio_url, concept.get("title", "song"))
