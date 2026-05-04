"""
╔══════════════════════════════════════════════════════════╗
║         MUSIC GENERATOR — FREE API Edition              ║
║                                                          ║
║  Mode A: Suno AI (Browser-Token auth — current method)  ║
║  Mode B: MusicGen local (Meta open-source, 100% free)   ║
║  Mode C: edge-tts voice + royalty-free beat (free)      ║
╚══════════════════════════════════════════════════════════╝
"""

import requests
import time
import os
import asyncio
import logging
import subprocess
from pathlib import Path
from config import SUNO_COOKIE, SONGS_DIR, MUSIC_MODE, TTS_MODE, EDGE_TTS_VOICE, EDGE_TTS_RATE, EDGE_TTS_PITCH

logger = logging.getLogger(__name__)
os.makedirs(SONGS_DIR, exist_ok=True)

# ── Read Suno Browser-Token from env ─────────────────────
# In .env set either:
#   SUNO_BROWSER_TOKEN=eyJ0aW1lc3RhbXAiOjE3...   (newer method)
#   SUNO_COOKIE=_session=xxx...                    (older method)
SUNO_BROWSER_TOKEN = os.getenv("SUNO_BROWSER_TOKEN", SUNO_COOKIE)


# ══════════════════════════════════════════════════════════
#  MAIN ENTRY — auto-routes based on MUSIC_MODE in .env
# ══════════════════════════════════════════════════════════

def generate_song(concept: dict, suno_prompt: str) -> str:
    """
    Generate full song. Routes to correct backend based on MUSIC_MODE:
      suno_cookie    → Suno AI (Browser-Token auth, current)
      musicgen_local → Meta's MusicGen running locally (100% free)
      gtts_only      → gTTS / edge-tts voice only
    Returns path to final .mp3
    """
    if MUSIC_MODE in ("suno_cookie", "suno"):
        return generate_song_suno(concept, suno_prompt)
    elif MUSIC_MODE == "musicgen_local":
        return generate_song_musicgen(concept, suno_prompt)
    else:
        return generate_voice_only(concept)


# ══════════════════════════════════════════════════════════
#  MODE A: SUNO AI — Browser-Token method (current/working)
# ══════════════════════════════════════════════════════════

def _build_suno_headers() -> dict:
    """
    Build correct Suno request headers.
    Suno now uses Browser-Token + Authorization instead of cookies.

    How to get your Browser-Token:
    1. Go to suno.com, log in (free account)
    2. Press F12 → Network tab → click any request to studio-api-prod.suno.com
    3. Look in Request Headers for:
         Browser-Token: eyJ0aW1lc3RhbXAiOi...
       OR
         Authorization: Bearer eyJhbGci...
    4. Copy the Browser-Token value into SUNO_BROWSER_TOKEN in your .env
    """
    token = SUNO_BROWSER_TOKEN.strip()

    # If it looks like a raw JWT/browser token (starts with eyJ)
    # wrap it in the JSON format Suno expects
    if token.startswith("eyJ") and not token.startswith('{"'):
        browser_token_header = f'{{"token":"{token}"}}'
    else:
        browser_token_header = token

    return {
        "Host":            "studio-api-prod.suno.com",
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0",
        "Accept":          "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer":         "https://suno.com/",
        "Origin":          "https://suno.com",
        "Browser-Token":   browser_token_header,
        "Content-Type":    "application/json",
        "Connection":      "keep-alive",
        "Sec-Fetch-Dest":  "empty",
        "Sec-Fetch-Mode":  "cors",
        "Sec-Fetch-Site":  "same-site",
    }

# Keep old name for backward compatibility
SUNO_HEADERS = {
    "Cookie": SUNO_COOKIE,
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://suno.ai/",
    "Origin": "https://suno.ai",
}


