---
name: documentary-studio
description: Autonomous AI documentary video production studio. Produces high-retention, broadcast-ready 1080p documentary videos from raw topics or headlines with voiceover, animated captions, procedural sound design, and distribution assets.
---

# Documentary Studio (`documentary-studio`)

Use this skill whenever you need to produce, edit, or script a high-retention investigative documentary video (history, true crime, disasters, mysteries, science, biographies).

## Capabilities
1. **7-Act Storytelling Engine**: Strictly complies with `STORY_RULES.md`:
   - 0-15s cold-open hook (*in media res*, catastrophic anomaly, zero chronological fluff)
   - Macro/Meso open loops with delayed resolution
   - Escalating stakes every 30-45 seconds
   - Rhythmic narration cadence with `[PAUSE:0.5s]` tension markers
2. **Narration & Word-Level Timing**:
   - Uses `edge-tts` (Microsoft Neural documentary voices: `en-US-ChristopherNeural`, `en-GB-RyanNeural`)
   - Computes millisecond-precise word-boundary timestamps
3. **Animated Subtitles**:
   - Generates `.ass` subtitles with word-by-word active highlighting (`documentary`, `hormozi`, `mrbeast` styles)
4. **Visual Sourcing & Motion**:
   - Wikimedia Commons public domain archival photo search
   - Pexels stock video/photo search
   - **Google Gemini API Visual Generation** (Tier 3 fallback using existing user API key)
   - Procedural documentary graphic generation
   - Hardware-accelerated Ken Burns pan/zoom and punch zooms
5. **Master Audio & Vocal Dominance**:
   - **Vocal Dominance Rule**: Narration voice is the primary hero signal and is strictly +15dB to +20dB louder than background music and SFX.
   - Tagged royalty-free ambient beds (`tension`, `reveal`, `somber`, `triumphant`, `ambient_drone`)
   - Background score automatically ducked by -24dB during voiceover with nominal level capped at 0.16 in pauses.
   - SFX triggers (whooshes, braams, radar pings) treated as subtle accents (volume ~0.22) and actively ducked by 60% during speech.
   - 400ms sound vacuum silence before climactic reveals
   - EBU R128 loudness normalization (-14.0 LUFS, -1.0 dBTP) driven by vocal clarity.
6. **Automated QC & Distribution Assets**:
   - Pacing cadence (WPM) audit, dead air detection (>1.2s), static shot duration audit (<5s)
   - 3 high-CTR curiosity titles, thumbnail brief, and dual-platform SEO (YouTube + Bilibili)
7. **Agent-Programmable Timeline & Validated FCPXML 1.8 (@chatoctopus/timeline)**:
   - Programmatic multi-track timeline (`timeline.json`) enabling AI agent clip inspection, swapping, and ripple trimming
   - Export to frame-accurate Apple Final Cut Pro XML 1.8 (`timeline.fcpxml`) powered by `@chatoctopus/timeline`
   - Automated XML validation pre-check before file write to ensure zero broken project files
   - Interoperable with Palmier Pro, DaVinci Resolve, and Adobe Premiere Pro
8. **Real-Time Progress Tracking & Failure Visibility**:
   - Live `PROGRESS.md` at project root overwritten on every stage transition
   - Instant checkpoint presence verification (6 core stages)
   - Machine-readable per-run ledger (`run_state.json`)
   - Exact error trace dump on any stage failure

## CLI Usage

### Check Real-Time Pipeline Progress
```powershell
# View active or specific run progress
uv run python -m docstudio status --run-id the_lost_cosmonaut

# View all runs with completion states and total render times
uv run python -m docstudio status --all
```

### Run End-to-End Production
```powershell
uv run python -m docstudio run --topic "The Lost Cosmonaut: The Secret Soviet Space Disaster"
```

### Choose Narrator Voice & Subtitle Style
```powershell
uv run python -m docstudio run --topic "The Dyatlov Pass Mystery" --voice en-GB-RyanNeural --style documentary
```

### Re-render Specific Checkpoints
If you edit the script (`01_script.json`) or change the subtitle style, only re-render downstream stages without re-synthesizing everything:
```powershell
uv run python -m docstudio run --topic "The Dyatlov Pass Mystery" --force captions,render
```

### Agent-Programmable Timeline & Palmier Pro Operations
```powershell
# Check Palmier Pro OS compatibility and local MCP server status
uv run python -m docstudio timeline mcp-status

# Inspect timeline tracks, clips, and cut timings
uv run python -m docstudio timeline inspect --run-id the_lost_cosmonaut

# Swap B-roll clip for a specific scene
uv run python -m docstudio timeline swap --run-id the_lost_cosmonaut --scene act1_s1 --asset path/to/new_footage.jpg

# Ripple trim a scene duration by delta seconds (subsequent clips shift automatically)
uv run python -m docstudio timeline trim --run-id the_lost_cosmonaut --scene act1_s1 --delta 1.5

# Export timeline to Apple Final Cut Pro XML (FCPXML) for DaVinci Resolve or Palmier Pro
uv run python -m docstudio timeline export-fcpxml --run-id the_lost_cosmonaut

# Synchronize timeline to active Palmier Pro instance via local MCP
uv run python -m docstudio timeline sync-palmier --run-id the_lost_cosmonaut
```

## Production Directory Structure
All generated assets are checkpointed in `workspace/runs/<topic_slug>/`:
- `01_script.json`: 7-act script and scene cues with SSML prosody and intensity ratings
- `02_narration.wav`: Master voiceover audio (Edge-TTS with Kokoro failover)
- `02_word_timestamps.json`: Millisecond word boundaries
- `03_captions.ass`: Word-by-word animated subtitles
- `04_visuals/`: Downloaded and generated scene visual assets
- `license_manifest.json`: Full commercial clearance audit trail
- `05_audio_mix.wav`: Voice + ducked ambient score (-22dB) + SFX + EBU R128 loudness normalization
- `06_final_render.mp4`: Finished 1080p MP4 documentary video with film grain and vignette
- `timeline.json`: Multi-track agent-programmable timeline model
- `timeline.fcpxml`: Validated Apple Final Cut Pro XML 1.8 for NLE import (Palmier Pro / DaVinci Resolve)
- `run_state.json`: Per-run execution metrics, stage durations, and completion status
- `qc_report.json` & `qc_report.md`: Quality control audit report
- `distribution_meta.json` & `distribution_meta.md`: Titles, thumbnail brief, YouTube/Bilibili SEO

At Project Root:
- `PROGRESS.md`: Real-time status dashboard tracking current stage, elapsed time, and 6 core checkpoint statuses.


