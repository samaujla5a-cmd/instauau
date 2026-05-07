"""
BRAINROT PIPELINE — Subway + Minecraft split screen
"""
import asyncio, os, re, json, random, logging, subprocess
from pathlib import Path
from datetime import datetime
from core.gemini_client import gemini

logger    = logging.getLogger("BRAINROT")
BASE_DIR  = Path(__file__).parent.parent
BRAIN_DIR = BASE_DIR / "output" / "brainrot"
BRAIN_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = BASE_DIR / "assets"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

VIRAL_TOPICS = [
    "sigma male rules nobody talks about",
    "things that hit different at 3am",
    "facts that sound fake but are real",
    "mind blowing facts about space",
    "dark psychology tricks that actually work",
    "things you did not know about your brain",
    "life hacks that actually work",
    "facts about money nobody teaches you",
    "things that will make you question reality",
    "unwritten rules of life",
    "things that are lowkey illegal",
    "facts gen z will never understand",
]


def generate_viral_text() -> dict:
    topic = random.choice(VIRAL_TOPICS)
    prompt = f"""Generate viral brainrot Instagram content about: "{topic}"
Return ONLY valid JSON, no markdown:
{{
    "hook": "SHORT hook max 6 words ALL CAPS no apostrophes",
    "points": ["point 1 max 8 words", "point 2 max 8 words", "point 3 max 8 words"],
    "caption": "Instagram caption with emojis 150 chars max",
    "hashtags": ["#brainrot", "#viral", "#fyp", "#facts", "#mindblown"]
}}"""
    raw = re.sub(r"```json|```", "", gemini(prompt)).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Brainrot JSON parse failed — using safe defaults")
        data = {
            "hook": topic.upper()[:40],
            "points": [
                "This will blow your mind completely",
                "Nobody talks about this ever",
                "Share this with your friends now",
            ],
            "caption": f"Mind blowing facts 🤯 {topic} #viral",
            "hashtags": ["#brainrot", "#viral", "#fyp", "#facts", "#mindblown"],
        }
    data["topic"] = topic
    logger.info(f"Generated brainrot topic: {topic}")
    return data


async def _tts(text: str, path: str) -> None:
    import edge_tts
    await edge_tts.Communicate(text, "en-US-GuyNeural", rate="+15%").save(path)


def generate_voiceover(hook: str, points: list, session: str) -> str | None:
    try:
        voice_text = hook + ". " + ". ".join(points[:3])
        path = str(BRAIN_DIR / f"voice_{session}.mp3")
        asyncio.run(_tts(voice_text, path))
        logger.info(f"✅ Voiceover: {path}")
        return path
    except Exception as e:
        logger.warning(f"TTS failed: {e}")
        return None


def _safe_text(t: str) -> str:
    return re.sub(r"[^A-Za-z0-9 ]", "", t)[:40].upper()


def _file_ok(path: str) -> bool:
    p = Path(path)
    return p.exists() and p.stat().st_size > 50_000


