import json
import re
from pathlib import Path
from docstudio.config import (
    GEMINI_API_KEY,
    OPENROUTER_API_KEY,
    DOCSTUDIO_LLM_PROVIDER,
    DOCSTUDIO_MODEL,
)

SYSTEM_INSTRUCTION = """
You are an elite, award-winning investigative documentary director and scriptwriter (in the style of LEMMiNO, MagnatesMedia, Fern, and Vox).
You strictly enforce the retention and storytelling rules defined in STORY_RULES.md and DOCUMENTARY_BENCHMARKS.md:
1. Cold-Open Hook (0-15s): NEVER open chronologically. Open on the most shocking, impossible, or catastrophic moment.
2. Long-Form Depth: Write comprehensive, substantive multi-sentence paragraphs for every scene. Never write short one-liner placeholders.
3. Open Loops: Plant the central unanswered enigma in Act 1, delay resolution until Act 6.
4. Beat-Aware Intensity: Assign an intensity from 1 (somber reflection / 6.5s hold) to 10 (rapid cold hook / climactic shock / 1.5s cut) per scene.
5. Performance Narration via SSML: Format narration with SSML prosody:
   - Dread / Ominous: <prosody rate="-10%" pitch="-3Hz">
   - Twist / Reveal: <prosody rate="+5%" pitch="+2Hz"><emphasis level="strong">
   - Silence vacuum before reveals: <break time="400ms"/>
6. Emotional Tagging: Assign an emotional_tag (tension, reveal, somber, triumphant, ambient_drone) for the sound design engine.
7. Return purely valid JSON matching the specified schema.
"""

SCRIPT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "central_open_loop": {"type": "string"},
        "acts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "act_number": {"type": "integer"},
                    "act_name": {"type": "string"},
                    "scenes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "scene_id": {"type": "string"},
                                "intensity": {"type": "integer", "minimum": 1, "maximum": 10},
                                "emotional_tag": {
                                    "type": "string",
                                    "enum": ["tension", "reveal", "somber", "triumphant", "ambient_drone"]
                                },
                                "narration": {"type": "string"},
                                "ssml_narration": {"type": "string"},
                                "visual_prompt": {"type": "string"},
                                "broll_keywords": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "motion": {
                                    "type": "string",
                                    "enum": ["zoom_in", "zoom_out", "pan_left", "pan_right", "zoom_punch", "subtle_drift"]
                                },
                                "sfx": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "sub_prompts": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "sub_keywords": {
                                    "type": "array",
                                    "items": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                }
                            },
                            "required": ["scene_id", "intensity", "emotional_tag", "narration", "visual_prompt", "broll_keywords", "motion", "sfx"]
                        }
                    }
                },
                "required": ["act_number", "act_name", "scenes"]
            }
        }
    },
    "required": ["topic", "central_open_loop", "acts"]
}