def generate_song_suno(concept: dict, prompt: str) -> str:
    """
    Generate song via Suno AI using Browser-Token (current auth method).
    Free account: ~10 songs/day. No credit card needed.

    How to get your Browser-Token:
    1. Go to suno.com, log in (free account is fine)
    2. Press F12 → Network tab → Enable "Raw" toggle on headers
    3. Click Create on Suno, let it start generating
    4. Click any request to studio-api-prod.suno.com
    5. In Request Headers, find:
         Browser-Token: eyJ0aW1lc3RhbXAiOi...
    6. Copy that value → paste into SUNO_BROWSER_TOKEN in your .env
    """
    if not SUNO_BROWSER_TOKEN:
        logger.warning("SUNO_BROWSER_TOKEN not set — falling back to TTS-only mode")
        return generate_voice_only(concept)

    logger.info("🎵 Generating with Suno AI (Browser-Token mode)...")

    headers = _build_suno_headers()

    # Refresh session first
    _suno_refresh_session(headers)

    payload = {
        "prompt":            concept["full_lyrics"],
        "tags":              prompt,
        "title":             concept["title"],
        "make_instrumental": False,
        "wait_audio":        False,
    }

    resp = requests.post(
        "https://studio-api-prod.suno.com/api/generate/v2/",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if resp.status_code == 401:
        raise RuntimeError(
            "❌ Suno token expired or invalid!\n"
            "Fix: F12 → Network → any request to studio-api-prod.suno.com\n"
            "     → Request Headers → copy Browser-Token value\n"
            "     → paste into SUNO_BROWSER_TOKEN in your .env"
        )
    if resp.status_code == 403:
        raise RuntimeError(
            "❌ Suno returned 403 Forbidden.\n"
            "Make sure you are logged into suno.com in your browser\n"
            "and re-copy the Browser-Token from a fresh request."
        )
    resp.raise_for_status()

    data     = resp.json()
    clip_ids = [item["id"] for item in data.get("clips", [])]
    if not clip_ids:
        raise ValueError(f"Suno returned no clip IDs. Response: {data}")

    logger.info(f"🕐 Waiting for Suno to render clip {clip_ids[0]}...")
    audio_url = _poll_suno(clip_ids[0], headers)

    out_path = os.path.join(SONGS_DIR, f"{_safe_name(concept['title'])}.mp3")
    _download_file(audio_url, out_path)
    logger.info(f"✅ Suno song downloaded: {out_path}")
    return out_path


def _suno_refresh_session(headers: dict):
    """Keep Suno session alive."""
    try:
        requests.get(
            "https://studio-api-prod.suno.com/api/session/",
            headers=headers,
            timeout=10
        )
    except Exception:
        pass  # Non-critical


def _poll_suno(clip_id: str, headers: dict, max_wait: int = 300) -> str:
    start = time.time()
    while time.time() - start < max_wait:
        resp = requests.get(
            f"https://studio-api-prod.suno.com/api/feed/?ids={clip_id}",
            headers=headers,
        )
        resp.raise_for_status()
        for clip in resp.json():
            if clip.get("status") == "complete" and clip.get("audio_url"):
                return clip["audio_url"]
            elif clip.get("status") == "error":
                raise RuntimeError(f"Suno generation failed: {clip}")
        logger.info("  ⏳ Still rendering...")
        time.sleep(10)
    raise TimeoutError("Suno timed out after 5 minutes")


# ══════════════════════════════════════════════════════════
#  MODE B: META MUSICGEN (Local — 100% Free, No Limits)
# ══════════════════════════════════════════════════════════

def generate_song_musicgen(concept: dict, prompt: str) -> str:
    """
    Generate music locally using Meta's MusicGen.
    100% free, unlimited, runs on CPU or GPU.

    Install: pip install audiocraft
    Model downloads automatically (~3-7GB first run).

    CPU: ~5-15 min per song. GPU (4GB VRAM): ~1-3 min.
    """
    try:
        from audiocraft.models import MusicGen
        from audiocraft.data.audio import audio_write
    except ImportError:
        raise ImportError(
            "audiocraft not installed.\n"
            "Run: pip install audiocraft\n"
            "Or switch MUSIC_MODE=suno_cookie in .env"
        )

    logger.info("🎵 Generating music with MusicGen (local, free)...")

    # Use small model for speed; "medium" or "large" for better quality
    model = MusicGen.get_pretrained("facebook/musicgen-small")
    model.set_generation_params(duration=180)  # 3 min song

    # Build a rich music prompt from the concept
    music_prompt = (
        f"trippy lo-fi hip-hop rap beat, {concept.get('suno_prompt', '')[:200]}, "
        f"psychedelic, weed vibe, 80 BPM, dark atmospheric, bass heavy, "
        f"808 drums, vinyl crackle, chill trap production"
    )

    # Generate (returns torch tensor)
    wav = model.generate([music_prompt])

    out_path = os.path.join(SONGS_DIR, _safe_name(concept["title"]))
    audio_write(
        out_path, wav[0].cpu(),
        model.sample_rate,
        strategy="loudness",
        loudness_compressor=True,
    )
    final_path = out_path + ".wav"
    # Convert to mp3 for compatibility
    mp3_path = out_path + ".mp3"
    _ffmpeg_convert(final_path, mp3_path)

    logger.info(f"✅ MusicGen song created: {mp3_path}")
    return mp3_path


# ══════════════════════════════════════════════════════════
#  MODE C: FREE TTS VOICE GENERATION
# ══════════════════════════════════════════════════════════

def generate_voice_only(concept: dict) -> str:
    """
    Generate voice-only track using free TTS.
    Routes to edge-tts (best quality) or gTTS (fallback).
    """
    lyrics = concept.get("full_lyrics", "")
    out_path = os.path.join(SONGS_DIR, f"{_safe_name(concept['title'])}.mp3")

    if TTS_MODE == "edge_tts":
        return _edge_tts(lyrics, out_path)
    else:
        return _gtts(lyrics, out_path)


def _edge_tts(text: str, out_path: str) -> str:
    """
    Microsoft Edge TTS — FREE, high quality neural voices.
    Install: pip install edge-tts
    Voices: en-US-GuyNeural, en-US-DavisNeural, en-US-TonyNeural
    """
    try:
        import edge_tts

        async def _generate():
            communicate = edge_tts.Communicate(
                text,
                EDGE_TTS_VOICE,
                rate=EDGE_TTS_RATE,
                pitch=EDGE_TTS_PITCH,
            )
            await communicate.save(out_path)

        asyncio.run(_generate())
        logger.info(f"✅ edge-tts voice generated: {out_path}")
        return out_path

    except ImportError:
        logger.warning("edge-tts not installed, falling back to gTTS. Run: pip install edge-tts")
        return _gtts(text, out_path)


def _gtts(text: str, out_path: str) -> str:
    """
    Google Translate TTS — FREE, simple, slightly robotic.
    Install: pip install gtts
    """
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(out_path)
        logger.info(f"✅ gTTS voice generated: {out_path}")
        return out_path
    except ImportError:
        raise ImportError("No TTS available. Run: pip install edge-tts gtts")


# ══════════════════════════════════════════════════════════
#  BEAT MIXER — Mix voice over royalty-free beat
# ══════════════════════════════════════════════════════════

def mix_voice_and_beat(voice_path: str, beat_path: str, out_path: str,
                       voice_vol: float = 1.0, beat_vol: float = 0.5) -> str:
    """
    Mix voice track with a beat using pydub.
    Provide your own royalty-free beat .mp3 as beat_path.

    Free beat sources:
    - looperman.com (free loops)
    - freemusicarchive.org
    - pixabay.com/music (free commercial license)
    - YouTube Audio Library
    """
    from pydub import AudioSegment

    logger.info("🎚️ Mixing voice + beat...")
    voice = AudioSegment.from_file(voice_path)
    beat  = AudioSegment.from_file(beat_path)

    # Loop beat to match voice duration
    if len(beat) < len(voice):
        repeats = (len(voice) // len(beat)) + 2
        beat = beat * repeats
    beat = beat[:len(voice)]

    # dB adjustments
    voice_adj = voice + (20 * voice_vol - 20)
    beat_adj  = beat  + (20 * beat_vol  - 20)

    mixed = voice_adj.overlay(beat_adj)
    mixed.export(out_path, format="mp3", bitrate="320k")
    logger.info(f"✅ Mix complete: {out_path}")
    return out_path


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════

def _download_file(url: str, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)


def _safe_name(title: str) -> str:
    return title.replace(" ", "_").replace("/", "_")[:50]


def _ffmpeg_convert(src: str, dst: str) -> None:
    """Convert audio via ffmpeg (must be installed)."""
    subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-b:a", "320k", dst],
        check=True, capture_output=True
    )


# Keep backward compatibility with original main.py
generate_song_suno        = generate_song_suno
generate_voice_elevenlabs = generate_voice_only   # redirect to free TTS
