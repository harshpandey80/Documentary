"""
MotionArray Documentary Motion Graphics Kit
Inspired by motionarray.com/stock-motion-graphics.

Provides broadcast-grade procedural motion graphics overlays & elements:
1. Retro CRT / Surveillance Viewfinder HUD:
   - Corner brackets [ ], blinking ● REC indicator, running timecode, declassified date stamp,
     central crosshair reticle, scanlines, and tracking telemetry.
2. Forensic Callout & Focal Target:
   - Animated focus reticle/circle around evidentiary details, leader pointer arrow, and floating metadata card.
3. Procedural Film Burn / Light Leak:
   - Warm amber & magenta cinematic film burn transition for high-impact chapter transitions.
4. Broadcast Lower Third Strap:
   - Two-tier documentary lower third with animated reveal and official archive source tag.
"""

from __future__ import annotations
import math
import subprocess
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Dict, Any, List, Tuple, Optional


class MotionArrayKit:
    """
    MotionArray Procedural Motion Graphics Kit.
    Generates ready-to-composite or standalone motion graphics videos.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or (Path("workspace") / "motionarray_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        font_names = [
            "arialbd.ttf" if bold else "arial.ttf",
            "segoeuib.ttf" if bold else "segoeui.ttf",
            "impact.ttf",
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        ]
        for name in font_names:
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                pass
        return ImageFont.load_default()

    def render_viewfinder_hud(
        self,
        dest_video: Path,
        duration: float = 3.0,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        classification: str = "TOP SECRET // SURVEILLANCE FEED",
        target_name: str = "SUBJECT: DECLASSIFIED DOSSIER",
        base_image: Optional[Image.Image] = None,
    ) -> Path:
        """
        Renders a Retro CRT / Surveillance Viewfinder HUD inspired by MotionArray Vertical CRT elements.
        Can render as a standalone background or composited over an existing base frame.
        """
        dest_video.parent.mkdir(parents=True, exist_ok=True)
        total_frames = max(1, int(duration * fps))

        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "rgba",
            "-r", str(fps),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            str(dest_video),
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

        font_large = self._get_font(int(width * 0.038), bold=True)
        font_mid = self._get_font(int(width * 0.026), bold=True)
        font_mono = self._get_font(int(width * 0.024), bold=False)

        # Subtle scanline pattern precalculation
        scanlines = np.ones((height, width, 3), dtype=np.float32)
        scanlines[::4, :, :] = 0.82
        scanlines[1::4, :, :] = 0.88

        try:
            for frame_idx in range(total_frames):
                if base_image:
                    bg = base_image.copy().resize((width, height)).convert("RGB")
                else:
                    # Deep dark surveillance monitor backdrop
                    arr = np.zeros((height, width, 3), dtype=np.uint8)
                    arr[:, :, 0] = 6
                    arr[:, :, 1] = 10
                    arr[:, :, 2] = 16
                    bg = Image.fromarray(arr)

                # Apply scanline texture
                arr_bg = np.array(bg, dtype=np.float32) * scanlines
                frame_img = Image.fromarray(np.clip(arr_bg, 0, 255).astype(np.uint8))
                draw = ImageDraw.Draw(frame_img)

                hud_color = (0, 255, 180)  # Neon phosphor emerald
                alert_color = (255, 45, 45)  # Crimson REC

                # 1. Outer Viewfinder Safe-Zone Corner Brackets [  ]
                margin_x = int(width * 0.07)
                margin_y = int(height * 0.06)
                b_len = int(width * 0.08)
                b_thick = 4

                # Top-Left [
                draw.line([(margin_x, margin_y), (margin_x + b_len, margin_y)], fill=hud_color, width=b_thick)
                draw.line([(margin_x, margin_y), (margin_x, margin_y + b_len)], fill=hud_color, width=b_thick)
                # Top-Right ]
                draw.line([(width - margin_x, margin_y), (width - margin_x - b_len, margin_y)], fill=hud_color, width=b_thick)
                draw.line([(width - margin_x, margin_y), (width - margin_x, margin_y + b_len)], fill=hud_color, width=b_thick)
                # Bottom-Left [
                draw.line([(margin_x, height - margin_y), (margin_x + b_len, height - margin_y)], fill=hud_color, width=b_thick)
                draw.line([(margin_x, height - margin_y), (margin_x, height - margin_y - b_len)], fill=hud_color, width=b_thick)
                # Bottom-Right ]
                draw.line([(width - margin_x, height - margin_y), (width - margin_x - b_len, height - margin_y)], fill=hud_color, width=b_thick)
                draw.line([(width - margin_x, height - margin_y), (width - margin_x, height - margin_y - b_len)], fill=hud_color, width=b_thick)

                # 2. Blinking ● REC indicator (Blinks every 15 frames / 0.5s)
                rec_visible = (frame_idx // 12) % 2 == 0
                if rec_visible:
                    draw.ellipse([margin_x + 10, margin_y + 16, margin_x + 30, margin_y + 36], fill=alert_color)
                    draw.text((margin_x + 40, margin_y + 14), "REC ●", fill=alert_color, font=font_mid)
                else:
                    draw.text((margin_x + 40, margin_y + 14), "REC", fill=(120, 120, 120), font=font_mid)

                # 3. Running Timecode
                total_sec = frame_idx / fps
                mins = int(total_sec // 60)
                secs = int(total_sec % 60)
                frames_rem = frame_idx % fps
                timecode_str = f"TC  00:{mins:02d}:{secs:02d}:{frames_rem:02d}"
                draw.text((width - margin_x - 260, margin_y + 14), timecode_str, fill=hud_color, font=font_mono)

                # 4. Central Target Reticle & Crosshairs
                cx = width // 2
                cy = height // 2
                reticle_rad = int(width * 0.16)
                # Central crosshairs
                draw.line([(cx - 30, cy), (cx - 8, cy)], fill=hud_color, width=2)
                draw.line([(cx + 8, cy), (cx + 30, cy)], fill=hud_color, width=2)
                draw.line([(cx, cy - 30), (cx, cy - 8)], fill=hud_color, width=2)
                draw.line([(cx, cy + 8), (cx, cy + 30)], fill=hud_color, width=2)

                # Rotating tracking marks
                rot_angle = frame_idx * 0.05
                for a_offset in [0, math.pi / 2, math.pi, 3 * math.pi / 2]:
                    ang = rot_angle + a_offset
                    tx1 = cx + math.cos(ang) * (reticle_rad - 15)
                    ty1 = cy + math.sin(ang) * (reticle_rad - 15)
                    tx2 = cx + math.cos(ang) * (reticle_rad + 10)
                    ty2 = cy + math.sin(ang) * (reticle_rad + 10)
                    draw.line([(tx1, ty1), (tx2, ty2)], fill=hud_color, width=2)

                # 5. Top Classification Stamp Banner
                draw.text((margin_x, margin_y - 34), classification.upper(), fill=hud_color, font=font_mono)

                # 6. Bottom Information Strap & Telemetry
                draw.text((margin_x, height - margin_y - 45), target_name.upper(), fill=(255, 255, 255), font=font_large)
                draw.text((margin_x, height - margin_y + 10), "OPTICAL SENSOR: 4K MULTI-SPECTRAL // ISO 800 // F/2.8", fill=hud_color, font=font_mono)

                # Battery & Signal Bars
                bat_x = width - margin_x - 140
                bat_y = height - margin_y + 10
                draw.rectangle([bat_x, bat_y, bat_x + 50, bat_y + 20], outline=hud_color, width=2)
                draw.rectangle([bat_x + 50, bat_y + 5, bat_x + 54, bat_y + 15], fill=hud_color)
                # 3 battery charge bars
                draw.rectangle([bat_x + 4, bat_y + 4, bat_x + 14, bat_y + 16], fill=hud_color)
                draw.rectangle([bat_x + 18, bat_y + 4, bat_x + 28, bat_y + 16], fill=hud_color)
                draw.rectangle([bat_x + 32, bat_y + 4, bat_x + 42, bat_y + 16], fill=hud_color)

                proc.stdin.write(frame_img.convert("RGBA").tobytes())

            proc.stdin.close()
            proc.wait()
        except Exception as e:
            proc.kill()
            raise e

        return dest_video

    def render_forensic_callout(
        self,
        target_point: Tuple[int, int],
        title: str,
        subtitle: str,
        dest_video: Path,
        duration: float = 3.0,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        base_image: Optional[Image.Image] = None,
        accent_color: Tuple[int, int, int] = (255, 200, 40),  # Warm amber/gold
    ) -> Path:
        """
        Renders an animated forensic callout (animated circle + leader pointer line + data card)
        pointing directly to a piece of evidence on a historical document, map, or artifact photo.
        """
        dest_video.parent.mkdir(parents=True, exist_ok=True)
        total_frames = max(1, int(duration * fps))

        tx, ty = target_point
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "rgba",
            "-r", str(fps),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            str(dest_video),
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

        font_title = self._get_font(int(width * 0.038), bold=True)
        font_sub = self._get_font(int(width * 0.024), bold=False)
        font_tag = self._get_font(int(width * 0.020), bold=True)

        # Destination card position
        card_x = min(max(tx + 80, 80), width - 420)
        card_y = max(ty - 160, 160)
        card_w = 380
        card_h = 130

        try:
            for frame_idx in range(total_frames):
                if base_image:
                    frame_img = base_image.copy().resize((width, height)).convert("RGB")
                else:
                    arr = np.zeros((height, width, 3), dtype=np.uint8)
                    arr[:, :, :] = 16
                    frame_img = Image.fromarray(arr)

                draw = ImageDraw.Draw(frame_img)

                # Progressive animation progress (0.0 to 1.0)
                raw_t = frame_idx / float(total_frames - 1) if total_frames > 1 else 1.0

                # 1. Animated Focus Reticle
                reticle_progress = min(1.0, raw_t / 0.35)
                max_rad = 42
                curr_rad = int(max_rad * reticle_progress)

                pulse = int(5 * math.sin(frame_idx * 0.35))
                draw.ellipse([tx - curr_rad - pulse, ty - curr_rad - pulse, tx + curr_rad + pulse, ty + curr_rad + pulse],
                             outline=accent_color, width=3)
                draw.ellipse([tx - 6, ty - 6, tx + 6, ty + 6], fill=accent_color)

                # 2. Animated Leader Pointer Line
                line_progress = min(1.0, max(0.0, (raw_t - 0.25) / 0.35))
                end_lx = tx + (card_x - tx) * line_progress
                end_ly = ty + ((card_y + card_h // 2) - ty) * line_progress

                if line_progress > 0:
                    draw.line([(tx, ty), (end_lx, end_ly)], fill=accent_color, width=3)

                # 3. Data Card Bloom
                card_progress = min(1.0, max(0.0, (raw_t - 0.5) / 0.3))
                if card_progress > 0:
                    cur_w = int(card_w * card_progress)
                    cur_h = int(card_h * card_progress)

                    # Card backdrop
                    draw.rectangle([card_x, card_y, card_x + cur_w, card_y + cur_h],
                                   fill=(12, 18, 28, 230))
                    draw.rectangle([card_x, card_y, card_x + cur_w, card_y + cur_h],
                                   outline=accent_color, width=2)
                    draw.rectangle([card_x, card_y, card_x + cur_w, card_y + 24],
                                   fill=accent_color)

                    if card_progress > 0.8:
                        draw.text((card_x + 10, card_y + 3), "FORENSIC EVIDENCE // ANOMALY", fill=(10, 10, 10), font=font_tag)
                        draw.text((card_x + 16, card_y + 36), title.upper(), fill=(255, 255, 255), font=font_title)
                        draw.text((card_x + 16, card_y + 78), subtitle, fill=(200, 210, 220), font=font_sub)

                proc.stdin.write(frame_img.convert("RGBA").tobytes())

            proc.stdin.close()
            proc.wait()
        except Exception as e:
            proc.kill()
            raise e

        return dest_video

    def render_film_burn_transition(
        self,
        dest_video: Path,
        duration: float = 1.8,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
    ) -> Path:
        """
        Renders a cinematic organic film burn / light leak transition video (warm amber, orange, magenta flares)
        inspired by MotionArray Film Leaks Transitions.
        """
        dest_video.parent.mkdir(parents=True, exist_ok=True)
        total_frames = max(1, int(duration * fps))

        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "rgba",
            "-r", str(fps),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            str(dest_video),
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

        mid_frame = total_frames / 2.0

        try:
            for frame_idx in range(total_frames):
                # Intensity rises to maximum at midpoint then fades
                intensity = 1.0 - abs(frame_idx - mid_frame) / mid_frame
                intensity = math.sin(intensity * math.pi / 2.0)

                # Generate organic gradient flares
                img = Image.new("RGB", (width, height), (0, 0, 0))
                draw = ImageDraw.Draw(img)

                # Main warm amber flare epicenter
                flare_x = int(width * (0.3 + 0.4 * math.sin(frame_idx * 0.15)))
                flare_y = int(height * (0.4 + 0.3 * math.cos(frame_idx * 0.12)))
                flare_radius = int(width * 0.7 * intensity)

                if flare_radius > 10:
                    # Multi-ring glowing radial gradient
                    for r in range(flare_radius, 0, -30):
                        step_t = 1.0 - (r / float(flare_radius))
                        r_val = int(min(255, 255 * step_t * intensity))
                        g_val = int(min(255, 140 * step_t * intensity))
                        b_val = int(min(255, 40 * step_t * intensity))
                        draw.ellipse([flare_x - r, flare_y - r, flare_x + r, flare_y + r],
                                     fill=(r_val, g_val, b_val))

                # Edge magenta light leak
                leak_w = int(width * 0.5 * intensity)
                if leak_w > 5:
                    for x in range(leak_w, 0, -20):
                        step_m = 1.0 - (x / float(leak_w))
                        draw.rectangle([width - x, 0, width, height],
                                       fill=(int(220 * step_m * intensity), 0, int(110 * step_m * intensity)))

                # Soften flares
                img = img.filter(ImageFilter.GaussianBlur(radius=18))

                proc.stdin.write(img.convert("RGBA").tobytes())

            proc.stdin.close()
            proc.wait()
        except Exception as e:
            proc.kill()
            raise e

        return dest_video
