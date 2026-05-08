import os, time, logging, requests
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger("AI_CLIENT")

GROQ_API_KEY     = os.getenv("GROQ_API_KEY", "")
GOOGLE_API_KEY   = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_API_KEY_2 = os.getenv("GOOGLE_API_KEY_2", "")
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

def _call_groq(prompt, max_tokens=2000, system=""):
    if not GROQ_API_KEY: raise ValueError("GROQ_API_KEY not set")
    messages = []
    if system: messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": GROQ_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.85}, timeout=60)
    if resp.status_code == 429: raise RuntimeError("Groq rate limited")
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()

def _call_gemini(prompt, max_tokens=2000, api_key=""):
    if not api_key: raise ValueError("No Gemini key")
    resp = requests.post(f"{GEMINI_URL}?key={api_key}", headers={"Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.85}}, timeout=60)
    if resp.status_code == 429: raise RuntimeError("Gemini rate limited")
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

def gemini(prompt, max_tokens=2000, system=""):
    providers = []
    if GROQ_API_KEY: providers.append(("Groq", lambda: _call_groq(prompt, max_tokens, system)))
    if GOOGLE_API_KEY: providers.append(("Gemini1", lambda: _call_gemini(prompt, max_tokens, GOOGLE_API_KEY)))
    if GOOGLE_API_KEY_2: providers.append(("Gemini2", lambda: _call_gemini(prompt, max_tokens, GOOGLE_API_KEY_2)))
    if not providers: raise Exception("No AI keys configured")
    last = None
    for name, fn in providers:
        try:
            r = fn(); logger.info(f"[AI] ✅ {name}"); return r
        except Exception as e:
            logger.warning(f"[AI] ⚠️ {name}: {e}"); last = e; time.sleep(2)
    raise Exception(f"All AI providers failed: {last}")
