#!/usr/bin/env python3
"""
F03_AI — Color Diagnostic Script
Extracts frames at each pipeline stage and analyzes color statistics
to identify exactly where colors get destroyed.
"""
import os
import sys
import json
import time
import argparse
import tempfile
import subprocess
import numpy as np
import cv2

# ─── Paths ──────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.join(BASE_DIR, "..", ".test", "f03_ai_debug")
FRAMES_DIR = os.path.join(TEST_DIR, "debug_frames")


def ensure_dirs():
    os.makedirs(FRAMES_DIR, exist_ok=True)


def extract_first_frame(video_path: str, output_path: str) -> bool:
    """Extract frame at 1 second mark."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(fps * 1))
    ret, frame = cap.read()
    cap.release()
    if ret:
        cv2.imwrite(output_path, frame)
    return ret


def analyze_frame(frame, name: str) -> dict:
    """Compute comprehensive color statistics for a frame."""
    stats = {"name": name, "shape": list(frame.shape)}

    # ── BGR stats ──
    for i, ch in enumerate(["b", "g", "r"]):
        c = frame[:, :, i].astype(np.float32)
        stats[f"{ch}_mean"] = round(float(c.mean()), 2)
        stats[f"{ch}_std"] = round(float(c.std()), 2)
        stats[f"{ch}_min"] = round(float(c.min()), 2)
        stats[f"{ch}_max"] = round(float(c.max()), 2)

    # ── HSV stats ──
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    stats["h_mean"] = round(float(h.mean()), 2)
    stats["s_mean"] = round(float(s.mean()), 2)
    stats["v_mean"] = round(float(v.mean()), 2)
    stats["s_std"] = round(float(s.std()), 2)

    # ── LAB stats ──
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB).astype(np.float32)
    l, a, b = lab[:, :, 0], lab[:, :, 1], lab[:, :, 2]
    stats["L_mean"] = round(float(l.mean()), 2)
    stats["a_mean"] = round(float(a.mean()), 2)
    stats["b_mean"] = round(float(b.mean()), 2)
    stats["a_std"] = round(float(a.std()), 2)
    stats["b_std"] = round(float(b.std()), 2)

    # ── Dominant color detection ──
    # If a channel is heavily shifted, we have a color cast
    stats["color_cast"] = "none"
    if stats["r_mean"] > stats["g_mean"] + 30 and stats["r_mean"] > stats["b_mean"] + 30:
        stats["color_cast"] = "RED dominant"
    elif stats["b_mean"] > stats["r_mean"] + 30 and stats["b_mean"] > stats["g_mean"] + 30:
        stats["color_cast"] = "BLUE dominant"
    elif stats["g_mean"] > stats["r_mean"] + 30 and stats["g_mean"] > stats["b_mean"] + 30:
        stats["color_cast"] = "GREEN dominant"

    # ── Skin tone detection (LAB a/b range for skin) ──
    # Healthy skin: a > 120, b > 120 in LAB (0-255 scale)
    skin_mask = (lab[:, :, 1] > 120) & (lab[:, :, 2] > 120)
    skin_pct = float(skin_mask.sum() / skin_mask.size * 100)
    stats["skin_pct"] = round(skin_pct, 1)
    stats["skin健康的"] = "yes" if skin_pct > 5 else "no"

    return stats


def make_comparison_image(frames: list, names: list, output_path: str):
    """Create side-by-side comparison of all frames."""
    if not frames:
        return

    h, w = frames[0].shape[:2]
    target_w = 400
    target_h = int(h * target_w / w)

    resized = []
    for i, f in enumerate(frames):
        r = cv2.resize(f, (target_w, target_h))
        # Add label
        cv2.putText(r, names[i], (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(r, names[i], (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
        resized.append(r)

    # Stack horizontally
    comparison = np.hstack(resized)
    cv2.imwrite(output_path, comparison)
    print(f"  Saved comparison: {output_path}")


def make_histogram_image(frames: list, names: list, output_path: str):
    """Create histogram comparison for each frame."""
    if not frames:
        return

    hist_h, hist_w = 200, 400
    hist_images = []

    for i, frame in enumerate(frames):
        hist_img = np.zeros((hist_h, hist_w, 3), dtype=np.uint8)
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # BGR

        for ch in range(3):
            hist = cv2.calcHist([frame], [ch], None, [256], [0, 256])
            hist = hist.flatten()
            hist = hist / hist.max() * (hist_h - 20)

            for x in range(256):
                x1 = int(x * hist_w / 256)
                x2 = int((x + 1) * hist_w / 256)
                y = int(hist_h - hist[x])
                cv2.rectangle(hist_img, (x1, y), (x2, hist_h), colors[ch], -1)

        cv2.putText(hist_img, names[i], (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        hist_images.append(hist_img)

    # Stack vertically
    comparison = np.vstack(hist_images)
    cv2.imwrite(output_path, comparison)
    print(f"  Saved histograms: {output_path}")


def run_upscale(input_path: str, output_path: str):
    """Run Step 1: Upscale via Modal."""
    print("  → Running Upscale...")
    try:
        import modal
        from modal import Function

        upscale_fn = Function.from_name("lac-upscale", "diffbir_upscale")

        with open(input_path, "rb") as f:
            video_bytes = f.read()

        result = upscale_fn.remote(video_bytes, sr_scale=1)

        with open(output_path, "wb") as f:
            f.write(result)
        print("  ✅ Upscale done")
        return True
    except Exception as e:
        print(f"  ❌ Upscale failed: {e}")
        return False


def run_vcg(input_path: str, ref_path: str, output_path: str):
    """Run Step 2: Color Grading via Modal."""
    print("  → Running VCG Color Grading...")
    try:
        import modal
        from modal import Function

        vcg_fn = Function.from_name("lac-vcg-color-grading", "vcg_grade")

        with open(input_path, "rb") as f:
            video_bytes = f.read()
        with open(ref_path, "rb") as f:
            ref_bytes = f.read()

        result = vcg_fn.remote(video_bytes, ref_bytes)

        with open(output_path, "wb") as f:
            f.write(result)
        print("  ✅ VCG done")
        return True
    except Exception as e:
        print(f"  ❌ VCG failed: {e}")
        return False


def run_amt(input_path: str, output_path: str, multiplier: int = 4):
    """Run Step 3: Interpolation via Modal."""
    print("  → Running AMT-G Interpolation...")
    try:
        import modal
        from modal import Function

        amt_fn = Function.from_name("lac-amt-interpolation", "amt_interpolate")

        with open(input_path, "rb") as f:
            video_bytes = f.read()

        result = amt_fn.remote(video_bytes, multiplier=multiplier, style="crunchy")

        with open(output_path, "wb") as f:
            f.write(result)
        print("  ✅ AMT done")
        return True
    except Exception as e:
        print(f"  ❌ AMT failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="F03_AI Color Diagnostic")
    parser.add_argument("--input", required=True, help="Input video path")
    parser.add_argument("--ref", help="Reference image for VCG")
    parser.add_argument("--skip-upscale", action="store_true", help="Skip upscale step")
    parser.add_argument("--skip-amt", action="store_true", help="Skip AMT interpolation")
    parser.add_argument("--local-only", action="store_true", help="Only analyze input, no Modal calls")
    args = parser.parse_args()

    ensure_dirs()
    print("=" * 60)
    print("  F03_AI — COLOR DIAGNOSTIC")
    print("=" * 60)

    # ── Paths ──
    input_path = args.input
    upscale_out = os.path.join(TEST_DIR, "step1_upscale.mp4")
    vcg_out = os.path.join(TEST_DIR, "step2_vcg.mp4")
    amt_out = os.path.join(TEST_DIR, "step3_amt.mp4")

    # ── Step 0: Extract and analyze input frame ──
    print("\n▶ STEP 0: Analyzing input video...")
    input_frame = os.path.join(FRAMES_DIR, "frame_00_input.png")
    if not extract_first_frame(input_path, input_frame):
        print("  ❌ Cannot extract frame from input")
        return

    frame_input = cv2.imread(input_frame)
    stats_input = analyze_frame(frame_input, "00_input")
    print(f"  Stats: {json.dumps(stats_input, indent=2)}")

    all_frames = [frame_input]
    all_names = ["Input"]
    all_stats = [stats_input]

    if args.local_only:
        print("\n▶ Local-only mode: analyzing input only")
        # Create comparison
        make_comparison_image(all_frames, all_names, os.path.join(FRAMES_DIR, "comparison.png"))
        make_histogram_image(all_frames, all_names, os.path.join(FRAMES_DIR, "histograms.png"))

        # Save report
        report = {"stats": all_stats, "diagnosis": "local_only"}
        with open(os.path.join(TEST_DIR, "debug_report.json"), "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n✅ Report saved to {TEST_DIR}/debug_report.json")
        return

    # ── Step 1: Upscale ──
    if not args.skip_upscale:
        print("\n▶ STEP 1: Running Upscale...")
        if run_upscale(input_path, upscale_out):
            frame_s1 = os.path.join(FRAMES_DIR, "frame_01_upscale.png")
            if extract_first_frame(upscale_out, frame_s1):
                frame = cv2.imread(frame_s1)
                stats = analyze_frame(frame, "01_upscale")
                print(f"  Stats: {json.dumps(stats, indent=2)}")
                all_frames.append(frame)
                all_names.append("Step1: Upscale")
                all_stats.append(stats)

                # Check for color damage
                delta_s = abs(stats["s_mean"] - stats_input["s_mean"])
                if delta_s > 20:
                    print(f"  ⚠️  WARNING: Saturation changed by {delta_s:.1f}")

    # ── Step 2: VCG Color Grading ──
    if args.ref:
        print("\n▶ STEP 2: Running VCG Color Grading...")
        if run_vcg(input_path if args.skip_upscale else upscale_out, args.ref, vcg_out):
            frame_s2 = os.path.join(FRAMES_DIR, "frame_02_vcg.png")
            if extract_first_frame(vcg_out, frame_s2):
                frame = cv2.imread(frame_s2)
                stats = analyze_frame(frame, "02_vcg")
                print(f"  Stats: {json.dumps(stats, indent=2)}")
                all_frames.append(frame)
                all_names.append("Step2: VCG")
                all_stats.append(stats)

                # Check for color damage
                prev_stats = all_stats[-2] if len(all_stats) > 1 else stats_input
                delta_r = abs(stats["r_mean"] - prev_stats["r_mean"])
                delta_b = abs(stats["b_mean"] - prev_stats["b_mean"])
                delta_s = abs(stats["s_mean"] - prev_stats["s_mean"])

                if delta_r > 20 or delta_b > 20:
                    print(f"  🚨 COLOR CAST DETECTED: R changed {delta_r:.1f}, B changed {delta_b:.1f}")
                if delta_s > 20:
                    print(f"  🚨 SATURATION DAMAGE: changed {delta_s:.1f}")
                if stats["color_cast"] != "none":
                    print(f"  🚨 COLOR CAST: {stats['color_cast']}")
    else:
        print("\n▶ STEP 2: Skipped (no --ref provided)")

    # ── Step 3: AMT Interpolation ──
    if not args.skip_amt:
        print("\n▶ STEP 3: Running AMT Interpolation...")
        prev_video = vcg_out if os.path.exists(vcg_out) else (upscale_out if os.path.exists(upscale_out) else input_path)
        if run_amt(prev_video, amt_out):
            frame_s3 = os.path.join(FRAMES_DIR, "frame_03_amt.png")
            if extract_first_frame(amt_out, frame_s3):
                frame = cv2.imread(frame_s3)
                stats = analyze_frame(frame, "03_amt")
                print(f"  Stats: {json.dumps(stats, indent=2)}")
                all_frames.append(frame)
                all_names.append("Step3: AMT")
                all_stats.append(stats)

                # Check for color damage
                prev_stats = all_stats[-2] if len(all_stats) > 1 else stats_input
                delta_r = abs(stats["r_mean"] - prev_stats["r_mean"])
                delta_b = abs(stats["b_mean"] - prev_stats["b_mean"])
                delta_s = abs(stats["s_mean"] - prev_stats["s_mean"])

                if delta_r > 20 or delta_b > 20:
                    print(f"  🚨 COLOR CAST: R changed {delta_r:.1f}, B changed {delta_b:.1f}")
                if delta_s > 20:
                    print(f"  🚨 SATURATION DAMAGE: changed {delta_s:.1f}")

    # ── Generate comparison images ──
    print("\n▶ Generating comparison images...")
    make_comparison_image(all_frames, all_names, os.path.join(FRAMES_DIR, "comparison.png"))
    make_histogram_image(all_frames, all_names, os.path.join(FRAMES_DIR, "histograms.png"))

    # ── Save report ──
    report = {
        "input": args.input,
        "steps_analyzed": len(all_stats),
        "stats": all_stats,
        "diagnosis": []
    }

    # Analyze deltas between steps
    for i in range(1, len(all_stats)):
        prev = all_stats[i - 1]
        curr = all_stats[i]
        issues = []

        r_delta = curr["r_mean"] - prev["r_mean"]
        g_delta = curr["g_mean"] - prev["g_mean"]
        b_delta = curr["b_mean"] - prev["b_mean"]

        if abs(r_delta) > 20:
            issues.append(f"Red shifted {r_delta:+.1f}")
        if abs(b_delta) > 20:
            issues.append(f"Blue shifted {b_delta:+.1f}")
        if abs(g_delta) > 20:
            issues.append(f"Green shifted {g_delta:+.1f}")

        s_delta = curr["s_mean"] - prev["s_mean"]
        if abs(s_delta) > 20:
            issues.append(f"Saturation changed {s_delta:+.1f}")

        if curr["color_cast"] != "none":
            issues.append(f"Color cast: {curr['color_cast']}")

        step_name = f"{prev['name']} → {curr['name']}"
        if issues:
            report["diagnosis"].append({"step": step_name, "issues": issues, "severity": "🚨 CRITICAL"})
        else:
            report["diagnosis"].append({"step": step_name, "issues": [], "severity": "✅ OK"})

    with open(os.path.join(TEST_DIR, "debug_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    # ── Print final diagnosis ──
    print("\n" + "=" * 60)
    print("  DIAGNOSIS")
    print("=" * 60)
    for d in report["diagnosis"]:
        print(f"\n  {d['severity']}: {d['step']}")
        for issue in d["issues"]:
            print(f"    - {issue}")

    print(f"\n✅ Full report: {TEST_DIR}/debug_report.json")
    print(f"✅ Frame comparison: {FRAMES_DIR}/comparison.png")
    print(f"✅ Histograms: {FRAMES_DIR}/histograms.png")


if __name__ == "__main__":
    main()
