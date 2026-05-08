import os, sys, time, logging, threading, signal
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
BASE_DIR=Path(__file__).parent.resolve(); sys.path.insert(0,str(BASE_DIR)); os.chdir(str(BASE_DIR)); os.environ["PYTHONPATH"]=str(BASE_DIR); load_dotenv()
logging.basicConfig(level=logging.INFO,format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",handlers=[logging.StreamHandler(sys.stdout)],force=True)
logger=logging.getLogger("DEPLOY")
for d in ["songs","videos","shorts","logs","brainrot","ai_model","sessions"]: (BASE_DIR/"output"/d).mkdir(parents=True,exist_ok=True)

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.send_header("Content-Type","text/plain"); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self,*a): pass

def main():
    signal.signal(signal.SIGTERM,lambda s,f:sys.exit(0)); signal.signal(signal.SIGINT,lambda s,f:sys.exit(0))
    logger.info("=== RAP + BRAINROT + AI MODEL — HUGGING FACE FREE TIER ===")
    def run(): import master; master.start_master_scheduler()
    threading.Thread(target=run,daemon=True,name="Scheduler").start()
    logger.info("=== ALL 3 CHANNELS RUNNING ===")
    port=int(os.environ.get("PORT",8080)); HTTPServer(("0.0.0.0",port),H).serve_forever()

if __name__=="__main__": main()