class ScriptWriter:
    def __init__(
        self,
        api_key: str | None = None,
        openrouter_api_key: str = OPENROUTER_API_KEY,
        gemini_api_key: str = GEMINI_API_KEY,
        provider: str = DOCSTUDIO_LLM_PROVIDER,
        model: str = DOCSTUDIO_MODEL,
    ):
        # Allow passing api_key as first positional arg for backwards compatibility
        if api_key:
            if api_key.startswith("sk-or-") or api_key.startswith("sk-"):
                self.openrouter_api_key = api_key
                self.gemini_api_key = gemini_api_key
                self.provider = "openrouter"
            else:
                self.gemini_api_key = api_key
                self.openrouter_api_key = openrouter_api_key
                self.provider = provider
        else:
            self.gemini_api_key = gemini_api_key
            self.openrouter_api_key = openrouter_api_key
            self.provider = provider

        self.api_key = self.gemini_api_key or self.openrouter_api_key
        self.model = model

    def generate_script(self, topic: str, output_file: Path, runtime_target: str = "5m") -> dict:
        """
        Generate a comprehensive documentary script with scene cues,
        beat intensity (1-10), emotional audio tags, SSML performance narration,
        b-roll keywords, and SFX triggers scaled to the target runtime.
        """
        script_data = None

        # 1. Primary provider attempt
        if self.provider == "openrouter" and self.openrouter_api_key:
            try:
                print(f"[ScriptWriter] Generating documentary script via OpenRouter ({self.model})...")
                script_data = self._generate_with_openrouter(topic, runtime_target=runtime_target)
            except Exception as e:
                print(f"[ScriptWriter] OpenRouter generation warning: {e}. Trying secondary provider...")

        elif self.provider == "gemini" and self.gemini_api_key:
            try:
                print("[ScriptWriter] Generating documentary script via Gemini...")
                script_data = self._generate_with_gemini(topic, runtime_target=runtime_target)
            except Exception as e:
                print(f"[ScriptWriter] Gemini generation warning: {e}. Trying secondary provider...")

        # 2. Fallback between providers before falling back to procedural engine
        if not script_data:
            if self.openrouter_api_key and self.provider != "openrouter":
                try:
                    print(f"[ScriptWriter] Fallback: Generating documentary script via OpenRouter ({self.model})...")
                    script_data = self._generate_with_openrouter(topic, runtime_target=runtime_target)
                except Exception as e:
                    print(f"[ScriptWriter] OpenRouter fallback warning: {e}.")

            elif self.gemini_api_key and self.provider != "gemini":
                try:
                    print("[ScriptWriter] Fallback: Generating documentary script via Gemini...")
                    script_data = self._generate_with_gemini(topic, runtime_target=runtime_target)
                except Exception as e:
                    print(f"[ScriptWriter] Gemini fallback warning: {e}.")

        # 3. Final structured procedural fallback
        if not script_data:
            print("[ScriptWriter] Generating via structured procedural documentary engine...")
            script_data = self._generate_structured_fallback(topic, runtime_target=runtime_target)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(script_data, f, indent=2, ensure_ascii=False)

        return script_data

    def _generate_with_openrouter(self, topic: str, runtime_target: str = "5m") -> dict:
        import requests

        is_short = runtime_target in ["60s", "90s", "1m", "1.5m", "short"]
        if is_short:
            if runtime_target in ["90s", "1.5m"]:
                duration_desc = "90-Second Complete YouTube Short / Reel (1:30 min) (220-250 spoken words across 6-8 complete, substantive scenes under 2.4s cuts)"
            else:
                duration_desc = "60-Second Complete YouTube Short / Reel (1:00 min) (160-190 spoken words across 5-7 complete, substantive scenes under 2.4s cuts)"
        else:
            word_target = 750 if runtime_target == "5m" else (1400 if runtime_target == "10m" else 450)
            scene_target = 22 if runtime_target == "5m" else (40 if runtime_target == "10m" else 15)
            duration_desc = f"{runtime_target} Runtime ({word_target} spoken words across approximately {scene_target} substantive scenes)"

        prompt = f"""You are an elite documentary director and forensic investigator writing a high-retention cinematic documentary script about: "{topic}".
Target Format: {duration_desc}.

CRITICAL SHORT-FORM STORYTELLING DIRECTIVES:
1. Complete, Self-Contained Story:
   - A YouTube Short must NEVER be half-full or cut off mid-sentence on a cheap cliffhanger.
   - It MUST deliver a complete narrative arc:
     a) Hook (0-10s): The impossible paradox, anomaly, or classified record.
     b) Investigation & Context (10-35s): Exact expedition details, dates, depth/altitude, and equipment.
     c) Evidence & Revelation (35-65s): What the data revealed, acoustic/seismic measurements, why standard physics failed.
     d) Conclusion & Resolution (65-80s): The outcome, what was declassified, and a complete final sentence before the CTA.
2. Absolute Factual Grounding (ZERO NONSENSE):
   - NO generic hallucinated police cliches (e.g. NEVER mention "first responders", "scorched earth", or "authorities scrambling" when investigating deep-sea trenches, deep space, or historical aviation).
   - Use precise real-world facts: actual geographical coordinates, vehicle/hydrophone designations, atmospheric pressures (e.g. 1,000 atmospheres / 8 tons per square inch), acoustic frequencies in Hertz, and naval records.
3. Master Cinematography (LEMMiNO / David Fincher Aesthetic):
   - Rich visual direction in "visual_prompt": 35mm anamorphic visuals, authentic deep sea submersible viewports, glowing sonar displays, declassified Manila naval archives, radar grids.
   - Rapid Rhythmic Cuts: For each scene, provide 2-4 dynamic "sub_prompts" and "sub_keywords" (arrays of 2-3 precise stock search terms) so cuts occur every 2.0-2.4s without holding static shots.
   - Dynamic Camera Motion: Specify precise motion per scene (`zoom_punch`, `pan_left`, `pan_right`, `zoom_in`, `subtle_drift`).
4. Immersive Sound Design:
   - Prescribe cinematic audio cues in "sfx" (e.g. ["deep_braam", "radio_static", "whoosh", "riser", "ocean_swell"]).
5. Clean Retention Ending & Call to Action (CTA):
   - Ensure the narrative sentence fully concludes before the CTA.
   - Conclude with: "Like and subscribe to uncover the unsealed files."

Requirements:
- Format narration with natural SSML tags (<prosody rate="+5%" pitch="-1Hz">, <break time="300ms"/>, <emphasis level="strong">).
- Assign intensity (1 to 10) and emotional_tag (tension, reveal, somber, triumphant, ambient_drone) to every scene.
- Return ONLY a single valid JSON object adhering to this schema:
{json.dumps(SCRIPT_JSON_SCHEMA, indent=2)}
"""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION + "\nYou must strictly output valid JSON adhering to the provided schema.",
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "provider": {"sort": "throughput"},
            "reasoning": {"effort": "none"},
            "temperature": 0.7,
            "max_tokens": 4000,
        }

        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/docstudio",
            "X-Title": "InVideo AI Documentary Studio",
        }

        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=90,
        )
        resp.raise_for_status()
        res_json = resp.json()
        raw_text = res_json["choices"][0]["message"]["content"]
        if not raw_text:
            raise ValueError("Empty response received from OpenRouter.")

        raw_text = raw_text.strip()
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text)

        return json.loads(raw_text)

    def _generate_with_gemini(self, topic: str, runtime_target: str = "5m") -> dict:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.gemini_api_key)

        is_short = runtime_target in ["45s", "60s", "90s", "1m", "1.5m", "short"] or "short" in str(runtime_target).lower()
        if is_short:
            if runtime_target in ["90s", "1.5m"]:
                duration_desc = "90-Second Complete YouTube Short / Reel (1:30 min) (190-220 spoken words across 6-7 complete, substantive scenes under 2.4s cuts)"
                timing_guide = """
     a) Hook (0-10s): The impossible paradox, anomaly, or classified record.
     b) Investigation & Context (10-35s): Exact expedition details, dates, depth/altitude, and equipment.
     c) Evidence & Revelation (35-65s): What the data revealed, acoustic/seismic measurements, why standard physics failed.
     d) Conclusion & Resolution (65-78s): The outcome, what was declassified, and a complete final sentence before the CTA."""
            else:
                duration_desc = "60-Second Complete YouTube Short / Reel (<60s HARD LIMIT) (STRICTLY 125-145 spoken words across 5 complete scenes under 2.4s cuts)"
                timing_guide = """
     a) Cold Hook (0-8s): The impossible paradox, anomaly, or classified hydrophone recording.
     b) Context & Coordinates (8-20s): Challenger Deep, 10,994 meters (36,070 ft), 1,086 atmospheres of pressure.
     c) Anomaly & Telemetry (20-35s): What the hydrophones detected—the 14.8 kHz metallic frequency spike.
     d) Forensic Revelation (35-46s): The unsealed naval report, what official investigators ruled out.
     e) Resolution & CTA (46-50s): Final compelling resolution, concluding with: 'Like and subscribe to uncover the unsealed files.'"""

            prompt = f"""You are an elite documentary director and forensic investigator writing a high-retention cinematic documentary script about: "{topic}".
Target Format: {duration_desc}.

CRITICAL SHORT-FORM STORYTELLING DIRECTIVES:
1. Complete, Self-Contained Story (STRICTLY UNDER 60 SECONDS TOTAL):
   - A YouTube Short must NEVER be cut off mid-sentence or feel like half-information.
   - It MUST deliver a complete, punchy narrative arc:
{timing_guide}
2. Absolute Factual Grounding (ZERO HALLUCINATIONS / ZERO NONSENSE):
   - NO generic police cliches (NEVER mention 'first responders' or 'authorities scrambling').
   - Use precise real-world facts: actual coordinates (11°22′N 142°35′E), vehicle/hydrophone designations (DSV Limiting Factor / Bathyscaphe Trieste), exact depth (10,994m / 36,070 ft), pressure (1,086 bar / 8 tons per square inch), and naval acoustic records.
3. Multi-Tier Visual Mix (LEMMiNO / Fincher Aesthetic):
   - For every scene, assign a visual "archetype" from:
     * "AI_CINEMATIC_RECREATION" (3D photorealistic crisis/abyss moments)
     * "INFOGRAPHIC_CODE2VIDEO" (3D animated tactical sonar maps, bathymetry HUDs, seismograms)
     * "FORENSIC_EVIDENCE" (declassified dossiers, naval incident reports, telegrams)
     * "ARCHIVAL_WITNESS" (historical submersible photography, expedition archives)
   - Rapid Rhythmic Cuts: Provide 2-4 dynamic "sub_prompts" and "sub_keywords" per scene so cuts occur every 2.0-2.4s.
4. Immersive Sound Design:
   - Prescribe cinematic audio cues in "sfx" (e.g. ["deep_braam", "radio_static", "whoosh", "riser", "ocean_swell"]).
5. Clean Retention Ending & Call to Action (CTA):
   - Complete the narrative thought before the CTA.
   - Conclude with: "Like and subscribe to uncover the unsealed files."

Requirements:
- Format narration with natural SSML tags (<prosody rate="+5%" pitch="-1Hz">, <break time="300ms"/>, <emphasis level="strong">).
- Total spoken word count MUST be strictly between 125 and 145 words to guarantee the entire short stays under 60.00 seconds.
- Assign intensity (1 to 10) and emotional_tag (tension, reveal, somber, triumphant, ambient_drone) to every scene.
- Return ONLY a single valid JSON object adhering to this schema:
{json.dumps(SCRIPT_JSON_SCHEMA, indent=2)}
"""
        else:
            word_target = 750 if runtime_target == "5m" else (1400 if runtime_target == "10m" else 450)
            scene_target = 22 if runtime_target == "5m" else (40 if runtime_target == "10m" else 15)
            prompt = f"""
Write a high-retention, binge-worthy investigative long-form documentary script about: "{topic}".
Target Runtime: {runtime_target} (Minimum {word_target} spoken words across approximately {scene_target} substantive scenes).

Strict 7-Act Long-Form Structure:
Act 1: The Cold-Open Hook (0:00-0:30, Intensity 9-10) — Open in media res on the impossible anomaly.
Act 2: The Setup & Status Quo (0:30-1:15, Intensity 3-4) — Meticulous context, technical blueprints, and the calm before the storm.
Act 3: The First Anomaly & Escalation (1:15-2:15, Intensity 5-6) — Chronological breadcrumbs and the first contradictory telemetry.
Act 4: The Midpoint Twist & Hidden Dossier (2:15-3:15, Intensity 7-8) — Declassified records that shatter the official government explanation.
Act 5: The Climax & System Collapse (3:15-4:15, Intensity 9-10) — The catastrophic culmination and the terrifying moment of truth.
Act 6: Forensic Resolution & The Cover-Up (4:15-4:45, Intensity 3-4) — Technical post-mortem, classified tribunals, and what authorities hid.
Act 7: The Modern Aftermath & Lingering Echo (4:45-5:00+, Intensity 5-6) — Modern satellites, unsealed archives, and final haunting open loop.

Requirements:
- Every scene MUST contain a substantive, multi-sentence paragraph (30-50 words per scene).
- Wrap dramatic narration lines in SSML tags (<prosody rate="..." pitch="...">, <break time="400ms"/>, <emphasis>).
- Assign intensity (1 to 10) and emotional_tag (tension, reveal, somber, triumphant, ambient_drone) to every scene.
- Return ONLY a single valid JSON object adhering to the schema.
"""

        # Model cascade: try gemini-3.5-flash first, then gemini-3.5-flash-lite, then gemini-3.6-flash
        models_to_try = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash"]
        last_error = None

        for model_id in models_to_try:
            try:
                print(f"[ScriptWriter] Calling Gemini API ({model_id})...")
                response = client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=SCRIPT_JSON_SCHEMA,
                        temperature=0.7,
                    )
                )
                raw_text = response.text.strip() if response and response.text else ""
                if raw_text.startswith("```"):
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)

                data = json.loads(raw_text)
                if data and "acts" in data and len(data["acts"]) > 0:
                    return data
            except Exception as ex:
                print(f"[ScriptWriter] Notice: Gemini ({model_id}) call returned: {ex}. Trying next model...")
                last_error = ex

        if last_error:
            raise last_error
        raise ValueError("Failed to generate script from Gemini models.")

    def _generate_structured_fallback(self, topic: str, runtime_target: str = "5m") -> dict:
        """
        Comprehensive, long-form documentary script generator built on DOCUMENTARY_BENCHMARKS.md
        and STORY_RULES.md. Produces 22 detailed scenes (~750 words, 5 minutes runtime)
        with forensic depth, primary source quotes, and full SSML markup.
        """
        clean_topic = topic.strip()

        # 60 to 90-Second Viral Short Form Target (YouTube Shorts / TikTok / Reels)
        if runtime_target in ["45s", "60s", "1m", "90s", "1.5m"] or "short" in str(runtime_target).lower():
            if "bermuda" in clean_topic.lower():
                return {
                    "topic": clean_topic,
                    "central_open_loop": "What truly caused Flight 19 and dozens of vessels to vanish in the Bermuda Triangle?",
                    "acts": [
                        {
                            "act_number": 1,
                            "act_name": "The Impossible Vanishing",
                            "scenes": [
                                {
                                    "scene_id": "act1_s1",
                                    "intensity": 10,
                                    "emotional_tag": "tension",
                                    "narration": "Never look at what the US Navy found beneath the Bermuda Triangle. On December 5th, 1945, five military bombers vanished over the Atlantic.",
                                    "ssml_narration": '<speak><prosody rate="+6%" pitch="-1Hz"><emphasis level="strong">Never look at what the US Navy found beneath the Bermuda Triangle.</emphasis></prosody> <break time="150ms"/> <prosody rate="+4%" pitch="-2Hz">On December 5th, 1945, five military bombers vanished over the Atlantic.</prosody></speak>',
                                    "visual_prompt": "Vintage aircraft cockpit dials shaking in violent storm, red emergency alarm light, military naval aviation 1945",
                                    "broll_keywords": ["military aircraft flying clouds", "stormy ocean aerial", "dark sea storm waves", "aircraft cockpit dials"],
                                    "sub_prompts": [
                                        "Vintage cockpit instrument panel glowing red in dark electrical storm, urgent military flight warning alert",
                                        "Classified US Navy military document stamped TOP SECRET with satellite map of Bermuda Triangle ocean coordinates",
                                        "Five US Navy TBM Avenger torpedo bombers flying in tight formation into pitch black Atlantic storm clouds",
                                        "Violent dark Atlantic ocean waves churning in squall, eerie misty horizon"
                                    ],
                                    "sub_keywords": [
                                        ["aircraft cockpit storm gauges", "red emergency light cockpit", "vintage cockpit flight"],
                                        ["classified top secret documents", "vintage military map", "naval ocean coordinates"],
                                        ["military aircraft flying clouds", "vintage bombers flight", "bomber formation sky"],
                                        ["dark stormy ocean waves", "storm sea crashing waves", "aerial ocean storm"]
                                    ],
                                    "motion": "zoom_punch",
                                    "sfx": ["deep_braam", "whoosh"]
                                },
                                {
                                    "scene_id": "act1_s2",
                                    "intensity": 9,
                                    "emotional_tag": "tension",
                                    "narration": "Compasses spun wildly as their commander sent one final transmission: 'Everything is wrong. Even the ocean looks strange.' Then, complete silence.",
                                    "ssml_narration": '<speak><prosody rate="+5%" pitch="-1Hz">Compasses spun wildly as their commander sent one final transmission:</prosody> <prosody rate="+2%" pitch="-2Hz"><emphasis level="strong">\'Everything is wrong. Even the ocean looks strange.\'</emphasis></prosody> <break time="200ms"/> <prosody rate="-2%" pitch="-3Hz">Then, complete silence.</prosody></speak>',
                                    "visual_prompt": "Extreme macro close-up of brass nautical compass needle spinning uncontrollably, dark electrical storm lightning",
                                    "broll_keywords": ["compass spinning erratic", "aircraft cockpit gauges dark", "stormy clouds lightning", "radio static"],
                                    "sub_prompts": [
                                        "Macro close-up of brass magnetic naval compass needle spinning erratically out of control in cockpit",
                                        "Naval pilot speaking desperately into vintage radio microphone inside shaking vibrating cockpit",
                                        "Vintage radio cathode-ray oscilloscope flatline wave, green phosphor static noise, dark screen"
                                    ],
                                    "sub_keywords": [
                                        ["compass spinning erratic", "magnetic compass needle dial", "nautical compass"],
                                        ["pilot radio headset cockpit", "naval radio communication", "cockpit pilot storm"],
                                        ["radio static oscilloscope", "green phosphor radar screen", "static noise signal"]
                                    ],
                                    "motion": "zoom_in",
                                    "sfx": ["whoosh", "radio_static_burst"]
                                }
                            ]
                        },
                        {
                            "act_number": 2,
                            "act_name": "The Unexplained Abyss",
                            "scenes": [
                                {
                                    "scene_id": "act2_s1",
                                    "intensity": 9,
                                    "emotional_tag": "reveal",
                                    "narration": "A rescue plane with thirteen men took off immediately. Twenty-seven minutes later, it vanished too. Zero wreckage. Zero survivors.",
                                    "ssml_narration": '<speak><prosody rate="+4%" pitch="-1Hz">A rescue plane with thirteen men took off immediately.</prosody> <break time="150ms"/> <prosody rate="+8%" pitch="+2Hz"><emphasis level="strong">Twenty-seven minutes later, it vanished too.</emphasis></prosody> <prosody rate="+2%" pitch="-2Hz">Zero wreckage. Zero survivors.</prosody></speak>',
                                    "visual_prompt": "Massive military seaplane flying boat taking off from naval runway into dense sea mist",
                                    "broll_keywords": ["flying boat aircraft taking off", "radar screen blip disappearing", "naval searchlight ocean fog"],
                                    "sub_prompts": [
                                        "Massive Martin PBM Mariner flying boat rescue aircraft taking off from naval base into dense fog",
                                        "Vintage green circular radar screen with glowing sweep line where aircraft blip suddenly blinks out",
                                        "Naval searchlight cutting through dense freezing ocean mist at night, completely empty water surface"
                                    ],
                                    "sub_keywords": [
                                        ["flying boat aircraft taking off", "military seaplane runway", "rescue plane taking off"],
                                        ["radar screen blip disappearing", "vintage military radar screen", "sonar radar green sweep"],
                                        ["naval searchlight ocean fog", "empty ocean search at night", "foggy sea waves night"]
                                    ],
                                    "motion": "pan_left",
                                    "sfx": ["deep_braam", "riser", "radar_ping"]
                                },
                                {
                                    "scene_id": "act2_s2",
                                    "intensity": 8,
                                    "emotional_tag": "somber",
                                    "narration": "Dozens of ships and aircraft have disappeared inside this deadly vortex. Scientists blame massive rogue waves and underwater methane explosions.",
                                    "ssml_narration": '<speak><prosody rate="+4%" pitch="-1Hz">Dozens of ships and aircraft have disappeared inside this deadly vortex.</prosody> <prosody rate="+6%" pitch="+1Hz">Scientists blame massive rogue waves and underwater methane explosions.</prosody></speak>',
                                    "visual_prompt": "Enormous rogue wave rising like a black wall in dark stormy ocean, deep underwater abyss bubbles",
                                    "broll_keywords": ["underwater shipwreck ocean floor", "massive rogue wave ocean", "underwater methane bubbles ocean"],
                                    "sub_prompts": [
                                        "Sunken historical steel shipwreck resting on dark abyssal ocean floor with underwater marine drift",
                                        "Terrifying 100-foot rogue wave rising like a massive black wall of water in violent stormy ocean",
                                        "Deep seabed volcanic rift erupting with colossal methane gas bubbles bursting toward dark surface"
                                    ],
                                    "sub_keywords": [
                                        ["underwater shipwreck ocean floor", "sunken ship abyss", "deep ocean wreck"],
                                        ["massive rogue wave ocean", "giant wave crashing sea", "storm ocean wall of water"],
                                        ["underwater methane bubbles ocean", "seabed hydrothermal vent gas", "underwater explosion bubbles"]
                                    ],
                                    "motion": "zoom_punch",
                                    "sfx": ["sub_impact", "whoosh"]
                                },
                                {
                                    "scene_id": "act2_s3",
                                    "intensity": 10,
                                    "emotional_tag": "tension",
                                    "narration": "Yet modern satellites still detect unexplained magnetic distortions deep beneath the seabed. Which is why navy pilots are still warned... Like and subscribe to uncover the unsealed files.",
                                    "ssml_narration": '<speak><prosody rate="+4%" pitch="-1Hz">Yet modern satellites still detect unexplained magnetic distortions deep beneath the seabed.</prosody> <break time="150ms"/> <prosody rate="+8%" pitch="+2Hz"><emphasis level="strong">Which is why navy pilots are still warned...</emphasis></prosody> <break time="200ms"/> <prosody rate="+6%" pitch="+1Hz"><emphasis level="strong">Like and subscribe to uncover the unsealed files.</emphasis></prosody></speak>',
                                    "visual_prompt": "Glowing satellite bathymetry scan of the Bermuda Triangle showing deep ocean floor trenches and magnetic anomalies",
                                    "broll_keywords": ["satellite earth ocean view", "deep ocean underwater trench", "pilot silhouette cockpit window", "like and subscribe button"],
                                    "sub_prompts": [
                                        "NASA satellite orbiting planet Earth with glowing blue bathymetry depth grid over Bermuda Triangle",
                                        "Deep underwater oceanic trench with glowing blue magnetic field distortion lines and sonar pulses",
                                        "Military naval pilot silhouette looking out cockpit canopy into endless dark Atlantic abyss at night",
                                        "High-tech tactical naval combat display with glowing holographic LIKE & SUBSCRIBE radar button alert over Bermuda Triangle coordinates"
                                    ],
                                    "sub_keywords": [
                                        ["satellite earth ocean view", "satellite orbiting earth space", "ocean bathymetry scan map"],
                                        ["deep ocean underwater trench", "sonar pulse deep water", "mysterious blue ocean abyss"],
                                        ["pilot silhouette cockpit window", "military pilot looking out", "dark ocean horizon clouds"],
                                        ["like and subscribe button", "tactical radar alert subscribe", "subscribe graphic animation"]
                                    ],
                                    "motion": "zoom_in",
                                    "sfx": ["impact_hit", "deep_braam"]
                                }
                            ]
                        }
                    ]
                }

            if any(k in clean_topic.lower() for k in ["mariana", "trench", "deep sea", "ocean anomaly", "abyss", "challenger deep"]):
                return {
                    "topic": clean_topic,
                    "central_open_loop": "What recorded a metallic 38-Hertz acoustic signal 36,000 feet beneath the Pacific Ocean?",
                    "acts": [
                        {
                            "act_number": 1,
                            "act_name": "The Abyssal Acoustic Anomaly",
                            "scenes": [
                                {
                                    "scene_id": "act1_s1",
                                    "intensity": 10,
                                    "emotional_tag": "tension",
                                    "narration": "Thirty-six thousand feet beneath the Pacific, inside the pitch-black abyss of Challenger Deep, titanium hydrophones recorded a sound that oceanographers cannot explain.",
                                    "ssml_narration": '<speak><prosody rate="+6%" pitch="-1Hz"><emphasis level="strong">Thirty-six thousand feet beneath the Pacific, inside the pitch-black abyss of Challenger Deep,</emphasis></prosody> <break time="150ms"/> <prosody rate="+4%" pitch="-2Hz">titanium hydrophones recorded a sound that oceanographers cannot explain.</prosody></speak>',
                                    "visual_prompt": "Deep sea titanium submersible probe sinking into pitch black Mariana Trench, bioluminescent marine snow, eerie ocean depth",
                                    "broll_keywords": ["deep sea underwater abyss", "submarine diving dark ocean", "ocean trench depth", "sonar screen pulsing"],
                                    "sub_prompts": [
                                        "Deep sea autonomous research hydrophone sinking slowly through pitch-black ocean abyss with bioluminescent particles",
                                        "Vintage analog sonar hydrophone recording console glowing in dim oceanographic research vessel control room",
                                        "3D bathymetric depth chart of Challenger Deep dropping into black canyon at 10,994 meters depth",
                                        "Heavy Pacific ocean storm waves crashing under ominous dark twilight sky"
                                    ],
                                    "sub_keywords": [
                                        ["deep sea underwater abyss", "submersible diving ocean", "dark underwater abyss"],
                                        ["sonar radar screen", "naval control room", "oceanographic research console"],
                                        ["bathymetric ocean map", "underwater canyon trench", "sonar depth display"],
                                        ["dark ocean storm waves", "stormy ocean sea", "heavy ocean swell"]
                                    ],
                                    "motion": "zoom_punch",
                                    "sfx": ["deep_braam", "whoosh"]
                                },
                                {
                                    "scene_id": "act1_s2",
                                    "intensity": 9,
                                    "emotional_tag": "tension",
                                    "narration": "At the bottom of the world, water pressure exceeds one thousand atmospheres, over eight tons per square inch. Yet the hydrophone captured a metallic, repeating acoustic pulse echoing through the bedrock.",
                                    "ssml_narration": '<speak><prosody rate="+5%" pitch="-1Hz">At the bottom of the world, water pressure exceeds one thousand atmospheres, over eight tons per square inch.</prosody> <break time="200ms"/> <prosody rate="+3%" pitch="-2Hz"><emphasis level="strong">Yet the hydrophone captured a metallic, repeating acoustic pulse echoing through the bedrock.</emphasis></prosody></speak>',
                                    "visual_prompt": "Crushing deep ocean pressure underwater viewport glass under extreme stress, deep blue water abyss",
                                    "broll_keywords": ["underwater viewport deep sea", "sonar frequency waveform display", "pressure gauge dial high", "deep ocean darkness"],
                                    "sub_prompts": [
                                        "Heavy titanium pressure hull viewport looking into empty black abyss of Mariana Trench",
                                        "Digital sound frequency analyzer displaying sharp rhythmic acoustic spikes at 38 Hertz",
                                        "Extreme high-pressure hydraulic ocean depth gauge needle pinned at maximum limit"
                                    ],
                                    "sub_keywords": [
                                        ["underwater submarine viewport", "deep ocean submersible hull", "ocean abyss darkness"],
                                        ["audio frequency waveform", "green oscilloscope sound wave", "sound frequency spectrum"],
                                        ["pressure gauge dial", "industrial pressure meter", "gauge dial instrument"]
                                    ],
                                    "motion": "zoom_in",
                                    "sfx": ["whoosh", "radar_ping"]
                                }
                            ]
                        },
                        {
                            "act_number": 2,
                            "act_name": "The Unsealed Spectrogram",
                            "scenes": [
                                {
                                    "scene_id": "act2_s1",
                                    "intensity": 9,
                                    "emotional_tag": "reveal",
                                    "narration": "When researchers from NOAA and Oregon State University isolated the audio spectrum, the acoustic pattern was dubbed the Western Pacific Biophony. But secondary sensors registered seismic movement travelling miles below the crust.",
                                    "ssml_narration": '<speak><prosody rate="+4%" pitch="-1Hz">When researchers from NOAA and Oregon State University isolated the audio spectrum, the acoustic pattern was dubbed the Western Pacific Biophony.</prosody> <break time="150ms"/> <prosody rate="+7%" pitch="+2Hz"><emphasis level="strong">But secondary sensors registered seismic movement travelling miles below the crust.</emphasis></prosody></speak>',
                                    "visual_prompt": "Declassified oceanographic research dossier with spectrogram frequency graph, red confidential stamp, naval research table",
                                    "broll_keywords": ["classified government documents", "seismic recording chart paper", "oceanographic research vessel night", "radar tracking display"],
                                    "sub_prompts": [
                                        "Classified Manila evidence dossier stamped DECLASSIFIED displaying acoustic spectrogram graphs",
                                        "Seismograph drum recorder needle trembling erratically tracing deep earth shockwaves",
                                        "Oceanographic research ship illuminated under spotlight beams on endless dark Pacific at night"
                                    ],
                                    "sub_keywords": [
                                        ["classified government dossier", "manila evidence folder", "redacted official documents"],
                                        ["seismograph drum paper needle", "seismic frequency graph", "analog scientific recorder"],
                                        ["ocean research vessel night", "ship spotlight ocean dark", "cargo vessel night sea"]
                                    ],
                                    "motion": "pan_left",
                                    "sfx": ["deep_braam", "riser"]
                                },
                                {
                                    "scene_id": "act2_s2",
                                    "intensity": 8,
                                    "emotional_tag": "somber",
                                    "narration": "While biologists suggested an unknown baleen whale species, acoustic engineers calculated that the sound source was moving at impossible speeds across the trench canyon, far exceeding any known biological creature.",
                                    "ssml_narration": '<speak><prosody rate="+4%" pitch="-1Hz">While biologists suggested an unknown baleen whale species,</prosody> <prosody rate="+6%" pitch="+1Hz"><emphasis level="strong">acoustic engineers calculated that the sound source was moving at impossible speeds across the trench canyon, far exceeding any known biological creature.</emphasis></prosody></speak>',
                                    "visual_prompt": "Massive dark silhouette moving deep beneath underwater oceanic canyon, eerie sonar ping ripples",
                                    "broll_keywords": ["underwater silhouette deep ocean", "submarine sonar navigation", "dark underwater canyon"],
                                    "sub_prompts": [
                                        "Massive dark underwater shadow gliding slowly over jagged abyssal oceanic canyon",
                                        "Naval acoustic hydrophone operator staring intently at cascading green waterfall display",
                                        "Declassified US Naval intelligence hydrophone transmission logs with heavy black redaction lines"
                                    ],
                                    "sub_keywords": [
                                        ["underwater silhouette deep ocean", "deep sea creature shadow", "mysterious underwater shape"],
                                        ["naval sonar operator display", "submarine control room dark", "radar waterfall display"],
                                        ["redacted military documents", "declassified naval archives", "blacked out text document"]
                                    ],
                                    "motion": "zoom_punch",
                                    "sfx": ["sub_impact", "whoosh"]
                                }
                            ]
                        },
                        {
                            "act_number": 3,
                            "act_name": "The Trieste Logs & Unsealed Files",
                            "scenes": [
                                {
                                    "scene_id": "act3_s1",
                                    "intensity": 9,
                                    "emotional_tag": "reveal",
                                    "narration": "Declassified naval sonar archives from Project Sound Surveillance revealed identical acoustic signatures dating back to 1960, when the bathyscaphe Trieste first descended to the trench floor.",
                                    "ssml_narration": '<speak><prosody rate="+4%" pitch="-1Hz">Declassified naval sonar archives from Project Sound Surveillance revealed identical acoustic signatures dating back to 1960,</prosody> <break time="150ms"/> <prosody rate="+6%" pitch="+1Hz"><emphasis level="strong">when the bathyscaphe Trieste first descended to the trench floor.</emphasis></prosody></speak>',
                                    "visual_prompt": "Vintage 1960 bathyscaphe Trieste submersible diving into deep ocean, vintage naval submarine control room",
                                    "broll_keywords": ["vintage submarine deep sea", "historic submersible diving", "naval sonar console 1960", "vintage naval archive"],
                                    "sub_prompts": [
                                        "Historical bathyscaphe Trieste submersible vessel descending through murky deep ocean water",
                                        "Vintage 1960 US Navy hydrophone monitoring station with reel to reel magnetic tape recorder spinning",
                                        "Declassified Department of the Navy incident logbook stamped CONFIDENTIAL open on wooden desk"
                                    ],
                                    "sub_keywords": [
                                        ["vintage submarine deep sea", "historic submersible underwater", "deep sea research sub"],
                                        ["reel to reel tape recorder vintage", "analog naval audio monitor", "sonar recording station"],
                                        ["declassified naval documents", "vintage military logbook", "classified stamp paper"]
                                    ],
                                    "motion": "pan_left",
                                    "sfx": ["deep_braam", "whoosh"]
                                },
                                {
                                    "scene_id": "act3_s2",
                                    "intensity": 10,
                                    "emotional_tag": "tension",
                                    "narration": "To this day, the raw hydrophone tapes remain classified under national defense directives. Seven miles down in total darkness, something is awake in the Earth's deepest scar. Like and subscribe to uncover the unsealed files.",
                                    "ssml_narration": '<speak><prosody rate="+4%" pitch="-1Hz">To this day, the raw hydrophone tapes remain classified under national defense directives.</prosody> <break time="150ms"/> <prosody rate="+6%" pitch="-2Hz"><emphasis level="strong">Seven miles down in total darkness, something is awake in the Earth\'s deepest scar.</emphasis></prosody> <break time="200ms"/> <prosody rate="+5%" pitch="+1Hz"><emphasis level="strong">Like and subscribe to uncover the unsealed files.</emphasis></prosody></speak>',
                                    "visual_prompt": "Satellite view of the Mariana Trench deep Pacific fracture, glowing bathymetric blue grid, cinematic YouTube outro framing",
                                    "broll_keywords": ["satellite view pacific ocean", "deep ocean trench glowing", "submersible robotic arm abyss", "like and subscribe button"],
                                    "sub_prompts": [
                                        "NASA satellite view of Earth orbiting over the deep Mariana Trench crescent in western Pacific",
                                        "Glowing blue digital bathymetry map tracking coordinates 11 degrees North, 142 degrees East",
                                        "Autonomous deep-sea exploration vehicle shining ultra-bright LED lights into infinite black ocean abyss",
                                        "Cinematic glowing tactical holographic SUBSCRIBE alert over Pacific Ocean nautical grid"
                                    ],
                                    "sub_keywords": [
                                        ["satellite view pacific ocean", "earth orbit satellite view", "pacific ocean satellite map"],
                                        ["bathymetric depth map grid", "sonar navigation display", "digital tactical map"],
                                        ["deep sea exploration submersible", "underwater robotic camera", "deep ocean led lights"],
                                        ["like and subscribe button", "tactical radar button", "subscribe button animation"]
                                    ],
                                    "motion": "zoom_in",
                                    "sfx": ["impact_hit", "deep_braam"]
                                }
                            ]
                        }
                    ]
                }

            return {
                "topic": clean_topic,
                "central_open_loop": f"What was truly uncovered during {clean_topic} that officials kept buried?",
                "acts": [
                    {
                        "act_number": 1,
                        "act_name": "The Unskippable Anomaly",
                        "scenes": [
                            {
                                "scene_id": "act1_s1",
                                "intensity": 10,
                                "emotional_tag": "tension",
                                "narration": f"In official records, the events of {clean_topic} were summarized in a few sanitized sentences. But unredacted archives tell a completely different story.",
                                "ssml_narration": f'<speak><prosody rate="+6%" pitch="-1Hz"><emphasis level="strong">In official records, the events of {clean_topic} were summarized in a few sanitized sentences.</emphasis></prosody> <break time="150ms"/> <prosody rate="+4%" pitch="-2Hz">But unredacted archives tell a completely different story.</prosody></speak>',
                                "visual_prompt": f"Dramatic declassified incident report during {clean_topic}, classified military dossiers, glowing investigation table",
                                "broll_keywords": ["classified file top secret", "declassified government archives", "dark military command room", "vintage microfilm reader"],
                                "sub_prompts": [
                                    f"Declassified government incident report stamped TOP SECRET regarding {clean_topic}",
                                    "Macro camera pan across vintage microfilm viewer displaying confidential inquiry logs",
                                    "Dim military intelligence archive room with rows of steel file cabinets",
                                    "Dark atmospheric horizon under heavy storm clouds with dramatic lightning"
                                ],
                                "sub_keywords": [
                                    ["classified file top secret", "redacted government documents", "vintage military dossier"],
                                    ["vintage microfilm reader", "microfilm archives", "retro computer display"],
                                    ["military intelligence archive", "dark document vault", "steel file cabinet rows"],
                                    ["dark stormy horizon", "storm lightning clouds", "dramatic atmospheric sky"]
                                ],
                                "motion": "zoom_punch",
                                "sfx": ["deep_braam", "whoosh"]
                            },
                            {
                                "scene_id": "act1_s2",
                                "intensity": 9,
                                "emotional_tag": "tension",
                                "narration": "Key physical telemetry registered impossible anomalies right before communication severed. When investigators arrived, standard physics offered no explanation.",
                                "ssml_narration": '<speak><prosody rate="+5%" pitch="-1Hz">Key physical telemetry registered impossible anomalies right before communication severed.</prosody> <break time="200ms"/> <prosody rate="-2%" pitch="-3Hz"><emphasis level="strong">When investigators arrived, standard physics offered no explanation.</emphasis></prosody></speak>',
                                "visual_prompt": "Vintage oscilloscope frequency dials fluctuating wildly, analog signal meters",
                                "broll_keywords": ["analog audio meters flickering", "oscilloscope green static", "radar tracking screen"],
                                "sub_prompts": [
                                    "Macro close-up of analog telemetry gauges and radio frequency dials twitching uncontrollably",
                                    "Vintage cathode-ray oscilloscope tube screen showing erratic waveform distortion",
                                    "Investigator examining baffling primary source telemetry under white inspection lights"
                                ],
                                "sub_keywords": [
                                    ["analog audio meters flickering", "electrical gauge dial", "scientific instrumentation"],
                                    ["oscilloscope green static", "radio static oscilloscope", "green phosphor static"],
                                    ["investigator examining documents", "forensic scientist laboratory", "dark analytical office"]
                                ],
                                "motion": "zoom_in",
                                "sfx": ["whoosh", "radio_static_burst"]
                            }
                        ]
                    },
                    {
                        "act_number": 2,
                        "act_name": "The Uncovered Dossier",
                        "scenes": [
                            {
                                "scene_id": "act2_s1",
                                "intensity": 9,
                                "emotional_tag": "reveal",
                                "narration": "Eyewitness logs and technical post-mortems confirm that an uncatalogued physical phenomenon occurred. Yet all physical evidence was abruptly classified under national security directives.",
                                "ssml_narration": '<speak><prosody rate="+4%" pitch="-1Hz">Eyewitness logs and technical post-mortems confirm that an uncatalogued physical phenomenon occurred.</prosody> <break time="150ms"/> <prosody rate="+7%" pitch="+2Hz"><emphasis level="strong">Yet all physical evidence was abruptly classified under national security directives.</emphasis></prosody></speak>',
                                "visual_prompt": "Massive underground vault door, classified files being sealed with red wax seal",
                                "broll_keywords": ["classified government vault", "redacted government documents", "military archive vault locked"],
                                "sub_prompts": [
                                    "Massive underground bank-vault steel security door swinging shut with heavy locking bolts",
                                    "Rubber stamp forcefully imprinting bold red RESTRICTED ink onto thick Manila evidence folder",
                                    "Macro camera pan across heavily blacked-out redacted lines in confidential inquiry transcripts"
                                ],
                                "sub_keywords": [
                                    ["classified government vault", "underground vault heavy door", "secure bunker vault"],
                                    ["rubber stamp classified secret", "manila evidence folder", "red ink top secret stamp"],
                                    ["redacted government documents", "leaked confidential files", "vintage microfilm archive"]
                                ],
                                "motion": "pan_left",
                                "sfx": ["deep_braam", "riser"]
                            },
                            {
                                "scene_id": "act2_s2",
                                "intensity": 8,
                                "emotional_tag": "somber",
                                "narration": "Decades later, declassified freedom of information requests uncovered the original sensor recordings, revealing what authorities knew from the very beginning.",
                                "ssml_narration": '<speak><prosody rate="+4%" pitch="-1Hz">Decades later, declassified freedom of information requests uncovered the original sensor recordings,</prosody> <prosody rate="+6%" pitch="+1Hz"><emphasis level="strong">revealing what authorities knew from the very beginning.</emphasis></prosody></speak>',
                                "visual_prompt": "Declassified government files unsealed on dark mahogany desk, dramatic rim lighting",
                                "broll_keywords": ["declassified documents desk", "vintage microfilm scanner", "analyst looking at files"],
                                "sub_prompts": [
                                    "Declassified Manila folder opening on dark investigative desk under warm desk lamp",
                                    "Digital scanner digitizing historical black and white incident photographs",
                                    "Senior analyst silhouette examining timeline map across dual glowing monitors"
                                ],
                                "sub_keywords": [
                                    ["declassified documents desk", "investigative files desk", "vintage evidence files"],
                                    ["scanner digitizing photos", "photographic archives", "historical documents scan"],
                                    ["analyst dual monitors", "control room analyst night", "computer monitor data glow"]
                                ],
                                "motion": "zoom_punch",
                                "sfx": ["sub_impact", "whoosh"]
                            },
                            {
                                "scene_id": "act2_s3",
                                "intensity": 10,
                                "emotional_tag": "tension",
                                "narration": "The full explanation remains buried in sealed government archives. Like and subscribe to uncover the unsealed files.",
                                "ssml_narration": '<speak><prosody rate="+5%" pitch="-1Hz">The full explanation remains buried in sealed government archives.</prosody> <break time="200ms"/> <prosody rate="+6%" pitch="+1Hz"><emphasis level="strong">Like and subscribe to uncover the unsealed files.</emphasis></prosody></speak>',
                                "visual_prompt": "Satellite orbiting Earth over glowing data anomaly coordinates, cinematic YouTube outro framing",
                                "broll_keywords": ["satellite orbiting earth space", "radar anomaly glow", "like and subscribe button"],
                                "sub_prompts": [
                                    "Satellite orbiting planet Earth in dark deep space above glowing blue telemetry grid",
                                    "Modern digital tracking radar sweep pulse over global coordinate map",
                                    "Investigator silhouette staring into glowing control room display in dim room",
                                    "Tactical glowing SUBSCRIBE alert button over coordinate map display"
                                ],
                                "sub_keywords": [
                                    ["satellite earth view space", "satellite orbiting earth space", "global tracking map"],
                                    ["radar anomaly glow", "digital energy pulse grid", "sensor telemetry surge"],
                                    ["analyst staring at screen", "control room dark silhouette", "warning screen flash"],
                                    ["like and subscribe button", "subscribe button animation", "tactical radar alert subscribe"]
                                ],
                                "motion": "zoom_in",
                                "sfx": ["impact_hit", "deep_braam"]
                            }
                        ]
                    }
                ]
            }

        script_dict = {
            "topic": clean_topic,
            "central_open_loop": f"What truly happened during {clean_topic} that military authorities and official records concealed from the world for decades?",
            "acts": [
                {
                    "act_number": 1,
                    "act_name": "The Cold-Open Hook",
                    "scenes": [
                        {
                            "scene_id": "act1_s1",
                            "intensity": 10,
                            "emotional_tag": "tension",
                            "narration": f"At precisely twelve minutes past midnight, deep within an unindexed military installation, the emergency alarms triggered across every console simultaneously. On the primary radar display, an unidentified contact appeared out of nowhere, hovered motionless for four seconds, and then vanished. [PAUSE:0.4s] Then, the entire monitoring grid went pitch black.",
                            "ssml_narration": f"<speak><prosody rate=\"-10%\" pitch=\"-4Hz\">At precisely twelve minutes past midnight, deep within an unindexed military installation, the emergency alarms triggered across every console simultaneously.</prosody> <prosody rate=\"-6%\" pitch=\"-2Hz\">On the primary radar display, an unidentified contact appeared out of nowhere, hovered motionless for four seconds, and then vanished.</prosody> <break time=\"400ms\"/> <prosody rate=\"+6%\" pitch=\"+2Hz\"><emphasis level=\"strong\">Then, the entire monitoring grid went pitch black.</emphasis></prosody></speak>",
                            "visual_prompt": "Dark military bunker control room, green CRT radar display showing sudden blip, red warning klaxons spinning, cinematic 16:9 4k",
                            "broll_keywords": ["radar screen blip", "military bunker control room", "emergency red lights alert"],
                            "motion": "zoom_punch",
                            "sfx": ["deep_braam", "whoosh"]
                        },
                        {
                            "scene_id": "act1_s2",
                            "intensity": 9,
                            "emotional_tag": "tension",
                            "narration": f"There was no Mayday broadcast. There was no distress frequency opened. When air traffic controllers frantically called back on the emergency guard channel, all they heard was dead silence, followed by an eerie, modulated electronic hum that didn't match any known aircraft.",
                            "ssml_narration": f"<speak><prosody rate=\"-8%\" pitch=\"-3Hz\">There was no Mayday broadcast. There was no distress frequency opened.</prosody> <prosody rate=\"-4%\" pitch=\"-1Hz\">When air traffic controllers frantically called back on the emergency guard channel, all they heard was dead silence, followed by an eerie, modulated electronic hum that didn't match any known aircraft.</prosody></speak>",
                            "visual_prompt": "Close-up of vintage oscilloscope waveform glowing green in dark cockpit, static electrical interference, macro anamorphic lens",
                            "broll_keywords": ["oscilloscope waveform monitor", "vintage radio headset", "static frequency radio"],
                            "motion": "zoom_in",
                            "sfx": ["whoosh"]
                        },
                        {
                            "scene_id": "act1_s3",
                            "intensity": 8,
                            "emotional_tag": "ambient_drone",
                            "narration": f"By sunrise, naval ships and reconnaissance aircraft were scouring the desolate expanse. But beneath the calm waves, there was zero wreckage, zero fuel slicks, and zero human survivors. This was the beginning of the mystery that would become known as {clean_topic}.",
                            "ssml_narration": f"<speak><prosody rate=\"-6%\" pitch=\"-2Hz\">By sunrise, naval ships and reconnaissance aircraft were scouring the desolate expanse.</prosody> <break time=\"400ms\"/> <prosody rate=\"+0%\" pitch=\"+0Hz\">But beneath the calm waves, there was zero wreckage, zero fuel slicks, and zero human survivors. This was the beginning of the mystery that would become known as {clean_topic}.</prosody></speak>",
                            "visual_prompt": "Vast open ocean under cold grey morning skies, lone search and rescue vessel in distance, atmospheric sea mist, cinematic wide shot",
                            "broll_keywords": ["ocean rescue ship", "foggy sea searchlights", "aerial ocean horizon"],
                            "motion": "subtle_drift",
                            "sfx": []
                        }
                    ]
                },
                {
                    "act_number": 2,
                    "act_name": "The Setup & Status Quo",
                    "scenes": [
                        {
                            "scene_id": "act2_s1",
                            "intensity": 3,
                            "emotional_tag": "ambient_drone",
                            "narration": f"To understand how this catastrophic event transpired, we have to look back at how impeccably ordinary everything appeared just hours earlier. On paper, the mission was deemed routine, fully cleared by every regulatory agency, and staffed by some of the most decorated veterans in the service.",
                            "ssml_narration": f"<speak><prosody rate=\"-2%\" pitch=\"-1Hz\">To understand how this catastrophic event transpired, we have to look back at how impeccably ordinary everything appeared just hours earlier.</prosody> <prosody rate=\"+0%\" pitch=\"+0Hz\">On paper, the mission was deemed routine, fully cleared by every regulatory agency, and staffed by some of the most decorated veterans in the service.</prosody></speak>",
                            "visual_prompt": "Archival dossier on wooden desk, black and white photographs of military personnel in uniform, mission flight logbook open, soft vintage tungsten lighting",
                            "broll_keywords": ["archival documents desk", "vintage flight logbook", "military personnel archive"],
                            "motion": "pan_left",
                            "sfx": []
                        },
                        {
                            "scene_id": "act2_s2",
                            "intensity": 3,
                            "emotional_tag": "somber",
                            "narration": "The pre-departure maintenance logs confirm that every single mechanical, electrical, and hydraulic subsystem had been thoroughly inspected. The telemetry recorders were calibrated, fuel tanks were completely topped off, and meteorological forecasts projected glass-smooth skies for hundreds of miles in every direction.",
                            "ssml_narration": "<speak><prosody rate=\"+0%\" pitch=\"+0Hz\">The pre-departure maintenance logs confirm that every single mechanical, electrical, and hydraulic subsystem had been thoroughly inspected. The telemetry recorders were calibrated, fuel tanks were completely topped off, and meteorological forecasts projected glass-smooth skies for hundreds of miles in every direction.</prosody></speak>",
                            "visual_prompt": "Vintage hangar floor, ground crew inspecting aircraft instruments with flashlights, blueprints laid out, atmospheric dust particles",
                            "broll_keywords": ["hangar ground crew aircraft", "vintage aircraft cockpit check", "meteorological weather map vintage"],
                            "motion": "subtle_drift",
                            "sfx": []
                        },
                        {
                            "scene_id": "act2_s3",
                            "intensity": 4,
                            "emotional_tag": "ambient_drone",
                            "narration": f"Those who spoke to the crew in their final briefing noted that morale was high. There was no hesitation, no apprehension, and absolutely no inkling of danger. Yet, buried deep within the auxiliary flight log, a single handwritten note was found decades later, stating simply: the instruments are fluctuating before we have even departed.",
                            "ssml_narration": "<speak><prosody rate=\"-2%\" pitch=\"-1Hz\">Those who spoke to the crew in their final briefing noted that morale was high. There was no hesitation, no apprehension, and absolutely no inkling of danger.</prosody> <break time=\"400ms\"/> <prosody rate=\"-6%\" pitch=\"-3Hz\">Yet, buried deep within the auxiliary flight log, a single handwritten note was found decades later, stating simply: the instruments are fluctuating before we have even departed.</prosody></speak>",
                            "visual_prompt": "Yellowed vintage paper with blurred handwritten ink, fountain pen resting beside classified stamp, close macro photography",
                            "broll_keywords": ["vintage handwritten letter", "yellowed paper archive", "fountain pen confidential notes"],
                            "motion": "zoom_in",
                            "sfx": ["whoosh"]
                        }
                    ]
                },
                {
                    "act_number": 3,
                    "act_name": "The First Anomaly & Escalation",
                    "scenes": [
                        {
                            "scene_id": "act3_s1",
                            "intensity": 5,
                            "emotional_tag": "tension",
                            "narration": "Forty-two minutes into the journey, the flight crossed the outer perimeter of civilian radar coverage. It was here that the first inexplicable telemetry distortion was recorded. The gyro-compasses, designed to maintain alignment through magnetic field anomalies, began rotating violently in complete 360-degree cycles.",
                            "ssml_narration": "<speak><prosody rate=\"+2%\" pitch=\"+1Hz\">Forty-two minutes into the journey, the flight crossed the outer perimeter of civilian radar coverage.</prosody> <prosody rate=\"-4%\" pitch=\"-2Hz\">It was here that the first inexplicable telemetry distortion was recorded. The gyro-compasses, designed to maintain alignment through magnetic field anomalies, began rotating violently in complete 360-degree cycles.</prosody></speak>",
                            "visual_prompt": "Aircraft cockpit compass dial spinning erratically under green night illumination, turbulent altimeter needle fluttering, intense cinematic drama",
                            "broll_keywords": ["spinning airplane compass", "cockpit gauges night", "altimeter dial turbulence"],
                            "motion": "zoom_punch",
                            "sfx": ["riser"]
                        },
                        {
                            "scene_id": "act3_s2",
                            "intensity": 6,
                            "emotional_tag": "tension",
                            "narration": "Radio communications with the regional control sector became rapidly degraded by heavy broadband static. The flight commander was heard asking if the sun had set in the wrong direction, reporting that the stars above their position did not correspond to any known navigational constellation.",
                            "ssml_narration": "<speak><prosody rate=\"-4%\" pitch=\"-2Hz\">Radio communications with the regional control sector became rapidly degraded by heavy broadband static.</prosody> <break time=\"400ms\"/> <prosody rate=\"-8%\" pitch=\"-4Hz\">The flight commander was heard asking if the sun had set in the wrong direction, reporting that the stars above their position did not correspond to any known navigational constellation.</prosody></speak>",
                            "visual_prompt": "Dark cockpit canopy looking out at distorted night sky with unfamiliar glowing constellations, static light interference, 16:9 cinematic",
                            "broll_keywords": ["night cockpit window stars", "radio static transmission tower", "vintage air traffic controller"],
                            "motion": "pan_right",
                            "sfx": ["whoosh"]
                        },
                        {
                            "scene_id": "act3_s3",
                            "intensity": 6,
                            "emotional_tag": "tension",
                            "narration": "Back on the mainland, air defense tracking stations picked up a secondary echo trailing directly behind the aircraft. It was traveling at an impossible airspeed, matching every evasive maneuver the flight attempted, before suddenly splitting into two distinct radar returns.",
                            "ssml_narration": "<speak><prosody rate=\"+4%\" pitch=\"+1Hz\">Back on the mainland, air defense tracking stations picked up a secondary echo trailing directly behind the aircraft.</prosody> <prosody rate=\"-6%\" pitch=\"-3Hz\">It was traveling at an impossible airspeed, matching every evasive maneuver the flight attempted, before suddenly splitting into two distinct radar returns.</prosody></speak>",
                            "visual_prompt": "Cold War military radar scope with two glowing phosphorescent blips converging, dimly lit bunker, tense officers looking on",
                            "broll_keywords": ["radar scope blips military", "cold war radar room", "air defense radar screen"],
                            "motion": "zoom_in",
                            "sfx": []
                        }
                    ]
                },
                {
                    "act_number": 4,
                    "act_name": "The Midpoint Twist & Hidden Dossier",
                    "scenes": [
                        {
                            "scene_id": "act4_s1",
                            "intensity": 7,
                            "emotional_tag": "reveal",
                            "narration": f"For over thirty years, the public was told that {clean_topic} was the unfortunate result of pilot disorientation and sudden severe weather. But in 2004, a mandatory declassification order unsealed thousands of pages from the naval intelligence vault, exposing the cover-up.",
                            "ssml_narration": f"<speak><prosody rate=\"-4%\" pitch=\"-2Hz\">For over thirty years, the public was told that {clean_topic} was the unfortunate result of pilot disorientation and sudden severe weather.</prosody> <break time=\"400ms\"/> <prosody rate=\"+6%\" pitch=\"+2Hz\"><emphasis level=\"strong\">But in 2004, a mandatory declassification order unsealed thousands of pages from the naval intelligence vault, exposing the cover-up.</emphasis></prosody></speak>",
                            "visual_prompt": "Declassified government file stamped TOP SECRET with red wax seal and bold red stamps, heavy black marker redactions across text, dramatic spotlight",
                            "broll_keywords": ["top secret declassified document", "redacted government files", "intelligence archive dossier"],
                            "motion": "zoom_punch",
                            "sfx": ["deep_braam"]
                        },
                        {
                            "scene_id": "act4_s2",
                            "intensity": 8,
                            "emotional_tag": "reveal",
                            "narration": "Among the unredacted files was a transcript from a classified submarine listening post located eight hundred miles away. Hydrophones on the ocean floor had detected an intense acoustic pulse, registering at over two hundred decibels, originating from the exact coordinates where the flight vanished.",
                            "ssml_narration": "<speak><prosody rate=\"-2%\" pitch=\"-1Hz\">Among the unredacted files was a transcript from a classified submarine listening post located eight hundred miles away.</prosody> <prosody rate=\"-6%\" pitch=\"-3Hz\">Hydrophones on the ocean floor had detected an intense acoustic pulse, registering at over two hundred decibels, originating from the exact coordinates where the flight vanished.</prosody></speak>",
                            "visual_prompt": "Submarine sonar operator in dimly lit red control room, glowing green circular sonar screen, headphones, intense focus",
                            "broll_keywords": ["submarine sonar room", "underwater hydrophone recording", "deep sea acoustic sensors"],
                            "motion": "pan_left",
                            "sfx": ["whoosh"]
                        },
                        {
                            "scene_id": "act4_s3",
                            "intensity": 7,
                            "emotional_tag": "somber",
                            "narration": "Even more chilling, the naval log revealed that two specialized interceptor jets had been scrambled thirty minutes prior to the disappearance, operating under an order that bypassed standard civilian channels entirely: find the craft, observe from maximum range, and do not engage.",
                            "ssml_narration": "<speak><prosody rate=\"-6%\" pitch=\"-3Hz\">Even more chilling, the naval log revealed that two specialized interceptor jets had been scrambled thirty minutes prior to the disappearance,</prosody> <prosody rate=\"-10%\" pitch=\"-4Hz\">operating under an order that bypassed standard civilian channels entirely: find the craft, observe from maximum range, and do not engage.</prosody></speak>",
                            "visual_prompt": "Two jet fighters parked on wet runway tarmac at night under floodlights, ground crew running, steam rising from asphalt",
                            "broll_keywords": ["military jets night runway", "fighter jets scrambling", "wet runway floodlights"],
                            "motion": "subtle_drift",
                            "sfx": []
                        }
                    ]
                },
                {
                    "act_number": 5,
                    "act_name": "The Climax & System Collapse",
                    "scenes": [
                        {
                            "scene_id": "act5_s1",
                            "intensity": 10,
                            "emotional_tag": "tension",
                            "narration": "At zero-zero-fifty-five hours, the climax of the incident unfolded. The flight recorder's telemetry signal suddenly registered an unrecoverable electrical surge, blowing out every circuit breaker in the cockpit in less than half a second.",
                            "ssml_narration": "<speak><prosody rate=\"+4%\" pitch=\"+1Hz\">At zero-zero-fifty-five hours, the climax of the incident unfolded.</prosody> <break time=\"400ms\"/> <prosody rate=\"+8%\" pitch=\"+3Hz\"><emphasis level=\"strong\">The flight recorder's telemetry signal suddenly registered an unrecoverable electrical surge, blowing out every circuit breaker in the cockpit in less than half a second.</emphasis></prosody></speak>",
                            "visual_prompt": "Cockpit electrical instrument panel sparking violently in darkness, instrument needles pinned to maximum, blinding electrical flash, cinematic slow motion",
                            "broll_keywords": ["electrical spark cockpit failure", "avionics instruments overload", "catastrophic aircraft failure"],
                            "motion": "zoom_punch",
                            "sfx": ["riser", "deep_braam"]
                        },
                        {
                            "scene_id": "act5_s2",
                            "intensity": 9,
                            "emotional_tag": "tension",
                            "narration": "The final fractured transmission from the cockpit contained only six words, spoken through severe electromagnetic interference: We are entering the cloud now. There is no horizon. Immediately following those words, all telemetry flatlined across the hemisphere.",
                            "ssml_narration": "<speak><prosody rate=\"-6%\" pitch=\"-3Hz\">The final fractured transmission from the cockpit contained only six words, spoken through severe electromagnetic interference:</prosody> <prosody rate=\"-12%\" pitch=\"-5Hz\"><emphasis level=\"strong\">We are entering the cloud now. There is no horizon.</emphasis></prosody> <prosody rate=\"-4%\" pitch=\"-2Hz\">Immediately following those words, all telemetry flatlined across the hemisphere.</prosody></speak>",
                            "visual_prompt": "Dense impenetrable vortex of clouds at night, lightning flashes illuminating strange geometric shapes within mist, cinematic 4k",
                            "broll_keywords": ["dark storm clouds lightning", "night sky storm vortex", "mysterious cloud formation"],
                            "motion": "zoom_in",
                            "sfx": ["whoosh"]
                        },
                        {
                            "scene_id": "act5_s3",
                            "intensity": 8,
                            "emotional_tag": "somber",
                            "narration": "Within minutes, the secondary radar contact disappeared as well, leaving nothing on the military consoles except ambient thermal noise. The entire search operation that followed was merely theater: authorities already knew that what occurred was completely beyond their ability to explain or recover.",
                            "ssml_narration": "<speak><prosody rate=\"-6%\" pitch=\"-3Hz\">Within minutes, the secondary radar contact disappeared as well, leaving nothing on the military consoles except ambient thermal noise.</prosody> <prosody rate=\"-4%\" pitch=\"-1Hz\">The entire search operation that followed was merely theater: authorities already knew that what occurred was completely beyond their ability to explain or recover.</prosody></speak>",
                            "visual_prompt": "Empty ocean surface at sunrise, waves rolling gently with no sign of human presence, cold cinematic melancholy",
                            "broll_keywords": ["calm ocean sunrise empty", "barren sea horizon", "ocean waves desolate"],
                            "motion": "subtle_drift",
                            "sfx": []
                        }
                    ]
                },
                {
                    "act_number": 6,
                    "act_name": "Forensic Resolution & The Cover-Up",
                    "scenes": [
                        {
                            "scene_id": "act6_s1",
                            "intensity": 4,
                            "emotional_tag": "somber",
                            "narration": "In the weeks following the catastrophe, an official investigative board was convened behind locked doors. Witnesses were required to sign lifetime nondisclosure agreements, and the physical radar magnetic tapes from that night were confiscated by federal agents.",
                            "ssml_narration": "<speak><prosody rate=\"-4%\" pitch=\"-2Hz\">In the weeks following the catastrophe, an official investigative board was convened behind locked doors. Witnesses were required to sign lifetime nondisclosure agreements, and the physical radar magnetic tapes from that night were confiscated by federal agents.</prosody></speak>",
                            "visual_prompt": "Heavy wooden boardroom table with closed manila folders, nameplates, dim overhead lighting, atmospheric shadows, cinematic vintage look",
                            "broll_keywords": ["confidential boardroom inquiry", "manila envelopes classified", "vintage government hearing"],
                            "motion": "pan_left",
                            "sfx": []
                        },
                        {
                            "scene_id": "act6_s2",
                            "intensity": 4,
                            "emotional_tag": "somber",
                            "narration": "The formal public report attributed the loss to unknown navigational confusion. But forensic investigators who reviewed the unredacted documents found that three separate pages containing the hydrophone acoustic analysis had been razor-blade sliced directly out of the master binder.",
                            "ssml_narration": "<speak><prosody rate=\"-2%\" pitch=\"-1Hz\">The formal public report attributed the loss to unknown navigational confusion.</prosody> <break time=\"400ms\"/> <prosody rate=\"-6%\" pitch=\"-3Hz\">But forensic investigators who reviewed the unredacted documents found that three separate pages containing the hydrophone acoustic analysis had been razor-blade sliced directly out of the master binder.</prosody></speak>",
                            "visual_prompt": "Archival binder open to jagged cut paper edges where pages were sliced out with razor, magnifying glass focusing on cut marks",
                            "broll_keywords": ["razor cut document pages", "missing archival records", "government archive mystery"],
                            "motion": "zoom_in",
                            "sfx": ["whoosh"]
                        },
                        {
                            "scene_id": "act6_s3",
                            "intensity": 5,
                            "emotional_tag": "ambient_drone",
                            "narration": "Independent scientists who modeled the magnetic disturbance suggested that an extreme localized ionospheric collapse or an unacknowledged deep-sea energy test could have produced the exact symptoms described in the final radio transmission.",
                            "ssml_narration": "<speak><prosody rate=\"-2%\" pitch=\"-1Hz\">Independent scientists who modeled the magnetic disturbance suggested that an extreme localized ionospheric collapse or an unacknowledged deep-sea energy test could have produced the exact symptoms described in the final radio transmission.</prosody></speak>",
                            "visual_prompt": "Scientific computer simulation displaying earth magnetosphere field lines fluctuating wildly, 3D wireframe globe, technical diagrams",
                            "broll_keywords": ["magnetosphere simulation 3D", "scientific earth wireframe", "atmospheric physics diagram"],
                            "motion": "subtle_drift",
                            "sfx": []
                        }
                    ]
                },
                {
                    "act_number": 7,
                    "act_name": "The Modern Aftermath & Lingering Echo",
                    "scenes": [
                        {
                            "scene_id": "act7_s1",
                            "intensity": 6,
                            "emotional_tag": "reveal",
                            "narration": f"Today, modern satellite constellations sweep across those exact ocean coordinates thousands of times each year. And yet, pilots and oceanographers quietly report that digital navigation systems still experience unexplained GPS drift when traversing that precise geographical corridor.",
                            "ssml_narration": f"<speak><prosody rate=\"-4%\" pitch=\"-2Hz\">Today, modern satellite constellations sweep across those exact ocean coordinates thousands of times each year.</prosody> <break time=\"400ms\"/> <prosody rate=\"+4%\" pitch=\"+1Hz\">And yet, pilots and oceanographers quietly report that digital navigation systems still experience unexplained GPS drift when traversing that precise geographical corridor.</prosody></speak>",
                            "visual_prompt": "Modern satellite in low earth orbit passing over blue planet, digital telemetry overlays, subtle lens flare, cinematic 16:9",
                            "broll_keywords": ["satellite orbit earth modern", "gps navigation telemetry map", "earth from space cinematic"],
                            "motion": "zoom_out",
                            "sfx": ["whoosh"]
                        },
                        {
                            "scene_id": "act7_s2",
                            "intensity": 7,
                            "emotional_tag": "tension",
                            "narration": f"The full classified files regarding {clean_topic} are scheduled to remain sealed until the end of this century. But whether this was an encounter with an unknown atmospheric phenomenon, an unacknowledged military black project, or something far stranger, one fact remains uncontested.",
                            "ssml_narration": f"<speak><prosody rate=\"-4%\" pitch=\"-2Hz\">The full classified files regarding {clean_topic} are scheduled to remain sealed until the end of this century.</prosody> <prosody rate=\"-8%\" pitch=\"-4Hz\">But whether this was an encounter with an unknown atmospheric phenomenon, an unacknowledged military black project, or something far stranger, one fact remains uncontested.</prosody></speak>",
                            "visual_prompt": "Concrete military archive underground vault door locked with heavy mechanical wheels, dramatic rim lighting, dust motes drifting",
                            "broll_keywords": ["military archive vault locked", "classified government vault", "concrete underground bunker"],
                            "motion": "subtle_drift",
                            "sfx": []
                        },
                        {
                            "scene_id": "act7_s3",
                            "intensity": 8,
                            "emotional_tag": "reveal",
                            "narration": f"Whatever happened out there in the dark... they were never truly alone. [PAUSE:0.4s] Click the video on your screen right now to uncover the declassified recordings they never wanted you to hear.",
                            "ssml_narration": f"<speak><prosody rate=\"-10%\" pitch=\"-4Hz\">Whatever happened out there in the dark... they were never truly alone.</prosody> <break time=\"400ms\"/> <prosody rate=\"+6%\" pitch=\"+2Hz\"><emphasis level=\"strong\">Click the video on your screen right now to uncover the declassified recordings they never wanted you to hear.</emphasis></prosody></speak>",
                            "visual_prompt": "Dark silhouette looking into an illuminated control room monitor displaying glowing geographical coordinates, cinematic YouTube outro framing 16:9",
                            "broll_keywords": ["cinematic outro silhouette", "glowing coordinates monitor", "mysterious dark control room"],
                            "motion": "zoom_punch",
                            "sfx": ["deep_braam", "whoosh"]
                        }
                    ]
                }
            ]
        }

        # For 8m or 10m long-form targets, inject comprehensive forensic expansion scenes
        if runtime_target in ["8m", "10m"]:
            base_script = script_dict
            # Add Act 3 expansion
            base_script["acts"][2]["scenes"].append({
                "scene_id": "act3_s4",
                "intensity": 6,
                "emotional_tag": "tension",
                "narration": f"Technical analysts who examined the emergency radio spectrum later discovered an anomalous acoustic Doppler shift in the background carrier wave. The pitch of the cockpit microphone had dropped by precisely fourteen hertz over two seconds, a signature that aerospace engineers note is consistent with sudden rapid atmospheric decompression or a violent magnetic surge.",
                "ssml_narration": f"<speak><prosody rate=\"-4%\" pitch=\"-2Hz\">Technical analysts who examined the emergency radio spectrum later discovered an anomalous acoustic Doppler shift in the background carrier wave.</prosody> <break time=\"400ms\"/> <prosody rate=\"+2%\" pitch=\"+1Hz\">The pitch of the cockpit microphone had dropped by precisely fourteen hertz over two seconds, a signature that aerospace engineers note is consistent with sudden rapid atmospheric decompression or a violent magnetic surge.</prosody></speak>",
                "visual_prompt": "Audio spectrogram visualization glowing neon green on black screen, frequencies fluctuating in waves, technical oscilloscope overlay",
                "broll_keywords": ["audio spectrogram display", "frequency waveform analysis", "vintage audio oscilloscope"],
                "motion": "zoom_in",
                "sfx": []
            })
            # Add Act 4 expansion
            base_script["acts"][3]["scenes"].append({
                "scene_id": "act4_s4",
                "intensity": 7,
                "emotional_tag": "reveal",
                "narration": f"Even more troubling were the naval thermal satellite records declassified forty years later. At the exact coordinates where the contact vanished, infrared sensors detected a circular localized sea-surface temperature drop of over four degrees Celsius within ninety seconds, a physical anomaly that oceanographers stated could not have occurred through any known natural weather phenomenon.",
                "ssml_narration": f"<speak><prosody rate=\"-2%\" pitch=\"-1Hz\">Even more troubling were the naval thermal satellite records declassified forty years later.</prosody> <break time=\"400ms\"/> <prosody rate=\"+4%\" pitch=\"+2Hz\">At the exact coordinates where the contact vanished, infrared sensors detected a circular localized sea-surface temperature drop of over four degrees Celsius within ninety seconds, a physical anomaly that oceanographers stated could not have occurred through any known natural weather phenomenon.</prosody></speak>",
                "visual_prompt": "Thermal satellite imagery heatmap displaying cold circular anomaly in deep blue ocean, temperature gradient scales, high resolution 4k",
                "broll_keywords": ["thermal satellite heatmap", "infrared ocean scan", "scientific temperature anomaly"],
                "motion": "pan_right",
                "sfx": ["whoosh"]
            })
            # Add Act 5 expansion
            base_script["acts"][4]["scenes"].append({
                "scene_id": "act5_s4",
                "intensity": 8,
                "emotional_tag": "tension",
                "narration": f"In a sealed deposition recorded before his death, the senior radar watch supervisor confessed that they had tracked two distinct radar returns descending in tandem from extreme altitude. But before the flight data could be exported to magnetic tape, senior officers arrived with armed escorts, ejected the reels, and placed the entire watch crew under strict communication quarantine.",
                "ssml_narration": f"<speak><prosody rate=\"-6%\" pitch=\"-3Hz\">In a sealed deposition recorded before his death, the senior radar watch supervisor confessed that they had tracked two distinct radar returns descending in tandem from extreme altitude.</prosody> <break time=\"400ms\"/> <prosody rate=\"-2%\" pitch=\"-1Hz\">But before the flight data could be exported to magnetic tape, senior officers arrived with armed escorts, ejected the reels, and placed the entire watch crew under strict communication quarantine.</prosody></speak>",
                "visual_prompt": "Vintage reel to reel magnetic tape recorder in dim security archive, tape spinning slowly, dramatic high contrast chiaroscuro",
                "broll_keywords": ["reel to reel tape spinning", "magnetic audio tape vintage", "classified tape archive"],
                "motion": "subtle_drift",
                "sfx": []
            })
            # Add Act 6 expansions
            base_script["acts"][5]["scenes"].append({
                "scene_id": "act6_s4",
                "intensity": 5,
                "emotional_tag": "ambient_drone",
                "narration": f"Declassified memos from the Naval Research Laboratory indicate that hydrophone listening stations spanning the Atlantic Ocean basin recorded an unprecedented acoustic pulse at the moment of the event. The signal possessed a low-frequency acoustic signature that traveled through the deep-water sound channel at over three thousand meters per second.",
                "ssml_narration": f"<speak><prosody rate=\"-4%\" pitch=\"-2Hz\">Declassified memos from the Naval Research Laboratory indicate that hydrophone listening stations spanning the Atlantic Ocean basin recorded an unprecedented acoustic pulse at the moment of the event.</prosody> <prosody rate=\"-2%\" pitch=\"-1Hz\">The signal possessed a low-frequency acoustic signature that traveled through the deep-water sound channel at over three thousand meters per second.</prosody></speak>",
                "visual_prompt": "Underwater hydrophone sensor array floating in dark abyss, glowing technical LED markers, particulate marine snow drifting, deep ocean blue",
                "broll_keywords": ["underwater hydrophone sensor", "deep ocean sound channel", "classified sonar listening station"],
                "motion": "subtle_drift",
                "sfx": []
            })
            base_script["acts"][5]["scenes"].append({
                "scene_id": "act6_s5",
                "intensity": 6,
                "emotional_tag": "somber",
                "narration": f"When independent archival researchers attempted to requisition the original hydrophone data reels under the Freedom of Information Act, the official agency response stated that the primary records had been destroyed in an accidental facility flood in 1984, leaving only secondary summary memos as the sole surviving evidence.",
                "ssml_narration": f"<speak><prosody rate=\"-2%\" pitch=\"-1Hz\">When independent archival researchers attempted to requisition the original hydrophone data reels under the Freedom of Information Act, the official agency response stated that the primary records had been destroyed in an accidental facility flood in 1984, leaving only secondary summary memos as the sole surviving evidence.</prosody></speak>",
                "visual_prompt": "Stamped government rejection document with red DENIED ink mark, official agency letterhead, vintage paper archive folder",
                "broll_keywords": ["government denied stamp", "freedom of information rejection", "redacted archival memo"],
                "motion": "pan_left",
                "sfx": ["whoosh"]
            })
            # Add Act 7 expansion
            base_script["acts"][6]["scenes"].insert(1, {
                "scene_id": "act7_s1b",
                "intensity": 7,
                "emotional_tag": "tension",
                "narration": f"To this day, maritime historians continue to search the ocean floor with high-resolution synthetic aperture sonar, hoping to locate even a fragment of the missing craft. Yet season after season, the survey vessels return with empty scans, as if whatever transpired that night left no earthly trace behind.",
                "ssml_narration": f"<speak><prosody rate=\"-4%\" pitch=\"-2Hz\">To this day, maritime historians continue to search the ocean floor with high-resolution synthetic aperture sonar, hoping to locate even a fragment of the missing craft.</prosody> <break time=\"400ms\"/> <prosody rate=\"-6%\" pitch=\"-3Hz\">Yet season after season, the survey vessels return with empty scans, as if whatever transpired that night left no earthly trace behind.</prosody></speak>",
                "visual_prompt": "Sonar scan display on research vessel showing dark seafloor bathymetry, glowing yellow contour lines, high tech survey monitor",
                "broll_keywords": ["sonar bathymetry screen", "ocean survey vessel monitor", "deep sea scan seafloor"],
                "motion": "zoom_in",
                "sfx": []
            })
            return base_script

        return script_dict
