# Architecture Migration: DocStudio Autonomous Documentary Production System

## Executive Overview
This document maps the evolution of the `docstudio` documentary pipeline from a developer-driven/assisted system into a genuinely autonomous, production-grade documentary generation engine. 

**Core Directive**: Preserve and build upon existing functioning modules (FFmpeg video assembler, Edge-TTS, ClaimsLedger, Code2Video, Vox motion graphics, multi-track audio mixing, and FCPXML timeline). Do NOT rebuild from scratch. Remove Antigravity as a runtime dependency. The application itself (Frontend + Backend Jobs) must orchestrate the entire documentary lifecycle.

---

## Component Architecture Migration Table

| Current Component | Purpose | Current Limitation | Target Component | Reuse / Modify / New | Dependencies | Risk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`docstudio/server.py`** | FastAPI REST & static server for web studio UI | Opaque background task; no persistent job model (`jobs/JOB_ID/...`); no multi-stage granular progress or per-stage retry. | **`docstudio/server.py`** & **`docstudio/job_manager.py`** | **MODIFY** (extend existing routes, add `/api/documentary/generate`, job status polling, retry endpoints) | `fastapi`, `uvicorn`, `pydantic` | Low: additive API routes maintain backward compatibility with studio frontend. |
| **`docstudio/progress_tracker.py`** | Logs stage progress to `run_state.json` and `PROGRESS.md` | Single linear progress dict; does not store granular intermediate artifacts (`research.json`, `story.json`, `storyboard.json`, etc.). | **`docstudio/job_manager.py`** | **NEW / EXTEND** (manages `jobs/JOB_ID/status.json`, artifact caching, stage isolation, checkpointing) | Python `json`, `pathlib` | Low: replaces flat state with structured disk-backed job directories. |
| *(None - New Stage)* | Deep topic research & primary source gathering | Previously LLM was prompted blindly with "write a script"; no structured entity/source/timeline extraction. | **`docstudio/research_engine.py`** | **NEW** (extracts entities, events, primary/secondary sources, timeline, statistics, conflicting accounts into `research.json`) | `llm_chain.py`, `re`, `urllib` | Medium: prompt engineering must yield structured, non-hallucinated JSON. |
| **`docstudio/claims_ledger.py`** | Fact verification gate matching spoken numbers against `claims.csv` | Hardcoded `claims.csv` root file; crashed on new topics with unverified numbers; no source provenance mapping for arbitrary statements. | **`docstudio/claims_ledger.py`** | **MODIFY** (auto-ingests claims from `research.json` into job-specific `claims.json`; maps claims to paragraph and shot IDs; handles uncertainty) | Python `csv`, `json`, `re` | Low: existing number regex and verification logic is battle-tested. |
| *(None - New Stage)* | Story architecture & narrative structure modeling | Scripts jumped straight from topic prompt to 6-act scenes; forced generic structure without answering "What is the viewer learning?". | **`docstudio/story_engine.py`** | **NEW** (analyzes researched evidence to produce `story.json`: central question, stakes, chronology, discoveries, turning points, reveals) | `llm_chain.py` | Low: pure structured reasoning output feeding into scriptwriting. |
| **`docstudio/scriptwriter.py`** | Generates documentary script with acts, scenes, and SSML | Prompts LLM for script without grounding in verified claims; output scenes have 1 visual per paragraph. | **`docstudio/scriptwriter.py`** | **MODIFY** (generates `narration.json` strictly grounded in `claims.json` and `story.json`; assigns claim IDs to every paragraph; avoids generic AI fluff) | `llm_chain.py`, `docstudio/config.py` | Medium: prompt adjustments must maintain high retention and beat intensity while adhering strictly to verified claims. |
| **`docstudio/vimax_director.py`** | Classifies scene archetypes and defines visual continuity tokens | Only operates on high-level scenes; does not generate shot-by-shot storyboards (1 visual per scene). | **`docstudio/visual_director/`** (`director.py`, `storyboard.py`, `classifier.py`) | **MODIFY / EXTEND** (evolves ViMax into a full Visual Director: scene -> multi-shot storyboard with semantic purpose, visual intent, layer timing) | `vimax_director.py`, `pacing.py` | Medium: must map narration sentences to multiple rapid shots (2.0s - 2.4s holds) before asset acquisition. |
| *(None - New Subsystem)* | Semantic Visual Decision & Evidence Engine | The system treated sentences as "find matching image/stock video" instead of choosing the optimal visual representation. | **`docstudio/evidence_engine.py`** & **`docstudio/visual_director/classifier.py`** | **NEW** (maps semantic info types: DATE->timeline, LOCATION->map, STAT->chart, CONTRADICTION->comparison, DOCUMENT->authentic highlight vs reconstruction) | Python standard library | Low: deterministic rule engine with semantic classification. |
| **`docstudio/code2video.py`**, **`map_animation.py`**, **`number_graphics.py`**, **`vox_motion_graphics.py`**, **`canva_templates.py`** | Procedural 2D/3D motion graphics rendering via Pillow + FFmpeg | High-quality graphics existed, but were sometimes called with generic placeholder data simply to fill time. | **`docstudio/motion_graphics/`** (`graphic_intent.py`, `dispatcher.py`) | **REUSE & EXTEND** (unifies existing generators under `GraphicIntent` schema: rejects graphics without verified data; routes to Map, Chart, Timeline, Dossier, etc.) | Existing PIL & FFmpeg renderers | Low: existing procedural code is preserved 100% and invoked only with verified data. |
| **`docstudio/broll_matcher.py`** | Multi-tier visual sourcing (Pexels, Pixabay, Wikimedia, LoC, Archive.org) | Acquires visuals per scene; needs to acquire per shot; needs to respect authentic vs reconstruction labeling. | **`docstudio/broll_matcher.py`** | **MODIFY** (accepts multi-shot visual intents; tags assets with `visual_status`: AUTHENTIC_SOURCE, RECONSTRUCTION, AI_GENERATED, STOCK, ARCHIVAL) | `requests`, `docstudio/config.py` | Medium: ensure cache reuse and rate-limit safety during multi-shot acquisition. |
| **`docstudio/ai_video_generator.py`** | Generates AI images (Pollinations Flux / Imagen 3) + Ken Burns pan/zoom | Monolithic file; ComfyUI is a dead stub; no clean provider interface for pluggable video models. | **`docstudio/ai_video/`** (`base_provider.py`, `providers/pollinations.py`, `providers/imagen.py`, `providers/ltx_stub.py`, `factory.py`) | **MODIFY / REFACTOR** (creates clean `AIVideoProvider` interface; lightweight defaults for HP Aero 13; no mandatory large local weights) | `requests`, `google-genai`, `ffmpeg` | Low: preserves Pollinations & Imagen 3 workflows while enabling modular provider extensions. |
| **`docstudio/relevance_scorer.py`** | Scores downloaded visual assets against search queries | CLIP model optional but torch not installed; token overlap fallback was basic string matching. | **`docstudio/relevance_scorer.py`** | **MODIFY** (enhances semantic scoring with entity, date, and location compatibility bonuses; penalizes duplicate assets; keeps heavy ML optional) | `re`, `math` | Low: purely algorithmic improvement without adding mandatory heavy dependencies. |
| **`docstudio/tts_engine.py`** | Speech synthesis via Edge-TTS and VoxCPM | Stripped SSML prosody with regex; did not support switching subtitle styles or semantic audio triggers. | **`docstudio/tts_engine.py`** | **MODIFY** (preserves Edge-TTS with fallback rate adjustments; retains word timestamps; feeds into multi-style caption engine) | `edge-tts`, `soundfile` | Low: Edge-TTS works reliably; preserve fallback. |
| **`docstudio/captions.py`** | Kinetic `.ass` subtitle generator | Only implemented Hormozi neon-pop style; unsuitable for subtle editorial long-form documentaries. | **`docstudio/captions.py`** | **MODIFY** (adds CINEMATIC, EDITORIAL, INVESTIGATIVE, MINIMAL styles alongside HORMOZI and SHORTS; respects aspect ratios) | Python string templating | Low: `.ass` styling templates are clean and self-contained. |
| **`docstudio/audio_mixer.py`** & **`cinematic_audio.py`** | 4-layer audio mixing, -24dB sidechain ducking, EBU R128 loudness | SFX triggered blindly on raw word occurrences rather than verified visual/story beats. | **`docstudio/cinematic_audio.py`** | **MODIFY** (connects SFX cues to shot visual events and story reveals; preserves -14.0 LUFS loudness mastering and smooth Hanning ducking) | `numpy`, `scipy`, `ffmpeg` | Low: core ducking and mastering math is preserved intact. |
| **`docstudio/video_assembler.py`** | Conforms clips, applies Ken Burns, concats via demuxer, color grades, and burns subtitles | Assembled video by whole scenes; needed multi-shot layering (PRIMARY_VISUAL, ANNOTATION, GRAPHIC). | **`docstudio/video_assembler.py`** | **MODIFY** (supports shot-level timeline assembly with multi-layer overlays, transition holding, and hardware-accelerated filters) | `ffmpeg`, `docstudio/ffmpeg_utils.py` | Medium: FFmpeg filter graphs must be robust and maintain exact 30.0 fps timing. |
| **`docstudio/qc_auditor.py`** | Audits hook score, retention dips, dead air | Did not verify provenance of evidence visuals, didn't flag fabricated documents, didn't detect static graphics without data. | **`docstudio/qc_auditor.py`** | **MODIFY** (expands QC gate: verifies visual coverage for every narration segment, checks claim provenance, checks graphic authenticity labels, tests duration) | Python `json`, `ffprobe` | Low: purely additive verification gate. |
| **`docstudio/timeline.py`** & **`scripts/generate_fcpxml.mjs`** | Multi-track timeline model and Apple Final Cut Pro XML 1.8 export | Exported basic clip timeline; Resolve MCP repository integration was absent. | **`docstudio/timeline.py`** & **`docstudio/resolve_bridge.py`** | **MODIFY / EXTEND** (preserves FCPXML 1.8 export as default; adds optional DaVinci Resolve MCP integration bridge if local server is running) | Node.js `@chatoctopus/timeline`, optional REST/MCP | Low: DaVinci remains completely optional; FFmpeg is always the guaranteed primary renderer. |
| **`docstudio/studio/`** (`index.html`, `app.js`, `style.css`) | Web UI for viewing and regenerating scenes | Progress bar was a simple percentage; did not display multi-stage job pipeline (Research -> Claims -> Story -> Shots -> Assets -> Graphics -> Audio -> Render -> QC). | **`docstudio/studio/`** | **MODIFY** (adds autonomous job pipeline stage stepper, real-time stage progress, job recovery, scene/shot inspector, and direct download/FCPXML export) | Vanilla HTML/CSS/JS | Low: no new frontend frameworks needed; enhances existing clean UI. |

