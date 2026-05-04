"""
INSTAGRAM UPLOADER — Official Meta Graph API Edition
=====================================================
Uses Meta's official Instagram Graph API.
No session hacking. No bans. No instagrapi.

How it works:
  1. Upload video to a temporary public URL (catbox.moe — Railway-compatible)
  2. Create a media container via Graph API
  3. Wait for Instagram to process the video
  4. Publish the container

Tokens expire after 60 days — refresh them via refresh_all_tokens().
"""

import os
import time
import logging
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


def _upload_to_public_url(file_path: str) -> str:
    """Host local video at a temporary public URL so Instagram can fetch it."""
    filename = Path(file_path).name
    logger.info(f"Hosting video for Instagram: {filename}")

    # Primary: catbox.moe — works on Railway, no size issues for reels
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (filename, f, "video/mp4")},
                timeout=180,
            )
        if resp.status_code == 200 and resp.text.startswith("https://"):
            url = resp.text.strip()
            logger.info(f"Hosted at: {url}")
            return url
        logger.warning(f"catbox.moe returned unexpected: {resp.text[:100]}")
    except Exception as e:
        logger.warning(f"catbox.moe failed ({e}), trying fallback...")

    # Fallback: litterbox.catbox.moe (72h expiry, same network, Railway-compatible)
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "72h"},
                files={"fileToUpload": (filename, f, "video/mp4")},
                timeout=180,
            )
        if resp.status_code == 200 and resp.text.startswith("https://"):
            url = resp.text.strip()
            logger.info(f"Hosted at fallback: {url}")
            return url
        logger.warning(f"litterbox returned: {resp.text[:100]}")
    except Exception as e:
        logger.warning(f"litterbox failed ({e}), trying last resort...")

    # Last resort: uguu.se (anonymous, Railway-compatible)
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                "https://uguu.se/upload",
                files={"files[]": (filename, f, "video/mp4")},
                timeout=180,
            )
        if resp.status_code == 200:
            data = resp.json()
            url = data.get("files", [{}])[0].get("url", "")
            if url:
                logger.info(f"Hosted at last resort: {url}")
                return url
    except Exception as e:
        logger.warning(f"uguu.se failed: {e}")

    raise RuntimeError("All video hosts failed — check Railway network settings")


def _wait_for_processing(creation_id: str, token: str, max_wait_sec: int = 300):
    logger.info(f"Waiting for Instagram processing (up to {max_wait_sec}s)...")
    for _ in range(max_wait_sec // 10):
        resp = requests.get(
            f"{GRAPH_BASE}/{creation_id}",
            params={"fields": "status_code,status,error_message", "access_token": token}, timeout=30,
        )
        data = resp.json()
        status = data.get("status_code", "UNKNOWN")
        error_msg = data.get("error_message", "no details")
        logger.info(f"  Status: {status}")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            logger.error(f"Instagram rejection detail: {error_msg} | Full response: {data}")
            raise RuntimeError(f"Instagram rejected the video: {error_msg}")
        time.sleep(10)
    raise TimeoutError("Video processing timed out after 5 minutes.")


def upload_reel(video_path: str, ig_metadata: dict) -> str:
    """
    Upload a video as an Instagram Reel via the official Graph API.
    ig_metadata: { account_label: "RAP"|"BRAINROT"|"MODEL", caption: "..." }
    """
    account_label = ig_metadata.get("account_label", "RAP").upper()
    caption       = ig_metadata.get("caption", "")
    token, user_id = _get_credentials(account_label)

    logger.info(f"[{account_label}] Uploading Reel via official Instagram API...")

    video_url = _upload_to_public_url(video_path)

    logger.info(f"[{account_label}] Creating media container...")
    resp = requests.post(
        f"{GRAPH_BASE}/{user_id}/media",
        params={
            "media_type": "REELS", "video_url": video_url,
            "caption": caption, "share_to_feed": "true", "access_token": token,
        }, timeout=60,
    )
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Container error: {data['error']['message']}")

    creation_id = data["id"]
    logger.info(f"[{account_label}] Container: {creation_id}")

    _wait_for_processing(creation_id, token)

    logger.info(f"[{account_label}] Publishing...")
    resp = requests.post(
        f"{GRAPH_BASE}/{user_id}/media_publish",
        params={"creation_id": creation_id, "access_token": token}, timeout=30,
    )
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Publish error: {data['error']['message']}")

    media_id = data["id"]
    logger.info(f"[{account_label}] Reel live! ID: {media_id}")
    return media_id


# ── Analytics helpers (used by dashboard) ─────────────────────────────────

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
                "limit": limit, "access_token": token,
            }, timeout=15,
        )
        return resp.json().get("data", [])
    except Exception:
        return []


def refresh_long_lived_token(account_label: str) -> str:
    """Refresh a long-lived token (valid 60 days). Call monthly."""
    token, _ = _get_credentials(account_label)
    resp = requests.get(
        "https://graph.instagram.com/refresh_access_token",
        params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=15,
    )
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Token refresh failed: {data['error']['message']}")
    new_token = data["access_token"]
    days_left = round(data.get("expires_in", 0) / 86400)
    logger.info(f"[{account_label}] Token refreshed — expires in {days_left} days")
    return new_token


def refresh_all_tokens():
    """Refresh tokens for all 3 accounts. Schedule monthly."""
    for label in ACCOUNTS:
        try:
            new_tok = refresh_long_lived_token(label)
            logger.info(f"[{label}] New token (first 20 chars): {new_tok[:20]}...")
        except Exception as e:
            logger.error(f"[{label}] Token refresh failed: {e}")
