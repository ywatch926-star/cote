#!/usr/bin/env python3
"""
F03_AI — Real Modal GPU Test Runner
Runs the full 3-stage pipeline on Modal with real GPU workers.

Usage:
    cd LACRIMAE
    python3 F03_AI/run_real_test.py
"""
from modal import Function
import os
import sys
import time
import json


def main():
    print("=" * 70)
    print("  F03_AI — REAL GPU PIPELINE TEST (Modal)")
    print("=" * 70)

    total_start = time.time()
    stats = {}

    # ─── Read inputs ──────────────────────────────────────────────────
    input_video = "/tmp/test_input.mp4"
    ref_image = "/tmp/ref_frame.png"
    output_dir = ".test/f03_ai_modal_test"
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(input_video):
        print(f"❌ Input video not found: {input_video}")
        sys.exit(1)
    if not os.path.exists(ref_image):
        print(f"❌ Reference image not found: {ref_image}")
        sys.exit(1)

    with open(input_video, "rb") as f:
        video_bytes = f.read()
    with open(ref_image, "rb") as f:
        ref_bytes = f.read()

    input_size_mb = len(video_bytes) / 1024 / 1024
    print(f"\n  Input:     {input_video} ({input_size_mb:.1f} MB)")
    print(f"  Reference: {ref_image}")
    print(f"  Settings:  sr_scale=1 (already 1080p), amt=×4 (30→120fps), style=crunchy")
    print()

    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 1: DiffBIR/Real-ESRGAN Upscale
    # ═══════════════════════════════════════════════════════════════════
    print("▶ ÉTAPE 1/3: Real-ESRGAN Upscale (Modal GPU)")
    print("  Connecting to lac-upscale worker...")
    step1_start = time.time()
    try:
        diffbir_fn = Function.from_name("lac-upscale", "diffbir_upscale")
        step1_bytes = diffbir_fn.remote(video_bytes, sr_scale=1)
        step1_time = time.time() - step1_start
        stats["step1"] = {
            "stage": "upscale",
            "time_s": round(step1_time, 1),
            "output_mb": round(len(step1_bytes) / 1024 / 1024, 2),
            "status": "ok"
        }
        print(f"  ✅ Done in {step1_time:.1f}s ({len(step1_bytes) / 1024 / 1024:.1f} MB)")
    except Exception as e:
        step1_time = time.time() - step1_start
        stats["step1"] = {"stage": "upscale", "status": "error", "error": str(e), "time_s": round(step1_time, 1)}
        print(f"  ❌ FAILED after {step1_time:.1f}s: {e}")
        print("  ⚠️  Continuing with original video for next steps...")
        step1_bytes = video_bytes

    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 2: VCG Color Grading
    # ═══════════════════════════════════════════════════════════════════
    print("\n▶ ÉTAPE 2/3: VCG Neural Color Grading (Modal GPU)")
    print("  Connecting to lac-vcg-color-grading worker...")
    step2_start = time.time()
    try:
        vcg_fn = Function.from_name("lac-vcg-color-grading", "vcg_grade")
        step2_bytes = vcg_fn.remote(step1_bytes, ref_bytes, lut_resolution=16, temporal_consistency=True)
        step2_time = time.time() - step2_start
        stats["step2"] = {
            "stage": "color_grade",
            "time_s": round(step2_time, 1),
            "output_mb": round(len(step2_bytes) / 1024 / 1024, 2),
            "status": "ok"
        }
        print(f"  ✅ Done in {step2_time:.1f}s ({len(step2_bytes) / 1024 / 1024:.1f} MB)")
    except Exception as e:
        step2_time = time.time() - step2_start
        stats["step2"] = {"stage": "color_grade", "status": "error", "error": str(e), "time_s": round(step2_time, 1)}
        print(f"  ❌ FAILED after {step2_time:.1f}s: {e}")
        print("  ⚠️  Continuing with ungraded video for next step...")
        step2_bytes = step1_bytes

    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 3: AMT-G Interpolation + OpenCV Crunch
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n▶ ÉTAPE 3/3: AMT-G Interpolation ×4 + Crunchy Style (Modal GPU)")
    print("  Connecting to lac-amt-interpolation worker...")
    step3_start = time.time()
    try:
        amt_fn = Function.from_name("lac-amt-interpolation", "amt_interpolate")
        final_bytes = amt_fn.remote(step2_bytes, multiplier=4, style_preset="crunchy")
        step3_time = time.time() - step3_start
        stats["step3"] = {
            "stage": "interpolate",
            "time_s": round(step3_time, 1),
            "output_mb": round(len(final_bytes) / 1024 / 1024, 2),
            "status": "ok"
        }
        print(f"  ✅ Done in {step3_time:.1f}s ({len(final_bytes) / 1024 / 1024:.1f} MB)")
    except Exception as e:
        step3_time = time.time() - step3_start
        stats["step3"] = {"stage": "interpolate", "status": "error", "error": str(e), "time_s": round(step3_time, 1)}
        print(f"  ❌ FAILED after {step3_time:.1f}s: {e}")
        final_bytes = step2_bytes

    # ─── Write output ─────────────────────────────────────────────────
    output_path = os.path.join(output_dir, "f03_ai_modal_final.mp4")
    with open(output_path, "wb") as f:
        f.write(final_bytes)
    output_size_mb = os.path.getsize(output_path) / 1024 / 1024

    # ─── Final stats ──────────────────────────────────────────────────
    total_time = time.time() - total_start
    stats["total"] = {
        "elapsed_s": round(total_time, 1),
        "input_mb": round(input_size_mb, 2),
        "output_mb": round(output_size_mb, 2),
    }

    print("\n" + "=" * 70)
    print("  PIPELINE TERMINÉ ✅")
    print("=" * 70)
    print(f"  Total:     {total_time:.1f}s")
    print(f"  Input:     {input_size_mb:.1f} MB")
    print(f"  Output:    {output_size_mb:.1f} MB → {output_path}")
    print(f"  Coût est.: ~${total_time / 3600 * 1.10:.4f} (A10G × 3 workers)")
    print()

    # Print step breakdown
    for key in ["step1", "step2", "step3"]:
        s = stats.get(key, {})
        status_icon = "✅" if s.get("status") == "ok" else "❌"
        print(f"  {status_icon} {s.get('stage', key)}: {s.get('time_s', '?')}s — {s.get('output_mb', '?')} MB")

    print()
    print("=" * 70)

    # Save stats
    stats_path = os.path.join(output_dir, "modal_stats.json")
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"  Stats: {stats_path}")
    print("=" * 70)

    return stats


if __name__ == "__main__":
    main()
