"""
╔══════════════════════════════════════════════════════════╗
║           TELEGRAM NOTIFIER                              ║
║                                                          ║
║  Sends real-time notifications to your Telegram bot:     ║
║  ✅ Post uploaded successfully                           ║
║  ❌ Post failed (with error)                             ║
║  📊 Daily summary                                        ║
║  🔔 Token expiry alerts                                  ║
╚══════════════════════════════════════════════════════════╝

SETUP (takes 2 minutes):
  1. Open Telegram → search @BotFather → /newbot
  2. Copy the bot token (looks like 7123456789:AAF...)
  3. Message your new bot once (say "hi")
  4. Add to Railway vars:
       TELEGRAM_BOT_TOKEN=7123456789:AAF...
       TELEGRAM_CHAT_ID=   (leave blank first run — bot will print it)
"""

import os
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")

# Daily stats tracker (in-memory, resets on restart)
_daily_stats = {
    "date":    datetime.utcnow().strftime("%Y-%m-%d"),
    "success": 0,
    "failed":  0,
    "channels": {},
}


# ══════════════════════════════════════════════════════════
#  CORE SEND
# ══════════════════════════════════════════════════════════

def _send(text: str, parse_mode: str = "HTML") -> bool:
    """Send a message. Returns True on success, False on failure."""
    if not TELEGRAM_BOT_TOKEN:
        logger.debug("Telegram not configured — skipping notification")
        return False

    chat_id = TELEGRAM_CHAT_ID
    if not chat_id:
        chat_id = _auto_detect_chat_id()
        if not chat_id:
            logger.warning("⚠️  TELEGRAM_CHAT_ID not set. Message your bot once and add TELEGRAM_CHAT_ID to Railway vars.")
            return False

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id":    chat_id,
                "text":       text,
                "parse_mode": parse_mode,
            },
            timeout=10,
        )
        if not resp.ok:
            logger.warning(f"Telegram send failed: {resp.status_code} {resp.text[:200]}")
            return False
        return True
    except Exception as e:
        logger.warning(f"Telegram error: {e}")
        return False


def _auto_detect_chat_id() -> str:
    """Get the most recent chat ID from bot updates (for first-run setup)."""
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
            timeout=10,
        )
        updates = resp.json().get("result", [])
        if updates:
            chat_id = str(updates[-1]["message"]["chat"]["id"])
            logger.info(f"✅ Auto-detected Telegram chat ID: {chat_id}")
            logger.info(f"   Add this to Railway vars: TELEGRAM_CHAT_ID={chat_id}")
            return chat_id
    except Exception:
        pass
    return ""


# ══════════════════════════════════════════════════════════
#  NOTIFICATION TYPES
# ══════════════════════════════════════════════════════════

def notify_post_success(channel: str, title: str, reel_id: str, video_path: str = ""):
    """Called after every successful Instagram upload."""
    _update_stats(channel, success=True)
    msg = (
        f"✅ <b>Post Uploaded!</b>\n\n"
        f"📺 <b>Channel:</b> {channel}\n"
        f"🎵 <b>Title:</b> {title}\n"
        f"🆔 <b>Reel ID:</b> <code>{reel_id}</code>\n"
        f"🕐 <b>Time:</b> {datetime.utcnow().strftime('%H:%M UTC')}"
    )
    _send(msg)


def notify_post_failed(channel: str, title: str, error: str):
    """Called when a post fails."""
    _update_stats(channel, success=False)
    # Trim long errors
    short_error = str(error)[:300]
    msg = (
        f"❌ <b>Post Failed</b>\n\n"
        f"📺 <b>Channel:</b> {channel}\n"
        f"🎵 <b>Title:</b> {title}\n"
        f"💥 <b>Error:</b> <code>{short_error}</code>\n"
        f"🕐 <b>Time:</b> {datetime.utcnow().strftime('%H:%M UTC')}"
    )
    _send(msg)


def notify_pipeline_start(channel: str):
    """Called at the start of each pipeline run."""
    msg = (
        f"🚀 <b>Pipeline Starting</b>\n"
        f"📺 <b>Channel:</b> {channel}\n"
        f"🕐 {datetime.utcnow().strftime('%H:%M UTC')}"
    )
    _send(msg)


def notify_token_expiry_warning(channel: str, days_left: int):
    """Called when a token is about to expire."""
    msg = (
        f"⚠️ <b>Token Expiring Soon!</b>\n\n"
        f"📺 <b>Channel:</b> {channel}\n"
        f"📅 <b>Days left:</b> {days_left}\n\n"
        f"Go to developers.facebook.com → your app → API setup to refresh."
    )
    _send(msg)


def notify_daily_summary():
    """Send end-of-day summary. Call this at midnight or from master scheduler."""
    stats = _daily_stats
    total     = stats["success"] + stats["failed"]
    rate      = int(100 * stats["success"] / total) if total else 0

    channel_lines = ""
    for ch, data in stats.get("channels", {}).items():
        channel_lines += f"  • {ch}: ✅{data['success']} ❌{data['failed']}\n"

    msg = (
        f"📊 <b>Daily Summary — {stats['date']}</b>\n\n"
        f"✅ Uploaded: <b>{stats['success']}</b>\n"
        f"❌ Failed:   <b>{stats['failed']}</b>\n"
        f"📈 Success:  <b>{rate}%</b>\n\n"
        f"<b>By channel:</b>\n{channel_lines}"
    )
    _send(msg)

    # Reset stats for next day
    _daily_stats.update({
        "date":     datetime.utcnow().strftime("%Y-%m-%d"),
        "success":  0,
        "failed":   0,
        "channels": {},
    })


def notify_error(message: str):
    """Generic error alert for any critical failure."""
    msg = (
        f"🔴 <b>Critical Error</b>\n\n"
        f"<code>{message[:500]}</code>\n"
        f"🕐 {datetime.utcnow().strftime('%H:%M UTC')}"
    )
    _send(msg)


def notify_startup():
    """Called once when the master scheduler starts."""
    _send(
        f"🟢 <b>InstaAuto Bot Started</b>\n"
        f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"All 3 channels scheduled and running."
    )


# ══════════════════════════════════════════════════════════
#  STATS HELPER
# ══════════════════════════════════════════════════════════

def _update_stats(channel: str, success: bool):
    key = "success" if success else "failed"
    _daily_stats[key] += 1
    ch = _daily_stats["channels"].setdefault(channel, {"success": 0, "failed": 0})
    ch[key] += 1
