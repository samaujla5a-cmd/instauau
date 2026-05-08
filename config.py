import os
from dotenv import load_dotenv
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY    = os.getenv("GOOGLE_API_KEY", "")

# ── Official API credentials ──────────────────────────────
RAP_IG_TOKEN      = os.getenv("RAP_IG_TOKEN", "")
RAP_IG_USER_ID    = os.getenv("RAP_IG_USER_ID", "")       # REQUIRED — no default

BRAINROT_IG_TOKEN   = os.getenv("BRAINROT_IG_TOKEN", "")
BRAINROT_IG_USER_ID = os.getenv("BRAINROT_IG_USER_ID", "")  # REQUIRED — no default

MODEL_IG_TOKEN    = os.getenv("MODEL_IG_TOKEN", "")
MODEL_IG_USER_ID  = os.getenv("MODEL_IG_USER_ID", "")       # REQUIRED — no default

KIE_API_KEY  = os.getenv("KIE_API_KEY", "")
MUSIC_MODE   = os.getenv("MUSIC_MODE", "kie_suno")
TTS_MODE     = os.getenv("TTS_MODE", "edge_tts")

# ── Telegram Bot ──────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")

RAP_TIMES      = ["00:00","02:30","05:00","07:00","09:00","11:00","13:00","15:00","17:00","19:00"]
BRAINROT_TIMES = ["00:20","02:50","05:20","07:20","09:20","11:20","13:20","15:20","17:20","19:20"]
MODEL_TIMES    = ["00:40","03:10","05:40","07:40","09:40","11:40","13:40","15:40","17:40","19:40"]

# ── Music Style: Pure Indian Hiphop ──────────────────────────────────────────
# References: Divine, Prabh Deep, Seedhe Maut, Kr$na, MC Stan
# Sound: boom-bap beats, sitar/sarangi samples, dhol kicks, dark cinematic
# NOT pop trap — real street Indian hiphop
MUSIC_STYLE = {
    "genre": "indian hiphop",
    "vibe": "boom-bap, desi folk samples, sitar loops, street storytelling, cinematic production",
    "mood": "raw, real, introspective, street-wise, proud desi identity",
    "language": "Hinglish (Hindi + English mix) — natural code-switching like real Indian street rap",
    "slang": ["bhai", "yaar", "teri maa", "sahi bola", "arey", "ek dum", "sach bol", "paisa", "izzat", "gully", "raat", "subah", "dard"],
    "themes": [
        "Mumbai gully life and hustle",
        "desi street wisdom and real talk",
        "growing up broke but staying real",
        "family sacrifice and grinding hard",
        "haters and fake people in desi society",
        "late night vibes in the city",
        "social media fame vs real life",
        "grinding from nothing to something",
        "desi pride and cultural identity",
        "love gone wrong Indian style",
        "temple to trap — spiritual meets street",
        "parents pressure and finding your own path",
    ]
}

# ── AI Model Character — Indian AI Influencer (Naina-style) ──────────────────
# Reference: @naina_avtr, @kyra_ai — consistent Indian AI girl aesthetic
AI_MODEL_CHARACTER = {
    "description": (
        "beautiful indian woman, 23 years old, sharp symmetrical face, "
        "long dark hair, dusky warm brown skin, confident expressive eyes, "
        "high fashion aesthetic, photorealistic, 8k, ultra detailed"
    ),
    "style_notes": "Mix of traditional Indian fashion and modern western looks. Bollywood meets streetwear.",
    "vibes": [
        {"theme": "saree aesthetic", "vibe": "silk saree, traditional jewelry, golden hour, dreamy soft light"},
        {"theme": "modern streetwear", "vibe": "oversized hoodie, joggers, sneakers, urban India background"},
        {"theme": "Bollywood glam", "vibe": "lehenga, dramatic makeup, film studio lighting, cinematic"},
        {"theme": "gym motivation", "vibe": "athletic wear, gym selfie, strong confident look, mirror reflection"},
        {"theme": "coffee shop aesthetic", "vibe": "casual kurta, chai cup, cozy cafe, golden bokeh"},
        {"theme": "beach vacation", "vibe": "sundress, Goa beach, sunset, relaxed and joyful"},
        {"theme": "festive Diwali", "vibe": "anarkali suit, diyas, warm golden light, celebratory"},
        {"theme": "boss energy", "vibe": "business formal Indian fusion, office or city backdrop, powerful"},
        {"theme": "monsoon vibes", "vibe": "kurti, petrichor, rain background, romantic moody light"},
        {"theme": "wedding season guest", "vibe": "georgette lehenga, heavy jewelry, wedding decor, glamorous"},
    ]
}

EDGE_TTS_VOICE = "en-US-GuyNeural"
EDGE_TTS_RATE  = "-10%"
EDGE_TTS_PITCH = "-5Hz"

VIDEO = {
    "shorts_resolution": (1080, 1920),
    "resolution": (1920, 1080),
    "fps": 30,
    # Richer dark palettes with accent — replaced flat solid colors
    "bg_colors": ["#0a0010", "#000d1a", "#0d0000", "#000a00", "#1a0a00"],
    "accent_colors": ["#ff00ff", "#00e5ff", "#ff4500", "#39ff14", "#ffcc00"],
}

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SONGS_DIR  = os.path.join(OUTPUT_DIR, "songs")
VIDEOS_DIR = os.path.join(OUTPUT_DIR, "videos")
SHORTS_DIR = os.path.join(OUTPUT_DIR, "shorts")
LOGS_DIR   = os.path.join(OUTPUT_DIR, "logs")

SEO = {
    "instagram_hashtags_base": [
        "#rap", "#hiphop", "#desitrap", "#hindirap", "#indierap",
        "#desirap", "#gully", "#trapmusic", "#mumbai", "#india",
        "#reels", "#viral", "#fyp", "#explore", "#trending",
        "#emiway", "#divine", "#seedhemaut", "#desivibes",
    ],
}