---

## Data Flow: Current vs Target Architecture

### Current Flow
```
User (via CLI or simple Web form)
  └─► pipeline.py
        ├─► Stage 1: ScriptWriter (direct LLM prompt)
        │     └─► ClaimsLedger (verifies numbers against root claims.csv; halts if unverified)
        ├─► Stage 2: TTSEngine (Edge-TTS scene wavs + word timestamps)
        ├─► Stage 3: Captions (.ass generation)
        ├─► Stage 4: BRollMatcher (1 visual per scene via Pexels/Pixabay/Wikimedia/KenBurns)
        ├─► Stage 5: AudioMixer (Ducking & -14 LUFS mastering)
        ├─► Stage 6: VideoAssembler (FFmpeg concat, color grade, burn-in)
        ├─► Stage 7: QCAuditor & DistributionPackager
        └─► timeline.py (FCPXML export)
```

### Target Autonomous Production Architecture
```
User
  └─► Frontend UI / REST API (POST /api/documentary/generate)
        │ Topic (optional duration, format, aspect_ratio, style, research_depth)
        ▼
   JobManager (Persistent disk state: jobs/JOB_ID/...)
        │
        ├─► 1. Deep Research Engine ────────────► research.json (entities, events, timeline, sources, claims)
        │
        ├─► 2. Claims / Fact Verification ──────► claims.json (provenance validation, uncertainty tracking)
        │
        ├─► 3. Story Architecture Model ────────► story.json (central question, beats, discoveries, reveals)
        │
        ├─► 4. Autonomous Narration ────────────► narration.json (paragraphs mapped to claim IDs)
        │
        ├─► 5. Neural Voiceover & Timestamps ──► audio/ (scene wavs, word-level millisecond alignments)
        │
        ├─► 6. Visual Director & Storyboard ────► storyboard.json (scenes with multiple shots, semantic purpose)
        │
        ├─► 7. Evidence & Graphic Dispatcher ──► graphics.json (data-backed charts, maps, timelines, dossiers)
        │
        ├─► 8. Semantic Asset Sourcing ─────────► assets.json (multi-tier waterfall: archive, procedural, stock, AI)
        │
        ├─► 9. Sound Design & Audio Master ─────► audio_master.wav (dialogue, room tone, SFX cues, -24dB ducking)
        │
        ├─► 10. Multi-Layer Video Assembly ─────► temp_render/ & final_documentary.mp4 (FFmpeg conform, grade, subs)
        │
        ├─► 11. Automated Quality Control ──────► qc.json (fact provenance, visual coverage, duration, broadcast check)
        │
        └─► 12. Timeline & Distribution ────────► timeline.fcpxml & distribution_pack/ (metadata, thumbnails, chapters)
```

