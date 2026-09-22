# Phase 2 — Production Hardening Engineering Report

## 1. Codebase Inspection & Baseline Analysis

Before making any modifications, the entire documentary studio pipeline and initial vertical slice were comprehensively inspected:
- **`docstudio/remote_creative_director/`**: Contains `director.py`, `context_builder.py`, `prompt_builder.py`, `validator.py`, and `manifest_schema.py`. The initial implementation established the two-pass directorial model and vertical slice execution.
- **Weaknesses Identified in Baseline:**
  1. **Contract Under-Specification**: `ShotDirective` lacked explicit truth categorization (`TruthCategory`), compute/cost classification, and execution parameters.
  2. **Decentralized Provider Resolution**: Visual types were mapped ad-hoc in router and broll logic without a single authoritative provider registry or strict separation between `SUPPORTED_NOW` and `PLANNED` visual capabilities.
  3. **Binary Validation Feedback**: The initial validator returned boolean `(is_valid, errors)` where errors were unindexed string messages. It lacked machine-readable error codes, severity levels (`ERROR`, `WARNING`, `INFO`), timeline coverage analysis, and shot repetition metrics.
  4. **Lack of Deterministic Caching**: Repeated identical shot directives triggered duplicate asset generation or stock queries, wasting time and external API quotas.
  5. **Brittle AI Response Parsing**: If the LLM returned conversational preambles (e.g., `"Here is your JSON:"`) or markdown wrappers, parsing could fail.
  6. **Lack of Grounded Fallback**: If remote LLM providers hit daily rate limits (e.g. Gemini 429 quota exhaustion or OpenRouter 402), the pipeline halted rather than using a grounded, narrative-aware fallback manifest.
  7. **Unsafe Fallback Substitutions**: If a specialized visual failed (e.g. animated map), systems would risk substituting unrelated generic stock footage instead of semantically appropriate fallbacks.

---

## 2. Architectural Decisions & Key Changes

### Principle: Remote AI = Creative Brain | Local DocStudio = Execution & Validation Engine
The Remote AI decides *what* to see, *why* to see it, *when* to show it, and *what medium* best communicates the truth. The local engine enforces contracts, resolves execution providers, caches assets, manages fallbacks, and assembles the timeline.

### Major Changes Implemented:
1. **Manifest Contract Hardening (`manifest_schema.py`)**:
   - Introduced `TruthCategory` enum (`DOCUMENTARY_EVIDENCE`, `ARCHIVAL`, `CONTEMPORARY`, `RECONSTRUCTION`, `AI_GENERATED`, `CONCEPTUAL`, `ILLUSTRATIVE`).
   - Introduced `CostClass` (`LOW`, `MEDIUM`, `HIGH`) and `ComputeClass` (`LOCAL`, `BROWSER`, `REMOTE`).
   - Added `ExecutionDirective` for explicit tool-dispatch parameters.
   - Added `request_fingerprint` property computing a deterministic SHA-256 hash of all shot parameters.
2. **Centralized Visual Type Registry (`visual_registry.py`)**:
   - Defined 21 canonical visual types partitioned into `SUPPORTED_NOW` vs. `PLANNED`.
   - Defined strict semantic fallback chains (e.g., `MAP` → `TIMELINE` → `DOCUMENT` → `EVIDENCE_DOSSIER`; never generic stock).
3. **Centralized Provider Registry (`provider_registry.py`)**:
   - Implemented `ExecutionProvider` abstract base class and 6 concrete providers: `MapExecutionProvider`, `ChartExecutionProvider`, `EvidenceExecutionProvider`, `BrowserVisualExecutionProvider`, `ProceduralMotionExecutionProvider`, and `StockExecutionProvider`.
   - Implemented `ProviderResolver` with cascading fallback resolution.
4. **Deterministic Asset Caching (`cache.py`)**:
   - Persistent JSON metadata index with SHA-256 fingerprint matching.
   - Tracks `cache_hits` and `cache_misses` per production run.
5. **Structured Validation Engine (`validator.py`)**:
   - Emits structured `ValidationResult` with `ValidationErrorItem` entries, machine-readable error codes (`TIMING_OVERLAP`, `NEGATIVE_OR_ZERO_DURATION`, `TIMING_GAP`, `DUPLICATE_SHOT_ID`, `MISSING_PURPOSE`, `HIGH_VISUAL_REPETITION`, etc.), and severities (`ERROR`, `WARNING`, `INFO`).
   - Implemented `CoverageReport` measuring documentary timeline coverage and listing uncovered gaps.
   - Implemented visual diversity metrics to flag visual monotony.
