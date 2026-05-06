"""
╔══════════════════════════════════════════════════════════╗
║         VIDEO CREATOR                                    ║
║         Psychedelic Visualizer | Full + Shorts          ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import random
import numpy as np
import logging
from pathlib import Path
from config import VIDEO, VIDEOS_DIR, SHORTS_DIR

logger = logging.getLogger(__name__)

try:
    from moviepy.editor import (
        AudioFileClip, VideoClip, CompositeVideoClip,
        TextClip, ColorClip, concatenate_videoclips
    )
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    import colorsys
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logger.warning("moviepy/PIL not installed. Run: pip install moviepy pillow numpy")


# ─────────────────────────────────────────────────────────
#  FULL VIDEO (1920x1080) for YouTube
# ─────────────────────────────────────────────────────────

def create_full_video(audio_path: str, concept: dict) -> str:
    """Create full 1920x1080 YouTube video with psychedelic visualizer."""
    if not MOVIEPY_AVAILABLE:
        raise ImportError("moviepy required. pip install moviepy pillow numpy")

    title = concept["title"]
    bg_color = random.choice(VIDEO["bg_colors"])
    accent = random.choice(VIDEO["accent_colors"])
    W, H = VIDEO["resolution"]
    fps = VIDEO["fps"]

    logger.info(f"🎬 Creating full video for '{title}'...")

    audio = AudioFileClip(audio_path)
    duration = audio.duration

    def make_frame(t):
        """Generate psychedelic visualizer frame."""
        img = Image.new("RGB", (W, H), _hex_to_rgb(bg_color))
        draw = ImageDraw.Draw(img)

        # Animated background gradient pulse
        pulse = 0.5 + 0.5 * np.sin(2 * np.pi * t * 0.3)
        _draw_smoke_bg(draw, W, H, t, bg_color, accent, pulse)

        # Waveform bars (pseudo-reactive)
        _draw_waveform_bars(draw, W, H, t, accent, pulse)

        # Floating particles
        _draw_particles(draw, W, H, t, accent)

        # Title text overlay
        _draw_title_overlay(img, title, W, H, accent)

        # Vignette
        img = _apply_vignette(img, W, H)

        return np.array(img)

    video = VideoClip(make_frame, duration=duration).set_fps(fps)
    video = video.set_audio(audio)

    out_path = os.path.join(VIDEOS_DIR, f"{title.replace(' ','_')}_full.mp4")
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    video.write_videofile(
        out_path, fps=fps, codec="libx264",
        audio_codec="aac", bitrate="8000k",
        ffmpeg_params=["-crf", "18"],
        logger=None
    )
    logger.info(f"✅ Full video: {out_path}")
    return out_path


# ─────────────────────────────────────────────────────────
#  SHORTS VIDEO (1080x1920) for YouTube Shorts + Reels
# ─────────────────────────────────────────────────────────

def create_short_video(audio_path: str, concept: dict, clip_index: int,
                       start_sec: float, duration_sec: float = 45.0) -> str:
    """Create a 9:16 vertical short from the best hook moments."""
    if not MOVIEPY_AVAILABLE:
        raise ImportError("moviepy required.")

    title = concept["title"]
    accent = VIDEO["accent_colors"][clip_index % len(VIDEO["accent_colors"])]
    bg_color = VIDEO["bg_colors"][clip_index % len(VIDEO["bg_colors"])]
    W, H = VIDEO["shorts_resolution"]  # 1080x1920

    logger.info(f"✂️  Creating Short #{clip_index+1} for '{title}'...")

    audio = AudioFileClip(audio_path).subclip(start_sec, start_sec + duration_sec)
    duration = audio.duration

    def make_frame(t):
        img = Image.new("RGB", (W, H), _hex_to_rgb(bg_color))
        draw = ImageDraw.Draw(img)

        pulse = 0.5 + 0.5 * np.sin(2 * np.pi * t * 0.4)
        _draw_smoke_bg(draw, W, H, t, bg_color, accent, pulse, scale=1.8)
        _draw_waveform_bars(draw, W, H, t, accent, pulse, vertical=True)
        _draw_particles(draw, W, H, t, accent, count=60)

        # Short-specific overlay: big hook text
        hook_lines = concept["hook"].split("\n")[:2]
        hook_text  = " / ".join(hook_lines)
        _draw_shorts_overlay(img, title, hook_text, W, H, accent, t)

        img = _apply_vignette(img, W, H, strength=0.6)
        return np.array(img)

    video = VideoClip(make_frame, duration=duration).set_fps(VIDEO["fps"])
    video = video.set_audio(audio)

    fname = f"{title.replace(' ','_')}_short_{clip_index+1}.mp4"
    out_path = os.path.join(SHORTS_DIR, fname)
    os.makedirs(SHORTS_DIR, exist_ok=True)
    video.write_videofile(
        out_path, fps=VIDEO["fps"], codec="libx264",
        audio_codec="aac", bitrate="5000k", logger=None,
        ffmpeg_params=["-movflags", "+faststart", "-pix_fmt", "yuv420p"]
    )
    logger.info(f"✅ Short #{clip_index+1}: {out_path}")
    return out_path


# ─── Drawing Helpers ──────────────────────────────────────

def _draw_smoke_bg(draw, W, H, t, bg_color, accent, pulse, scale=1.0):
    """Draw animated smoky background blobs (RGBA composited onto RGB base)."""
    n_blobs = 8
    r,g,b = _hex_to_rgb(accent)
    base = draw._image
    for i in range(n_blobs):
        angle  = (2 * np.pi * i / n_blobs) + t * 0.15
        radius = int((W * 0.25 + W * 0.1 * pulse) * scale)
        cx = int(W/2 + W * 0.3 * np.cos(angle) * scale)
        cy = int(H/2 + H * 0.25 * np.sin(angle * 1.3) * scale)
        alpha = int(30 + 20 * pulse)
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        ImageDraw.Draw(overlay).ellipse(
            [cx-radius, cy-radius, cx+radius, cy+radius], fill=(r, g, b, alpha))
        merged = Image.alpha_composite(base.convert("RGBA"), overlay)
        base.paste(merged.convert("RGB"))


def _draw_waveform_bars(draw, W, H, t, accent, pulse, vertical=False):
    """Pseudo audio-reactive waveform bars."""
    r,g,b = _hex_to_rgb(accent)
    n_bars = 64
    bar_w  = W // (n_bars * 2) if not vertical else (W // (n_bars // 2))

    for i in range(n_bars):
        wave = np.sin(i * 0.4 + t * 3) * 0.5 + 0.5
        wave += np.sin(i * 0.15 + t * 1.7) * 0.3
        wave = max(0.05, min(1.0, wave)) * pulse

        if not vertical:
            bar_h = int(H * 0.3 * wave)
            x = (W // n_bars) * i
            draw.rectangle([x, H//2 - bar_h, x + bar_w, H//2 + bar_h],
                           fill=(r, g, b))
        else:
            bar_h = int(W * 0.35 * wave)
            x = (W // n_bars) * i
            cy = H * 2 // 3
            draw.rectangle([x, cy - bar_h, x + bar_w, cy + bar_h],
                           fill=(r, g, b))


def _draw_particles(draw, W, H, t, accent, count=40):
    """Draw floating cosmic particles."""
    r,g,b = _hex_to_rgb(accent)
    np.random.seed(42)
    positions = np.random.rand(count, 2)
    for i, (px, py) in enumerate(positions):
        speed = 0.03 + i * 0.002
        fx = (px + t * speed) % 1.0
        fy = (py + t * speed * 0.7) % 1.0
        x, y = int(fx * W), int(fy * H)
        size = random.randint(2, 6)
        draw.ellipse([x-size, y-size, x+size, y+size], fill=(r, g, b))


def _draw_title_overlay(img, title, W, H, accent):
    """Draw song title at bottom."""
    draw = ImageDraw.Draw(img)
    r,g,b = _hex_to_rgb(accent)
    # Simple text (install ImageFont for custom fonts)
    font_size = max(36, W // 35)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        font = ImageFont.load_default()
    text = f"🎵 {title.upper()} 🎵"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2
    y = H - int(H * 0.1)
    # Shadow
    draw.text((x+3, y+3), text, font=font, fill=(0, 0, 0))
    draw.text((x, y),   text, font=font, fill=(r, g, b))


def _draw_shorts_overlay(img, title, hook, W, H, accent, t):
    """Draw short-optimized overlay with title + hook + progress bar."""
    draw = ImageDraw.Draw(img)
    r,g,b = _hex_to_rgb(accent)

    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except:
        font_big = font_med = ImageFont.load_default()

    # Title
    draw.text((60, 120), title.upper(), font=font_big, fill=(r, g, b))
    # Hook text
    hook_short = hook[:60] + "..." if len(hook) > 60 else hook
    draw.text((60, 220), hook_short, font=font_med, fill=(255, 255, 255))
    # Subscribe CTA
    draw.text((60, H - 180), "🔔 SUBSCRIBE FOR MORE", font=font_med, fill=(r, g, b))


def _apply_vignette(img, W, H, strength=0.5):
    """Apply dark vignette edges."""
    vignette = Image.new("L", (W, H), 255)
    draw = ImageDraw.Draw(vignette)
    for i in range(min(W, H) // 2):
        alpha = int(255 * (i / (min(W, H) / 2)) ** 0.5)
        draw.ellipse([i, i, W-i, H-i], fill=min(255, alpha + 100))
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=80))

    dark = Image.new("RGB", (W, H), (0, 0, 0))
    img  = Image.composite(img, dark, vignette)
    return img


def _hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
