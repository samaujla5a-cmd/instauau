"""
VIDEO CREATOR — Pure FFmpeg Edition
Replaces moviepy frame generator (too heavy for Railway) with direct ffmpeg calls.
Produces a clean 1080x1920 vertical reel with title overlay + audio.
"""
import os
import subprocess
import logging
from pathlib import Path
from config import VIDEO, SHORTS_DIR

logger = logging.getLogger(__name__)
os.makedirs(SHORTS_DIR, exist_ok=True)

BG_COLORS = [
    "#0d0221", "#1a0533", "#0a1628", "#1c0a00",
    "#001a0d", "#1a1a00", "#1a000d", "#000d1a",
]
ACCENT_COLORS = [
    "#ff00ff", "#00ffff", "#ff6600", "#00ff88",
    "#ff0088", "#ffcc00", "#0088ff", "#ff4444",
]


def create_short_video(audio_path: str, concept: dict, clip_index: int,
                       start_sec: float, duration_sec: float = 30.0) -> str:
    title     = concept.get("title", "Untitled")
    hook      = concept.get("hook", "")[:60]
    bg_hex    = BG_COLORS[clip_index % len(BG_COLORS)].lstrip("#")
    acc_hex   = ACCENT_COLORS[clip_index % len(ACCENT_COLORS)].lstrip("#")

    fname    = f"{title.replace(' ','_')}_short_{clip_index+1}.mp4"
    out_path = os.path.join(SHORTS_DIR, fname)

    safe_duration = max(5.0, float(duration_sec) - 0.15)

    def _esc(t):
        return (t.replace("'", "")
                 .replace('"', "")
                 .replace(":", "\\:")
                 .replace("%", "\\%")
                 .replace("[", "").replace("]", ""))

    title_safe = _esc(title.upper())
    hook_safe  = _esc(hook)
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    vf_bg = (
        f"color=c=0x{bg_hex}:size=1080x1920:rate=30,"
        f"geq="
        f"r='clip({int(bg_hex[0:2],16)}+80*sin(2*PI*X/1080+T*0.5)*sin(2*PI*Y/1920+T*0.3),0,255)':"
        f"g='clip({int(bg_hex[2:4],16)}+60*sin(2*PI*X/540+T*0.4),0,255)':"
        f"b='clip({int(bg_hex[4:6],16)}+100*sin(2*PI*Y/960+T*0.6)*sin(T*0.2),0,255)'"
    )

    drawtext_title = (
        f"drawtext=text='{title_safe}'"
        f":fontfile={font}:fontsize=72:fontcolor=0x{acc_hex}"
        f":bordercolor=black:borderw=3"
        f":x=(w-text_w)/2:y=h*0.12"
        f":box=1:boxcolor=black@0.5:boxborderw=20"
    )
    drawtext_hook = (
        f"drawtext=text='{hook_safe}'"
        f":fontfile={font}:fontsize=44:fontcolor=white"
        f":bordercolor=black:borderw=2"
        f":x=(w-text_w)/2:y=h*0.22"
        f":box=1:boxcolor=black@0.4:boxborderw=12"
    ) if hook_safe else ""

    drawtext_sub = (
        f"drawtext=text='FOLLOW FOR MORE'"
        f":fontfile={font}:fontsize=40:fontcolor=0x{acc_hex}"
        f":bordercolor=black:borderw=2"
        f":x=(w-text_w)/2:y=h*0.88"
        f":box=1:boxcolor=black@0.5:boxborderw=12"
    )

    vf_parts = [vf_bg, drawtext_title]
    if drawtext_hook:
        vf_parts.append(drawtext_hook)
    vf_parts.append(drawtext_sub)
    vf_filter = ",".join(vf_parts)

    logger.info(f"✂️  Creating Short #{clip_index+1} for '{title}' via ffmpeg...")

    cmd = [
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
        out_path
    ]

    result = subprocess.run(cmd, capture_output=True, timeout=300)
    file_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0

    if file_size < 50_000:
        logger.error(f"FFmpeg failed (file={file_size}b): {result.stderr.decode()[-500:]}")
        if os.path.exists(out_path):
            os.remove(out_path)
        fallback = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=0x{bg_hex}:size=1080x1920:rate=30",
            "-i", audio_path,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-t", str(safe_duration),
            "-shortest",
            out_path
        ]
        subprocess.run(fallback, capture_output=True, timeout=120)
        file_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0

    logger.info(f"✅ Short #{clip_index+1}: {out_path} ({file_size//1024}KB)")
    return out_path


def create_full_video(audio_path: str, concept: dict) -> str:
    return create_short_video(audio_path, concept, 0, 0)
