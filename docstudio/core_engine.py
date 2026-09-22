"""
core_engine.py — Clean documentary engine inspired by the user's reference script.

Key upgrades over raw script:
  - Uses DocStudio's shared Gemini client (no user API key needed separately)
  - Pollinations AI as FREE image fallback when Pexels/Pixabay fail
  - Ken Burns zoom perfectly matched to audio duration (no black frames)
  - Drops into existing pipeline as Stage 3b (image generation) + Stage 5b (Ken Burns render)
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

import requests

# ─── DocStudio shared config (no separate API key needed) ─────────────────────
from docstudio.config import GEMINI_API_KEY, DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FPS

# ─── Gemini client (shared, same key as rest of DocStudio) ────────────────────
def _get_gemini_client():
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        return None


# ─── Pollinations.ai — FREE image generation, no API key needed ──────────────
def fetch_pollinations_image(
    prompt: str,
    dest: Path,
    width: int = None,
    height: int = None,
    max_retries: int = 5,
) -> bool:
    """
    Downloads a free AI-generated image from Pollinations.ai.
    Used as fallback when Pexels/Pixabay return no results.
    Includes exponential backoff with jitter to handle 429 rate-limits.
    """
    w = width or DEFAULT_WIDTH
    h = height or DEFAULT_HEIGHT
    encoded = urllib.parse.quote(prompt[:400])
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={w}&height={h}&nologo=true&seed={abs(hash(prompt)) % 99999}"
    )
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 1000:
                dest.write_bytes(resp.content)
                return True
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 0))
                wait = retry_after if retry_after > 0 else (2 ** attempt + random.uniform(0, 2))
                print(f"[Pollinations] 429 rate-limit — waiting {wait:.1f}s (attempt {attempt}/{max_retries})")
                time.sleep(wait)
                continue
            # Non-retryable HTTP error
            print(f"[Pollinations] HTTP {resp.status_code} — giving up")
            return False
        except requests.exceptions.Timeout:
            wait = 2 ** attempt + random.uniform(0, 1)
            print(f"[Pollinations] Timeout on attempt {attempt}/{max_retries}, retrying in {wait:.1f}s...")
            time.sleep(wait)
        except Exception as e:
            print(f"[Pollinations] Failed: {e}")
            return False
    print(f"[Pollinations] All {max_retries} attempts exhausted — giving up")
    return False


# ─── Ken Burns zoom — perfectly matched to audio duration ────────────────────
def render_ken_burns(
    image_path: Path,
    audio_path: Path,
    output_path: Path,
    duration: float,
    motion: str = "zoom_in",
    width: int = None,
    height: int = None,
    fps: int = None,
) -> bool:
    """
    Renders a single scene clip with smooth Ken Burns motion matched EXACTLY
    to the narration audio duration. Zero black frames, no audio/video desync.

    motion options: zoom_in | zoom_out | pan_left | pan_right | subtle_drift
    """
    w = width or DEFAULT_WIDTH
    h = height or DEFAULT_HEIGHT
    f = fps or DEFAULT_FPS
    total_frames = max(1, int(duration * f))

    # Motion presets — all produce exactly `duration` seconds
    MOTIONS = {
        "zoom_in": (
            f"scale=8000:-1,"
            f"zoompan=z='min(zoom+0.0015,1.5)':d={total_frames}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={f}"
        ),
        "zoom_out": (
            f"scale=8000:-1,"
            f"zoompan=z='if(eq(on,1),1.5,max(zoom-0.0015,1.0))':d={total_frames}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={f}"
        ),
        "pan_left": (
            f"scale=8000:-1,"
            f"zoompan=z='1.2':d={total_frames}"
            f":x='iw/zoom/2+({total_frames}-on)*((iw-iw/zoom)/{total_frames})'"
            f":y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={f}"
        ),
        "pan_right": (
            f"scale=8000:-1,"
            f"zoompan=z='1.2':d={total_frames}"
            f":x='on*((iw-iw/zoom)/{total_frames})'"
            f":y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={f}"
        ),
        "subtle_drift": (
            f"scale=8000:-1,"
            f"zoompan=z='1.05+0.0005*on':d={total_frames}"
            f":x='iw/2-(iw/zoom/2)+sin(on/30)*5':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={f}"
        ),
        "zoom_punch": (
            f"scale=8000:-1,"
            f"zoompan=z='if(lt(on,{int(total_frames*0.1)}),1.0+0.01*on,min(zoom+0.0008,1.3))'"
            f":d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={f}"
        ),
    }

    vf = MOTIONS.get(motion, MOTIONS["zoom_in"])

    if audio_path and Path(audio_path).exists():
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(image_path),
            "-i", str(audio_path),
            "-filter_complex", f"[0:v]{vf}[v]",
            "-map", "[v]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",           # clip ends when audio ends — no black frames
            str(output_path)
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(image_path),
            "-filter_complex", f"[0:v]{vf}[v]",
            "-map", "[v]",
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            str(output_path)
        ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path.exists() and output_path.stat().st_size > 0
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode("utf-8", errors="replace")[-500:] if e.stderr else str(e)
        print(f"[KenBurns] FFmpeg error: {err_msg}")
        return False


# ─── Audio duration helper ────────────────────────────────────────────────────
def get_audio_duration(audio_path: Path) -> float:
    """Returns exact duration of an audio file in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ]
        result = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        return float(result)
    except Exception:
        return 5.0  # safe fallback


