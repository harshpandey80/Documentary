import json
import re
from pathlib import Path
from docstudio.config import (
    GEMINI_API_KEY,
    GROQ_API_KEY,
    OPENROUTER_API_KEY,
    DOCSTUDIO_LLM_PROVIDER,
    DOCSTUDIO_MODEL,
)
from docstudio.llm_chain import complete_json, LLMChainExhausted

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
        gemini_api_key: str = GEMINI_API_KEY,
        groq_api_key: str = GROQ_API_KEY,
        openrouter_api_key: str = OPENROUTER_API_KEY,
        provider: str = DOCSTUDIO_LLM_PROVIDER,
        model: str = DOCSTUDIO_MODEL,
    ):
        # Allow passing api_key as first positional arg for backwards compatibility
        if api_key:
            if api_key.startswith("gsk_"):
                self.groq_api_key = api_key
                self.gemini_api_key = gemini_api_key
                self.openrouter_api_key = openrouter_api_key
                self.provider = "groq"
            elif api_key.startswith("sk-or-") or api_key.startswith("sk-"):
                self.openrouter_api_key = api_key
                self.gemini_api_key = gemini_api_key
                self.groq_api_key = groq_api_key
                self.provider = "openrouter"
            else:
                self.gemini_api_key = api_key
                self.groq_api_key = groq_api_key
                self.openrouter_api_key = openrouter_api_key
                self.provider = provider
        else:
            self.gemini_api_key = gemini_api_key
            self.groq_api_key = groq_api_key
            self.openrouter_api_key = openrouter_api_key
            self.provider = provider

        self.api_key = self.gemini_api_key or self.groq_api_key or self.openrouter_api_key
        self.model = model

    def generate_script(self, topic: str, output_file: Path, runtime_target: str = "5m") -> dict:
        """
        Generate a comprehensive documentary script with scene cues,
        beat intensity (1-10), emotional audio tags, SSML performance narration,
        b-roll keywords, and SFX triggers scaled to the target runtime.
        """
        script_data = None

        # 1. Primary provider attempt via resilient LLM chain (Gemini -> Groq -> OpenRouter)
        try:
            print(f"[ScriptWriter] Generating documentary script via LLM chain ({self.provider})...")
            script_data = self._generate_with_gemini(topic, runtime_target=runtime_target)
        except Exception as e:
            print(f"[ScriptWriter] LLM chain script generation error: {e}. Trying legacy provider fallback...")

        # 2. Legacy fallback to OpenRouter direct REST if needed
        if not script_data and self.openrouter_api_key:
            try:
                print(f"[ScriptWriter] Fallback: Generating documentary script via OpenRouter direct ({self.model})...")
                script_data = self._generate_with_openrouter(topic, runtime_target=runtime_target)
            except Exception as e:
                print(f"[ScriptWriter] OpenRouter direct fallback warning: {e}.")

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
     a) Cold Hook (0-8s): The impossible paradox, anomaly, or primary crisis event.
     b) Context & Coordinates (8-20s): Exact location coordinates, date/time, physical parameters or baseline measurements.
     c) Anomaly & Telemetry (20-35s): What instruments detected or what anomalous data occurred.
     d) Forensic Revelation (35-46s): The unsealed findings, official investigations, and ruled-out hypotheses.
     e) Resolution & CTA (46-50s): Final compelling resolution, concluding with: 'Like and subscribe to uncover the unsealed files.'"""

            prompt = f"""You are an elite documentary director and forensic investigator writing a high-retention cinematic documentary script about: "{topic}".
Target Format: {duration_desc}.

