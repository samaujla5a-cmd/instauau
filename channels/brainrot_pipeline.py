"""
BRAINROT PIPELINE — Indian HALKU Brainrot (2025 Viral Format)
==============================================================
Format: Indian desi absurdist creatures — the "Halku" brainrot style
that's blowing up on Indian Instagram/Reels in 2025.

Reference format: Halku Chacha, Tillu Bhains, Pappu Sher style —
absurd Indian names + surreal fused creatures + Hindi-English voiceover.
FULL SCREEN 9:16. No split screen. No subway surfers. No minecraft.
"""
import asyncio, os, re, json, random, logging, subprocess, requests, time
from pathlib import Path
from datetime import datetime
from core.gemini_client import gemini

logger    = logging.getLogger("BRAINROT")
BASE_DIR  = Path(__file__).parent.parent
BRAIN_DIR = BASE_DIR / "output" / "brainrot"
BRAIN_DIR.mkdir(parents=True, exist_ok=True)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

KIE_API_KEY = os.getenv("KIE_API_KEY", "")

# ── Indian Halku Brainrot Character Generator ──────────────────────────────
HALKU_TEMPLATES = [
    ("sher",    "sarkari babu briefcase",  "Halku Sher Babu"),
    ("bhains",  "chai ki ketli body",      "Tillu Bhains Chaiwala"),
    ("bandar",  "jugaad scooter",          "Pappu Bandar Jugaadu"),
    ("haathi",  "paneer tikka trunk",      "Motu Haathi Tikka"),
    ("gadha",   "UPSC notes wings",        "Chintu Gadha UPSC"),
    ("kutta",   "cricket bat legs",        "Bholu Kutta Cricketer"),
    ("billi",   "bindi and saree",         "Chamki Billi Auntie"),
    ("ghoda",   "desi ghee armor",         "Sardar Ghoda Ghee"),
    ("bakri",   "auto-rickshaw shell",     "Guddi Bakri Auto"),
    ("ullu",    "sarkari stamp beak",      "Lallu Ullu Sarkaar"),
    ("girgit",  "haldi turmeric skin",     "Haldu Girgit Haldi"),
    ("murgha",  "ludo board wings",        "Pappu Murgha Ludo"),
    ("bhalu",   "masala dabba stomach",    "Bunty Bhalu Masala"),
    ("tota",    "news channel mic beak",   "Breaking Tota News"),
    ("machchar","five rupee coin wings",   "Machchar Bhai Paanch"),
    ("neela machhli", "samosa fins",       "Samosa Machhli Bhai"),
]

HALKU_POWERS = [
    "ek dum 1000 kilo chai pee sakta hai aur fir bhi neend nahi aati",
    "sarkari file itni tez chalata hai ki light bhi peechhe reh jaati hai",
    "jugaad se rocket launch kar deta hai aur petrol ka kharcha nahi",
    "biryani ki smell se poori colony ko hypnotize kar leta hai",
    "cricket commentary sunke dushman bhaag jaate hain seedha ghar",
    "desi ghee se itna strong hai ki Hulk bhi bhai bolta hai",
    "UPSC ke saare syllabus yaad hain par admit card gum ho jaata hai",
    "auto ka meter itna fast chalata hai ki calculator bhi haar maanta hai",
    "ludo khelte waqt cheats karta hai par pakda nahi jaata kabhi",
]

HALKU_WEAKNESSES = [
    "chai mein adrak na ho toh coma mein chala jaata hai",
    "IRCTC ka ticket confirm nahi hua toh power khatam ho jaati hai",
    "bijli chali jaaye toh transformer ban jaata hai zero se",
    "internet slow ho toh instantly sad ho jaata hai",
    "ghar mein sabji nahi hai ye sunke instantly defeat ho jaata hai",
]

