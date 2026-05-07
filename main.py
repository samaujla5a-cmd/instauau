"""
RAP PIPELINE — Full Song + 4 Smart Reel Clips Per Run
======================================================
Flow per run:
  1. Generate song concept + full lyrics (Groq/Gemini — free)
  2. Generate real song via kie.ai Suno V4 (actual rap vocals + beat)
  3. Build full-length cinematic video
  4. Smart-trim into 4 hook clips
  5. Upload all 4 clips to Instagram RAP account
"""

import os
import sys
import json
import logging
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from config import SONGS_DIR, SHORTS_DIR, LOGS_DIR, SEO
from core.lyrics_generator import generate_song_concept, generate_suno_music_prompt
from core.music_generator import generate_song
from core.video_creator import create_reel_clips
from uploaders.instagram_uploader import upload_reel
from core.telegram_notifier import (
    notify_pipeline_start, notify_post_success, notify_post_failed
)


def setup_logging():
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file = os.path.join(LOGS_DIR, f"rap_{datetime.now().strftime('%Y%m%d')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )


logger = logging.getLogger("RAP_PIPELINE")


def _audio_duration(audio_path: str) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, timeout=15,
        )
        if r.returncode == 0:
            return float(r.stdout.decode().strip())
    except Exception as e:
        logger.warning(f"ffprobe duration failed: {e}")
    return 30.0


def run_full_pipeline(dry_run=False):
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"🎵 RAP PIPELINE START | {session_id}")
    notify_pipeline_start("RAP")

    result = {
        "session_id":  session_id,
        "started_at":  datetime.now().isoformat(),
        "song_title":  None,
        "reels":       [],
        "errors":      [],
    }

    hashtags = " ".join(SEO["instagram_hashtags_base"])

    try:
        # ── Step 1: Generate song concept + lyrics ────────────────────────
        logger.info("[1/4] Generating song concept & lyrics...")
        concept = generate_song_concept()
        result["song_title"] = concept["title"]
        logger.info(f"      Title: '{concept['title']}'")

        # ── Step 2: Generate real song audio via kie.ai Suno V4 ──────────
        logger.info("[2/4] Generating song audio via kie.ai Suno V4...")
        suno_prompt = generate_suno_music_prompt(concept)
        audio_path  = generate_song(concept, suno_prompt)
        duration    = _audio_duration(audio_path)
        logger.info(f"      Audio: {duration:.1f}s — {audio_path}")

        # ── Step 3: Create 4 hook reel clips ──────────────────────────────
        logger.info("[3/4] Smart-trimming into 4 reel clips...")
        reel_paths = create_reel_clips(audio_path, concept, n_clips=4)
        logger.info(f"      Created {len(reel_paths)} clips")

        # ── Step 4: Upload each clip ──────────────────────────────────────
        logger.info("[4/4] Uploading reels...")
        for i, reel_path in enumerate(reel_paths):
            caption = (
                f"🎵 {concept['title']} — Part {i+1}\n\n"
                f"{concept.get('instagram_caption', '')}\n\n"
                f"{hashtags}"
            )
            if not dry_run:
                try:
                    reel_id = upload_reel(reel_path, {"caption": caption, "account_label": "RAP"})
                    result["reels"].append({"id": reel_id, "title": concept["title"], "clip": i + 1})
                    logger.info(f"      ✅ Reel {i+1} posted: {reel_id}")
                    notify_post_success("RAP", f"{concept['title']} pt{i+1}", reel_id, reel_path)
                except Exception as e:
                    logger.error(f"      ❌ Reel {i+1} upload failed: {e}")
                    result["errors"].append(f"reel_{i+1}: {e}")
                    notify_post_failed("RAP", f"{concept['title']} pt{i+1}", str(e))
            else:
                logger.info(f"      [DRY RUN] Would upload: {reel_path}")
                result["reels"].append({"id": f"DRY_{i}", "title": concept["title"], "clip": i + 1})

    except Exception as e:
        logger.error(f"PIPELINE FAILED: {e}", exc_info=True)
        result["errors"].append(str(e))
        notify_post_failed("RAP", result.get("song_title") or "Unknown", str(e))

    result["completed_at"] = datetime.now().isoformat()
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(os.path.join(LOGS_DIR, f"session_{session_id}.json"), "w") as f:
        json.dump(result, f, indent=2)

    logger.info(
        f"DONE | '{result['song_title']}' | "
        f"Reels: {len(result['reels'])} | Errors: {len(result['errors'])}"
    )
    return result


if __name__ == "__main__":
    setup_logging()
    run_full_pipeline(dry_run="--dry-run" in sys.argv)
