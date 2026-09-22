"""
Canva Video Templates Engine for Documentary AI
------------------------------------------------
Provides Canva-inspired high-retention video templates for documentaries, explainer shorts,
and vertical reels:
1. Split-Screen Comparison (Before vs After, Myth vs Fact, Historical Era Comparison)
2. "Did You Know?" Curiosity Hook Card (Viral fact hook with animated highlighter)
3. Historical Quote & Testimony Card (Editorial quote marks, author badge, historical title)
4. Ranked Countdown / Listicle Step Card (Bold numeric step counter, progress accent line)
5. Breaking News / Historic Bulletin Alert (Pulsing red alert banner, animated bottom ticker)

Pure local CPU rendering: Pillow + NumPy + FFmpeg.
Supports 1080x1920 (9:16 vertical) and 1920x1080 (16:9 horizontal).
"""

from __future__ import annotations
import math
import subprocess
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, List, Tuple, Optional


class CanvaTemplateEngine:
    """
    Canva-Inspired Procedural Motion Graphics Template Engine.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or (Path("workspace") / "canva_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_font(self, size: int, bold: bool = False, serif: bool = False) -> ImageFont.ImageFont:
        fonts_dir = Path(__file__).resolve().parent.parent / "assets" / "fonts"
        if serif:
            primary_cands = [fonts_dir / "Cinzel-Bold.ttf"]
            font_names = [
                "georgiab.ttf" if bold else "georgia.ttf",
                "timesbd.ttf" if bold else "times.ttf",
                "DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf",
            ]
        else:
            primary_cands = [fonts_dir / "Montserrat-Bold.ttf", fonts_dir / "Inter-Bold.ttf"]
            font_names = [
                "arialbd.ttf" if bold else "arial.ttf",
                "segoeuib.ttf" if bold else "segoeui.ttf",
                "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
            ]
        for p in primary_cands:
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), size)
                except Exception:
                    pass
        for name in font_names:
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                pass
        return ImageFont.load_default()

    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
        words = text.split()
        if not words:
            return []
        lines = []
        curr = words[0]
        for w in words[1:]:
            test_line = curr + " " + w
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if (bbox[2] - bbox[0]) <= max_width:
                curr = test_line
            else:
                lines.append(curr)
                curr = w
        lines.append(curr)
        return lines

    def render_comparison_video(
        self,
        title_a: str,
        desc_a: str,
        title_b: str,
        desc_b: str,
        dest_video: Path,
        duration: float = 3.0,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        main_header: str = "HISTORICAL COMPARISON",
    ) -> Path:
        """
        Canva Split-Screen Comparison Template (Side A vs Side B).
        Features:
        - Sleek header strap with high-contrast badge
        - Side A (Blue) vs Side B (Amber) cards with dynamic pill badges
        - Central animated 'VS' emblem with divider line
        """
        dest_video.parent.mkdir(parents=True, exist_ok=True)
        total_frames = max(1, int(duration * fps))

        frames_dir = self.cache_dir / f"compare_{abs(hash(title_a + title_b + str(duration)))}"
        frames_dir.mkdir(parents=True, exist_ok=True)

        is_vertical = height >= width

        font_header = self._get_font(int(width * 0.038), bold=True)
        font_sub = self._get_font(int(width * 0.024), bold=False)
        font_side_title = self._get_font(int(width * 0.040), bold=True)
        font_desc = self._get_font(int(width * 0.030), bold=False)
        font_vs = self._get_font(int(width * 0.045), bold=True)

        arr = np.zeros((height, width, 3), dtype=np.uint8)

        if is_vertical:
            split_point = height // 2
            # Top half: Deep Navy
            arr[:split_point, :, 0] = 15
            arr[:split_point, :, 1] = 23
            arr[:split_point, :, 2] = 42
            # Bottom half: Deep Dark Slate
            arr[split_point:, :, 0] = 26
            arr[split_point:, :, 1] = 24
            arr[split_point:, :, 2] = 22
        else:
            split_point = width // 2
            arr[:, :split_point, 0] = 15
            arr[:, :split_point, 1] = 23
            arr[:, :split_point, 2] = 42
            arr[:, split_point:, 0] = 26
            arr[:, split_point:, 1] = 24
            arr[:, split_point:, 2] = 22

        base_img = Image.fromarray(arr)

        for frame_idx in range(total_frames):
            frame = base_img.copy()
            draw = ImageDraw.Draw(frame)

            # 1. Top Header Banner
            top_y = int(height * 0.06)
            draw.rectangle([60, top_y, width - 60, top_y + 70], fill=(20, 30, 50))
            draw.rectangle([60, top_y, width - 60, top_y + 70], outline=(56, 189, 248), width=2)
            draw.text((85, top_y + 18), f"●  {main_header.upper()}", fill=(240, 248, 255), font=font_header)

            if is_vertical:
                # 2. Side A Card (Top Section)
                a_box_y = int(height * 0.14)
                card_h = int(height * 0.22)
                draw.rectangle([70, a_box_y, width - 70, a_box_y + card_h], fill=(24, 38, 64))
                draw.rectangle([70, a_box_y, width - 70, a_box_y + card_h], outline=(56, 189, 248), width=2)

                # Side A Tag Pill (measured dynamically)
                tag_a_text = title_a.upper()
                bbox_a = draw.textbbox((0, 0), tag_a_text, font=font_side_title)
                pill_w_a = (bbox_a[2] - bbox_a[0]) + 36
                pill_h_a = (bbox_a[3] - bbox_a[1]) + 20

                draw.rectangle([95, a_box_y + 20, 95 + pill_w_a, a_box_y + 20 + pill_h_a], fill=(56, 189, 248))
                draw.text((113, a_box_y + 28), tag_a_text, fill=(10, 15, 25), font=font_side_title)

                # Side A Description
                lines_a = self._wrap_text(desc_a, font_desc, width - 200, draw)
                for idx, line in enumerate(lines_a[:3]):
                    draw.text((100, a_box_y + 20 + pill_h_a + 22 + idx * 36), line, fill=(226, 232, 240), font=font_desc)

                # 3. Side B Card (Bottom Section)
                b_box_y = int(height * 0.48)
                draw.rectangle([70, b_box_y, width - 70, b_box_y + card_h], fill=(42, 34, 26))
                draw.rectangle([70, b_box_y, width - 70, b_box_y + card_h], outline=(251, 146, 60), width=2)

                # Side B Tag Pill (measured dynamically)
                tag_b_text = title_b.upper()
                bbox_b = draw.textbbox((0, 0), tag_b_text, font=font_side_title)
                pill_w_b = (bbox_b[2] - bbox_b[0]) + 36
                pill_h_b = (bbox_b[3] - bbox_b[1]) + 20

                draw.rectangle([95, b_box_y + 20, 95 + pill_w_b, b_box_y + 20 + pill_h_b], fill=(251, 146, 60))
                draw.text((113, b_box_y + 28), tag_b_text, fill=(20, 12, 5), font=font_side_title)

                # Side B Description
                lines_b = self._wrap_text(desc_b, font_desc, width - 200, draw)
                for idx, line in enumerate(lines_b[:3]):
                    draw.text((100, b_box_y + 20 + pill_h_b + 22 + idx * 36), line, fill=(243, 244, 246), font=font_desc)

                # 4. Central VS Divider Line & Animated Emblem
                div_y = int(height * 0.42)
                draw.line([(0, div_y), (width, div_y)], fill=(255, 255, 255), width=2)

                vs_radius = 42
                pulse = int(4 * math.sin(frame_idx * 0.3))
                cx = width // 2
                draw.ellipse([cx - vs_radius - pulse, div_y - vs_radius - pulse, cx + vs_radius + pulse, div_y + vs_radius + pulse], fill=(225, 29, 72))
                draw.ellipse([cx - vs_radius - pulse, div_y - vs_radius - pulse, cx + vs_radius + pulse, div_y + vs_radius + pulse], outline=(255, 255, 255), width=3)
                draw.text((cx - 24, div_y - 24), "VS", fill=(255, 255, 255), font=font_vs)

                # 5. Bottom Telemetry (Safe zone: strictly < 1530)
                draw.text((75, min(int(height * 0.74), 1420)), "CANVA EDITORIAL LAYOUT // VERIFIED HISTORICAL RECORDS", fill=(148, 163, 184), font=font_sub)

            frame_path = frames_dir / f"frame_{frame_idx:04d}.png"
            frame.save(frame_path)

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(frames_dir / "frame_%04d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "fast",
            str(dest_video)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        for f in frames_dir.glob("frame_*.png"):
            try:
                f.unlink()
            except Exception:
                pass
        try:
            frames_dir.rmdir()
        except Exception:
            pass

        return dest_video

    def render_curiosity_hook_video(
        self,
        headline: str,
        subtext: str,
        dest_video: Path,
        duration: float = 3.0,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        badge_text: str = "UNTOLD REALITY",
    ) -> Path:
        """
        Canva 'Did You Know?' Viral Curiosity Hook Card.
        Features:
        - Floating card with drop shadow
        - Neon pill badge measured dynamically
        - Animated keyword highlight sweep across the headline
        """
        dest_video.parent.mkdir(parents=True, exist_ok=True)
        total_frames = max(1, int(duration * fps))

        frames_dir = self.cache_dir / f"hook_{abs(hash(headline + str(duration)))}"
        frames_dir.mkdir(parents=True, exist_ok=True)

        font_badge = self._get_font(int(width * 0.030), bold=True)
        font_head = self._get_font(int(width * 0.046), bold=True)
        font_sub = self._get_font(int(width * 0.028), bold=False)
        font_footer = self._get_font(int(width * 0.022), bold=True)

        arr = np.zeros((height, width, 3), dtype=np.uint8)
        arr[:, :, 0] = 11
        arr[:, :, 1] = 15
        arr[:, :, 2] = 25
        base_canvas = Image.fromarray(arr)

        card_margin = int(width * 0.08)
        card_y = int(height * 0.24)
        card_w = width - card_margin * 2
        card_h = int(height * 0.42)

        for frame_idx in range(total_frames):
            frame = base_canvas.copy()
            draw = ImageDraw.Draw(frame)

            raw_t = frame_idx / float(total_frames - 1) if total_frames > 1 else 1.0

            # 1. Floating Card Shadow & Body
            draw.rectangle([card_margin + 6, card_y + 8, card_margin + card_w + 6, card_y + card_h + 8],
                           fill=(0, 0, 0))
            draw.rectangle([card_margin, card_y, card_margin + card_w, card_y + card_h],
                           fill=(18, 24, 38))
            draw.rectangle([card_margin, card_y, card_margin + card_w, card_y + card_h],
                           outline=(59, 130, 246), width=2)

            # 2. Top Pill Badge (Measured Dynamically)
            badge_str = f"●  {badge_text.upper()}"
            b_box = draw.textbbox((0, 0), badge_str, font=font_badge)
            pill_w = (b_box[2] - b_box[0]) + 36
            pill_x = card_margin + 36
            pill_y = card_y - 24
            draw.rectangle([pill_x, pill_y, pill_x + pill_w, pill_y + 46], fill=(234, 179, 8))
            draw.text((pill_x + 18, pill_y + 10), badge_str, fill=(15, 23, 42), font=font_badge)

            # 3. Main Headline with Animated Highlighter Sweep
            wrapped_heads = self._wrap_text(headline, font_head, card_w - 70, draw)
            head_start_y = card_y + 55
            hl_progress = min(1.0, max(0.0, (raw_t - 0.15) / 0.45))

            for i, line in enumerate(wrapped_heads[:3]):
                ly = head_start_y + i * 56
                if i == 0 and hl_progress > 0:
                    line_bbox = draw.textbbox((card_margin + 36, ly), line, font=font_head)
                    full_w = line_bbox[2] - line_bbox[0]
                    active_w = int(full_w * hl_progress)
                    draw.rectangle([card_margin + 34, ly + 4, card_margin + 34 + active_w, ly + 48],
                                   fill=(250, 204, 21))
                    draw.text((card_margin + 36, ly), line, fill=(15, 23, 42), font=font_head)
                else:
                    draw.text((card_margin + 36, ly), line, fill=(255, 255, 255), font=font_head)

            # 4. Explanatory Subtext
            sub_start_y = head_start_y + len(wrapped_heads[:3]) * 56 + 25
            wrapped_sub = self._wrap_text(subtext, font_sub, card_w - 70, draw)
            for j, sline in enumerate(wrapped_sub[:3]):
                draw.text((card_margin + 36, sub_start_y + j * 36), sline, fill=(203, 213, 225), font=font_sub)

            # 5. Bottom Verified Intel Tag
            draw.line([(card_margin + 36, card_y + card_h - 50), (card_margin + card_w - 36, card_y + card_h - 50)],
                      fill=(51, 65, 85), width=1)
            draw.text((card_margin + 36, card_y + card_h - 36), "OFFICIAL HISTORICAL DISCLOSURE // UNSEALED FILES",
                      fill=(148, 163, 184), font=font_footer)

            frame_path = frames_dir / f"frame_{frame_idx:04d}.png"
            frame.save(frame_path)

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(frames_dir / "frame_%04d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "fast",
            str(dest_video)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        for f in frames_dir.glob("frame_*.png"):
            try:
                f.unlink()
            except Exception:
                pass
        try:
            frames_dir.rmdir()
        except Exception:
            pass

        return dest_video

    def render_quote_card_video(
        self,
        quote_text: str,
        author: str,
        title_context: str,
        dest_video: Path,
        duration: float = 3.0,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
    ) -> Path:
        """
        Canva Editorial Quote Card Template.
        Features:
        - Large stylized typographic quotes (“ ”)
        - Serif quote body text
        - Author attribution with title strap
        """
        dest_video.parent.mkdir(parents=True, exist_ok=True)
        total_frames = max(1, int(duration * fps))

        frames_dir = self.cache_dir / f"quote_{abs(hash(quote_text + author + str(duration)))}"
        frames_dir.mkdir(parents=True, exist_ok=True)

        font_quote_mark = self._get_font(int(width * 0.16), bold=True, serif=True)
        font_body = self._get_font(int(width * 0.040), bold=False, serif=True)
        font_author = self._get_font(int(width * 0.036), bold=True)
        font_title = self._get_font(int(width * 0.024), bold=False)

        arr = np.zeros((height, width, 3), dtype=np.uint8)
        arr[:, :, 0] = 18
        arr[:, :, 1] = 21
        arr[:, :, 2] = 28
        base_canvas = Image.fromarray(arr)

        card_margin = int(width * 0.08)
        card_y = int(height * 0.26)
        card_w = width - card_margin * 2
        card_h = int(height * 0.36)

        for frame_idx in range(total_frames):
            frame = base_canvas.copy()
            draw = ImageDraw.Draw(frame)

            # Card Background
            draw.rectangle([card_margin, card_y, card_margin + card_w, card_y + card_h],
                           fill=(26, 31, 44))
            draw.rectangle([card_margin, card_y, card_margin + card_w, card_y + card_h],
                           outline=(217, 119, 6), width=2)

            # 1. Stylized Gold Quote Mark “
            draw.text((card_margin + 36, card_y + 10), "“", fill=(217, 119, 6), font=font_quote_mark)

            # 2. Quote Body
            wrapped = self._wrap_text(quote_text, font_body, card_w - 70, draw)
            start_y = card_y + 120
            for k, qline in enumerate(wrapped[:3]):
                draw.text((card_margin + 40, start_y + k * 46), f"{qline}", fill=(243, 244, 246), font=font_body)

            # 3. Gold Accent Line
            line_y = start_y + len(wrapped[:3]) * 46 + 22
            draw.line([(card_margin + 40, line_y), (card_margin + 180, line_y)], fill=(217, 119, 6), width=3)

            # 4. Author & Historical Title
            draw.text((card_margin + 40, line_y + 16), author.upper(), fill=(255, 255, 255), font=font_author)
            draw.text((card_margin + 40, line_y + 56), title_context.upper(), fill=(209, 213, 219), font=font_title)

            # 5. Corner Archival Stamp
            draw.text((card_margin + card_w - 200, card_y + card_h - 32), "ARCHIVAL RECORD",
                      fill=(156, 163, 175), font=font_title)

            frame_path = frames_dir / f"frame_{frame_idx:04d}.png"
            frame.save(frame_path)

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(frames_dir / "frame_%04d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "fast",
            str(dest_video)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        for f in frames_dir.glob("frame_*.png"):
            try:
                f.unlink()
            except Exception:
                pass
        try:
            frames_dir.rmdir()
        except Exception:
            pass

        return dest_video

    def render_ranked_step_video(
        self,
        step_number: str,
        headline: str,
        description: str,
        dest_video: Path,
        duration: float = 3.0,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        category: str = "PIVOTAL TURNING POINT",
    ) -> Path:
        """
        Canva Ranked Listicle / Step Countdown Card.
        Features:
        - Giant step number badge ('01', '02', '03')
        - High-impact headline and description
        - Animated progress accent line
        """
        dest_video.parent.mkdir(parents=True, exist_ok=True)
        total_frames = max(1, int(duration * fps))

        frames_dir = self.cache_dir / f"step_{abs(hash(step_number + headline + str(duration)))}"
        frames_dir.mkdir(parents=True, exist_ok=True)

        font_num = self._get_font(int(width * 0.14), bold=True)
        font_cat = self._get_font(int(width * 0.026), bold=True)
        font_head = self._get_font(int(width * 0.046), bold=True)
        font_desc = self._get_font(int(width * 0.028), bold=False)

        arr = np.zeros((height, width, 3), dtype=np.uint8)
        arr[:, :, 0] = 6
        arr[:, :, 1] = 26
        arr[:, :, 2] = 20
        base_canvas = Image.fromarray(arr)

        card_margin = int(width * 0.08)
        card_y = int(height * 0.28)
        card_w = width - card_margin * 2
        card_h = int(height * 0.36)

        for frame_idx in range(total_frames):
            frame = base_canvas.copy()
            draw = ImageDraw.Draw(frame)

            raw_t = frame_idx / float(total_frames - 1) if total_frames > 1 else 1.0

            # Card Container
            draw.rectangle([card_margin, card_y, card_margin + card_w, card_y + card_h],
                           fill=(12, 40, 32))
            draw.rectangle([card_margin, card_y, card_margin + card_w, card_y + card_h],
                           outline=(16, 185, 129), width=2)

            # 1. Category Tag
            draw.text((card_margin + 36, card_y + 26), f"●  {category.upper()}", fill=(52, 211, 153), font=font_cat)

            # 2. Giant Step Number Badge
            num_str = f"{int(step_number):02d}" if step_number.isdigit() else step_number
            draw.text((card_margin + 36, card_y + 48), num_str, fill=(16, 185, 129), font=font_num)

            # 3. Main Step Headline
            wrapped_head = self._wrap_text(headline, font_head, card_w - 70, draw)
            head_y = card_y + 175
            for idx, hline in enumerate(wrapped_head[:2]):
                draw.text((card_margin + 36, head_y + idx * 52), hline.upper(), fill=(255, 255, 255), font=font_head)

            # 4. Description
            wrapped_desc = self._wrap_text(description, font_desc, card_w - 70, draw)
            desc_y = head_y + len(wrapped_head[:2]) * 52 + 14
            for j, dline in enumerate(wrapped_desc[:2]):
                draw.text((card_margin + 36, desc_y + j * 36), dline, fill=(209, 250, 229), font=font_desc)

            # 5. Animated Progress Line Filling Bottom
            prog_w = int((card_w - 72) * raw_t)
            draw.rectangle([card_margin + 36, card_y + card_h - 20, card_margin + 36 + prog_w, card_y + card_h - 14],
                           fill=(16, 185, 129))

            frame_path = frames_dir / f"frame_{frame_idx:04d}.png"
            frame.save(frame_path)

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(frames_dir / "frame_%04d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "fast",
            str(dest_video)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        for f in frames_dir.glob("frame_*.png"):
            try:
                f.unlink()
            except Exception:
                pass
        try:
            frames_dir.rmdir()
        except Exception:
            pass

        return dest_video

    def render_breaking_bulletin_video(
        self,
        headline: str,
        ticker_text: str,
        dest_video: Path,
        duration: float = 3.0,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        category: str = "HISTORIC BULLETIN",
    ) -> Path:
        """
        Canva Breaking News Alert & Historical Bulletin.
        Features:
        - Flashing crimson header
        - High-contrast news headline card
        - Layered animated scrolling bottom ticker tape
        """
        dest_video.parent.mkdir(parents=True, exist_ok=True)
        total_frames = max(1, int(duration * fps))

        frames_dir = self.cache_dir / f"bulletin_{abs(hash(headline + str(duration)))}"
        frames_dir.mkdir(parents=True, exist_ok=True)

        font_alert = self._get_font(int(width * 0.036), bold=True)
        font_head = self._get_font(int(width * 0.048), bold=True)
        font_ticker = self._get_font(int(width * 0.026), bold=True)
        font_sub = self._get_font(int(width * 0.026), bold=False)

        arr = np.zeros((height, width, 3), dtype=np.uint8)
        arr[:, :, :] = 10
        base_canvas = Image.fromarray(arr)

        card_margin = int(width * 0.07)
        card_y = int(height * 0.28)
        card_w = width - card_margin * 2
        card_h = int(height * 0.32)

        ticker_y = int(height * 0.76)
        ticker_h = 64

        for frame_idx in range(total_frames):
            frame = base_canvas.copy()
            draw = ImageDraw.Draw(frame)

            raw_t = frame_idx / float(total_frames - 1) if total_frames > 1 else 1.0

            # 1. Flashing Red Alert Header Bar
            alert_bg = (220, 38, 38) if (frame_idx // 8) % 2 == 0 else (185, 28, 28)
            draw.rectangle([card_margin, card_y - 50, card_margin + card_w, card_y], fill=alert_bg)
            draw.text((card_margin + 20, card_y - 40), f"●  {category.upper()} // FLASH DISPATCH", fill=(255, 255, 255), font=font_alert)

            # 2. Main Bulletin Card
            draw.rectangle([card_margin, card_y, card_margin + card_w, card_y + card_h], fill=(24, 24, 27))
            draw.rectangle([card_margin, card_y, card_margin + card_w, card_y + card_h], outline=(220, 38, 38), width=3)

            # 3. Headline Text
            wrapped_head = self._wrap_text(headline, font_head, card_w - 60, draw)
            for i, line in enumerate(wrapped_head[:3]):
                draw.text((card_margin + 30, card_y + 36 + i * 58), line.upper(), fill=(255, 255, 255), font=font_head)

            draw.text((card_margin + 30, card_y + card_h - 40), "CONFIRMED DISPATCH // PRIMARY SOURCE ARCHIVE", fill=(161, 161, 170), font=font_sub)

            # 4. Animated Scrolling Bottom Ticker Tape
            draw.rectangle([0, ticker_y, width, ticker_y + ticker_h], fill=(220, 38, 38))

            scroll_offset = int((width + 800) * raw_t)
            ticker_content = f"{ticker_text.upper()}   +++   ARCHIVE CLASSIFICATION DECLASSIFIED   +++   TELEMETRY REAL-TIME RECORD"
            draw.text((width - scroll_offset, ticker_y + 18), ticker_content, fill=(255, 255, 255), font=font_ticker)

            # Static 'LIVE FEED' badge rendered on top of the scrolling text on left
            draw.rectangle([0, ticker_y, 170, ticker_y + ticker_h], fill=(17, 24, 39))
            draw.rectangle([0, ticker_y, 170, ticker_y + ticker_h], outline=(220, 38, 38), width=1)
            draw.text((22, ticker_y + 18), "LIVE FEED", fill=(255, 255, 255), font=font_ticker)

            frame_path = frames_dir / f"frame_{frame_idx:04d}.png"
            frame.save(frame_path)

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(frames_dir / "frame_%04d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "fast",
            str(dest_video)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        for f in frames_dir.glob("frame_*.png"):
            try:
                f.unlink()
            except Exception:
                pass
        try:
            frames_dir.rmdir()
        except Exception:
            pass

        return dest_video