def _probe_ok(path: str) -> bool:
    """Confirm file is a valid MP4 with a video stream."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name",
         "-of", "default=noprint_wrappers=1", path],
        capture_output=True, timeout=20,
    )
    return r.returncode == 0


def _ffmpeg(cmd: list, timeout: int = 300) -> str:
    r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    return r.stderr.decode(errors="replace")


def create_split_screen_video(content: dict, duration: int = 45) -> str:
    session     = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path    = str(BRAIN_DIR / f"brainrot_{session}.mp4")
    tmp_path    = out_path + ".tmp.mp4"
    top_clip    = str(ASSETS_DIR / "subway.mp4")
    bottom_clip = str(ASSETS_DIR / "minecraft.mp4")

    # ── Asset check — fail fast with a clear message ─────────────────────────
    missing = [p for p in [top_clip, bottom_clip] if not os.path.exists(p)]
    if missing:
        raise FileNotFoundError(
            f"Missing brainrot asset files: {missing}\n"
            "Add subway.mp4 and minecraft.mp4 to the assets/ folder in your repo."
        )

    hook_safe  = _safe_text(content.get("hook", "MIND BLOWING FACTS"))
    voice_path = generate_voiceover(
        content.get("hook", ""), content.get("points", []), session)

    logger.info("Creating split screen video...")

    # ── Attempt 1: split screen + drawtext + audio ───────────────────────────
    # FIX: -t BEFORE -i forces FFmpeg to cut inputs at duration before passing
    # them into filter_complex. Without this, -stream_loop + vstack deadlocks
    # because FFmpeg waits for both infinite streams to end before flushing,
    # producing 0 frames output (the frame=0 / time=N/A symptom seen in logs).
    # IMPORTANT: -movflags +faststart on EVERY attempt — without it the moov
    # atom lands at the end and Instagram rejects with "ftyp box not found".
    filter_v1 = (
        f"[0:v]scale=1080:960,setsar=1[top];"
        f"[1:v]scale=1080:960,setsar=1[bot];"
        f"[top][bot]vstack=inputs=2[stk];"
        f"[stk]drawtext=text='{hook_safe}'"
        f":fontfile={FONT}:fontsize=60:fontcolor=yellow"
        f":bordercolor=black:borderw=3"
        f":x=(w-text_w)/2:y=50"
        f":box=1:boxcolor=black@0.5:boxborderw=10[out]"
    )
    cmd1 = [
        "ffmpeg", "-y",
        # -t before -i: pre-trim each looped input to exactly <duration> sec
        "-stream_loop", "-1", "-t", str(duration), "-i", top_clip,
        "-stream_loop", "-1", "-t", str(duration), "-i", bottom_clip,
    ]
    if voice_path:
        cmd1 += ["-i", voice_path]
    cmd1 += ["-filter_complex", filter_v1, "-map", "[out]"]
    if voice_path:
        cmd1 += ["-map", "2:a", "-c:a", "aac", "-b:a", "128k"]
    else:
        cmd1 += ["-an"]
    cmd1 += [
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        tmp_path,
    ]
    err = _ffmpeg(cmd1)
    sz  = Path(tmp_path).stat().st_size if Path(tmp_path).exists() else 0
    if sz >= 50_000 and _probe_ok(tmp_path):
        os.replace(tmp_path, out_path)
        logger.info(f"✅ Split screen created: {out_path}")
        return out_path

    logger.error(f"Attempt 1 produced {sz}b stderr: {err[-400:]}")
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    # ── Attempt 2: split screen, NO drawtext ────────────────────────────────
    filter_v2 = (
        f"[0:v]scale=1080:960,setsar=1[top];"
        f"[1:v]scale=1080:960,setsar=1[bot];"
        f"[top][bot]vstack=inputs=2[out]"
    )
    cmd2 = [
        "ffmpeg", "-y",
        # -t before -i here too
        "-stream_loop", "-1", "-t", str(duration), "-i", top_clip,
        "-stream_loop", "-1", "-t", str(duration), "-i", bottom_clip,
    ]
    if voice_path:
        cmd2 += ["-i", voice_path]
    cmd2 += ["-filter_complex", filter_v2, "-map", "[out]"]
    if voice_path:
        cmd2 += ["-map", "2:a", "-c:a", "aac", "-b:a", "128k"]
    else:
        cmd2 += ["-an"]
    cmd2 += [
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        tmp_path,
    ]
    err = _ffmpeg(cmd2)
    sz  = Path(tmp_path).stat().st_size if Path(tmp_path).exists() else 0
    if sz >= 50_000 and _probe_ok(tmp_path):
        os.replace(tmp_path, out_path)
        logger.info(f"✅ Split screen (no text): {out_path}")
        return out_path

    logger.error(f"Attempt 2 produced {sz}b stderr: {err[-400:]}")
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    # ── Attempt 3: single clip full screen ───────────────────────────────────
    cmd3 = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", top_clip]
    if voice_path:
        cmd3 += ["-i", voice_path, "-map", "0:v", "-map", "1:a",
                 "-c:a", "aac", "-b:a", "128k"]
    else:
        cmd3 += ["-map", "0:v", "-an"]
    cmd3 += [
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        out_path,
    ]
    err = _ffmpeg(cmd3)
    sz  = Path(out_path).stat().st_size if Path(out_path).exists() else 0
    if sz < 50_000:
        raise RuntimeError(
            f"All 3 brainrot FFmpeg attempts failed. Last stderr: {err[-400:]}"
        )
    logger.info(f"✅ Single-clip fallback: {out_path} ({sz // 1024}KB)")
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
        content            = generate_viral_text()
        result["topic"]    = content.get("topic")
        result["title"]    = content.get("topic", "Brainrot")
        result["caption"]  = content.get("caption")
        result["hashtags"] = content.get("hashtags", [])
        result["video_path"] = create_split_screen_video(content)
        logger.info(f"Brainrot video ready: {result['video_path']}")
    except Exception as e:
        logger.error(f"Brainrot pipeline failed: {e}", exc_info=True)
        result["errors"].append(str(e))
    result["completed_at"] = datetime.now().isoformat()
    return result
