import os
from dotenv import load_dotenv
load_dotenv()

KIE_API_KEY  = os.getenv("KIE_API_KEY", "")
GOOGLE_API_KEY    = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_API_KEY_2  = os.getenv("GOOGLE_API_KEY_2", "")
GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")

RAP_IG_TOKEN      = os.getenv("RAP_IG_TOKEN", "")
RAP_IG_USER_ID    = os.getenv("RAP_IG_USER_ID", "")
BRAINROT_IG_TOKEN   = os.getenv("BRAINROT_IG_TOKEN", "")
BRAINROT_IG_USER_ID = os.getenv("BRAINROT_IG_USER_ID", "")
MODEL_IG_TOKEN    = os.getenv("MODEL_IG_TOKEN", "")
MODEL_IG_USER_ID  = os.getenv("MODEL_IG_USER_ID", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")

RAP_TIMES      = ["00:00","02:30","05:00","07:00","09:00","11:00","13:00","15:00","17:00","19:00"]
BRAINROT_TIMES = ["00:20","02:50","05:20","07:20","09:20","11:20","13:20","15:20","17:20","19:20"]
MODEL_TIMES    = ["00:40","03:10","05:40","07:40","09:40","11:40","13:40","15:40","17:40","19:40"]

MUSIC_STYLE = {
    "genre": "indian hiphop",
    "vibe": "boom-bap, desi folk samples, sitar loops, street storytelling",
    "mood": "raw, real, introspective, street-wise",
    "language": "Hinglish",
    "slang": ["bhai","yaar","teri maa","sahi bola","arey","ek dum","sach bol","paisa","izzat","gully"],
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
        "temple to trap spiritual meets street",
        "parents pressure and finding your own path",
    ]
}

AI_MODEL_CHARACTER = {
    "description": (
        "beautiful indian woman, 23 years old, sharp symmetrical face, "
        "long dark hair, dusky warm brown skin, confident expressive eyes, "
        "high fashion aesthetic, photorealistic, 8k, ultra detailed"
    ),
    "vibes": [
        {"theme": "saree aesthetic", "vibe": "silk saree, traditional jewelry, golden hour, dreamy soft light"},
        {"theme": "modern streetwear", "vibe": "oversized hoodie, joggers, sneakers, urban India background"},
        {"theme": "Bollywood glam", "vibe": "lehenga, dramatic makeup, film studio lighting, cinematic"},
        {"theme": "gym motivation", "vibe": "athletic wear, gym selfie, strong confident look"},
        {"theme": "coffee shop aesthetic", "vibe": "casual kurta, chai cup, cozy cafe, golden bokeh"},
        {"theme": "beach vacation", "vibe": "sundress, Goa beach, sunset, relaxed and joyful"},
        {"theme": "festive Diwali", "vibe": "anarkali suit, diyas, warm golden light, celebratory"},
        {"theme": "boss energy", "vibe": "business formal Indian fusion, office backdrop, powerful"},
        {"theme": "monsoon vibes", "vibe": "kurti, petrichor, rain background, romantic moody light"},
        {"theme": "wedding season guest", "vibe": "georgette lehenga, heavy jewelry, wedding decor, glamorous"},
    ]
}

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SONGS_DIR  = os.path.join(OUTPUT_DIR, "songs")
VIDEOS_DIR = os.path.join(OUTPUT_DIR, "videos")
SHORTS_DIR = os.path.join(OUTPUT_DIR, "shorts")
LOGS_DIR   = os.path.join(OUTPUT_DIR, "logs")

SEO = {
    "instagram_hashtags_base": [
        "#rap","#hiphop","#desitrap","#hindirap","#desirap",
        "#gully","#trapmusic","#mumbai","#india","#reels",
        "#viral","#fyp","#explore","#trending","#desivibes",
    ],
}
