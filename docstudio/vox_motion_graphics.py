"""
Vox-Style Paper-Collage Motion Graphics Engine
---------------------------------------------
100% Free & Local procedural motion graphics generator inspired by Vox / Johnny Harris
explainer documentaries.

Generates broadcast-ready 1080p (16:9) and vertical (9:16) MP4 video clips:
1. Animated Newspaper Clippings (torn paper, masthead, headline, animated yellow highlighter sweep, scotch tape)
2. Declassified Forensic Dossiers (typewriter font, black redaction bars, slamming red rubber stamp)
3. Polaroid Evidence Pinboard (polaroid frame, push pin, investigation thread, handwritten caption)

Pure local CPU execution: Pillow + NumPy + FFmpeg.
Zero external paid API costs (no muapi.ai, no OpenAI required).
"""

from __future__ import annotations

import math
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


# ----------------------------------------------------------------------
# Font Helper Functions
# ----------------------------------------------------------------------

_SERIF_FONTS = ["Georgia", "Times New Roman", "DejaVu Serif", "serif"]
_MONO_FONTS = ["Impact", "Consolas", "Courier New", "Lucida Console", "monospace"]
_SANS_FONTS = ["Arial Black", "Impact", "Arial", "Calibri", "DejaVu Sans", "sans-serif"]

_BUNDLED_FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

_FONT_SEARCH_DIRS = [
    _BUNDLED_FONTS_DIR,
    Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
    Path("C:/Windows/Fonts"),
    Path("/usr/share/fonts/truetype"),
    Path("/usr/share/fonts"),
    Path("/Library/Fonts"),
    Path.home() / ".fonts",
]

_FONT_FAMILY_FILENAMES = {
    "Montserrat": ["Montserrat-Bold.ttf", "Montserrat.ttf"],
    "Cinzel": ["Cinzel-Bold.ttf", "Cinzel.ttf"],
    "Inter": ["Inter-Bold.ttf", "Inter.ttf"],
    "Impact": ["Montserrat-Bold.ttf", "impact.ttf", "Impact.ttf"],
    "Arial Black": ["Montserrat-Bold.ttf", "ariblk.ttf", "Arial Black.ttf"],
    "Arial": ["Inter-Bold.ttf", "arialbd.ttf", "arial.ttf", "Arial.ttf"],
    "Calibri": ["Inter-Bold.ttf", "calibrib.ttf", "calibri.ttf"],
    "DejaVu Sans": ["Inter-Bold.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"],
    "Georgia": ["Cinzel-Bold.ttf", "georgiab.ttf", "georgia.ttf", "Georgia.ttf"],
    "Times New Roman": ["Cinzel-Bold.ttf", "timesbd.ttf", "times.ttf", "Times New Roman.ttf"],
    "Consolas": ["consolab.ttf", "consola.ttf", "Consolas.ttf"],
    "Courier New": ["courbd.ttf", "cour.ttf", "Courier New.ttf"],
}


def _resolve_font_file(name: str) -> Optional[str]:
    if os.path.exists(name):
        return name
    filenames = _FONT_FAMILY_FILENAMES.get(name, [name, f"{name}.ttf"])
    for fdir in _FONT_SEARCH_DIRS:
        if fdir.exists():
            for fname in filenames:
                cand = fdir / fname
                if cand.exists():
                    return str(cand)
    return None


def _get_font(font_names: List[str], size: int) -> Optional[object]:
    if not _PIL_AVAILABLE:
        return None
    for name in font_names:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            pass
        resolved = _resolve_font_file(name)
        if resolved:
            try:
                return ImageFont.truetype(resolved, size)
            except (OSError, IOError):
                pass

    # Bundled SIL OFL fonts fallback
    fallback_cands = ["Montserrat-Bold.ttf", "Inter-Bold.ttf", "Cinzel-Bold.ttf", "ariblk.ttf", "arialbd.ttf", "calibrib.ttf"]
    for fdir in _FONT_SEARCH_DIRS:
        if fdir.exists():
            for fname in fallback_cands:
                cand = fdir / fname
                if cand.exists():
                    try:
                        return ImageFont.truetype(str(cand), size)
                    except (OSError, IOError):
                        pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def _wrap_text(text: str, font: object, max_width: int, draw: object) -> List[str]:
    """Wrap text to fit within a given pixel width."""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        try:
            bbox = draw.textbbox((0, 0), test_line, font=font)
            w = bbox[2] - bbox[0]
        except Exception:
            w = len(test_line) * 12

        if w <= max_width or not current_line:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))
    return lines


# ----------------------------------------------------------------------
# VoxMotionGraphicsEngine
# ----------------------------------------------------------------------

