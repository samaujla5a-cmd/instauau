import os
from dotenv import load_dotenv
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY    = os.getenv("GOOGLE_API_KEY", "")

# ── Official API credentials ──────────────────────────────
RAP_IG_TOKEN      = os.getenv("RAP_IG_TOKEN", "")
RAP_IG_USER_ID    = os.getenv("RAP_IG_USER_ID", "26289756050724249")

BRAINROT_IG_TOKEN   = os.getenv("BRAINROT_IG_TOKEN", "")
BRAINROT_IG_USER_ID = os.getenv("BRAINROT_IG_USER_ID", "27577862725154087")

MODEL_IG_TOKEN    = os.getenv("MODEL_IG_TOKEN", "")
MODEL_IG_USER_ID  = os.getenv("MODEL_IG_USER_ID", "26616509901340408")

MUSIC_MODE   = os.getenv("MUSIC_MODE", "gtts_only")
TTS_MODE     = os.getenv("TTS_MODE", "edge_tts")
SUNO_COOKIE  = os.getenv("SUNO_COOKIE", "")

RAP_TIMES      = ["00:00","02:30","05:00","07:00","09:00","11:00","13:00","15:00","17:00","19:00"]
BRAINROT_TIMES = ["00:20","02:50","05:20","07:20","09:20","11:20","13:20","15:20","17:20","19:20"]
MODEL_TIMES    = ["00:40","03:10","05:40","07:40","09:40","11:40","13:40","15:40","17:40","19:40"]

MUSIC_STYLE = {
    "genre": "hip-hop",
    "vibe": "trippy, chill, psychedelic, lo-fi trap",
    "mood": "elevated, introspective, smooth",
    "themes": [
        "consciousness expansion","universe and cosmos","street wisdom",
        "late night vibes","third eye awakening","deep thoughts",
        "spiritual journey","city lights at 3am","peace and elevation",
    ]
}

EDGE_TTS_VOICE = "en-US-GuyNeural"
EDGE_TTS_RATE  = "-10%"
EDGE_TTS_PITCH = "-5Hz"

VIDEO = {
    "shorts_resolution": (1080, 1920),
    "resolution": (1920, 1080),
    "fps": 30,
    "bg_colors": ["#0a0010","#001a00","#10000a","#000d1a"],
    "accent_colors": ["#39ff14","#ff00ff","#00ffff","#ffff00","#ff4500"],
}

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SONGS_DIR  = os.path.join(OUTPUT_DIR, "songs")
VIDEOS_DIR = os.path.join(OUTPUT_DIR, "videos")
SHORTS_DIR = os.path.join(OUTPUT_DIR, "shorts")
LOGS_DIR   = os.path.join(OUTPUT_DIR, "logs")

SEO = {
    "instagram_hashtags_base": [
        "#rap","#hiphop","#trap","#trippyvibes","#lofi",
        "#chillvibes","#undergroundhiphop","#rapmusic","#newmusic",
        "#reels","#viral","#fyp","#explore","#trending"
    ],
}
