import os, time, json, logging, requests
from pathlib import Path
from config import SONGS_DIR
logger = logging.getLogger(__name__)
os.makedirs(SONGS_DIR, exist_ok=True)
KIE_API_KEY = os.getenv("KIE_API_KEY","")
KIE_GEN_URL = "https://api.kie.ai/api/v1/generate"
KIE_TASK_URL = "https://api.kie.ai/api/v1/generate/record-info"

def _headers():
    if not KIE_API_KEY: raise ValueError("KIE_API_KEY not set")
    return {"Authorization": f"Bearer {KIE_API_KEY}", "Content-Type": "application/json"}

def _poll(task_id):
    waited = 0
    while waited < 360:
        time.sleep(10); waited += 10
        try:
            r = requests.get(KIE_TASK_URL, params={"taskId":task_id}, headers=_headers(), timeout=30); r.raise_for_status()
        except: continue
        data = r.json().get("data") or {}; st = data.get("state") or data.get("status","PENDING")
        if st in ("SUCCESS","success"):
            resp = data.get("response") or {}; sl = resp.get("sunoData") or []
            if sl and isinstance(sl,list): return sl[0]
            au = resp.get("audioUrl") or data.get("audioUrl") or ""
            if au: return resp
            raise RuntimeError(f"SUCCESS but no audioUrl")
        if st in ("ERROR","FAILED","TIMEOUT","error","failed"): raise RuntimeError(f"Suno failed ({st})")
    raise TimeoutError("Suno timed out")

def _download(url, title):
    safe = "".join(c for c in title if c.isalnum() or c in " _-")[:40]; path = str(Path(SONGS_DIR)/f"{safe}.mp3")
    r = requests.get(url, timeout=180, stream=True); r.raise_for_status()
    with open(path,"wb") as f:
        for c in r.iter_content(65536): f.write(c)
    sz = Path(path).stat().st_size // 1024
    if sz < 10: raise RuntimeError(f"Audio too small ({sz}KB)")
    logger.info(f"  ✅ Audio: {path} ({sz}KB)"); return path

def generate_song(concept, suno_prompt=""):
    logger.info(f"🎵 Generating: '{concept.get('title')}' via Suno V4...")
    lyrics = concept.get("full_lyrics",concept.get("hook","")); style = concept.get("suno_prompt","desi hip hop")[:120]
    payload = {"prompt":lyrics[:2000],"style":style,"title":concept.get("title","Untitled")[:80],"customMode":True,"instrumental":False,"model":"V4","vocalGender":"m","callBackUrl":"https://example.com/callback"}
    resp = requests.post(KIE_GEN_URL, headers=_headers(), json=payload, timeout=60)
    if resp.status_code == 422:
        payload.pop("fetchLyrics",None); resp = requests.post(KIE_GEN_URL, headers=_headers(), json=payload, timeout=60)
    resp.raise_for_status()
    tid = (resp.json().get("data") or {}).get("taskId","")
    if not tid: raise RuntimeError(f"No taskId")
    suno = _poll(tid)
    concept.pop("lyric_timestamps",None); concept.pop("cover_image_url",None)
    lts = suno.get("lyrics") or suno.get("lyricTimestamps") or []
    concept["lyric_timestamps"] = lts if isinstance(lts,list) else []
    au = suno.get("audioUrl") or suno.get("audio_url") or suno.get("url") or ""
    if not au: raise RuntimeError(f"No audioUrl")
    concept["cover_image_url"] = suno.get("imageUrl","")
    return _download(au, concept.get("title","song"))
