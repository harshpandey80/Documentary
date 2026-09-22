# Remote Creative Director Architecture Specification

## 1. Executive Overview
The **Remote Creative Director** architecture establishes a fundamental separation of concerns for the `docstudio` autonomous video engine:

$$\text{Remote AI} = \textbf{Thinking \& Directing} \quad\longleftrightarrow\quad \text{Local DocStudio} = \textbf{Execution, Validation \& Assembly}$$

### The Problem Solved
Prior iterations attempted to decide what visual to display using deterministic local regexes and heuristic keyword matchers (e.g. matching numbers to show charts, dates to show archives, or fixed cut intervals every 2.4s). This created repetitive, unmotivated visuals and slideshow-like edits.

### The Solution
Visual direction requires **holistic story comprehension**:
- What does the viewer already know?
- What is the key takeaway of this specific moment?
- What visual medium communicates that concept with highest clarity?
- Is visual continuity maintained across characters, locations, and objects?

The Remote Creative Director receives the **entire documentary context** and emits a strictly validated **Shot Manifest**. DocStudio validates the manifest and delegates each shot to specialized execution tools (browser-based generation, route maps, data graphics, evidence documents, or curated stock).

---

## 2. Architecture & Pipeline Flow

```
+-------------------------------------------------------------------------------+
|                           REMOTE CREATIVE DIRECTOR                            |
|                                                                               |
|   Topic + Full Research + Verified Claims + Story Beats + Narration Timings  |
|                                     |                                         |
|                 PASS 1: Storyboard & Narrative Purpose                        |
|                                     |                                         |
|                  PASS 2: Cinematic Prompt Engineering                         |
|                                     |                                         |
|                  Self-Critique & Continuity Verification                      |
+-------------------------------------+-----------------------------------------+
                                      | Emits
                                      v
+-------------------------------------------------------------------------------+
|                     SHOT MANIFEST (Central Contract)                          |
|                                                                               |
|  - Scene & Shot hierarchy        - Exact start/end/duration timestamps        |
|  - Explicit Visual Purpose       - Mandatory Visual Reason                    |
|  - Assigned Visual Type          - Source Strategy (Generate / Code / Stock)  |
+-------------------------------------+-----------------------------------------+
                                      | Validated by ShotManifestValidator
                                      v
+-------------------------------------------------------------------------------+
|                            LOCAL DOCSTUDIO ENGINE                             |
|                                                                               |
|       Dispatches each shot to its appropriate specialized execution tool:     |
|                                                                               |
|   * AI Video / Image  --> Browser Visual Provider (Google Flow / Web UI)      |
|   * Route Maps        --> MapAnimationEngine (OpenStreetMap / CartoDB)       |
|   * Data Charts       --> NumberGraphicsEngine (Procedural PIL/Matplotlib)    |
|   * Primary Evidence  --> VoxMotionGraphicsEngine (Declassified Dossier)      |
|   * Historical Stock  --> BRollMatcher (Semantic asset ranking)               |
+-------------------------------------+-----------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
|                    MULTI-LAYER ASSEMBLY & QC AUDIT                            |
|                                                                               |
|   - FFmpeg 60fps / 30fps hardware-accelerated Ken Burns & transitions        |
|   - 4-layer audio mastering (dialogue 1.0, music -24dB ducking, EBU R128)     |
|   - 10-point automated quality audit & FCPXML / DaVinci Resolve export        |
+-------------------------------------------------------------------------------+
```

---

## 3. Visual Decision Hierarchy
When deciding the visual type for any story beat, the Remote Creative Director evaluates options in strict priority order:

1. **AUTHENTIC EVIDENCE**: Declassified documents, court filings, official telegrams, authentic logs.
2. **REAL ARCHIVAL MATERIAL**: Historical photographs, authenticated period film, real newsreels.
3. **DATA / MAP / TIMELINE / DIAGRAM**: Animated route maps for geography, kinetic charts for statistics, chronological timelines for complex sequences.
4. **SCREEN / UI RECREATION**: Radar sweeps, sonar displays, cockpit HUD telemetry, digital communication logs.
5. **CINEMATIC RECONSTRUCTION**: Grounded historical dramatic recreation of actions with physical realism.
6. **AI IMAGE -> VIDEO**: High-resolution photorealistic still brought to life with 3D camera parallax/motion.
7. **AI IMAGE**: Photorealistic still frame with hardware-accelerated Ken Burns punch-zoom.
8. **STOCK / B-ROLL**: Curated high-production atmospheric environments (ocean swells, storm clouds).
9. **ABSTRACT / ATMOSPHERIC**: Minimal visual texture used only to reset visual pacing.

> [!IMPORTANT]
> **No AI Video for Data or Geography**: If narration says *"37 kilometers off the coast"*, the system mandates a **MAP**, not generic footage of ocean waves. If narration quotes a financial figure, the system mandates a **DATA CHART**, not corporate office stock.

---

## 4. Visual Purpose Vocabulary
Every single shot in the Shot Manifest **must** declare its primary narrative purpose from this closed vocabulary:

| Purpose Key | Directorial Intention |
| :--- | :--- |
| `ESTABLISH` | Grounds the viewer in the time period, environment, or physical setting. |
| `INTRODUCE_PERSON` | Establishes an individual's identity, role, and historical significance. |
| `INTRODUCE_LOCATION`| Shows geographic context and strategic relevance. |
| `EXPLAIN_GEOGRAPHY` | Visualizes distances, travel paths, borders, or territorial positions via maps. |
| `EXPLAIN_SEQUENCE` | Breaks down a step-by-step causal chain of events. |
| `SHOW_SCALE` | Demonstrates the physical magnitude, human volume, or financial proportion. |
| `SHOW_EVIDENCE` | Presents primary proof (unsealed files, signed orders, forensic analysis). |
| `SHOW_CONTRADICTION`| Highlights conflicting testimony or anomalies between official reports and reality. |
| `SHOW_STATISTICS` | Communicates critical numbers, rates of change, or comparative data. |
| `RECONSTRUCT_EVENT` | Reconstructs an unseen crisis, action, or physical moment where motion matters. |
| `CREATE_TENSION` | Uses tight framing, impending danger, or ominous pacing to escalate stakes. |
| `EMPHASIZE_REVEAL` | Punctuates a key turning point or previously concealed fact. |
| `CONCLUDE` | Summarizes narrative impact and drives viewer curiosity into the CTA. |

---

## 5. Central Contract: Shot Manifest JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "DocStudioShotManifest",
  "type": "object",
  "required": [
    "documentary_id",
    "version",
    "topic",
    "aspect_ratio",
    "total_duration",
    "director_notes",
    "scenes"
  ],
  "properties": {
    "documentary_id": { "type": "string" },
    "version": { "type": "integer", "default": 1 },
    "topic": { "type": "string" },
    "aspect_ratio": { "type": "string", "enum": ["16:9", "9:16"] },
    "total_duration": { "type": "number" },
    "director_notes": { "type": "string" },
    "continuity_bible": {
      "type": "object",
      "properties": {
        "characters": { "type": "array", "items": { "type": "object" } },
        "locations": { "type": "array", "items": { "type": "object" } },
        "key_objects": { "type": "array", "items": { "type": "object" } }
      }
    },
    "scenes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "scene_id",
          "story_beat",
          "viewer_takeaway",
          "narration_range",
          "shots"
        ],
        "properties": {
          "scene_id": { "type": "string" },
          "story_beat": { "type": "string" },
          "viewer_takeaway": { "type": "string" },
          "narration_range": {
            "type": "object",
            "required": ["start", "end"],
            "properties": {
              "start": { "type": "number" },
              "end": { "type": "number" }
            }
          },
          "shots": {
            "type": "array",
            "items": {
              "type": "object",
              "required": [
                "shot_id",
                "start",
                "end",
                "duration",
                "purpose",
                "visual_type",
                "visual_reason",
                "source_strategy"
              ],
              "properties": {
                "shot_id": { "type": "string" },
                "start": { "type": "number" },
                "end": { "type": "number" },
                "duration": { "type": "number" },
                "purpose": { "type": "string" },
                "visual_type": { "type": "string" },
                "visual_reason": { "type": "string" },
                "source_strategy": {
                  "type": "string",
                  "enum": [
                    "GENERATE_AI_VIDEO",
                    "GENERATE_AI_IMAGE",
                    "PROCEDURAL_MAP",
                    "PROCEDURAL_CHART",
                    "PROCEDURAL_DOCUMENT",
                    "RETRIEVE_ARCHIVE_STOCK"
                  ]
                },
                "prompt": { "type": "string" },
                "motion": { "type": "string" },
                "camera": { "type": "string" },
                "composition": { "type": "string" },
                "evidence_claims": {
                  "type": "array",
                  "items": { "type": "string" }
                },
                "transition_in": { "type": "string" },
                "transition_out": { "type": "string" },
                "execution_metadata": { "type": "object" }
              }
            }
          }
        }
      }
    }
  }
}
```

---

## 6. Browser Visual Provider Abstraction

### Design Principle
The browser automation worker is **NOT** the director. It receives already-decided generation requests and handles browser interaction, queueing, asset download, and status verification.

### Interface: `BrowserVisualProvider`
```python
class BrowserVisualProvider(ABC):
    @abstractmethod
    def generate_image(self, request: BrowserGenerationRequest) -> BrowserGenerationResult:
        """Generates still imagery via web creative platform."""
        pass

    @abstractmethod
    def generate_video(self, request: BrowserGenerationRequest) -> BrowserGenerationResult:
        """Generates video clip via web creative platform."""
        pass

    @abstractmethod
    def check_status(self, task_id: str) -> BrowserTaskStatus:
        """Checks status of long-running web generation task."""
        pass

    @abstractmethod
    def download_asset(self, download_url: str, target_path: Path) -> Path:
        """Downloads generated asset into local job visuals directory."""
        pass
