"""
RAP PIPELINE — Official Instagram API Edition
Generates rap song + vertical short video + posts to Instagram
"""
import os, sys, json, logging, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from config import SONGS_DIR, SHORTS_DIR, LOGS_DIR, MUSIC_MODE, SEO
from core.lyrics_generator import generate_song_concept, generate_suno_music_prompt
from core.music_generator import generate_song
from core.video_creator import create_short_video
from core.clip_extractor import get_clip_timestamps, trim_audio_clip
from uploaders.instagram_uploader import upload_reel
from core.telegram_notifier import notify_pipeline_start, notify_post_success, notify_post_failed, notify_error

def setup_logging():
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file = os.path.join(LOGS_DIR, f"rap_{datetime.now().strftime('%Y%m%d')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)]
    )

logger = logging.getLogger("RAP_PIPELINE")

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

    try:
        logger.info("[1/4] Generating song concept & lyrics...")
        concept = generate_song_concept()
        result["song_title"] = concept["title"]
        logger.info(f"    Title: '{concept['title']}'")

        logger.info(f"[2/4] Generating music ({MUSIC_MODE})...")
        suno_prompt = generate_suno_music_prompt(concept)
        audio_path  = generate_song(concept, suno_prompt)
        result["audio_path"] = audio_path

        logger.info("[3/4] Creating short videos...")
        try:
            from moviepy.editor import AudioFileClip
            audio_duration = AudioFileClip(audio_path).duration
        except Exception:
            audio_duration = 60

        clips    = get_clip_timestamps(concept, audio_duration)
        hashtags = " ".join(SEO["instagram_hashtags_base"])

        logger.info(f"[4/4] Uploading {len(clips)} reels...")
        for i, clip in enumerate(clips[:4]):
            try:
                clip_audio  = os.path.join(SONGS_DIR, f"{concept['title'].replace(' ','_')}_clip{i+1}.mp3")
                safe_start  = min(clip["start_sec"], max(0, audio_duration - 5))
                safe_end    = min(clip["end_sec"], audio_duration)
                trim_audio_clip(audio_path, safe_start, safe_end, clip_audio)
                short_path = create_short_video(clip_audio, concept, i, clip["start_sec"], clip["end_sec"] - clip["start_sec"])
                caption    = f"🎵 {concept['title']} — Part {i+1}\n\n{hashtags}"

                if not dry_run:
                    reel_id = upload_reel(short_path, {"caption": caption, "account_label": "RAP"})
                    result["reels"].append({"id": reel_id, "clip": clip.get("title", "")})
                    logger.info(f"  Reel {i+1} posted: {reel_id}")
                    notify_post_success("RAP", concept["title"], reel_id, short_path)
                else:
                    logger.info(f"  [DRY RUN] Skipping upload for clip {i+1}")
                    result["reels"].append({"id": f"DRY_{i}", "clip": clip.get("title", "")})
            except Exception as e:
                logger.error(f"  Clip {i+1} failed: {e}")
                result["errors"].append(f"Clip {i+1}: {str(e)}")
                notify_post_failed("RAP", concept.get("title", "Unknown"), str(e))

    except Exception as e:
        logger.error(f"PIPELINE FAILED: {e}", exc_info=True)
        result["errors"].append(str(e))

    result["completed_at"] = datetime.now().isoformat()
    log_path = os.path.join(LOGS_DIR, f"session_{session_id}.json")
    with open(log_path, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"DONE | '{result['song_title']}' | Reels: {len(result['reels'])}")
    return result

if __name__ == "__main__":
    setup_logging()
    run_full_pipeline(dry_run="--dry-run" in sys.argv)
