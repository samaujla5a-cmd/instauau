import os, logging, threading, requests
from datetime import datetime
logger = logging.getLogger(__name__)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN",""); CHAT  = os.getenv("TELEGRAM_CHAT_ID","")
_lock = threading.Lock(); _stats = {"date":datetime.utcnow().strftime("%Y-%m-%d"),"success":0,"failed":0,"channels":{}}

def _send(text):
    if not TOKEN: return False
    cid = CHAT
    if not cid:
        try:
            r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", timeout=10)
            ups = r.json().get("result",[])
            if ups: cid = str(ups[-1]["message"]["chat"]["id"])
        except: pass
    if not cid: return False
    try: return requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":cid,"text":text,"parse_mode":"HTML"}, timeout=10).ok
    except: return False

def _update(ch, ok):
    k = "success" if ok else "failed"
    with _lock: _stats[k] += 1; _stats["channels"].setdefault(ch,{"success":0,"failed":0})[k] += 1

def notify_post_success(ch,title,rid,path=""): _update(ch,True); _send(f"✅ <b>Posted!</b>\n📺 {ch}\n🎵 {title}\n🆔 <code>{rid}</code>")
def notify_post_failed(ch,title,err): _update(ch,False); _send(f"❌ <b>Failed</b>\n📺 {ch}\n🎵 {title}\n💥 <code>{str(err)[:300]}</code>")
def notify_pipeline_start(ch): _send(f"🚀 <b>Pipeline</b> {ch}")
def notify_error(msg): _send(f"🔴 <b>Error</b>\n<code>{str(msg)[:500]}</code>")
def notify_startup(): _send(f"🟢 <b>Bot Started</b> — 3 channels")
def notify_daily_summary():
    with _lock: s = dict(_stats)
    total = s["success"]+s["failed"]; rate = int(100*s["success"]/total) if total else 0
    lines = "".join(f"  • {k}: ✅{v['success']} ❌{v['failed']}\n" for k,v in s["channels"].items())
    _send(f"📊 <b>Daily — {s['date']}</b>\n✅ {s['success']} ❌ {s['failed']} 📈 {rate}%\n{lines}")
    with _lock: _stats.update({"date":datetime.utcnow().strftime("%Y-%m-%d"),"success":0,"failed":0,"channels":{}})