```

### Safety & Resilience
- **No brittle pixel coordinate clicks**: Uses semantic DOM/accessibility selectors.
- **Resource Queue**: Generation tasks run through `BrowserGenerationQueue` with max concurrency 1-2 to protect 16 GB RAM and prevent browser process exhaustion.
- **Screenshot Diagnostics**: On error, captures full-page screenshot into `jobs/<ID>/temp_render/browser_error_<task>.png`.
- **Automatic Degradation**: If browser automation fails after configured retries, falls back automatically to:
  $$\text{Browser Video} \longrightarrow \text{Pollinations / Cloud API} \longrightarrow \text{2.5D Parallax} \longrightarrow \text{Ken Burns Still}$$

---

## 7. Two-Pass Directing Process

1. **Pass 1 — Storyboard & Visual Strategy**:
   - The remote LLM evaluates the entire story context: research dossier, claims, story beats, and narration timing.
   - It partitions each scene into shots, assigns `purpose`, `visual_type`, `visual_reason`, and `source_strategy`.
   - It performs **self-critique**: checks for visual repetition, verifies that maps are used for geography, documents for quotes/evidence, and AI video is reserved only for scenes where physical motion is essential.
2. **Pass 2 — Prompt Engineering**:
   - Once Pass 1 is validated, Pass 2 synthesizes granular photorealistic generation prompts adhering to the **Continuity Bible** (lighting, camera lenses, period attire, architectural consistency).

---

## 8. File Structure & Modifications

### New Modules Created in Phase 1 & Phase 2
```
docstudio/
├── remote_creative_director/
│   ├── __init__.py
│   ├── director.py             # Executive Remote Creative Director & AI recovery
│   ├── prompt_builder.py       # Two-pass LLM prompts
│   ├── manifest_schema.py      # Strict dataclasses & JSON schema (Truth, Cost, Compute)
│   ├── validator.py            # ShotManifestValidator (Structured error codes & coverage)
│   ├── visual_registry.py      # Canonical 21 Visual Types & Semantic Fallback chains
│   ├── provider_registry.py    # Central ExecutionProvider ABC & ProviderResolver
│   ├── cache.py                # Deterministic SHA-256 asset cache & hit/miss index
│   ├── context_builder.py      # Whole-story context assembly
│   ├── browser_bridge.py       # Bridge to browser workers
│   ├── provider_router.py      # Execution tool router with caching
│   ├── run_reporter.py         # Production Run Reporter (run_report.json / RUN_SUMMARY.md)
│   └── retry.py                # Self-healing manifest retry
│
└── visual_providers/
    └── browser/
        ├── __init__.py
        ├── base_provider.py    # Abstract BrowserVisualProvider interface
        ├── queue.py            # Concurrency-limited generation queue
        └── web_generation_provider.py  # Playwright/Web generator implementation
```

### Existing Modules Modified as Execution Tools
- [`docstudio/autonomous_pipeline.py`](file:///c:/Users/Harsh%20Pandey/OneDrive/Desktop/documentry-AI/docstudio/autonomous_pipeline.py): Stage 5 invokes `RemoteCreativeDirector` to emit `shot_manifest.json`. Stage 6 executes shots via the manifest router and generates `run_report.json`.
- [`docstudio/map_animation.py`](file:///c:/Users/Harsh%20Pandey/OneDrive/Desktop/documentry-AI/docstudio/map_animation.py): Executed when `visual_type == "MAP"`.
- [`docstudio/number_graphics.py`](file:///c:/Users/Harsh%20Pandey/OneDrive/Desktop/documentry-AI/docstudio/number_graphics.py): Executed when `visual_type == "DATA_CHART"`.
- [`docstudio/vox_motion_graphics.py`](file:///c:/Users/Harsh%20Pandey/OneDrive/Desktop/documentry-AI/docstudio/vox_motion_graphics.py): Executed when `visual_type == "AUTHENTIC_EVIDENCE"`.
- [`docstudio/server.py`](file:///c:/Users/Harsh%20Pandey/OneDrive/Desktop/documentry-AI/docstudio/server.py): Adds manifest and visual debug endpoints.

---

## 9. Phase 2 Hardened Provider & Fallback Architecture

### Central Provider Resolution
Visual types are resolved exclusively through `ProviderResolver.resolve(visual_type)`:
```
visual_type
    │
    ▼
[ProviderResolver] ──▶ Matches registered ExecutionProvider
    │
    ▼ (If unavailable / execution failure)
[Semantic Fallback Chain] ──▶ Cascades through domain-appropriate alternatives
```

### Truth Categories & Documentary Safety
Every shot directive carries a mandatory `TruthCategory`:
- `DOCUMENTARY_EVIDENCE`: Primary source document, unsealed file, court record.
- `ARCHIVAL`: Authenticated period photograph or authentic newsreel footage.
- `CONTEMPORARY`: Verified modern satellite imagery or actual location footage.
- `RECONSTRUCTION`: Grounded historical reenactment with physical realism.
- `AI_GENERATED`: Synthetically generated visual approximation.
- `CONCEPTUAL`: Abstract representation or visual metaphor.
- `ILLUSTRATIVE`: Infographic, chart, or explanatory diagram.

Under no circumstances may an authentic archival claim be visually fulfilled by an unflagged AI hallucination.

