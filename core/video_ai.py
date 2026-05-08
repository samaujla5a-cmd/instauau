"""
AI VIDEO GENERATOR — Hugging Face Spaces (100% FREE, No Card)
Real AI video movement. NO zoomed photo fallbacks.
"""
import os, time, json, logging, subprocess, requests, shutil
from pathlib import Path
from core.frame_builder import create_model_overlay

logger = logging.getLogger("VIDEO_AI")

def _cleanup(*paths):
    for p in paths:
        try:
            if Path(p).exists(): os.remove(p)
        except: pass

def _download(url, path):
    r = requests.get(url, timeout=180, stream=True)
    r.raise_for_status()
    with open(path, "wb") as f:
        for c in r.iter_content(65536): f.write(c)
    sz = Path(path).stat().st_size // 1024
    if sz < 20: raise RuntimeError(f"File too small ({sz}KB)")
    logger.info(f"  ✅ Downloaded: {path} ({sz}KB)")
    return path

def _loop_video(input_path, output_path, target_duration):
    tmp = output_path + ".tmp.mp4"
    cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", input_path, "-t", str(target_duration),
           "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920", "-an", tmp]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    sz = Path(tmp).stat().st_size if Path(tmp).exists() else 0
    if sz >= 50_000:
        os.replace(tmp, output_path); _cleanup(input_path)
        logger.info(f"  ✅ Looped to {target_duration}s: {output_path} ({sz//1024}KB)")
        return output_path
    shutil.copy2(input_path, output_path); _cleanup(tmp); return output_path

def _parse_hf_result(result):
    if isinstance(result, str):
        if Path(result).exists(): return result
        if result.startswith("http"): return result
    elif isinstance(result, tuple) or isinstance(result, list):
        for item in result:
            if isinstance(item, str):
                if Path(item).exists(): return item
                if item.startswith("http"): return item
            elif isinstance(item, dict):
                url = item.get("url") or item.get("video")
                if url and isinstance(url, str): return url
    return None

def _download_if_url(path_or_url, local_path):
    if path_or_url.startswith("http"):
        return _download(path_or_url, local_path)
    if Path(path_or_url).exists() and path_or_url != local_path:
        shutil.move(path_or_url, local_path)
    return local_path

# ═══════════════════════════════════════════════════════════
#  METHOD 1: CogVideoX
# ═══════════════════════════════════════════════════════════

def _cogvideox(image_path, prompt):
    logger.info("  🎬 Trying CogVideoX (free)...")
    try:
        from gradio_client import Client, handle_file
        spaces = ["THUDM/CogVideoX-5B-Space", "THUDM/CogVideoX-2B-Space"]
        for space in spaces:
            try:
                client = Client(space, verbose=False)
                # Auto-detect API name
                api_name = None
                try:
                    apis = client.view_api()
                    if hasattr(apis, 'named_endpoints') and apis.named_endpoints:
                        for name in apis.named_endpoints:
                            if any(k in name.lower() for k in ['predict','generate','run','video']): api_name=name; break
                        if not api_name: api_name = list(apis.named_endpoints.keys())[0]
                except: api_name = "/predict"
                
                job = client.submit(image=handle_file(image_path), prompt=prompt[:500], api_name=api_name)
                result = job.result(timeout=300)
                vid = _parse_hf_result(result)
                if vid: return vid
            except Exception as e:
                logger.warning(f"  {space} failed: {e}")
                continue
    except ImportError: logger.warning("  gradio_client not installed")
    except Exception as e: logger.warning(f"  CogVideoX error: {e}")
    return None

# ═══════════════════════════════════════════════════════════
#  METHOD 2: Stable Video Diffusion
# ═══════════════════════════════════════════════════════════

def _svd_hf(image_path, motion=6):
    logger.info("  🎬 Trying SVD (free)...")
    try:
        from gradio_client import Client, handle_file
        spaces = ["stabilityai/stable-video-diffusion", "multimodalart/stable-video-diffusion"]
        for space in spaces:
            try:
                client = Client(space, verbose=False)
                job = client.submit(image=handle_file(image_path), seed=42, motion_bucket_id=motion, fps_id=6, noise_aug_strength=0.1, decoding_t=7, api_name="/animate")
                result = job.result(timeout=300)
                vid = _parse_hf_result(result)
                if vid: return vid
            except Exception as e:
                logger.warning(f"  {space} failed: {e}")
                continue
    except ImportError: pass
    except Exception as e: logger.warning(f"  SVD error: {e}")
    return None

# ═══════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════

def generate_video_from_image(image_path, prompt, duration=5, aspect_ratio="9:16", output_path="", loop_duration=0):
    if not output_path: output_path = str(Path("output") / "ai_video_temp.mp4")
    logger.info(f"  🎬 Generating AI video (100% FREE via Hugging Face)...")
    
    raw_path = output_path.replace(".mp4", "_raw.mp4")
    video_src = None

    # 1. CogVideoX
    try:
        video_src = _cogvideox(image_path, prompt)
        if video_src: _download_if_url(video_src, raw_path)
    except Exception as e: logger.warning(f"  CogVideoX failed: {e}")

    # 2. SVD
    if not Path(raw_path).exists() or Path(raw_path).stat().st_size < 10000:
        try:
            video_src = _svd_hf(image_path, motion=6)
            if video_src: _download_if_url(video_src, raw_path)
        except Exception as e: logger.warning(f"  SVD failed: {e}")

    if not Path(raw_path).exists() or Path(raw_path).stat().st_size < 10000:
        raise RuntimeError("All Hugging Face video models failed. Servers might be busy. Pipeline stopped.")

    if loop_duration > 0:
        looped_path = output_path.replace(".mp4", "_looped.mp4")
        return _loop_video(raw_path, looped_path, loop_duration)
    
    if raw_path != output_path: shutil.move(raw_path, output_path)
    return output_path
