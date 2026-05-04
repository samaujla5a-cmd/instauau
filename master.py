"""
MASTER SCHEDULER — Official API Edition
Runs all 3 channels on schedule: Rap, Brainrot, AI Model
30 posts/day total (10 per channel). Refreshes tokens monthly.
"""
import os, sys, time, logging, schedule, threading
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))
load_dotenv()

from config import RAP_TIMES, BRAINROT_TIMES, MODEL_TIMES
from uploaders.instagram_uploader import upload_reel, refresh_all_tokens
from channels.brainrot_pipeline import run_brainrot_pipeline
from channels.ai_model_pipeline import run_ai_model_pipeline
from main import run_full_pipeline as run_rap_pipeline

logger = logging.getLogger("MASTER")


def post_reel(result: dict, account_label: str):
    if not result.get("video_path"):
        logger.warning(f"[{account_label}] No video_path in result — skipping")
        return
    caption = f"{result.get('caption', '')}\n\n{' '.join(result.get('hashtags', []))}"
    try:
        media_id = upload_reel(result["video_path"], {
            "caption": caption,
            "account_label": account_label,
        })
        logger.info(f"[{account_label}] Posted! ID: {media_id}")
    except Exception as e:
        logger.error(f"[{account_label}] Upload failed: {e}", exc_info=True)


def run_rap_channel():
    logger.info("RAP CHANNEL starting...")
    try:
        run_rap_pipeline(dry_run=False)
    except Exception as e:
        logger.error(f"Rap error: {e}", exc_info=True)


def run_brainrot_channel():
    logger.info("BRAINROT CHANNEL starting...")
    try:
        result = run_brainrot_pipeline()
        post_reel(result, "BRAINROT")
    except Exception as e:
        logger.error(f"Brainrot error: {e}", exc_info=True)


def run_model_channel():
    logger.info("AI MODEL CHANNEL starting...")
    try:
        result = run_ai_model_pipeline()
        post_reel(result, "MODEL")
    except Exception as e:
        logger.error(f"Model error: {e}", exc_info=True)


def start_master_scheduler():
    all_jobs = (
        [(t, run_rap_channel)       for t in RAP_TIMES] +
        [(t, run_brainrot_channel)  for t in BRAINROT_TIMES] +
        [(t, run_model_channel)     for t in MODEL_TIMES]
    )

    # Refresh tokens on the 1st of every month at 03:00 UTC.
    # NOTE: `schedule` has no .month — we run daily at 03:00 and gate on day-of-month.
    def monthly_token_refresh():
        if datetime.utcnow().day == 1:
            threading.Thread(target=refresh_all_tokens, daemon=True).start()

    schedule.every().day.at("03:00").do(monthly_token_refresh)

    logger.info(f"MASTER SCHEDULER STARTED — {len(all_jobs)} daily jobs")
    for time_str, fn in all_jobs:
        schedule.every().day.at(time_str).do(
            lambda f=fn: threading.Thread(target=f, daemon=True).start()
        )

    # Log a heartbeat every 10 minutes so Railway logs stay active
    def heartbeat():
        next_jobs = schedule.next_run()
        logger.info(f"[HEARTBEAT] Running. Next job at: {next_jobs}")

    schedule.every(10).minutes.do(heartbeat)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    start_master_scheduler()
