import os, sys, time, logging, schedule, threading
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
BASE_DIR=Path(__file__).parent.resolve(); sys.path.insert(0,str(BASE_DIR)); load_dotenv()
from config import RAP_TIMES, BRAINROT_TIMES, MODEL_TIMES
from uploaders.instagram_uploader import refresh_all_tokens
from channels.brainrot_pipeline import run_brainrot_pipeline
from channels.ai_model_pipeline import run_ai_model_pipeline
from main import run_full_pipeline as run_rap_pipeline
from core.telegram_notifier import notify_startup, notify_pipeline_start, notify_post_success, notify_post_failed, notify_daily_summary, notify_error
logger = logging.getLogger("MASTER")

def post_reel(result, account_label):
    if not result.get("video_path"):
        errs=result.get("errors",[]); err=errs[0] if errs else "No video_path"
        notify_post_failed(account_label, result.get("title",result.get("topic","Unknown")), err); return
    caption=f"{result.get('caption','')}\n\n{' '.join(result.get('hashtags',[]))}"
    title=result.get("title",result.get("topic","Unknown"))
    try:
        from uploaders.instagram_uploader import upload_reel
        mid=upload_reel(result["video_path"],{"caption":caption,"account_label":account_label})
        notify_post_success(account_label,title,mid,result["video_path"])
    except Exception as e: notify_post_failed(account_label,title,str(e))

def run_rap_channel():
    try: run_rap_pipeline(dry_run=False)
    except Exception as e: notify_error(f"RAP crashed: {e}")

def run_brainrot_channel():
    notify_pipeline_start("BRAINROT")
    try: post_reel(run_brainrot_pipeline(), "BRAINROT")
    except Exception as e: notify_error(f"BRAINROT crashed: {e}")

def run_model_channel():
    notify_pipeline_start("MODEL")
    try: post_reel(run_ai_model_pipeline(), "MODEL")
    except Exception as e: notify_error(f"MODEL crashed: {e}")

def start_master_scheduler():
    all_jobs = ([(t,run_rap_channel) for t in RAP_TIMES] + [(t,run_brainrot_channel) for t in BRAINROT_TIMES] + [(t,run_model_channel) for t in MODEL_TIMES])
    def _monthly_refresh():
        if datetime.utcnow().day==1: threading.Thread(target=refresh_all_tokens,daemon=True).start()
    schedule.every().day.at("03:00").do(_monthly_refresh)
    schedule.every().day.at("23:55").do(notify_daily_summary)
    notify_startup()
    for t,fn in all_jobs: schedule.every().day.at(t).do(lambda f=fn: threading.Thread(target=f,daemon=True).start())
    def heartbeat(): logger.info(f"[HEARTBEAT] Next: {schedule.next_run()}")
    schedule.every(10).minutes.do(heartbeat)
    while True: schedule.run_pending(); time.sleep(30)
