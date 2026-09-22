"""
Phase 6 – Visual Relevance Scorer
----------------------------------
Scores how well a visual asset matches the narration/keywords for a shot.
Features a CPU CLIP relevance gate (loads one model at a time, frees memory immediately)
with configurable threshold and high-precision semantic fallback.

API:
    scorer = RelevanceScorer(threshold=0.20)
    score = scorer.score(query="Roman legionnaires invading Britannia 43 AD", asset_path=Path("shot.jpg"))
    # Returns float 0.0-1.0; >= threshold to accept
"""

from __future__ import annotations

import gc
import os
import re
from pathlib import Path
from typing import List, Optional, Union

# Minimum relevance score to accept an asset; below this triggers next tier
DEFAULT_RELEVANCE_THRESHOLD = 0.20


def build_per_cut_query(narration: str, visual_prompt: str = "", keywords: Optional[List[str]] = None) -> str:
    """
    Builds a focused search/relevance query combining the Visual Cut text and spoken narration.
    """
    parts = []
    if visual_prompt and visual_prompt.strip():
        parts.append(visual_prompt.strip())
    if narration and narration.strip():
        # Extract main nouns and key verbs from narration
        clean_narr = re.sub(r"[^\w\s\-\d]", "", narration)
        parts.append(clean_narr.strip())
    if keywords:
        for kw in keywords:
            if kw and kw not in " ".join(parts):
                parts.append(kw.strip())
    return " ".join(parts)[:180].strip()


