import os, sys, json, logging
from datetime import datetime
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv; load_dotenv()
from config import SONGS_DIR, SHORTS_DIR, VIDEOS_DIR, LOGS_DIR, SEO
from core.lyrics_generator import generate_song_concept, generate_suno_music_prompt
from core.music_generator import generate_song
from core.video_creator import create_full_video, trim_reel_clips
from uploaders.instagram_uploader import upload_reel
from core.telegram_notifier import notify_pipeline_start, notify_post_success, notify_post_failed

STATE_FILE = Path(LOGS_DIR) / "rap_state.json"; os.makedirs(LOGS_DIR, exist_ok=True)
logger = logging.getLogger("RAP_PIPELINE")

def _load_state():
    try:
        if STATE_FILE.exists(): return json.loads(STATE_FILE.read_text())
    except: pass
    return None

def _save_state(state): STATE_FILE.write_text(json.dumps(state, indent=2))

def _upload_clip(clip_path, concept, clip_index, dry_run=False):
    hashtags = " ".join(SEO["instagram_hashtags_base"])
    caption = f"🎵 {concept['title']} — Part {clip_index+1}\n\n{concept.get('instagram_caption','')}\n\n{hashtags}"
    if not dry_run:
        try:
            rid = upload_reel(clip_path, {"caption": caption, "account_label": "RAP"})
            notify_post_success("RAP", f"{concept['title']} pt{clip_index+1}", rid, clip_path); return rid
        except Exception as e:
            notify_post_failed("RAP", f"{concept['title']} pt{clip_index+1}", str(e)); return None
    return f"DRY_{clip_index}"

def _generate_new_batch(dry_run=False):
    session = datetime.now().strftime("%Y%m%d_%H%M%S"); notify_pipeline_start("RAP")
    concept = generate_song_concept()
    audio_path = generate_song(concept, generate_suno_music_prompt(concept))
    full_video = create_full_video(audio_path, concept)
    clip_paths = trim_reel_clips(full_video, audio_path, concept, n=4)
    _upload_clip(clip_paths[0], concept, 0, dry_run)
    pending = [{"path": p, "clip_index": i} for i, p in enumerate(clip_paths[1:], start=1)]
    _save_state({"pending_clips": pending, "concept": {"title": concept.get("title",""), "instagram_caption": concept.get("instagram_caption","")}, "generated_at": datetime.now().isoformat()})

def run_full_pipeline(dry_run=False):
    logger.info("RAP CHANNEL starting...")
    state = _load_state()
    if state and state.get("pending_clips"):
        clip = state["pending_clips"].pop(0); _save_state(state); concept = state.get("concept",{})
        if os.path.exists(clip["path"]): _upload_clip(clip["path"], concept, clip["clip_index"], dry_run)
        else: _generate_new_batch(dry_run)
    else: _generate_new_batch(dry_run)
