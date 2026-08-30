"""
F03_AI Configuration — GPU, presets, timeouts, paths
"""
import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ─── Paths ────────────────────────────────────────────────────────────
PRESETS_DIR = Path(__file__).parent.parent / "PRESETS"

# ─── GPU Config ───────────────────────────────────────────────────────
@dataclass
class GPUConfig:
    gpu: str = "A10G"            # Modal GPU type
    float16: bool = True         # Use float16 for all models
    timeout_diffbir: int = 600   # seconds
    timeout_vcg: int = 600       # seconds
    timeout_amt: int = 900       # seconds (interpolation is heavier)
    cpu_cores: float = 4.0

# ─── DiffBIR Config ──────────────────────────────────────────────────
@dataclass
class DiffBIRConfig:
    repo_url: str = "https://github.com/XPixelGroup/DiffBIR.git"
    weights_base: str = "https://huggingface.co"
    general_weight: str = "general_swinir_v1.ckpt"
    face_weight: str = "face_swinir_v1.ckpt"
    sr_scale: int = 2            # 720p → 1080p
    device: str = "cuda"

# ─── VCG Config ──────────────────────────────────────────────────────
@dataclass
class VCGConfig:
    repo_url: str = "https://github.com/seunghyuns98/VideoColorGrading.git"
    model_name: str = "seunghyuns98/VCG-Weights"
    lut_resolution: int = 16     # 16³ LUT cube
    temporal_consistency: bool = True
    device: str = "cuda"

# ─── AMT Config ──────────────────────────────────────────────────────
@dataclass
class AMTConfig:
    repo_url: str = "https://github.com/MCG-NKU/AMT.git"
    model_weight: str = "amt-g.pth"
    weights_base: str = "https://huggingface.co"
    multiplier: int = 4          # 30fps → 120fps
    device: str = "cuda"

# ─── Style Presets ───────────────────────────────────────────────────
@dataclass
class StylePreset:
    sharpen_int: float = 1.2
    sat_boost: float = 1.1
    glow_int: float = 0.4
    glow_small_ksize: int = 25
    glow_wide_ksize: int = 71
    highlight_threshold: int = 205

DEFAULT_STYLE = StylePreset()

def load_style_presets() -> dict:
    """Load style presets from JSON file."""
    presets_path = PRESETS_DIR / "style_presets.json"
    if not presets_path.exists():
        return {"default": DEFAULT_STYLE}
    
    with open(presets_path) as f:
        raw = json.load(f)
    
    presets = {}
    for name, params in raw.items():
        presets[name] = StylePreset(**params)
    return presets

def get_style_preset(name: str = "default") -> StylePreset:
    """Get a specific style preset by name."""
    presets = load_style_presets()
    return presets.get(name, DEFAULT_STYLE)

# ─── Pipeline Config ─────────────────────────────────────────────────
@dataclass
class PipelineConfig:
    gpu: GPUConfig = field(default_factory=GPUConfig)
    diffbir: DiffBIRConfig = field(default_factory=DiffBIRConfig)
    vcg: VCGConfig = field(default_factory=VCGConfig)
    amt: AMTConfig = field(default_factory=AMTConfig)
    style_preset: str = "default"
    target_resolution: tuple = (1080, 1920)  # width, height (TikTok 9:16)
    maintain_aspect: bool = True

# Global config instance
CONFIG = PipelineConfig()
