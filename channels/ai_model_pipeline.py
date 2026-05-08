import asyncio, json, logging, os, random, re, subprocess
import urllib.parse
from datetime import datetime
from pathlib import Path
import requests
from core.gemini_client import gemini
from core.video_ai import generate_video_from_image
from core.frame_builder import create_placeholder_model, create_model_overlay
from config import BASE_DIR, AI_MODEL_CHARACTER

logger = logging.getLogger("AI_MODEL")
MODEL_DIR = Path(BASE_DIR) / "output" / "ai_model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
LOCKED = AI_MODEL_CHARACTER["description"]
VIBES = AI_MODEL_CHARACTER["vibes"]

def generate_content_concept():
    td = random.choice(VIBES)
    prompt = f"""Create Instagram content for Indian AI lifestyle model. Theme: {td['theme']}, Vibe: {td['vibe']}
Return ONLY valid JSON: {{"quote":"motivational quote max 8 words","caption":"Instagram caption with emojis 150 chars","hashtags":["#aiinfluencer","#indianmodel","#lifestyle","#desi","#fashion","#viral","#fyp"],"video_motion_prompt":"subtle motion 8 words max"}}"""
    raw = re.sub(r"```json|```","",gemini(prompt)).strip()
    try: data = json.loads(raw)
    except: data = {"quote":"Stay real stay beautiful","caption":"Living my best life ✨🇮🇳","hashtags":["#aiinfluencer","#indianmodel","#desi","#viral"],"video_motion_prompt":"gentle hair movement soft golden light"}
    data["theme"] = td["theme"]; data["vibe"] = td["vibe"]; return data

def _pollinations_image(prompt, session):
    enc = urllib.parse.quote(prompt[:500]); seed = random.randint(1,9999)
    url = f"https://image.pollinations.ai/prompt/{enc}?width=1080&height=1350&nologo=true&seed={seed}"
    try:
        r = requests.get(url, timeout=120, stream=True)
        if r.status_code != 200: return None
        out = str(MODEL_DIR/f"model_{session}.jpg")
        with open(out,"wb") as f:
            for c in r.iter_content(65536): f.write(c)
        if Path(out).stat().st_size > 5000: return out
    except: pass
    return None

def generate_model_image(content, session):
    prompt = f"{LOCKED}, {content['vibe']}, fully clothed, high fashion, instagram aesthetic, natural lighting, ultra detailed"
    logger.info("🖼️  Generating model image...")
    r = _pollinations_image(prompt, session)
    if r: return r
    out = str(MODEL_DIR/f"model_{session}.jpg")
    return create_placeholder_model(content.get("theme","lifestyle"), content.get("quote",""), out)

def generate_model_video(image_path, content, session):
    logger.info("🎬 Generating model VIDEO (AI only)...")
    motion = content.get("video_motion_prompt","slow cinematic push in, soft light")
    video_prompt = f"cinematic slow motion, {motion}, gentle hair movement, soft breathing, camera slowly pushing in, {content['vibe']}, golden hour lighting"
    out = str(MODEL_DIR/f"raw_video_{session}.mp4")
    return generate_video_from_image(image_path, video_prompt, duration=5, aspect_ratio="9:16", output_path=out, loop_duration=8)

def _add_overlay_and_audio(video_path, content, session):
    quote = re.sub(r"[^A-Za-z0-9 '-]","",content.get("quote",""))[:50].strip()
    if len(quote)<3: quote = "Stay real stay beautiful"
    out = str(MODEL_DIR/f"reel_{session}.mp4"); tmp = out+".tmp.mp4"
    
    overlay_path = str(MODEL_DIR/f"overlay_{session}.png")
    create_model_overlay(quote, "AI MODEL", 1080, 1920, overlay_path)
    
    voice_path = None; vp = str(MODEL_DIR/f"voice_{session}.mp3")
    try:
        def _run_tts():
            import edge_tts; l = asyncio.new_event_loop()
            try: l.run_until_complete(edge_tts.Communicate(quote,"en-IN-NeerjaNeural",rate="+5%").save(vp))
            finally: l.close()
        _run_tts()
        if Path(vp).exists() and Path(vp).stat().st_size > 1000: voice_path = vp
    except: pass

    cmd = ["ffmpeg","-y","-i",video_path,"-i",overlay_path]
    if voice_path: cmd += ["-i",voice_path]
    vf = "[0:v][1:v]overlay=0:0:format=auto"
    if voice_path: cmd += ["-filter_complex",vf,"-map","0:v","-map","2:a","-c:a","aac","-b:a","128k","-shortest"]
    else: cmd += ["-filter_complex",vf,"-map","0:v","-an"]
    cmd += ["-c:v","libx264","-preset","fast","-pix_fmt","yuv420p","-movflags","+faststart",tmp]
    
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    sz = Path(tmp).stat().st_size if Path(tmp).exists() else 0
    if sz >= 50_000: os.replace(tmp, out); return out
    import shutil; shutil.copy2(video_path, out); return out

def run_ai_model_pipeline():
    sid = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"AI MODEL PIPELINE | {sid}")
    result = {"session_id":sid,"channel":"ai_model","started_at":datetime.now().isoformat(),"video_path":None,"caption":None,"hashtags":[],"errors":[]}
    try:
        content = generate_content_concept()
        result["title"] = content.get("theme","AI Model"); result["caption"] = content.get("caption",""); result["hashtags"] = content.get("hashtags",[])
        img = generate_model_image(content, sid)
        vid = generate_model_video(img, content, sid) # RAISES if HF fails
        result["video_path"] = _add_overlay_and_audio(vid, content, sid)
    except Exception as e:
        logger.error(f"❌ Model pipeline FAILED: {e}",exc_info=True); result["errors"].append(str(e))
    result["completed_at"] = datetime.now().isoformat(); return result
