"""Hardware detection for NIKAME MLOps.

Detects NVIDIA GPUs, Apple Silicon (MPS), system RAM, and CPU cores
 to optimize ML serving placement.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Literal


@dataclass
class HardwareSpecs:
    """Summary of detected system hardware."""
    cpu_count: int
    ram_gb: float
    gpu_type: Literal["nvidia", "amd", "apple", "none"]
    vram_gb: float = 0.0
    gpu_count: int = 0
    mps_available: bool = False


class HardwareDetector:
    """Utility to detect available compute resources."""

    @staticmethod
    def detect() -> HardwareSpecs:
        """Run all detection logic and return hardware specs."""
        cpu_count = os.cpu_count() or 1
        ram_gb = HardwareDetector._get_ram_gb()
        
        gpu_type: Literal["nvidia", "amd", "apple", "none"] = "none"
        vram_gb = 0.0
        gpu_count = 0
        mps_available = False

        # 1. Check for NVIDIA GPU
        nvidia_smi = shutil.which("nvidia-smi")
        if nvidia_smi:
            try:
                # Simple query for VRAM and count
                res = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.total,name", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, check=True
                )
                lines = res.stdout.strip().split("\n")
                if lines:
                    gpu_type = "nvidia"
                    gpu_count = len(lines)
                    # Use the first GPU's VRAM as representative (simple approach)
                    vram_gb = float(lines[0].split(",")[0]) / 1024.0
            except (subprocess.CalledProcessError, ValueError, IndexError):
                pass

        # 2. Check for Apple Silicon (MPS)
        if gpu_type == "none" and os.uname().sysname == "Darwin":
            gpu_type = "apple"
            mps_available = True
            vram_gb = ram_gb * 0.5

        return HardwareSpecs(
            cpu_count=cpu_count,
            ram_gb=ram_gb,
            gpu_type=gpu_type,
            vram_gb=vram_gb,
            gpu_count=gpu_count,
            mps_available=mps_available
        )

    @staticmethod
    def _get_ram_gb() -> float:
        """Get total system RAM in GB."""
        try:
            import psutil
            return psutil.virtual_memory().total / (1024 ** 3)
        except ImportError:
            try:
                if os.path.exists("/proc/meminfo"):
                    with open("/proc/meminfo", "r") as f:
                        for line in f:
                            if "MemTotal" in line:
                                return int(line.split()[1]) / (1024 ** 2)
            except (IOError, ValueError, IndexError):
                pass
        return 8.0