# ─── Gemini-powered script generator (uses DocStudio's shared key) ────────────
KIDS_SYSTEM_PROMPT = """
You are a documentary producer. Given a topic, output a valid JSON list of scenes.
Format:
[
  {
    "scene_num": 1,
    "narration": "Vivid, dramatic narration text here.",
    "image_prompt": "Cinematic description for image generation, photorealistic, dramatic lighting, 35mm film",
    "motion": "zoom_in"
  }
]
motion must be one of: zoom_in, zoom_out, pan_left, pan_right, subtle_drift, zoom_punch
Output ONLY raw JSON, no markdown, no code blocks.
"""

def generate_script_via_gemini(topic: str, num_scenes: int = 6) -> list[dict]:
    """
    Generates a scene-by-scene script using DocStudio's Gemini client.
    Falls back to a minimal placeholder if Gemini is unavailable.
    """
    client = _get_gemini_client()
    if not client:
        # Minimal fallback so pipeline doesn't crash
        return [
            {
                "scene_num": i + 1,
                "narration": f"Scene {i+1} of {topic}.",
                "image_prompt": f"Cinematic scene about {topic}, dramatic, high quality",
                "motion": "zoom_in"
            }
            for i in range(num_scenes)
        ]

    try:
        from google import genai
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Topic: {topic}\n\nProduce a {num_scenes}-scene dramatic documentary.",
            config={"system_instruction": KIDS_SYSTEM_PROMPT},
        )
        raw = response.text.strip()
        # Strip markdown code fences if Gemini adds them
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[CoreEngine] Gemini script generation failed: {e}")
        return []


# ─── Full quick-render pipeline (used by server as express mode) ──────────────
async def quick_render(
    topic: str,
    out_dir: Path,
    num_scenes: int = 6,
    voice: str = "en-US-ChristopherNeural",
    width: int = None,
    height: int = None,
) -> Optional[Path]:
    """
    Standalone quick-render that produces a final MP4 without the full pipeline.
    Used when user hits 'Quick Generate' (fast mode).

    Returns path to final_documentary.mp4 or None on failure.
    """
    import edge_tts

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    clips = []

    print(f"[CoreEngine] Generating script for: {topic}")
    scenes = generate_script_via_gemini(topic, num_scenes)
    if not scenes:
        return None

    for s in scenes:
        num = s.get("scene_num", scenes.index(s) + 1)
        narration = s.get("narration", "")
        img_prompt = s.get("image_prompt", topic)
        motion = s.get("motion", "zoom_in")

        aud_file = out_dir / f"audio_{num}.mp3"
        img_file = out_dir / f"img_{num}.jpg"
        clip_file = out_dir / f"clip_{num}.mp4"

        print(f"  [Scene {num}] Generating voice...")
        try:
            comm = edge_tts.Communicate(narration, voice)
            await comm.save(str(aud_file))
        except Exception as e:
            print(f"  [Scene {num}] TTS failed: {e}")
            continue

        duration = get_audio_duration(aud_file)

        print(f"  [Scene {num}] Fetching image (duration={duration:.1f}s)...")
        ok = fetch_pollinations_image(img_prompt, img_file, width, height)
        if not ok:
            print(f"  [Scene {num}] Image fetch failed, skipping scene.")
            continue

        print(f"  [Scene {num}] Rendering Ken Burns clip ({motion})...")
        ok = render_ken_burns(img_file, aud_file, clip_file, duration, motion, width, height)
        if ok:
            clips.append(clip_file)

    if not clips:
        print("[CoreEngine] No clips rendered.")
        return None

    # Concatenate all clips
    concat_file = out_dir / "concat.txt"
    concat_file.write_text(
        "\n".join(f"file '{c.resolve()}'" for c in clips)
    )
    final_out = out_dir / "final_documentary.mp4"
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(final_out)
        ], check=True, capture_output=True)
        print(f"[CoreEngine] ✅ Done → {final_out}")
        return final_out
    except subprocess.CalledProcessError as e:
        print(f"[CoreEngine] Concat failed: {e.stderr.decode()[-300:]}")
        return None
