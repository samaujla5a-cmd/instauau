"""
AI CLIENT — Groq Primary + Gemini Fallback
==========================================
Drop-in replacement for gemini_client.py

Priority order:
  1. Groq  (llama-3.3-70b — 14,400 req/day FREE, never rate-limits at your scale)
  2. Gemini PRIMARY key  (fallback if Groq down)
  3. Gemini BACKUP key   (last resort)

HOW TO SET UP GROQ (2 minutes):
  1. Go to console.groq.com → sign up free
  2. API Keys → Create API Key
  3. Copy key → add to Railway as: GROQ_API_KEY=gsk_...
  That's it. 14,400 free requests/day. Done.

Railway env vars needed:
  GROQ_API_KEY=gsk_...             ← primary (get from console.groq.com)
  GOOGLE_API_KEY=AIza...           ← fallback 1 (keep your existing key)
  GOOGLE_API_KEY_2=AIza...         ← fallback 2 (keep your existing key)
"""

import os
import json
import time
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("AI_CLIENT")

# ── Credentials ──────────────────────────────────────────────────────────────
GROQ_API_KEY     = os.getenv("GROQ_API_KEY", "")
GOOGLE_API_KEY   = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_API_KEY_2 = os.getenv("GOOGLE_API_KEY_2", "")

# ── Groq config ───────────────────────────────────────────────────────────────
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"   # best free model on Groq

# ── Gemini config ─────────────────────────────────────────────────────────────
GEMINI_URL   = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_MODEL = "gemini-2.0-flash"


# ════════════════════════════════════════════════════════════════════════════════
#  GROQ  (Primary)
# ════════════════════════════════════════════════════════════════════════════════

def _call_groq(prompt: str, max_tokens: int = 2000, system: str = "") -> str:
    """
    Call Groq API (OpenAI-compatible).
    Free tier: 14,400 requests/day, 6,000 tokens/min.
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set in env vars")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type":  "application/json",
        },
        json={
            "model":      GROQ_MODEL,
            "messages":   messages,
            "max_tokens": max_tokens,
            "temperature": 0.85,
        },
        timeout=60,
    )

    if resp.status_code == 429:
        raise RuntimeError(f"Groq rate limited (429): {resp.text[:200]}")
    if resp.status_code == 401:
        raise ValueError("Groq API key invalid — check GROQ_API_KEY in Railway")

    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


# ════════════════════════════════════════════════════════════════════════════════
#  GEMINI  (Fallback)
# ════════════════════════════════════════════════════════════════════════════════

def _call_gemini(prompt: str, max_tokens: int = 2000, api_key: str = "") -> str:
    """Call Gemini Flash API."""
    if not api_key:
        raise ValueError("No Gemini API key provided")

    resp = requests.post(
        f"{GEMINI_URL}?key={api_key}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature":     0.85,
            },
        },
        timeout=60,
    )

    if resp.status_code == 429:
        raise RuntimeError(f"Gemini rate limited (429)")
    if resp.status_code in (401, 403):
        raise ValueError(f"Gemini API key invalid (HTTP {resp.status_code})")

    resp.raise_for_status()
    data = resp.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected Gemini response format: {data}")


# ════════════════════════════════════════════════════════════════════════════════
#  MAIN PUBLIC FUNCTION  — drop-in replacement for old _gemini() / gemini()
# ════════════════════════════════════════════════════════════════════════════════

def gemini(prompt: str, max_tokens: int = 2000, system: str = "") -> str:
    """
    Generate text using AI. Tries providers in order:
      1. Groq (primary  — fast, 14,400 req/day free)
      2. Gemini PRIMARY key (fallback)
      3. Gemini BACKUP key  (last resort)

    Raises Exception only if ALL providers fail.
    """
    providers = []

    # ── 1. Groq ──
    if GROQ_API_KEY:
        providers.append(("Groq/llama-3.3-70b", lambda: _call_groq(prompt, max_tokens, system)))
    else:
        logger.warning("GROQ_API_KEY not set — Groq skipped. Add it at console.groq.com for best results.")

    # ── 2. Gemini primary ──
    if GOOGLE_API_KEY:
        providers.append(("Gemini/primary", lambda: _call_gemini(prompt, max_tokens, GOOGLE_API_KEY)))

    # ── 3. Gemini backup ──
    if GOOGLE_API_KEY_2:
        providers.append(("Gemini/backup", lambda: _call_gemini(prompt, max_tokens, GOOGLE_API_KEY_2)))

    if not providers:
        raise Exception(
            "No AI API keys configured! Add at least one of:\n"
            "  GROQ_API_KEY (get free at console.groq.com)\n"
            "  GOOGLE_API_KEY (Google AI Studio)"
        )

    last_error = None
    for name, call_fn in providers:
        try:
            logger.info(f"[AI] Calling {name}...")
            result = call_fn()
            logger.info(f"[AI] ✅ {name} succeeded")
            return result
        except RuntimeError as e:
            # Rate limit or temporary error — try next provider
            logger.warning(f"[AI] ⚠️ {name} failed (rate limit/temp): {e}")
            last_error = e
            time.sleep(2)
        except ValueError as e:
            # Config error (bad key etc) — log and skip
            logger.error(f"[AI] ✗ {name} config error: {e}")
            last_error = e
        except Exception as e:
            logger.warning(f"[AI] ⚠️ {name} unexpected error: {e}")
            last_error = e
            time.sleep(2)

    raise Exception(
        f"All AI providers failed. Last error: {last_error}\n"
        f"Check GROQ_API_KEY, GOOGLE_API_KEY, GOOGLE_API_KEY_2 in Railway vars."
    )


# ── Alias so existing code that imports _gemini() still works ─────────────────
_gemini = gemini


# ════════════════════════════════════════════════════════════════════════════════
#  JSON HELPER  — used by pipelines that expect structured JSON output
# ════════════════════════════════════════════════════════════════════════════════

def gemini_json(prompt: str, max_tokens: int = 2000) -> dict:
    """
    Call AI and parse response as JSON.
    Strips markdown fences automatically.
    """
    import re
    raw = gemini(prompt, max_tokens)
    # Strip ```json ... ``` fences
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI returned invalid JSON: {e}\nRaw response:\n{raw[:500]}")


# ── Alias ─────────────────────────────────────────────────────────────────────
_gemini_json = gemini_json


if __name__ == "__main__":
    # Quick test — run: python ai_client.py
    logging.basicConfig(level=logging.INFO)
    print("\nTesting AI client...\n")
    result = gemini("Say hello and tell me which AI model you are. Keep it to 2 sentences.")
    print(f"Response: {result}\n")
    print("✅ AI client working!")
