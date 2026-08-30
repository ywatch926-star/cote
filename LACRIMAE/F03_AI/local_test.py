#!/usr/bin/env python3
"""
F03_AI — Local E2E Test Runner
Tests the full 3-stage pipeline on a local video without Modal GPU.
Uses OpenCV-only fallback implementations for each stage to verify:
  1. Video I/O (read/write frames)
  2. Étape 1: Upscale (bicubic fallback when Real-ESRGAN unavailable)
  3. Étape 2: Color grading (histogram transfer fallback)
  4. Étape 3: Interpolation + OpenCV crunch style
  5. Output validation (codec, resolution, FPS, frame count)

Usage:
    cd LACRIMAE
    python3 F03_AI/local_test.py [--input .test/rife_input_5s.mp4] [--output .test/f03_ai_local_test.mp4]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np


# ─── ÉTAPE 1: Local Upscale (bicubic fallback) ──────────────────────
def local_upscale(input_path: str, output_path: str, sr_scale: int = 2) -> dict:
    """Upscale video using bicubic interpolation (stand-in for Real-ESRGAN)."""
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    target_w, target_h = w * sr_scale, h * sr_scale

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (target_w, target_h))

    frame_count = 0
    t0 = time.time()
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        upscaled = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
        out.write(upscaled)
        frame_count += 1
    cap.release()
    out.release()
    elapsed = time.time() - t0
    return {"stage": "upscale", "frames": frame_count, "elapsed_s": round(elapsed, 2),
            "resolution": f"{target_w}x{target_h}", "fps": fps}


# ─── ÉTAPE 2: Local Color Grading (histogram match fallback) ────────
def local_color_grade(input_path: str, output_path: str) -> dict:
    """Apply histogram-based color grading (stand-in for VCG L-Diffuser)."""
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Build target histogram profile (warm cinematic tones)
    # Simulates "golden hour" reference image profile
    lut_r = np.clip(np.arange(256) * 1.05 + 5, 0, 255).astype(np.uint8)
    lut_g = np.clip(np.arange(256) * 1.02, 0, 255).astype(np.uint8)
    lut_b = np.clip(np.arange(256) * 0.95, 0, 255).astype(np.uint8)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    frame_count = 0
    t0 = time.time()
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        # Apply channel-wise LUT
        graded = cv2.merge([lut_b[frame[:, :, 0]],
                            lut_g[frame[:, :, 1]],
                            lut_r[frame[:, :, 2]]])
        out.write(graded)
        frame_count += 1
    cap.release()
    out.release()
    elapsed = time.time() - t0
    return {"stage": "color_grade", "frames": frame_count, "elapsed_s": round(elapsed, 2),
            "resolution": f"{w}x{h}", "fps": fps}


# ─── ÉTAPE 3: Local Interpolation + Crunch ───────────────────────────
def _apply_crunch(frame: np.ndarray, preset: dict) -> np.ndarray:
    """Apply the OpenCV crunchy style (single pass)."""
    si = preset.get("sharpen_int", 1.2)
    sb = preset.get("sat_boost", 1.1)
    gi = preset.get("glow_int", 0.4)

    # Unsharp mask
    blur = cv2.GaussianBlur(frame, (9, 9), 10.0)
    sharpened = cv2.addWeighted(frame, 1.0 + si, blur, -si, 0)

    # Saturation
    hsv = cv2.cvtColor(sharpened, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    s = np.clip(s * sb, 0, 255).astype(np.uint8)
    v = np.clip(v * 1.06, 0, 255).astype(np.uint8)
    color_popped = cv2.cvtColor(cv2.merge([h, s, v]), cv2.COLOR_HSV2BGR)

    # Glow
    _, highlights = cv2.threshold(color_popped, 205, 255, cv2.THRESH_TOZERO)
    glow_s = cv2.GaussianBlur(highlights, (25, 25), 0)
    glow_w = cv2.GaussianBlur(highlights, (71, 71), 0)
    total_glow = cv2.addWeighted(glow_s, 0.7, glow_w, 0.3, 0)
    return cv2.addWeighted(color_popped, 1.0, total_glow, gi, 0)


def local_interpolate(input_path: str, output_path: str, multiplier: int = 4,
                      style_preset: str = "default") -> dict:
    """Interpolate using streaming linear blend + apply crunch style.
    Memory-efficient: only holds current + next frame in memory."""
    PRESETS = {
        "default": {"sharpen_int": 1.2, "sat_boost": 1.1, "glow_int": 0.4},
        "demon":   {"sharpen_int": 1.8, "sat_boost": 1.4, "glow_int": 0.6},
        "cinema":  {"sharpen_int": 0.8, "sat_boost": 1.05, "glow_int": 0.3},
        "crunchy": {"sharpen_int": 1.5, "sat_boost": 1.3, "glow_int": 0.5},
    }
    style = PRESETS.get(style_preset, PRESETS["default"])

    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    target_fps = int(fps * multiplier)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, target_fps, (w, h))

    frame_count = 0
    t0 = time.time()

    # Streaming: read two frames at a time (memory-efficient)
    ret, prev_frame = cap.read()
    if not ret:
        cap.release()
        out.release()
        return {"stage": "interpolate", "frames": 0, "elapsed_s": 0}

    while True:
        ret, next_frame = cap.read()
        if not ret:
            # Write last anchor
            out.write(_apply_crunch(prev_frame, style))
            frame_count += 1
            break

        # Write anchor frame
        out.write(_apply_crunch(prev_frame, style))
        frame_count += 1

        # Write interpolated frames
        for t_step in range(1, multiplier):
            t = t_step / multiplier
            blended = cv2.addWeighted(prev_frame, 1.0 - t, next_frame, t, 0)
            out.write(_apply_crunch(blended, style))
            frame_count += 1

        prev_frame = next_frame

    cap.release()
    out.release()
    elapsed = time.time() - t0
    return {"stage": "interpolate", "frames": frame_count, "elapsed_s": round(elapsed, 2),
            "resolution": f"{w}x{h}", "fps": target_fps, "multiplier": multiplier,
            "style": style_preset}


# ─── Output Validation ───────────────────────────────────────────────
def validate_output(path: str) -> dict:
    """Validate the output video file."""
    cap = cv2.VideoCapture(path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    size_mb = os.path.getsize(path) / (1024 * 1024)
    return {"path": path, "width": w, "height": h, "fps": round(fps, 2),
            "frame_count": fc, "size_mb": round(size_mb, 2)}


# ─── Main ────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="F03_AI Local E2E Test")
    parser.add_argument("--input", default=".test/rife_input_5s.mp4")
    parser.add_argument("--output", default=".test/f03_ai_local_test.mp4")
    parser.add_argument("--sr-scale", type=int, default=2)
    parser.add_argument("--amt-multiplier", type=int, default=4)
    parser.add_argument("--style", default="default")
    args = parser.parse_args()

    root = Path(__file__).parent.parent
    input_path = str(root / args.input)
    output_dir = root / ".test" / "f03_ai_pipeline"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(input_path):
        print(f"❌ Input not found: {input_path}")
        sys.exit(1)

    print("=" * 70)
    print("  F03_AI LOCAL E2E TEST — Pipeline v3.1")
    print("=" * 70)
    print(f"  Input:     {input_path}")
    print(f"  Output:    {root / args.output}")
    print(f"  SR Scale:  ×{args.sr_scale}")
    print(f"  AMT Mult:  ×{args.amt_multiplier}")
    print(f"  Style:     {args.style}")
    print("=" * 70)

    stats = {}
    total_t0 = time.time()

    # ── ÉTAPE 1 ──
    print("\n▶ ÉTAPE 1/3: Upscale (bicubic fallback)")
    s1_out = str(output_dir / "step1_upscaled.mp4")
    stats["step1"] = local_upscale(input_path, s1_out, args.sr_scale)
    print(f"  ✅ {stats['step1']['frames']} frames → {stats['step1']['resolution']} "
          f"@ {stats['step1']['fps']}fps in {stats['step1']['elapsed_s']}s")

    # ── ÉTAPE 2 ──
    print("\n▶ ÉTAPE 2/3: Color Grading (histogram transfer)")
    s2_out = str(output_dir / "step2_graded.mp4")
    stats["step2"] = local_color_grade(s1_out, s2_out)
    print(f"  ✅ {stats['step2']['frames']} frames → {stats['step2']['resolution']} "
          f"@ {stats['step2']['fps']}fps in {stats['step2']['elapsed_s']}s")

    # ── ÉTAPE 3 ──
    print(f"\n▶ ÉTAPE 3/3: Interpolation ×{args.amt_multiplier} + Crunch ({args.style})")
    final_out = str(root / args.output)
    stats["step3"] = local_interpolate(s2_out, final_out, args.amt_multiplier, args.style)
    print(f"  ✅ {stats['step3']['frames']} frames → {stats['step3']['resolution']} "
          f"@ {stats['step3']['fps']}fps in {stats['step3']['elapsed_s']}s")

    # ── Validation ──
    print("\n▶ Validation")
    validated = validate_output(final_out)
    stats["validation"] = validated
    print(f"  Resolution:  {validated['width']}×{validated['height']}")
    print(f"  FPS:         {validated['fps']}")
    print(f"  Frames:      {validated['frame_count']}")
    print(f"  Size:        {validated['size_mb']} MB")

    # ── Summary ──
    total_elapsed = round(time.time() - total_t0, 2)
    stats["total"] = {"elapsed_s": total_elapsed}

    print("\n" + "=" * 70)
    print(f"  PIPELINE LOCAL TEST COMPLETE ✅  ({total_elapsed}s)")
    print("=" * 70)

    # Save stats
    stats_path = str(output_dir / "pipeline_stats.json")
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"  Stats saved: {stats_path}")

    # Check expectations
    input_info = validate_output(input_path)
    output_info = validated

    checks = []
    checks.append(("Resolution scaled", output_info["width"] == input_info["width"] * args.sr_scale
                    and output_info["height"] == input_info["height"] * args.sr_scale))
    checks.append(("FPS multiplied", abs(output_info["fps"] - input_info["fps"] * args.amt_multiplier) < 1))
    expected_frames = (input_info["frame_count"] - 1) * args.amt_multiplier + 1
    checks.append(("Frame count correct",
                    abs(output_info["frame_count"] - expected_frames) <= 2))
    checks.append(("Output file exists", os.path.exists(final_out)))
    checks.append(("Output non-empty", output_info["size_mb"] > 0))

    print("\n  CHECKS:")
    all_pass = True
    for name, passed in checks:
        icon = "✅" if passed else "❌"
        print(f"    {icon} {name}")
        if not passed:
            all_pass = False

    if all_pass:
        print("\n  ALL CHECKS PASSED ✅")
    else:
        print("\n  SOME CHECKS FAILED ❌")
        sys.exit(1)


if __name__ == "__main__":
    main()