class RelevanceScorer:
    """
    CPU-friendly visual relevance scorer with CPU CLIP relevance gate.
    Loads vision/text embedding models on-demand one at a time and garbage-collects
    immediately after scoring to respect strict memory caps (<3GB free RAM).
    """

    def __init__(self, threshold: float = DEFAULT_RELEVANCE_THRESHOLD):
        self.threshold = threshold

    def score(
        self,
        keywords: Optional[List[str]] = None,
        asset_path: Optional[Path] = None,
        context: str = "",
        query: str = "",
    ) -> float:
        """
        Return relevance score 0.0–1.0.
        1.0  = perfect match
        0.0  = completely irrelevant
        """
        if not asset_path:
            return 0.0

        if not keywords and not query and not context:
            return 1.0

        full_query = query.strip() if query else ""
        if not full_query:
            kws = keywords or []
            full_query = build_per_cut_query(narration=context, visual_prompt="", keywords=kws)

        # 1. Try CPU CLIP Gate if available
        clip_score = self._score_cpu_clip(asset_path, full_query)
        if clip_score is not None:
            return clip_score

        # 2. Semantic token & metadata overlap fallback
        return self._score_text_only(keywords or [], asset_path, context, full_query)

    def is_relevant(
        self,
        keywords: Optional[List[str]] = None,
        asset_path: Optional[Path] = None,
        context: str = "",
        query: str = "",
    ) -> bool:
        return self.score(keywords, asset_path, context, query) >= self.threshold

    # ------------------------------------------------------------------
    # CPU CLIP Relevance Gate
    # ------------------------------------------------------------------

    def _score_cpu_clip(self, asset_path: Path, query_text: str) -> Optional[float]:
        """
        Runs CPU CLIP scoring if torch / open_clip or onnxruntime clip is present.
        Loads model, evaluates single image against query, and frees memory immediately.
        """
        if not query_text:
            return None

        # Check for open_clip or torch
        try:
            import torch
            import open_clip
            from PIL import Image

            # Load tiny ViT-B-32 or MobileCLIP on CPU
            model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k', device='cpu')
            tokenizer = open_clip.get_tokenizer('ViT-B-32')

            # Extract image frame if video
            img_path = self._extract_probe_frame(asset_path)
            if not img_path or not img_path.exists():
                return None

            image = preprocess(Image.open(img_path)).unsqueeze(0)
            text = tokenizer([query_text])

            with torch.no_grad():
                image_features = model.encode_image(image)
                text_features = model.encode_text(text)
                image_features /= image_features.norm(dim=-1, keepdim=True)
                text_features /= text_features.norm(dim=-1, keepdim=True)
                similarity = (image_features @ text_features.T).item()

            # Clean up immediately
            del model, preprocess, tokenizer, image, text, image_features, text_features
            gc.collect()

            # Normalize similarity (typically 0.15 - 0.35 for matching CLIP pairs) to 0.0 - 1.0
            norm_score = max(0.0, min(1.0, (similarity - 0.10) / 0.25))
            return float(norm_score)
        except Exception:
            # Fall back cleanly without crashing
            pass

        return None

    def _extract_probe_frame(self, asset_path: Path) -> Optional[Path]:
        """Extracts a middle probe frame from video or returns image path."""
        p = Path(asset_path)
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            return p

        probe_frame = p.parent / f"_probe_{p.stem}.jpg"
        if probe_frame.exists():
            return probe_frame

        try:
            import subprocess
            cmd = [
                "ffmpeg", "-y", "-nostats", "-loglevel", "error",
                "-ss", "1.0",
                "-i", str(p),
                "-vframes", "1",
                "-q:v", "3",
                str(probe_frame)
            ]
            subprocess.run(cmd, capture_output=True, timeout=5)
            if probe_frame.exists():
                return probe_frame
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # High-Precision Semantic Fallback
    # ------------------------------------------------------------------

    def _score_text_only(
        self, keywords: List[str], asset_path: Path, context: str, full_query: str = ""
    ) -> float:
        """
        High-precision keyword and semantic token overlap scorer.
        Compares query tokens against asset stem, path, and context.
        """
        stem = re.sub(r"[_\-\.]+", " ", asset_path.stem.lower())
        target_text = (stem + " " + context.lower()).strip()
        query_text = (full_query + " " + " ".join(keywords)).lower()

        # Tokenize target and query
        target_tokens = set(re.findall(r"\b\w{3,}\b", target_text))
        query_tokens = set(re.findall(r"\b\w{3,}\b", query_text))

        if not query_tokens:
            return 1.0

        overlap = len(target_tokens & query_tokens)
        score = overlap / len(query_tokens)

        # Boost for multi-word or exact keyphrase match
        for kw in keywords:
            if len(kw) >= 4 and kw.lower() in target_text:
                score = min(1.0, score + 0.35)
                break

        # Check for specific historical years or critical nouns (e.g. 1066, 1588, navy, armada)
        years_in_query = re.findall(r"\b(1\d{3}|20\d{2})\b", query_text)
        for y in years_in_query:
            if y in target_text:
                score = min(1.0, score + 0.40)
            elif any(c.isdigit() for c in target_text):
                # Penalty if target has different explicit year
                years_in_target = re.findall(r"\b(1\d{3}|20\d{2})\b", target_text)
                if years_in_target and y not in years_in_target:
                    score = max(0.0, score - 0.30)

        return min(1.0, round(score, 3))

    def rank_candidate_assets(
        self,
        candidate_paths: List[Path],
        query: str = "",
        context: str = "",
        keywords: Optional[List[str]] = None,
        entities: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        year: Optional[str] = None,
        recent_used_stems: Optional[List[str]] = None,
        last_selected_stem: Optional[str] = None,
        min_width: int = 1280,
        min_height: int = 720,
    ) -> List[Tuple[Path, float, Dict[str, Any]]]:
        """
        Multi-factor semantic asset ranker without heavy ML dependencies.
        Ranks candidates considering:
        - semantic relevance
        - date compatibility
        - entity compatibility
        - location compatibility
        - resolution adequacy
        - duplicate penalty
        - previous-shot similarity penalty
        """
        recent = set(s.lower() for s in (recent_used_stems or []))
        last_stem = (last_selected_stem or "").lower()
        entities = [e.lower() for e in (entities or []) if len(e) >= 3]
        locations = [loc.lower() for loc in (locations or []) if len(loc) >= 3]
        keywords = [k.lower() for k in (keywords or [])]

        ranked: List[Tuple[Path, float, Dict[str, Any]]] = []

        for p in candidate_paths:
            p = Path(p)
            stem = p.stem.lower()
            stem_words = set(re.findall(r"\b\w{3,}\b", stem))

            # 1. Base semantic score
            base_score = self.score(keywords=keywords, asset_path=p, context=context, query=query)

            # 2. Date compatibility
            date_boost = 0.0
            if year:
                clean_y = str(year).strip()
                if clean_y in stem:
                    date_boost = 0.25
                elif any(c.isdigit() for c in stem):
                    stem_years = re.findall(r"\b(1\d{3}|20\d{2})\b", stem)
                    if stem_years and clean_y not in stem_years:
                        date_boost = -0.20

            # 3. Entity compatibility
            entity_boost = 0.0
            for ent in entities:
                if ent in stem or any(w in stem_words for w in ent.split()):
                    entity_boost += 0.15

            # 4. Location compatibility
            location_boost = 0.0
            for loc in locations:
                if loc in stem or any(w in stem_words for w in loc.split()):
                    location_boost += 0.15

            # 5. Resolution adequacy (header probe only)
            resolution_factor = 0.0
            try:
                from PIL import Image
                if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                    with Image.open(p) as img:
                        w, h = img.size
                        if w >= min_width and h >= min_height:
                            resolution_factor = 0.10
                        elif w < 800 or h < 600:
                            resolution_factor = -0.15
            except Exception:
                pass

            # 6. Duplicate penalty
            duplicate_penalty = 0.0
            if stem in recent:
                duplicate_penalty = -0.40

            # 7. Previous shot similarity penalty
            similarity_penalty = 0.0
            if last_stem:
                if stem == last_stem:
                    similarity_penalty = -0.50
                else:
                    # Common prefix / suffix similarity check
                    last_words = set(re.findall(r"\b\w{3,}\b", last_stem))
                    if len(stem_words & last_words) >= 2:
                        similarity_penalty = -0.25

            total_score = (
                base_score
                + date_boost
                + entity_boost
                + location_boost
                + resolution_factor
                + duplicate_penalty
                + similarity_penalty
            )
            total_score = max(0.0, min(1.0, round(total_score, 3)))

            breakdown = {
                "base_score": base_score,
                "date_boost": date_boost,
                "entity_boost": entity_boost,
                "location_boost": location_boost,
                "resolution_factor": resolution_factor,
                "duplicate_penalty": duplicate_penalty,
                "similarity_penalty": similarity_penalty,
            }
            ranked.append((p, total_score, breakdown))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked


# Singleton for lightweight use
_default_scorer: Optional[RelevanceScorer] = None

def get_scorer(threshold: float = DEFAULT_RELEVANCE_THRESHOLD) -> RelevanceScorer:
    global _default_scorer
    if _default_scorer is None or _default_scorer.threshold != threshold:
        _default_scorer = RelevanceScorer(threshold=threshold)
    return _default_scorer