HINGLISH_OPENERS = [
    "DEKHO BHAI", "YE KYA HAI BHAI", "CHHODO SAB KUCH",
    "SCIENTISTS NE KHOJA", "HALKU AA GAYA",
    "KHABARDAR DOST", "BHAI SUNO ZARA", "YE WALA NEW HAI",
    "LOG DARTE HAIN JISSE",
]


def generate_creature() -> dict:
    template = random.choice(HALKU_TEMPLATES)
    animal, obj, default_name = template
    power = random.choice(HALKU_POWERS)
    weakness = random.choice(HALKU_WEAKNESSES)
    opener = random.choice(HINGLISH_OPENERS)

    prompt = f"""You create viral Indian Halku Brainrot meme characters — Indian absurdist humor mixing
desi life, Hinglish, jugaad culture, and surreal animal-object fusions. Think: Tillu Bhains, Halku Chacha, Pappu Sher.
Base: {animal} fused with {obj}.

Return ONLY valid JSON, no markdown:
{{
    "name": "Desi absurdist name 2-3 words Hinglish like Tillu Bhains Chaiwala or Pappu Sher Babu",
    "image_prompt": "Surreal photorealistic {animal} grotesquely fused with {obj}, Indian desi meme creature, white background, absurdist AI art, ultra detailed, funny and unsettling, very Indian aesthetic",
    "narrator_script": "Dramatic Hinglish 30-40 word narration: {opener} [NAME]! Ye {animal} aur {obj} ka combination hai jo India mein paida hua. Iska power: {power}. Iska weakness: {weakness}. KOI NAHI BACH SAKTA [NAME] SE!",
    "hook_text": "Creature name ALL CAPS Hinglish max 25 chars",
    "caption": "Instagram caption max 120 chars with emojis desi humor Hinglish vibe",
    "hashtags": ["#halkubrainrot", "#desimemes", "#indianbrainrot", "#viral", "#fyp", "#desi", "#funnyvideo", "#reels"]
}}"""

    raw = re.sub(r"```json|```", "", gemini(prompt)).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Brainrot JSON parse failed — using defaults")
        data = {
            "name": default_name,
            "image_prompt": (
                f"surreal photorealistic {animal} grotesquely fused with {obj}, "
                "Indian desi meme creature, white background, ultra detailed 8k absurdist art, funny"
            ),
            "narrator_script": (
                f"{opener} {default_name.upper()}! "
                f"Ye {animal} aur {obj} ka combination hai. "
                f"Iska power: {power}. "
                f"Iska weakness: {weakness}. "
                "KOI NAHI BACH SAKTA!"
            ),
            "hook_text": default_name.upper()[:25],
            "caption": f"Bhai ye kya hai yaar 💀 {default_name} #halkubrainrot",
            "hashtags": ["#halkubrainrot", "#desimemes", "#indianbrainrot", "#viral", "#fyp"],
        }

    data["animal"] = animal
    logger.info(f"Generated creature: {data.get('name', 'Unknown')}")
    return data


def _kie_headers():
    return {"Authorization": f"Bearer {KIE_API_KEY}", "Content-Type": "application/json"}


def _poll_kie_image(task_id: str) -> str | None:
    for _ in range(20):
        time.sleep(10)
        try:
            r = requests.get(
                "https://api.kie.ai/api/v1/jobs/recordInfo",
                params={"taskId": task_id}, headers=_kie_headers(), timeout=30
            )
            if not r.ok:
                continue
            data = r.json().get("data") or {}
            status = data.get("state") or data.get("status", "PENDING")
            if status in ("success", "SUCCESS"):
                result_json = data.get("resultJson") or ""
                if result_json:
                    result = json.loads(result_json)
                    urls = result.get("resultUrls") or []
                    if urls:
                        return urls[0]
                resp = data.get("response") or {}
                return resp.get("imageUrl") or resp.get("url") or None
            if status in ("error", "ERROR", "failed", "FAILED"):
                return None
        except Exception:
            continue
    return None


