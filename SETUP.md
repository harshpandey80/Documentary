# Setup & Architecture Guide (`SETUP.md`)

This document details the toolchain, setup instructions, architectural decisions, and safety systems for the **Autonomous Documentary Video Production Studio** (`DocStudio`).

---

## 1. Tool Evaluation & Architectural Rationale

### A. Dual-Engine Narration System (Edge-TTS + Kokoro-ONNX Failover)
*   **Primary (Edge-TTS)**: High-retention Microsoft Neural documentary voices (`en-US-ChristopherNeural`, `en-GB-RyanNeural`, `en-US-GuyNeural`). Generates millisecond-accurate word-boundary timestamps natively.
*   **Performance Narration (SSML)**: Script scenes are encoded with W3C SSML prosody (`rate`, `pitch`, `break`, `emphasis`) to deliver dramatic variation rather than flat reading:
    *   *Dread / Ominous*: `rate="-12%" pitch="-4Hz"`
    *   *Twist / Reveal*: `rate="+5%" pitch="+2Hz"` with strong emphasis and deliberate silence preceding the reveal.
*   **Failover System (Kokoro-ONNX)**: Edge-TTS relies on cloud infrastructure. If a request times out, fails, or is rate-limited, DocStudio automatically fails over to the local, offline **Kokoro-82M ONNX** engine running directly on CPU without interrupting the production run.

### B. Licensed Music & SFX Library with Beat-Aware Ducking
*   **Hardware Architecture Constraint**:
    *   Target Host: **HP Aero 13 (AMD Ryzen, 16GB RAM, Integrated Graphics)**.
    *   **AudioLDM Ruled Out**: Diffusion-based audio models require dedicated GPUs with 8GB+ VRAM. Running AudioLDM on CPU/integrated graphics causes memory exhaustion and excessive latencies.
*   **Curated Royalty-Free & Procedural Audio Sourcing**:
    *   DocStudio uses a self-hosted licensed audio bed library covering all 5 core documentary emotional categories:
        *   `ambient_tension.wav`: Dark C2/Eb2 minor chord with breathing LFO pulse.
        *   `ambient_reveal.wav`: Shimmering harmonic resonance bed for major twists.
        *   `ambient_somber.wav`: Deep, melancholic drone with sub-oscillator for somber reflections.
        *   `ambient_triumphant.wav`: Rising harmonic progressions for breakthroughs.
        *   `ambient_drone.wav`: Grounding 55Hz foundation sub-rumble.
    *   Full procedural SFX triggers: `whoosh.wav` (cuts), `deep_braam.wav` (impact reveals), `riser.wav` (cliffhangers), `impact_hit.wav` (stings).
    *   Supports external licensed tracks from **YouTube Audio Library** or **Pixabay Audio API** (`PIXABAY_API_KEY`) with the same beat-tagging system.
*   **Beat-Aware Dynamic Ducking**:
    *   Narration-critical lines automatically duck the music bed by **-22dB**.
    *   Pauses, scene transitions, and cliffhangers allow the music bed to swell by **+6dB**.
    *   400ms prior to major punch-zooms and reveals, a **Sound Vacuum** (complete negative-space audio dropout) is applied before an impact braam hits.

### C. Visual Cohesion Engine (Unified Color Grade & Texture)
*   To eliminate the visual clash between vintage monochrome archival photos, vibrant modern Pexels stock, and AI-generated stills, DocStudio applies a unified FFmpeg grading filter to all assets before editing:
    1.  **Framing Normalization**: Scale and center-crop to 1920x1080.
    2.  **Color Grade**: Crushed blacks, slight desaturation, and subtle teal/amber split-toning (`eq=contrast=1.06:brightness=-0.02:saturation=0.85,colorbalance=...`).
    3.  **Dynamic 35mm Film Grain**: Procedural temporal grain (`noise=alls=11:allf=t+u`).
    4.  **Cinematic Vignette**: Edge-darkening (`vignette=PI/4.5`) to keep viewer focus centered on the subtitle text.

### D. Multi-Source Visual Acquisition & Commercial License Whitelist
*   **Sourcing Hierarchy**:
    1.  **Tier 1**: Wikimedia Commons Public Domain & US National Archives API (100% CC0 / PD).
    2.  **Tier 2**: Pexels Stock Photo & Video API (Free Commercial & Derivative use).
    3.  **Tier 3**: **Google Gemini API Visual Generation** (`imagen-3.0-generate-002` / Gemini visual prompt synthesis via existing user API key). Replaces macOS-dependent Palmier Pro generative models.
    4.  **Tier 4**: Procedural Cinematic Documentary Graphic Slides (Guaranteed CC0 original).
*   **Zero Monetization Risk**:
    *   The B-roll engine verifies every item against an explicit whitelist of commercial-eligible licenses (`Public domain`, `CC0`, `CC-BY`, `Pexels`, `AI Generated - Commercial Terms Verified`).
    *   Any asset with `NonCommercial` (`CC-BY-NC`), `NoDerivatives` (`CC-BY-ND`), or missing metadata is **hard-rejected**.
    *   Every run writes `license_manifest.json` detailing source URLs, licenses, and attribution text.

