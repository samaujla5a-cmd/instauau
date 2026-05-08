import os, re, threading, logging
from pathlib import Path
logger = logging.getLogger(__name__)
_lock = threading.Lock(); _ENV = Path(__file__).parent.parent / ".env"

def get_token(key):
    with _lock: return os.environ.get(key,"")

def set_token(key, val):
    with _lock:
        os.environ[key] = val
        try:
            if _ENV.exists():
                t = _ENV.read_text(); pat = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
                t = pat.sub(f"{key}={val}",t) if pat.search(t) else t.rstrip("\n")+f"\n{key}={val}\n"
            else: t = f"{key}={val}\n"
            _ENV.write_text(t)
        except Exception as e: logger.warning(f"Token write failed: {e}")