def generate_creature_image(content: dict, session: str) -> str | None:
    """Try kie.ai Flux for full-screen 9:16 creature image."""
    if not KIE_API_KEY:
        logger.info("No KIE_API_KEY — skipping creature image generation")
        return None

    image_prompt = content.get("image_prompt", "")
    if not image_prompt:
        return None

    endpoints = [
        ("https://api.kie.ai/api/v1/flux-kontext/generate", True),
        ("https://api.kie.ai/api/v1/flux/generate", False),
        ("https://api.kie.ai/api/v1/image/flux/generate", False),
    ]

    for endpoint, is_kontext in endpoints:
        try:
            if is_kontext:
                payload = {"callBackUrl": "https://example.com/callback",
                           "input": {"prompt": image_prompt[:500], "aspect_ratio": "9:16"}}
            else:
                payload = {"prompt": image_prompt[:500], "model": "flux-dev",
                           "width": 1080, "height": 1920, "seed": random.randint(1, 9999),
                           "callBackUrl": "https://example.com/callback"}

            resp = requests.post(endpoint, headers=_kie_headers(), json=payload, timeout=60)
            if resp.status_code in (404, 422):
                continue
            if resp.status_code == 402:
                logger.warning("kie.ai credits exhausted")
                return None
            if resp.ok:
                task_id = (resp.json().get("data") or {}).get("taskId", "")
                if task_id:
                    image_url = _poll_kie_image(task_id)
                    if image_url:
                        out_path = str(BRAIN_DIR / f"creature_{session}.jpg")
                        r = requests.get(image_url, timeout=120, stream=True)
                        r.raise_for_status()
                        with open(out_path, "wb") as f:
                            for chunk in r.iter_content(65536):
                                f.write(chunk)
                        if Path(out_path).stat().st_size > 10000:
                            logger.info(f"✅ Creature image: {out_path}")
                            return out_path
        except Exception as e:
            logger.warning(f"kie.ai creature image error at {endpoint}: {e}")
            continue

    logger.info("All kie.ai image endpoints failed — using gradient fallback")
    return None


def _create_fallback_image(content: dict, session: str) -> str:
    """Desi saffron/green gradient placeholder when kie.ai is down."""
    out_path = str(BRAIN_DIR / f"creature_{session}.jpg")
    name = re.sub(r"[^A-Za-z0-9 ]", "", content.get("hook_text", "HALKU BRAINROT"))[:25]
    animal = content.get("animal", "sher").upper()

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "color=c=0x0a0a1a:size=1080x1920:rate=1",
        "-vf", (
            "drawbox=x=0:y=0:w=iw:h=ih/3:color=0xFF6700@0.4:t=fill,"
            "drawbox=x=0:y=2*ih/3:w=iw:h=ih/3:color=0x138808@0.35:t=fill,"
            "drawbox=x=0:y=0:w=iw:h=12:color=0xFF6700@1.0:t=fill,"
            "drawbox=x=0:y=ih-12:w=iw:h=12:color=0x138808@1.0:t=fill,"
            f"drawtext=text='{animal}'"
            f":fontfile={FONT}:fontsize=120:fontcolor=white"
            f":x=(w-text_w)/2:y=h*0.30"
            ":bordercolor=black:borderw=5,"
            f"drawtext=text='{name}'"
            f":fontfile={FONT}:fontsize=64:fontcolor=0xFFD700"
            f":x=(w-text_w)/2:y=h*0.52"
            ":bordercolor=black:borderw=4,"
            "drawtext=text='HALKU BRAINROT'"
            f":fontfile={FONT}:fontsize=36:fontcolor=white"
            ":x=(w-text_w)/2:y=h*0.65"
            ":bordercolor=0xFF6700:borderw=3"
            ":box=1:boxcolor=0xFF6700@0.8:boxborderw=10"
        ),
        "-frames:v", "1",
        "-q:v", "2",
        out_path,
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=30)
    if not Path(out_path).exists() or Path(out_path).stat().st_size < 1000:
        raise RuntimeError(f"Fallback image creation failed: {r.stderr.decode()[-200:]}")
    logger.info(f"✅ Fallback creature image: {out_path}")
    return out_path


