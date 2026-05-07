"""
BRAINROT PIPELINE — Italian Brainrot Style (2025 Viral Format)
==============================================================
Format: AI-generated absurd Italian-named creature image displayed
over Subway Surfers / Minecraft split screen with dramatic English narration.

Reference: Tralalero Tralala, Bombardino Crocodilo style.
- TOP HALF: AI creature image (from kie.ai) OR Minecraft fallback
- BOTTOM HALF: Subway Surfers gameplay (the dopamine trap)  
- Creature name in massive yellow text
- Dramatic voiceover narrating lore
- "ITALIAN BRAINROT" badge
"""
import asyncio, os, re, json, random, logging, subprocess, requests, time
from pathlib import Path
from datetime import datetime
from core.gemini_client import gemini

logger    = logging.getLogger("BRAINROT")
BASE_DIR  = Path(__file__).parent.parent
BRAIN_DIR = BASE_DIR / "output" / "brainrot"
BRAIN_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = BASE_DIR / "assets"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

KIE_API_KEY = os.getenv("KIE_API_KEY", "")

# ── Italian Brainrot Character Generator ─────────────────────────────────────
CREATURE_TEMPLATES = [
    ("shark", "Nike sneakers", "Tralalini Tralalù"),
    ("crocodile", "military bomber jet", "Bombardelli Crocodilino"),
    ("monkey", "giant banana", "Chimpanzello Bananini"),
    ("cat", "cappuccino cup head", "Gattocino Cappuccinelli"),
    ("elephant", "cactus body", "Elefantino Cactusello"),
    ("bear", "pizza wings", "Orsello Pizzarino"),
    ("dog", "spaghetti legs", "Canino Spaghetini"),
    ("lion", "gelato cone body", "Leonello Gelatino"),
    ("frog", "espresso machine torso", "Ranocchio Espressini"),
    ("eagle", "mozzarella wings", "Aquilino Mozzarellello"),
    ("gorilla", "Ferrari engine chest", "Gorillini Ferrarello"),
    ("tiger", "pasta tornado aura", "Tigrello Pastasciuttini"),
    ("wolf", "Roman colosseum shell", "Lupino Colossellino"),
    ("octopus", "vespa scooter body", "Polpino Vespettino"),
    ("penguin", "opera singing mouth", "Pinguino Operellino"),
    ("hippo", "wine barrel body", "Ippopotellino Vinello"),
    ("cobra", "mandolin guitar tail", "Cobrino Mandolellino"),
    ("rhino", "meatball horn", "Rinocerello Polpettino"),
]

CREATURE_POWERS = [
    "runs at the speed of a Lamborghini on the Autostrada",
    "can summon unlimited pasta from thin air",
    "screams Italian opera at 140 decibels when threatened",
    "transforms into a giant cannoli when angry",
    "its footsteps sound like someone slapping pizza dough",
    "can bench press the Leaning Tower of Pisa",
    "breathes fire that smells like garlic bread",
    "absorbs power from WiFi signals and espresso",
    "its tears turn into mozzarella pearls when it cries",
    "can teleport by doing the Italian hand gesture",
    "regenerates health by eating carbonara",
    "its roar causes earthquakes in all of Naples",
]

CREATURE_WEAKNESSES = [
    "pineapple on pizza",
    "decaf coffee",
    "overcooked pasta",
    "a German correcting its Italian pronunciation",
    "running out of olive oil",
    "bad espresso",
    "a Frenchman claiming to make better pasta",
    "instant coffee",
    "unsalted food",
]

DRAMATIC_OPENERS = [
    "BEHOLD", "WITNESS THE TERROR OF", "FEAR THE MIGHTY",
    "BOW DOWN BEFORE", "TREMBLE AT THE SIGHT OF",
    "THE LEGENDS SPEAK OF", "SCIENTISTS DISCOVERED",
    "DEEP IN ITALY LIVES", "NONE CAN ESCAPE",
]


