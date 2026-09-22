"""
Code2Video Motion Graphics Engine (inspired by showlab/Code2Video)
Generates programmatic, code-driven video animations for documentaries:
1. Animated Tactical War Maps (advancing troop vectors, contested borders, radar sweep)
2. Classified Dossier Redactions (animated declassification stamps, forensic document analysis)
3. Kinetic Data Timelines (casualty counters, military production gauges)
"""

from __future__ import annotations
import math
import subprocess
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from typing import Dict, Any, Optional

class Code2VideoEngine:
    """
    Code-Centric Documentary Motion Graphics Generator.
    """

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or (Path("workspace") / "code2video_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def generate_tactical_map_video(
        self,
        topic: str,
        dest_video: Path,
        duration: float = 4.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        scene_id: str = "",
        telemetry: Optional[Dict[str, str]] = None,
    ) -> Path | None:
        """
        Renders an animated military tactical operations map with moving frontline arrows,
        coordinate grids, territory shading, and an active radar sweep line.
        Parametrized dynamically without hardcoded topic facts.
        """
        tel = telemetry or {}
        unique_key = f"{topic}_{scene_id}_{duration}_{width}x{height}"
        frames_dir = self.cache_dir / f"map_frames_{abs(hash(unique_key))}"
        frames_dir.mkdir(parents=True, exist_ok=True)

        total_frames = int(duration * fps)
        is_vertical = height > width

        # Dynamic telemetry parameters
        lat_val = abs(hash(topic + scene_id + "lat")) % 80
        lon_val = abs(hash(topic + scene_id + "lon")) % 180
        default_coords = f"LAT {lat_val:02d}°{abs(hash(scene_id))%60:02d}'N  LON {lon_val:03d}°{abs(hash(topic))%60:02d}'E"
        coords = tel.get("coords", default_coords)
        location = tel.get("location", f"SECTOR ALPHA // {topic.upper()[:24]}")
        telemetry_str = tel.get("telemetry", "TELEMETRY: SENSOR ARRAY ACTIVE // STATUS: RECORDING")
        freq_label = tel.get("frequency", "SIGNAL FREQUENCY: 14.8 KHZ")
        center_label = tel.get("center_label", f"{topic.upper()[:22]} // ZONE")
        signal_label = tel.get("signal_label", "TELEMETRY SPECTRUM OSCILLOGRAM")
        anomaly_label = tel.get("anomaly_label", "ANOMALY CONTACT")

        for i in range(total_frames):
            progress = i / total_frames
            img = Image.new("RGB", (width, height), (10, 16, 24))
            draw = ImageDraw.Draw(img)

            # 1. High-Tech Grid Background
            grid_spacing = 60 if is_vertical else 80
            for x in range(0, width, grid_spacing):
                draw.line([(x, 0), (x, height)], fill=(18, 28, 40), width=1)
            for y in range(0, height, grid_spacing):
                draw.line([(0, y), (width, y)], fill=(18, 28, 40), width=1)

            if is_vertical:
                # =========================================================================
                # VERTICAL 9:16 TACTICAL BATHYMETRIC SONAR HUD
                # =========================================================================
                # Top Header Banner
                draw.rectangle([40, 80, width - 40, 240], fill=(14, 22, 34), outline=(40, 85, 125), width=2)
                draw.line([40, 80, 40, 240], fill=(230, 45, 45), width=6)
                draw.text((65, 100), f"TACTICAL TELEMETRY // {topic.upper()[:30]}", fill=(240, 245, 255))
                draw.text((65, 135), f"LOCATION: {location} // {coords}", fill=(80, 200, 240))
                draw.text((65, 168), f"{telemetry_str}", fill=(160, 180, 205))
                draw.text((65, 200), f"{freq_label} // PHASE: {int(progress * 4) + 1}", fill=(245, 180, 40))

                # Central Circular Sonar Radar Display
                radar_center = (width // 2, int(height * 0.42))
                radar_radius = int(width * 0.40)

                # Outer radar ring
                draw.ellipse(
                    [radar_center[0]-radar_radius, radar_center[1]-radar_radius,
                     radar_center[0]+radar_radius, radar_center[1]+radar_radius],
                    outline=(50, 120, 95), width=3
                )
                # Inner depth range rings
                for r_frac in [0.25, 0.50, 0.75]:
                    rr = int(radar_radius * r_frac)
                    draw.ellipse(
                        [radar_center[0]-rr, radar_center[1]-rr, radar_center[0]+rr, radar_center[1]+rr],
                        outline=(30, 75, 60), width=1
                    )
                # Radar crosshairs
                draw.line([(radar_center[0]-radar_radius, radar_center[1]), (radar_center[0]+radar_radius, radar_center[1])], fill=(35, 85, 65), width=1)
                draw.line([(radar_center[0], radar_center[1]-radar_radius), (radar_center[0], radar_center[1]+radar_radius)], fill=(35, 85, 65), width=1)

                # Animated rotating radar sweep
                radar_angle = progress * 4 * math.pi
                sweep_x = int(radar_center[0] + radar_radius * math.cos(radar_angle))
                sweep_y = int(radar_center[1] + radar_radius * math.sin(radar_angle))
                draw.line([radar_center, (sweep_x, sweep_y)], fill=(80, 255, 120), width=3)
                
                # Fading phosphor wake line
                wake_angle = radar_angle - 0.25
                wake_x = int(radar_center[0] + radar_radius * math.cos(wake_angle))
                wake_y = int(radar_center[1] + radar_radius * math.sin(wake_angle))
                draw.line([radar_center, (wake_x, wake_y)], fill=(40, 160, 80), width=1)

                # Anomaly blip pinging
                blip_pos = (radar_center[0] + int(radar_radius * 0.55), radar_center[1] - int(radar_radius * 0.35))
                pulse_size = int(6 + 8 * abs(math.sin(progress * 10)))
                draw.ellipse([blip_pos[0]-pulse_size, blip_pos[1]-pulse_size, blip_pos[0]+pulse_size, blip_pos[1]+pulse_size], outline=(255, 60, 60), width=2)
                draw.ellipse([blip_pos[0]-3, blip_pos[1]-3, blip_pos[0]+3, blip_pos[1]+3], fill=(255, 80, 80))
                draw.text((blip_pos[0]+12, blip_pos[1]-8), anomaly_label, fill=(255, 100, 100))

                # Terrain / Contour Cross-Section (Mid-Lower Section)
                trench_top_y = int(height * 0.65)
                trench_bottom_y = int(height * 0.78)
                trench_pts = [
                    (40, trench_top_y), (int(width * 0.35), trench_top_y + 40),
                    (int(width * 0.46), trench_bottom_y), (int(width * 0.54), trench_bottom_y),
                    (int(width * 0.65), trench_top_y + 40), (width - 40, trench_top_y),
                    (width - 40, trench_bottom_y + 40), (40, trench_bottom_y + 40)
                ]
                draw.polygon(trench_pts, fill=(18, 30, 46), outline=(60, 150, 200))
                draw.text((width // 2 - 110, trench_bottom_y + 8), center_label, fill=(100, 220, 255))

                # Oscilloscope / Signal Frequency Monitor (Bottom safe zone < 1530)
                osc_top = int(height * 0.68)
                osc_bottom = min(int(height * 0.76), 1460)
                draw.rectangle([40, osc_top, width - 40, osc_bottom], fill=(12, 18, 26), outline=(40, 80, 110), width=1)
                draw.text((55, osc_top + 10), signal_label, fill=(130, 160, 190))
                
                # Draw animated waveform
                wave_mid_y = (osc_top + osc_bottom) // 2 + 10
                prev_pt = None
                for wx in range(50, width - 50, 6):
                    phase_shift = progress * 20 + wx * 0.04
                    amp = 30 * math.sin(phase_shift) * math.cos(wx * 0.015)
                    curr_pt = (wx, int(wave_mid_y + amp))
                    if prev_pt:
                        draw.line([prev_pt, curr_pt], fill=(50, 220, 140), width=2)
                    prev_pt = curr_pt
            else:
                # =========================================================================
                # LANDSCAPE 16:9 TACTICAL OPERATIONS MAP
                # =========================================================================
                land_color = (24, 34, 46)
                coast_points = [
                    (int(width*0.10), int(height*0.10)), (int(width*0.25), int(height*0.20)),
                    (int(width*0.35), int(height*0.16)), (int(width*0.48), int(height*0.30)),
                    (int(width*0.60), int(height*0.22)), (int(width*0.75), int(height*0.38)),
                    (int(width*0.90), int(height*0.32)), (int(width*0.95), int(height*0.60)),
                    (int(width*0.90), int(height*0.88)), (int(width*0.65), int(height*0.92)),
                    (int(width*0.45), int(height*0.84)), (int(width*0.20), int(height*0.88)),
                    (int(width*0.08), int(height*0.58))
                ]
                draw.polygon(coast_points, fill=land_color, outline=(45, 85, 115))

                # Animated Advancing Operations Arrow
                a_start = (int(width * 0.20), int(height * 0.75))
                a_end = (
                    int(width * 0.20 + (width * 0.50 - width * 0.20) * min(1.0, progress * 1.3)),
                    int(height * 0.75 + (height * 0.40 - height * 0.75) * min(1.0, progress * 1.3)),
                )
                draw.line([a_start, a_end], fill=(225, 45, 45), width=6)
                draw.ellipse([a_end[0]-10, a_end[1]-10, a_end[0]+10, a_end[1]+10], fill=(255, 80, 80))

                # Radar Sweep Display
                radar_center = (int(width * 0.82), int(height * 0.28))
                radar_radius = int(height * 0.22)
                draw.ellipse(
                    [radar_center[0]-radar_radius, radar_center[1]-radar_radius,
                     radar_center[0]+radar_radius, radar_center[1]+radar_radius],
                    outline=(45, 110, 85), width=2
                )
                radar_angle = progress * 4 * math.pi
                sweep_x = int(radar_center[0] + radar_radius * math.cos(radar_angle))
                sweep_y = int(radar_center[1] + radar_radius * math.sin(radar_angle))
                draw.line([radar_center, (sweep_x, sweep_y)], fill=(80, 255, 120), width=2)

                # Header HUD
                draw.rectangle([80, 60, int(width * 0.48), 160], fill=(12, 18, 26), outline=(40, 80, 115), width=2)
                draw.line([80, 60, 80, 160], fill=(225, 45, 45), width=6)
                draw.text((105, 78), f"TACTICAL THEATER: {topic.upper()[:40]}", fill=(240, 245, 255))
                draw.text((105, 115), f"PHASE {int(progress * 4) + 1} // {coords} // {telemetry_str[:32]}", fill=(130, 180, 220))

            frame_file = frames_dir / f"frame_{i:04d}.jpg"
            img.save(frame_file, quality=92)

        # Assemble into MP4 with FFmpeg
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(frames_dir / "frame_%04d.jpg"),
            "-t", f"{duration:.3f}",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            str(dest_video),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            for f in frames_dir.glob("*.jpg"):
                try:
                    f.unlink()
                except Exception:
                    pass
            try:
                frames_dir.rmdir()
            except Exception:
                pass

            if res.returncode == 0 and dest_video.exists():
                return dest_video
        except Exception:
            pass

        return None

    def generate_dossier_redaction_video(
        self,
        topic: str,
        dest_video: Path,
        duration: float = 4.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        scene_id: str = "",
        telemetry: Optional[Dict[str, str]] = None,
    ) -> Path | None:
        """
        Renders an authentic classified dossier inspection with animated redaction bars
        and a heavy 'DECLASSIFIED - TOP SECRET' ink stamp hitting the document.
        Optimized dynamically for vertical (9:16) and landscape (16:9) framing.
        """
        tel = telemetry or {}
        unique_key = f"{topic}_{scene_id}_{duration}_{width}x{height}"
        frames_dir = self.cache_dir / f"dossier_frames_{abs(hash(unique_key))}"
        frames_dir.mkdir(parents=True, exist_ok=True)

        total_frames = int(duration * fps)
        is_vertical = height > width

        # Document boundaries
        doc_left = int(width * 0.08) if is_vertical else int(width * 0.16)
        doc_right = int(width * 0.92) if is_vertical else int(width * 0.84)
        doc_top = int(height * 0.06) if is_vertical else int(height * 0.08)
        doc_bottom = min(int(height * 0.76), 1460) if is_vertical else int(height * 0.92)

        agency_header = tel.get("agency", "CENTRAL ARCHIVES // HISTORICAL RECORD DIVISION")
        file_id = tel.get("file_id", f"ARC-{abs(hash(topic + scene_id)) % 90000 + 10000:05d}")
        lat_val = abs(hash(topic + scene_id + "lat")) % 80
        lon_val = abs(hash(topic + scene_id + "lon")) % 180
        coords = tel.get("coords", f"LAT: {lat_val:02d}°{abs(hash(scene_id))%60:02d}'N  LON: {lon_val:03d}°{abs(hash(topic))%60:02d}'E")
        stamp_title = tel.get("stamp_title", "ARCHIVAL RECORD // OFFICIAL EXHIBIT")
        stamp_authority = tel.get("stamp_authority", "NATIONAL ARCHIVES & RECORDS SERVICE")

        for i in range(total_frames):
            progress = i / total_frames

            # Outer backdrop: dark archive desktop
            img = Image.new("RGB", (width, height), (18, 16, 14))
            draw = ImageDraw.Draw(img)

            # Document drop shadow
            draw.rectangle([doc_left + 12, doc_top + 12, doc_right + 12, doc_bottom + 12], fill=(8, 7, 6))

            # Aged Manila parchment background
            draw.rectangle([doc_left, doc_top, doc_right, doc_bottom], fill=(234, 226, 208), outline=(130, 115, 95), width=2)

            # Document margins
            inner_left = doc_left + (40 if is_vertical else 60)
            inner_right = doc_right - (40 if is_vertical else 60)

            # Header & Classification Banner
            draw.rectangle([inner_left, doc_top + 25, inner_right, doc_top + 70], fill=(45, 40, 35))
            draw.text((inner_left + 20, doc_top + 38), "TOP SECRET // RESTRICTED ACCESS // EYES ONLY", fill=(245, 235, 220))

            draw.line([(inner_left, doc_top + 90), (inner_right, doc_top + 90)], fill=(120, 110, 95), width=2)
            draw.text((inner_left, doc_top + 105), agency_header[:55], fill=(60, 52, 44))
            draw.text((inner_left, doc_top + 135), f"SUBJECT: {topic.upper()[:44]} - ARCHIVAL DOSSIER", fill=(85, 75, 65))
            draw.text((inner_left, doc_top + 165), f"FILE ID: {file_id} // {coords}", fill=(110, 100, 90))
            draw.line([(inner_left, doc_top + 195), (inner_right, doc_top + 195)], fill=(150, 140, 125), width=1)

            # Typewriter body lines with animated redaction bars
            y_cursor = doc_top + 230
            line_spacing = 42 if is_vertical else 38
            num_lines = 16 if is_vertical else 12

            for line_idx in range(num_lines):
                line_y = y_cursor + line_idx * line_spacing
                if line_y > doc_bottom - 160:
                    break

                # Draw typewriter-like text line simulation
                draw.line([(inner_left, line_y), (inner_right - (40 if line_idx % 3 == 0 else 10), line_y)], fill=(125, 115, 105), width=3)

                # Black redaction bars over sensitive data lines
                if line_idx in [2, 4, 7, 9, 12, 14]:
                    redact_prog = min(1.0, progress * 1.8)
                    bar_w = int((inner_right - inner_left - 120) * redact_prog)
                    draw.rectangle([inner_left + 100, line_y - 12, inner_left + 100 + bar_w, line_y + 12], fill=(18, 16, 14))

            # Animated Stamp: Slam down at 35% progress with impact scale
            if progress > 0.35:
                stamp_w = int((inner_right - inner_left) * 0.75)
                stamp_h = 100 if is_vertical else 90
                stamp_x1 = (width - stamp_w) // 2
                stamp_y1 = int(height * 0.58) if is_vertical else int(height * 0.52)
                stamp_x2 = stamp_x1 + stamp_w
                stamp_y2 = stamp_y1 + stamp_h

                # Red ink stamp box with heavy border
                draw.rectangle([stamp_x1, stamp_y1, stamp_x2, stamp_y2], outline=(190, 30, 30), width=6)
                draw.text((stamp_x1 + 30, stamp_y1 + 18), stamp_title, fill=(190, 30, 30))
                draw.text((stamp_x1 + 45, stamp_y1 + 54), stamp_authority, fill=(160, 45, 45))

            frame_file = frames_dir / f"frame_{i:04d}.jpg"
            img.save(frame_file, quality=92)

        # Assemble into MP4 with FFmpeg
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(frames_dir / "frame_%04d.jpg"),
            "-t", f"{duration:.3f}",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            str(dest_video),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            for f in frames_dir.glob("*.jpg"):
                try:
                    f.unlink()
                except Exception:
                    pass
            try:
                frames_dir.rmdir()
            except Exception:
                pass

            if res.returncode == 0 and dest_video.exists():
                return dest_video
        except Exception:
            pass

        return None
