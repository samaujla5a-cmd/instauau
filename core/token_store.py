"""
TOKEN STORE — Thread-safe persistent token storage
===================================================
Tokens are written to .env (for Railway) and kept in a module-level
dict guarded by a threading.Lock so concurrent channel threads never
see a half-written token.

Usage:
    from core.token_store import get_token, set_token

    token = get_token("RAP_IG_TOKEN")
    set_token("RAP_IG_TOKEN", new_value)   # persists to .env + os.environ
"""

import os
import re
import threading
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_ENV_FILE = Path(__file__).parent.parent / ".env"


def get_token(env_key: str) -> str:
    """Return the current token value (always reads from os.environ)."""
    with _lock:
        return os.environ.get(env_key, "")


def set_token(env_key: str, value: str) -> None:
    """
    Persist a new token value.
    1. Updates os.environ immediately (all threads see it after lock releases).
    2. Rewrites the .env file so the value survives a Railway redeploy.
    """
    with _lock:
        os.environ[env_key] = value
        _write_env_file(env_key, value)
        logger.info(f"[token_store] {env_key} updated and persisted")


def _write_env_file(key: str, value: str) -> None:
    """Rewrite or append the key=value line in the .env file."""
    try:
        if _ENV_FILE.exists():
            text = _ENV_FILE.read_text()
            pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
            if pattern.search(text):
                new_text = pattern.sub(f"{key}={value}", text)
            else:
                new_text = text.rstrip("\n") + f"\n{key}={value}\n"
        else:
            new_text = f"{key}={value}\n"
        _ENV_FILE.write_text(new_text)
    except Exception as e:
        # Non-fatal — os.environ was already updated; log and continue
        logger.warning(f"[token_store] Could not write .env for {key}: {e}")
