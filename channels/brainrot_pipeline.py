import asyncio, os, re, json, random, logging, subprocess, requests
import urllib.parse
from pathlib import Path
from datetime import datetime
from core.gemini_client import gemini
from core.video_ai import generate_video_from_image
from core.frame_builder import create_brainrot_creature_frame, create_brainrot_bg

logger = logging.getLogger("BRAINROT")
BASE_DIR = Path(__file__).parent.parent; BRAIN_DIR = BASE_DIR / "output" / "brainrot"
BRAIN_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATES = [("sher","sarkari babu briefcase","Halku Sher Babu"),("bhains","chai ki ketli body","Tillu Bhains Chaiwala"),("bandar","jugaad scooter","Pappu Bandar Jugaadu"),("haathi","paneer tikka trunk","Motu Haathi Tikka"),("gadha","UPSC notes wings","Chintu Gadha UPSC"),("kutta","cricket bat legs","Bholu Kutta Cricketer"),("billi","bindi and saree","Chamki Billi Auntie"),("ghoda","desi ghee armor","Sardar Ghoda Ghee"),("bakri","auto-rickshaw shell","Guddi Bakri Auto"),("ullu","sarkari stamp beak","Lallu Ullu Sarkaar")]
POWERS = ["ek dum 1000 kilo chai pee sakta hai","sarkari file tez chalata hai","jugaad se rocket launch kar deta hai"]
WEAKNESSES = ["chai mein adrak na ho toh coma","IRCTC ticket confirm nahi toh power khatam"]
OPENERS = ["DEKHO BHAI","YE KYA HAI BHAI","SCIENTISTS NE KHOJA","HALKU AA GAYA"]

def generate_creature():
    t=random.choice(TEMPLATES); animal,obj,dname=t; power=random.choice(POWERS); weak=random.choice(WEAKNESSES); op=random.choice(OPENERS)
    prompt=f"""Create viral Indian Halku Brainrot character. Base: {animal} fused with {obj}.
Return ONLY valid JSON: {{"name":"Desi name 2-3 words","image_prompt":"Surreal {animal} fused with {obj}, meme creature, white bg, ultra detailed","narrator_script":"Hinglish 30-40 words: {op} [NAME]! Ye {animal} aur {obj} ka combo. Power: {power}. Weakness: {weak}. KOI NAHI BACH SAKTA!","hook_text":"ALL CAPS name max 25 chars","caption":"Instagram caption max 120 chars","hashtags":["#halkubrainrot","#desimemes","#indianbrainrot","#viral","#fyp"]}}"""
    raw=re.sub(r"```json|```","",gemini(prompt)).strip()
    try: data=json.loads(raw)
    except: data={"name":dname,"image_prompt":f"surreal {animal} fused with {obj}, meme creature","narrator_script":f"{op} {dname.upper()}! KOI NAHI BACH SAKTA!","hook_text":dname.upper()[:25],"caption":f"Bhai ye kya hai 💀 {dname} #halkubrainrot","hashtags":["#halkubrainrot","#desimemes","#viral","#fyp"]}
    data["animal"]=animal; return data

def _pollinations_image(prompt, session):
    enc=urllib.parse.quote(prompt[:500]); seed=random.randint(1,9999)
    url=f"https://image.pollinations.ai/prompt/{enc}?width=1080&height=1920&nologo=true&seed={seed}"
    try:
        r=requests.get(url,timeout=120,stream=True)
        if r.status_code!=200: return None
        out=str(BRAIN_DIR/f"creature_{session}.jpg")
        with open(out,"wb") as f:
            for c in r.iter_content(65536): f.write(c)
        if Path(out).stat().st_size>10000: return out
    except: pass
    return None

def generate_creature_image(content, session): return _pollinations_image(content.get("image_prompt",""), session)

def _voiceover(script, session):
    try:
        path=str(BRAIN_DIR/f"voice_{session}.mp3")
        def _run():
            import edge_tts; l=asyncio.new_event_loop()
            try: l.run_until_complete(edge_tts.Communicate(script,"en-IN-PrabhatNeural",rate="-8%",pitch="+5Hz").save(path))
            finally: l.close()
        _run()
        if Path(path).exists() and Path(path).stat().st_size>1000: return path
    except: pass
    return None

def _safe(t, m=28): return re.sub(r"[^A-Za-z0-9 ]","",t)[:m].upper()

def create_brainrot_video(content, creature_image, duration=30):
    session=datetime.now().strftime("%Y%m%d_%H%M%S"); out=str(BRAIN_DIR/f"brainrot_{session}.mp4")
    cname=_safe(content.get("hook_text",content.get("name","HALKU"))); animal=content.get("animal","sher")
    script=content.get("narrator_script","BHAI YE KYA HAI"); voice=_voiceover(script,session); has_voice=bool(voice and os.path.exists(voice))
    logger.info(f"🎬 Brainrot VIDEO (AI only): {cname}")
    
    if creature_image and os.path.exists(creature_image):
        video_prompt=f"surreal {animal} creature moving dramatically, rotating, dynamic animation, cinematic lighting"
        ai_video=generate_video_from_image(creature_image,video_prompt,duration=5,aspect_ratio="9:16",output_path=str(BRAIN_DIR/f"ai_{session}.mp4"),loop_duration=duration)
    else: raise RuntimeError("No creature image — cannot create AI video")
    
    if has_voice: return _merge_audio(ai_video,voice,out,duration)
    import shutil; shutil.copy2(ai_video,out); return out

def _merge_audio(video,audio,out,dur=30):
    tmp=out+".tmp.mp4"
    cmd=["ffmpeg","-y","-stream_loop","-1","-i",video,"-i",audio,"-map","0:v","-map","1:a","-c:v","libx264","-preset","fast","-c:a","aac","-b:a","128k","-pix_fmt","yuv420p","-movflags","+faststart","-t",str(dur),"-shortest",tmp]
    subprocess.run(cmd,capture_output=True,timeout=120)
    sz=Path(tmp).stat().st_size if Path(tmp).exists() else 0
    if sz>=50000: os.replace(tmp,out); return out
    import shutil; shutil.copy2(video,out); return out

def run_brainrot_pipeline():
    sid=datetime.now().strftime("%Y%m%d_%H%M%S"); logger.info(f"BRAINROT PIPELINE | {sid}")
    result={"session_id":sid,"channel":"brainrot","started_at":datetime.now().isoformat(),"video_path":None,"caption":None,"hashtags":[],"errors":[]}
    try:
        content=generate_creature()
        result["title"]=content.get("name","Halku"); result["topic"]=content.get("name","Halku"); result["caption"]=content.get("caption",""); result["hashtags"]=content.get("hashtags",[])
        img=generate_creature_image(content,sid)
        result["video_path"]=create_brainrot_video(content,img) # RAISES if HF fails
    except Exception as e:
        logger.error(f"❌ Brainrot pipeline FAILED: {e}",exc_info=True); result["errors"].append(str(e))
    result["completed_at"]=datetime.now().isoformat(); return result
