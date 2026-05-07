"""
VIDEO CREATOR — Cinematic Rap Reels + Smart Song Trimmer
=========================================================
FIX: Replaced geq (per-pixel, ~15 min/clip on Railway) with fast
     drawbox pulsing border. geq was causing both Attempt 1 AND 2
     to silently timeout, falling to bare Attempt 3 (no text at all).
"""

import os
import subprocess
import logging
import re
from pathlib import Path
from config import VIDEO, SHORTS_DIR, VIDEOS_DIR

logger = logging.getLogger(__name__)
os.makedirs(SHORTS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

PALETTES = [
    ("#0a0010", "#ff00ff"),
    ("#000d1a", "#00e5ff"),
    ("#0d0000", "#ff4500"),
    ("#000a00", "#39ff14"),
    ("#1a0a00", "#ffcc00"),
]


def _run(cmd, timeout=600):
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def _probe_ok(path):
    r = _run(["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=codec_name",
               "-of", "default=noprint_wrappers=1", path], timeout=20)
    return r.returncode == 0


def _duration(audio_path):
    r = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", audio_path], timeout=15)
    if r.returncode == 0:
        try:
            return float(r.stdout.decode().strip())
        except ValueError:
            pass
    return 30.0


def _esc(t):
    return (t.replace("'", "").replace('"', "").replace(":", "\\:")
             .replace("%", "\\%").replace("[", "").replace("]", "")
             .replace("\\", "\\\\"))


def _safe(t, maxlen=35):
    return re.sub(r"[^A-Za-z0-9 ]", "", t)[:maxlen]


def _detect_hook_timestamps(audio_path, duration, n_clips=4):
    clip_len   = min(55, max(30, duration / (n_clips + 1)))
    step       = duration / (n_clips + 2)
    candidates = []
    for i in range(n_clips + 3):
        start = 5 + i * step
        end   = start + clip_len
        if end > duration - 2:
            break
        candidates.append((start, end))

    scored = []
    for start, end in candidates:
        r = _run(["ffmpeg", "-ss", str(start), "-t", str(clip_len),
                  "-i", audio_path, "-af", "volumedetect", "-f", "null", "-"], timeout=30)
        output = r.stderr.decode(errors="replace")
        m = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", output)
        scored.append((float(m.group(1)) if m else -99.0, start, end))

    scored.sort(reverse=True)
    chosen = sorted(scored[:n_clips], key=lambda x: x[1])
    result = [(round(s, 1), round(min(e, duration - 0.5), 1)) for _, s, e in chosen]
    logger.info(f"  Hook timestamps: {result}")
    return result


def _build_lyric_drawtext(timestamps, palette_idx, clip_start=0.0):
    if not timestamps:
        return ""
    _, accent = PALETTES[palette_idx % len(PALETTES)]
    acc = accent.lstrip("#")
    filters = []
    for item in timestamps[:40]:
        t = float(item.get("time", 0)) - clip_start
        if t < 0:
            continue
        text = _esc(_safe(str(item.get("text", "")), 45))
        if not text:
            continue
        filters.append(
            f"drawtext=text='{text}'"
            f":fontfile={FONT}:fontsize=56:fontcolor=0x{acc}"
            f":bordercolor=black:borderw=3"
            f":x=(w-text_w)/2:y=h*0.72"
            f":box=1:boxcolor=black@0.55:boxborderw=14"
            f":enable='between(t,{t:.2f},{t+2.5:.2f})'"
        )
    return ",".join(filters)


def _build_video(audio_path, out_path, title, hook, palette_idx,
                 duration, lyric_drawtext="", start_sec=0.0):
    """
    Build a 1080x1920 reel. Uses fast drawbox animation instead of geq.
    geq was 10-20 min per clip on Railway -> always timed out silently.
    drawbox is near-zero CPU overhead.
    """
    tmp_path           = out_path + ".tmp.mp4"
    bg_hex, accent_hex = PALETTES[palette_idx % len(PALETTES)]
    bg  = bg_hex.lstrip("#")
    acc = accent_hex.lstrip("#")

    title_safe = _esc(_safe(title.upper(), 28))
    hook_safe  = _esc(_safe(hook, 40))
    safe_dur   = max(5.0, duration - 0.2)

    # Fast animated border — pulses every second (CPU cost ~0 vs geq ~100%)
    dt_border = (
        f"drawbox=x=0:y=0:w=iw:h=8:color=0x{acc}@0.95:t=fill"
        f":enable='between(mod(t\\,1.0)\\,0\\,0.5)',"
        f"drawbox=x=0:y=ih-8:w=iw:h=8:color=0x{acc}@0.95:t=fill"
        f":enable='between(mod(t\\,1.0)\\,0\\,0.5)'"
    )

    dt_title = (
        f"drawtext=text='{title_safe}'"
        f":fontfile={FONT}:fontsize=68:fontcolor=0x{acc}"
        f":bordercolor=black:borderw=4"
        f":x=(w-text_w)/2:y=h*0.08"
        f":box=1:boxcolor=black@0.6:boxborderw=18"
    )

    dt_hook = (
        f"drawtext=text='{hook_safe}'"
        f":fontfile={FONT}:fontsize=40:fontcolor=white"
        f":bordercolor=black:borderw=2"
        f":x=(w-text_w)/2:y=h*0.20"
        f":box=1:boxcolor=black@0.4:boxborderw=10"
    ) if hook_safe else ""

    dt_cta = (
        f"drawtext=text='FOLLOW FOR MORE'"
        f":fontfile={FONT}:fontsize=38:fontcolor=0x{acc}"
        f":bordercolor=black:borderw=2"
        f":x=(w-text_w)/2:y=h*0.91"
        f":box=1:boxcolor=black@0.5:boxborderw=10"
    )

    def _vf_full():
        parts = [dt_border, dt_title]
        if dt_hook:
            parts.append(dt_hook)
        if lyric_drawtext:
            parts.append(lyric_drawtext)
        parts.append(dt_cta)
        return ",".join(parts)

    def _vf_simple():
        parts = [dt_border, dt_title, dt_cta]
        return ",".join(parts)

    def _cmd(vf, preset, output):
        return [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=0x{bg}:size=1080x1920:rate=30",
            "-ss", str(start_sec), "-i", audio_path,
            "-map", "0:v", "-map", "1:a",
            "-vf", vf,
            "-c:v", "libx264", "-preset", preset,
            "-b:v", "3500k", "-maxrate", "4500k", "-bufsize", "9000k",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-t", str(safe_dur),
            "-shortest",
            output,
        ]

    def _try(vf, preset, output):
        _run(_cmd(vf, preset, output), timeout=300)
        sz = Path(output).stat().st_size if Path(output).exists() else 0
        if sz < 50_000 or not _probe_ok(output):
            if Path(output).exists():
                os.remove(output)
            return 0
        return sz

    # Attempt 1: full overlays + synced lyrics
    sz = _try(_vf_full(), "fast", tmp_path)
    if sz:
        os.replace(tmp_path, out_path)
        logger.info(f"  ✅ Video: {out_path} ({sz // 1024}KB)")
        return out_path

    # Attempt 2: title + border, no lyrics
    sz = _try(_vf_simple(), "fast", tmp_path)
    if sz:
        os.replace(tmp_path, out_path)
        logger.info(f"  ✅ Video (no lyrics): {out_path} ({sz // 1024}KB)")
        return out_path

    # Attempt 3: ultrafast bare minimum
    bare = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x{bg}:size=1080x1920:rate=30",
        "-ss", str(start_sec), "-i", audio_path,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-t", str(safe_dur),
        "-shortest",
        out_path,
    ]
    r  = _run(bare, timeout=300)
    sz = Path(out_path).stat().st_size if Path(out_path).exists() else 0
    if sz < 50_000:
        raise RuntimeError(
            f"All 3 FFmpeg attempts failed.\n"
            f"Stderr: {r.stderr.decode(errors='replace')[-500:]}"
        )
    logger.info(f"  ✅ Video (bare): {out_path} ({sz // 1024}KB)")
    return out_path