6. **Resilient AI Parsing & Grounded Fallback (`director.py`)**:
   - Implemented `clean_and_parse_json()` stripping conversational prose and code blocks.
   - Implemented `_build_grounded_fallback_manifest()` to guarantee production never halts when LLM quotas are exhausted.
7. **Production Run Reporter (`run_reporter.py`)**:
   - Generates machine-readable `run_report.json` and formatted `RUN_SUMMARY.md`.

---

## 3. Manifest Schema & Validation Rules

### Schema Hierarchy
```text
ShotManifest
├── manifest_id: str
├── project_id: str
├── topic: str
├── total_duration: float
├── aspect_ratio: "16:9" | "9:16"
├── style_preset: str
├── visual_pace_target: float
├── continuity_bible: Dict[str, Any]
├── execution_strategy: Dict[str, Any]
└── scenes: List[SceneDirective]
    ├── scene_id: str
    ├── scene_index: int
    ├── narrative_goal: str
    ├── duration: float
    └── shots: List[ShotDirective]
        ├── shot_id: str
        ├── scene_id: str
        ├── purpose: VisualPurpose
        ├── visual_reason: str
        ├── visual_type: VisualType
        ├── duration: float
        ├── narration_range: NarrationRange (start_s, end_s, text)
        ├── source_strategy: SourceStrategy (type, query, evidence_ref, prompt)
        ├── truth_category: TruthCategory
        ├── execution: ExecutionDirective (provider, cost_class, compute_class, parameters)
        ├── composition: str
        ├── evidence_claims: List[str]
        └── request_fingerprint: str (SHA-256)
```

### Validation Rules Enforced
| Category | Rule Code | Severity | Description |
| :--- | :--- | :--- | :--- |
| **Timing** | `NEGATIVE_OR_ZERO_DURATION` | `ERROR` | Duration must be strictly > 0s. |
| **Timing** | `EXCESSIVE_DURATION` | `WARNING` | Shots held longer than 6.0s flagged for pacing. |
| **Timing** | `TIMING_OVERLAP` | `ERROR` | Sequential shots must not have overlapping time ranges. |
| **Timing** | `TIMING_GAP` | `WARNING` | Gaps > 0.5s between consecutive shots flagged. |
| **Timing** | `SCENE_DURATION_MISMATCH` | `WARNING` | Sum of shot durations deviates from scene duration. |
| **Timing** | `MANIFEST_DURATION_MISMATCH`| `WARNING` | Sum of scene durations deviates from total runtime. |
| **Identity** | `DUPLICATE_SHOT_ID` | `ERROR` | Every shot ID must be globally unique within the manifest. |
| **Semantics**| `MISSING_PURPOSE` | `ERROR` | Every shot must declare a valid narrative purpose. |
| **Semantics**| `MISSING_REASON` | `ERROR` | Every shot must state why the visual is shown now. |
| **Semantics**| `MISSING_VISUAL_TYPE` | `ERROR` | Visual type must be declared and valid. |
| **Semantics**| `UNSUPPORTED_VISUAL_TYPE` | `ERROR` | Directs must only use currently executable visual types. |
| **Execution**| `UNSUPPORTED_PROVIDER` | `ERROR` | Execution provider must be registered in the provider registry. |
| **Diversity**| `HIGH_VISUAL_REPETITION` | `WARNING` | Single visual type exceeding 60% of total runtime flagged. |
| **Truth** | `MISLABELED_TRUTH_CATEGORY`| `WARNING` | Historical claims must declare appropriate evidence/archival tags. |

---

## 4. Centralized Provider Registry & Semantic Fallback Matrix

The `ProviderResolver` matches each `VisualType` to its registered execution provider. If the primary provider is unavailable or fails, it cascades through semantic fallbacks:

```text
MAP / MAP_ANIMATION
  ↓ fallback
TIMELINE
  ↓ fallback
DOCUMENT / ARCHIVAL_FOOTAGE
  ↓ fallback
AUTHENTIC_EVIDENCE / PROCEDURAL_MOTION

DATA_CHART / CHART
  ↓ fallback
INFOGRAPHIC / KINETIC_TYPOGRAPHY
  ↓ fallback
DOCUMENT / PROCEDURAL_MOTION

AI_VIDEO / AI_IMAGE
  ↓ fallback
BROWSER_GENERATED_VISUAL
  ↓ fallback
ARCHIVAL_FOOTAGE / PHOTOGRAPH
  ↓ fallback
PROCEDURAL_MOTION
```

