"""
ViMax Agentic Video Director Engine (inspired by HKUDS/ViMax)
Multi-agent directorial framework ensuring narrative coherence, visual style continuity,
and intentional documentary scene pacing across the entire film timeline.
"""

from __future__ import annotations
from typing import Dict, Any, List
import json
from pathlib import Path

# Documentary Scene Archetypes
ARCHETYPE_AI_RECREATION = "AI_CINEMATIC_RECREATION"       # High-impact AI video clip / 3D reenactment
ARCHETYPE_TALKING_HEAD = "EXPERT_TALKING_HEAD"             # Historian / witness interview cutaway
ARCHETYPE_INFOGRAPHIC = "INFOGRAPHIC_CODE2VIDEO"           # Animated 3D map / tactical radar / telemetry HUD
ARCHETYPE_ARCHIVAL = "ARCHIVAL_WITNESS"                   # Authentic archival newsreel / historical footage
ARCHETYPE_EVIDENCE = "FORENSIC_EVIDENCE"                   # Declassified document / naval log / photo scan
ARCHETYPE_ATMOSPHERIC_STOCK = "ATMOSPHERIC_BROLL"         # High-production natural environment / atmospheric transition

class ViMaxDirector:
    """
    Directs the documentary production across scenes to guarantee:
    1. Visual and historical continuity (Color, Lighting, Texture tokens)
    2. Dynamic, high-retention pacing (alternating between AI footage, archives, talking heads, and maps)
    """

    def __init__(self, topic: str):
        self.topic = topic
        self.continuity_bible = self._build_continuity_bible(topic)

    def _build_continuity_bible(self, topic: str) -> Dict[str, Any]:
        """Defines era-specific visual anchor tokens for whole-documentary consistency."""
        topic_lower = topic.lower()
        if any(w in topic_lower for w in ["war", "ww2", "wwii", "combat", "military", "battle"]):
            era_palette = {
                "era_name": "1939-1945 Total Conflict",
                "color_grading": "muted olive drab, desaturated khaki, tungsten warmth, deep silver blacks",
                "film_stock": "Kodak Tri-X 35mm with subtle silver halide halation",
                "lighting_tone": "moody chiaroscuro with dense volumetric atmospheric smoke",
                "infographic_theme": "military green tactical map with glowing radar orange vectors",
            }
        elif any(w in topic_lower for w in ["space", "nasa", "apollo", "universe", "planet", "galaxy"]):
            era_palette = {
                "era_name": "Cosmic Exploration",
                "color_grading": "deep void black, neon cerulean, solar gold highlights",
                "film_stock": "high-dynamic range Hasselblad 70mm transparency film",
                "lighting_tone": "unfiltered high-contrast solar key light with celestial rim glow",
                "infographic_theme": "orbital trajectory telemetry HUD with cyan velocity vectors",
            }
        elif any(w in topic_lower for w in ["crime", "murder", "fbi", "mystery", "conspiracy"]):
            era_palette = {
                "era_name": "Forensic Investigation",
                "color_grading": "cold slate gray, sodium vapor amber, high contrast shadows",
                "film_stock": "gritty 16mm surveillance print",
                "lighting_tone": "harsh fluorescent spill and interrogation beam",
                "infographic_theme": "redacted declassified casefile with red forensic pins",
            }
        else:
            era_palette = {
                "era_name": "Modern Investigative Documentary",
                "color_grading": "naturalistic 35mm cinema, balanced skin tones, rich shadow depth",
                "film_stock": "Arri Alexa Mini LF 4K cinematic grain",
                "lighting_tone": "motivated practical lighting with soft window key",
                "infographic_theme": "sleek minimalist slate and gold typography",
            }
        return era_palette

    def orchestrate_scene_archetypes(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Assigns each scene in the script an intentional documentary archetype.
        Ensures the documentary never feels repetitive:
        - Opening: High-impact AI Recreation or Archival Hook
        - Context: Infographic tactical map or forensic document
        - Climax: Dramatic AI cinematic reenactments
        - Commentary: Expert / witness talking head cutaways
        """
        total = len(scenes)
        pattern = [
            ARCHETYPE_AI_RECREATION,  # Hook: Dramatic AI Recreation
            ARCHETYPE_ARCHIVAL,       # Reality anchor: Authentic archival film
            ARCHETYPE_INFOGRAPHIC,    # Map / context: Code2Video tactical map
            ARCHETYPE_EVIDENCE,       # Proof: Declassified letter / photo evidence
            ARCHETYPE_TALKING_HEAD,   # Human voice: Expert / witness talking head
            ARCHETYPE_AI_RECREATION,  # Cinematic depth: AI Reenactment
            ARCHETYPE_ARCHIVAL,       # Archival anchor
        ]

        directed_scenes = []
        for idx, sc in enumerate(scenes):
            sc_copy = dict(sc)
            # Use pattern cycling or heuristic from narration
            archetype = pattern[idx % len(pattern)]

            # Check if scene naturally demands a map or quote
            narration = sc_copy.get("narration", "").lower()
            if any(k in narration for k in ["map", "territory", "border", "flank", "advance", "mile", "kilometer"]):
                archetype = ARCHETYPE_INFOGRAPHIC
            elif any(k in narration for k in ["stated", "declared", "wrote in his diary", "testified", "quote"]):
                archetype = ARCHETYPE_TALKING_HEAD
            elif any(k in narration for k in ["explosion", "blast", "clash", "darkness", "storm", "night", "fire"]):
                archetype = ARCHETYPE_AI_RECREATION

            sc_copy["archetype"] = archetype
            sc_copy["visual_continuity"] = self.continuity_bible
            directed_scenes.append(sc_copy)

        return directed_scenes

    def save_directorial_plan(self, output_dir: Path, directed_scenes: List[Dict[str, Any]]):
        """Exports the ViMax directorial breakdown to the workspace."""
        plan_path = output_dir / "vimax_directorial_plan.json"
        summary = {
            "topic": self.topic,
            "continuity_bible": self.continuity_bible,
            "total_scenes": len(directed_scenes),
            "archetype_distribution": {
                ARCHETYPE_AI_RECREATION: sum(1 for s in directed_scenes if s.get("archetype") == ARCHETYPE_AI_RECREATION),
                ARCHETYPE_TALKING_HEAD: sum(1 for s in directed_scenes if s.get("archetype") == ARCHETYPE_TALKING_HEAD),
                ARCHETYPE_INFOGRAPHIC: sum(1 for s in directed_scenes if s.get("archetype") == ARCHETYPE_INFOGRAPHIC),
                ARCHETYPE_ARCHIVAL: sum(1 for s in directed_scenes if s.get("archetype") == ARCHETYPE_ARCHIVAL),
                ARCHETYPE_EVIDENCE: sum(1 for s in directed_scenes if s.get("archetype") == ARCHETYPE_EVIDENCE),
            },
            "scenes": [
                {
                    "scene_id": s.get("scene_id"),
                    "archetype": s.get("archetype"),
                    "headline": s.get("headline"),
                }
                for s in directed_scenes
            ]
        }
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        return plan_path

    def classify_scene_archetype(self, scene: Dict[str, Any], is_cold_hook: bool = False) -> str:
        """
        Classifies a scene into its optimal documentary archetype.
        Ensures diverse distribution across AI Reenactments, Animated Maps, Forensic Evidence, and Stock.
        """
        narration = scene.get("narration", "").lower()
        keywords = " ".join(scene.get("broll_keywords", [])).lower()
        prompt = scene.get("visual_prompt", "").lower()
        sc_id = str(scene.get("scene_id", "")).lower()
        combined = f"{sc_id} {narration} {keywords} {prompt}"

        # 0. Cold Hook (0–8s): Must be gripping, unskippable, and attentive. Never generic stock.
        if is_cold_hook or "hook" in sc_id or sc_id in ["act1_s1", "act1_s1_sub0", "s0", "scene_0"]:
            if any(k in combined for k in ["document", "classified", "telegram", "memo", "order"]):
                return ARCHETYPE_EVIDENCE
            elif any(k in combined for k in ["radar", "map", "telemetry", "coordinates", "vector"]):
                return ARCHETYPE_INFOGRAPHIC
            else:
                return ARCHETYPE_AI_RECREATION

        # 1. 3D Animated Infographics & Tactical Overlays (Code2Video)
        if any(k in combined for k in [
            "map", "radar", "coordinate", "telemetry", "route", "flight path", 
            "vector", "altitude", "heading", "compass", "latitude", "longitude", 
            "stats", "counter", "grid", "nautical mile", "boundary"
        ]):
            return ARCHETYPE_INFOGRAPHIC

        # 2. Forensic Declassified Evidence & Archival Scans
        elif any(k in combined for k in [
            "document", "letter", "report", "telegram", "secret", "classified", 
            "file", "memo", "dossier", "transcript", "logbook", "patent", "official record"
        ]):
            return ARCHETYPE_EVIDENCE

        # 3. Authentic Archival Newsreels & Historical Photos
        elif any(k in combined for k in [
            "archive", "newsreel", "black and white", "vintage photo", "1940", "1945", "1950", "newspaper headline"
        ]):
            return ARCHETYPE_ARCHIVAL

        # 4. Expert Witness / Interview Cutaways
        elif any(k in combined for k in [
            "stated", "declared", "diary", "testified", "quote", "according to", "witness", "historian", "investigator"
        ]):
            return ARCHETYPE_TALKING_HEAD

        # 5. Natural Environmental / Atmospheric Transitions
        elif any(k in combined for k in [
            "open ocean", "clouds passing", "sunset", "vast sky", "tranquil", "aerial coastline", "horizon"
        ]):
            return ARCHETYPE_ATMOSPHERIC_STOCK

        # 6. Default to High-Impact 3D AI Cinematic Reenactment for Action / Anomalies
        else:
            return ARCHETYPE_AI_RECREATION

    def enrich_visual_prompt(self, base_prompt: str, archetype: str) -> str:
        """
        Enriches the base visual prompt with era-specific cinematography directives
        from the continuity bible, ensuring cross-scene visual consistency.
        """
        bible = self.continuity_bible
        color = bible.get("color_grading", "cinematic color grade")
        film = bible.get("film_stock", "35mm film")
        lighting = bible.get("lighting_tone", "dramatic documentary lighting")

        if archetype == ARCHETYPE_AI_RECREATION:
            return (
                f"{base_prompt}, {color}, {lighting}, {film}, "
                f"cinematic documentary reenactment, dramatic ultra-HD, "
                f"8K photorealistic, 3D camera parallax, volumetric fog"
            )
        elif archetype == ARCHETYPE_INFOGRAPHIC:
            infographic_theme = bible.get("infographic_theme", "tactical animated map")
            return (
                f"Animated 3D {infographic_theme}: {base_prompt}, "
                f"smooth motion graphics, tactical radar vectors, glowing telemetry HUD, "
                f"high-contrast overlaid coordinates on terrain"
            )
        elif archetype == ARCHETYPE_TALKING_HEAD:
            return (
                f"Cinematic expert interview cutaway: {base_prompt}, "
                f"shallow depth of field bokeh, {lighting}, "
                f"documentary talking-head medium close-up, warm practical light"
            )
        elif archetype == ARCHETYPE_EVIDENCE:
            return (
                f"Forensic evidence reveal: {base_prompt}, "
                f"declassified document texture, 30fps macro 3D camera drift, "
                f"high-contrast forensic lighting, {film}"
            )
        elif archetype == ARCHETYPE_ARCHIVAL:
            return (
                f"Authentic archival newsreel: {base_prompt}, "
                f"black and white 16mm grain, vignette, subtle film flicker, "
                f"period-accurate {bible.get('era_name', '')} documentary footage"
            )
        elif archetype == ARCHETYPE_ATMOSPHERIC_STOCK:
            return (
                f"Cinematic atmospheric b-roll: {base_prompt}, "
                f"wide establishing shot, natural lighting, smooth gimbal motion"
            )
        return base_prompt

    def generate_visual_storyboard_plan(self, shots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Formulates a comprehensive visual combination plan for user review before rendering.
        Categorizes shots into narrative phases and assigns optimal visual engines.
        """
        archetype_labels = {
            ARCHETYPE_AI_RECREATION: "⚡ AI Cinematic Reenactment (3D)",
            ARCHETYPE_INFOGRAPHIC: "🗺️ 3D Animated Tactical Map / HUD (Code2Video)",
            ARCHETYPE_EVIDENCE: "📜 Forensic Declassified Evidence (Macro Motion)",
            ARCHETYPE_ARCHIVAL: "🎞️ Authentic Archival Newsreel / Record",
            ARCHETYPE_TALKING_HEAD: "🎙️ Historical Witness / Expert Cutaway",
            ARCHETYPE_ATMOSPHERIC_STOCK: "🌊 Atmospheric Cinema Stock",
        }

        total_shots = len(shots)
        storyboard = []
        cur_time = 0.0

        for idx, shot in enumerate(shots):
            dur = float(shot.get("duration", 2.2))
            start_t = cur_time
            end_t = cur_time + dur
            cur_time = end_t

            is_hook = (idx == 0 or start_t < 6.0)
            arch = shot.get("archetype")
            if not arch:
                arch = self.classify_scene_archetype(shot, is_cold_hook=is_hook)

            # Narrative phase
            if is_hook:
                phase = "🔥 COLD HOOK (Thumb-Stop)"
            elif idx < total_shots * 0.35:
                phase = "🧭 CONTEXT & ANOMALY"
            elif idx < total_shots * 0.70:
                phase = "⚠️ CRISIS ESCALATION"
            elif idx < total_shots * 0.90:
                phase = "🔍 FORENSIC REVELATION"
            else:
                phase = "🎯 CTA & UNSEALED LOOP"

            storyboard.append({
                "index": idx + 1,
                "scene_id": shot.get("scene_id", f"scene_{idx+1}"),
                "time_range": f"{start_t:.1f}s - {end_t:.1f}s",
                "duration": dur,
                "phase": phase,
                "archetype": arch,
                "visual_type": archetype_labels.get(arch, arch),
                "keywords": shot.get("broll_keywords", []),
                "visual_prompt": shot.get("visual_prompt", ""),
            })

        # Calculate diversity statistics
        type_counts = {}
        for s in storyboard:
            type_counts[s["archetype"]] = type_counts.get(s["archetype"], 0) + 1

        stats = {k: f"{v} cuts ({v/total_shots*100:.0f}%)" for k, v in type_counts.items()}

        # Build clean markdown table
        md_lines = [
            f"# Visual Combination Storyboard Plan: {self.topic}",
            "",
            f"**Total Visual Cuts**: {total_shots} | **Estimated Runtime**: {cur_time:.1f}s",
            "",
            "### Diversity Balance:",
        ]
        for arch, stat_str in stats.items():
            label = archetype_labels.get(arch, arch)
            md_lines.append(f"- **{label}**: {stat_str}")

        md_lines.extend([
            "",
            "### Scene-by-Scene Visual Breakdown:",
            "",
            "| Cut | Time | Narrative Phase | Visual Engine / Type | Core Visual Focus |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ])

        for s in storyboard:
            prompt_preview = s["visual_prompt"][:45] + "..." if len(s["visual_prompt"]) > 45 else s["visual_prompt"]
            md_lines.append(
                f"| #{s['index']} | `{s['time_range']}` | {s['phase']} | **{s['visual_type']}** | {prompt_preview or ', '.join(s['keywords'][:3])} |"
            )

        markdown_output = "\n".join(md_lines)

        return {
            "topic": self.topic,
            "total_shots": total_shots,
            "total_duration": cur_time,
            "diversity_stats": stats,
            "storyboard": storyboard,
            "markdown_plan": markdown_output,
        }

