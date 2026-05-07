"""
INSTAGRAM UPLOADER — Official Meta Graph API Edition
=====================================================
Uses Meta's official Instagram Graph API.
No session hacking. No bans. No instagrapi.

How it works:
  1. Upload video to a temporary public URL (Instagram-compatible host)
  2. Create a media container via Graph API
  3. Wait for Instagram to process the video
  4. Publish the container

Tokens expire after 60 days — refresh them via refresh_all_tokens().
"""

import os
import time
import uuid
import logging
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.instagram.com/v21.0"

ACCOUNTS = {
    "RAP":      {"token_env": "RAP_IG_TOKEN",      "id_env": "RAP_IG_USER_ID"},
    "BRAINROT": {"token_env": "BRAINROT_IG_TOKEN",  "id_env": "BRAINROT_IG_USER_ID"},
    "MODEL":    {"token_env": "MODEL_IG_TOKEN",      "id_env": "MODEL_IG_USER_ID"},
}


def _get_credentials(account_label: str):
    cfg = ACCOUNTS.get(account_label.upper())
    if not cfg:
        raise ValueError(f"Unknown account: {account_label}. Use RAP, BRAINROT, or MODEL.")
    token   = os.getenv(cfg["token_env"], "")
    user_id = os.getenv(cfg["id_env"], "")
    if not token:
        raise ValueError(f"Missing env var: {cfg['token_env']}")
    if not user_id:
        raise ValueError(f"Missing env var: {cfg['id_env']}")
    return token, user_id


def _validate_mp4_locally(file_path: str) -> None:
    """
    Run ffprobe locally to confirm the file is a valid, readable MP4.
    Also checks that -movflags +faststart was used (moov/ftyp at file start).
    Raises RuntimeError on any problem so we fail fast instead of waiting
    90 s for Instagram to reject the video.
    """
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height",
            "-of", "default=noprint_wrappers=1",
            file_path,
        ],
        capture_output=True,
        timeout=30,
    )
    if probe.returncode != 0:
        stderr = probe.stderr.decode(errors="replace")[:400]
        raise RuntimeError(
            f"Local MP4 validation failed — file is corrupt or missing moov atom.\n"
            f"Ensure FFmpeg used -movflags +faststart.\nffprobe: {stderr}"
        )

    # Verify faststart layout: first box must be 'ftyp'
    with open(file_path, "rb") as f:
        header = f.read(16)
    first_box = header[4:8].decode("ascii", errors="replace")
    if first_box != "ftyp":
        raise RuntimeError(
            f"MP4 does not have faststart layout (first box is '{first_box}', expected 'ftyp').\n"
            f"Re-encode with -movflags +faststart."
        )


def _looks_like_mp4(url: str) -> bool:
    """
    Download the first 16 bytes from the URL and check for MP4 magic bytes.
    This catches the case where a host returns an HTML error page instead of
    the raw video file — which is exactly what filebin.net was doing and
    caused Instagram to report 'ftyp box not found'.
    """
    try:
        r = requests.get(
            url,
            headers={"Range": "bytes=0-15"},
            timeout=15,
            allow_redirects=True,
        )
        if r.status_code not in (200, 206):
            return False
        data = r.content
        if len(data) < 8:
            return False
        box_type = data[4:8]
        return box_type in (b"ftyp", b"moov")
    except Exception as e:
        logger.debug(f"MP4 check failed: {e}")
        return False


