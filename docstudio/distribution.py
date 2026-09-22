import json
from pathlib import Path

class DistributionPackager:
    def generate_distribution_assets(
        self,
        topic: str,
        script_data: dict,
        total_duration_seconds: float,
        output_path: Path,
    ) -> dict:
        """
        Generate research-backed high-CTR distribution assets based on RESEARCH_NOTES.md:
        - 3 Alternative Titles (Negative Constraint, Declassified Secret, Fatal Anomaly)
        - Thumbnail Creative Brief (Visual Hierarchy, Contrast Pairing, 2-4 Word Text Overlay)
        - YouTube SEO Description (Hook Above Fold, Timestamps, Search Keywords, Hashtags)
        - Bilibili Package (Bracketed Hook Title, Danmaku/Coin CTA, Timestamp Chapters, Category Tags)
        """
        clean_topic = topic.replace("The ", "").strip()

        # ----------------------------------------------------
        # 1. 3 RESEARCH-BACKED CURIOSITY-GAP TITLES
        # ----------------------------------------------------
        # Pattern A: Negative Constraint / Withheld Information (High CTR on Browse)
        title_a = f"Why No One Was Supposed to Find {clean_topic}"
        # Pattern B: The Declassified / Redacted Secret
        title_b = f"The Secret Incident Erased From Official History: {topic}"
        # Pattern C: The Fatal Paradox / Curiosity Gap
        title_c = f"What Really Happened During {topic}? (The Unsealed Truth)"

        titles = [title_a, title_b, title_c]

        # ----------------------------------------------------
        # 2. THUMBNAIL CREATIVE BRIEF
        # ----------------------------------------------------
        thumbnail_brief = {
            "dimensions": "1920x1080 (16:9) | Safe Zone: Center 80% (Mobile Optimized)",
            "visual_hierarchy": {
                "primary_subject": (
                    "High-contrast, desaturated focal subject occupying 45%–55% of canvas "
                    "(e.g., vintage cockpit instrument dials, redacted archival dossier with razor cuts, or shadowy silhouette)."
                ),
                "lighting_and_tone": (
                    "Chiaroscuro lighting: deep atmospheric blacks (#0a0d12) contrasted against a single searing accent "
                    "(hazard amber #ffaa00 or warning crimson #e63946)."
                ),
                "depth_and_texture": "Subtle 35mm film grain overlay and heavy edge vignette to focus gaze inward."
            },
            "text_overlay": {
                "font_style": "Ultra-bold sans-serif (e.g., Montserrat Black or Impact)",
                "color_palette": "Pure White (#ffffff) or Warning Yellow (#ffd700) with dark drop shadow / black stroke",
                "recommended_phrases": ["THEY KNEW.", "ZERO TRACE.", "UNSEALED.", "WHAT HAPPENED?"],
                "placement": "Top-left or Bottom-left quadrant; never overlapping YouTube timestamp badge in bottom-right."
            },
            "emotional_hook": "Piques intense curiosity and suspicion without revealing the documentary conclusion."
        }

        # ----------------------------------------------------
        # 3. YOUTUBE SEO PACKAGE & CHAPTER TIMESTAMPS
        # ----------------------------------------------------
        acts = script_data.get("acts", [])
        chapters = []
        cur_sec = 0.0
        act_dur = total_duration_seconds / max(1, len(acts))
        for act in acts:
            m = int(cur_sec // 60)
            s = int(cur_sec % 60)
            chapters.append(f"{m:02d}:{s:02d} {act.get('act_name', 'Chapter')}")
            cur_sec += act_dur

        yt_description = (
            f"For decades, the full truth behind {topic} remained buried beneath redacted military archives and conflicting official statements.\n\n"
            f"In this investigative documentary, we trace declassified logs, forensic evidence, and eyewitness testimonies "
            f"to uncover the catastrophic sequence of events that unfolded.\n\n"
            f"TIMESTAMPS:\n" + "\n".join(chapters) + "\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔎 ABOUT THIS INVESTIGATION:\n"
            f"Produced with declassified historical archives and verified public domain records. "
            f"All forensic analysis is based on historical documentation.\n\n"
            f"🔔 Subscribe for in-depth investigative historical and mystery documentaries.\n\n"
            f"#Documentary #HistoryMystery #{clean_topic.replace(' ', '')} #Investigation #Declassified"
        )

        yt_tags = [
            topic,
            f"{topic} documentary",
            f"{clean_topic} explained",
            "historical mystery",
            "investigative documentary",
            "declassified records",
            "unsolved disaster",
            "true story documentary",
            "forensic analysis",
            "historical deep dive",
        ]

        # ----------------------------------------------------
        # 4. BILIBILI PACKAGE (CHINESE LOCALIZED METADATA)
        # ----------------------------------------------------
        bilibili_title = f"【硬核解密】绝密档案解禁：{topic}背后究竟隐藏了什么？"
        bilibili_description = (
            f"【深度纪实 · 悬疑考据】\n"
            f"几十年来，关于{topic}的真相一直被重重封存与迷雾笼罩。\n"
            f"本期深度调查影片通过解禁档案、原始无线电通讯记录与最新证据链，"
            f"逐层还原这场历史迷局的真正终点。\n\n"
            f"【视频时间轴】\n" + "\n".join(chapters) + "\n\n"
            f"💬 弹幕互动：你认为这起事件的背后究竟是意外还是人为掩盖？在弹幕分享你的推理！\n"
            f"⭐ 硬核考据制作不易，欢迎大家【点赞、投币、收藏】三连支持！"
        )

        bilibili_tags = [
            "纪录片",
            "历史解密",
            "未解之谜",
            "硬核科普",
            "历史秘闻",
            "悬疑探秘",
            "调查记录",
            topic,
            clean_topic,
        ]

        dist_package = {
            "topic": topic,
            "titles": titles,
            "thumbnail_brief": thumbnail_brief,
            "youtube": {
                "title": titles[0],
                "description": yt_description,
                "tags": yt_tags,
                "chapters": chapters,
            },
            "bilibili": {
                "title": bilibili_title,
                "description": bilibili_description,
                "tags": bilibili_tags,
                "chapters": chapters,
            }
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dist_package, f, indent=2, ensure_ascii=False)

        # Output Human-Readable Markdown Version
        md_path = output_path.with_suffix(".md")
        md_content = f"""# Distribution Package: {topic}

## 🎯 3 High-CTR Curiosity-Gap Titles
1. **{titles[0]}** *(Pattern: Negative Constraint / Mystery)*
2. **{titles[1]}** *(Pattern: Declassified Secret)*
3. **{titles[2]}** *(Pattern: The Fatal Anomaly / Question)*

---

## 🎨 Thumbnail Creative Brief (16:9 / Mobile-Optimized)
- **Primary Subject**: {thumbnail_brief['visual_hierarchy']['primary_subject']}
- **Lighting & Atmosphere**: {thumbnail_brief['visual_hierarchy']['lighting_and_tone']}
- **Depth & Texture**: {thumbnail_brief['visual_hierarchy']['depth_and_texture']}
- **Text Overlay Concept**: `"{thumbnail_brief['text_overlay']['recommended_phrases'][0]}"` or `"{thumbnail_brief['text_overlay']['recommended_phrases'][1]}"`
- **Typography**: {thumbnail_brief['text_overlay']['font_style']} in {thumbnail_brief['text_overlay']['color_palette']}
- **Placement**: {thumbnail_brief['text_overlay']['placement']}

---

## 📺 YouTube SEO Package
**Primary Video Title**: `{titles[0]}`

**Description**:
```text
{yt_description}
```

**Tags**:
`{", ".join(yt_tags)}`

---

## 🇨🇳 Bilibili Package (Bilingual / Danmaku Optimized)
**Title**: `{bilibili_title}`

**Description**:
```text
{bilibili_description}
```

**Tags**:
`{", ".join(bilibili_tags)}`
"""
        md_path.write_text(md_content, encoding="utf-8")
        return dist_package