class VoxMotionGraphicsEngine:
    """
    Procedural paper-collage motion graphics generator.
    Produces high-retention 1080p / 9:16 animated clips with Ken Burns camera drift.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or (Path("workspace") / "vox_collage_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Newspaper Clipping with Animated Highlighter
    # ------------------------------------------------------------------

    def render_newspaper_clipping(
        self,
        headline: str,
        subtext: str = "",
        dest_video: Optional[Path] = None,
        duration: float = 4.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        scene_id: str = "",
        highlight_phrase: str = "",
    ) -> Optional[Path]:
        """
        Renders an authentic newspaper clipping on a dark desk, featuring:
        - Vintage masthead & date rule
        - Bold serif headline
        - Multi-column newsprint body text
        - Animated fluorescent yellow highlighter sweep across key claim
        - Scotch tape strips on corners
        - Organic camera push-in and micro-drift
        """
        if not _PIL_AVAILABLE:
            print("[VoxMotion] Pillow not installed — skipping newspaper collage.")
            return None

        if dest_video is None:
            key = abs(hash(f"news_{headline}_{subtext}_{scene_id}_{duration}_{width}x{height}"))
            dest_video = self.cache_dir / f"vox_news_{key}.mp4"

        if dest_video.exists() and dest_video.stat().st_size > 15000:
            return dest_video

        frames_dir = self.cache_dir / f"news_frames_{abs(hash(str(dest_video)))}"
        frames_dir.mkdir(parents=True, exist_ok=True)

        total_frames = int(duration * fps)
        is_vertical = height > width

        # Base dimensions of paper clipping
        clip_w = int(width * (0.88 if is_vertical else 0.72))
        clip_h = int(height * (0.75 if is_vertical else 0.78))

        # Fonts
        title_font_size = max(24, int(clip_h * 0.045))
        headline_font_size = max(32, int(clip_w * (0.055 if is_vertical else 0.048)))
        body_font_size = max(14, int(clip_h * 0.024))
        date_font_size = max(12, int(clip_h * 0.020))

        masthead_font = _get_font(_SERIF_FONTS, title_font_size)
        headline_font = _get_font(_SERIF_FONTS, headline_font_size)
        body_font = _get_font(_SERIF_FONTS, body_font_size)
        date_font = _get_font(_MONO_FONTS, date_font_size)

        # Pre-render static clipping on an RGBA canvas
        paper_canvas = Image.new("RGBA", (clip_w, clip_h), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(paper_canvas)

        # Aged paper background color
        paper_bg = (245, 240, 228, 255)
        p_draw.rectangle([10, 10, clip_w - 10, clip_h - 10], fill=paper_bg)

        # Subtle paper aging grain
        np_noise = np.random.randint(-8, 9, (clip_h, clip_w, 3), dtype=np.int16)
        paper_img = np.array(paper_canvas)
        for c in range(3):
            paper_img[:, :, c] = np.clip(paper_img[:, :, c].astype(np.int16) + np_noise[:, :, c], 0, 255)
        paper_canvas = Image.fromarray(paper_img.astype(np.uint8))
        p_draw = ImageDraw.Draw(paper_canvas)

        # Decorative borders / newspaper masthead
        margin_x = 40
        curr_y = 35

        masthead_text = "THE INVESTIGATIVE CHRONICLE"
        p_draw.text((clip_w // 2, curr_y), masthead_text, fill=(30, 28, 26), font=masthead_font, anchor="mt")
        curr_y += title_font_size + 12

        # Date & volume line
        p_draw.line([(margin_x, curr_y), (clip_w - margin_x, curr_y)], fill=(80, 75, 70), width=2)
        curr_y += 6
        p_draw.text((margin_x + 5, curr_y), "SPECIAL ARCHIVAL DISPATCH // VOL. XLVIII", fill=(90, 85, 80), font=date_font)
        p_draw.text((clip_w - margin_x - 5, curr_y), "EVIDENCE RECORD", fill=(90, 85, 80), font=date_font, anchor="rt")
        curr_y += date_font_size + 8
        p_draw.line([(margin_x, curr_y), (clip_w - margin_x, curr_y)], fill=(80, 75, 70), width=3)
        curr_y += 24

        # Wrap and draw Headline
        clean_headline = headline.strip().upper()
        headline_lines = _wrap_text(clean_headline, headline_font, clip_w - (margin_x * 2), p_draw)
        headline_line_boxes = []

        for line in headline_lines[:4]:
            bbox = p_draw.textbbox((margin_x, curr_y), line, font=headline_font)
            headline_line_boxes.append((bbox, line))
            p_draw.text((margin_x, curr_y), line, fill=(15, 14, 12), font=headline_font)
            curr_y += (bbox[3] - bbox[1]) + 10

        curr_y += 12
        p_draw.line([(margin_x, curr_y), (clip_w - margin_x, curr_y)], fill=(120, 115, 110), width=1)
        curr_y += 18

        # Simulated columns of newsprint text
        cols = 2 if clip_w < 900 else 3
        col_w = (clip_w - (margin_x * 2) - ((cols - 1) * 25)) // cols
        col_start_y = curr_y

        sub_clean = subtext or "Official records, timeline telemetry, and declassified witness accounts confirm the anomalous events documented in this forensic inquiry."
        sub_words = sub_clean.split()

        for c_idx in range(cols):
            cx = margin_x + c_idx * (col_w + 25)
            cy = col_start_y
            sample_text = " ".join(sub_words[(c_idx * 15):((c_idx + 1) * 15 + 10)]) or sub_clean
            col_lines = _wrap_text(sample_text, body_font, col_w, p_draw)
            for cl in col_lines[:8]:
                if cy + body_font_size > clip_h - 40:
                    break
                p_draw.text((cx, cy), cl, fill=(45, 42, 38), font=body_font)
                cy += body_font_size + 6

        # Generate frames with animated highlighter sweep and camera motion
        bg_dark = (14, 18, 24)
        for frame_idx in range(total_frames):
            t = frame_idx / max(1, total_frames - 1)

            # Master 1080p background
            frame = Image.new("RGBA", (width, height), bg_dark)

            # Copy paper canvas to apply time-dependent highlighter
            p_frame = paper_canvas.copy()
            hl_layer = Image.new("RGBA", (clip_w, clip_h), (0, 0, 0, 0))
            hl_draw = ImageDraw.Draw(hl_layer)

            # Animated highlighter sweep across the first headline line
            if headline_line_boxes:
                target_box, _ = headline_line_boxes[0]
                box_x0, box_y0, box_x1, box_y1 = target_box
                sweep_progress = min(1.0, max(0.0, (t - 0.15) / 0.50))
                curr_x1 = box_x0 + (box_x1 - box_x0 + 20) * sweep_progress

                if sweep_progress > 0.0:
                    # Highlighter bar: fluorescent yellow with semi-transparency
                    hl_rect = [box_x0 - 8, box_y0 - 2, curr_x1, box_y1 + 4]
                    hl_draw.rectangle(hl_rect, fill=(255, 235, 40, 140))

            p_frame = Image.alpha_composite(p_frame, hl_layer)

            # Scotch tape strips at top-left and top-right corners
            tape_layer = Image.new("RGBA", (clip_w, clip_h), (0, 0, 0, 0))
            t_draw = ImageDraw.Draw(tape_layer)
            tape_color = (255, 250, 190, 130)
            t_draw.polygon([(20, 0), (90, 0), (75, 45), (5, 45)], fill=tape_color)
            t_draw.polygon([(clip_w - 90, 0), (clip_w - 20, 0), (clip_w - 5, 45), (clip_w - 75, 45)], fill=tape_color)
            p_frame = Image.alpha_composite(p_frame, tape_layer)

            # Slight static paper rotation (1.2 degrees for authentic collage tilt)
            rotated_paper = p_frame.rotate(1.2, expand=True, resample=Image.BICUBIC)

            # Ken Burns camera zoom and drift over time
            zoom = 1.0 + (0.07 * t)
            target_w = int(rotated_paper.width * zoom)
            target_h = int(rotated_paper.height * zoom)
            scaled_paper = rotated_paper.resize((target_w, target_h), Image.BILINEAR)

            # Center position with slight lateral drift
            drift_x = int((t - 0.5) * 40)
            drift_y = int((t - 0.5) * 20)
            pos_x = (width - target_w) // 2 + drift_x
            pos_y = (height - target_h) // 2 + drift_y

            # Paste rotated paper onto dark desk with alpha
            frame.paste(scaled_paper, (pos_x, pos_y), scaled_paper)

            frame_rgb = frame.convert("RGB")
            frame_rgb.save(frames_dir / f"frame_{frame_idx:04d}.jpg", quality=90)

        # Assemble into MP4 with FFmpeg
        out_clip = self._encode_frames(frames_dir, dest_video, fps, duration)
        return out_clip

    # ------------------------------------------------------------------
    # 2. Declassified Forensic Dossier with Stamped Seal
    # ------------------------------------------------------------------

    def render_declassified_dossier(
        self,
        topic: str = "",
        document_body: str = "",
        dest_video: Optional[Path] = None,
        duration: float = 4.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        stamp_text: str = "DECLASSIFIED",
        scene_id: str = "",
        case_title: Optional[str] = None,
        paragraphs: Optional[List[str]] = None,
        **kwargs,
    ) -> Optional[Path]:
        """
        Renders an authentic government declassified document dossier:
        - Typewriter text styling
        - Black redaction marker lines
        - Stamped red ink seal slamming down
        - File classification header and tracking number
        """
        if case_title and not topic:
            topic = case_title
        if paragraphs and not document_body:
            document_body = "\n\n".join(str(p) for p in paragraphs)
        if not topic:
            topic = "CLASSIFIED ARCHIVE"
        if not _PIL_AVAILABLE:
            print("[VoxMotion] Pillow not installed — skipping dossier collage.")
            return None

        if dest_video is None:
            key = abs(hash(f"dossier_{topic}_{document_body[:30]}_{scene_id}_{duration}_{width}x{height}"))
            dest_video = self.cache_dir / f"vox_dossier_{key}.mp4"

        if dest_video.exists() and dest_video.stat().st_size > 15000:
            return dest_video

        frames_dir = self.cache_dir / f"dossier_frames_{abs(hash(str(dest_video)))}"
        frames_dir.mkdir(parents=True, exist_ok=True)

        total_frames = int(duration * fps)
        is_vertical = height > width

        # Document canvas dimensions
        doc_w = int(width * (0.86 if is_vertical else 0.68))
        doc_h = int(height * (0.80 if is_vertical else 0.82))

        header_font = _get_font(_MONO_FONTS, max(18, int(doc_h * 0.028)))
        mono_font = _get_font(_MONO_FONTS, max(15, int(doc_h * 0.023)))
        stamp_font = _get_font(_SANS_FONTS, max(42, int(doc_w * 0.075)))

        # Pre-render static base dossier
        dossier = Image.new("RGBA", (doc_w, doc_h), (242, 237, 222, 255))
        d_draw = ImageDraw.Draw(dossier)

        # File header
        pad_x = 45
        pad_y = 40
        d_draw.text((pad_x, pad_y), "DECLASSIFIED UNDER FREEDOM OF INFORMATION ACT // SEC. 552", fill=(120, 40, 40), font=header_font)
        pad_y += 30
        d_draw.text((pad_x, pad_y), f"FILE NO: AR-{abs(hash(topic))%90000+10000} // TOPIC: {topic.upper()[:28]}", fill=(60, 55, 50), font=header_font)
        pad_y += 28
        d_draw.line([(pad_x, pad_y), (doc_w - pad_x, pad_y)], fill=(90, 80, 70), width=2)
        pad_y += 32

        # Text paragraphs with redactions
        body_text = document_body or (
            f"Official telemetry logs concerning {topic} confirm unprecedented anomalies. "
            "Primary instruments recorded severe magnetic distortion across all navigational channels. "
            "Classified military reports obtained under executive order indicate that critical event records "
            "were sequestered pending forensic analysis by defense intelligence."
        )

        lines = _wrap_text(body_text, mono_font, doc_w - (pad_x * 2), d_draw)
        redact_lines = {1, 3, 5}  # Indices to black out partially

        for idx, line in enumerate(lines[:12]):
            if pad_y + 24 > doc_h - 40:
                break
            d_draw.text((pad_x, pad_y), line, fill=(35, 32, 28), font=mono_font)

            # Redaction marker bar
            if idx in redact_lines:
                bbox = d_draw.textbbox((pad_x, pad_y), line, font=mono_font)
                redact_w = int((bbox[2] - bbox[0]) * 0.75)
                d_draw.rectangle([bbox[0], bbox[1] - 1, bbox[0] + redact_w, bbox[3] + 2], fill=(15, 15, 15))

            pad_y += 26

        # Create Stamp Graphic
        stamp_w, stamp_h = int(doc_w * 0.65), int(doc_h * 0.22)
        stamp_img = Image.new("RGBA", (stamp_w, stamp_h), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(stamp_img)

        # Red rubber stamp box + text
        red_ink = (210, 30, 30, 220)
        s_draw.rectangle([6, 6, stamp_w - 6, stamp_h - 6], outline=red_ink, width=8)
        s_draw.text((stamp_w // 2, stamp_h // 2), stamp_text, fill=red_ink, font=stamp_font, anchor="mm")

        # Distressed stamp rotation (-14 degrees)
        stamp_rotated = stamp_img.rotate(-14, expand=True, resample=Image.BICUBIC)

        bg_dark = (12, 16, 22)
        stamp_drop_frame = int(total_frames * 0.25)

        for frame_idx in range(total_frames):
            t = frame_idx / max(1, total_frames - 1)
            frame = Image.new("RGBA", (width, height), bg_dark)

            p_frame = dossier.copy()

            # Slam stamp down at drop frame
            if frame_idx >= stamp_drop_frame:
                # Stamp slam impact scale
                impact_age = frame_idx - stamp_drop_frame
                if impact_age < 4:
                    scale = 1.3 - (impact_age * 0.1)
                else:
                    scale = 1.0

                s_w = int(stamp_rotated.width * scale)
                s_h = int(stamp_rotated.height * scale)
                scaled_stamp = stamp_rotated.resize((s_w, s_h), Image.BILINEAR)

                stamp_x = (doc_w - s_w) // 2 + 10
                stamp_y = (doc_h - s_h) // 2 - 20
                p_frame.paste(scaled_stamp, (stamp_x, stamp_y), scaled_stamp)

            # Ken Burns camera motion
            zoom = 1.0 + (0.06 * t)
            target_w = int(p_frame.width * zoom)
            target_h = int(p_frame.height * zoom)
            scaled_dossier = p_frame.resize((target_w, target_h), Image.BILINEAR)

            pos_x = (width - target_w) // 2 + int((t - 0.5) * 30)
            pos_y = (height - target_h) // 2 + int((t - 0.5) * 15)

            frame.paste(scaled_dossier, (pos_x, pos_y), scaled_dossier)

            frame_rgb = frame.convert("RGB")
            frame_rgb.save(frames_dir / f"frame_{frame_idx:04d}.jpg", quality=90)

        out_clip = self._encode_frames(frames_dir, dest_video, fps, duration)
        return out_clip

    # ------------------------------------------------------------------
    # 3. Polaroid Evidence Pinboard Slide
    # ------------------------------------------------------------------

    def render_polaroid_evidence(
        self,
        label: str,
        dest_video: Optional[Path] = None,
        duration: float = 4.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        scene_id: str = "",
        image_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Renders a retro Polaroid evidence card:
        - Polaroid border with bottom handwritten ink label
        - Red push-pin at top center
        - Investigation cork/slate board backdrop
        - Smooth slide-in and settling camera motion
        """
        if not _PIL_AVAILABLE:
            print("[VoxMotion] Pillow not installed — skipping polaroid collage.")
            return None

        if dest_video is None:
            key = abs(hash(f"polaroid_{label}_{scene_id}_{duration}_{width}x{height}"))
            dest_video = self.cache_dir / f"vox_polaroid_{key}.mp4"

        if dest_video.exists() and dest_video.stat().st_size > 15000:
            return dest_video

        frames_dir = self.cache_dir / f"polaroid_frames_{abs(hash(str(dest_video)))}"
        frames_dir.mkdir(parents=True, exist_ok=True)

        total_frames = int(duration * fps)
        is_vertical = height > width

        # Polaroid dimensions
        card_w = int(width * (0.65 if is_vertical else 0.42))
        card_h = int(card_w * 1.22)
        inner_w = int(card_w * 0.86)
        inner_h = int(card_w * 0.86)

        label_font = _get_font(_MONO_FONTS, max(16, int(card_w * 0.055)))

        # Build Polaroid Card
        card = Image.new("RGBA", (card_w, card_h), (248, 246, 240, 255))
        c_draw = ImageDraw.Draw(card)

        # Image window
        win_x = (card_w - inner_w) // 2
        win_y = (card_w - inner_w) // 2 + 10

        if image_path and Path(image_path).exists():
            try:
                photo = Image.open(image_path).convert("RGB")
                photo = photo.resize((inner_w, inner_h), Image.LANCZOS)
                card.paste(photo, (win_x, win_y))
            except Exception:
                c_draw.rectangle([win_x, win_y, win_x + inner_w, win_y + inner_h], fill=(30, 40, 50))
        else:
            # Procedural blueprint / sonar texture inside window
            c_draw.rectangle([win_x, win_y, win_x + inner_w, win_y + inner_h], fill=(24, 32, 44))
            for grid_i in range(win_x, win_x + inner_w, 30):
                c_draw.line([(grid_i, win_y), (grid_i, win_y + inner_h)], fill=(40, 52, 70), width=1)
            for grid_j in range(win_y, win_y + inner_h, 30):
                c_draw.line([(win_x, grid_j), (win_x + inner_w, grid_j)], fill=(40, 52, 70), width=1)
            c_draw.text((win_x + inner_w // 2, win_y + inner_h // 2), "ARCHIVAL RECORD", fill=(120, 150, 180), font=label_font, anchor="mm")

        # Handwritten bottom label
        clean_label = label[:32].upper()
        c_draw.text((card_w // 2, card_h - 45), clean_label, fill=(20, 20, 25), font=label_font, anchor="mm")

        # Red Push-Pin with drop shadow
        pin_radius = max(8, int(card_w * 0.025))
        pin_x, pin_y = card_w // 2, 16
        c_draw.ellipse([pin_x - pin_radius + 2, pin_y - pin_radius + 4, pin_x + pin_radius + 2, pin_y + pin_radius + 4], fill=(0, 0, 0, 100))
        c_draw.ellipse([pin_x - pin_radius, pin_y - pin_radius, pin_x + pin_radius, pin_y + pin_radius], fill=(220, 35, 35))
        c_draw.ellipse([pin_x - pin_radius // 2, pin_y - pin_radius // 2, pin_x, pin_y], fill=(255, 120, 120))

        # Rotate card slightly for collage angle
        card_rotated = card.rotate(-4.0, expand=True, resample=Image.BICUBIC)

        bg_slate = (10, 14, 20)
        for frame_idx in range(total_frames):
            t = frame_idx / max(1, total_frames - 1)
            frame = Image.new("RGBA", (width, height), bg_slate)

            # Animate entry: smooth slide-in from top-left, then gentle float
            entry_progress = min(1.0, t / 0.35)
            # ease-out
            eased = 1.0 - math.pow(1.0 - entry_progress, 3)

            start_offset = -int(height * 0.3)
            current_offset = int(start_offset * (1.0 - eased))

            zoom = 1.0 + (0.05 * t)
            target_w = int(card_rotated.width * zoom)
            target_h = int(card_rotated.height * zoom)
            scaled_card = card_rotated.resize((target_w, target_h), Image.BILINEAR)

            pos_x = (width - target_w) // 2 + int((t - 0.5) * 25)
            pos_y = (height - target_h) // 2 + current_offset

            frame.paste(scaled_card, (pos_x, pos_y), scaled_card)

            frame_rgb = frame.convert("RGB")
            frame_rgb.save(frames_dir / f"frame_{frame_idx:04d}.jpg", quality=90)

        out_clip = self._encode_frames(frames_dir, dest_video, fps, duration)
        return out_clip

    # ------------------------------------------------------------------
    # 4. Jitter-Inspired Kinetic Headline Reveal
    # ------------------------------------------------------------------

    def render_kinetic_headline(
        self,
        headline: str,
        category_tag: str = "OFFICIAL RECORD",
        subtext: str = "",
        dest_video: Optional[Path] = None,
        duration: float = 4.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        scene_id: str = "",
        accent_color: Tuple[int, int, int] = (0, 255, 136),
        bg_image_path: Optional[Union[str, Path]] = None,
        overwrite: bool = False,
    ) -> Optional[Path]:
        """
        Jitter-inspired kinetic typography reveal:
        - Composited over authentic historical imagery with a sleek dark scrim
        - Category pill badge with smooth scale & fade-in
        - Bold kinetic headline with spring overshoot scale
        - Animated accent underline sweep
        - Continuous subtle camera push-in
        - Positioned in upper-mid safe-zone for vertical shorts
        """
        if not _PIL_AVAILABLE:
            return None

        if dest_video is None:
            key = abs(hash(f"kinetic_{headline}_{category_tag}_{scene_id}_{duration}_{width}x{height}_{bg_image_path}"))
            dest_video = self.cache_dir / f"vox_kinetic_{key}.mp4"

        if not overwrite and dest_video.exists() and dest_video.stat().st_size > 15000:
            return dest_video

        frames_dir = self.cache_dir / f"kinetic_frames_{abs(hash(str(dest_video)))}"
        frames_dir.mkdir(parents=True, exist_ok=True)

        total_frames = int(duration * fps)
        is_vertical = height > width

        # Base layout & font sizing
        tag_font_size = max(18, int(width * 0.020 if not is_vertical else width * 0.036))
        head_font_size = max(38, int(width * 0.050 if not is_vertical else width * 0.072))
        sub_font_size = max(18, int(width * 0.022 if not is_vertical else width * 0.036))

        tag_font = _get_font(_SANS_FONTS, tag_font_size)
        head_font = _get_font(["Impact", "Arial Black"] + _SANS_FONTS, head_font_size)
        sub_font = _get_font(_SANS_FONTS, sub_font_size)

        max_text_w = int(width * (0.86 if is_vertical else 0.75))

        bg_raw = None
        if bg_image_path and Path(bg_image_path).exists():
            try:
                bg_raw = Image.open(bg_image_path).convert("RGB")
            except Exception:
                bg_raw = None

        for frame_idx in range(total_frames):
            t = frame_idx / max(1, total_frames - 1)
            cam_zoom = 1.0 + 0.05 * t

            if bg_raw:
                # Dynamic Ken Burns push-in on background image
                crop_w = int(bg_raw.width / cam_zoom)
                crop_h = int(bg_raw.height / cam_zoom)
                cx = (bg_raw.width - crop_w) // 2
                cy_bg = (bg_raw.height - crop_h) // 2
                cropped = bg_raw.crop((cx, cy_bg, cx + crop_w, cy_bg + crop_h)).resize((width, height), Image.BILINEAR)
                # Dark translucent scrim to guarantee text legibility
                scrim = Image.new("RGBA", (width, height), (10, 14, 20, 165))
                frame = Image.alpha_composite(cropped.convert("RGBA"), scrim).convert("RGB")
            else:
                # Dark modern backdrop
                frame = Image.new("RGB", (width, height), (14, 17, 22))
                draw_tmp = ImageDraw.Draw(frame)
                grid_spacing = 60
                for gx in range(0, width, grid_spacing):
                    draw_tmp.line([(gx, 0), (gx, height)], fill=(22, 26, 34), width=1)
                for gy in range(0, height, grid_spacing):
                    draw_tmp.line([(0, gy), (width, gy)], fill=(22, 26, 34), width=1)

            draw = ImageDraw.Draw(frame)

            # Kinetic entry timing (0 to 0.4s)
            entry_t = min(1.0, (frame_idx / fps) / 0.4)
            spring = 1.0 - math.pow(2, -10 * entry_t) * math.cos(3 * math.pi * entry_t)
            spring = max(0.0, spring)

            # Center position (elevated in vertical mode for subtitle clearance)
            cy = int(height * 0.36) if is_vertical else (height // 2 - int(head_font_size * 0.8))

            # 1. Category Pill Badge
            tag_text = category_tag.upper()
            try:
                tbox = draw.textbbox((0, 0), tag_text, font=tag_font)
                tw, th = tbox[2] - tbox[0], tbox[3] - tbox[1]
            except Exception:
                tw, th = len(tag_text) * 10, tag_font_size

            pill_pad_x, pill_pad_y = 16, 6
            pill_w = tw + pill_pad_x * 2
            pill_h = th + pill_pad_y * 2
            pill_x = (width - pill_w) // 2
            pill_y = cy - pill_h - 24

            pill_alpha = min(1.0, entry_t * 1.5)
            if pill_alpha > 0.05:
                draw.rounded_rectangle(
                    [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
                    radius=pill_h // 2,
                    fill=(30, 38, 48),
                    outline=accent_color,
                    width=2,
                )
                draw.text((pill_x + pill_pad_x, pill_y + pill_pad_y), tag_text, fill=accent_color, font=tag_font)

            # 2. Kinetic Headline with wrapped lines
            wrapped_heads = _wrap_text(headline, head_font, max_text_w, draw)
            head_y = cy
            line_spacing = int(head_font_size * 1.25)

            for line in wrapped_heads:
                try:
                    lbox = draw.textbbox((0, 0), line, font=head_font)
                    lw = lbox[2] - lbox[0]
                except Exception:
                    lw = len(line) * (head_font_size // 2)
                lx = (width - lw) // 2
                draw.text((lx, head_y), line, fill=(245, 248, 252), font=head_font)
                head_y += line_spacing

            # 3. Animated Accent Underline Sweep
            sweep_progress = min(1.0, max(0.0, ((frame_idx / fps) - 0.25) / 0.5))
            if sweep_progress > 0:
                line_w = int(max_text_w * 0.7 * sweep_progress)
                line_x1 = (width - line_w) // 2
                draw.line([(line_x1, head_y + 8), (line_x1 + line_w, head_y + 8)], fill=accent_color, width=4)

            # 4. Subtext / Source Citation
            if subtext:
                sub_y = head_y + 28
                wrapped_sub = _wrap_text(subtext, sub_font, int(max_text_w * 0.9), draw)
                for sline in wrapped_sub[:2]:
                    try:
                        sbox = draw.textbbox((0, 0), sline, font=sub_font)
                        sw = sbox[2] - sbox[0]
                    except Exception:
                        sw = len(sline) * 9
                    sx = (width - sw) // 2
                    draw.text((sx, sub_y), sline, fill=(160, 170, 185), font=sub_font)
                    sub_y += int(sub_font_size * 1.3)

            frame.save(frames_dir / f"frame_{frame_idx:04d}.jpg", quality=92)

        out_clip = self._encode_frames(frames_dir, dest_video, fps, duration)
        return out_clip

    # ------------------------------------------------------------------
    # 5. Jitter-Inspired Stat Counter Card
    # ------------------------------------------------------------------

    def render_stat_counter_card(
        self,
        target_number: float,
        unit: str = "",
        label: str = "RECORDED TELEMETRY",
        subtitle: str = "Verified by military radar logs",
        dest_video: Optional[Path] = None,
        duration: float = 4.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        scene_id: str = "",
        is_integer: bool = True,
        bg_image_path: Optional[Union[str, Path]] = None,
        overwrite: bool = False,
    ) -> Optional[Path]:
        """
        Jitter-inspired frosted glass animated stat counter:
        - Composited over authentic historical imagery with a sleek dark scrim
        - Frosted glass container with rounded corners and glowing emerald border
        - Smooth numerical counter counting up from 0 to target_number
        - Progress indicator ring & glowing bar
        - Contextual label and documentary subtitle
        - Positioned in upper-mid safe-zone for vertical shorts
        """
        if not _PIL_AVAILABLE:
            return None

        if dest_video is None:
            key = abs(hash(f"counter_{target_number}_{unit}_{label}_{scene_id}_{duration}_{width}x{height}_{bg_image_path}"))
            dest_video = self.cache_dir / f"vox_counter_{key}.mp4"

        if not overwrite and dest_video.exists() and dest_video.stat().st_size > 15000:
            return dest_video

        frames_dir = self.cache_dir / f"counter_frames_{abs(hash(str(dest_video)))}"
        frames_dir.mkdir(parents=True, exist_ok=True)

        total_frames = int(duration * fps)
        is_vertical = height > width

        # Sizing
        card_w = int(width * (0.90 if is_vertical else 0.55))
        card_h = int(height * (0.35 if is_vertical else 0.48))

        num_font_size = max(56, int(card_h * 0.28))
        label_font_size = max(20, int(card_h * 0.08))
        sub_font_size = max(18, int(card_h * 0.06))

        # Dynamically calculate font size so target number + unit fits within card with padding
        max_num_w = card_w - 100
        sample_str = f"{int(round(target_number)):,}{unit}" if is_integer else f"{target_number:,.1f}{unit}"
        dummy_img = Image.new("RGB", (10, 10))
        d_test = ImageDraw.Draw(dummy_img)
        while num_font_size > 36:
            test_font = _get_font(["Impact", "Arial Black"] + _MONO_FONTS, num_font_size)
            try:
                tbox = d_test.textbbox((0, 0), sample_str, font=test_font)
                if (tbox[2] - tbox[0]) <= max_num_w:
                    num_font = test_font
                    break
            except Exception:
                num_font = test_font
                break
            num_font_size -= 4
        else:
            num_font = _get_font(["Impact", "Arial Black"] + _MONO_FONTS, num_font_size)

        label_font = _get_font(["Arial Black", "Impact"] + _SANS_FONTS, label_font_size)
        sub_font = _get_font(_SANS_FONTS, sub_font_size)

        bg_raw = None
        if bg_image_path and Path(bg_image_path).exists():
            try:
                bg_raw = Image.open(bg_image_path).convert("RGB")
            except Exception:
                bg_raw = None

        for frame_idx in range(total_frames):
            t = frame_idx / max(1, total_frames - 1)
            cam_zoom = 1.0 + 0.05 * t

            if bg_raw:
                crop_w = int(bg_raw.width / cam_zoom)
                crop_h = int(bg_raw.height / cam_zoom)
                cx = (bg_raw.width - crop_w) // 2
                cy_bg = (bg_raw.height - crop_h) // 2
                cropped = bg_raw.crop((cx, cy_bg, cx + crop_w, cy_bg + crop_h)).resize((width, height), Image.BILINEAR)
                scrim = Image.new("RGBA", (width, height), (10, 14, 20, 160))
                frame = Image.alpha_composite(cropped.convert("RGBA"), scrim).convert("RGB")
            else:
                frame = Image.new("RGB", (width, height), (12, 14, 18))

            # Card position (elevated in vertical shorts for lower-third subtitle safety)
            card_x1 = (width - card_w) // 2
            card_y1 = int(height * 0.18) if is_vertical else (height - card_h) // 2
            card_x2 = card_x1 + card_w
            card_y2 = card_y1 + card_h

            # Glass card background with glowing emerald border
            card_overlay = Image.new("RGBA", (card_w, card_h), (18, 24, 34, 235))
            c_draw = ImageDraw.Draw(card_overlay)
            c_draw.rounded_rectangle(
                [0, 0, card_w, card_h],
                radius=24,
                fill=(18, 24, 34, 235),
                outline=(0, 230, 150),
                width=3,
            )
            frame_rgba = frame.convert("RGBA")
            frame_rgba.paste(card_overlay, (card_x1, card_y1), card_overlay)
            frame = frame_rgba.convert("RGB")
            draw = ImageDraw.Draw(frame)

            # Counter progression with cubic ease-out
            count_progress = min(1.0, (frame_idx / fps) / max(0.5, duration * 0.6))
            ease_progress = 1.0 - math.pow(1.0 - count_progress, 3)
            current_val = target_number * ease_progress

            if is_integer:
                val_str = f"{int(round(current_val)):,}{unit}"
            else:
                val_str = f"{current_val:,.1f}{unit}"

            # Top label badge
            cy = card_y1 + 45
            draw.text((card_x1 + 45, cy), label.upper(), fill=(0, 255, 150), font=label_font)

            # Big numeric readout
            cy += label_font_size + 24
            draw.text((card_x1 + 45, cy), val_str, fill=(255, 255, 255), font=num_font)

            # Progress bar under number
            cy += num_font_size + 25
            bar_w = card_w - 90
            draw.rounded_rectangle(
                [card_x1 + 45, cy, card_x1 + 45 + bar_w, cy + 8],
                radius=4,
                fill=(35, 45, 60),
            )
            prog_w = int(bar_w * ease_progress)
            if prog_w > 0:
                draw.rounded_rectangle(
                    [card_x1 + 45, cy, card_x1 + 45 + prog_w, cy + 8],
                    radius=4,
                    fill=(0, 255, 150),
                )

            # Subtitle
            cy += 28
            if subtitle:
                draw.text((card_x1 + 45, cy), subtitle, fill=(200, 215, 230), font=sub_font)

            frame.save(frames_dir / f"frame_{frame_idx:04d}.jpg", quality=90)

        out_clip = self._encode_frames(frames_dir, dest_video, fps, duration)
        return out_clip

    # ------------------------------------------------------------------
    # 6. Jitter-Inspired Editorial Lower-Third Tagline
    # ------------------------------------------------------------------

    def render_editorial_tagline(
        self,
        title: str,
        category: str = "DEEP INVESTIGATION",
        subtitle: str = "Declassified Military Intelligence",
        dest_video: Optional[Path] = None,
        duration: float = 4.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        scene_id: str = "",
    ) -> Optional[Path]:
        """
        Jitter-inspired minimalist documentary lower-third card:
        - Smooth slide-in from bottom-left
        - High-contrast typography with crisp border
        - Category tag + primary title + source subtitle
        """
        if not _PIL_AVAILABLE:
            return None

        if dest_video is None:
            key = abs(hash(f"tagline_{title}_{category}_{scene_id}_{duration}_{width}x{height}"))
            dest_video = self.cache_dir / f"vox_tagline_{key}.mp4"

        if dest_video.exists() and dest_video.stat().st_size > 15000:
            return dest_video

        frames_dir = self.cache_dir / f"tagline_frames_{abs(hash(str(dest_video)))}"
        frames_dir.mkdir(parents=True, exist_ok=True)

        total_frames = int(duration * fps)
        is_vertical = height > width

        card_w = int(width * (0.86 if is_vertical else 0.52))
        card_h = int(height * (0.18 if is_vertical else 0.16))

        tag_font_size = max(12, int(card_h * 0.15))
        title_font_size = max(20, int(card_h * 0.32))
        sub_font_size = max(12, int(card_h * 0.16))

        tag_font = _get_font(_SANS_FONTS, tag_font_size)
        title_font = _get_font(_SANS_FONTS, title_font_size)
        sub_font = _get_font(_SERIF_FONTS, sub_font_size)

        for frame_idx in range(total_frames):
            t = frame_idx / max(1, total_frames - 1)
            frame = Image.new("RGB", (width, height), (15, 17, 21))
            draw = ImageDraw.Draw(frame)

            # Slide-in animation from bottom
            entry_t = min(1.0, (frame_idx / fps) / 0.45)
            slide_offset = int((1.0 - math.pow(1.0 - entry_t, 3)) * (card_h + 40))

            card_x = int(width * 0.07)
            card_y = height - slide_offset

            # Card background
            draw.rounded_rectangle(
                [card_x, card_y, card_x + card_w, card_y + card_h],
                radius=14,
                fill=(245, 247, 250),
                outline=(200, 205, 215),
                width=1,
            )

            # Inner text
            tx = card_x + 28
            ty = card_y + 18

            # Category pill
            draw.text((tx, ty), category.upper(), fill=(100, 110, 125), font=tag_font)
            ty += tag_font_size + 8

            # Main title
            draw.text((tx, ty), title[:45], fill=(20, 25, 35), font=title_font)
            ty += title_font_size + 6

            # Subtitle
            if subtitle:
                draw.text((tx, ty), subtitle[:55], fill=(80, 90, 105), font=sub_font)

            frame.save(frames_dir / f"frame_{frame_idx:04d}.jpg", quality=90)

        out_clip = self._encode_frames(frames_dir, dest_video, fps, duration)
        return out_clip

    # ------------------------------------------------------------------
    # Dispatcher: Automatic Archetype & Template Selection
    # ------------------------------------------------------------------

    def render_vox_scene(
        self,
        topic: str,
        narration: str,
        dest_video: Path,
        duration: float = 4.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        scene_id: str = "",
        style: str = "auto",
        photo_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Smart dispatcher that routes to the most effective Vox paper-collage or
        Jitter kinetic motion graphic style based on narrative intent.
        """
        text_lower = (narration + " " + topic).lower()

        if style == "auto":
            # Check for numbers / stats / meters / percent
            num_match = re.search(r"\b(\d+[\d,]*(?:\.\d+)?)\s*(meters|feet|percent|%|ft|m|knots|miles|km|hours|seconds|depth)?\b", text_lower)
            if num_match and any(k in text_lower for k in ["recorded", "reached", "depth", "distance", "speed", "altitude", "percent", "rate"]):
                style = "stat_counter"
            elif any(k in text_lower for k in ["breaking", "announced", "officially", "declared", "headline", "news", "press"]):
                style = "newspaper"
            elif any(k in text_lower for k in ["photo", "witness", "sighting", "seen", "image", "recovered", "polaroid"]):
                style = "polaroid"
            elif any(k in text_lower for k in ["classified", "dossier", "file", "telegram", "memo", "redacted"]):
                style = "dossier"
            else:
                style = "kinetic_headline"

        if style == "newspaper":
            headline = narration.split(".")[0] if narration else topic
            return self.render_newspaper_clipping(
                headline=headline[:60],
                subtext=narration,
                dest_video=dest_video,
                duration=duration,
                width=width,
                height=height,
                fps=fps,
                scene_id=scene_id,
            )
        elif style == "polaroid":
            label = narration.split()[0:4]
            return self.render_polaroid_evidence(
                label=" ".join(label),
                dest_video=dest_video,
                duration=duration,
                width=width,
                height=height,
                fps=fps,
                scene_id=scene_id,
                image_path=photo_path,
            )
        elif style == "stat_counter":
            # Extract number if possible
            num_match = re.search(r"(\d+[\d,]*(?:\.\d+)?)", narration)
            val = float(num_match.group(1).replace(",", "")) if num_match else 100.0
            return self.render_stat_counter_card(
                target_number=val,
                unit="",
                label=topic[:30],
                subtitle=narration[:60],
                dest_video=dest_video,
                duration=duration,
                width=width,
                height=height,
                fps=fps,
                scene_id=scene_id,
                bg_image_path=photo_path,
            )
        elif style == "kinetic_headline":
            return self.render_kinetic_headline(
                headline=narration.split(".")[0] if narration else topic,
                category_tag=topic[:25],
                subtext=narration,
                dest_video=dest_video,
                duration=duration,
                width=width,
                height=height,
                fps=fps,
                scene_id=scene_id,
                bg_image_path=photo_path,
            )
        else:
            return self.render_declassified_dossier(
                topic=topic,
                document_body=narration,
                dest_video=dest_video,
                duration=duration,
                width=width,
                height=height,
                fps=fps,
                scene_id=scene_id,
            )

    # ------------------------------------------------------------------
    # Template Catalog Access (Curated Jitter Templates)
    # ------------------------------------------------------------------

    @staticmethod
    def get_available_motion_templates(category: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Query the 452 curated motion graphics templates crawled from Jitter.
        Categories: 'kinetic_typography', 'infographics_and_stats', 'editorial_and_archival',
                    'hud_and_lower_thirds', 'cinematic_transitions'.
        """
        asset_file = Path(__file__).parent / "assets" / "curated_motion_templates.json"
        if not asset_file.exists():
            return []
        try:
            import json
            data = json.loads(asset_file.read_text(encoding="utf-8"))
            if category:
                return data.get(category.lower(), [])
            all_templates = []
            for cat_list in data.values():
                all_templates.extend(cat_list)
            return all_templates
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Internal FFmpeg Encoding
    # ------------------------------------------------------------------

    def _encode_frames(
        self, frames_dir: Path, dest_video: Path, fps: int, duration: float
    ) -> Optional[Path]:
        """Encode JPG sequence to H.264 silent MP4 via FFmpeg."""
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
        except Exception as e:
            print(f"[VoxMotion] FFmpeg encode warning: {e}")
        return None

