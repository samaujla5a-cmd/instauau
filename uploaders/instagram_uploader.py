import os, time, logging, requests
from pathlib import Path
from config import RAP_IG_TOKEN, RAP_IG_USER_ID, BRAINROT_IG_TOKEN, BRAINROT_IG_USER_ID, MODEL_IG_TOKEN, MODEL_IG_USER_ID
logger = logging.getLogger(__name__)
ACCOUNTS = {"RAP":{"token":RAP_IG_TOKEN,"uid":RAP_IG_USER_ID},"BRAINROT":{"token":BRAINROT_IG_TOKEN,"uid":BRAINROT_IG_USER_ID},"MODEL":{"token":MODEL_IG_TOKEN,"uid":MODEL_IG_USER_ID}}
IG_BASE = "https://graph.facebook.com/v19.0"

def _get_account(label):
    acc=ACCOUNTS.get(label,{}); token=acc.get("token",""); uid=acc.get("uid","")
    if not token or not uid: raise ValueError(f"Missing token/uid for {label}")
    return token, uid

def _host_catbox(path):
    try:
        with open(path,"rb") as f: r=requests.post("https://catbox.moe/user/api.php",files={"fileToUpload":f},data={"reqtype":"fileupload"},timeout=120)
        if r.status_code==200 and r.text.startswith("https://"): return r.text.strip()
    except: pass
    return None

def _host_tmpfiles(path):
    try:
        fname=Path(path).name
        with open(path,"rb") as f: r=requests.post("https://tmpfiles.org/api/v1/upload",files={"file":(fname,f)},timeout=120)
        if r.status_code==200:
            url=r.json().get("data",{}).get("url","")
            if url: return url.replace("tmpfiles.org/","tmpfiles.org/dl/")
    except: pass
    return None

def _host_video(path):
    for name,fn in [("catbox",_host_catbox),("tmpfiles",_host_tmpfiles)]:
        url=fn(path)
        if url: return url
    raise RuntimeError("All hosting services failed")

def upload_reel(video_path, opts=None):
    opts=opts or {}; label=opts.get("account_label","RAP"); caption=opts.get("caption",""); token,uid=_get_account(label)
    logger.info(f"[{label}] Uploading Reel..."); video_url=_host_video(video_path)
    r=requests.post(f"{IG_BASE}/{uid}/media",params={"media_type":"REELS","video_url":video_url,"caption":caption,"share_to_feed":"true","access_token":token}); r.raise_for_status()
    container=r.json()["id"]; logger.info(f"[{label}] Container: {container}")
    for _ in range(60):
        time.sleep(10); r=requests.get(f"{IG_BASE}/{container}",params={"fields":"status_code,status","access_token":token}); st=r.json().get("status_code","")
        if st=="FINISHED": break
        if st in ("ERROR","FAILED"): raise RuntimeError(f"IG failed: {r.json()}")
    else: raise TimeoutError("IG processing timed out")
    r=requests.post(f"{IG_BASE}/{uid}/media_publish",params={"creation_id":container,"access_token":token}); r.raise_for_status()
    mid=r.json()["id"]; logger.info(f"[{label}] ✅ Reel live! ID: {mid}"); return mid

def refresh_all_tokens():
    for label,acc in ACCOUNTS.items():
        token=acc.get("token","")
        if not token: continue
        try:
            r=requests.get(f"{IG_BASE}/refresh_access_token",params={"grant_type":"ig_refresh_token","access_token":token})
            if r.ok:
                new=r.json().get("access_token",token)
                if new!=token:
                    from core.token_store import set_token; set_token(f"{label}_IG_TOKEN",new)
        except: pass