# ── PUBLIC API ─────────────────────────────────────────────────────────────────

def create_full_video(audio_path, concept):
    title    = concept.get("title", "Untitled")
    hook     = concept.get("hook", "")[:60]
    duration = _duration(audio_path)
    out_path = str(Path(VIDEOS_DIR) / f"{_safe(title)}_full.mp4")
    lts      = concept.get("lyric_timestamps", [])
    logger.info(f"🎬 Building full video: '{title}' ({duration:.0f}s)")
    return _build_video(audio_path, out_path, title, hook, 0, duration,
                        _build_lyric_drawtext(lts, 0), 0.0)


def create_reel_clips(audio_path, concept, n_clips=4):
    title    = concept.get("title", "Untitled")
    hook     = concept.get("hook", "")[:60]
    duration = _duration(audio_path)
    lts      = concept.get("lyric_timestamps", [])
    logger.info(f"✂️  Smart-trimming '{title}' into {n_clips} reels...")
    timestamps = _detect_hook_timestamps(audio_path, duration, n_clips)

    paths = []
    for i, (start, end) in enumerate(timestamps):
        clip_dur  = end - start
        out_path  = str(Path(SHORTS_DIR) / f"{_safe(title)}_reel_{i+1}.mp4")
        palette   = i % len(PALETTES)
        clip_lts  = [x for x in lts if start <= float(x.get("time", 0)) <= end]
        ly_filter = _build_lyric_drawtext(clip_lts, palette, clip_start=start)
        logger.info(f"  Clip {i+1}: {start:.0f}s–{end:.0f}s ({clip_dur:.0f}s)")
        try:
            p = _build_video(audio_path, out_path, title, hook, palette,
                             clip_dur, ly_filter, start_sec=start)
            paths.append(p)
        except Exception as e:
            logger.error(f"  ❌ Clip {i+1} failed: {e}")

    logger.info(f"  ✅ Created {len(paths)}/{n_clips} reel clips")
    return paths


def create_short_video(audio_path, concept, clip_index, start_sec, duration_sec=45.0):
    """Legacy compat."""
    title    = concept.get("title", "Untitled")
    hook     = concept.get("hook", "")[:60]
    out_path = str(Path(SHORTS_DIR) / f"{_safe(title)}_short_{clip_index + 1}.mp4")
    lts      = concept.get("lyric_timestamps", [])
    clip_lts = [x for x in lts if start_sec <= float(x.get("time", 0)) <= start_sec + duration_sec]
    ly_filter = _build_lyric_drawtext(clip_lts, clip_index, clip_start=start_sec)
    return _build_video(audio_path, out_path, title, hook, clip_index,
                        duration_sec, ly_filter, start_sec)