def generate_creature() -> dict:
    template = random.choice(CREATURE_TEMPLATES)
    animal, obj, default_name = template
    power = random.choice(CREATURE_POWERS)
    weakness = random.choice(CREATURE_WEAKNESSES)
    opener = random.choice(DRAMATIC_OPENERS)

    prompt = f"""You create viral Italian Brainrot meme characters like Tralalero Tralala and Bombardino Crocodilo.
Base: {animal} fused with {obj}. 

Return ONLY valid JSON, no markdown:
{{
    "name": "Pseudo-Italian creature name (2-3 words, suffix like -ini -ello -ino e.g. Chimpanzini Bananini)",
    "image_prompt": "Surreal photorealistic {animal} grotesquely fused with {obj}, meme creature, white background, absurdist AI art, ultra detailed, funny and unsettling",
    "narrator_script": "Dramatic 30-40 word narration: '{opener} [NAME]! A {animal} fused with {obj} born in Naples. It {power}. Its only weakness is {weakness}. NONE CAN ESCAPE [NAME]!'",
    "hook_text": "Creature name ALL CAPS max 25 chars",
    "caption": "Instagram caption max 120 chars with emojis absurdist humor Italian vibe",
    "hashtags": ["#brainrot", "#italianbrainrot", "#viral", "#fyp", "#memes", "#aianimals"]
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
                "funny meme creature, white background, ultra detailed 8k absurdist art"
            ),
            "narrator_script": (
                f"{opener} {default_name.upper()}! A {animal} fused with {obj} "
                f"born in the mountains of Naples. It {power}. "
                f"Its only weakness is {weakness}. NONE CAN ESCAPE!"
            ),
            "hook_text": default_name.upper()[:25],
            "caption": f"POV: you just met {default_name} 💀🇮🇹 #brainrot",
            "hashtags": ["#brainrot", "#italianbrainrot", "#viral", "#fyp", "#memes"],
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
    """Try kie.ai Flux for AI creature image. Returns local path or None."""
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
                           "input": {"prompt": image_prompt[:500], "aspect_ratio": "1:1"}}
            else:
                payload = {"prompt": image_prompt[:500], "model": "flux-dev",
                           "width": 960, "height": 960, "seed": random.randint(1, 9999),
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

    logger.info("All kie.ai image endpoints failed — using Minecraft top half")
    return None


async def _tts(text: str, path: str) -> None:
    import edge_tts
    # Dramatic slower pace like Italian brainrot narrators
    await edge_tts.Communicate(text, "en-US-GuyNeural", rate="-5%", pitch="-10Hz").save(path)


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


def _safe_text(t: str, maxlen: int = 30) -> str:
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


def create_brainrot_video(content: dict, creature_image_path: str | None, duration: int = 45) -> str:
    """
    Italian Brainrot split-screen video:
    TOP (960px):  AI creature image OR Minecraft gameplay  
    BOTTOM (960px): Subway Surfers (the viral scroll-trap)
    Overlay: creature name + ITALIAN BRAINROT badge + bottom CTA
    Audio: dramatic voiceover narrating creature lore
    """
    session     = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path    = str(BRAIN_DIR / f"brainrot_{session}.mp4")
    tmp_path    = out_path + ".tmp.mp4"
    subway_clip = str(ASSETS_DIR / "subway.mp4")
    minecraft_clip = str(ASSETS_DIR / "minecraft.mp4")

    missing = [p for p in [subway_clip, minecraft_clip] if not os.path.exists(p)]
    if missing:
        raise FileNotFoundError(f"Missing asset files: {missing}")

    creature_name = _safe_text(content.get("hook_text", content.get("name", "BRAINROT CREATURE")), 28)
    narrator_text = content.get("narrator_script", "BEHOLD THIS CREATURE")
    voice_path = generate_voiceover(narrator_text, session)

    logger.info(f"Building brainrot video: {creature_name}")

    has_image = creature_image_path and os.path.exists(creature_image_path)

    def _build(use_creature_img: bool, with_text: bool, output: str) -> subprocess.CompletedProcess:
        cmd = ["ffmpeg", "-y"]

        # Input 0: top source
        if use_creature_img and has_image:
            cmd += ["-loop", "1", "-t", str(duration), "-i", creature_image_path]
        else:
            cmd += ["-stream_loop", "-1", "-t", str(duration), "-i", minecraft_clip]

        # Input 1: subway surfers (bottom)
        cmd += ["-stream_loop", "-1", "-t", str(duration), "-i", subway_clip]

        # Input 2: voice (optional)
        voice_input_idx = None
        if voice_path and os.path.exists(voice_path):
            cmd += ["-i", voice_path]
            voice_input_idx = 2

        # Filter complex
        if with_text:
            name_safe = creature_name.replace("'", "").replace(":", "\\:").replace("%", "\\%")
            fc = (
                "[0:v]scale=1080:960,setsar=1[top];"
                "[1:v]scale=1080:960,setsar=1[bot];"
                "[top][bot]vstack=inputs=2[stk];"
                # Creature name — massive yellow centered at very top
                f"[stk]drawtext=text='{name_safe}'"
                f":fontfile={FONT}:fontsize=68:fontcolor=yellow"
                ":bordercolor=black:borderw=5"
                ":x=(w-text_w)/2:y=18"
                ":box=1:boxcolor=black@0.75:boxborderw=14,"
                # ITALIAN BRAINROT badge top-right
                "drawtext=text='ITALIAN BRAINROT'"
                f":fontfile={FONT}:fontsize=22:fontcolor=white"
                ":bordercolor=red:borderw=2"
                ":x=w-text_w-15:y=h/2+20"
                ":box=1:boxcolor=red@0.9:boxborderw=6,"
                # Yellow divider line at midpoint
                "drawbox=x=0:y=958:w=iw:h=4:color=yellow@1.0:t=fill,"
                # Bottom scroll bait text
                "drawtext=text='KEEP WATCHING... IF YOU DARE'"
                f":fontfile={FONT}:fontsize=22:fontcolor=white"
                ":bordercolor=black:borderw=2"
                ":x=(w-text_w)/2:y=h-36"
                ":box=1:boxcolor=black@0.6:boxborderw=6"
                "[out]"
            )
        else:
            fc = (
                "[0:v]scale=1080:960,setsar=1[top];"
                "[1:v]scale=1080:960,setsar=1[bot];"
                "[top][bot]vstack=inputs=2[out]"
            )

        cmd += ["-filter_complex", fc, "-map", "[out]"]

        if voice_input_idx is not None:
            cmd += ["-map", f"{voice_input_idx}:a", "-c:a", "aac", "-b:a", "128k"]
        else:
            cmd += ["-an"]

        cmd += [
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output,
        ]
        return _ffmpeg(cmd)

    # Attempt 1: AI creature image top + full text + voice
    r = _build(use_creature_img=True, with_text=True, output=tmp_path)
    sz = Path(tmp_path).stat().st_size if Path(tmp_path).exists() else 0
    if sz >= 50_000 and _probe_ok(tmp_path):
        os.replace(tmp_path, out_path)
        logger.info(f"✅ Brainrot video ready: {out_path} ({sz // 1024}KB)")
        return out_path
    logger.warning(f"Attempt 1 failed ({sz}b)")
    if Path(tmp_path).exists(): os.remove(tmp_path)

    # Attempt 2: Minecraft top + full text
    r = _build(use_creature_img=False, with_text=True, output=tmp_path)
    sz = Path(tmp_path).stat().st_size if Path(tmp_path).exists() else 0
    if sz >= 50_000 and _probe_ok(tmp_path):
        os.replace(tmp_path, out_path)
        logger.info(f"✅ Brainrot video (minecraft top): {out_path}")
        return out_path
    logger.warning(f"Attempt 2 failed ({sz}b): {r.stderr.decode()[-300:]}")
    if Path(tmp_path).exists(): os.remove(tmp_path)

    # Attempt 3: Minecraft top + no text
    r = _build(use_creature_img=False, with_text=False, output=tmp_path)
    sz = Path(tmp_path).stat().st_size if Path(tmp_path).exists() else 0
    if sz >= 50_000 and _probe_ok(tmp_path):
        os.replace(tmp_path, out_path)
        logger.info(f"✅ Brainrot video (no text): {out_path}")
        return out_path
    if Path(tmp_path).exists(): os.remove(tmp_path)

    # Attempt 4: Single clip bare minimum
    cmd4 = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", subway_clip]
    if voice_path and os.path.exists(voice_path):
        cmd4 += ["-i", voice_path, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "128k"]
    else:
        cmd4 += ["-map", "0:v", "-an"]
    cmd4 += [
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-t", str(duration), "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path,
    ]
    r = _ffmpeg(cmd4)
    sz = Path(out_path).stat().st_size if Path(out_path).exists() else 0
    if sz < 50_000:
        raise RuntimeError(f"All brainrot attempts failed. stderr: {r.stderr.decode()[-400:]}")
    logger.info(f"✅ Fallback single clip: {out_path} ({sz // 1024}KB)")
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
        result["topic"]    = content.get("name", "Italian Brainrot")
        result["title"]    = content.get("name", "Brainrot Creature")
        result["caption"]  = content.get("caption", "")
        result["hashtags"] = content.get("hashtags", [])

        creature_image = generate_creature_image(content, session_id)

        result["video_path"] = create_brainrot_video(content, creature_image)
        logger.info(f"Brainrot video ready: {result['video_path']}")
    except Exception as e:
        logger.error(f"Brainrot pipeline failed: {e}", exc_info=True)
        result["errors"].append(str(e))
    result["completed_at"] = datetime.now().isoformat()
    return result
