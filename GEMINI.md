# Documentary Studio Production & Autonomous Agent Rules

See [AGENTS.md](file:///c:/Users/Harsh%20Pandey/OneDrive/Desktop/documentry-AI/AGENTS.md) for the complete ruleset.

## Summary of Core Requirements:
1. **Audio Balancing (CRITICAL)**:
   - Voiceover is ALWAYS significantly louder and clearer than background music and SFX.
   - Voice gain: 1.00. Music ducked to -24 dB during speech (pause ceiling: 0.16). SFX gain: 0.22, ducked by 60% during speech. Master loudness: EBU R128 -14.0 LUFS (-1.0 dBTP).
2. **Pacing & Cadence**:
   - 1.25x narration speed (+25% rate).
   - Rapid cuts: maximum cut hold 2.0s - 2.4s.
   - Strictly under 60.00s for Shorts/Reels/TikTok.
3. **Visuals & AI Clips**:
   - Prioritize exact historical archives.
   - Use photorealistic 8K AI-generated clips for dramatic/unseen scenes.
   - Dynamic motion (Ken Burns) on every shot.
4. **Subtitles & CTA**:
   - Hormozi word-by-word active green highlighting.
5. **Multi-Tier Visual Mix & Pre-Render Storyboard Review (CRITICAL)**:
   - Ban 100% stock footage compilations.
   - Intelligently combine all 4 tiers: AI Cinematic Recreations (3D), 3D Animated Tactical Maps (`Code2Video`), Declassified Forensic Records, and Atmospheric Cinema Stock.
   - Create attentive, unique cold hooks (0–8s) tailored to the mystery.
   - Always present the visual combination plan to the user before rendering.
6. **100% Narration-Grounded AI Visual Engine (STRICT RULE)**:
   - Ban repetitive procedural dossier overlays, canvas templates, and static map cards.
   - Every scene visual MUST be an authentic, photorealistic AI-generated clip generated specifically from the exact spoken line of narration.
   - Enabled by default via `DOCSTUDIO_ALL_AI_VISUALS=1` (`--all-ai-visuals`).

