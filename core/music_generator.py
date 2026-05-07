"""
╔══════════════════════════════════════════════════════════╗
║         MUSIC GENERATOR — FREE API Edition              ║
║                                                          ║
║  Mode A: TTS.ai (Kokoro — natural voice, free API)      ║
║  Mode B: edge-tts voice (fallback)                      ║
║  Mode C: gTTS (last resort)                             ║
╚══════════════════════════════════════════════════════════╝
"""

import requests
import time
import os
import asyncio
import logging
import subprocess
from pathlib import Path
from config import SONGS_DIR, MUSIC_MODE, TTS_MODE, EDGE_TTS_VOICE, EDGE_TTS_RATE, EDGE_TTS_PITCH

logger = logging.getLogger(__name__)
os.makedirs(SONGS_DIR, exist_ok=True)

TTSAI_API_KEY = os.getenv("TTSAI_API_KEY", "")


# ══════════════════════════════════════════════════════════
#  MAIN ENTRY
# ══════════════════════════════════════════════════════════

def generate_song(concept: dict, suno_prompt: str = "") -> str:
    """
    Route based on MUSIC_MODE env var:
      tts_ai              → TTS.ai Kokoro (natural voice, recommended free option)
      gtts_only / edge_tts → edge-tts / gTTS fallback
    """
    # TTS.ai — primary free option
    if TTSAI_API_KEY or MUSIC_MODE == "tts_ai":
        try:
            return generate_ttsai(concept)
        except Exception as e:
            logger.warning(f"TTS.ai failed ({e}), falling back to edge-tts...")

    return generate_voice_only(concept)


# ══════════════════════════════════════════════════════════
#  MODE A: TTS.AI — Kokoro (Natural voice, free API)
# ══════════════════════════════════════════════════════════

def generate_ttsai(concept: dict) -> str:
    """
    Generate natural-sounding voice using TTS.ai Kokoro model.
    Get free API key at: https://tts.ai
    Add to Railway vars: TTSAI_API_KEY=sk-tts-your-key
    """
    lyrics = concept.get("full_lyrics", concept.get("hook", ""))
    lyrics = lyrics[:3000]

    out_path = os.path.join(SONGS_DIR, f"{_safe_name(concept['title'])}.mp3")

    logger.info("🎙️ Generating voice with TTS.ai (Kokoro)...")

    headers = {"Content-Type": "application/json"}
    if TTSAI_API_KEY:
        headers["Authorization"] = f"Bearer {TTSAI_API_KEY}"

    payload = {
        "model":  "kokoro",
        "text":   lyrics,
        "voice":  "am_adam",
        "format": "mp3",
    }

    resp = requests.post(
        "https://api.tts.ai/v1/tts/",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if resp.status_code == 429:
        raise RuntimeError("TTS.ai rate limit hit — try again later or upgrade")
    if resp.status_code == 401:
        raise RuntimeError("TTS.ai invalid API key — check TTSAI_API_KEY")
    resp.raise_for_status()

    data = resp.json()
    uuid = data.get("uuid")
    if not uuid:
        raise RuntimeError(f"TTS.ai gave no UUID: {data}")

    logger.info(f"  🕐 TTS.ai job {uuid} — polling for result...")

    for attempt in range(60):
        time.sleep(2)
        result = requests.get(
            "https://api.tts.ai/v1/speech/results/",
            params={"uuid": uuid},
            headers=headers,
            timeout=15,
        ).json()

        status = result.get("status")
        if status == "completed":
            result_url = result.get("result_url")
            if not result_url:
                raise RuntimeError("TTS.ai completed but no result_url")
            audio_resp = requests.get(result_url, timeout=60)
            audio_resp.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(audio_resp.content)
            logger.info(f"✅ TTS.ai voice generated: {out_path}")
            return out_path
        elif status == "failed":
            raise RuntimeError(f"TTS.ai generation failed: {result.get('error')}")
        else:
            logger.info(f"  ⏳ TTS.ai status: {status} (attempt {attempt+1})")

    raise TimeoutError("TTS.ai timed out after 2 minutes")


# ══════════════════════════════════════════════════════════
#  MODE B: EDGE-TTS FALLBACK
# ══════════════════════════════════════════════════════════

def generate_voice_only(concept: dict) -> str:
    lyrics   = concept.get("full_lyrics", "")
    out_path = os.path.join(SONGS_DIR, f"{_safe_name(concept['title'])}.mp3")
    return _edge_tts(lyrics, out_path)


def _edge_tts(text: str, out_path: str) -> str:
    try:
        import edge_tts

        async def _generate():
            communicate = edge_tts.Communicate(
                text, EDGE_TTS_VOICE, rate=EDGE_TTS_RATE, pitch=EDGE_TTS_PITCH,
            )
            await communicate.save(out_path)

        asyncio.run(_generate())
        logger.info(f"✅ edge-tts voice generated: {out_path}")
        return out_path
    except ImportError:
        return _gtts(text, out_path)


def _gtts(text: str, out_path: str) -> str:
    from gtts import gTTS
    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(out_path)
    logger.info(f"✅ gTTS voice generated: {out_path}")
    return out_path


# ══════════════════════════════════════════════════════════
#  BEAT MIXER
# ══════════════════════════════════════════════════════════

def mix_voice_and_beat(voice_path: str, beat_path: str, out_path: str,
                       voice_vol: float = 1.0, beat_vol: float = 0.5) -> str:
    from pydub import AudioSegment
    logger.info("🎚️ Mixing voice + beat...")
    voice = AudioSegment.from_file(voice_path)
    beat  = AudioSegment.from_file(beat_path)
    if len(beat) < len(voice):
        repeats = (len(voice) // len(beat)) + 2
        beat = beat * repeats
    beat      = beat[:len(voice)]
    voice_adj = voice + (20 * voice_vol - 20)
    beat_adj  = beat  + (20 * beat_vol  - 20)
    mixed     = voice_adj.overlay(beat_adj)
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
    subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-b:a", "320k", dst],
        check=True, capture_output=True
    )


# backward compat
generate_voice_elevenlabs = generate_voice_only
generate_song_musicgen    = generate_voice_only