---

## 5. Asset Caching & Request Fingerprinting

Every shot generates a deterministic SHA-256 fingerprint based on:
```python
fingerprint = hashlib.sha256(
    f"{topic}|{scene_id}|{shot_id}|{visual_type}|{prompt}|{provider}|{json_params}".encode('utf-8')
).hexdigest()[:16]
```
The `AssetCacheManager` stores cached assets in `jobs/<job_id>/asset_cache/` indexed by `cache_index.json`. On cache hit, asset generation is bypassed entirely.

---

## 6. Test Suite & Verification Results

### Summary: 154 / 154 Tests Passed (0 Failures)
All automated unit and regression tests pass in 15.09 seconds.

| Test File | Test Count | Status | Description |
| :--- | :--- | :--- | :--- |
| `tests/test_adversarial_manifests.py` | 7 | **PASS** | Malformed manifests, negative durations, broken ranges, duplicate IDs, unsupported providers, truth mislabeling, recovery from raw prose. |
| `tests/test_golden_scenarios.py` | 7 | **PASS** | Validates History, Science, Biography, Geography, Economics, Investigation, and Conceptual manifests. |
| `tests/test_visual_registry_and_cache.py` | 5 | **PASS** | Visual type registry, semantic fallback chains, provider resolver, deterministic fingerprinting, cache hits/misses. |
| `tests/test_remote_creative_director.py` | 6 | **PASS** | Context builder, prompt builder, director initialization, schema parsing. |
| `tests/test_claims_ledger.py` | 6 | **PASS** | Truth claims, evidence verification, citation tracking. |
| `tests/test_no_hardcoded_topics.py` | 1 | **PASS** | Scans source code to prevent hardcoded topic leaks (Rule 5 compliance). |
| Existing Engine Tests (Audio, Video, Map, Charts, Server) | 122 | **PASS** | Complete regression verification. |

### 10-Scenario Documentary Domain Benchmark
All 10 documentary domain scenarios were tested via `scratch/test_10_scenarios.py`:
- **Scenario 1 (History)**: *The Lost Amber Room of Saint Petersburg* — **PASS** (0 errors)
- **Scenario 2 (Science)**: *The James Webb Cosmic Dawn Discoveries* — **PASS** (0 errors)
- **Scenario 3 (Technology)**: *The Silicon Valley Microchip Revolution* — **PASS** (0 errors)
- **Scenario 4 (Geography)**: *The Vanishing Aral Sea* — **PASS** (0 errors)
- **Scenario 5 (Economics)**: *Black Tuesday: The 1929 Wall Street Crash* — **PASS** (0 errors)
- **Scenario 6 (Biography)**: *Marie Curie: The Extraction of Pure Radium* — **PASS** (0 errors)
- **Scenario 7 (Culture)**: *The Rosetta Stone: Cracking the Sacred Glyphs* — **PASS** (0 errors)
- **Scenario 8 (Environment)**: *Chernobyl 1986: The Exclusion Zone and Reactor No. 4* — **PASS** (0 errors)
- **Scenario 9 (Investigation)**: *The Mary Celeste: The Unsolved Atlantic Abandonment* — **PASS** (0 errors)
- **Scenario 10 (Architecture)**: *The Colosseum Hypogeum: Ancient Roman Staging* — **PASS** (0 errors)

---

## 7. Known Limitations

1. **Third-Party LLM Free-Tier Rate Limits**: Free tier Gemini keys have a quota limit of 20 requests/day. While the director handles this via the grounded fallback manifest, a production deployment should configure paid tier keys or dedicated self-hosted endpoints.
2. **Browser Visual Generation Latency**: Generating video via browser UI automation (e.g. Flow/Web generators) requires 30–60s per clip. The `BrowserGenerationQueue` limits concurrency to 1–2 to protect host RAM.
3. **Historical Archive Public Domain APIs**: Archival search currently falls back to Wikimedia Commons and Pexels. Full NARA (National Archives) integration is targeted for Phase 3.

---

## 8. Recommended Phase 3 Milestones

1. **Interactive Visual Director UI in Studio Frontend**: Provide an interactive timeline UI where users can view and tweak the shot manifest before rendering.
2. **Full NARA & Europeana API Integration**: Add specialized forensic archival providers for deep historical investigations.
3. **Automated Multi-Pass Prompt Refinement**: Use a fast local vision model to inspect generated images/videos against the Continuity Bible and trigger targeted re-generations.
