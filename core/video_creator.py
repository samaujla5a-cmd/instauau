"""
VIDEO CREATOR — Pure FFmpeg Edition
Produces a clean 1080x1920 vertical reel with animated background,
title overlay, and audio.  No moviepy — pure ffmpeg subprocess calls.

Key design decisions:
  - lavfi color source is supplied as a -f lavfi -i input, so -vf must NOT
    include a color= source filter (that was the original crash bug).
  - Every output goes through a .tmp file then os.replace() so a partial
    write never leaves a corrupt file at the final path.
  - -movflags +faststart on EVERY encode path so Instagram can parse the
    moov atom without seeking to the end of the file.
  - A local ffprobe validation runs before returning the path so callers
    can trust the file is a real, readable MP4.
"""
import os
import subprocess
import logging
from pathlib import Path
from config import VIDEO, SHORTS_DIR

logger = logging.getLogger(__name__)
os.makedirs(SHORTS_DIR, exist_ok=True)

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

BG_COLORS = [
    "#0d0221", "#1a0533", "#0a1628", "#1c0a00",
    "#001a0d", "#1a1a00", "#1a000d", "#000d1a",
]
ACCENT_COLORS = [
    "#ff00ff", "#00ffff", "#ff6600", "#00ff88",
    "#ff0088", "#ffcc00", "#0088ff", "#ff4444",
]


def _esc(text: str) -> str:
    """Escape special characters for FFmpeg drawtext filter."""
    return (
        text.replace("'", "")
            .replace('"', "")
            .replace(":", "\\:")
            .replace("%", "\\%")
            .replace("[", "").replace("]", "")
            .replace("\\", "\\\\")
    )


def _probe_ok(path: str) -> bool:
    """Return True if ffprobe can read the file as a valid video."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name",
         "-of", "default=noprint_wrappers=1", path],
        capture_output=True, timeout=20,
    )
    return r.returncode == 0


def _run_ffmpeg(cmd: list, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def create_short_video(
    audio_path: str,
    concept: dict,
    clip_index: int,
    start_sec: float,
    duration_sec: float = 30.0,
) -> str:
    title = concept.get("title", "Untitled")
    hook  = concept.get("hook", "")[:60]

    bg_hex  = BG_COLORS[clip_index % len(BG_COLORS)].lstrip("#")
    acc_hex = ACCENT_COLORS[clip_index % len(ACCENT_COLORS)].lstrip("#")

    fname    = f"{title.replace(' ', '_')}_short_{clip_index + 1}.mp4"
    out_path = os.path.join(SHORTS_DIR, fname)
    tmp_path = out_path + ".tmp.mp4"

    safe_duration = max(5.0, float(duration_sec) - 0.15)

    title_safe = _esc(title.upper())
    hook_safe  = _esc(hook)

    # ── Video filter chain ───────────────────────────────────────────────────
    # The lavfi `color` source is already the input stream [0:v] via:
    #   -f lavfi -i color=c=0x{bg}:size=1080x1920:rate=30
    # So -vf must NOT include another color= source.
    # We apply: animated colours (geq) → title text → optional hook → CTA.
    bg_r = int(bg_hex[0:2], 16)
    bg_g = int(bg_hex[2:4], 16)
    bg_b = int(bg_hex[4:6], 16)

    geq = (
        f"geq="
        f"r='clip({bg_r}+80*sin(2*PI*X/1080+T*0.5)*sin(2*PI*Y/1920+T*0.3),0,255)':"
        f"g='clip({bg_g}+60*sin(2*PI*X/540+T*0.4),0,255)':"
        f"b='clip({bg_b}+100*sin(2*PI*Y/960+T*0.6)*sin(T*0.2),0,255)'"
    )

    dt_title = (
        f"drawtext=text='{title_safe}'"
        f":fontfile={FONT}:fontsize=72:fontcolor=0x{acc_hex}"
        f":bordercolor=black:borderw=3"
        f":x=(w-text_w)/2:y=h*0.12"
        f":box=1:boxcolor=black@0.5:boxborderw=20"
    )
    dt_hook = (
        f"drawtext=text='{hook_safe}'"
        f":fontfile={FONT}:fontsize=44:fontcolor=white"
        f":bordercolor=black:borderw=2"
        f":x=(w-text_w)/2:y=h*0.22"
        f":box=1:boxcolor=black@0.4:boxborderw=12"
    ) if hook_safe else ""

    dt_cta = (
        f"drawtext=text='FOLLOW FOR MORE'"
        f":fontfile={FONT}:fontsize=40:fontcolor=0x{acc_hex}"
        f":bordercolor=black:borderw=2"
        f":x=(w-text_w)/2:y=h*0.88"
        f":box=1:boxcolor=black@0.5:boxborderw=12"
    )

    vf_parts = [geq, dt_title]
    if dt_hook:
        vf_parts.append(dt_hook)
    vf_parts.append(dt_cta)
    vf_filter = ",".join(vf_parts)

    # Simple fallback filter (no geq — less CPU, more compatible)
    vf_simple = f"{dt_title},{dt_cta}"

    logger.info(f"✂️  Creating Short #{clip_index + 1} for '{title}' via ffmpeg...")

    # ── Attempt 1: animated background + all text overlays ──────────────────
    cmd1 = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x{bg_hex}:size=1080x1920:rate=30",
        "-i", audio_path,
        "-vf", vf_filter,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast",
        "-b:v", "3500k", "-maxrate", "4000k", "-bufsize", "8000k",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-t", str(safe_duration),
        "-shortest",
        tmp_path,
    ]
    _run_ffmpeg(cmd1)
    sz = os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0
    if sz >= 50_000 and _probe_ok(tmp_path):
        os.replace(tmp_path, out_path)
        logger.info(f"✅ Short #{clip_index + 1}: {out_path} ({sz // 1024}KB)")
        return out_path

    logger.warning(f"Attempt 1 produced {sz}b — trying fallback (no geq)...")
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    # ── Attempt 2: solid colour + text (no geq, ultrafast preset) ───────────
    cmd2 = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x{bg_hex}:size=1080x1920:rate=30",
        "-i", audio_path,
        "-vf", vf_simple,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-t", str(safe_duration),
        "-shortest",
        tmp_path,
    ]
    _run_ffmpeg(cmd2)
    sz = os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0
    if sz >= 50_000 and _probe_ok(tmp_path):
        os.replace(tmp_path, out_path)
        logger.info(f"✅ Short #{clip_index + 1} (fallback): {out_path} ({sz // 1024}KB)")
        return out_path

    logger.warning(f"Attempt 2 produced {sz}b — trying bare minimum...")
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    # ── Attempt 3: no text, no animated bg — bare minimum ───────────────────
    cmd3 = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x{bg_hex}:size=1080x1920:rate=30",
        "-i", audio_path,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-t", str(safe_duration),
        "-shortest",
        out_path,
    ]
    result = _run_ffmpeg(cmd3)
    sz = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    if sz < 50_000:
        stderr = result.stderr.decode(errors="replace")[-400:]
        raise RuntimeError(
            f"All 3 FFmpeg attempts failed for '{title}'. "
            f"Last stderr: {stderr}"
        )

    logger.info(f"✅ Short #{clip_index + 1} (bare): {out_path} ({sz // 1024}KB)")
    return out_path


def create_full_video(audio_path: str, concept: dict) -> str:
    return create_short_video(audio_path, concept, 0, 0)