async def _tts(text: str, path: str) -> None:
    import edge_tts
    # Indian English male narrator — dramatic pacing
    await edge_tts.Communicate(text, "en-IN-PrabhatNeural", rate="-8%", pitch="+5Hz").save(path)


def generate_voiceover(narrator_script: str, session: str) -> str | None:
    try:
        path = str(BRAIN_DIR / f"voice_{session}.mp3")

        def _run_tts():
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_tts(narrator_script, path))
            finally:
                loop.close()

        _run_tts()
        if Path(path).exists() and Path(path).stat().st_size > 1000:
            logger.info(f"✅ Voiceover: {path}")
            return path
    except Exception as e:
        logger.warning(f"TTS failed: {e}")
    return None


def _safe_text(t: str, maxlen: int = 28) -> str:
    return re.sub(r"[^A-Za-z0-9 ]", "", t)[:maxlen].upper()


def _probe_ok(path: str) -> bool:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name",
         "-of", "default=noprint_wrappers=1", path],
        capture_output=True, timeout=20,
    )
    return r.returncode == 0


def _ffmpeg(cmd: list, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def create_brainrot_video(content: dict, creature_image_path: str | None, duration: int = 30) -> str:
    """
    Indian Halku Brainrot — FULL SCREEN 9:16 format.
    No split screen. No subway surfers. No minecraft. Just the creature.
    """
    session   = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path  = str(BRAIN_DIR / f"brainrot_{session}.mp4")
    tmp_path  = out_path + ".tmp.mp4"

    creature_name = _safe_text(content.get("hook_text", content.get("name", "HALKU CREATURE")), 28)
    narrator_text = content.get("narrator_script", "BHAI YE KYA HAI")
    voice_path    = generate_voiceover(narrator_text, session)

    logger.info(f"Building Halku brainrot video: {creature_name}")

    # Get or create creature image
    has_image = creature_image_path and os.path.exists(creature_image_path)
    if not has_image:
        try:
            creature_image_path = _create_fallback_image(content, session)
            has_image = True
        except Exception as e:
            logger.warning(f"Fallback image creation failed: {e}")
            has_image = False

    def _build(with_text: bool, output: str) -> subprocess.CompletedProcess:
        # Build all inputs first, then output options — FFmpeg is strict about this order.
        # BUG FIX: previously -vf was placed after voice input causing FFmpeg to treat
        # it as an input option for the audio file ("Option vf cannot be applied to input").
        cmd = ["ffmpeg", "-y"]

        # Input 0: video source (image loop or color)
        if has_image:
            cmd += ["-loop", "1", "-t", str(duration), "-i", creature_image_path]
        else:
            cmd += ["-f", "lavfi", "-t", str(duration),
                    "-i", "color=c=0x1a0a00:size=1080x1920:rate=30"]

        # Input 1: audio (voice) — must be added before any output options
        has_voice = voice_path and os.path.exists(voice_path)
        if has_voice:
            cmd += ["-i", voice_path]

        # All output options come AFTER all inputs
        name_safe = creature_name.replace("'", "").replace(":", "\\:").replace("%", "\\%")

        if with_text:
            vf = (
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,setsar=1,"
                f"drawtext=text='{name_safe}'"
                f":fontfile={FONT}:fontsize=72:fontcolor=0xFFD700"
                ":bordercolor=black:borderw=5"
                ":x=(w-text_w)/2:y=35"
                ":box=1:boxcolor=black@0.7:boxborderw=16,"
                "drawtext=text='HALKU BRAINROT'"
                f":fontfile={FONT}:fontsize=22:fontcolor=white"
                ":bordercolor=0xFF6700:borderw=2"
                ":x=w-text_w-15:y=135"
                ":box=1:boxcolor=0xFF6700@0.92:boxborderw=8,"
                "drawtext=text='BHAI DEKH LE... AUR SHARE KAR'"
                f":fontfile={FONT}:fontsize=28:fontcolor=white"
                ":bordercolor=black:borderw=2"
                ":x=(w-text_w)/2:y=h-55"
                ":box=1:boxcolor=black@0.65:boxborderw=8"
            )
        else:
            vf = (
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,setsar=1,format=yuv420p"
            )

        cmd += ["-map", "0:v", "-vf", vf]

        if has_voice:
            cmd += ["-map", "1:a", "-c:a", "aac", "-b:a", "128k"]
        else:
            cmd += ["-an"]

        cmd += [
            "-t", str(duration),
            "-r", "30",   # explicit fps — required for still-image -loop 1 input
            "-c:v", "libx264", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output,
        ]
        return _ffmpeg(cmd)

    # Attempt 1: full screen + text + voice
    r = _build(with_text=True, output=tmp_path)
    sz = Path(tmp_path).stat().st_size if Path(tmp_path).exists() else 0
    if sz >= 50_000 and _probe_ok(tmp_path):
        os.replace(tmp_path, out_path)
        logger.info(f"✅ Halku brainrot video: {out_path} ({sz // 1024}KB)")
        return out_path
    logger.warning(f"Attempt 1 failed ({sz}b)")
    if Path(tmp_path).exists():
        os.remove(tmp_path)

    # Attempt 2: no text
    r = _build(with_text=False, output=tmp_path)
    sz = Path(tmp_path).stat().st_size if Path(tmp_path).exists() else 0
    if sz >= 50_000 and _probe_ok(tmp_path):
        os.replace(tmp_path, out_path)
        logger.info(f"✅ Halku brainrot video (no text): {out_path}")
        return out_path
    logger.warning(f"Attempt 2 failed ({sz}b): {r.stderr.decode()[-300:]}")
    if Path(tmp_path).exists():
        os.remove(tmp_path)

    # Attempt 3: pure color bar minimum
    cmd3 = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-t", str(duration),
        "-i", "color=c=0x1a0500:size=1080x1920:rate=30",
        "-vf", f"drawtext=text='{creature_name}':fontfile={FONT}:fontsize=80:fontcolor=0xFFD700:x=(w-text_w)/2:y=(h-text_h)/2,format=yuv420p",
    ]
    if voice_path and os.path.exists(voice_path):
        cmd3 += ["-i", voice_path, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "128k"]
    else:
        cmd3 += ["-an"]
    cmd3 += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path]
    r = _ffmpeg(cmd3)
    sz = Path(out_path).stat().st_size if Path(out_path).exists() else 0
    if sz < 50_000:
        raise RuntimeError(f"All brainrot attempts failed. stderr: {r.stderr.decode()[-400:]}")
    logger.info(f"✅ Fallback color video: {out_path} ({sz // 1024}KB)")
    return out_path


def run_brainrot_pipeline() -> dict:
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"BRAINROT PIPELINE START | {session_id}")
    result = {
        "session_id": session_id, "channel": "brainrot",
        "started_at": datetime.now().isoformat(),
        "video_path": None, "caption": None, "hashtags": [], "errors": [],
    }
    try:
        content = generate_creature()
        result["topic"]    = content.get("name", "Halku Brainrot")
        result["title"]    = content.get("name", "Halku Creature")
        result["caption"]  = content.get("caption", "")
        result["hashtags"] = content.get("hashtags", [])

        creature_image = generate_creature_image(content, session_id)
        result["video_path"] = create_brainrot_video(content, creature_image)
        logger.info(f"Halku brainrot video ready: {result['video_path']}")
    except Exception as e:
        logger.error(f"Brainrot pipeline failed: {e}", exc_info=True)
        result["errors"].append(str(e))
    result["completed_at"] = datetime.now().isoformat()
    return result
