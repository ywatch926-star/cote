"""
F03_AI — Pipeline Orchestrator
Chains the 3 Modal workers sequentially:
  Étape 1: DiffBIR (upscale + textures)
  Étape 2: VCG (color grading)
  Étape 3: AMT-G + OpenCV (interpolation + crunch)
"""
import modal
import os
import sys
import time
import json
from pathlib import Path
from typing import Optional


def run_pipeline(
    input_video: str,
    reference_image: str,
    output_video: str,
    sr_scale: int = 2,
    lut_resolution: int = 16,
    amt_multiplier: int = 4,
    style_preset: str = "default",
    verbose: bool = True,
) -> dict:
    """
    Run the full F03_AI pipeline.
    
    Args:
        input_video: Path to input video file
        reference_image: Path to reference image for color grading
        output_video: Path to output video file
        sr_scale: DiffBIR upscale factor (2 = 720p→1080p)
        lut_resolution: VCG LUT cube resolution
        amt_multiplier: AMT FPS multiplier (4 = 30→120fps)
        style_preset: OpenCV style preset (default/demon/cinema/crunchy)
        verbose: Print progress logs
    
    Returns:
        Pipeline stats dict (timings, sizes)
    """
    stats = {}
    total_start = time.time()
    
    def log(msg):
        if verbose:
            print(f"[ORCHESTRATOR] {msg}")
    
    # ─── Validate inputs ─────────────────────────────────────────────
    if not os.path.exists(input_video):
        raise FileNotFoundError(f"Input video not found: {input_video}")
    if not os.path.exists(reference_image):
        raise FileNotFoundError(f"Reference image not found: {reference_image}")
    
    input_size = os.path.getsize(input_video)
    log(f"Input: {input_video} ({input_size / 1024 / 1024:.1f} MB)")
    log(f"Reference: {reference_image}")
    log(f"Output: {output_video}")
    log(f"Settings: sr_scale={sr_scale}, lut={lut_resolution}, "
        f"amt=×{amt_multiplier}, style={style_preset}")
    
    # ─── Read input files ────────────────────────────────────────────
    with open(input_video, "rb") as f:
        video_bytes = f.read()
    with open(reference_image, "rb") as f:
        ref_bytes = f.read()
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 1: DiffBIR Upscale + Textures
    # ═══════════════════════════════════════════════════════════════════
    log("=" * 60)
    log("ÉTAPE 1/3: DiffBIR — Upscale + Texture Regeneration")
    log("=" * 60)
    
    step_start = time.time()
    try:
        diffbir_fn = modal.Function.from_name(
            "lac-upscale", "diffbir_upscale"
        )
        step1_bytes = diffbir_fn.remote(video_bytes, sr_scale=sr_scale)
        step1_time = time.time() - step_start
        stats["step1_diffbir"] = {
            "time_s": round(step1_time, 1),
            "output_bytes": len(step1_bytes),
            "status": "ok"
        }
        log(f"✅ Étape 1 terminée en {step1_time:.1f}s ({len(step1_bytes) / 1024 / 1024:.1f} MB)")
    except Exception as e:
        log(f"❌ Étape 1 échouée: {e}")
        stats["step1_diffbir"] = {"status": "error", "error": str(e)}
        raise
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 2: VCG Color Grading
    # ═══════════════════════════════════════════════════════════════════
    log("=" * 60)
    log("ÉTAPE 2/3: VCG — Neural Color Grading (L-Diffuser)")
    log("=" * 60)
    
    step_start = time.time()
    try:
        vcg_fn = modal.Function.from_name(
            "lac-vcg-color-grading", "vcg_grade"
        )
        step2_bytes = vcg_fn.remote(
            step1_bytes,
            ref_bytes,
            lut_resolution=lut_resolution,
            temporal_consistency=True,
        )
        step2_time = time.time() - step_start
        stats["step2_vcg"] = {
            "time_s": round(step2_time, 1),
            "output_bytes": len(step2_bytes),
            "status": "ok"
        }
        log(f"✅ Étape 2 terminée en {step2_time:.1f}s ({len(step2_bytes) / 1024 / 1024:.1f} MB)")
    except Exception as e:
        log(f"❌ Étape 2 échouée: {e}")
        stats["step2_vcg"] = {"status": "error", "error": str(e)}
        raise
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 3: AMT-G Interpolation + OpenCV Crunch
    # ═══════════════════════════════════════════════════════════════════
    log("=" * 60)
    log("ÉTAPE 3/3: AMT-G — Interpolation + OpenCV Crunchy Style")
    log("=" * 60)
    
    step_start = time.time()
    try:
        amt_fn = modal.Function.from_name(
            "lac-amt-interpolation", "amt_interpolate"
        )
        final_bytes = amt_fn.remote(
            step2_bytes,
            multiplier=amt_multiplier,
            style_preset=style_preset,
        )
        step3_time = time.time() - step_start
        stats["step3_amt"] = {
            "time_s": round(step3_time, 1),
            "output_bytes": len(final_bytes),
            "status": "ok"
        }
        log(f"✅ Étape 3 terminée en {step3_time:.1f}s ({len(final_bytes) / 1024 / 1024:.1f} MB)")
    except Exception as e:
        log(f"❌ Étape 3 échouée: {e}")
        stats["step3_amt"] = {"status": "error", "error": str(e)}
        raise
    
    # ─── Write output ────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_video) or ".", exist_ok=True)
    with open(output_video, "wb") as f:
        f.write(final_bytes)
    
    # ─── Final stats ─────────────────────────────────────────────────
    total_time = time.time() - total_start
    output_size = os.path.getsize(output_video)
    
    stats["total"] = {
        "time_s": round(total_time, 1),
        "input_mb": round(input_size / 1024 / 1024, 1),
        "output_mb": round(output_size / 1024 / 1024, 1),
        "steps_completed": 3,
    }
    
    log("=" * 60)
    log("PIPELINE TERMINÉ ✅")
    log(f"  Total: {total_time:.1f}s")
    log(f"  Input:  {input_size / 1024 / 1024:.1f} MB")
    log(f"  Output: {output_size / 1024 / 1024:.1f} MB")
    log(f"  Coût Modal estimé: ~${total_time / 3600 * 1.10:.3f} (A10G)")
    log("=" * 60)
    
    return stats


# ─── CLI ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="F03_AI Pipeline Orchestrator"
    )
    parser.add_argument("input_video", help="Input video path")
    parser.add_argument("reference_image", help="Reference image for color grading")
    parser.add_argument("output_video", help="Output video path")
    parser.add_argument("--sr-scale", type=int, default=2, help="Upscale factor")
    parser.add_argument("--lut-resolution", type=int, default=16, help="LUT resolution")
    parser.add_argument("--amt-multiplier", type=int, default=4, help="FPS multiplier")
    parser.add_argument("--style", default="default", 
                       choices=["default", "demon", "cinema", "crunchy"],
                       help="Style preset")
    
    args = parser.parse_args()
    
    result = run_pipeline(
        input_video=args.input_video,
        reference_image=args.reference_image,
        output_video=args.output_video,
        sr_scale=args.sr_scale,
        lut_resolution=args.lut_resolution,
        amt_multiplier=args.amt_multiplier,
        style_preset=args.style,
    )
    
    print(json.dumps(result, indent=2))
