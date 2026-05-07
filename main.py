"""
RAP PIPELINE — 1 Song Per Run, 10x Per Day = 10 RAP Reels/Day
"""
import os, sys, json, logging, subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from config import SONGS_DIR, SHORTS_DIR, LOGS_DIR, MUSIC_MODE, SEO
from core.lyrics_generator import generate_song_concept, generate_suno_music_prompt
from core.music_generator import generate_song
from core.video_creator import create_short_video
from uploaders.instagram_uploader import upload_reel
from core.telegram_notifier import notify_pipeline_start, notify_post_success, notify_post_failed

def setup_logging():
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file = os.path.join(LOGS_DIR, f"rap_{datetime.now().strftime('%Y%m%d')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)]
    )

logger = logging.getLogger("RAP_PIPELINE")


def _get_audio_duration(audio_path: str) -> float:
    """
    Get audio duration using ffprobe (available everywhere ffmpeg is installed).
    Falls back to 30.0 s if ffprobe fails.
    Avoids importing moviepy which is very heavy and slow to load.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            capture_output=True,
            timeout=15,
        )
        if result.returncode == 0:
            return float(result.stdout.decode().strip())
    except Exception as e:
        logger.warning(f"ffprobe duration check failed: {e}")

    # Fallback: pydub (already in requirements)
    try:
        from pydub import AudioSegment
        return len(AudioSegment.from_file(audio_path)) / 1000.0
    except Exception as e:
        logger.warning(f"pydub duration check failed: {e}")

    return 30.0


def run_full_pipeline(dry_run=False):
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"🎵 RAP PIPELINE START | {session_id}")
    notify_pipeline_start("RAP")

    result = {
        "session_id": session_id,
        "started_at": datetime.now().isoformat(),
        "song_title": None,
        "reels": [],
        "errors": [],
    }

    hashtags = " ".join(SEO["instagram_hashtags_base"])

    try:
        logger.info("[1/3] Generating song concept & lyrics...")
        concept = generate_song_concept()
        result["song_title"] = concept["title"]
        logger.info(f"    Title: '{concept['title']}'")

        logger.info(f"[2/3] Generating audio ({MUSIC_MODE})...")
        suno_prompt = generate_suno_music_prompt(concept)
        audio_path  = generate_song(concept, suno_prompt)

        duration      = _get_audio_duration(audio_path)
        safe_duration = max(5.0, duration - 0.15)
        logger.info(f"    Audio: {duration:.1f}s")

        logger.info("[3/3] Creating video & uploading...")
        short_path = create_short_video(audio_path, concept, 0, 0, safe_duration)
        caption    = f"🎵 {concept['title']}\n\n{hashtags}"

        if not dry_run:
            reel_id = upload_reel(short_path, {"caption": caption, "account_label": "RAP"})
            result["reels"].append({"id": reel_id, "title": concept["title"]})
            logger.info(f"✅ Reel posted: {reel_id}")
            notify_post_success("RAP", concept["title"], reel_id, short_path)
        else:
            logger.info("[DRY RUN] Skipping upload")
            result["reels"].append({"id": "DRY_0", "title": concept["title"]})

    except Exception as e:
        logger.error(f"PIPELINE FAILED: {e}", exc_info=True)
        result["errors"].append(str(e))
        notify_post_failed("RAP", result.get("song_title") or "Unknown", str(e))

    result["completed_at"] = datetime.now().isoformat()
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(os.path.join(LOGS_DIR, f"session_{session_id}.json"), "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"DONE | '{result['song_title']}' | Reels: {len(result['reels'])}")
    return result


if __name__ == "__main__":
    setup_logging()
    run_full_pipeline(dry_run="--dry-run" in sys.argv)