---

## Migration Principles & Verification Checkpoints

1. **Non-Destructive Evolution**:
   - Every existing module that currently works (`video_assembler.py`, `tts_engine.py`, `captions.py`, `code2video.py`, `vox_motion_graphics.py`, `map_animation.py`, `number_graphics.py`, `cinematic_audio.py`) is preserved, reused, and driven by the higher-level autonomous pipeline.
2. **Strict Hardware Compatibility (HP Aero 13)**:
   - Max 16 GB RAM and 512 GB SSD.
   - All AI video models are behind an abstract provider interface (`AIVideoProvider`).
   - Default generation uses cloud/API endpoints (Pollinations Flux, Google Imagen 3) or procedural graphics; heavy local 20GB+ diffusion weights are NOT installed or required.
   - Immediate garbage collection and cache size monitoring.
3. **Fact Provenance & Documentary Authenticity**:
   - Reconstructed documents and AI-generated scenes are explicitly labeled internally as `RECONSTRUCTION` or `AI_GENERATED`.
   - Never generate fake historical documents with fabricated text and present them as authentic evidence.
   - Fact verification enforces that every spoken statistic or date is tied to a researched claim.
4. **Independent Stage Resiliency**:
   - If Stage 10 (Rendering) fails, Stages 1–9 do NOT rerun.
   - If a single shot fails asset acquisition, only that shot is regenerated.
   - All stages read from and write to disk-backed job checkpoints (`jobs/JOB_ID/`).
