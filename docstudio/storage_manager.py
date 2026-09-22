"""
docstudio/storage_manager.py
============================
Storage and Resource Manager (Autonomous Rules 17 & 29).

Enforces machine hardware safety on constrained development machines
(e.g., HP Aero 13 with 16 GB RAM and 512 GB SSD):
1. Pre-flight SSD disk space monitoring.
2. Temporary render file and frame cache cleanup.
3. Configurable asset cache eviction limits.
4. Duplicate asset detection by file size and content hash.
5. Old job pruning and archive management.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from docstudio.config import BASE_DIR, RUNS_DIR


class StorageManager:
    def __init__(
        self,
        base_dir: Optional[Path] = None,
        min_free_gb: float = 10.0,
        max_cache_gb: float = 5.0,
    ):
        self.base_dir = Path(base_dir) if base_dir else BASE_DIR
        self.min_free_gb = min_free_gb
        self.max_cache_gb = max_cache_gb

    def check_disk_space(self, target_path: Optional[Path] = None) -> dict:
        """
        Monitors available SSD capacity before triggering resource-intensive jobs.
        """
        check_dir = target_path or self.base_dir
        if not check_dir.exists():
            check_dir = check_dir.parent

        total, used, free = shutil.disk_usage(str(check_dir))
        free_gb = free / (1024 ** 3)
        total_gb = total / (1024 ** 3)
        used_gb = used / (1024 ** 3)

        sufficient = free_gb >= self.min_free_gb
        warning = None
        if not sufficient:
            warning = (
                f"LOW DISK SPACE WARNING: Only {free_gb:.2f} GB free on {check_dir.drive or check_dir}. "
                f"DocStudio requires at least {self.min_free_gb:.1f} GB for safe video production."
            )

        return {
            "free_gb": round(free_gb, 2),
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "sufficient": sufficient,
            "min_required_gb": self.min_free_gb,
            "warning": warning,
        }

    def clean_job_temp_files(self, job_dir: Path) -> dict:
        """
        Cleans ephemeral working artifacts (temp frames, uncompressed segment mixes, FFmpeg temp cuts)
        while preserving all structured JSON artifacts, logs, and final render outputs.
        """
        job_dir = Path(job_dir)
        if not job_dir.exists():
            return {"cleaned_bytes": 0, "cleaned_files": []}

        cleaned_files = []
        cleaned_bytes = 0

        # Patterns for temporary/ephemeral files
        temp_dir_names = ["temp_render", "frame_cache", "tmp", "__pycache__"]
        for dname in temp_dir_names:
            td = job_dir / dname
            if td.exists() and td.is_dir():
                for f in td.rglob("*"):
                    if f.is_file():
                        cleaned_bytes += f.stat().st_size
                shutil.rmtree(td, ignore_errors=True)
                cleaned_files.append(str(td.name))

        # Individual temp files
        for p in job_dir.glob("*.tmp"):
            if p.is_file():
                cleaned_bytes += p.stat().st_size
                p.unlink(missing_ok=True)
                cleaned_files.append(p.name)

        return {
            "cleaned_bytes": cleaned_bytes,
            "cleaned_mb": round(cleaned_bytes / (1024 * 1024), 2),
            "cleaned_targets": cleaned_files,
        }

    def enforce_cache_limits(self, cache_dir: Optional[Path] = None) -> dict:
        """
        Prunes the oldest cached media assets if cache exceeds max_cache_gb.
        """
        target_cache = cache_dir or (self.base_dir / "assets" / "cache")
        if not target_cache.exists():
            return {"pruned_count": 0, "freed_mb": 0.0}

        all_files = [f for f in target_cache.rglob("*") if f.is_file()]
        total_size = sum(f.stat().st_size for f in all_files)
        limit_bytes = int(self.max_cache_gb * (1024 ** 3))

        if total_size <= limit_bytes:
            return {
                "pruned_count": 0,
                "freed_mb": 0.0,
                "current_cache_mb": round(total_size / (1024 * 1024), 2),
            }

        # Sort files by modification time (oldest first)
        sorted_files = sorted(all_files, key=lambda f: f.stat().st_mtime)
        freed = 0
        pruned_count = 0
        for f in sorted_files:
            if total_size - freed <= limit_bytes:
                break
            try:
                sz = f.stat().st_size
                f.unlink(missing_ok=True)
                freed += sz
                pruned_count += 1
            except Exception:
                pass

        return {
            "pruned_count": pruned_count,
            "freed_mb": round(freed / (1024 * 1024), 2),
            "current_cache_mb": round((total_size - freed) / (1024 * 1024), 2),
        }

    def detect_duplicate_assets(self, directory: Path) -> list[dict]:
        """
        Scans a directory for identical media files by byte size and SHA-256 hash.
        """
        directory = Path(directory)
        if not directory.exists():
            return []

        by_size: dict[int, list[Path]] = {}
        for f in directory.rglob("*"):
            if f.is_file() and f.suffix.lower() in (".mp4", ".mov", ".jpg", ".jpeg", ".png", ".wav"):
                sz = f.stat().st_size
                by_size.setdefault(sz, []).append(f)

        duplicates = []
        for sz, files in by_size.items():
            if len(files) > 1 and sz > 0:
                hashes: dict[str, list[str]] = {}
                for f in files:
                    try:
                        h = hashlib.sha256(f.read_bytes()[:1048576]).hexdigest()  # Hash first 1MB for speed
                        hashes.setdefault(h, []).append(str(f))
                    except Exception:
                        pass
                for h, paths in hashes.items():
                    if len(paths) > 1:
                        duplicates.append({
                            "size_bytes": sz,
                            "hash_sample": h[:12],
                            "files": paths,
                        })

        return duplicates
