"""
DocStudio Memory Guard
Monitors system RAM before memory-intensive steps (TTS, depth models, CLIP, rendering).
Enforces the 3.0 GB minimum available RAM rule on resource-constrained hardware.
"""

from __future__ import annotations
import gc
import os
import sys
from typing import List, Tuple
import psutil

class MemoryGuardError(RuntimeError):
    """Raised when available system RAM is insufficient for a heavy pipeline stage."""
    pass

def get_available_ram_gb() -> float:
    """Returns available physical RAM in Gigabytes."""
    mem = psutil.virtual_memory()
    return mem.available / (1024 ** 3)

def get_total_ram_gb() -> float:
    """Returns total physical RAM in Gigabytes."""
    mem = psutil.virtual_memory()
    return mem.total / (1024 ** 3)

def get_top_memory_consumers(limit: int = 5) -> List[Tuple[str, float]]:
    """Identifies the top memory-consuming processes to assist the user in freeing RAM."""
    procs = []
    current_pid = os.getpid()
    for p in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            if p.info['pid'] == current_pid:
                continue
            mem_bytes = p.info['memory_info'].rss if p.info.get('memory_info') else 0
            mem_mb = mem_bytes / (1024 * 1024)
            if mem_mb > 50:  # Only report processes using >50MB
                procs.append((p.info['name'] or f"PID {p.info['pid']}", mem_mb))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
            
    procs.sort(key=lambda x: x[1], reverse=True)
    return procs[:limit]

def check_memory_guard(step_name: str = "Heavy Pipeline Step", min_free_gb: float = 3.0, auto_gc: bool = True) -> float:
    """
    Checks if available RAM meets or exceeds the required threshold.
    If RAM is below min_free_gb, attempts garbage collection first.
    If still below threshold, raises MemoryGuardError with explicit advice on what to close.
    """
    if auto_gc:
        gc.collect()

    avail_gb = get_available_ram_gb()
    if avail_gb >= min_free_gb:
        return avail_gb

    # If below threshold, force Python GC and re-check
    gc.collect()
    avail_gb = get_available_ram_gb()
    if avail_gb >= min_free_gb:
        return avail_gb

    top_procs = get_top_memory_consumers(5)
    suggestions = "\n".join([f"  - {name}: {mb:.1f} MB" for name, mb in top_procs])
    
    error_msg = (
        f"\n[MEMORY GUARD ALERT] Critical memory limit reached before '{step_name}'!\n"
        f"Available RAM: {avail_gb:.2f} GB | Required Minimum: {min_free_gb:.2f} GB | Total RAM: {get_total_ram_gb():.2f} GB.\n\n"
        f"Hardware Safety Halt: To prevent OS thrashing or Out-Of-Memory termination, "
        f"please close background applications to free at least {min_free_gb - avail_gb:.2f} GB.\n"
        f"Top memory consumers currently running:\n{suggestions}\n"
    )
    raise MemoryGuardError(error_msg)

class HeavyStageContext:
    """
    Context manager for sequential heavy stages.
    Ensures memory is verified before entry, and aggressively freed after exit.
    """
    def __init__(self, step_name: str, min_free_gb: float = 3.0):
        self.step_name = step_name
        self.min_free_gb = min_free_gb

    def __enter__(self):
        check_memory_guard(step_name=self.step_name, min_free_gb=self.min_free_gb)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        gc.collect()
        return False


class MemoryGuard:
    """Convenience class providing static methods for memory inspection and gating."""

    @staticmethod
    def get_memory_status() -> dict:
        mem = psutil.virtual_memory()
        return {
            "total_gb": mem.total / (1024 ** 3),
            "available_gb": mem.available / (1024 ** 3),
            "percent_used": mem.percent,
        }

    @staticmethod
    def check(step_name: str = "Heavy Pipeline Step", min_free_gb: float = 3.0) -> float:
        return check_memory_guard(step_name=step_name, min_free_gb=min_free_gb)


def check_system_memory(min_gb: float = 3.0) -> bool:
    """Non-throwing boolean check for whether system meets RAM threshold."""
    try:
        check_memory_guard(step_name="Probe Check", min_free_gb=min_gb)
        return True
    except MemoryGuardError:
        return False

