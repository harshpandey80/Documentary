"""
DocStudio Remote Creative Director — Prompt Builder.
Implements Two-Pass directorial reasoning:
- Pass 1: Storyboard & Visual Strategy (Scene/shot timing, purpose, visual type, and reasoning).
- Pass 2: Prompt Engineering (Detailed photographic/cinematic prompts adhering to Continuity Bible).
"""

from __future__ import annotations
import json
from typing import Dict, Any, List
from docstudio.remote_creative_director.context_builder import DirectorialContext


class PromptBuilder:
    """
    Constructs rich prompts that force the remote AI to act as an executive documentary director.
    """

    @staticmethod
    def build_pass1_system_prompt() -> str:
        return """You are the Executive Creative Director and Master Editor for a world-class investigative documentary film studio.
Your mandate is to direct the visual narrative: decide what the viewer sees, why they see it, when it appears, and what visual medium communicates the information with highest forensic clarity.

DO NOT behave like an assistant matching keywords to pictures.
You must reason globally over the entire documentary arc:
1. WHAT CAME BEFORE: What visuals have already been shown? Avoid repeating the same visual archetype.
2. WHAT IS HAPPENING NOW: What is the core revelation or evidence in this specific moment?
3. WHAT DOES THE VIEWER NEED TO UNDERSTAND: Choose the medium that makes the concept instantly clear:
   - Coordinates, travel, distances -> MAP (MapAnimation)
   - Numbers, statistics, growth, financial flows -> DATA_CHART (NumberGraphics)
   - Quotes, official orders, telegrams, declassified logs -> AUTHENTIC_EVIDENCE / PROCEDURAL_DOCUMENT
   - Real historical people or events with records -> REAL_ARCHIVAL
   - Unseen crisis moments where physical motion is crucial -> AI_IMAGE_TO_VIDEO (reserved for peak tension)
   - Environmental transitions or atmospheric scene resets -> STOCK_BROLL / ATMOSPHERIC_VISUAL
4. NO FIXED-INTERVAL CHOPPING: Visual cuts must be motivated by story events (new entity, revelation, contradiction, data point, or shift in scale), NOT arbitrary 2-second clocks.
5. SELF-CRITIQUE: Reject redundant visuals. If a map explains geography better than drone footage, mandate a map. If a signed document proves a fact, mandate evidence.

You MUST respond strictly with a valid JSON object conforming to the Shot Manifest Schema. No markdown commentary outside the JSON."""

    @staticmethod
    def build_pass1_user_prompt(context: DirectorialContext) -> str:
        ctx_dict = context.to_dict()
        ctx_json = json.dumps(ctx_dict, indent=2, ensure_ascii=False)

        beats_section = ""
        if context.story_beats:
            lines = ["STORY BEATS & VIEWER SEEING INTENTS (DIRECTORIAL INTENT):"]
            for b in context.story_beats:
                b_id = b.get("beat_id", "")
                b_name = b.get("beat_name", "")
                v_seeing = b.get("viewer_seeing_intent", "")
                v_learn = b.get("viewer_learning", "")
                lines.append(f"- Beat [{b_id}] {b_name}:\n    viewer_seeing_intent: \"{v_seeing}\"\n    viewer_learning: \"{v_learn}\"")
            beats_section = "\n" + "\n".join(lines) + "\n"

        req_scene_count = len(context.scenes)
        return f"""Review the complete documentary production package below and direct the Shot Manifest for:
TOPIC: "{context.topic}"
TARGET DURATION: {context.target_duration}s
ASPECT RATIO: {context.aspect_ratio}
STYLE: {context.documentary_style}
VISUAL BUDGET: {json.dumps(context.visual_budget.to_dict())}
{beats_section}
FULL NARRATIVE CONTEXT PACKAGE:
{ctx_json}

============================================================
DIRECTORIAL REQUIREMENTS:
1. STORY INTENT ALIGNMENT: You MUST honor each story beat's 'viewer_seeing_intent' and 'viewer_learning' when directing visuals for corresponding narration scenes.
2. SCENE PARITY: You MUST generate exactly {req_scene_count} scenes, matching 1:1 with the {req_scene_count} narration scenes provided.
3. Every shot MUST contain:
   - "shot_id": unique identifier (e.g. "S01_01")
   - "start": start time in seconds
   - "end": end time in seconds
   - "duration": duration in seconds (end - start)
   - "purpose": One of [ESTABLISH, INTRODUCE_PERSON, INTRODUCE_LOCATION, EXPLAIN_GEOGRAPHY, EXPLAIN_SEQUENCE, SHOW_SCALE, SHOW_EVIDENCE, SHOW_CONTRADICTION, SHOW_STATISTICS, SHOW_RELATIONSHIP, SHOW_CAUSE_EFFECT, RECONSTRUCT_EVENT, CREATE_EMOTIONAL_WEIGHT, CREATE_TENSION, RESET_VISUAL_PACING, SHOW_CONTEXT, SHOW_TRANSITION, EMPHASIZE_REVEAL, CONCLUDE]
   - "visual_type": One of [AUTHENTIC_EVIDENCE, REAL_ARCHIVAL, DATA_CHART, MAP, TIMELINE_DIAGRAM, SCREEN_RECREATION, CINEMATIC_RECONSTRUCTION, AI_IMAGE_TO_VIDEO, AI_IMAGE, STOCK_BROLL, ATMOSPHERIC_VISUAL]
   - "visual_reason": 1-2 sentences explaining WHY this visual is essential here and what concept it communicates to the viewer based on viewer_seeing_intent.
   - "source_strategy": One of [GENERATE_AI_VIDEO, GENERATE_AI_IMAGE, PROCEDURAL_MAP, PROCEDURAL_CHART, PROCEDURAL_DOCUMENT, RETRIEVE_ARCHIVE_STOCK]
   - "evidence_claims": List of claim_ids supported by this shot.
4. CONTINUITY: Ensure lighting, color temperature, and period details remain consistent across recurring characters and locations.
5. BUDGET ENFORCEMENT: Do not exceed max_ai_videos ({context.visual_budget.max_ai_videos}). Spend them only on pivotal moments.
6. SELF-CRITIQUE: Include "director_notes" and "visual_rationale" at the top level summarizing your editorial strategy and confirming zero unmotivated visuals.

Produce the complete JSON Shot Manifest now."""

    @staticmethod
    def build_pass2_system_prompt() -> str:
        return """You are the Senior Visual Prompter and Continuity Specialist.
Your mandate is to write photorealistic, cinematic prompts for approved AI shots in a validated documentary manifest.
Enforce strict physical realism, 35mm film grain, documentary color grading, authentic period details, and absolute visual continuity across character attire and environmental lighting.
Do not use hyperbolic buzzwords ('photorealistic', 'hyper-detailed', '8k'). Use precise optical, lens, lighting, and textural descriptions.
Respond strictly in JSON."""

    @staticmethod
    def build_pass2_user_prompt(manifest_json: Dict[str, Any], continuity_bible: Dict[str, Any]) -> str:
        ai_shots = []
        for sc in manifest_json.get("scenes", []):
            for sh in sc.get("shots", []):
                if sh.get("source_strategy") in ["GENERATE_AI_VIDEO", "GENERATE_AI_IMAGE"]:
                    ai_shots.append({
                        "shot_id": sh.get("shot_id"),
                        "purpose": sh.get("purpose"),
                        "visual_type": sh.get("visual_type"),
                        "visual_reason": sh.get("visual_reason"),
                        "existing_prompt": sh.get("prompt", ""),
                    })

        payload = {
            "continuity_bible": continuity_bible,
            "shots_to_prompt": ai_shots,
        }

        return f"""Refine and expand the cinematic generation prompts for the following AI shots:
{json.dumps(payload, indent=2)}

For each shot, return:
{{
  "shot_id": "...",
  "prompt": "Full cinematic scene description with lighting, lens, subject action, environment, and period accuracy adhering to continuity bible",
  "camera": "Camera angle and framing (e.g. low-angle slow push, medium handheld tracking)",
  "motion": "Subject and environmental motion dynamics",
  "composition": "Framing and depth structure"
}}

Return a JSON object: {{"prompt_directives": [ ... ]}}"""