### E. Beat-Aware Pacing (Intensity Scale 1–5)
*   Instead of arbitrary cuts every 3–5 seconds, cut timing maps directly to the scene's dramatic intensity:
    *   **Intensity 1 (Reflection)**: 5.5s – 8.0s hold
    *   **Intensity 2 (Exposition)**: 4.0s – 5.5s hold
    *   **Intensity 3 (Investigation)**: 2.8s – 3.8s cut
    *   **Intensity 4 (Escalation)**: 2.0s – 2.8s cut
    *   **Intensity 5 (Cold Hook / Climax)**: 1.2s – 2.0s rapid cut with punch zoom

### F. Broadcast Loudness Normalization (EBU R128)
*   The final audio track is passed through FFmpeg's two-pass `loudnorm` filter targeting:
    *   **Integrated Loudness**: `-14.0 LUFS` (YouTube / Bilibili standard)
    *   **True Peak**: `-1.0 dBTP`
    *   **Loudness Range (LRA)**: `7.0 LU`

### G. Retention QC & Distribution Packaging
*   Outputs `qc_report.md` auditing:
    *   First 8s cold hook commitment
    *   Retention dip risk timestamps (holds exceeding intensity limits or slow cadence)
    *   Caption sync drift
    *   Dead air incidents (>1.2s)
*   Outputs `distribution_meta.md` containing:
    *   3 curiosity-gap titles (Negative constraint, Declassified file, Fatal error)
    *   Thumbnail creative brief (focal point, contrast ratio, 2-3 word hook)
    *   Platform-specific SEO descriptions for YouTube and Bilibili.

### H. Timeline Integration & Validated FCPXML Export (@chatoctopus/timeline)
*   **Primary Engine**: Programmatic FFmpeg filtergraph remains 100% the primary, authoritative, headless production path.
*   **Palmier Pro / NLE Interoperability**: Retains full timeline export for manual touch-up. Exported files can be loaded into Palmier Pro (on Mac), DaVinci Resolve, or Premiere Pro.
*   **FCPXML 1.8 Reliability**: Replaces hand-rolled XML strings with the vetted `@chatoctopus/timeline` engine.
    *   Uses frame-accurate rational time math (e.g. `0s`, `36/30s`) to eliminate floating-point drift.
    *   Every generated `timeline.fcpxml` must pass `@chatoctopus/timeline`'s `validate` command before being committed to the run folder.
    *   If validation fails, the export halts and the error is written to `PROGRESS.md`.

### I. Live Progress Tracking (`PROGRESS.md` & CLI)
*   **Root `PROGRESS.md`**: Automatically overwritten after each stage transition:
    *   Active run ID, topic, start time, elapsed duration, overall status.
    *   Verification checklist of the 6 core checkpoints (`01_script.json` through `06_final_render.mp4`).
    *   Stage-by-stage status table (`done` / `in progress` / `failed + reason`).
    *   Full exception stack trace and step name logged on any failure.
*   **Per-Run State Ledger**: `workspace/runs/<run_id>/run_state.json` stores machine-readable timing and completion status.
*   **CLI Commands**:
    *   `uv run python -m docstudio status [--run-id <id>]`: Print active or specified run progress.
    *   `uv run python -m docstudio status --all`: Tabular report of all runs, completion states, and render durations.

### J. Security Constraint — Dependency Vetting Protocol
Before installing any new package or repository:
1.  **Singular Maintainer Audit**: Verify real commit history and absence of cloned/star-farmed repository networks.
2.  **Source Code Inspection**: Inspect all TypeScript/JavaScript/Python code touching disk, network, or subprocesses.
3.  **Explicit User Flagging**: Flag low-provenance or generic packages to the user before installation.
4.  **Hard Blacklist**: Permanent rejection of repos matching the "OpenMontage" mass-duplicated pattern.
*   *Vetted Clearance Record*: `@chatoctopus/timeline@0.3.0` vetted (Author: `moinism`, single dependency `fast-xml-parser: ^5.2.0`, pure in-memory AST calculations, no telemetry or shell execution).

### K. Architecture Sanity Check & State Isolation
*   **Run-Scoped Isolation**: Every run is fully self-contained in `workspace/runs/<run_id>/`.
*   **Immutable State Handoff**: Each stage consumes explicit prior checkpoint files and produces immutable output.
*   **Decision Ledger (`DECISIONS.md`)**: Documents runtime choices (voice selection, failover triggers, B-roll sourcing, budget compliance).
*   **Cost Tracking**: Enforces zero-cost targets and audits API usage.

---

## 2. Prerequisites & Environment

1. **FFmpeg**: Version 9.0.1 or higher (with `libass` and `freetype` enabled).
2. **Python**: Python 3.10+ managed cleanly with `uv`.
3. **API Keys**:
   - `GEMINI_API_KEY`: For scriptwriting, storyboard cues, and image generation.
   - `PEXELS_API_KEY` *(Optional)*: For stock footage.
   - `PIXABAY_API_KEY` *(Optional)*: For music/audio retrieval.

---

## 3. Quickstart & Verification

```powershell
# Sync virtual environment
uv sync

# Run the end-to-end documentary pipeline
uv run python -m docstudio run --topic "The Mysterious Vanishing of Flight 19"
```
