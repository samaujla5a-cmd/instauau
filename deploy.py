"""
DEPLOY.PY — Railway entry point
HTTP server runs on the MAIN thread (required for Railway healthcheck).
Master Scheduler runs in a background daemon thread.
All logging goes to stdout so Railway Deploy Logs captures everything.
"""
import os, sys, time, logging, threading, signal
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))
os.chdir(str(BASE_DIR))
os.environ["PYTHONPATH"] = str(BASE_DIR)
load_dotenv()

# Force ALL logging to stdout — no files, so Railway captures everything
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,  # override any other handler set by imported modules
)
logger = logging.getLogger("DEPLOY")

# Create all output dirs
for d in ["songs", "videos", "shorts", "logs", "brainrot", "ai_model", "sessions"]:
    (BASE_DIR / "output" / d).mkdir(parents=True, exist_ok=True)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass  # suppress noisy access logs


def start_master_scheduler():
    def run():
        sys.path.insert(0, str(BASE_DIR))
        import master
        master.start_master_scheduler()
    t = threading.Thread(target=run, daemon=True, name="MasterScheduler")
    t.start()
    logger.info("Master Scheduler started (3 channels, 30 posts/day)")
    return t


def handle_shutdown(sig, frame):
    logger.info("Shutting down...")
    sys.exit(0)


def main():
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    logger.info("=== RAP + BRAINROT + AI MODEL — INSTAGRAM ONLY ===")

    # Start scheduler in background
    start_master_scheduler()
    logger.info("=== ALL 3 CHANNELS RUNNING — 30 posts/day ===")

    # Start HTTP server on MAIN thread — Railway healthcheck requires this
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health server listening on 0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
