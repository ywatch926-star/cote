"""
F03_AI — Étape 2: L-Diffuser Video Color Grading
Source: ICCV 2025 (seunghyuns98/VideoColorGrading)
GPU: A10G | Timeout: 600s
"""
import modal

app = modal.App("lac-vcg-color-grading")

# ─── Docker Image ────────────────────────────────────────────────────
vcg_image = (
    modal.Image.debian_slim()
    .apt_install("git", "libgl1-mesa-glx", "libglib2.0-0", "wget")
    .pip_install(
        "torch", "torchvision", "torchaudio",
        "opencv-python-headless", "transformers", "numpy",
        "accelerate", "diffusers", "einops", "scipy",
    )
    .run_commands(
        "git clone https://github.com/seunghyuns98/VideoColorGrading.git /app"
    )
)


@app.function(
    image=vcg_image,
    gpu="A10G",
    timeout=600,
    cpu=4.0,
)
def vcg_grade(
    video_bytes: bytes,
    reference_image_bytes: bytes,
    lut_resolution: int = 16,
    temporal_consistency: bool = True,
) -> bytes:
    """
    Apply neural color grading using L-Diffuser.
    Generates a 3D LUT from a reference image and applies it to video.
    
    Args:
        video_bytes: Input video as bytes
        reference_image_bytes: Reference image (the "look" to transfer) as bytes
        lut_resolution: LUT cube resolution (16 = 16x16x16)
        temporal_consistency: Enable temporal consistency across frames
    
    Returns:
        Color-graded video as bytes
    """
    import sys
    sys.path.append("/app")
    
    import torch
    import cv2
    import numpy as np
    import os
    import requests
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # ─── Write inputs to container ───────────────────────────────────
    input_path = "/tmp/input_vcg.mp4"
    ref_path = "/tmp/reference_vcg.png"
    output_path = "/tmp/output_vcg.mp4"
    
    with open(input_path, "wb") as f:
        f.write(video_bytes)
    with open(ref_path, "wb") as f:
        f.write(reference_image_bytes)
    
    # ─── Read video info ─────────────────────────────────────────────
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    
    print(f"[VCG] Input: {width}x{height} @ {fps}fps, {total_frames} frames")
    print(f"[VCG] LUT resolution: {lut_resolution}³")
    
    # ─── Load VCG Pipeline ───────────────────────────────────────────
    print("[VCG] Loading L-Diffuser model...")
    try:
        from models.vcg_pipeline import VideoColorGradingPipeline
        
        pipeline = VideoColorGradingPipeline.from_pretrained(
            "seunghyuns98/VCG-Weights",
            torch_dtype=torch.float16
        ).to(device)
        
        print("[VCG] Model loaded successfully")
        
        # Run VCG inference
        pipeline(
            video_path=input_path,
            reference_image_path=ref_path,
            output_path=output_path,
            lut_resolution=lut_resolution,
            temporal_consistency=temporal_consistency,
        )
        
    except Exception as e:
        print(f"[VCG] VCG pipeline failed: {e}")
        print("[VCG] Falling back to Reinhard color transfer...")
        
        # ─── Fallback: Reinhard color transfer ──────────────────────
        # Proven algorithm: matches mean/std of LAB channels
        # Reference: Reinhard et al. "Transfer of Color between Images" 2001
        ref_img = cv2.imread(ref_path)
        if ref_img is None:
            raise ValueError("Cannot load reference image from bytes")
        
        def reinhard_transfer(source, ref):
            """Transfer color statistics from ref to source using LAB color space."""
            src_lab = cv2.cvtColor(source, cv2.COLOR_BGR2LAB).astype(np.float32)
            ref_lab = cv2.cvtColor(ref, cv2.COLOR_BGR2LAB).astype(np.float32)
            
            result = np.copy(src_lab)
            for ch in range(3):  # L, a, b
                src_mean, src_std = src_lab[:, :, ch].mean(), src_lab[:, :, ch].std()
                ref_mean, ref_std = ref_lab[:, :, ch].mean(), ref_lab[:, :, ch].std()
                
                src_std = max(src_std, 1e-6)
                
                # Transfer: normalize source, then scale to ref stats
                result[:, :, ch] = (
                    (src_lab[:, :, ch] - src_mean) * (ref_std / src_std) + ref_mean
                )
            
            result = np.clip(result, 0, 255).astype(np.uint8)
            return cv2.cvtColor(result, cv2.COLOR_LAB2BGR)
        
        # Compute reference stats from a sample of the reference image
        # (resize ref to match source for consistent stats)
        ref_resized = cv2.resize(ref_img, (width, height))
        
        # Read all frames, apply Reinhard transfer
        cap = cv2.VideoCapture(input_path)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            graded = reinhard_transfer(frame, ref_resized)
            out.write(graded)
            frame_count += 1
        
        cap.release()
        out.release()
        print(f"[VCG] Reinhard fallback applied to {frame_count} frames")
    
    # ─── Read output ─────────────────────────────────────────────────
    with open(output_path, "rb") as f:
        output_bytes = f.read()
    
    # ─── Cleanup ─────────────────────────────────────────────────────
    for p in [input_path, ref_path, output_path]:
        if os.path.exists(p):
            os.remove(p)
    
    print(f"[VCG] Done. {len(output_bytes)} bytes output")
    return output_bytes