CRITICAL SHORT-FORM STORYTELLING DIRECTIVES:
1. Complete, Self-Contained Story (STRICTLY UNDER 60 SECONDS TOTAL):
   - A YouTube Short must NEVER be cut off mid-sentence or feel like half-information.
   - It MUST deliver a complete, punchy narrative arc:
{timing_guide}
2. Absolute Factual Grounding (ZERO HALLUCINATIONS / ZERO NONSENSE):
   - NO generic filler cliches (NEVER mention vague 'authorities scrambling' or generic fluff).
   - Use precise real-world facts: exact coordinates, official vehicle/vessel/instrument designations, measured numbers, dates, and archival records.
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

        # Delegate to the Phase 4 LLM chain (Gemini -> Groq -> OpenRouter)
        from docstudio.llm_chain import complete_json, LLMChainExhausted
        try:
            data = complete_json(
                prompt=prompt,
                system=SYSTEM_INSTRUCTION,
                temperature=0.7,
                provider_override=self.provider if self.provider in ("gemini", "groq", "openrouter") else None,
            )
            if data and "acts" in data and len(data["acts"]) > 0:
                return data
            raise ValueError("LLM chain returned valid JSON but missing 'acts' key.")
        except LLMChainExhausted as exc:
            raise RuntimeError(str(exc)) from exc

    def _generate_structured_fallback(self, topic: str, runtime_target: str = "5m") -> dict:
        """
        Comprehensive, long-form documentary script generator built on DOCUMENTARY_BENCHMARKS.md
        and STORY_RULES.md. Produces 22 detailed scenes (~750 words, 5 minutes runtime)
        with forensic depth, primary source quotes, and full SSML markup.
        """
        clean_topic = topic.strip()

        # Check if an external pre-authored script matches in examples/
        examples_dir = Path("examples")
        if examples_dir.exists():
            clean_slug = clean_topic.lower().replace(" ", "_").replace(",", "").replace("-", "_")
            for cand in [
                examples_dir / f"{clean_slug}.json",
                examples_dir / f"{clean_slug}_short.json",
                examples_dir / f"{clean_slug}_longform.json",
            ]:
                if cand.exists():
                    try:
                        with open(cand, "r", encoding="utf-8") as ef:
                            print(f"  [ScriptWriter] 📖 Loaded pre-authored script from examples: {cand.name}")
                            return json.load(ef)
                    except Exception as err:
                        print(f"  [ScriptWriter] Notice loading example {cand.name}: {err}")

        # 60 to 90-Second Viral Short Form Target (YouTube Shorts / TikTok / Reels)
        if runtime_target in ["45s", "60s", "1m", "90s", "1.5m"] or "short" in str(runtime_target).lower():

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

    @staticmethod
    def _normalize_emotional_tag(tag: str) -> str:
        tag_lower = str(tag or "").lower().strip()
        valid = {"tension", "reveal", "somber", "triumphant", "ambient_drone"}
        if tag_lower in valid:
            return tag_lower
        tag_map = {
            "suspense": "tension",
            "mystery": "tension",
            "dramatic": "tension",
            "ominous": "tension",
            "shocking": "reveal",
            "discovery": "reveal",
            "wonder": "reveal",
            "curiosity": "reveal",
            "sad": "somber",
            "tragic": "somber",
            "reflective": "somber",
            "melancholy": "somber",
            "triumph": "triumphant",
            "heroic": "triumphant",
            "ambient": "ambient_drone",
            "drone": "ambient_drone",
            "calm": "ambient_drone",
        }
        return tag_map.get(tag_lower, "tension")

    def generate_narration_from_story(
        self,
        story_data: dict,
        claims_data: dict | None = None,
        output_file: Path | None = None,
        runtime_target: str = "5m",
        style: str = "cinematic_investigative",
    ) -> dict:
        """
        Generates structured narration grounded in the story architecture (story.json)
        and verified claims (claims.json).
        
        Every narration paragraph explicitly maps to claim_ids and story beats.
        Returns a dict containing:
          - topic
          - logline
          - central_open_loop
          - paragraphs: list of paragraph dicts with claim_ids, beat_id, text, etc.
          - acts: backward-compatible list of acts and scenes for downstream renderers.
        """
        topic = story_data.get("topic", "Documentary")
        beats = story_data.get("beats", [])
        
        # Build claims lookup map for grounding
        claims_lookup = {}
        if claims_data and "claims" in claims_data:
            for c in claims_data["claims"]:
                cid = c.get("claim_id")
                if cid:
                    stmt = c.get("statement") or c.get("claim", "")
                    claims_lookup[cid] = stmt

        # Attempt generation via LLM chain
        narration_data = None
        try:
            narration_data = self._generate_narration_with_llm(
                story_data=story_data,
                claims_lookup=claims_lookup,
                runtime_target=runtime_target,
                style=style,
            )
        except Exception as exc:
            print(f"[ScriptWriter] LLM narration generation unavailable ({exc}). Using structured deterministic narration engine.")
            narration_data = None

        if not narration_data or not narration_data.get("paragraphs"):
            narration_data = self._build_deterministic_narration(
                story_data=story_data,
                claims_lookup=claims_lookup,
                runtime_target=runtime_target,
            )

        # Ensure compatibility acts array exists alongside paragraphs
        if "acts" not in narration_data or not narration_data["acts"]:
            narration_data["acts"] = self._assemble_acts_from_paragraphs(
                paragraphs=narration_data["paragraphs"],
                topic=topic,
                central_open_loop=story_data.get("central_question", ""),
            )

        if output_file:
            out_p = Path(output_file)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:
                json.dump(narration_data, f, indent=2, ensure_ascii=False)

        return narration_data

    def _generate_narration_with_llm(
        self,
        story_data: dict,
        claims_lookup: dict,
        runtime_target: str,
        style: str,
    ) -> dict | None:
        topic = story_data.get("topic", "")
        beats = story_data.get("beats", [])
        beats_summary = []
        for b in beats:
            b_claims = [f"{cid}: {claims_lookup.get(cid, '')}" for cid in b.get("claim_ids", []) if cid in claims_lookup]
            beats_summary.append({
                "beat_id": b.get("beat_id"),
                "story_function": b.get("story_function"),
                "viewer_learning": b.get("viewer_learning"),
                "viewer_seeing_intent": b.get("viewer_seeing_intent"),
                "target_duration_s": b.get("target_duration_s"),
                "claim_ids": b.get("claim_ids", []),
                "referenced_claims": b_claims,
                "intensity": b.get("intensity", 7),
                "mood": b.get("mood", "tension"),
            })

        system_prompt = (
            "You are an elite, award-winning investigative documentary director and scriptwriter (LEMMiNO / Vox style).\n"
            "Write high-retention, authentic documentary narration directly grounded in the provided story architecture and claims.\n"
            "RULES:\n"
            "1. Every paragraph must advance one specific story beat.\n"
            "2. Ground each paragraph in the provided claims; output the claim_ids used.\n"
            "3. Hook immediately in media res. Never open with chronological clichés like 'In the year...'.\n"
            "4. For each paragraph, provide visual_prompt, broll_keywords (3-4 terms), motion (zoom_in, zoom_punch, pan_left, pan_right, subtle_drift), and sfx.\n"
            "5. Tone: Concise, curious, rhythmic, and factual. No generic AI filler.\n"
            "6. Conclude the final paragraph with: 'Like and subscribe to uncover the unsealed files.'\n"
            "7. Return JSON matching schema: {\"paragraphs\": [{\"paragraph_id\": \"P01\", \"beat_id\": \"...\", \"story_beat\": \"...\", \"text\": \"...\", \"claim_ids\": [...], \"emotional_tag\": \"...\", \"intensity\": 7, \"visual_prompt\": \"...\", \"broll_keywords\": [...], \"motion\": \"...\", \"sfx\": [...]}]}"
        )

        user_prompt = (
            f"Topic: {topic}\n"
            f"Runtime Target: {runtime_target}\n"
            f"Style: {style}\n"
            f"Central Question: {story_data.get('central_question', '')}\n"
            f"Logline: {story_data.get('logline', '')}\n"
            f"Story Beats & Claims:\n{json.dumps(beats_summary, indent=2)}\n\n"
            "Generate structured narration paragraphs."
        )

        res = complete_json(user_prompt, system_prompt, temperature=0.3)
        if isinstance(res, dict) and "paragraphs" in res and res["paragraphs"]:
            # Format and enrich paragraphs
            paragraphs = []
            for idx, p in enumerate(res["paragraphs"]):
                pid = p.get("paragraph_id") or f"P{idx+1:02d}"
                text = p.get("text", "")
                words = len(text.split())
                dur = round(words / 2.3, 2)
                paragraphs.append({
                    "paragraph_id": pid,
                    "beat_id": p.get("beat_id", f"B{idx+1:02d}"),
                    "scene_id": f"s_{idx+1}",
                    "story_beat": p.get("story_beat", "investigation"),
                    "text": text,
                    "claim_ids": p.get("claim_ids", []),
                    "intensity": p.get("intensity", 7),
                    "emotional_tag": self._normalize_emotional_tag(p.get("emotional_tag", "tension")),
                    "estimated_duration_sec": dur,
                    "visual_prompt": p.get("visual_prompt", "Archival photograph and cinematic motion"),
                    "broll_keywords": p.get("broll_keywords", [topic, "documentary"]),
                    "motion": p.get("motion", "zoom_in"),
                    "sfx": p.get("sfx", []),
                })
            return {
                "topic": topic,
                "logline": story_data.get("logline", ""),
                "central_open_loop": story_data.get("central_question", ""),
                "paragraphs": paragraphs,
                "acts": self._assemble_acts_from_paragraphs(paragraphs, topic, story_data.get("central_question", "")),
            }
        return None

    def _build_deterministic_narration(
        self,
        story_data: dict,
        claims_lookup: dict,
        runtime_target: str,
    ) -> dict:
        topic = story_data.get("topic", "Documentary")
        beats = story_data.get("beats", [])
        paragraphs = []

        for idx, beat in enumerate(beats):
            pid = f"P{idx+1:02d}"
            bid = beat.get("beat_id", f"B{idx+1:02d}")
            s_func = beat.get("story_function", "investigation")
            learning = beat.get("viewer_learning", "")
            claim_ids = beat.get("claim_ids", [])
            seeing_intent = beat.get("viewer_seeing_intent", "Archival document review and cinematic analysis")

            # Collect factual statements
            claim_texts = [claims_lookup[cid] for cid in claim_ids if cid in claims_lookup]

            # Construct crisp, documentary-style narration
            if s_func == "hook":
                text = f"At the center of the {topic} investigation lies an anomaly that defies conventional explanation: {story_data.get('central_question', 'what truly occurred')}."
                if learning:
                    text += f" {learning}"
            elif s_func == "resolution":
                text = f"{learning} Despite decades of inquiry, the primary files remain contested. Like and subscribe to uncover the unsealed files."
            else:
                text = learning
                if claim_texts:
                    # Incorporate factual evidence smoothly
                    text += f" Official records indicate that {claim_texts[0]}."

            words = len(text.split())
            dur = max(2.5, round(words / 2.3, 2))
            
            # Map mood
            mood = beat.get("mood", "tension")
            if mood not in ["tension", "reveal", "somber", "triumphant", "ambient_drone"]:
                mood = "tension" if beat.get("intensity", 5) > 6 else "somber"

            motion = "zoom_punch" if s_func == "hook" else ("pan_right" if idx % 2 == 1 else "zoom_in")
            sfx = ["deep_braam"] if s_func == "hook" else (["riser"] if s_func == "turning_point" else [])

            paragraphs.append({
                "paragraph_id": pid,
                "beat_id": bid,
                "scene_id": f"s_{idx+1}",
                "story_beat": s_func,
                "text": text,
                "claim_ids": claim_ids,
                "intensity": beat.get("intensity", 6),
                "emotional_tag": mood,
                "estimated_duration_sec": dur,
                "visual_prompt": f"{seeing_intent}, high resolution 4k cinematic documentary style",
                "broll_keywords": [topic, s_func, "forensic archival"],
                "motion": motion,
                "sfx": sfx,
            })

        return {
            "topic": topic,
            "logline": story_data.get("logline", ""),
            "central_open_loop": story_data.get("central_question", ""),
            "paragraphs": paragraphs,
            "acts": self._assemble_acts_from_paragraphs(paragraphs, topic, story_data.get("central_question", "")),
        }

    def _assemble_acts_from_paragraphs(
        self,
        paragraphs: list,
        topic: str,
        central_open_loop: str,
    ) -> list:
        """
        Organizes flat paragraphs into structured acts with scenes for backward-compatible rendering.
        """
        if not paragraphs:
            return []

        # Divide paragraphs into acts (approx 3-4 scenes per act)
        chunk_size = 4
        chunks = [paragraphs[i:i + chunk_size] for i in range(0, len(paragraphs), chunk_size)]
        acts = []

        act_names = [
            "The Anomaly & Cold Hook",
            "The Initial Timeline & Records",
            "Forensic Contradictions & Evidence",
            "The Deep Analysis",
            "Unresolved Enigmas & Verdict",
        ]

        for a_idx, chunk in enumerate(chunks):
            act_num = a_idx + 1
            act_name = act_names[a_idx] if a_idx < len(act_names) else f"Act {act_num}: Continued Investigation"
            scenes = []

            for s_idx, p in enumerate(chunk):
                sc_id = f"act{act_num}_s{s_idx + 1}"
                text = p.get("text", "")
                scenes.append({
                    "scene_id": sc_id,
                    "paragraph_id": p.get("paragraph_id", f"P{s_idx+1:02d}"),
                    "beat_id": p.get("beat_id", ""),
                    "claim_ids": p.get("claim_ids", []),
                    "intensity": p.get("intensity", 6),
                    "emotional_tag": p.get("emotional_tag", "tension"),
                    "narration": text,
                    "ssml_narration": f"<speak><prosody rate=\"-2%\" pitch=\"-1Hz\">{text}</prosody></speak>",
                    "visual_prompt": p.get("visual_prompt", f"{topic} archival footage"),
                    "broll_keywords": p.get("broll_keywords", [topic]),
                    "motion": p.get("motion", "zoom_in"),
                    "sfx": p.get("sfx", []),
                })

            acts.append({
                "act_number": act_num,
                "act_name": act_name,
                "scenes": scenes,
            })

        return acts
