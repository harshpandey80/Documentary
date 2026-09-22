import re
from pathlib import Path
from docstudio.config import CAPTION_STYLES, DEFAULT_CAPTION_STYLE, DEFAULT_WIDTH, DEFAULT_HEIGHT

def format_ass_timestamp(seconds: float) -> str:
    """Format seconds into ASS timestamp: H:MM:SS.cc"""
    seconds = max(0.0, float(seconds))
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        secs += 1
        centis -= 100
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"

def generate_ass_subtitles(
    word_timestamps: list[dict],
    output_path: Path,
    style_name: str = DEFAULT_CAPTION_STYLE,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> Path:
    """
    Generate an Advanced SubStation Alpha (.ass) file with:
    - Balanced 2-4 word retention chunks (no awkward single-word lines)
    - Zero gap/flicker between words (dialogue stays visible across micro-pauses)
    - Zero text wobble/jitter (pure high-contrast color pop without character displacement)
    - Safe-zone positioning for both 16:9 widescreen and 9:16 vertical Shorts/TikTok
    """
    style = CAPTION_STYLES.get(style_name, CAPTION_STYLES["documentary"]).copy()
    words_per_line = style.get("words_per_line", 3 if height > width else 4)
    is_uppercase = style.get("uppercase", False)

    # Calibrate safe zone for vertical 9:16 video
    margin_v = style.get("margin_v", 60)
    alignment = style.get("alignment", 2)
    font_size = style.get("font_size", 48)

    if height > width: # 9:16 Portrait
        # Prevent TikTok/Shorts UI overlap
        if alignment == 2:
            margin_v = max(margin_v, 380)
        font_size = int(font_size * 1.15)
    else: # 16:9 Landscape
        if alignment == 2:
            margin_v = max(margin_v, 80)

    # 1. Clean & normalize word boundaries
    cleaned_words = []
    for w in word_timestamps:
        word_text = w.get("word", "").strip()
        # Filter out pause tokens or empty markup symbols
        if not word_text or re.match(r"^\[.*\]$", word_text):
            continue
        cleaned_words.append({
            "word": word_text.upper() if is_uppercase else word_text,
            "raw_word": word_text,
            "start": float(w.get("start", 0.0)),
            "end": float(w.get("end", 0.0)),
            "scene_id": w.get("scene_id", ""),
        })

    if not cleaned_words:
        output_path.write_text("", encoding="utf-8")
        return output_path

    # 2. Balanced chunking engine
    # Target 2-4 words per chunk or ~16-24 chars; avoid 1-word chunks unless a long pause occurs
    chunks = []
    current_chunk = []

    for i, word in enumerate(cleaned_words):
        current_chunk.append(word)

        # Check pause to next word
        has_next = (i < len(cleaned_words) - 1)
        next_pause = (cleaned_words[i+1]["start"] - word["end"]) if has_next else 0.0
        scene_changed = has_next and (cleaned_words[i+1]["scene_id"] != word["scene_id"])

        chunk_char_len = sum(len(w["word"]) for w in current_chunk) + len(current_chunk)
        chunk_word_count = len(current_chunk)

        should_split = False
        if not has_next:
            should_split = True
        elif scene_changed:
            should_split = True
        elif next_pause > 0.55: # Significant natural pause
            should_split = True
        elif chunk_word_count >= words_per_line:
            should_split = True
        elif chunk_char_len >= 22 and chunk_word_count >= 2:
            should_split = True
        elif word["raw_word"].endswith((".", "!", "?")) and chunk_word_count >= 2:
            should_split = True

        if should_split:
            chunks.append(current_chunk)
            current_chunk = []

    if current_chunk:
        chunks.append(current_chunk)

    # 3. Build ASS file header
    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.601",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        (
            f"Style: Default,{style['font_name']},{font_size},"
            f"{style['primary_color']},{style['secondary_color']},{style['outline_color']},{style['back_color']},"
            f"1,0,0,0,100,100,0,0,1,{style['outline_width']},{style['shadow_offset']},"
            f"{alignment},40,40,{margin_v},1"
        ),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    # 4. Generate dialogue events with gapless transitions (no flicker)
    for c_idx, chunk in enumerate(chunks):
        if not chunk:
            continue

        next_chunk = chunks[c_idx + 1] if c_idx < len(chunks) - 1 else None
        next_chunk_start = next_chunk[0]["start"] if next_chunk else None

        for i, active_word in enumerate(chunk):
            w_start = active_word["start"]

            # Cover the silent gap to the next word so the subtitle never flickers off!
            if i < len(chunk) - 1:
                w_end = chunk[i + 1]["start"]
            else:
                # Last word in chunk: hold through natural release or next chunk onset
                if next_chunk_start is not None:
                    w_end = min(active_word["end"] + 0.22, next_chunk_start)
                else:
                    w_end = active_word["end"] + 0.22

            start_str = format_ass_timestamp(w_start)
            end_str = format_ass_timestamp(w_end)

            # Build line text: active word receives neon/gold color pop; NO scaling to prevent wobble
            line_parts = []
            for j, word_item in enumerate(chunk):
                w_text = word_item["word"]
                if j == i:
                    # Active word: secondary color pop + bold + crisp outline
                    line_parts.append(
                        f"{{\\c{style['secondary_color']}\\b1}}{w_text}{{\\rDefault}}"
                    )
                else:
                    # Inactive word: clean base color
                    line_parts.append(f"{{\\c{style['primary_color']}}}{w_text}")

            event_text = " ".join(line_parts)
            ass_lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{event_text}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(ass_lines), encoding="utf-8")
    return output_path