def _upload_to_public_url(file_path: str) -> str:
    """
    Host video at a public URL that Instagram's crawler can fetch.

    Requirements:
      - Serves raw bytes with Content-Type: video/mp4  (no JS redirects)
      - No bot-blocking
      - Stays available long enough for Instagram to fetch (~5 min)

    Every candidate URL is validated with _looks_like_mp4() before being
    returned — if a host returns HTML, we move on to the next host.
    """
    filename  = Path(file_path).name
    file_size = os.path.getsize(file_path)
    logger.info(f"Hosting video for Instagram: {filename} ({file_size // 1024 // 1024}MB)")

    # ── Host 1: transfer.sh ─────────────────────────────────────────────────
    # PUT upload, returns a direct raw-content URL.  Well known, no JS wall.
    try:
        with open(file_path, "rb") as f:
            resp = requests.put(
                f"https://transfer.sh/{filename}",
                data=f,
                headers={"Content-Type": "video/mp4", "Max-Days": "1"},
                timeout=180,
            )
        if resp.status_code == 200:
            url = resp.text.strip()
            if url.startswith("https://") and _looks_like_mp4(url):
                logger.info(f"✅ Hosted at transfer.sh: {url}")
                return url
            logger.warning(f"transfer.sh URL failed MP4 check: {url[:80]}")
        else:
            logger.warning(f"transfer.sh returned HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"transfer.sh failed: {e}")

    # ── Host 2: 0x0.st ──────────────────────────────────────────────────────
    # Long-running paste/file host.  multipart POST, returns plain URL.
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                "https://0x0.st",
                files={"file": (filename, f, "video/mp4")},
                timeout=180,
            )
        if resp.status_code == 200 and resp.text.strip().startswith("https://"):
            url = resp.text.strip()
            if _looks_like_mp4(url):
                logger.info(f"✅ Hosted at 0x0.st: {url}")
                return url
            logger.warning(f"0x0.st URL failed MP4 check: {url[:80]}")
        else:
            logger.warning(f"0x0.st returned HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"0x0.st failed: {e}")

    # ── Host 3: tmpfiles.org ─────────────────────────────────────────────────
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                "https://tmpfiles.org/api/v1/upload",
                files={"file": (filename, f, "video/mp4")},
                timeout=180,
            )
        if resp.status_code == 200:
            data = resp.json()
            raw_url = data.get("data", {}).get("url", "")
            # tmpfiles.org needs /dl/ for direct download (not the HTML viewer)
            url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
            if url and _looks_like_mp4(url):
                logger.info(f"✅ Hosted at tmpfiles: {url}")
                return url
            logger.warning(f"tmpfiles URL failed MP4 check: {url[:80]}")
        else:
            logger.warning(f"tmpfiles returned HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"tmpfiles failed: {e}")

    # ── Host 4: filebin.net ──────────────────────────────────────────────────
    # Last resort.  Validated carefully because it can return HTML pages.
    try:
        bin_id = str(uuid.uuid4())[:8]
        with open(file_path, "rb") as f:
            resp = requests.post(
                f"https://filebin.net/{bin_id}/{filename}",
                data=f,
                headers={"Content-Type": "video/mp4", "Accept": "application/json"},
                timeout=180,
            )
        if resp.status_code in (200, 201):
            url = f"https://filebin.net/{bin_id}/{filename}"
            if _looks_like_mp4(url):
                logger.info(f"✅ Hosted at filebin: {url}")
                return url
            logger.warning("filebin URL failed MP4 check (host returned HTML, not video)")
        else:
            logger.warning(f"filebin returned HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"filebin failed: {e}")

    raise RuntimeError(
        "All video hosts failed the MP4 content check.\n"
        "Hosts tried: transfer.sh, 0x0.st, tmpfiles.org, filebin.net\n"
        "Check Railway outbound network settings."
    )


def _wait_for_processing(creation_id: str, token: str, max_wait_sec: int = 300):
    logger.info(f"Waiting for Instagram processing (up to {max_wait_sec}s)...")
    for _ in range(max_wait_sec // 10):
        resp = requests.get(
            f"{GRAPH_BASE}/{creation_id}",
            params={"fields": "status_code,status,error_message", "access_token": token},
            timeout=30,
        )
        data      = resp.json()
        status    = data.get("status_code", "UNKNOWN")
        error_msg = data.get("error_message", "no details")
        logger.info(f"  Status: {status}")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            logger.error(f"Instagram rejection detail: {error_msg} | Full: {data}")
            raise RuntimeError(f"Instagram rejected the video: {error_msg}")
        time.sleep(10)
    raise TimeoutError("Video processing timed out after 5 minutes.")


def upload_reel(video_path: str, ig_metadata: dict) -> str:
    """
    Upload a video as an Instagram Reel via the official Graph API.
    ig_metadata: { account_label: "RAP"|"BRAINROT"|"MODEL", caption: "..." }
    """
    # ── Pre-flight checks ────────────────────────────────────────────────────
    file_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0
    if file_size < 50_000:
        raise RuntimeError(
            f"Video file is too small ({file_size} bytes) — likely corrupt or empty.\n"
            f"FFmpeg probably failed silently. Path: {video_path}"
        )

    # Validate MP4 structure locally before uploading
    _validate_mp4_locally(video_path)

    account_label  = ig_metadata.get("account_label", "RAP").upper()
    caption        = ig_metadata.get("caption", "")
    token, user_id = _get_credentials(account_label)

    logger.info(f"[{account_label}] Uploading Reel via official Instagram API...")

    # ── Upload to public URL ─────────────────────────────────────────────────
    video_url = _upload_to_public_url(video_path)

    # ── Create media container ───────────────────────────────────────────────
    logger.info(f"[{account_label}] Creating media container...")
    resp = requests.post(
        f"{GRAPH_BASE}/{user_id}/media",
        params={
            "media_type":    "REELS",
            "video_url":     video_url,
            "caption":       caption,
            "share_to_feed": "true",
            "access_token":  token,
        },
        timeout=60,
    )
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Container creation error: {data['error']['message']}")

    creation_id = data["id"]
    logger.info(f"[{account_label}] Container: {creation_id}")

    # ── Wait for processing ──────────────────────────────────────────────────
    _wait_for_processing(creation_id, token)

    # ── Publish ──────────────────────────────────────────────────────────────
    logger.info(f"[{account_label}] Publishing...")
    resp = requests.post(
        f"{GRAPH_BASE}/{user_id}/media_publish",
        params={"creation_id": creation_id, "access_token": token},
        timeout=30,
    )
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Publish error: {data['error']['message']}")

    media_id = data["id"]
    logger.info(f"[{account_label}] ✅ Reel live! ID: {media_id}")
    return media_id


# ── Analytics helpers ──────────────────────────────────────────────────────

def get_account_stats(account_label: str) -> dict:
    try:
        token, user_id = _get_credentials(account_label)
        resp = requests.get(
            f"{GRAPH_BASE}/{user_id}",
            params={"fields": "username,followers_count,media_count,account_type", "access_token": token},
            timeout=15,
        )
        data = resp.json()
        if "error" in data:
            return {"error": data["error"]["message"], "label": account_label}
        data["label"] = account_label
        return data
    except Exception as e:
        return {"error": str(e), "label": account_label}


def get_recent_media(account_label: str, limit: int = 6) -> list:
    try:
        token, user_id = _get_credentials(account_label)
        resp = requests.get(
            f"{GRAPH_BASE}/{user_id}/media",
            params={
                "fields": "id,caption,media_type,timestamp,like_count,comments_count,thumbnail_url",
                "limit":  limit,
                "access_token": token,
            },
            timeout=15,
        )
        return resp.json().get("data", [])
    except Exception:
        return []


def refresh_long_lived_token(account_label: str) -> str:
    token, _ = _get_credentials(account_label)
    resp = requests.get(
        "https://graph.instagram.com/refresh_access_token",
        params={"grant_type": "ig_refresh_token", "access_token": token},
        timeout=15,
    )
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Token refresh failed: {data['error']['message']}")
    new_token = data["access_token"]
    days_left = round(data.get("expires_in", 0) / 86400)
    logger.info(f"[{account_label}] Token refreshed — expires in {days_left} days")
    return new_token


def refresh_all_tokens():
    for label in ACCOUNTS:
        try:
            new_tok = refresh_long_lived_token(label)
            logger.info(f"[{label}] New token: {new_tok[:20]}...")
        except Exception as e:
            logger.error(f"[{label}] Token refresh failed: {e}")
