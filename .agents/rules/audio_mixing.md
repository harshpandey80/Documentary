# Audio Mixing & Retention Rules for Documentaries

## Golden Audio Rule: Voiceover Dominance
The **narration voice MUST ALWAYS be significantly louder and clearer** than background music and sound effects (SFX).

1. **Dialogue is the Hero**:
   - The narration voice is the primary vehicle for viewer retention and comprehension.
   - Narration voice gain must be kept prominent (`DOCSTUDIO_VOICE_GAIN=1.00`), crisp, and uncompressed by competing tracks.

2. **Ducking & Background Music Subordination**:
   - Music beds must sit comfortably underneath the narrator at all times.
   - Music volume during active speech must be ducked by at least **-24dB** (`DOCSTUDIO_DUCKING_DB=-24.0`).
   - Nominal music volume during pauses must not exceed `DOCSTUDIO_MUSIC_GAIN=0.16` to prevent jarring volume jumps.

3. **Subtle Accent Sound Effects (SFX)**:
   - Sound effects (braams, whooshes, radar pings, hits) are subtle accents, NOT primary audio events.
   - SFX master volume must be capped at `DOCSTUDIO_SFX_GAIN=0.22`.
   - When the narrator is speaking, SFX must automatically sidechain-duck by 60% so consonant clarity is never obscured.

4. **Master Loudness Target**:
   - Final composite master must normalize to **-14.0 LUFS** (EBU R128 standard) with true peak capped at **-1.0 dBTP**, calibrated to the voice as the dominant energy driver.
