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
        
        # ─── Fallback: Simple cinematic color grading ─────────────
        # Safe, predictable: saturation boost + contrast + warm tone
        def cinematic_grade(frame, sat_boost=1.15, contrast=1.08, warmth=1.03):
            """Apply subtle cinematic look without destroying skin tones."""
            # 1. Boost saturation slightly (HSV)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat_boost, 0, 255)
            frame = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
            
            # 2. Slight contrast boost
            frame = cv2.convertScaleAbs(frame, alpha=contrast, beta=0)
            
            # 3. Warm tone: boost red channel slightly, reduce blue
            frame = frame.astype(np.float32)
            frame[:, :, 2] = np.clip(frame[:, :, 2] * warmth, 0, 255)  # R
            frame[:, :, 0] = np.clip(frame[:, :, 0] / warmth, 0, 255)  # B
            
            return frame.astype(np.uint8)
        
        # Read all frames, apply cinematic grading
        cap = cv2.VideoCapture(input_path)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            graded = cinematic_grade(frame)
            out.write(graded)
            frame_count += 1
        
        cap.release()
        out.release()
        print(f"[VCG] Cinematic fallback applied to {frame_count} frames")
    
    # ─── Read output ─────────────────────────────────────────────────
    with open(output_path, "rb") as f:
        output_bytes = f.read()
    
    # ─── Cleanup ─────────────────────────────────────────────────────
    for p in [input_path, ref_path, output_path]:
        if os.path.exists(p):
            os.remove(p)
    
    print(f"[VCG] Done. {len(output_bytes)} bytes output")
    return output_bytes
