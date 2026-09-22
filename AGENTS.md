# Autonomous Agent Directives & Production Rules

These rules are permanent project guidelines. Every AI agent working on this documentary studio codebase MUST adhere to these rules without exception.

---

## 1. Audio Balancing & Vocal Dominance (CRITICAL)
- **Narration voice MUST ALWAYS be significantly louder and clearer than background music and sound effects (SFX).**
- Voice is the hero element of the documentary. It anchors the viewer's attention and drives the story forward.
- **Voiceover Gain**: `DOCSTUDIO_VOICE_GAIN=1.00` (100% full scale, crisp transients, compressed, unmasked).
- **Music Bed Ducking**: Background music must duck by at least **-24.0 dB** (`DOCSTUDIO_DUCKING_DB=-24.0`) whenever the narrator speaks.
- **Music Pause Ceiling**: During speech pauses, nominal music gain is capped at `0.16` (`DOCSTUDIO_MUSIC_GAIN=0.16`) to prevent sudden volume spikes.
- **Sound Effects (SFX)**: Must be subtle accent cues (`DOCSTUDIO_SFX_GAIN=0.22`), and must automatically duck by **60%** during speech so consonants and syllables are never masked.
- **Master Loudness**: EBU R128 standard: `-14.0 LUFS` (`-1.0 dBTP`), driven primarily by dialogue clarity.

---

## 2. Retention & Pacing Rules (Shorts & Vertical Reels)
- **Narration Cadence**: Snappy **1.25x speed (+25% rate)** (`DOCSTUDIO_VOICE_RATE=+25%`). Eliminate sluggish delivery and dead air to maximize engagement velocity.
- **Rapid Cuts**: Maximum cut hold of **2.0s to 2.4s** (`rapid_cuts=True`). Never hold a static shot longer than 2.5 seconds in vertical shorts.
- **Strict Duration Limit**: For YouTube Shorts / TikTok / Reels, target runtime must stay strictly **under 60.00 seconds** (sweet spot: 45s - 50s at 1.25x speed) to guarantee short-form classification and prevent drop-offs.
- **Dynamic Camera Motion**: Every single visual cut must feature hardware-accelerated motion (Ken Burns punch-zoom, lateral pan, or crash-zoom).

---

## 3. Visual Sourcing & Photorealistic AI Generation
- **Authentic Historical Sourcing**: Prioritize real, historical archives (declassified photos, official maps, military records, patents, court filings) over generic stock footage.
- **Photorealistic 8K AI Generated Clips**: When authentic archives do not exist (e.g. ancient anomalies, deep-sea trenches, cockpit crisis moments, violent rogue waves), generate photorealistic 8K visuals and convert them into cinematic video clips.
- **Zero Stock Fluff**: Never use irrelevant generic corporate stock footage. Every shot must visually advance the specific narrative sentence being spoken.

---

## 4. Subtitles & Typography
- **Hormozi Word-by-Word Subtitles**: Use animated kinetic captions (`hormozi` style).
- **Active Word Highlighting**: Active word highlighted in bright neon green (`&H0000FF00`), outlined in black for maximum contrast across all visual backgrounds.
- **Screen Positioning**: Centered vertically in the lower third with safe zone padding to prevent overlap with platform UI controls (YouTube Shorts title/buttons).

---

## 5. Unskippable Hooks & Call To Action (CTA)
- **Cold Hook (0–8s)**: Start *in media res* with a catastrophic anomaly or classified revelation. Zero chronological preamble ("In 1945...").
- **Escalating Micro-Loops**: Raise stakes and open narrative questions every 10–15 seconds.
- **Call to Action (CTA)**: Always end with both spoken and visual **"Like and Subscribe"** triggers linked into an unsealed files loop (e.g. *"Like and subscribe to uncover the unsealed files"*).

---

## 6. Research & Topic Intelligence
- For any new topic, thoroughly investigate official historical records, geographic coordinates, vehicle serial numbers, timeline anomalies, and scientific theories to build a compelling, evidence-rich documentary script.

---

## 7. Multi-Tier Visual Mix & Pre-Render Storyboard Review (CRITICAL)
- **Zero Single-Source Domination**: A documentary must NEVER be composed purely of generic stock footage. Every film must execute a deliberate, multi-tier visual combination:
  1. **AI Cinematic Recreations (3D & Photorealistic)**: Crisis moments, extreme closeups, unseen historical anomalies (minimum 20-30% of cuts).
  2. **3D Animated Infographics & Tactical Overlays (`Code2Video`)**: Animated 3D nautical/air maps, radar sweeps, coordinate telemetry HUDs, live data counters (minimum 20% of cuts).
  3. **Forensic Archival Evidence**: Declassified government records, military logs, telegrams, and historical photos animated with 30fps macro 3D camera drift (minimum 20% of cuts).
  4. **Cinematic Atmospheric Stock**: Curated high-production natural environments (ocean swells, storm clouds) for transitions (maximum 30% of cuts).
- **Attentive & Unique Cold Hooks (0–8s)**: Cold hooks must be tailored specifically to the mystery's greatest shock element (e.g. abrupt 3D cockpit master alarm vs. pulsing magnetic radar anomaly vs. declassified telegram zoom).
- **Mandatory Pre-Render Combination Review**: Before generating assets or rendering video, the agent/studio MUST formulate and present the complete scene-by-scene visual archetype combination table to the user for approval.

